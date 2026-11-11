import pytest
from decimal import Decimal
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.account_manager import AccountManager
from app.db import Base
from app.models import Account


@pytest.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s:
        yield s
    await engine.dispose()


async def test_create_and_read_credentials(session):
    manager = AccountManager()
    account = await manager.create(
        session,
        name="acc1",
        login="user@wb.by",
        password="p@ssw0rd",
        totp_secret="JBSWY3DPEHPK3PXP",
        currency="USDT",
        network="TRC",
        wallet_address="TXXX",
        auto_withdraw_threshold=Decimal("10"),
        auto_withdraw_enabled=True,
    )
    await session.commit()

    login, password, totp = manager.credentials(account)
    assert login == "user@wb.by"
    assert password == "p@ssw0rd"
    assert totp == "JBSWY3DPEHPK3PXP"
    # the plaintext must not be stored
    assert "p@ssw0rd" not in account.password_enc


async def test_settings_are_isolated(session):
    manager = AccountManager()
    a1 = await manager.create(session, name="a1", login="l1", password="p1")
    a2 = await manager.create(session, name="a2", login="l2", password="p2")
    await session.commit()

    await manager.update_settings(session, a1.id, currency="USDT", network="TRC")
    await session.commit()

    assert a1.currency == "USDT"
    assert a2.currency is None


async def test_validate_settings(session):
    manager = AccountManager()
    account = await manager.create(session, name="a", login="l", password="p")
    problems = manager.validate_withdrawal_settings(account)
    assert len(problems) == 3
    assert any("currency" in p for p in problems)


async def test_parse_amount():
    manager = AccountManager()
    assert manager.parse_amount("10.5") == Decimal("10.5")
    assert manager.parse_amount(" 1 000,25 ") == Decimal("1000.25")
    with pytest.raises(ValueError):
        manager.parse_amount("abc")
    with pytest.raises(ValueError):
        manager.parse_amount("0")
