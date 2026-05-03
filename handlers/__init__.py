"""Handler routers, registered on the main Dispatcher in bot.py."""
from aiogram import Router

from .admin import router as admin_router
from .cart import router as cart_router
from .catalog import router as catalog_router
from .checkout import router as checkout_router
from .inline_search import router as inline_search_router
from .order_admin import router as order_admin_router
from .payments import router as payments_router
from .start import router as start_router
from .webapp import router as webapp_router


def build_router() -> Router:
    root = Router(name="root")
    # Order matters: command-style routers first (they short-circuit specific
    # /commands), then catalog/cart/checkout for normal browsing, FSM-bearing
    # routers last so generic message handlers don't swallow FSM input.
    # Payments + WebApp routers go early so the F.successful_payment /
    # F.web_app_data filters win before catch-all message handlers.
    root.include_router(payments_router)
    root.include_router(webapp_router)
    root.include_router(start_router)
    root.include_router(admin_router)
    root.include_router(order_admin_router)
    root.include_router(inline_search_router)
    root.include_router(catalog_router)
    root.include_router(cart_router)
    root.include_router(checkout_router)
    return root
