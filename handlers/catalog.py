"""Catalog browsing: categories → products → product detail with photo."""
from __future__ import annotations

import logging
from html import escape
from pathlib import Path

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest, TelegramNetworkError
from aiogram.filters import Command
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto, Message, URLInputFile

from database import Database, Product
from keyboards.inline import categories_kb, product_kb, products_kb
from utils.parsing import safe_int
from utils.telegram import replace_or_edit

router = Router(name="catalog")
log = logging.getLogger(__name__)

ASSETS_ROOT = Path(__file__).resolve().parent.parent


def _format_product(product: Product) -> str:
    return (
        f"<b>{escape(product.name)}</b>\n\n"
        f"{escape(product.description)}\n\n"
        f"💵 <b>${product.price:.2f}</b>"
    )


async def _show_categories(message: Message, db: Database) -> None:
    categories = await db.list_categories()
    if not categories:
        await message.answer("Catalog is being prepared. Please come back soon.")
        return
    text = "🛍 <b>Choose a category</b>"
    await replace_or_edit(message, text, categories_kb(categories))


@router.message(Command("catalog"))
async def cmd_catalog(message: Message, db: Database) -> None:
    await _show_categories(message, db)


@router.callback_query(F.data == "catalog")
async def cb_catalog(call: CallbackQuery, db: Database) -> None:
    await _show_categories(call.message, db)
    await call.answer()


@router.callback_query(F.data.startswith("cat:"))
async def cb_category(call: CallbackQuery, db: Database) -> None:
    category_id = safe_int(call.data.split(":", 1)[1] if ":" in (call.data or "") else None)
    if category_id is None:
        await call.answer("Invalid request", show_alert=True)
        return
    category = await db.get_category(category_id)
    if not category:
        await call.answer("Category not found", show_alert=True)
        return

    products = await db.list_products(category_id)
    if not products:
        await call.answer("No products in this category yet", show_alert=True)
        return

    header = (
        f"{escape(category.emoji)} <b>{escape(category.name)}</b>\n\nPick a product:"
    )
    await replace_or_edit(call.message, header, products_kb(products))
    await call.answer()


@router.callback_query(F.data.startswith("prod:"))
async def cb_product(call: CallbackQuery, db: Database) -> None:
    product_id = safe_int(call.data.split(":", 1)[1] if ":" in (call.data or "") else None)
    if product_id is None:
        await call.answer("Invalid request", show_alert=True)
        return
    product = await db.get_product(product_id)
    if not product:
        await call.answer("Product not found", show_alert=True)
        return

    caption = _format_product(product)
    keyboard = product_kb(product)

    if await _try_show_with_photo(call.message, product, caption, keyboard):
        await call.answer()
        return

    # Photo missing, broken or rejected by Telegram → text-only card.
    await replace_or_edit(call.message, caption, keyboard)
    await call.answer()


async def _try_show_with_photo(
    message: Message,
    product: Product,
    caption: str,
    keyboard,
) -> bool:
    """Attempt to render the product card with its photo.

    Returns ``True`` when the photo was shown successfully, ``False`` otherwise
    (so the caller can fall back to a text-only card). Any IO/Telegram error is
    swallowed and logged — a missing or corrupted photo must never take the bot
    down.
    """
    photo = _resolve_photo(product)
    if photo is None:
        return False

    try:
        # Swap media in place when we're already showing a photo card.
        if message.photo:
            try:
                await message.edit_media(
                    media=InputMediaPhoto(media=photo, caption=caption),
                    reply_markup=keyboard,
                )
                return True
            except TelegramBadRequest:
                pass  # fall through to delete+resend
        try:
            await message.delete()
        except TelegramBadRequest:
            pass
        await message.answer_photo(
            photo=photo, caption=caption, reply_markup=keyboard
        )
        return True
    except (TelegramNetworkError, TelegramAPIError, FileNotFoundError, OSError) as exc:
        log.warning(
            "Failed to send photo for product %s (%s): %s",
            product.id,
            product.photo_url,
            exc,
        )
        return False


def _resolve_photo(product: Product) -> URLInputFile | FSInputFile | None:
    """Build an InputFile for the product photo or return None if unavailable.

    Errors here (missing file, unicode-normalisation mismatches between the
    DB-stored path and the on-disk path, permission errors, etc.) are non-fatal
    — the caller falls back to a text-only card.
    """
    if not product.photo_url:
        return None
    if product.photo_url.startswith(("http://", "https://")):
        return URLInputFile(product.photo_url)
    try:
        local_path = ASSETS_ROOT / product.photo_url
        if not local_path.is_file():
            log.warning(
                "Photo file missing for product %s: %s", product.id, local_path
            )
            return None
        return FSInputFile(str(local_path))
    except OSError as exc:  # pragma: no cover — pathological filesystem state
        log.warning(
            "Cannot resolve photo for product %s (%s): %s",
            product.id,
            product.photo_url,
            exc,
        )
        return None
