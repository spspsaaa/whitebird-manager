"""WhiteBird local inventory validator. Offline, read-only, standard library only.

This module intentionally does not launch browsers, read cookies or send money.
Input file format: {"accounts": [{"name":"A","browser":"octo","profile_id":"id"}]}
"""
import argparse
import json
from pathlib import Path


def validate_inventory(data):
    if not isinstance(data, dict) or not isinstance(data.get("accounts"), list):
        raise ValueError("Expected an object containing an accounts list")
    rows = data["accounts"]
    if len(rows) > 100:
        raise ValueError("Too many accounts")
    seen = set()
    names = set()
    counts = {"octo": 0, "dolphin": 0}
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            raise ValueError(f"Account {index}: invalid record")
        name, browser, pid = (row.get(k) for k in ("name", "browser", "profile_id"))
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 60:
            raise ValueError(f"Account {index}: invalid name")
        if browser not in counts:
            raise ValueError(f"Account {index}: unknown browser")
        if not isinstance(pid, str) or not 1 <= len(pid.strip()) <= 120:
            raise ValueError(f"Account {index}: invalid profile ID")
        key = (browser, pid.strip())
        if key in seen:
            raise ValueError(f"Account {index}: duplicate browser profile")
        if name.strip().casefold() in names:
            raise ValueError(f"Account {index}: duplicate account name")
        seen.add(key)
        names.add(name.strip().casefold())
        counts[browser] += 1
    if counts["dolphin"] > 4:
        raise ValueError("Dolphin limit: 4")
    return {"accounts": len(rows), "octo": counts["octo"], "dolphin": counts["dolphin"], "valid": True}


def main():
    parser = argparse.ArgumentParser(description="Validate local profile mapping without network access")
    parser.add_argument("inventory", type=Path)
    args = parser.parse_args()
    data = json.loads(args.inventory.read_text(encoding="utf-8-sig"))
    print(json.dumps(validate_inventory(data), ensure_ascii=False))


if __name__ == "__main__":
    main()
