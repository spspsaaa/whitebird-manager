"""Whitebird client factory.

Every account gets its own AsyncWhitebird instance and its own token-store
file, so sessions and settings never overlap between accounts.
"""
from __future__ import annotations

import logging
from pathlib import Path

from whitebird._client import AsyncWhitebird
from whitebird.otp import TOTP
from whitebird.tokens import FileTokenStore

from app.config import get_settings

log = logging.getLogger(__name__)


def token_store_path(login: str) -> Path:
    """Per-account token store path (session isolation)."""
    settings = get_settings()
    settings.ensure_dirs()
    safe = "".join(c for c in login.lower() if c.isalnum() or c in "._-")
    return settings.token_dir / f"{safe}.token"


def build_client(
    login: str,
    password: str,
    totp_secret: str | None = None,
) -> AsyncWhitebird:
    """Create an isolated async client for one Whitebird account.

    The TOTP provider is passed as a plain callable, which the SDK accepts
    for both the sync and async code providers.
    """
    otp = TOTP(totp_secret) if totp_secret else None
    return AsyncWhitebird(
        login,
        password,
        otp=otp,
        token_store=FileTokenStore(token_store_path(login)),
        max_retries=2,
    )
