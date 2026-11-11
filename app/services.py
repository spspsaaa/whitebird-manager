"""Service layer connecting the database, the account manager and the API."""
from __future__ import annotations

import logging

from app.account_manager import account_manager
from app.models import Account, AccountStatus
from app.wb.auth import auth_manager
from app.wb.balance import balance_manager
from app.wb.exceptions import AuthError

log = logging.getLogger(__name__)


async def client_for_account(account: Account):
    """Return an authenticated Whitebird client for the account.

    The session is stored per account, so accounts never share a session.
    """
    login, password, totp = account_manager.credentials(account)
    try:
        return await auth_manager.ensure_session(account.id, login, password, totp)
    except AuthError:
        account.status = AccountStatus.ERROR
        account.last_error = "Не удалось войти в аккаунт"
        raise


async def refresh_balance(account: Account) -> list:
    client = await client_for_account(account)
    return await balance_manager.balances(client)
