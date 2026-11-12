"""WhiteBird single-PC operator: local inventory, status, selection, reports.

No transfers, credential collection, or undocumented browser API calls.
"""
import argparse
import json
import sys
from pathlib import Path
from select_profile import select_account
from unified_status import build_report
from balance_import import validate_balances
from agent_upload import upload_observations
from browser_launch import start_selected


def main(argv=None):
    parser = argparse.ArgumentParser(description="WhiteBird Windows local operator")
    parser.add_argument("--inventory", type=Path, default=Path(__file__).with_name("accounts.json"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="Check Octo and Dolphin local ports")
    sub.add_parser("accounts", help="List mapped account names and browsers")
    sub.add_parser("check", help="Run offline preflight checks and report missing inputs")
    report = sub.add_parser("report", help="Combine mapped accounts and manually observed balances")
    upload = sub.add_parser("upload", help="Opt-in HTTPS upload of observed balances")
    upload.add_argument("--balances", type=Path, default=Path(__file__).with_name("balances.json"))
    report.add_argument("--balances", type=Path, default=Path(__file__).with_name("balances.json"))
    launch = sub.add_parser("open", help="Explicitly open a named account in its local browser")
    launch.add_argument("name")
    choose = sub.add_parser("select", help="Resolve a named account to its local profile")
    choose.add_argument("name")
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.inventory.read_text(encoding="utf-8-sig"))
        from inventory import validate_inventory
        summary = validate_inventory(data)
        if args.command == "status":
            result = build_report(args.inventory)
        elif args.command == "check":
            balance_file = args.inventory.with_name("balances.json")
            result = {"inventory": summary, "balance_file_present": balance_file.is_file(),
                      "profile_mapping_complete": summary["accounts"] == 21 and
                      summary["octo"] == 17 and summary["dolphin"] == 4,
                      "ready_for_live_browser_start": False,
                      "next": "Verify installed Octo and Dolphin local API documentation before enabling profile start"}
        elif args.command == "accounts":
            result = {"summary": summary, "accounts": [
                {"name": row["name"], "browser": row["browser"]}
                for row in data["accounts"]]}
        elif args.command == "open":
            result = start_selected(data, args.name)
        elif args.command == "upload":
            observations = json.loads(args.balances.read_text(encoding="utf-8-sig"))
            result = upload_observations(observations, [row["name"] for row in data["accounts"]])
        elif args.command == "report":
            observations = json.loads(args.balances.read_text(encoding="utf-8-sig"))
            result = validate_balances(observations, [row["name"] for row in data["accounts"]])
            result["inventory"] = summary
            result["missing_accounts"] = [row["name"] for row in data["accounts"]
                                          if row["name"].strip().casefold() not in
                                          {item["account"].strip().casefold() for item in result["balances"]}]
        else:
            selected = select_account(data, args.name)
            result = {"selection": selected,
                      "notice": "Profile selected. Browser start requires verified local API configuration."}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
