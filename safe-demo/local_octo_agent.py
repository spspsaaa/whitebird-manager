"""Local, offline-first Octo profile inventory helper.

This module deliberately does not connect to a browser, WhiteBird or Telegram.
It never reads cookies, passwords, 2FA secrets or wallet addresses.
"""
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

PROFILE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,120}$")

@dataclass(frozen=True)
class LocalProfile:
    account_id: int
    browser: str
    profile_id: str

def parse_profile_config(data):
    if not isinstance(data, dict):
        raise ValueError("Configuration must be an object")
    if set(data) != {"account_id", "browser", "profile_id"}:
        raise ValueError("Only account_id, browser and profile_id are allowed")
    account_id = data["account_id"]
    browser = data["browser"]
    profile_id = data["profile_id"]
    if isinstance(account_id, bool) or not isinstance(account_id, int) or account_id <= 0:
        raise ValueError("Invalid account ID")
    if browser != "octo":
        raise ValueError("Only Octo Browser is supported by this helper")
    if not isinstance(profile_id, str) or not PROFILE_ID_PATTERN.fullmatch(profile_id):
        raise ValueError("Invalid profile ID")
    return LocalProfile(account_id, browser, profile_id)

def load_profile_config(path):
    file_path = Path(path).expanduser()
    if file_path.is_symlink() or not file_path.is_file():
        raise ValueError("Expected a regular configuration file")
    if file_path.stat().st_size > 4096:
        raise ValueError("Configuration too large")
    with file_path.open("r", encoding="utf-8") as handle:
        return parse_profile_config(json.load(handle))

def status(profile):
    if not isinstance(profile, LocalProfile):
        raise TypeError("Expected LocalProfile")
    return {
        "account_id": profile.account_id,
        "browser": profile.browser,
        "profile_configured": True,
        "browser_connected": False,
        "whitebird_connected": False,
        "balances_available": False,
        "mode": "read_only",
    }

def main():
    path = os.environ.get("OCTO_PROFILE_CONFIG")
    if not path:
        raise SystemExit("Set OCTO_PROFILE_CONFIG to a local JSON config file")
    profile = load_profile_config(path)
    print(json.dumps(status(profile), ensure_ascii=False))

if __name__ == "__main__":
    main()
