"""Balance manager: reads the balances of one account."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

from whitebird._client import AsyncWhitebird
from whitebird._generated.models import AccountingAccountType

log = logging.getLogger(__name__)


@dataclass
class BalanceItem:
    currency: str
    amount: Decimal
    usd_amount: Decimal | None = None
    reserved: Decimal | None = None
    type: str | None = None

    @property
    def available(self) -> Decimal:
        if self.reserved is None:
            return self.amount
        return self.amount - self.reserved


class BalanceManager:
    async def balances(self, client: AsyncWhitebird) -> list[BalanceItem]:
        """All balances of the account (enhanced: includes USD value)."""
        account = await client.accounting.accounts.get_enhanced(
            type=AccountingAccountType.USER_BALANCE
        )
        items: list[BalanceItem] = []
        for balance in account.balances or []:
            items.append(
                BalanceItem(
                    currency=balance.currency,
                    amount=balance.amount,
                    usd_amount=getattr(balance, "usd_amount", None),
                    reserved=getattr(balance, "reserved_amount", None),
                    type=getattr(balance, "type", None),
                )
            )
        return items

    async def balance_of(self, client: AsyncWhitebird, currency: str) -> Decimal:
        """Balance of one currency (0 when the account has none)."""
        for item in await self.balances(client):
            if item.currency.upper() == currency.upper():
                return item.amount
        return Decimal("0")

    async def total_usd(self, client: AsyncWhitebird) -> Decimal:
        """Total balance of the account converted to USD."""
        total = Decimal("0")
        for item in await self.balances(client):
            if item.usd_amount is not None:
                total += item.usd_amount
        return total


balance_manager = BalanceManager()
