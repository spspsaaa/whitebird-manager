"""Select a mapped browser profile locally, without exposing credentials.

This step deliberately does not call undocumented browser start APIs.
"""
import argparse
import json
from pathlib import Path
from inventory import validate_inventory


def select_account(data, name):
    validate_inventory(data)
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Account name is required")
    matches = [row for row in data["accounts"] if row["name"].strip().casefold() == name.strip().casefold()]
    if len(matches) != 1:
        raise ValueError("Account not found or ambiguous")
    row = matches[0]
    return {"account": row["name"].strip(), "browser": row["browser"],
            "profile_id": row["profile_id"].strip(), "status": "selected_not_started"}


def main():
    parser = argparse.ArgumentParser(description="Select a local browser profile without launching it")
    parser.add_argument("inventory", type=Path)
    parser.add_argument("account", help="Exact account name")
    args = parser.parse_args()
    data = json.loads(args.inventory.read_text(encoding="utf-8-sig"))
    print(json.dumps(select_account(data, args.account), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
