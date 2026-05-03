# Screenshots

Pixel-perfect Telegram-styled mockups of every key screen the bot can show.
Use them as the cover and gallery images on the Upwork portfolio item, in
your README, in case-study slides, etc.

| #   | File                          | Screen                                                                |
| --- | ----------------------------- | --------------------------------------------------------------------- |
| 01  | `01_main_menu.png`            | Welcome message + main menu (Catalog / Cart / My orders / About / 🌐 Open Shop) |
| 02  | `02_catalog.png`              | Category list (8 categories ordered by intent, not alphabet)          |
| 03  | `03_product_detail.png`       | Product card with photo, description, price, Add-to-cart button       |
| 04  | `04_cart.png`                 | Cart screen with `−` / `+` / 🗑 quantity controls and grand total    |
| 05  | `05_checkout_promo.png`       | 4-step FSM checkout, last step prompts for an optional promo code     |
| 06  | `06_checkout_review.png`      | Order review with applied promo discount and 💳 / ✅ buttons          |
| 07  | `07_payment_invoice.png`      | Telegram Payments invoice (Smart Glocal/Stripe) with itemised lines   |
| 08  | `08_payment_success.png`      | Customer DMs after payment + auto status updates (confirmed → shipping) |
| 09  | `09_owner_notification.png`   | Owner DM on every new paid order, with full details + payment id      |
| 10  | `10_order_admin.png`          | Admin `/order <id>` view with inline status-change buttons            |
| 11  | `11_stats_dashboard.png`      | Admin `/stats` — revenue (today/7d/30d), AOV, status counts, top-5    |
| 12  | `12_inline_search.png`        | `@VelvetMorning_bot ethiopian` inline-mode dropdown                   |
| 13  | `13_webapp_home.png`          | WebApp (React+Tailwind) — home view with all 8 categories             |
| 14  | `14_webapp_cart.png`          | WebApp — cart with quantity controls and Telegram MainButton          |
| —   | `all_screens.png`             | Grid of all 14 screens on one canvas — handy hero image               |
| —   | `demo.gif`                    | Animated walkthrough of the user flow (10 frames, ~2.2 s each, 365 KB) |

## How they were made

`mockups.html` is a hand-coded Telegram-styled HTML rendering of every key
screen (uses Tailwind via CDN, no build). `_render.py` opens it with
Playwright and dumps each phone-frame element into its own PNG at 2×
resolution, plus a full-page grid overview.

If you want to update them after editing the bot:

```bash
python -m pip install playwright pillow
python -m playwright install chromium
python _render.py     # 14 still PNGs + grid overview
python _make_gif.py   # animated demo GIF
```

## Should I use real screenshots instead?

Both work for Upwork. The mockups are pixel-clean, version-controlled,
faster to update, and match the bot's actual texts and keyboards 1:1.

If you want real device captures for added credibility:

1. Run the bot (`python bot.py`) and use it from Telegram Desktop.
2. Capture each screen with macOS `Cmd+Shift+4` or the Telegram screenshot
   tool.
3. Replace the PNG with the same filename — `README.md` and the main project
   README reference them by name.

The mockups are great for documentation; real screenshots are slightly more
convincing for clients. You can also use both — mockups in the README,
real screenshots in your case-study slides or demo video.
