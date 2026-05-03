"""Inline keyboard builders.

We use compact callback_data strings (`cat:<id>`, `prod:<id>`, `add:<id>`, ...)
to keep payloads under Telegram's 64-byte limit.
"""
from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import CartItem, Category, Product


def main_menu_kb(*, webapp_url: str | None = None) -> InlineKeyboardMarkup:
    """Main menu. If ``webapp_url`` isn't passed, fall back to ``config.webapp_url``
    so callers don't need to plumb config through every layer."""
    if webapp_url is None:
        try:
            from config import config as _cfg
            webapp_url = _cfg.webapp_url or None
        except Exception:
            webapp_url = None

    builder = InlineKeyboardBuilder()
    builder.button(text="🛍 Catalog", callback_data="catalog")
    builder.button(text="🧺 Cart", callback_data="cart")
    builder.button(text="📦 My orders", callback_data="my_orders")
    builder.button(text="ℹ️ About", callback_data="about")
    if webapp_url:
        builder.button(text="🌐 Open Shop", web_app=WebAppInfo(url=webapp_url))
        builder.adjust(2, 2, 1)
    else:
        builder.adjust(2, 2)
    return builder.as_markup()


def categories_kb(categories: list[Category]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for cat in categories:
        label = f"{cat.emoji} {cat.name}".strip()
        builder.button(text=label, callback_data=f"cat:{cat.id}")
    builder.button(text="🧺 Cart", callback_data="cart")
    builder.button(text="🏠 Home", callback_data="home")
    builder.adjust(1)
    return builder.as_markup()


def products_kb(products: list[Product]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for product in products:
        builder.button(
            text=f"{product.name}  ·  ${product.price:.2f}",
            callback_data=f"prod:{product.id}",
        )
    builder.button(text="⬅️ Categories", callback_data="catalog")
    builder.button(text="🧺 Cart", callback_data="cart")
    builder.adjust(1)
    return builder.as_markup()


def product_kb(product: Product) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Add to cart", callback_data=f"add:{product.id}")
    builder.button(text="⬅️ Back", callback_data=f"cat:{product.category_id}")
    builder.button(text="🧺 Cart", callback_data="cart")
    builder.adjust(1, 2)
    return builder.as_markup()


def cart_kb(items: list[CartItem]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in items:
        builder.row(
            InlineKeyboardButton(text="➖", callback_data=f"qty:{item.product_id}:dec"),
            InlineKeyboardButton(
                text=f"{item.name[:24]} × {item.quantity}",
                callback_data=f"prod:{item.product_id}",
            ),
            InlineKeyboardButton(text="➕", callback_data=f"qty:{item.product_id}:inc"),
            InlineKeyboardButton(text="🗑", callback_data=f"qty:{item.product_id}:rm"),
        )
    if items:
        builder.row(InlineKeyboardButton(text="✅ Checkout", callback_data="checkout"))
        builder.row(InlineKeyboardButton(text="🧹 Clear cart", callback_data="clear_cart"))
    builder.row(
        InlineKeyboardButton(text="🛍 Catalog", callback_data="catalog"),
        InlineKeyboardButton(text="🏠 Home", callback_data="home"),
    )
    return builder.as_markup()


def confirm_order_kb(*, payments_enabled: bool = False) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if payments_enabled:
        builder.button(text="💳 Pay with card", callback_data="pay_card")
    builder.button(text="✅ Confirm (pay on delivery)", callback_data="order_confirm")
    builder.button(text="❌ Cancel", callback_data="order_cancel")
    builder.adjust(1)
    return builder.as_markup()


def cancel_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Cancel checkout", callback_data="order_cancel")
    return builder.as_markup()
