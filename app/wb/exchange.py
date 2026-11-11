"""Exchange manager: converts fiat (RUB) into crypto and back.

Flow:
    1. quotes.create -> a quote with the rate and the resulting amount
    2. orders.create -> an exchange order
    3. poll orders.get until the order reaches COMPLETED / FAILED / EXPIRED

The destination of the crypto leg is the Whitebird wallet of the same
account, so the converted amount lands on the account balance and can then
be withdrawn to the configured address.
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from decimal import Decimal

from whitebird._client import AsyncWhitebird
from whitebird._generated.models import (
    ExchangeDestination,
    ExchangeLegType,
    ExchangeQuoteLegRequest,
)

log = logging.getLogger(__name__)


@dataclass
class ExchangeQuote:
    quote_id: str
    input_amount: Decimal
    input_currency: str
    output_amount: Decimal
    output_currency: str
    rate: Decimal | None
    expires_at: str | None = None


class ExchangeManager:
    async def quote(
        self,
        client: AsyncWhitebird,
        from_asset: str,
        to_asset: str,
        amount: Decimal,
        provider: str | None = None,
        token: str | None = None,
        to_address: str | None = None,
    ) -> ExchangeQuote:
        """Get a quote for converting `from_asset` into `to_asset`."""
        input_leg = ExchangeQuoteLegRequest(
            asset=from_asset,
            type=ExchangeLegType.FIAT_PROVIDER,
            amount=amount,
            provider=provider,
            token=token,
        )
        output_leg = ExchangeQuoteLegRequest(
            asset=to_asset,
            type=ExchangeLegType.INTERNAL_BALANCE,
            to_address=to_address,
        )
        try:
            quote = await client.exchange.quotes.create(input=input_leg, output=output_leg)
        except Exception as exc:
            raise exc

        in_amount = Decimal(str(getattr(quote.input, "amount", amount) or amount))
        out_amount = Decimal(str(getattr(quote.output, "amount", 0) or 0))
        return ExchangeQuote(
            quote_id=quote.id or "",
            input_amount=in_amount,
            input_currency=from_asset,
            output_amount=out_amount,
            output_currency=to_asset,
            rate=quote.exchange_rate_value,
            expires_at=str(quote.expiration_date) if quote.expiration_date else None,
        )

    async def execute(
        self,
        client: AsyncWhitebird,
        quote_id: str,
        destination: str = ExchangeDestination.EXCHANGE,
        external_id: str | None = None,
    ) -> dict:
        """Create the exchange order for a previously obtained quote."""
        result = await client.exchange.orders.create(
            quote_id=quote_id,
            destination=destination,
            external_id=external_id,
        )
        return result.model_dump() if hasattr(result, "model_dump") else dict(result)

    async def wait(
        self,
        client: AsyncWhitebird,
        order_id: str,
        timeout: float = 300.0,
        interval: float = 5.0,
    ) -> dict:
        """Poll the order until it completes or fails."""
        deadline = asyncio.get_running_loop().time() + timeout
        last: dict = {}
        while asyncio.get_running_loop().time() < deadline:
            order = await client.exchange.orders.get(order_id)
            last = order.model_dump() if hasattr(order, "model_dump") else dict(order)
            status = str(last.get("status", "")).upper()
            if status in {"COMPLETED", "FAILED", "EXPIRED", "DECLINED"}:
                return last
            await asyncio.sleep(interval)
        last["timeout"] = True
        return last

    async def assets(self, client: AsyncWhitebird) -> dict:
        """List the crypto and fiat assets available for exchange."""
        assets = await client.exchange.assets.list()
        return assets.model_dump() if hasattr(assets, "model_dump") else dict(assets)


exchange_manager = ExchangeManager()
