"""Small Telegram helper utilities.

Centralises the edit-or-replace pattern: when a callback arrives we want to
mutate the existing message in place, but we have to fall back to deleting it
and sending a fresh one if the previous message was a photo card or its content
hasn't changed.
"""
from __future__ import annotations

from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, Message


async def replace_or_edit(
    message: Message,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """Show ``text`` in place of ``message``.

    Strategy:
    1. If ``message`` is a photo card → delete + send new (``edit_text`` cannot
       turn a photo message into text).
    2. Otherwise try ``edit_text``; if Telegram refuses (e.g. content unchanged
       or message too old) fall back to delete + send.

    The keyboard always reflects the new state, so a user clicking the same
    "Home" button twice never sees a stale message or a hanging click.
    """
    if message.photo:
        try:
            await message.delete()
        except TelegramBadRequest:
            pass
        await message.answer(text, reply_markup=reply_markup)
        return

    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest:
        try:
            await message.delete()
        except TelegramBadRequest:
            pass
        await message.answer(text, reply_markup=reply_markup)
