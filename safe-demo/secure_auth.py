"""Authorization boundary and durable, one-time owner approvals.

No TOTP seed, password, browser automation, or payment execution is implemented.
A production authentication adapter must use the provider's approved 2FA flow.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import sqlite3
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Protocol


class AuthenticationRequired(PermissionError):
    pass


class AuthenticationAdapter(Protocol):
    """Provider-approved login interface. Never return or log credentials."""

    def begin_login(self, account_id: int) -> str:
        """Return an opaque challenge ID, not a secret."""

    def finish_login(self, challenge_id: str, owner_supplied_code: str) -> bool:
        """Complete the provider's approved challenge."""


@dataclass(frozen=True)
class WithdrawalIntent:
    account_id: int
    currency: str
    amount: str
    network: str
    destination: str
    fee: str

    def canonical(self) -> bytes:
        if type(self.account_id) is not int or self.account_id <= 0:
            raise ValueError("Invalid account")
        if self.currency != "USDT":
            raise ValueError("Unsupported currency")
        try:
            amount, fee = Decimal(self.amount), Decimal(self.fee)
        except (InvalidOperation, TypeError):
            raise ValueError("Invalid amount or fee") from None
        if not amount.is_finite() or amount <= 0 or not fee.is_finite() or fee < 0:
            raise ValueError("Invalid amount or fee")
        if not self.network or len(self.network) > 64:
            raise ValueError("Invalid network")
        if not self.destination or len(self.destination) > 256:
            raise ValueError("Invalid destination")
        payload = {
            "account_id": self.account_id,
            "currency": self.currency,
            "amount": str(amount.normalize()),
            "network": self.network,
            "destination": self.destination,
            "fee": str(fee.normalize()),
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


class ApprovalStore:
    """SQLite-backed approval tickets; never executes an external transfer."""

    def __init__(self, db_path: str, owner_id: int, ttl_seconds: int = 300):
        if type(owner_id) is not int or owner_id <= 0:
            raise ValueError("Invalid owner")
        if not 1 <= ttl_seconds <= 3600:
            raise ValueError("Invalid TTL")
        self.db_path = db_path
        self.owner_id = owner_id
        self.ttl_seconds = ttl_seconds
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS withdrawal_approvals (
                ticket_hash TEXT PRIMARY KEY,
                intent_hash TEXT NOT NULL,
                expires_at INTEGER NOT NULL,
                consumed_at INTEGER,
                created_at INTEGER NOT NULL
            )""")

    def _connect(self):
        connection = sqlite3.connect(self.db_path, timeout=15, isolation_level=None)
        connection.execute("PRAGMA busy_timeout=15000")
        return connection

    def _check_owner(self, actor_id: int):
        if type(actor_id) is not int or actor_id != self.owner_id:
            raise PermissionError("Only the owner may approve an operation")

    def prepare(self, actor_id: int, intent: WithdrawalIntent) -> str:
        self._check_owner(actor_id)
        digest = hashlib.sha256(intent.canonical()).hexdigest()
        ticket = secrets.token_urlsafe(32)
        ticket_hash = hashlib.sha256(ticket.encode()).hexdigest()
        now = int(time.time())
        with self._connect() as db:
            db.execute(
                "INSERT INTO withdrawal_approvals VALUES (?, ?, ?, NULL, ?)",
                (ticket_hash, digest, now + self.ttl_seconds, now),
            )
        return ticket

    def consume(self, actor_id: int, ticket: str, intent: WithdrawalIntent) -> bool:
        """Atomically consume approval for the *exact* operation parameters.

        False means missing, expired, changed, or already consumed. The caller
        must never interpret False as authorization. A consumed ticket is not
        proof of transfer execution; external settlement requires a separate
        durable idempotency mechanism and reconciliation.
        """
        self._check_owner(actor_id)
        if not isinstance(ticket, str) or len(ticket) > 256:
            return False
        intent_hash = hashlib.sha256(intent.canonical()).hexdigest()
        ticket_hash = hashlib.sha256(ticket.encode()).hexdigest()
        now = int(time.time())
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                row = db.execute(
                    "SELECT intent_hash, expires_at, consumed_at FROM withdrawal_approvals WHERE ticket_hash=?",
                    (ticket_hash,),
                ).fetchone()
                if row is None or row[1] <= now or row[2] is not None or not hmac.compare_digest(row[0], intent_hash):
                    db.execute("ROLLBACK")
                    return False
                db.execute(
                    "UPDATE withdrawal_approvals SET consumed_at=? WHERE ticket_hash=? AND consumed_at IS NULL",
                    (now, ticket_hash),
                )
                db.execute("COMMIT")
                return True
            except Exception:
                db.execute("ROLLBACK")
                raise
