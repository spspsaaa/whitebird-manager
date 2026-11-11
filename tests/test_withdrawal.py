from decimal import Decimal

import pytest

from app.wb.exceptions import OperationBlocked
from app.wb.withdrawal import WithdrawalManager


class FakeCalculation:
    def __init__(self):
        self.id = "calc-1"
        self.withdrawalAmount = Decimal("10")
        self.commissionAmount = Decimal("0.5")
        self.receivedAmount = Decimal("9.5")
        self.expirationDate = None


class FakeWithdrawals:
    def __init__(self, error=None):
        self.error = error
        self.created = []

    async def calculate_crypto(self, **kwargs):
        if self.error:
            raise self.error
        return FakeCalculation()

    async def create_crypto(self, **kwargs):
        self.created.append(kwargs)
        return {"transactionId": "tx-1"}


class FakeBalance:
    def __init__(self, error=None):
        self.withdrawals = FakeWithdrawals(error)
        self.operations = FakeWithdrawals()


class FakeClient:
    def __init__(self, error=None):
        self.balance = FakeBalance(error)


async def test_quote_returns_commission():
    manager = WithdrawalManager()
    quote = await manager.quote(
        FakeClient(), "USDT", Decimal("10"), "TRC", "TXXX"
    )
    assert quote.calculation_id == "calc-1"
    assert quote.commission_amount == Decimal("0.5")
    assert quote.received_amount == Decimal("9.5")


async def test_execute_passes_calculation_id():
    manager = WithdrawalManager()
    client = FakeClient()
    result = await manager.execute(client, "calc-1", comment="test")
    assert result == {"transactionId": "tx-1"}
    assert client.balance.withdrawals.created[0]["calculation_id"] == "calc-1"


async def test_blocking_error_is_mapped():
    manager = WithdrawalManager()
    client = FakeClient(error=Exception("SMS_VERIFICATION_REQUIRED"))
    with pytest.raises(OperationBlocked) as exc:
        await manager.quote(client, "USDT", Decimal("10"), "TRC", "TXXX")
    assert exc.value.kind == "sms"


async def test_execute_requires_calculation_id():
    manager = WithdrawalManager()
    with pytest.raises(ValueError):
        await manager.execute(FakeClient(), "")
