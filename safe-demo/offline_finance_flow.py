"""Strictly offline WhiteBird-like financial workflow simulator.

No network, browser API, real TOTP seed, credentials, or real transfers.
"""
from dataclasses import dataclass
from decimal import Decimal
from threading import RLock
from uuid import uuid4

RATE_RUB_PER_USDT = Decimal("100.00")
ZERO = Decimal("0.00")


@dataclass(frozen=True)
class Snapshot:
    rub: Decimal
    usdt: Decimal


class MockAccount:
    def __init__(self, rub="1250.00", usdt="42.50"):
        self.rub = Decimal(rub)
        self.usdt = Decimal(usdt)
        self.logged_in = False
        self.code_entries = []
        self.history = []


class OfflineFinanceAgent:
    """Simulates code entry, conversion, approval, and withdrawal in memory."""

    def __init__(self, owner_id, code="TEST-123456"):
        if type(owner_id) is not int or owner_id <= 0:
            raise ValueError("Invalid owner")
        self.owner_id = owner_id
        self._test_code = code
        self._accounts = {}
        self._drafts = {}
        self._completed = {}
        self._lock = RLock()

    def _auth(self, actor_id):
        if type(actor_id) is not int or actor_id != self.owner_id:
            raise PermissionError("Only the owner can operate the simulator")

    def _account(self, account_id):
        if type(account_id) is not int or account_id <= 0:
            raise ValueError("Invalid account")
        return self._accounts.setdefault(account_id, MockAccount())

    def enter_test_code(self, actor_id, account_id, code):
        self._auth(actor_id)
        with self._lock:
            account = self._account(account_id)
            account.code_entries.append("[REDACTED]")
            account.logged_in = code == self._test_code
            return account.logged_in

    def balance(self, actor_id, account_id):
        self._auth(actor_id)
        with self._lock:
            account = self._account(account_id)
            if not account.logged_in:
                raise PermissionError("Test login required")
            return Snapshot(account.rub, account.usdt)

    def convert_all_rub(self, actor_id, account_id):
        self._auth(actor_id)
        with self._lock:
            account = self._account(account_id)
            if not account.logged_in:
                raise PermissionError("Test login required")
            if any(d["account_id"] == account_id for d in self._drafts.values()):
                raise PermissionError("Pending withdrawal must be resolved first")
            converted = (account.rub / RATE_RUB_PER_USDT).quantize(Decimal("0.01"))
            account.usdt += converted
            account.rub = ZERO
            account.history.append(("mock_conversion", converted))
            return self.balance(actor_id, account_id)

    def prepare_withdrawal(self, actor_id, account_id, destination):
        self._auth(actor_id)
        if not isinstance(destination, str) or not destination.startswith("TEST-") or len(destination) > 80:
            raise ValueError("Only fake TEST- destinations allowed")
        with self._lock:
            account = self._account(account_id)
            if not account.logged_in:
                raise PermissionError("Test login required")
            if account.usdt <= ZERO:
                raise ValueError("Nothing to withdraw")
            if any(d["account_id"] == account_id for d in self._drafts.values()):
                raise PermissionError("Already pending")
            request_id = uuid4().hex
            self._drafts[request_id] = {
                "account_id": account_id,
                "destination": destination,
                "amount": account.usdt,
            }
            return {"request_id": request_id, **self._drafts[request_id]}

    def confirm_withdrawal(self, actor_id, request_id):
        self._auth(actor_id)
        with self._lock:
            if request_id in self._completed:
                return {"status": "already_completed", **self._completed[request_id]}
            draft = self._drafts.pop(request_id, None)
            if draft is None:
                raise ValueError("Unknown or expired request")
            account = self._account(draft["account_id"])
            if not account.logged_in or account.usdt != draft["amount"]:
                raise PermissionError("Session or amount changed; create a new request")
            account.usdt = ZERO
            account.history.append(("mock_withdrawal", draft["amount"], draft["destination"]))
            result = {**draft, "status": "simulated_only"}
            self._completed[request_id] = result
            return result

    def logout(self, actor_id, account_id):
        self._auth(actor_id)
        with self._lock:
            self._account(account_id).logged_in = False
            for request_id, draft in list(self._drafts.items()):
                if draft["account_id"] == account_id:
                    del self._drafts[request_id]
