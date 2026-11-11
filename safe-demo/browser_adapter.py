"""Safe browser-profile dispatch boundary.

The local browser bridge is intentionally not implemented: only a trusted,
locally installed adapter may launch a profile. No remote command execution,
cookies, credentials, or 2FA secrets are handled here.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Protocol

PROFILE_ID = re.compile(r"^[A-Za-z0-9_-]{1,120}$")


class BrowserUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class BrowserProfile:
    account_id: int
    browser: str
    profile_id: str

    def __post_init__(self):
        if type(self.account_id) is not int or self.account_id <= 0:
            raise ValueError("Invalid account ID")
        if self.browser not in ("octo", "dolphin"):
            raise ValueError("Unsupported browser")
        if not isinstance(self.profile_id, str) or not PROFILE_ID.fullmatch(self.profile_id):
            raise ValueError("Invalid profile ID")


class LocalBrowserBridge(Protocol):
    def open_profile(self, browser: str, profile_id: str) -> bool: ...
    def profile_is_running(self, browser: str, profile_id: str) -> bool: ...


class BrowserProfileManager:
    def __init__(self, bridge: LocalBrowserBridge, profiles: dict[int, BrowserProfile]):
        self.bridge = bridge
        self.profiles = dict(profiles)
        for account_id, profile in self.profiles.items():
            if type(account_id) is not int or account_id != profile.account_id:
                raise ValueError("Account/profile mismatch")

    def ensure_open(self, account_id: int) -> BrowserProfile:
        if type(account_id) is not int or account_id not in self.profiles:
            raise ValueError("Unknown account")
        profile = self.profiles[account_id]
        if not self.bridge.profile_is_running(profile.browser, profile.profile_id):
            if not self.bridge.open_profile(profile.browser, profile.profile_id):
                raise BrowserUnavailable("Browser profile could not be started")
        if not self.bridge.profile_is_running(profile.browser, profile.profile_id):
            raise BrowserUnavailable("Browser profile did not become ready")
        return profile


class OfflineBrowserBridge:
    """Test-only bridge, with no connection to real browser software."""

    def __init__(self, fail_to_open: bool = False):
        self.running = set()
        self.open_calls = []
        self.fail_to_open = fail_to_open

    def open_profile(self, browser: str, profile_id: str) -> bool:
        self.open_calls.append((browser, profile_id))
        if self.fail_to_open:
            return False
        self.running.add((browser, profile_id))
        return True

    def profile_is_running(self, browser: str, profile_id: str) -> bool:
        return (browser, profile_id) in self.running
