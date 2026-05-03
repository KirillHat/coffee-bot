# Upwork portfolio description (ready-to-paste)

---

## Title (under 70 chars — Upwork will truncate)

> **Telegram E-commerce Bot — Payments, WebApp, Admin Panel (Python/aiogram)**

Alternative shorter variants:

- *Production-Ready Telegram Shop Bot with Stripe Payments + Mini-App*
- *Telegram E-Shop: Catalog, Cart, Card Payments, WebApp, Admin Stats*

---

## Description (≈200 words — fits Upwork's project field cleanly)

Production-ready Telegram bot for an online coffee shop. Customers browse a
**40-item catalog by category**, build a cart, **apply promo codes**, and
**pay by card via Telegram Payments** (Smart Glocal / Stripe / YooKassa) —
all without leaving Telegram.

Built with **aiogram 3** and async SQLite. Includes a complete admin
toolkit:

- **Order status workflow** (`new → confirmed → shipping → delivered`)
  with auto-DMs to the customer at every transition
- **`/stats` dashboard** — total / today / 7d / 30d revenue, orders, AOV,
  status breakdown, top-5 products by units sold
- **Promo-code manager** with min-subtotal and max-uses limits
- **Add-product wizard** for the catalog

Also ships:

- 🌐 **React + Tailwind WebApp** mini-app (deployed to GitHub Pages) —
  swipey native catalog inside Telegram with cart sync back to the bot
- 🔍 **Inline search** — `@bot ethiopian` from any chat returns matching
  products with deep-links into the shop
- 🚦 **Sliding-window rate-limiting** middleware with admin bypass
- 🛡 HTML-escaped admin notifications, atomic cart operations, schema
  auto-migrations, graceful photo fallback

21 modules, modular architecture (handlers, middlewares, keyboards, states,
utils), MIT-licensed, end-to-end smoke-tested.

**Live demo:** [@VelvetMorning_bot](https://t.me/VelvetMorning_bot)
**WebApp:** https://kirillhat.github.io/coffee-bot-webapp/
**Code:** GitHub repo (link in profile)

---

## Skills / tags for the portfolio item

`Python` · `Telegram Bot` · `aiogram 3` · `Telegram Payments` · `Telegram WebApp` ·
`Stripe` · `Smart Glocal` · `React 18` · `Tailwind CSS` · `SQLite` ·
`Async/Await` · `FSM` · `E-commerce` · `Backend Development` ·
`Python Asyncio` · `REST API` · `OAuth` · `GitHub Pages`

---

## Suggested cover & gallery images

- **Cover image:** `screenshots/all_screens.png` — 4×4 grid of every
  feature on one canvas; gives clients a 3-second elevator pitch.
- **Animated demo:** `screenshots/demo.gif` — 22-second loop of the full
  user flow (catalog → cart → promo → payment → success → WebApp →
  `/stats`). Upload as a "video" attachment if Upwork allows.
- **Gallery (in this order, ~6 shots is the sweet spot):**
  1. `screenshots/01_main_menu.png` — first impression
  2. `screenshots/06_checkout_review.png` — promo discount applied
  3. `screenshots/07_payment_invoice.png` — 💳 Stripe-style native payment
  4. `screenshots/08_payment_success.png` — auto-confirmation + status DMs
  5. `screenshots/11_stats_dashboard.png` — the admin sales overview
  6. `screenshots/13_webapp_home.png` — the WebApp mini-app

---

## Suggested rate / project pricing

- **Hourly rate** with this single project in your portfolio: **$25–40 /hr**
- **Fixed-price** for a similar bot: **$800–2 500** depending on integrations
- **Optional WebApp add-on** for an existing bot: **+$500–1 000**
- **Optional Telegram Payments setup** (provider negotiation, testing,
  go-live): **+$200–500**

If you list yourself below $15/hr with this kind of demo, serious clients
will assume something is wrong with the work.

---

## Pinned message in the first reply to a client

When a client opens chat, send something like this in the first 60 seconds:

> Hey {{name}}, thanks for reaching out!
>
> Quick links so you can evaluate the work before deciding:
>
> 🔹 Live bot: [@VelvetMorning_bot](https://t.me/VelvetMorning_bot)
> 🔹 Mini-app: kirillhat.github.io/coffee-bot-webapp
> 🔹 Source code: github.com/{{your-username}}/coffee-bot
>
> Test card for the payment flow: `5555 5555 5555 4444`,
> any future date, any CVC. No real money is charged.
>
> Happy to walk you through the architecture on a quick call, or scope
> out what would need to change to fit your business.
