"""Security helpers: secret encryption and owner-only access control."""
from __future__ import annotations

import logging
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings

log = logging.getLogger(__name__)


class Vault:
    """Encrypts/decrypts account credentials at rest with a Fernet key."""

    def __init__(self, key: str | None = None) -> None:
        raw = key or get_settings().encryption_key
        self._fernet = Fernet(raw.encode() if isinstance(raw, str) else raw)

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken as exc:
            raise ValueError("Cannot decrypt stored secret (wrong ENCRYPTION_KEY?)") from exc

    def encrypt_fields(self, **fields: str | None) -> dict[str, str]:
        return {k: self.encrypt(v) for k, v in fields.items() if v}

    def decrypt_fields(self, **fields: str | None) -> dict[str, str]:
        return {k: self.decrypt(v) for k, v in fields.items() if v}


def is_owner(user_id: int | None, settings: Any | None = None) -> bool:
    """Backend-side owner check. Every command must pass through this."""
    if user_id is None:
        return False
    s = settings or get_settings()
    return int(user_id) == int(s.owner_id)


def is_admin(user_id: int | None, settings: Any | None = None) -> bool:
    if user_id is None:
        return False
    s = settings or get_settings()
    if int(user_id) == int(s.owner_id):
        return True
    return s.admin_id is not None and int(user_id) == int(s.admin_id)
