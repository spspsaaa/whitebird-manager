"""Bot handlers: menu, accounts, balances, withdrawals, auto, history."""
from __future__ import annotations

import logging
from decimal import Decimal

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from app.account_manager import account_manager
from app.bot.keyboards import (
    account_card,
    back_to_main,
    list_menu,
    main_menu,
    withdraw_picker,
)
from app.db import session_scope
from app.models import Operation, OperationStatus
from app.security import is_owner
from app.services import client_for_account
from app.wb.balance import balance_manager

log = logging.getLogger(__name__)
router = Router()

NL = "\n"


def _fmt(value) -> str:
    if value is None:
        return "-"
    if isinstance(value, Decimal):
        text = f"{value:f}".rstrip("0").rstrip(".")
        return text or "0"
    return str(value)


async def _accounts_list() -> list[tuple[int, str]]:
    async with session_scope() as session:
        accounts = await account_manager.list_all(session)
        return [(a.id, a.name) for a in accounts]


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    if not is_owner(message.from_user.id):
        return
    await message.answer(
        "Whitebird Manager" + NL + NL + "Управляю аккаунтами, балансами и выводами.",
        reply_markup=main_menu(),
    )


@router.callback_query(F.data == "menu:main")
async def cb_main(call: CallbackQuery) -> None:
    await call.message.edit_text("Главное меню", reply_markup=main_menu())
    await call.answer()


@router.callback_query(F.data == "accounts:list")
async def cb_accounts(call: CallbackQuery) -> None:
    accounts = await _accounts_list()
    if not accounts:
        await call.message.edit_text(
            "Аккаунтов пока нет. Добавь первый через \"\u2795 \u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u0430\u043a\u043a\u0430\u0443\u043d\u0442\u044c\".",
            reply_markup=back_to_main(),
        )
    else:
        await call.message.edit_text(
            "\u2704 \u0412\u0441\u0435 \u0430\u043a\u043a\u0430\u0443\u043d\u0442\u044b",
            reply_markup=list_menu("\u2704", accounts, ""),
        )
    await call.answer()


@router.callback_query(F.data.startswith("account:") and F.data.count(":") == 1)
async def cb_account_open(call: CallbackQuery) -> None:
    account_id = int(call.data.split(":")[1])
    async with session_scope() as session:
        account = await account_manager.get(session, account_id)
        text = NL.join(
            [
                f"<b>{account.name}</b>",
                "",
                f"Логин: {account.login}",
                f"Статус: {account.status.value}",
                f"Валюта: {_fmt(account.currency)} {account.network or ''}",
                f"Кошелек: {_fmt(account.wallet_address)}",
                f"Порог авто-вывода: {_fmt(account.auto_withdraw_threshold)}",
                f"Авто-вывод: {'включен' if account.auto_withdraw_enabled else 'выключен'}",
                f"Браузер: {_fmt(account.browser_provider)} / {_fmt(account.browser_profile_id)}",
            ]
        )
        await call.message.edit_text(
            text, reply_markup=account_card(account.id, account.auto_withdraw_enabled)
        )
    await call.answer()


@router.callback_query(F.data.startswith("account:") and F.data.endswith(":delete"))
async def cb_account_delete(call: CallbackQuery) -> None:
    account_id = int(call.data.split(":")[1])
    async with session_scope() as session:
        account = await account_manager.get(session, account_id)
        name = account.name
        await account_manager.delete(session, account_id)
    await call.message.edit_text(
        f"Аккаунт \"{name}\" удален.", reply_markup=back_to_main()
    )
    await call.answer()


@router.callback_query(F.data == "balances:all")
async def cb_balances_all(call: CallbackQuery) -> None:
    accounts = await _accounts_list()
    if not accounts:
        await call.message.edit_text("Аккаунтов пока нет.", reply_markup=back_to_main())
        await call.answer()
        return

    lines = ["Балансы" + NL]
    async with session_scope() as session:
        for account_id, name in accounts:
            account = await account_manager.get(session, account_id)
            try:
                client = await client_for_account(account)
                items = await balance_manager.balances(client)
                parts = [f"{_fmt(i.amount)} {i.currency}" for i in items if i.amount]
                lines.append(f"- {name}: {', '.join(parts) if parts else 'нет средств'}")
            except Exception as exc:
                lines.append(f"- {name}: ошибка - {exc}")
    await call.message.edit_text(NL.join(lines), reply_markup=back_to_main())
    await call.answer()


@router.callback_query(F.data.startswith("account:") and F.data.endswith(":balance"))
async def cb_account_balance(call: CallbackQuery) -> None:
    account_id = int(call.data.split(":")[1])
    async with session_scope() as session:
        account = await account_manager.get(session, account_id)
        try:
            client = await client_for_account(account)
            items = await balance_manager.balances(client)
            parts = NL.join(
                f"- {_fmt(i.amount)} {i.currency}"
                + (f" (${_fmt(i.usd_amount)})" if i.usd_amount else "")
                for i in items
            )
            await call.message.edit_text(
                f"Баланс: {account.name}" + NL + NL + (parts or "Нет средств"),
                reply_markup=account_card(account.id, account.auto_withdraw_enabled),
            )
        except Exception as exc:
            await call.message.edit_text(
                f"Не удалось получить баланс: {exc}",
                reply_markup=account_card(account.id, account.auto_withdraw_enabled),
            )
    await call.answer()


@router.callback_query(F.data == "withdraw:menu")
async def cb_withdraw_menu(call: CallbackQuery) -> None:
    accounts = await _accounts_list()
    if not accounts:
        await call.message.edit_text("Аккаунтов пока нет.", reply_markup=back_to_main())
    else:
        await call.message.edit_text(
            "Выбор аккаунта для вывода", reply_markup=withdraw_picker(accounts)
        )
    await call.answer()


@router.callback_query(F.data.startswith("withdraw:") and F.data.count(":") == 1)
async def cb_withdraw_start(call: CallbackQuery) -> None:
    account_id = int(call.data.split(":")[1])
    async with session_scope() as session:
        account = await account_manager.get(session, account_id)
        problems = account_manager.validate_withdrawal_settings(account)
        if problems:
            await call.message.edit_text(
                "Не хватает параметров для вывода:" + NL + NL.join(f"- {p}" for p in problems),
                reply_markup=account_card(account.id, account.auto_withdraw_enabled),
            )
            await call.answer()
            return

        try:
            client = await client_for_account(account)
            balance = await balance_manager.balance_of(client, account.currency or "")
        except Exception as exc:
            await call.message.edit_text(
                f"Не удалось получить баланс: {exc}",
                reply_markup=account_card(account.id, account.auto_withdraw_enabled),
            )
            await call.answer()
            return

        await call.message.edit_text(
            NL.join(
                [
                    "Вывод средств",
                    "",
                    f"Аккаунт: {account.name}",
                    f"Валюта: {account.currency} ({account.network})",
                    f"Кошелек: {account.wallet_address}",
                    f"Доступно: {_fmt(balance)} {account.currency}",
                ]
            ),
            reply_markup=back_to_main(),
        )
    await call.answer()


@router.callback_query(F.data == "auto:menu")
async def cb_auto_menu(call: CallbackQuery) -> None:
    accounts = await _accounts_list()
    if not accounts:
        await call.message.edit_text("Аккаунтов пока нет.", reply_markup=back_to_main())
    else:
        lines = ["Автоматический вывод" + NL]
        async with session_scope() as session:
            for account_id, name in accounts:
                account = await account_manager.get(session, account_id)
                state = "включен" if account.auto_withdraw_enabled else "выключен"
                lines.append(
                    f"- {name}: {state}, порог "
                    f"{_fmt(account.auto_withdraw_threshold)} {account.currency or ''}"
                )
        await call.message.edit_text(NL.join(lines), reply_markup=back_to_main())
    await call.answer()


@router.callback_query(F.data.startswith("auto:") and F.data.endswith(":toggle"))
async def cb_auto_toggle(call: CallbackQuery) -> None:
    account_id = int(call.data.split(":")[1])
    async with session_scope() as session:
        account = await account_manager.get(session, account_id)
        account.auto_withdraw_enabled = not account.auto_withdraw_enabled
        await call.message.edit_text(
            f"Авто-вывод для \"{account.name}\": "
            f"{'включен' if account.auto_withdraw_enabled else 'выключен'}",
            reply_markup=account_card(account.id, account.auto_withdraw_enabled),
        )
    await call.answer()


@router.callback_query(F.data == "history:list")
async def cb_history(call: CallbackQuery) -> None:
    from sqlalchemy import select

    async with session_scope() as session:
        result = await session.execute(
            select(Operation).order_by(Operation.created_at.desc()).limit(20)
        )
        operations = list(result.scalars().all())

    if not operations:
        await call.message.edit_text("История пуста.", reply_markup=back_to_main())
    else:
        icons = {
            OperationStatus.SUCCESS: "OK",
            OperationStatus.FAILED: "FAIL",
            OperationStatus.PENDING: "...",
            OperationStatus.NEEDS_CONFIRMATION: "?",
            OperationStatus.BLOCKED: "BLOCK",
        }
        lines = ["Последние операции" + NL]
        for op in operations:
            icon = icons.get(op.status, "-")
            lines.append(f"[{icon}] {op.created_at:%d.%m %H:%M} - {op.summary}")
        await call.message.edit_text(NL.join(lines), reply_markup=back_to_main())
    await call.answer()
