"""Validate user-observed wallet balances without logging or transferring them.

Local-only file format:
{"balances":[{"account":"Account 01","RUB.wb":"123.45","USDT":"2.00"}]}
Values are copied from visible wallet pages, not fetched from browser APIs.
"""
import argparse
import json
import re
from decimal import Decimal
from pathlib import Path

_AMOUNT = re.compile(r"(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,8})?\Z")


def validate_balances(data, account_names):
    if not isinstance(data, dict) or not isinstance(data.get("balances"), list):
        raise ValueError("Expected balances list")
    if len(data["balances"]) > 100:
        raise ValueError("Too many balance entries")
    allowed = {name.strip().casefold(): name for name in account_names}
    seen = set()
    totals = {"RUB.wb": Decimal("0"), "USDT": Decimal("0")}
    normalized = []
    for index, entry in enumerate(data["balances"], 1):
        if not isinstance(entry, dict) or not isinstance(entry.get("account"), str):
            raise ValueError(f"Row {index}: invalid account")
        key = entry["account"].strip().casefold()
        if key not in allowed or key in seen:
            raise ValueError(f"Row {index}: unknown or duplicate account")
        seen.add(key)
        item = {"account": allowed[key]}
        for currency in totals:
            raw = entry.get(currency)
            if not isinstance(raw, str) or not _AMOUNT.fullmatch(raw):
                raise ValueError(f"Row {index}: invalid {currency} amount")
            value = Decimal(raw)
            totals[currency] += value
            item[currency] = str(value)
        normalized.append(item)
    return {"source": "manually_observed_not_verified", "count": len(normalized),
            "totals": {k: str(v) for k, v in totals.items()}, "balances": normalized}


def main():
    parser = argparse.ArgumentParser(description="Validate local manually observed wallet balances")
    parser.add_argument("inventory", type=Path)
    parser.add_argument("balances", type=Path)
    args = parser.parse_args()
    inventory = json.loads(args.inventory.read_text(encoding="utf-8-sig"))
    from inventory import validate_inventory
    validate_inventory(inventory)
    observations = json.loads(args.balances.read_text(encoding="utf-8-sig"))
    report = validate_balances(observations, [row["name"] for row in inventory["accounts"]])
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
