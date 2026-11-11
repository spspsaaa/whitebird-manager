"""Authentication manager.

Two ways to get a session for an account:

1. Direct login with password + TOTP (works because every account has 2FA,
   so Whitebird never asks for a slider captcha).
2. Import a session obtained in an anti-detect browser profile - used when
   the password is unknown or the account needs a browser step.

Both end up in the same per-account token store, so all later calls are
plain authenticated HTTP requests.
"""
from __future__ import annotations

import logging
import time

from whitebird._client import AsyncWhitebird
from whitebird.tokens import FileTokenStore, Tokens

from app.config import get_settings
from app.wb.client import build_client, token_store_path

log = logging.getLogger(__name__)


class AuthError(RuntimeError):
    """Authentication failed."""


class AuthManager:
    def __init__(self) -> None:
        self._clients: dict[int, AsyncWhitebird] = {}

    # ------------------------------------------------------------- clients
    def client_for(
        self,
        account_id: int,
        login: str,
        password: str,
        totp_secret: str | None = None,
    ) -> AsyncWhitebird:
        client = self._clients.get(account_id)
        if client is None:
            client = build_client(login, password, totp_secret)
            self._clients[account_id] = client
        return client

    def drop(self, account_id: int) -> None:
        self._clients.pop(account_id, None)

    # -------------------------------------------------------------- tokens
    def token_store_path(self, login: str) -> str:
        return str(token_store_path(login))

    def has_session(self, login: str) -> bool:
        store = FileTokenStore(token_store_path(login))
        return store.load() is not None

    def store_session(self, login: str, access: str, refresh: str | None, expires_at: float | None) -> None:
        """Persist a session obtained elsewhere (e.g. from a browser)."""
        store = FileTokenStore(token_store_path(login))
        store.save(
            Tokens(access_token=access, refresh_token=refresh, expires_at=expires_at)
        )

    def clear_session(self, login: str) -> None:
        FileTokenStore(token_store_path(login)).clear()

    # ---------------------------------------------------------------- login
    async def login(
        self,
        account_id: int,
        login: str,
        password: str,
        totp_secret: str | None = None,
    ) -> AsyncWhitebird:
        """Log in and return an authenticated client."""
        client = self.client_for(account_id, login, password, totp_secret)
        try:
            await client.login()
        except Exception as exc:
            raise AuthError(f"Login failed: {exc}") from exc
        return client

    async def ensure_session(
        self,
        account_id: int,
        login: str,
        password: str,
        totp_secret: str | None = None,
    ) -> AsyncWhitebird:
        """Return a client with a live session, logging in if needed.

        The SDK refreshes the access token on its own while the refresh
        token is still valid, so a stored session survives restarts.
        """
        client = self.client_for(account_id, login, password, totp_secret)
        if not self.has_session(login):
            await self.login(account_id, login, password, totp_secret)
        return client

    async def session_expires_in(self, login: str) -> float | None:
        store = FileTokenStore(token_store_path(login))
        tokens = store.load()
        if tokens is None or tokens.expires_at is None:
            return None
        return tokens.expires_at - time.time()


auth_manager = AuthManager()
