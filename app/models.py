"""Database models: accounts, per-account withdrawal settings, operations."""
from __future__ import annotations

import enum
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AccountStatus(str, enum.Enum):
    NEW = "new"
    CONNECTED = "connected"
    ERROR = "error"
    DISABLED = "disabled"


class OperationKind(str, enum.Enum):
    BALANCE = "balance"
    WITHDRAWAL = "withdrawal"
    EXCHANGE = "exchange"
    AUTH = "auth"


class OperationStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    NEEDS_CONFIRMATION = "needs_confirmation"
    BLOCKED = "blocked"


class Account(Base):
    """A single Whitebird account managed independently of all others."""

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    login: Mapped[str] = mapped_column(String(128))

    # Encrypted with Vault (Fernet) - never stored in plaintext.
    password_enc: Mapped[str] = mapped_column(Text)
    totp_secret_enc: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[AccountStatus] = mapped_column(
        Enum(AccountStatus, native_enum=False), default=AccountStatus.NEW
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # --- Per-account withdrawal settings (never shared between accounts) ---
    currency: Mapped[str | None] = mapped_column(String(16), nullable=True)
    network: Mapped[str | None] = mapped_column(String(32), nullable=True)
    wallet_address: Mapped[str | None] = mapped_column(String(256), nullable=True)
    auto_withdraw_threshold: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 8), nullable=True
    )
    auto_withdraw_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    # Fiat -> crypto conversion settings for this account
    convert_from_fiat: Mapped[str | None] = mapped_column(String(8), nullable=True)
    convert_to_asset: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Anti-detect browser profile bound to this account ("dolphin" | "octo")
    browser_provider: Mapped[str | None] = mapped_column(String(16), nullable=True)
    browser_profile_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    operations: Mapped[list["Operation"]] = relationship(
        back_populates="account", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Account {self.id} {self.name} {self.status}>"


class Operation(Base):
    """Journal of every operation performed by the system."""

    __tablename__ = "operations"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), nullable=True, index=True
    )
    kind: Mapped[OperationKind] = mapped_column(Enum(OperationKind, native_enum=False))
    status: Mapped[OperationStatus] = mapped_column(
        Enum(OperationStatus, native_enum=False), default=OperationStatus.PENDING
    )
    summary: Mapped[str] = mapped_column(Text, default="")
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Whitebird-side identifiers
    calculation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    transaction_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tx_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # Idempotency: prevents the same operation being executed twice.
    idempotency_key: Mapped[str | None] = mapped_column(
        String(128), nullable=True, unique=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    account: Mapped[Account | None] = relationship(back_populates="operations")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Operation {self.id} {self.kind} {self.status}>"


class PendingConfirmation(Base):
    """Operations awaiting explicit owner confirmation before execution."""

    __tablename__ = "pending_confirmations"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    action: Mapped[str] = mapped_column(String(32))
    payload: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (UniqueConstraint("account_id", "action", name="uq_pending_action"),)


Index("ix_operations_account_created", Operation.account_id, Operation.created_at)
