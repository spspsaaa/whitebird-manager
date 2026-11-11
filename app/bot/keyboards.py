"""Inline keyboards of the bot."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📋 Все аккаунты", callback_data="accounts:list"),
                InlineKeyboardButton(text="💰 Балансы", callback_data="balances:all"),
            ],
            [
                InlineKeyboardButton(text="📤 Вывод средств", callback_data="withdraw:menu"),
                InlineKeyboardButton(text="⚡ Массовый вывод", callback_data="withdraw:mass"),
            ],
            [InlineKeyboardButton(text="🤖 Автоматический вывод", callback_data="auto:menu")],
            [
                InlineKeyboardButton(text="➕ Добавить аккаунт", callback_data="account:add"),
                InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings:menu"),
            ],
            [InlineKeyboardButton(text="📊 История операций", callback_data="history:list")],
        ]
    )


def list_menu(
    title_prefix: str,
    accounts: list[tuple[int, str]],
    empty_text: str,
) -> InlineKeyboardMarkup:
    """A list of accounts, each row opening its own action."""
    if not accounts:
        return back_to_main()
    rows = [
        [
            InlineKeyboardButton(
                text=f"{title_prefix} {name}", callback_data=f"account:{account_id}"
            )
        ]
        for account_id, name in accounts
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def account_card(account_id: int, auto_on: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💰 Баланс", callback_data=f"account:{account_id}:balance"),
                InlineKeyboardButton(text="📤 Вывести", callback_data=f"withdraw:{account_id}"),
            ],
            [
                InlineKeyboardButton(
                    text=("🤖 Авто-вывод: включён" if auto_on else "🤖 Авто-вывод: выключен"),
                    callback_data=f"auto:{account_id}:toggle",
                )
            ],
            [
                InlineKeyboardButton(text="⚙️ Параметры", callback_data=f"settings:{account_id}"),
                InlineKeyboardButton(text="📊 История", callback_data=f"history:{account_id}"),
            ],
            [
                InlineKeyboardButton(text="🗑 Удалить", callback_data=f"account:{account_id}:delete"),
                InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:main"),
            ],
        ]
    )


def withdraw_picker(accounts: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"📤 {name}", callback_data=f"withdraw:{account_id}"
            )
        ]
        for account_id, name in accounts
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_to_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:main")]]
    )
