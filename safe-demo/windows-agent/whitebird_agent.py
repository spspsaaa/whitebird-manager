"""WhiteBird single-PC operator: local inventory, status, selection, reports.

No transfers, credential collection, or undocumented browser API calls.
"""
import argparse
import json
import sys
from pathlib import Path
from select_profile import select_account
from unified_status import build_report


def main(argv=None):
    parser = argparse.ArgumentParser(description="WhiteBird Windows local operator")
    parser.add_argument("--inventory", type=Path, default=Path(__file__).with_name("accounts.json"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="Check Octo and Dolphin local ports")
    sub.add_parser("accounts", help="List mapped account names and browsers")
    choose = sub.add_parser("select", help="Resolve a named account to its local profile")
    choose.add_argument("name")
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.inventory.read_text(encoding="utf-8-sig"))
        from inventory import validate_inventory
        summary = validate_inventory(data)
        if args.command == "status":
            result = build_report(args.inventory)
        elif args.command == "accounts":
            result = {"summary": summary, "accounts": [
                {"name": row["name"], "browser": row["browser"]}
                for row in data["accounts"]]}
        else:
            selected = select_account(data, args.name)
            result = {"selection": selected,
                      "notice": "Profile selected. Browser start requires verified local API configuration."}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
