"""Records every user we see into the bot_users table.

Cheap touch on every event so /stats can report unique customers and we have
a customer list for future broadcast / GDPR-erase commands.
"""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from database import Database

log = logging.getLogger(__name__)


class UserTrackingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = getattr(event, "from_user", None)
        db: Database | None = data.get("db")
        if user and db:
            try:
                await db.upsert_user(user.id, user.username)
            except Exception as exc:  # noqa: BLE001 — never block handlers on tracking failure
                log.debug("upsert_user failed: %s", exc)
        return await handler(event, data)
