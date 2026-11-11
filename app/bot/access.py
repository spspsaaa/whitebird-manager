"""Owner-only access control for the bot.

The check lives on the backend: a message from anyone but the owner is
ignored completely - no reply, no data, no error.
"""
from __future__ import annotations

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from app.config import get_settings
from app.security import is_owner


class OwnerOnlyMiddleware(BaseMiddleware):
    """Silently drops every update that is not from the owner."""

    async def __call__(self, handler, event: TelegramObject, data: dict):
        user = data.get("event_from_user")
        if user is None or not is_owner(user.id):
            return None
        return await handler(event, data)
