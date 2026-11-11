"""Offline session orchestration for WhiteBird Manager.

Adapters are deliberately provider-neutral. No credentials, TOTP generation,
browser control or live financial operations are included.
"""
from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


class LoginRequired(Exception):
    pass


class VerificationRequired(Exception):
    pass


class SessionAdapter(Protocol):
    def is_authenticated(self, account_id: int) -> bool: ...
    def login(self, account_id: int) -> bool: ...
    def read_balance(self, account_id: int) -> Decimal: ...


@dataclass(frozen=True)
class BalanceResult:
    account_id: int
    balance: Decimal
    relogged: bool


class SessionManager:
    def __init__(self, adapter: SessionAdapter):
        self.adapter = adapter

    def check_balance(self, account_id: int) -> BalanceResult:
        if type(account_id) is not int or account_id <= 0:
            raise ValueError("Invalid account ID")
        relogged = False
        if not self.adapter.is_authenticated(account_id):
            if not self.adapter.login(account_id):
                raise VerificationRequired("Owner verification required")
            relogged = True
        if not self.adapter.is_authenticated(account_id):
            raise LoginRequired("Session is not authenticated")
        balance = self.adapter.read_balance(account_id)
        if not isinstance(balance, Decimal) or not balance.is_finite() or balance < 0:
            raise ValueError("Invalid balance from provider")
        return BalanceResult(account_id, balance, relogged)


class OfflineDemoAdapter:
    """Test double only. Does not connect to WhiteBird or a browser."""

    def __init__(self, balances: dict[int, str], active: set[int] | None = None,
                 require_verification: bool = False):
        self.balances = balances
        self.active = set(active or ())
        self.require_verification = require_verification
        self.login_attempts = 0

    def is_authenticated(self, account_id: int) -> bool:
        return account_id in self.active

    def login(self, account_id: int) -> bool:
        self.login_attempts += 1
        if self.require_verification or account_id not in self.balances:
            return False
        self.active.add(account_id)
        return True

    def read_balance(self, account_id: int) -> Decimal:
        if account_id not in self.active:
            raise LoginRequired("Not authenticated")
        return Decimal(self.balances[account_id])
