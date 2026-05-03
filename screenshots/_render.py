"""Render mockups.html into individual PNG screenshots using Playwright.

Run once:
    python3 -m pip install playwright
    python3 -m playwright install chromium
    python3 _render.py

Outputs one PNG per screen plus an `all_screens.png` overview grid.
"""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "mockups.html"

# (DOM id, output filename, human title for README)
SCREENS = [
    ("screen-main-menu",       "01_main_menu.png",          "Main menu"),
    ("screen-catalog",         "02_catalog.png",            "Catalog (8 categories)"),
    ("screen-product",         "03_product_detail.png",     "Product detail card"),
    ("screen-cart",            "04_cart.png",               "Cart with quantity controls"),
    ("screen-promo",           "05_checkout_promo.png",     "Checkout — promo code step"),
    ("screen-checkout",        "06_checkout_review.png",    "Checkout review with discount"),
    ("screen-payment",         "07_payment_invoice.png",    "Telegram Payments invoice"),
    ("screen-payment-success", "08_payment_success.png",    "Payment success + status updates"),
    ("screen-owner",           "09_owner_notification.png", "Owner DM on new paid order"),
    ("screen-order-admin",     "10_order_admin.png",        "Admin /order with status buttons"),
    ("screen-stats",           "11_stats_dashboard.png",    "Admin /stats dashboard"),
    ("screen-inline-search",   "12_inline_search.png",      "Inline search across products"),
    ("screen-webapp-home",     "13_webapp_home.png",        "WebApp — home (8 categories)"),
    ("screen-webapp-cart",     "14_webapp_cart.png",        "WebApp — cart with checkout"),
]


def main() -> None:
    if not SOURCE.exists():
        raise SystemExit(f"missing {SOURCE}")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 900},
            device_scale_factor=2,  # retina-sharp
        )
        page = ctx.new_page()
        page.goto(SOURCE.as_uri(), wait_until="networkidle")

        for selector_id, filename, _ in SCREENS:
            element = page.locator(f"#{selector_id}")
            element.screenshot(path=str(HERE / filename))
            print(f"  ✓ {filename}")

        # Full-grid overview for the portfolio README hero image.
        page.set_viewport_size({"width": 1620, "height": 4200})
        page.screenshot(path=str(HERE / "all_screens.png"), full_page=True)
        print(f"  ✓ all_screens.png")

        browser.close()


if __name__ == "__main__":
    main()
