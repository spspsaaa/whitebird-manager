"""Single-PC read-only diagnostics for Octo and Dolphin profile inventory.

No external network calls, browser control, credentials or transfers.
"""
import argparse
import json
import socket
from datetime import datetime, timezone
from pathlib import Path

from inventory import validate_inventory


def local_port_status(host="127.0.0.1", port=58888, timeout=1.5):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return "reachable"
    except (OSError, TimeoutError):
        return "unavailable"


def octo_port_status():
    return local_port_status(port=58888)


def dolphin_port_status():
    return local_port_status(port=3001)


def build_report(inventory_path, check_port=True):
    data = json.loads(Path(inventory_path).read_text(encoding="utf-8-sig"))
    summary = validate_inventory(data)
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "inventory": summary,
        "octo_local_api": octo_port_status() if check_port else "not_checked",
        "dolphin_local_api": dolphin_port_status() if check_port else "not_checked",
        "mode": "read_only",
    }


def main():
    parser = argparse.ArgumentParser(description="Offline inventory + local Octo availability check")
    parser.add_argument("inventory", type=Path)
    parser.add_argument("--skip-port-check", action="store_true")
    args = parser.parse_args()
    print(json.dumps(build_report(args.inventory, not args.skip_port_check), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
