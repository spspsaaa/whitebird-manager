"""Account manager: CRUD and per-account settings.

Every account keeps its own withdrawal settings - changing one account
never touches another.
"""
from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Account, AccountStatus
from app.security import Vault
from app.wb.exceptions import AccountNotFound

log = logging.getLogger(__name__)


class AccountManager:
    def __init__(self, vault: Vault | None = None) -> None:
        self.vault = vault or Vault()

    # ------------------------------------------------------------------ CRUD
    async def create(
        self,
        session: AsyncSession,
        name: str,
        login: str,
        password: str,
        totp_secret: str | None = None,
        currency: str | None = None,
        network: str | None = None,
        wallet_address: str | None = None,
        auto_withdraw_threshold: Decimal | None = None,
        auto_withdraw_enabled: bool = False,
        convert_from_fiat: str | None = None,
        convert_to_asset: str | None = None,
    ) -> Account:
        """Add a new account together with all of its settings."""
        account = Account(
            name=name,
            login=login,
            password_enc=self.vault.encrypt(password),
            totp_secret_enc=self.vault.encrypt(totp_secret) if totp_secret else None,
            status=AccountStatus.NEW,
            currency=currency,
            network=network,
            wallet_address=wallet_address,
            auto_withdraw_threshold=auto_withdraw_threshold,
            auto_withdraw_enabled=auto_withdraw_enabled,
            convert_from_fiat=convert_from_fiat,
            convert_to_asset=convert_to_asset,
        )
        session.add(account)
        await session.flush()
        return account

    async def get(self, session: AsyncSession, account_id: int) -> Account:
        account = await session.get(Account, account_id)
        if account is None:
            raise AccountNotFound(f"Account {account_id} not found")
        return account

    async def list_all(self, session: AsyncSession) -> list[Account]:
        result = await session.execute(select(Account).order_by(Account.name))
        return list(result.scalars().all())

    async def by_name(self, session: AsyncSession, name: str) -> Account | None:
        result = await session.execute(select(Account).where(Account.name == name))
        return result.scalars().first()

    async def delete(self, session: AsyncSession, account_id: int) -> None:
        account = await self.get(session, account_id)
        await session.delete(account)

    # -------------------------------------------------------------- secrets
    def credentials(self, account: Account) -> tuple[str, str, str | None]:
        """Return (login, password, totp_secret) decrypted."""
        password = self.vault.decrypt(account.password_enc)
        totp = (
            self.vault.decrypt(account.totp_secret_enc)
            if account.totp_secret_enc
            else None
        )
        return account.login, password, totp

    # -------------------------------------------------------------- settings
    async def update_settings(
        self,
        session: AsyncSession,
        account_id: int,
        currency: str | None = None,
        network: str | None = None,
        wallet_address: str | None = None,
        auto_withdraw_threshold: Decimal | None = None,
        auto_withdraw_enabled: bool | None = None,
        convert_from_fiat: str | None = None,
        convert_to_asset: str | None = None,
        password: str | None = None,
        totp_secret: str | None = None,
    ) -> Account:
        """Change the settings of one account only."""
        account = await self.get(session, account_id)
        if currency is not None:
            account.currency = currency
        if network is not None:
            account.network = network
        if wallet_address is not None:
            account.wallet_address = wallet_address
        if auto_withdraw_threshold is not None:
            account.auto_withdraw_threshold = auto_withdraw_threshold
        if auto_withdraw_enabled is not None:
            account.auto_withdraw_enabled = auto_withdraw_enabled
        if convert_from_fiat is not None:
            account.convert_from_fiat = convert_from_fiat
        if convert_to_asset is not None:
            account.convert_to_asset = convert_to_asset
        if password:
            account.password_enc = self.vault.encrypt(password)
        if totp_secret:
            account.totp_secret_enc = self.vault.encrypt(totp_secret)
        return account

    async def set_status(
        self,
        session: AsyncSession,
        account_id: int,
        status: AccountStatus,
        error: str | None = None,
    ) -> Account:
        account = await self.get(session, account_id)
        account.status = status
        account.last_error = error
        return account

    # ------------------------------------------------------------ validation
    @staticmethod
    def parse_amount(value: str) -> Decimal:
        try:
            amount = Decimal(value.strip().replace(",", ".").replace(" ", ""))
        except (InvalidOperation, AttributeError) as exc:
            raise ValueError(f"Not a valid amount: {value!r}") from exc
        if amount <= 0:
            raise ValueError("Amount must be greater than zero")
        return amount

    def validate_withdrawal_settings(self, account: Account) -> list[str]:
        """Return the list of problems that block a withdrawal."""
        problems: list[str] = []
        if not account.currency:
            problems.append("currency is not set")
        if not account.network:
            problems.append("network is not set")
        if not account.wallet_address:
            problems.append("wallet address is not set")
        if account.auto_withdraw_enabled and account.auto_withdraw_threshold is None:
            problems.append("auto withdrawal is on but no threshold is set")
        return problems


account_manager = AccountManager()
