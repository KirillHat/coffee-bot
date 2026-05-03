# Changelog

All notable changes to this project. The project follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html) loosely.

## [1.0.0] — 2026-05-02

First publicly-shippable release. Goes from "demo bot" to "production-grade
e-commerce platform with payments, mini-app and admin tooling".

### Added — payments & ordering
- 💳 **Telegram Payments** integration (Smart Glocal / Stripe / YooKassa).
  Customers tap "Pay with card" on the checkout review, see the native
  Telegram payment sheet, and on success the order is created and
  force-confirmed automatically. Owner gets a "NEW PAID ORDER" DM.
- 🎁 **Promo codes** with discount percent, optional minimum subtotal,
  optional max-uses cap, and an admin wizard (`/promo add`).
- 📦 **Order status workflow** (`new → confirmed → shipping → delivered`
  + `cancelled`). Admin sets status via inline buttons in `/order <id>` or
  via `/set_status <id> <status>`. Customer is auto-DMed with a friendly
  status message tailored to each transition.
- 🧾 Schema-level history (`order_status_history`), payment id stored
  (`payment_charge_id`, `payment_provider`), discount captured (`subtotal`,
  `discount_amount`, `promo_code`).

### Added — discovery & admin
- 🔍 **Inline search** — `@VelvetMorning_bot ethiopian` from any chat shows
  matching products in a dropdown with deep-links back into the bot.
- 📊 **Admin `/stats` dashboard** — total / today / 7d / 30d revenue,
  paid-vs-unpaid order counts, average order value, unique customers, full
  status breakdown and top-5 products by units sold.

### Added — UX & operations
- 🌐 **Telegram WebApp mini-app** (React 18 + Tailwind CSS via CDN, no
  build step) with native theme integration, haptic feedback and
  context-sensitive `MainButton`. Hosted on GitHub Pages. Cart syncs back
  to the bot via `Telegram.WebApp.sendData` and resumes the standard
  checkout FSM.
- 🚦 **Sliding-window rate-limiting middleware** (30 messages / 60 callbacks
  per minute per user, configurable). Admins are exempt; throttled users get
  a single friendly notice per cooldown window.
- 👥 **User tracking middleware** writes every interaction into a
  `bot_users` table for `/stats` and future GDPR/broadcast features.

### Improved
- 8-category catalog of 40 specialty-coffee products, each with a unique
  AI-generated photo, priced realistically.
- Categories sort by intent (drinks → food → beans → equipment → accessories)
  instead of alphabetical order.
- `seed_if_empty` auto-detects drift between DB and `seed_data.PRODUCTS`
  and rebuilds the catalog without touching order history.
- Atomic cart updates (`add_to_cart` returns `bool`, `adjust_cart_quantity`
  is single-statement) so rapid double-tap doesn't lose increments.
- `get_cart` filters out-of-stock products by default so deactivating a
  product also removes it from existing carts.
- N+1 in `list_orders` collapsed into a single LEFT JOIN.
- All user-supplied text (name, phone, address, username, item names)
  HTML-escaped before rendering — no HTML injection in admin notifications.
- `safe_int` defensively parses callback_data — old or tampered buttons
  no longer crash the handler.
- `replace_or_edit` helper unifies the edit-or-delete-and-resend pattern,
  fixing double-tap "Home"/"About" crashes and photo→text transitions.
- `confirm_order` now gracefully handles stale FSM state after a bot
  restart with a "session expired" notice instead of silently ignoring
  the click.
- Photo card has graceful text-only fallback if the file is missing or
  unreadable (FileNotFoundError, OSError, TelegramAPIError all caught).

### Tooling
- `webapp/build_catalog.py` regenerates the WebApp's `catalog.json` from
  `seed_data.PRODUCTS`.
- `screenshots/mockups.html` + `_render.py` produce 14 pixel-perfect
  Telegram-styled PNGs at 2× resolution.
- `screenshots/_make_gif.py` stitches an animated demo GIF.
- `webapp/index.html` self-bootstraps catalog data via `fetch` so the
  same file works for both bot-served and statically-hosted setups.

### Documentation
- README rewritten with hero demo GIF, screenshot grid, full feature list,
  enabling-payments and enabling-WebApp guides, and live demo links.
- New `screenshots/README.md` with index, regeneration instructions and
  a "real screenshots vs mockups" decision guide.
- `.env.example` covers the new `PAYMENT_PROVIDER_TOKEN` and `WEBAPP_URL`
  variables with usage notes and test-card numbers.
- `LICENSE` (MIT) added.

## [0.1.0] — 2026-04-28

Initial demo release.

- Catalog → cart → 3-step FSM checkout → owner notification.
- 9 specialty-coffee products, 4 categories.
- aiogram 3 + aiosqlite, single-file SQLite DB.
- Owner DM with full order details on every confirmed order.
- Admin product wizard (`/add_product`), order list (`/orders_all`),
  category list (`/categories`).
- Six PNG mockup screenshots (`screenshots/01..06`).
