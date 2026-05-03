"""Admin commands: add products, list categories, view recent orders.

Access is gated by the ADMIN_IDS list in .env. Non-admins get a polite refusal.
"""
from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config import Config
from database import Database
from states.order import AddProductStates

router = Router(name="admin")


def _is_admin(user_id: int, config: Config) -> bool:
    return user_id in config.admin_ids


@router.message(Command("admin"))
async def cmd_admin(message: Message, config: Config) -> None:
    if not _is_admin(message.from_user.id, config):
        await message.answer("This command is only available to administrators.")
        return
    await message.answer(
        "<b>Admin panel</b>\n\n"
        "<b>Catalog</b>\n"
        "/categories — list categories\n"
        "/add_product — add a new product\n"
        "\n<b>Orders</b>\n"
        "/orders_all — last 20 orders\n"
        "/order &lt;id&gt; — order detail with status buttons\n"
        "/set_status &lt;id&gt; &lt;status&gt; — change order status\n"
        "\n<b>Marketing</b>\n"
        "/promo — list promo codes\n"
        "/promo add — create a new promo code\n"
        "\n<b>Insights</b>\n"
        "/stats — sales overview (revenue, top products, status breakdown)\n"
        "\n/cancel — abort the current admin action"
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message, db: Database, config: Config) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    s = await db.stats_summary()

    lines = ["📊 <b>Sales overview</b>", ""]
    lines.append(f"💰 <b>Total revenue:</b> ${s['revenue_total']:,.2f}")
    lines.append(f"   Today: ${s['revenue_today']:,.2f}")
    lines.append(f"   7 days: ${s['revenue_week']:,.2f}")
    lines.append(f"   30 days: ${s['revenue_month']:,.2f}")
    lines.append("")
    lines.append(f"🧾 <b>Orders:</b> {s['order_count']} ({s['paid_count']} paid via card)")
    lines.append(f"💵 <b>Avg order value:</b> ${s['avg_order']:,.2f}")
    lines.append(f"👥 <b>Unique customers:</b> {s['unique_customers']}")

    if s["status_counts"]:
        lines.append("")
        lines.append("<b>Status breakdown:</b>")
        from database import STATUS_LABELS
        for st, count in sorted(s["status_counts"].items()):
            label = STATUS_LABELS.get(st, st)
            lines.append(f"  {label}: {count}")

    if s["top_products"]:
        lines.append("")
        lines.append("🏆 <b>Top 5 products (units sold):</b>")
        from html import escape as _esc
        for i, p in enumerate(s["top_products"], 1):
            lines.append(
                f"  {i}. {_esc(p['name'])} — "
                f"{p['units']} units · ${p['revenue']:,.2f}"
            )

    await message.answer("\n".join(lines))


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext, config: Config) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    if await state.get_state() is None:
        await message.answer("Nothing to cancel.")
        return
    await state.clear()
    await message.answer("Cancelled.")


@router.message(Command("categories"))
async def cmd_categories(message: Message, db: Database, config: Config) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    cats = await db.list_categories()
    if not cats:
        await message.answer("No categories yet.")
        return
    lines = ["<b>Categories</b>"]
    for cat in cats:
        lines.append(f"• <code>{cat.id}</code> — {escape(cat.emoji)} {escape(cat.name)}")
    await message.answer("\n".join(lines))


@router.message(Command("orders_all"))
async def cmd_orders_all(message: Message, db: Database, config: Config) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    orders = await db.list_orders(limit=20)
    if not orders:
        await message.answer("No orders yet.")
        return
    lines = ["📦 <b>Last orders</b>", ""]
    for order in orders:
        username = f"@{escape(order.username)}" if order.username else "—"
        lines.append(
            f"#{order.id} · {escape(order.created_at)} · {username}\n"
            f"   {escape(order.full_name)} · {escape(order.phone)}\n"
            f"   ${order.total:.2f} · <i>{escape(order.status)}</i>"
        )
    await message.answer("\n\n".join(lines))


# ---- Add product wizard --------------------------------------------------


@router.message(Command("add_product"))
async def add_product_start(
    message: Message, state: FSMContext, db: Database, config: Config
) -> None:
    if not _is_admin(message.from_user.id, config):
        return
    cats = await db.list_categories()
    if not cats:
        await message.answer("Please create a category first (none exist).")
        return
    await state.set_state(AddProductStates.category)
    lines = ["Send the <b>category id</b> for the new product:"]
    for cat in cats:
        lines.append(f"<code>{cat.id}</code> — {escape(cat.emoji)} {escape(cat.name)}")
    await message.answer("\n".join(lines))


@router.message(AddProductStates.category, F.text.regexp(r"^\d+$"))
async def add_product_category(message: Message, state: FSMContext, db: Database) -> None:
    category = await db.get_category(int(message.text))
    if not category:
        await message.answer("No such category. Try again or /cancel.")
        return
    await state.update_data(category_id=category.id)
    await state.set_state(AddProductStates.name)
    await message.answer(
        f"Category: {escape(category.name)}\n\nSend the <b>product name</b>:"
    )


@router.message(AddProductStates.category)
async def add_product_category_invalid(message: Message) -> None:
    await message.answer("Please send a numeric category id, or /cancel.")


@router.message(AddProductStates.name)
async def add_product_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if not (2 <= len(name) <= 100):
        await message.answer("Name must be 2-100 characters.")
        return
    await state.update_data(name=name)
    await state.set_state(AddProductStates.description)
    await message.answer("Send the <b>description</b>:")


@router.message(AddProductStates.description)
async def add_product_description(message: Message, state: FSMContext) -> None:
    description = (message.text or "").strip()
    if not (5 <= len(description) <= 800):
        await message.answer("Description must be 5-800 characters.")
        return
    await state.update_data(description=description)
    await state.set_state(AddProductStates.price)
    await message.answer("Send the <b>price</b> (e.g. <code>18.50</code>):")


@router.message(AddProductStates.price)
async def add_product_price(message: Message, state: FSMContext) -> None:
    try:
        price = float((message.text or "").replace(",", ".").strip())
        if price < 0:
            raise ValueError
    except ValueError:
        await message.answer("Please send a non-negative number, e.g. 18.50")
        return
    await state.update_data(price=price)
    await state.set_state(AddProductStates.photo_url)
    await message.answer(
        "Send a <b>photo URL</b> (https://...) or type <code>skip</code> to omit:"
    )


@router.message(AddProductStates.photo_url)
async def add_product_photo(
    message: Message, state: FSMContext, db: Database
) -> None:
    raw = (message.text or "").strip()
    photo_url: str | None
    if raw.lower() == "skip":
        photo_url = None
    elif raw.startswith(("http://", "https://")):
        photo_url = raw
    else:
        await message.answer("Please send a valid URL or 'skip'.")
        return

    data = await state.get_data()
    product_id = await db.add_product(
        category_id=data["category_id"],
        name=data["name"],
        description=data["description"],
        price=data["price"],
        photo_url=photo_url,
    )
    await state.clear()
    await message.answer(
        f"✅ Added product <b>#{product_id}</b> — {escape(data['name'])} "
        f"for ${data['price']:.2f}."
    )
