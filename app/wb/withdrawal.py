"""Withdrawal manager: calculates and executes crypto withdrawals.

Flow:
    1. calculate_crypto -> commission, received amount, calculation id
    2. owner confirmation (unless auto-approved)
    3. create_crypto with the calculation id (requires an operation MFA token)
    4. the platform may demand an extra anti-fraud verification -> we stop
       and ask the owner instead of trying to work around it
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

from whitebird._client import AsyncWhitebird
from whitebird._generated.models import BalanceAccountType, BalanceCryptoAsset

from app.wb.exceptions import (
    BLOCKING_ERRORS,
    OperationBlocked,
)

log = logging.getLogger(__name__)


@dataclass
class WithdrawalQuote:
    """Result of the calculation step."""

    calculation_id: str
    withdrawal_amount: Decimal
    commission_amount: Decimal | None
    received_amount: Decimal
    currency: str
    network: str | None
    address: str
    expires_at: str | None = None


class WithdrawalManager:
    async def quote(
        self,
        client: AsyncWhitebird,
        currency: str,
        amount: Decimal,
        network: str | None,
        address: str,
    ) -> WithdrawalQuote:
        """Calculate a withdrawal: what is sent, the fee and what arrives."""
        asset = BalanceCryptoAsset(code=currency, amount=amount, network=network)
        try:
            calculation = await client.balance.withdrawals.calculate_crypto(
                account_type=BalanceAccountType.WALLET,
                asset=asset,
                to_address=address,
            )
        except Exception as exc:
            raise self._map_error(exc) from exc

        return WithdrawalQuote(
            calculation_id=calculation.id or "",
            withdrawal_amount=calculation.withdrawalAmount or amount,
            commission_amount=calculation.commissionAmount,
            received_amount=calculation.receivedAmount or amount,
            currency=currency,
            network=network,
            address=address,
            expires_at=str(calculation.expirationDate) if calculation.expirationDate else None,
        )

    async def execute(
        self,
        client: AsyncWhitebird,
        calculation_id: str,
        comment: str | None = None,
    ) -> dict:
        """Execute a previously calculated withdrawal."""
        if not calculation_id:
            raise ValueError("calculation_id is required")
        try:
            result = await client.balance.withdrawals.create_crypto(
                account_type=BalanceAccountType.WALLET,
                calculation_id=calculation_id,
                comment=comment,
            )
        except Exception as exc:
            raise self._map_error(exc) from exc
        return result if isinstance(result, dict) else {"result": str(result)}

    # ------------------------------------------------------------- helpers
    @staticmethod
    def _map_error(exc: Exception) -> Exception:
        """Turn platform errors into domain errors."""
        message = str(exc)
        code = ""
        for candidate in BLOCKING_ERRORS:
            if candidate in message:
                code = candidate
                break
        if code:
            kind = BLOCKING_ERRORS[code]
            return OperationBlocked(
                f"Whitebird requires an extra verification step ({code}). "
                "Complete it in the browser profile, then retry.",
                kind=kind,
            )
        return exc


withdrawal_manager = WithdrawalManager()
