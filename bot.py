"""Entry point for the Roastline Coffee shop bot.

Run:
    python bot.py

The bot reads BOT_TOKEN, ADMIN_IDS, OWNER_CHAT_ID and CURRENCY from .env
(see .env.example). On first start it creates an SQLite file and seeds it
with a demo catalogue.
"""
from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from database import Database
from handlers import build_router
from middlewares import RateLimitMiddleware, UserTrackingMiddleware
from utils.seed_data import seed_if_empty


async def on_startup(db: Database) -> None:
    await db.connect()
    inserted = await seed_if_empty(db)
    if inserted:
        logging.info(
            "Catalog ready: %d products (re-seeded from seed_data.py).", inserted
        )
    else:
        logging.info("Catalog is up to date — no re-seed needed.")


async def on_shutdown(db: Database) -> None:
    await db.close()


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)s — %(message)s",
        stream=sys.stdout,
    )
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    db = Database(config.db_path)
    await on_startup(db)

    # Inject shared dependencies into handlers.
    dp["db"] = db
    dp["config"] = config

    # Middlewares run for every update before handlers.
    rate_limiter = RateLimitMiddleware(admin_ids=set(config.admin_ids))
    user_tracker = UserTrackingMiddleware()
    for observer in (dp.message, dp.callback_query, dp.inline_query):
        observer.middleware(user_tracker)
        observer.middleware(rate_limiter)

    dp.include_router(build_router())

    try:
        logging.info("Bot is starting…")
        await bot.delete_webhook(drop_pending_updates=True)
        # Explicit allowed_updates so Telegram delivers inline_query,
        # pre_checkout_query and successful_payment alongside messages.
        # aiogram's auto-detect skips them when the routers are nested deep.
        await dp.start_polling(
            bot,
            allowed_updates=[
                "message",
                "edited_message",
                "callback_query",
                "inline_query",
                "pre_checkout_query",
                "shipping_query",
            ],
        )
    finally:
        await on_shutdown(db)
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped.")
