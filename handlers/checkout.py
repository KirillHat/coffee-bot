"""Checkout flow: collects name, phone and address via FSM, then creates the order
and notifies the shop owner.
"""
from __future__ import annotations

import logging
import re
from html import escape

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import Config
from database import Database, OrderSummary
from keyboards.inline import cancel_kb, confirm_order_kb, main_menu_kb
from states.order import CheckoutStates
from utils.telegram import replace_or_edit

router = Router(name="checkout")
log = logging.getLogger(__name__)

PHONE_RE = re.compile(r"^[+]?[\d\s\-()]{7,20}$")


def _format_summary(order: OrderSummary, currency: str) -> str:
    lines = [
        f"🧾 <b>Order #{order.id}</b>",
        f"<b>Name:</b> {escape(order.full_name)}",
        f"<b>Phone:</b> {escape(order.phone)}",
        f"<b>Address:</b> {escape(order.address)}",
        "",
        "<b>Items:</b>",
    ]
    for item in order.items:
        lines.append(
            f"• {escape(item.name)} — {item.quantity} × {item.price:.2f} = "
            f"{item.subtotal:.2f} {escape(currency)}"
        )
    lines.append("")
    if order.discount_amount > 0:
        lines.append(f"Subtotal: {order.subtotal:.2f} {escape(currency)}")
        if order.promo_code:
            lines.append(
                f"Promo <code>{escape(order.promo_code)}</code>: "
                f"−{order.discount_amount:.2f} {escape(currency)}"
            )
    lines.append(f"<b>Total: {order.total:.2f} {escape(currency)}</b>")
    if order.payment_charge_id:
        lines.append(
            f"<i>💳 Paid via {escape(order.payment_provider or 'card')} "
            f"(charge {escape(order.payment_charge_id)})</i>"
        )
    return "\n".join(lines)


async def _render_review(
    message: Message,
    data: dict,
    db: Database,
    user_id: int,
    *,
    config: Config | None = None,
) -> None:
    items = await db.get_cart(user_id)
    if not items:
        await message.answer("Your cart is empty.", reply_markup=main_menu_kb())
        return
    subtotal = round(sum(i.subtotal for i in items), 2)
    discount = round(data.get("discount_amount", 0.0) or 0.0, 2)
    total = round(max(0.0, subtotal - discount), 2)
    promo_code = data.get("promo_code")

    text_lines = [
        "Please review your order:",
        "",
        f"<b>Name:</b> {escape(data['full_name'])}",
        f"<b>Phone:</b> {escape(data['phone'])}",
        f"<b>Address:</b> {escape(data['address'])}",
        "",
        "<b>Items:</b>",
    ]
    for item in items:
        text_lines.append(
            f"• {escape(item.name)} — {item.quantity} × ${item.price:.2f} = "
            f"<b>${item.subtotal:.2f}</b>"
        )
    text_lines.append("")
    text_lines.append(f"Subtotal: ${subtotal:.2f}")
    if promo_code and discount > 0:
        text_lines.append(
            f"Promo <code>{escape(promo_code)}</code>: −${discount:.2f}"
        )
    text_lines.append(f"<b>Total: ${total:.2f}</b>")
    text = "\n".join(text_lines)
    payments_enabled = bool(config and config.payments_enabled)
    await replace_or_edit(message, text, confirm_order_kb(payments_enabled=payments_enabled))


@router.callback_query(F.data == "checkout")
async def start_checkout(call: CallbackQuery, db: Database, state: FSMContext) -> None:
    items = await db.get_cart(call.from_user.id)
    if not items:
        await call.answer("Your cart is empty", show_alert=True)
        return
    await state.set_state(CheckoutStates.full_name)
    text = (
        "Let's place your order.\n\n"
        "<b>Step 1 of 3.</b> Please send me your full name."
    )
    await replace_or_edit(call.message, text, cancel_kb())
    await call.answer()


@router.message(CheckoutStates.full_name)
async def step_full_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if len(name) < 2 or len(name) > 80:
        await message.answer("Please send a valid name (2-80 characters).")
        return
    await state.update_data(full_name=name)
    await state.set_state(CheckoutStates.phone)
    await message.answer(
        "<b>Step 2 of 3.</b> Please send your phone number "
        "(international format preferred, e.g. +1 555 123 4567).",
        reply_markup=cancel_kb(),
    )


@router.message(CheckoutStates.phone)
async def step_phone(message: Message, state: FSMContext) -> None:
    phone = (message.text or "").strip()
    if not PHONE_RE.match(phone):
        await message.answer("That doesn't look like a valid phone number. Please try again.")
        return
    await state.update_data(phone=phone)
    await state.set_state(CheckoutStates.address)
    await message.answer(
        "<b>Step 3 of 3.</b> Please send the delivery address "
        "(street, city, postal code).",
        reply_markup=cancel_kb(),
    )


@router.message(CheckoutStates.address)
async def step_address(message: Message, state: FSMContext, db: Database) -> None:
    address = (message.text or "").strip()
    if len(address) < 5 or len(address) > 250:
        await message.answer("Please send a more detailed address (5-250 characters).")
        return
    await state.update_data(address=address)
    await state.set_state(CheckoutStates.promo)
    await message.answer(
        "<b>Promo code</b> (optional)\n\n"
        "Send a promo code to apply a discount, or send <code>skip</code> "
        "to continue without one.",
        reply_markup=cancel_kb(),
    )


@router.message(CheckoutStates.promo)
async def step_promo(
    message: Message, state: FSMContext, db: Database, config: Config
) -> None:
    raw = (message.text or "").strip()
    user_id = message.from_user.id

    if raw.lower() in {"skip", "/skip", "-", "no"}:
        await state.update_data(promo_code=None, discount_amount=0.0)
        await state.set_state(CheckoutStates.confirm)
        data = await state.get_data()
        await _render_review(message, data, db, user_id, config=config)
        return

    code = raw.upper()
    if len(code) > 32 or not code.replace("_", "").replace("-", "").isalnum():
        await message.answer(
            "That doesn't look like a promo code. Send a code or <code>skip</code>."
        )
        return

    promo = await db.get_promo_code(code)
    if promo is None:
        await message.answer(
            "❌ Promo code not found. Try another one or send <code>skip</code>."
        )
        return

    items = await db.get_cart(user_id)
    subtotal = sum(i.subtotal for i in items)
    from datetime import datetime, timezone
    ok, why = promo.can_apply(subtotal, now_iso=datetime.now(timezone.utc).isoformat())
    if not ok:
        await message.answer(f"❌ {why}\n\nSend another code or <code>skip</code>.")
        return

    discount = promo.discount_for(subtotal)
    await state.update_data(promo_code=promo.code, discount_amount=discount)
    await state.set_state(CheckoutStates.confirm)
    data = await state.get_data()
    await _render_review(message, data, db, user_id, config=config)


@router.callback_query(F.data == "order_cancel")
async def cancel_order(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    text = "Checkout cancelled. Your cart is still saved."
    await replace_or_edit(call.message, text, main_menu_kb())
    await call.answer()


@router.callback_query(F.data == "order_confirm")
async def confirm_order(
    call: CallbackQuery,
    state: FSMContext,
    db: Database,
    bot: Bot,
    config: Config,
) -> None:
    # Reject stale clicks (bot restart, FSM purge, double-tap after confirm).
    if await state.get_state() != CheckoutStates.confirm.state:
        await call.answer(
            "This checkout session has expired. Open your cart and try again.",
            show_alert=True,
        )
        await replace_or_edit(
            call.message,
            "⌛ This checkout session has expired. Your cart is still saved.",
            main_menu_kb(),
        )
        return

    data = await state.get_data()
    try:
        order = await db.create_order(
            user_id=call.from_user.id,
            username=call.from_user.username,
            full_name=data["full_name"],
            phone=data["phone"],
            address=data["address"],
            promo_code=data.get("promo_code"),
            discount_amount=data.get("discount_amount", 0.0) or 0.0,
        )
    except ValueError:
        await call.answer("Your cart is empty.", show_alert=True)
        await state.clear()
        return

    await state.clear()

    user_text = (
        "✅ <b>Order confirmed!</b>\n\n"
        f"Your order number is <b>#{order.id}</b>.\n"
        "We will contact you shortly to confirm delivery details.\n\n"
        "Thank you for choosing Roastline Coffee 🙌"
    )
    await replace_or_edit(call.message, user_text, main_menu_kb())
    await call.answer("Order placed!")

    # Notify the shop owner in their dedicated chat.
    if config.owner_chat_id:
        username_display = (
            f"@{escape(call.from_user.username)}" if call.from_user.username else "—"
        )
        owner_text = (
            "🆕 <b>New order received</b>\n\n"
            + _format_summary(order, config.currency)
            + f"\n\n<b>Customer:</b> {username_display} (id <code>{call.from_user.id}</code>)"
        )
        try:
            await bot.send_message(config.owner_chat_id, owner_text)
        except Exception as exc:
            log.warning("Could not notify owner chat %s: %s", config.owner_chat_id, exc)


def _format_user_orders(orders: list[OrderSummary]) -> str:
    if not orders:
        return "You don't have any orders yet."
    lines = ["📦 <b>Your recent orders</b>", ""]
    for o in orders:
        item_count = sum(item.quantity for item in o.items)
        items_label = "item" if item_count == 1 else "items"
        lines.append(
            f"#{o.id} · {escape(o.created_at)} · ${o.total:.2f} · "
            f"{item_count} {items_label} · <i>{escape(o.status)}</i>"
        )
    return "\n".join(lines)


@router.message(Command("orders"))
async def cmd_my_orders(message: Message, db: Database) -> None:
    orders = await db.list_user_orders(message.from_user.id, limit=10)
    await message.answer(_format_user_orders(orders))


@router.callback_query(F.data == "my_orders")
async def cb_my_orders(call: CallbackQuery, db: Database) -> None:
    orders = await db.list_user_orders(call.from_user.id, limit=10)
    text = _format_user_orders(orders)
    await replace_or_edit(call.message, text, main_menu_kb())
    await call.answer()
