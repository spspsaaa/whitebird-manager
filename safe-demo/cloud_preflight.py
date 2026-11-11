"""Read-only Linux host preflight for a future browser worker.

Does not launch browsers, inspect profiles, read credentials, or contact any
external service. Report is suitable for sharing after reviewing hostname.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
import sys
from pathlib import Path


def _memory_gib(meminfo: str) -> float | None:
    for line in meminfo.splitlines():
        if line.startswith("MemTotal:"):
            parts = line.split()
            if len(parts) >= 2 and parts[1].isdigit():
                return round(int(parts[1]) / (1024 * 1024), 2)
    return None


def assess(system: str, memory_gib: float | None, free_disk_gib: float,
           cpu_count: int | None, display_available: bool) -> dict:
    checks = {
        "linux": system == "Linux",
        "memory_recommended_8_gib": memory_gib is not None and memory_gib >= 8,
        "disk_at_least_40_gib": free_disk_gib >= 40,
        "cpu_at_least_2": cpu_count is not None and cpu_count >= 2,
        "display_available": display_available,
    }
    return {
        "checks": checks,
        "ready_for_manual_browser_trial": all(checks.values()),
        "note": "Passing does not prove Octo/Dolphin compatibility or 24/7 uptime.",
    }


def inspect_host() -> dict:
    try:
        meminfo = Path("/proc/meminfo").read_text(encoding="utf-8")
    except OSError:
        meminfo = ""
    disk = shutil.disk_usage("/")
    memory = _memory_gib(meminfo)
    free_disk = round(disk.free / (1024 ** 3), 2)
    cpu = os.cpu_count()
    display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    result = assess(platform.system(), memory, free_disk, cpu, display)
    result["resources"] = {
        "os": platform.system(),
        "architecture": platform.machine(),
        "memory_gib": memory,
        "free_disk_gib": free_disk,
        "cpu_count": cpu,
        "display_available": display,
    }
    return result


if __name__ == "__main__":
    json.dump(inspect_host(), sys.stdout, ensure_ascii=False, indent=2)
    print()
