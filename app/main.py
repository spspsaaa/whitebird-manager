"""Application entry point: bot + scheduler + health endpoint."""
from __future__ import annotations

import asyncio
import logging
import os
from contextlib import suppress

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.bot.access import OwnerOnlyMiddleware
from app.bot.handlers import router
from app.config import get_settings
from app.db import dispose_db, init_db, session_scope

log = logging.getLogger(__name__)

COMMANDS = [
    BotCommand(command="start", description="Главное меню"),
]


def setup_logging() -> None:
    logging.basicConfig(
        level=get_settings().log_level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


async def auto_withdrawal_job(bot: Bot) -> None:
    """Periodic check of the auto withdrawal thresholds."""
    from app.account_manager import account_manager
    from app.auto_withdrawal import AutoWithdrawalEngine
    from app.services import client_for_account
    from app.wb.withdrawal import withdrawal_manager

    engine = AutoWithdrawalEngine(account_manager, withdrawal_manager)
    async with session_scope() as session:
        accounts = await account_manager.list_all(session)
        events = await engine.check_all(
            session,
            lambda account: client_for_account(account),
        )

    for event in events:
        try:
            await bot.send_message(
                get_settings().owner_id,
                f"🤖 {event['message']}",
            )
        except Exception:  # pragma: no cover - notification must not break the job
            log.warning("Could not send the notification", exc_info=True)


async def health(request):
    from aiohttp import web

    return web.json_response({"status": "ok"})


async def run() -> None:
    setup_logging()
    settings = get_settings()
    settings.ensure_dirs()

    await init_db()
    log.info("Database ready")

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode="HTML"))
    dispatcher = Dispatcher(storage=MemoryStorage())
    # The owner check is enforced on the backend, before any handler runs.
    dispatcher.update.middleware(OwnerOnlyMiddleware())
    dispatcher.include_router(router)
    await bot.set_my_commands(COMMANDS)

    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        auto_withdrawal_job,
        "interval",
        seconds=settings.balance_poll_seconds,
        args=[bot],
        id="auto_withdrawal",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    log.info("Scheduler started (every %ss)", settings.balance_poll_seconds)

    # Health endpoint so Render can check the service.
    from aiohttp import web

    app = web.Application()
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", "8000")))
    await site.start()
    log.info("Health endpoint on :%s", os.getenv("PORT", "8000"))

    try:
        await dispatcher.start_polling(bot)
    finally:
        scheduler.shutdown(wait=False)
        with suppress(Exception):
            await bot.session.close()
        await dispose_db()


if __name__ == "__main__":
    asyncio.run(run())
