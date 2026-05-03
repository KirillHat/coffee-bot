"""WebApp data receiver.

The WebApp (webapp/index.html) calls ``Telegram.WebApp.sendData(json)`` when
the user taps "Send order". Telegram delivers it as a ``Message`` with a
``web_app_data`` field containing the raw string.

We parse it, refill the cart in our DB, and start the normal checkout FSM —
this keeps a single source of truth for order workflow.
"""
from __future__ import annotations

import json
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database import Database
from keyboards.inline import cancel_kb
from states.order import CheckoutStates

router = Router(name="webapp")
log = logging.getLogger(__name__)


@router.message(F.web_app_data)
async def on_webapp_data(message: Message, state: FSMContext, db: Database) -> None:
    raw = message.web_app_data.data
    try:
        payload = json.loads(raw)
        items = payload.get("items", [])
        if not isinstance(items, list) or not items:
            raise ValueError("empty items")
    except (ValueError, TypeError) as exc:
        log.warning("malformed webapp payload from %s: %s", message.from_user.id, exc)
        await message.answer(
            "I couldn't read the order from the WebApp. Please try again."
        )
        return

    user_id = message.from_user.id
    # Replace the cart with what the WebApp built — DB-side validation
    # (in_stock, max_qty) still applies via add_to_cart.
    await db.clear_cart(user_id)
    added = 0
    for item in items:
        try:
            product_id = int(item.get("id"))
            quantity = max(1, int(item.get("quantity", 1)))
        except (TypeError, ValueError):
            continue
        ok = await db.add_to_cart(user_id, product_id, qty=quantity)
        if ok:
            added += 1

    if added == 0:
        await message.answer(
            "Your WebApp cart contained items we can no longer offer. "
            "Please pick from the latest catalog."
        )
        return

    await state.set_state(CheckoutStates.full_name)
    await message.answer(
        f"✅ Cart synced from WebApp ({added} item(s)).\n\n"
        "<b>Step 1 of 3.</b> Please send me your full name to finish the order.",
        reply_markup=cancel_kb(),
    )
