"""Per-user rate limiting middleware.

Drops events from a user that exceed a sliding-window quota and replies with a
friendly notice. Ignores admin user_ids (passed at construction time) so admin
operations never hit the wall.

The limiter is in-memory; on bot restart all counters reset, which is fine for
a small-shop bot. For production scale-out you'd swap the deques with a Redis
sorted-set.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, InlineQuery, Message, TelegramObject

log = logging.getLogger(__name__)


class RateLimitMiddleware(BaseMiddleware):
    """Sliding-window rate limiter.

    Defaults: 30 messages / minute and 60 callback clicks / minute per user.
    Configurable on init. Admins are exempt.
    """

    def __init__(
        self,
        *,
        admin_ids: set[int] | None = None,
        message_limit: int = 30,
        callback_limit: int = 60,
        window_seconds: float = 60.0,
        warn_cooldown_seconds: float = 30.0,
    ) -> None:
        self._admins = admin_ids or set()
        self._msg_limit = message_limit
        self._cb_limit = callback_limit
        self._window = window_seconds
        self._warn_cooldown = warn_cooldown_seconds
        self._buckets: dict[tuple[int, str], deque[float]] = defaultdict(deque)
        self._last_warning: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_id = self._extract_user_id(event)
        if user_id is None or user_id in self._admins:
            return await handler(event, data)

        kind, limit = self._classify(event)
        if kind is None:
            return await handler(event, data)

        if self._is_over_limit(user_id, kind, limit):
            log.info("rate-limited user=%s kind=%s", user_id, kind)
            await self._notify_throttled(event, user_id)
            return None

        return await handler(event, data)

    def _classify(self, event: TelegramObject) -> tuple[str | None, int]:
        if isinstance(event, Message):
            return "msg", self._msg_limit
        if isinstance(event, CallbackQuery):
            return "cb", self._cb_limit
        if isinstance(event, InlineQuery):
            return "inline", self._cb_limit
        return None, 0

    def _extract_user_id(self, event: TelegramObject) -> int | None:
        user = getattr(event, "from_user", None)
        return user.id if user else None

    def _is_over_limit(self, user_id: int, kind: str, limit: int) -> bool:
        now = time.monotonic()
        bucket = self._buckets[(user_id, kind)]
        # Evict timestamps that fell out of the sliding window.
        cutoff = now - self._window
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            return True
        bucket.append(now)
        return False

    async def _notify_throttled(self, event: TelegramObject, user_id: int) -> None:
        # Only one warning per cooldown window — otherwise the user gets a
        # warning toast for every blocked click and the chat gets spammy.
        now = time.monotonic()
        last = self._last_warning.get(user_id, 0)
        if now - last < self._warn_cooldown:
            return
        self._last_warning[user_id] = now
        try:
            if isinstance(event, CallbackQuery):
                await event.answer("Too many requests, please slow down.", show_alert=True)
            elif isinstance(event, Message):
                await event.answer("⚠️ You're sending messages too fast. Please wait a moment.")
            elif isinstance(event, InlineQuery):
                await event.answer(
                    [],
                    cache_time=10,
                    is_personal=True,
                    switch_pm_text="Slow down — try again in a minute",
                    switch_pm_parameter="rate_limited",
                )
        except Exception as exc:  # noqa: BLE001
            log.debug("could not deliver throttle notice: %s", exc)
