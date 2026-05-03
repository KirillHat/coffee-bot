"""Telegram Payments — Stripe (Test) integration.

Flow:
1. User taps 💳 "Pay with card" on the cart-review screen.
2. Bot sends an Invoice via :code:`bot.send_invoice` with cart items as
   :code:`LabeledPrice`s and the discount as a negative line.
3. Telegram pops up a native payment sheet on the user's device.
4. Just before charging, Telegram sends a :code:`pre_checkout_query` — we
   re-validate the cart hasn't changed and ack within 10s.
5. On success, :code:`successful_payment` arrives — we create the order,
   notify the owner, and confirm to the customer.

Test cards (Stripe Test):
    4242 4242 4242 4242 | any future date | any CVC

Provider token comes from @BotFather → /mybots → bot → Payments → Stripe TEST.
"""
from __future__ import annotations

import json
import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
    SuccessfulPayment,
)

from config import Config
from database import Database
from keyboards.inline import main_menu_kb
from states.order import CheckoutStates
from utils.telegram import replace_or_edit

router = Router(name="payments")
log = logging.getLogger(__name__)

# Telegram Payments expects amounts in the smallest currency unit (cents, kopeks…).
SUBUNITS_PER_UNIT = 100


def _to_subunits(amount: float) -> int:
    """USD 4.20 → 420. Always round-half-up."""
    return int(round(amount * SUBUNITS_PER_UNIT))


@router.callback_query(F.data == "pay_card", CheckoutStates.confirm)
async def cb_pay_card(
    call: CallbackQuery, state: FSMContext, db: Database, bot: Bot, config: Config
) -> None:
    if not config.payments_enabled:
        await call.answer("Card payments are not configured for this bot.", show_alert=True)
        return

    data = await state.get_data()
    user_id = call.from_user.id
    items = await db.get_cart(user_id)
    if not items:
        await call.answer("Your cart is empty.", show_alert=True)
        await state.clear()
        return

    discount = round(data.get("discount_amount", 0.0) or 0.0, 2)
    promo_code = data.get("promo_code")

    # Build LabeledPrice list — one line per cart item, plus a negative
    # discount line if a promo applies.
    prices: list[LabeledPrice] = [
        LabeledPrice(
            label=f"{item.name} × {item.quantity}",
            amount=_to_subunits(item.subtotal),
        )
        for item in items
    ]
    if discount > 0:
        prices.append(
            LabeledPrice(
                label=f"Promo {promo_code} discount",
                amount=-_to_subunits(discount),
            )
        )

    # We need this metadata back when the payment succeeds — Telegram will
    # echo our `payload` verbatim in the SuccessfulPayment update.
    payload = json.dumps({
        "user_id": user_id,
        "promo_code": promo_code,
        "discount_amount": discount,
        "full_name": data.get("full_name"),
        "phone": data.get("phone"),
        "address": data.get("address"),
    })

    try:
        await bot.send_invoice(
            chat_id=user_id,
            title="Roastline Coffee order",
            description=(
                f"{len(items)} item(s) — see breakdown below. "
                "After payment, your order is created automatically."
            ),
            payload=payload,
            provider_token=config.payment_provider_token,
            currency=config.currency,
            prices=prices,
            need_name=False,
            need_phone_number=False,
            need_email=False,
            need_shipping_address=False,
            is_flexible=False,
            send_phone_number_to_provider=False,
            start_parameter="checkout",
        )
        await call.answer("Opening payment sheet…")
    except TelegramAPIError as exc:
        log.warning("send_invoice failed for user %s: %s", user_id, exc)
        await call.answer(
            "Couldn't open the payment sheet. Try again or pay on delivery.",
            show_alert=True,
        )


@router.pre_checkout_query()
async def on_pre_checkout(query: PreCheckoutQuery, db: Database) -> None:
    """Telegram asks 'is this still ok?' just before charging the card.

    We MUST answer within 10 seconds. Validate the cart still has items
    and the user is still us — if the cart was emptied since the invoice
    was sent, refuse cleanly.
    """
    try:
        payload = json.loads(query.invoice_payload)
        cart_user_id = int(payload["user_id"])
    except (ValueError, KeyError, TypeError):
        await query.answer(ok=False, error_message="Invalid payment session.")
        return

    if query.from_user.id != cart_user_id:
        await query.answer(ok=False, error_message="Payment session belongs to another user.")
        return

    items = await db.get_cart(cart_user_id)
    if not items:
        await query.answer(
            ok=False,
            error_message="Your cart is empty. Please add items and try again.",
        )
        return

    await query.answer(ok=True)


@router.message(F.successful_payment)
async def on_successful_payment(
    message: Message, db: Database, bot: Bot, config: Config, state: FSMContext
) -> None:
    """Charge succeeded → create the order, clear the cart, notify everyone."""
    payment: SuccessfulPayment = message.successful_payment
    try:
        payload = json.loads(payment.invoice_payload)
    except (ValueError, TypeError):
        log.error("malformed payment payload from user %s", message.from_user.id)
        await message.answer(
            "Payment received, but the order data is malformed — please contact support."
        )
        return

    user_id = message.from_user.id
    try:
        order = await db.create_order(
            user_id=user_id,
            username=message.from_user.username,
            full_name=payload.get("full_name") or message.from_user.full_name or "—",
            phone=payload.get("phone") or "—",
            address=payload.get("address") or "—",
            promo_code=payload.get("promo_code"),
            discount_amount=float(payload.get("discount_amount") or 0.0),
            payment_charge_id=payment.provider_payment_charge_id,
            payment_provider="telegram_payments",
        )
    except ValueError:
        await message.answer(
            "Cart was empty at confirm time — payment was processed but no order created. "
            "Please contact support."
        )
        return

    # Auto-confirm paid orders — there's no doubt about willingness to buy.
    await db.update_order_status(
        order.id, "confirmed", changed_by=user_id, note="Auto-confirmed via card payment", force=True
    )
    await state.clear()

    user_text = (
        f"💳 <b>Payment received — thank you!</b>\n\n"
        f"Order: <b>#{order.id}</b>\n"
        f"Charged: <b>${order.total:.2f} {escape(config.currency)}</b>\n\n"
        f"We'll start preparing your order right away. ☕"
    )
    await message.answer(user_text, reply_markup=main_menu_kb())

    # Notify owner.
    if config.owner_chat_id:
        from .checkout import _format_summary  # local import — avoid cycles
        owner_text = (
            f"💳 <b>NEW PAID ORDER</b>\n\n{_format_summary(order, config.currency)}"
        )
        try:
            await bot.send_message(config.owner_chat_id, owner_text)
        except TelegramAPIError as exc:
            log.warning("owner notify failed: %s", exc)
