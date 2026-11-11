"""Offline command-gated login simulator. No real browser, TOTP, or money movement."""
from dataclasses import dataclass
from threading import RLock


@dataclass(frozen=True)
class LoginResult:
    account_id: int
    status: str
    rub: str = ""
    usdt: str = ""


class FakeBrowser:
    def __init__(self):
        self.opened = set()
        self.events = []

    def open_profile(self, account_id):
        self.events.append(("open", account_id))
        self.opened.add(account_id)

    def close_profile(self, account_id):
        self.events.append(("close", account_id))
        self.opened.discard(account_id)


class FakeLoginProvider:
    def __init__(self, expected_code="TEST-123456"):
        self.expected_code = expected_code

    def login(self, account_id, code):
        return code == self.expected_code

    def balances(self, account_id):
        return {"rub": "1250.00", "usdt": "42.50"}


class CommandLoginDemo:
    def __init__(self, owner_id, browser=None, provider=None):
        if type(owner_id) is not int or owner_id <= 0:
            raise ValueError("owner_id must be positive integer")
        self.owner_id = owner_id
        self.browser = browser if browser is not None else FakeBrowser()
        self.provider = provider if provider is not None else FakeLoginProvider()
        self._lock = RLock()
        self._pending = set()

    def request_login(self, actor_id, account_id):
        self._authorize(actor_id, account_id)
        with self._lock:
            if account_id in self._pending:
                return LoginResult(account_id, "already_pending")
            self._pending.add(account_id)
            return LoginResult(account_id, "awaiting_test_code")

    def complete_login(self, actor_id, account_id, test_code):
        self._authorize(actor_id, account_id)
        with self._lock:
            if account_id not in self._pending:
                return LoginResult(account_id, "not_requested")
            self._pending.remove(account_id)
            try:
                self.browser.open_profile(account_id)
                if not self.provider.login(account_id, test_code):
                    return LoginResult(account_id, "login_failed")
                balances = self.provider.balances(account_id)
                return LoginResult(account_id, "balance_read", balances["rub"], balances["usdt"])
            finally:
                self.browser.close_profile(account_id)

    def withdraw(self, actor_id, account_id):
        self._authorize(actor_id, account_id)
        raise PermissionError("Real withdrawals are disabled in offline simulator")

    def _authorize(self, actor_id, account_id):
        if type(actor_id) is not int or actor_id != self.owner_id:
            raise PermissionError("Not the bot owner")
        if type(account_id) is not int or account_id <= 0:
            raise ValueError("Invalid account ID")
