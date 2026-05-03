"""Inline-mode search.

User types ``@VelvetMorning_bot ethiopian`` from any Telegram chat and gets
a dropdown of matching products. Picking one inserts a styled message into
the chat with a deep-link back to the bot.

Inline mode must be enabled at @BotFather → /mybots → Bot Settings → Inline Mode.
"""
from __future__ import annotations

import logging
from html import escape

from aiogram import F, Router
from aiogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
)

from database import Database

router = Router(name="inline_search")
log = logging.getLogger(__name__)

MAX_RESULTS = 20
CACHE_SECONDS = 30


@router.inline_query()
async def on_inline_query(query: InlineQuery, db: Database) -> None:
    text = (query.query or "").strip()

    bot_username = (await query.bot.get_me()).username

    if not text:
        # Empty query — show a hint result so users see something useful.
        hint = InlineQueryResultArticle(
            id="hint",
            title="Type a product name…",
            description="e.g. 'ethiopian', 'latte', 'chemex'",
            input_message_content=InputTextMessageContent(
                message_text=(
                    "🔍 Search Roastline Coffee inline by typing "
                    f"<code>@{bot_username} &lt;query&gt;</code>"
                ),
                parse_mode="HTML",
            ),
        )
        await query.answer([hint], cache_time=CACHE_SECONDS, is_personal=True)
        return

    products = await db.search_products(text, limit=MAX_RESULTS)

    if not products:
        no_match = InlineQueryResultArticle(
            id="empty",
            title="No products match",
            description=f"Nothing found for “{text}”",
            input_message_content=InputTextMessageContent(
                message_text=(
                    f"🔍 No Roastline Coffee products match “{escape(text)}”."
                ),
                parse_mode="HTML",
            ),
        )
        await query.answer([no_match], cache_time=CACHE_SECONDS, is_personal=True)
        return

    results = []
    for p in products:
        deep_link = f"https://t.me/{bot_username}?start=product_{p.id}"
        share_text = (
            f"☕ <b>{escape(p.name)}</b>\n"
            f"💵 ${p.price:.2f}\n\n"
            f"{escape(p.description[:200])}{'…' if len(p.description) > 200 else ''}\n\n"
            f"<a href=\"{deep_link}\">Open in Roastline Coffee bot →</a>"
        )
        results.append(
            InlineQueryResultArticle(
                id=f"p{p.id}",
                title=f"{p.name} — ${p.price:.2f}",
                description=(p.description[:80] + "…") if len(p.description) > 80 else p.description,
                input_message_content=InputTextMessageContent(
                    message_text=share_text,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                ),
                thumbnail_url=p.photo_url if p.photo_url and p.photo_url.startswith("http") else None,
            )
        )

    await query.answer(results, cache_time=CACHE_SECONDS, is_personal=True)
