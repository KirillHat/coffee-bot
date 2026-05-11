# Demo-video script (90–120 seconds)

A short, well-paced demo wins more contracts than 5 minutes of rambling.
Aim for **90–120 seconds** at 1080p. The bigger the feature set, the more
the demo must respect the viewer's time.

## Recording setup

- **Tool:** [Loom](https://www.loom.com/) (fastest), [OBS Studio](https://obsproject.com/) (free, best quality),
  or QuickTime + iPhone mirroring for mobile-style footage.
- **Window layout:** Telegram Desktop on the left, your terminal running
  `python bot.py` on the right (so the viewer sees the logs react to clicks),
  WebApp window floating in the corner when you trigger it.
- **Resolution:** 1920 × 1080. If recording mobile, use the iOS built-in
  screen recorder or `scrcpy` for Android.
- **Voice-over:** turn it on. A quiet narration adds ~30 % perceived
  professionalism.

## Pre-flight checklist

- [ ] `cp .env.example .env` and fill in `BOT_TOKEN`, `ADMIN_IDS`,
      `OWNER_CHAT_ID`, `PAYMENT_PROVIDER_TOKEN` (Smart Glocal / Stripe test),
      `WEBAPP_URL` (https://kirillhat.github.io/coffee-bot-webapp/).
- [ ] Delete any existing `shop.db` so the catalog and orders are fresh.
- [ ] Open **two** Telegram chats side-by-side: the customer chat with the
      bot, and the owner chat (where notifications land — same user is fine).
- [ ] Run `python bot.py` and confirm the log shows
      `Catalog ready: 40 products` (or `Catalog is up to date — no re-seed needed`).
- [ ] Send `/start` once to warm up the bot — delete that message before
      recording so the take starts on a clean chat.
- [ ] Pre-create a promo code: `/promo add` → `SPRING10` / 10% / min 0 /
      unlimited. The discount will land in the demo invoice.
- [ ] Have the Stripe test card handy: `5555 5555 5555 4444` · 12/30 · 123.

## Storyboard — what to show, in order

| Time      | Action                                                                                              | Voice-over (suggested)                                                                                          |
| --------- | --------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| 0:00–0:05 | Title card or zoom-in on the bot's chat header                                                      | "This is Roastline Coffee — a production Telegram bot for a specialty coffee shop."                              |
| 0:05–0:12 | Send `/start`, point to the **five-button** main menu (Catalog / Cart / My orders / About / 🌐 Open Shop) | "Full inline keyboard navigation, no slash commands needed. The fifth button opens a React WebApp inside Telegram." |
| 0:12–0:22 | Tap **Catalog** → category → product → **➕ Add to cart**                                            | "8 categories, 40 products, each with a photo, description and price. Catalog is async SQLite."                  |
| 0:22–0:32 | Open **🧺 Cart**, demo **−/+/🗑** controls; subtotals recalculate                                   | "Quantity changes are atomic at the SQL layer, so rapid double-tap can't lose an increment."                     |
| 0:32–0:50 | Tap **Checkout** → name → phone → address → promo (`SPRING10`)                                      | "Four-step FSM checkout with input validation and an optional promo-code step. Watch the total drop 10 %."       |
| 0:50–1:05 | On the review screen, tap **💳 Pay with card** → enter `5555 5555 5555 4444`                        | "Real Telegram Payments. Smart Glocal in test mode here, swap in Stripe or YooKassa for production."             |
| 1:05–1:15 | Show the "Payment received" message + auto status DMs (confirmed → shipping)                        | "On a successful charge the order is created, force-confirmed, and the customer gets shipping updates by DM."    |
| 1:15–1:25 | **Switch to the owner chat** — show the "NEW PAID ORDER" notification with charge id                | "The shop owner gets the full order, payment id, and customer contact in real time."                             |
| 1:25–1:35 | Admin: `/order N` → tap **➡ 🚚 Shipping** → switch back to customer chat → DM lands                 | "Admins manage the order workflow with inline buttons — every transition auto-DMs the customer."                 |
| 1:35–1:45 | Send `/stats` — show revenue, AOV, top-5 products, status breakdown                                 | "Built-in sales dashboard — revenue, average order value, status breakdown and top products by units sold."      |
| 1:45–1:55 | Tap **🌐 Open Shop** in the main menu — WebApp opens, swipe through categories, tap Send order      | "Optional Tailwind WebApp deployed to GitHub Pages — the cart syncs back to the bot via `Telegram.WebApp.sendData`." |
| 1:55–2:05 | From any chat: `@VelvetMorning_bot ethiopian` — inline search dropdown                              | "Inline search works from any chat — perfect for sharing a product as a recommendation."                         |
| 2:05–2:15 | Cut to the GitHub README — show CI badge green, scroll past the screenshot grid                     | "Source on GitHub: MIT-licensed, 46 tests passing, ruff clean, Docker-ready. Link in the description."           |

## Pro tips

- **Hide your tokens.** Set log level to `WARNING` for the demo, or crop the
  terminal so the `Run polling for bot @VelvetMorning_bot id=…` line stays
  out of frame.
- **Picture-in-picture for the owner chat.** When the "NEW PAID ORDER"
  notification arrives, scale the owner chat to a small floating window in
  the corner — clients love seeing both sides at once.
- **Speed up the typing parts** in post (1.5–2×). Nobody wants to watch
  someone type "John Smith" in real time.
- **End with a 2-second freeze frame** of the GitHub URL or the live-demo
  Telegram link — an easy click-through for the prospect.
- **Caption it.** A second voice-over track in subtitles makes the video
  accessible and watchable on muted feeds (LinkedIn, Twitter previews).

## Where to host

1. **YouTube (unlisted)** — share-link is tiny, embeds work inside Upwork.
2. **Loom** — auto-generates a thumbnail and viewer analytics.
3. **Vimeo** — clean, ad-free player if you also have a personal site.

Paste the link into the Upwork **Project Link** field of this portfolio
item, and once more at the bottom of `upwork_description.md`.

## If you're not recording today

The repo already ships an animated GIF at `screenshots/demo.gif` (22 s, 10
key frames). It plays inline in the GitHub README and inside Upwork's
preview — good enough to publish the portfolio item immediately and add the
real video later.
