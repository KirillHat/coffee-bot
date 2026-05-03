"""Cart screen, add/remove/quantity controls."""
from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from database import CartItem, Database
from keyboards.inline import cart_kb, main_menu_kb
from utils.parsing import safe_int
from utils.telegram import replace_or_edit

router = Router(name="cart")

# Hard cap on per-product quantity to keep totals sane and prevent abuse.
MAX_QTY = 99


def _format_cart(items: list[CartItem]) -> str:
    if not items:
        return "🧺 <b>Your cart is empty</b>\n\nBrowse the catalog to add some coffee."
    lines = ["🧺 <b>Your cart</b>", ""]
    total = 0.0
    for item in items:
        lines.append(
            f"• {escape(item.name)}\n   {item.quantity} × ${item.price:.2f} = "
            f"<b>${item.subtotal:.2f}</b>"
        )
        total += item.subtotal
    lines.append("")
    lines.append(f"<b>Total: ${total:.2f}</b>")
    return "\n".join(lines)


async def _render_cart(message: Message, db: Database, user_id: int) -> None:
    items = await db.get_cart(user_id)
    text = _format_cart(items)
    keyboard = cart_kb(items) if items else main_menu_kb()
    await replace_or_edit(message, text, keyboard)


@router.message(Command("cart"))
async def cmd_cart(message: Message, db: Database) -> None:
    await _render_cart(message, db, message.from_user.id)


@router.callback_query(F.data == "cart")
async def cb_cart(call: CallbackQuery, db: Database) -> None:
    await _render_cart(call.message, db, call.from_user.id)
    await call.answer()


@router.callback_query(F.data.startswith("add:"))
async def cb_add(call: CallbackQuery, db: Database) -> None:
    parts = (call.data or "").split(":", 1)
    product_id = safe_int(parts[1] if len(parts) == 2 else None)
    if product_id is None:
        await call.answer("Invalid request", show_alert=True)
        return
    product = await db.get_product(product_id)
    if not product or not product.in_stock:
        await call.answer("This product is unavailable", show_alert=True)
        return

    added = await db.add_to_cart(
        call.from_user.id, product_id, qty=1, max_qty=MAX_QTY
    )
    if added:
        await call.answer(f"Added: {product.name}", show_alert=False)
    else:
        # Either the product disappeared between checks or the cart already
        # has MAX_QTY of it.
        await call.answer(
            f"Already at max ({MAX_QTY}) or unavailable", show_alert=True
        )


@router.callback_query(F.data.startswith("qty:"))
async def cb_qty(call: CallbackQuery, db: Database) -> None:
    parts = (call.data or "").split(":")
    if len(parts) != 3:
        await call.answer("Invalid request", show_alert=True)
        return
    _, product_id_str, action = parts
    product_id = safe_int(product_id_str)
    if product_id is None or action not in {"inc", "dec", "rm"}:
        await call.answer("Invalid request", show_alert=True)
        return
    user_id = call.from_user.id

    items = {item.product_id: item for item in await db.get_cart(user_id)}
    item = items.get(product_id)
    if not item and action != "rm":
        await call.answer("Item is no longer in your cart", show_alert=True)
        await _render_cart(call.message, db, user_id)
        return

    if action == "inc":
        if item.quantity >= MAX_QTY:
            await call.answer(f"Max {MAX_QTY} per item", show_alert=True)
            return
        await db.adjust_cart_quantity(user_id, product_id, delta=+1, max_qty=MAX_QTY)
        await call.answer("➕")
    elif action == "dec":
        await db.adjust_cart_quantity(user_id, product_id, delta=-1, max_qty=MAX_QTY)
        await call.answer("➖")
    elif action == "rm":
        await db.remove_from_cart(user_id, product_id)
        await call.answer("Removed", show_alert=False)

    await _render_cart(call.message, db, user_id)


@router.callback_query(F.data == "clear_cart")
async def cb_clear(call: CallbackQuery, db: Database) -> None:
    await db.clear_cart(call.from_user.id)
    await call.answer("Cart cleared")
    await _render_cart(call.message, db, call.from_user.id)
