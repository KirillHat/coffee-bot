"""Admin commands that mutate order state, plus customer notifications.

Commands:
- /order <id>            — show order detail with status-change buttons
- /set_status <id> <st>  — change order status (also via inline buttons)
- /promo                 — list / add promo codes (FSM wizard)
"""
from __future__ import annotations

import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import Config
from database import (
    Database,
    ORDER_STATUSES,
    STATUS_LABELS,
    STATUS_TRANSITIONS,
    OrderSummary,
)
from states.order import AddPromoStates
from utils.parsing import safe_int

router = Router(name="order_admin")
log = logging.getLogger(__name__)


def _is_admin(user_id: int, config: Config) -> bool:
    return user_id in config.admin_ids


def _order_card(order: OrderSummary) -> str:
    lines = [
        f"🧾 <b>Order #{order.id}</b> — {STATUS_LABELS.get(order.status, order.status)}",
        f"<b>Created:</b> {escape(order.created_at)}",
        f"<b>Customer:</b> {escape(order.full_name)}",
        f"<b>Phone:</b> {escape(order.phone)}",
        f"<b>Address:</b> {escape(order.address)}",
        f"<b>User id:</b> <code>{order.user_id}</code>",
    ]
    if order.username:
        lines.append(f"<b>Username:</b> @{escape(order.username)}")
    lines.append("")
    lines.append("<b>Items:</b>")
    for item in order.items:
        lines.append(
            f"• {escape(item.name)} — {item.quantity} × ${item.price:.2f} "
            f"= ${item.subtotal:.2f}"
        )
    lines.append("")
    if order.discount_amount > 0:
        lines.append(f"Subtotal: ${order.subtotal:.2f}")
        if order.promo_code:
            lines.append(
                f"Promo <code>{escape(order.promo_code)}</code>: "
                f"−${order.discount_amount:.2f}"
            )
    lines.append(f"<b>Total: ${order.total:.2f}</b>")
    if order.payment_charge_id:
        lines.append(
            f"<i>💳 Paid via {escape(order.payment_provider or 'card')}</i>"
        )
    return "\n".join(lines)


def _status_kb(order: OrderSummary) -> InlineKeyboardMarkup:
    """Buttons for the next-allowed statuses."""
    builder = InlineKeyboardBuilder()
    allowed = STATUS_TRANSITIONS.get(order.status, frozenset())
    for status in ORDER_STATUSES:
        if status in allowed:
            builder.button(
                text=f"➡ {STATUS_LABELS.get(status, status)}",
                callback_data=f"ord_set:{order.id}:{status}",
            )
    builder.button(text="🔄 Refresh", callback_data=f"ord_show:{order.id}")
    builder.adjust(1)
    return builder.as_markup()


async def _notify_customer(bot: Bot, order: OrderSummary, new_status: str) -> None:
    """Send the customer a friendly status update."""
    nice = STATUS_LABELS.get(new_status, new_status)
    text = (
        f"📦 <b>Order #{order.id} update</b>\n\n"
        f"Status: {nice}\n"
        f"Total: ${order.total:.2f}"
    )
    if new_status == "confirmed":
        text += "\n\n✅ Thanks! Your order has been accepted and we're preparing it."
    elif new_status == "shipping":
        text += "\n\n🚚 Your order is on its way. Expect delivery in 1–3 business days."
    elif new_status == "delivered":
        text += "\n\n🎉 Delivered! We hope you enjoy your coffee. ☕"
    elif new_status == "cancelled":
        text += "\n\n❌ Your order has been cancelled. Contact support if this is a mistake."
    try:
        await bot.send_message(order.user_id, text)
    except TelegramAPIError as exc:
        log.warning("could not notify customer %s about order %s: %s",
                    order.user_id, order.id, exc)


# ---------------------------------------------------------------------------
# /order <id>
# ---------------------------------------------------------------------------

@router.message(Command("order"))
async def cmd_order(message: Message, command: CommandObject, db: Database, config: Config) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    arg = (command.args or "").strip()
    order_id = safe_int(arg)
    if order_id is None:
        await message.answer("Usage: <code>/order &lt;id&gt;</code>")
        return
    order = await db.get_order(order_id)
    if not order:
        await message.answer(f"Order #{order_id} not found.")
        return
    await message.answer(_order_card(order), reply_markup=_status_kb(order))


@router.callback_query(F.data.startswith("ord_show:"))
async def cb_order_show(call: CallbackQuery, db: Database, config: Config) -> None:
    if not _is_admin(call.from_user.id, config):
        await call.answer("Admins only", show_alert=True)
        return
    order_id = safe_int(call.data.split(":", 1)[1])
    if order_id is None:
        await call.answer("Invalid request", show_alert=True)
        return
    order = await db.get_order(order_id)
    if not order:
        await call.answer("Order not found", show_alert=True)
        return
    try:
        await call.message.edit_text(_order_card(order), reply_markup=_status_kb(order))
    except TelegramAPIError:
        await call.message.answer(_order_card(order), reply_markup=_status_kb(order))
    await call.answer()


@router.callback_query(F.data.startswith("ord_set:"))
async def cb_order_set_status(
    call: CallbackQuery, db: Database, config: Config, bot: Bot
) -> None:
    if not _is_admin(call.from_user.id, config):
        await call.answer("Admins only", show_alert=True)
        return
    parts = (call.data or "").split(":")
    if len(parts) != 3:
        await call.answer("Invalid request", show_alert=True)
        return
    order_id = safe_int(parts[1])
    new_status = parts[2]
    if order_id is None:
        await call.answer("Invalid order id", show_alert=True)
        return

    ok, err = await db.update_order_status(
        order_id, new_status, changed_by=call.from_user.id
    )
    if not ok:
        await call.answer(err or "Failed", show_alert=True)
        return

    order = await db.get_order(order_id)
    if order:
        await _notify_customer(bot, order, new_status)
        try:
            await call.message.edit_text(
                _order_card(order), reply_markup=_status_kb(order)
            )
        except TelegramAPIError:
            pass
    await call.answer(f"Status: {STATUS_LABELS.get(new_status, new_status)}")


@router.message(Command("set_status"))
async def cmd_set_status(
    message: Message, command: CommandObject, db: Database, config: Config, bot: Bot
) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    args = (command.args or "").strip().split()
    if len(args) != 2:
        await message.answer(
            "Usage: <code>/set_status &lt;order_id&gt; &lt;status&gt;</code>\n\n"
            f"Statuses: {', '.join(ORDER_STATUSES)}"
        )
        return
    order_id = safe_int(args[0])
    new_status = args[1].lower()
    if order_id is None:
        await message.answer("Invalid order id")
        return
    ok, err = await db.update_order_status(
        order_id, new_status, changed_by=message.from_user.id
    )
    if not ok:
        await message.answer(f"❌ {err}")
        return
    order = await db.get_order(order_id)
    if order:
        await _notify_customer(bot, order, new_status)
        await message.answer(
            f"✅ Order #{order_id} → {STATUS_LABELS.get(new_status, new_status)}",
            reply_markup=_status_kb(order),
        )


# ---------------------------------------------------------------------------
# /promo (list + simple add wizard)
# ---------------------------------------------------------------------------

@router.message(Command("promo"))
async def cmd_promo(
    message: Message, command: CommandObject, db: Database, config: Config, state: FSMContext
) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    arg = (command.args or "").strip().lower()
    if arg in {"add", "new"}:
        await state.set_state(AddPromoStates.code)
        await message.answer(
            "🎁 <b>New promo code</b>\n\n"
            "Step 1/4. Send the code (letters, digits, _ or -, up to 32 chars):"
        )
        return

    codes = await db.list_promo_codes()
    if not codes:
        await message.answer(
            "No promo codes yet. Create one with <code>/promo add</code>."
        )
        return
    lines = ["🎁 <b>Promo codes</b>", ""]
    for c in codes:
        used = f" · {c.used_count}/{c.max_uses}" if c.max_uses else f" · {c.used_count} uses"
        active = "✅" if c.active else "⏸"
        lines.append(
            f"{active} <code>{escape(c.code)}</code> · −{c.discount_pct}%"
            f"{used} · min ${c.min_subtotal:.2f}"
        )
    lines.append("")
    lines.append("Add: <code>/promo add</code>")
    await message.answer("\n".join(lines))


@router.message(AddPromoStates.code)
async def promo_step_code(message: Message, state: FSMContext) -> None:
    code = (message.text or "").strip().upper()
    if not (1 <= len(code) <= 32) or not code.replace("_", "").replace("-", "").isalnum():
        await message.answer("Invalid code. Use letters, digits, _ or - (max 32).")
        return
    await state.update_data(code=code)
    await state.set_state(AddPromoStates.discount)
    await message.answer("Step 2/4. Discount percent (1–100), e.g. <code>10</code>:")


@router.message(AddPromoStates.discount)
async def promo_step_discount(message: Message, state: FSMContext) -> None:
    pct = safe_int((message.text or "").strip())
    if pct is None or not 1 <= pct <= 100:
        await message.answer("Send an integer 1–100.")
        return
    await state.update_data(discount_pct=pct)
    await state.set_state(AddPromoStates.min_subtotal)
    await message.answer(
        "Step 3/4. Minimum cart subtotal in $ (or <code>0</code> for none):"
    )


@router.message(AddPromoStates.min_subtotal)
async def promo_step_min(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").replace(",", ".").strip()
    try:
        min_subtotal = max(0.0, float(raw))
    except ValueError:
        await message.answer("Send a number, e.g. <code>20</code>.")
        return
    await state.update_data(min_subtotal=min_subtotal)
    await state.set_state(AddPromoStates.max_uses)
    await message.answer(
        "Step 4/4. Max uses (positive integer, or <code>0</code> for unlimited):"
    )


@router.message(AddPromoStates.max_uses)
async def promo_step_max(
    message: Message, state: FSMContext, db: Database
) -> None:
    raw = (message.text or "").strip()
    try:
        max_uses_int = int(raw)
        if max_uses_int < 0:
            raise ValueError
    except ValueError:
        await message.answer("Send a non-negative integer.")
        return
    max_uses = max_uses_int if max_uses_int > 0 else None
    data = await state.get_data()
    await db.add_promo_code(
        data["code"],
        data["discount_pct"],
        min_subtotal=data["min_subtotal"],
        max_uses=max_uses,
    )
    await state.clear()
    await message.answer(
        f"✅ Promo <code>{escape(data['code'])}</code> created: "
        f"−{data['discount_pct']}%, min ${data['min_subtotal']:.2f}, "
        f"max uses: {max_uses if max_uses else 'unlimited'}."
    )
