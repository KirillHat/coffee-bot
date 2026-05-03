"""/start, /help, the main menu, About screen, and deep-links."""
from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import CallbackQuery, Message

from database import Database
from keyboards.inline import main_menu_kb, product_kb
from utils.parsing import safe_int
from utils.telegram import replace_or_edit

router = Router(name="start")


WELCOME_TEXT = (
    "👋 <b>Welcome to Roastline Coffee</b>\n\n"
    "We deliver freshly roasted specialty coffee right to your door.\n\n"
    "• 🛍 Browse the catalog\n"
    "• 🧺 Add items to your cart\n"
    "• ✅ Place an order in under a minute\n\n"
    "Tap a button below to get started."
)

ABOUT_TEXT = (
    "ℹ️ <b>About Roastline Coffee</b>\n\n"
    "We are a small-batch roaster sourcing direct-trade green beans from "
    "farms in Ethiopia, Colombia, Kenya and Brazil.\n\n"
    "All beans are roasted to order and shipped within 24 hours.\n\n"
    "Need help? Email <code>hello@roastline.example</code>."
)


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, db: Database) -> None:
    """Show the main menu, or jump straight to a product if the user came in
    via a `?start=product_N` deep link from inline search."""
    arg = (command.args or "").strip()
    if arg.startswith("product_"):
        product_id = safe_int(arg[len("product_"):])
        if product_id is not None:
            product = await db.get_product(product_id)
            if product:
                from html import escape
                caption = (
                    f"<b>{escape(product.name)}</b>\n\n"
                    f"{escape(product.description)}\n\n"
                    f"💵 <b>${product.price:.2f}</b>"
                )
                await message.answer(caption, reply_markup=product_kb(product))
                return
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_kb())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    text = (
        "<b>Available commands</b>\n"
        "/start — main menu\n"
        "/catalog — browse products\n"
        "/cart — view your cart\n"
        "/orders — your past orders\n"
        "/help — this message"
    )
    await message.answer(text)


@router.callback_query(F.data == "home")
async def cb_home(call: CallbackQuery) -> None:
    await replace_or_edit(call.message, WELCOME_TEXT, main_menu_kb())
    await call.answer()


@router.callback_query(F.data == "about")
async def cb_about(call: CallbackQuery) -> None:
    await replace_or_edit(call.message, ABOUT_TEXT, main_menu_kb())
    await call.answer()
