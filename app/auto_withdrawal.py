"""Auto withdrawal engine.

Watches the balance of every account and, when the configured threshold is
reached, notifies the owner and - depending on the settings - performs the
withdrawal after an explicit confirmation.
"""
from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Account, AccountStatus, Operation, OperationKind, OperationStatus
from app.wb.balance import balance_manager
from app.wb.exceptions import OperationBlocked

log = logging.getLogger(__name__)


class AutoWithdrawalEngine:
    """Checks thresholds and prepares automatic withdrawals."""

    def __init__(self, account_manager, withdrawal_manager) -> None:
        self.account_manager = account_manager
        self.withdrawal_manager = withdrawal_manager

    async def check_all(self, session: AsyncSession, client_factory) -> list[dict]:
        """Check every account with auto withdrawal enabled.

        Returns the list of triggered events (for notification).
        """
        result = await session.execute(
            select(Account).where(Account.auto_withdraw_enabled.is_(True))
        )
        accounts = list(result.scalars().all())
        events: list[dict] = []

        for account in accounts:
            problems = self.account_manager.validate_withdrawal_settings(account)
            if problems:
                events.append(
                    {
                        "account": account.name,
                        "kind": "config_error",
                        "message": "Auto withdrawal is misconfigured: "
                        + ", ".join(problems),
                    }
                )
                continue

            try:
                client = await client_factory(account)
                balance = await balance_manager.balance_of(
                    client, account.currency or ""
                )
            except Exception as exc:
                log.warning("balance check failed for %s: %s", account.name, exc)
                events.append(
                    {
                        "account": account.name,
                        "kind": "error",
                        "message": f"Could not read the balance: {exc}",
                    }
                )
                continue

            threshold = account.auto_withdraw_threshold or Decimal("0")
            if balance <= threshold:
                continue

            events.append(
                {
                    "account": account.name,
                    "account_id": account.id,
                    "kind": "threshold_reached",
                    "currency": account.currency,
                    "balance": str(balance),
                    "threshold": str(threshold),
                    "message": (
                        f"{account.name}: balance {balance} {account.currency} "
                        f"reached the threshold {threshold}. Withdrawal prepared."
                    ),
                }
            )

            operation = Operation(
                account_id=account.id,
                kind=OperationKind.WITHDRAWAL,
                status=OperationStatus.NEEDS_CONFIRMATION,
                summary=(
                    f"Auto withdrawal {balance} {account.currency} -> "
                    f"{account.wallet_address}"
                ),
                details=(
                    f"balance={balance} threshold={threshold} "
                    f"network={account.network} address={account.wallet_address}"
                ),
                idempotency_key=f"auto:{account.id}:{account.currency}:{balance}",
            )
            session.add(operation)
            await session.flush()

            try:
                quote = await self.withdrawal_manager.quote(
                    client,
                    currency=account.currency or "",
                    amount=balance,
                    network=account.network,
                    address=account.wallet_address or "",
                )
                operation.calculation_id = quote.calculation_id
                operation.details = (
                    f"balance={balance} threshold={threshold} "
                    f"network={account.network} address={account.wallet_address} "
                    f"commission={quote.commission_amount} "
                    f"received={quote.received_amount}"
                )
                operation.status = OperationStatus.NEEDS_CONFIRMATION
            except OperationBlocked as exc:
                operation.status = OperationStatus.BLOCKED
                operation.error = str(exc)
                events.append(
                    {
                        "account": account.name,
                        "kind": "blocked",
                        "message": str(exc),
                    }
                )
            except Exception as exc:
                operation.status = OperationStatus.FAILED
                operation.error = str(exc)

        return events

    async def mark_status(
        self, session: AsyncSession, account_id: int, status: AccountStatus, error: str | None = None
    ) -> None:
        await self.account_manager.set_status(session, account_id, status, error)
