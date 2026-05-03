# Demo-video script (60–90 seconds)

A short, well-paced demo wins more contracts than 5 minutes of rambling. Aim for **60–90 seconds**, captured at 1080p.

## Recording setup

- **Tool:** [Loom](https://www.loom.com/) (easiest), [OBS Studio](https://obsproject.com/) (best quality, free), or QuickTime + iPhone mirroring.
- **Window layout:** Telegram Desktop on the left, your terminal running `python bot.py` on the right (so the viewer sees the logs reacting to clicks).
- **Resolution:** 1920 × 1080. If recording mobile, use Android screen recorder + scrcpy or iOS built-in.
- **Voice-over:** turn it on. A quiet narration adds ~30% perceived professionalism.

## Pre-flight checklist

- [ ] `cp .env.example .env` and fill in `BOT_TOKEN`, `ADMIN_IDS`, `OWNER_CHAT_ID`.
- [ ] Delete any existing `shop.db` so the seed data is fresh.
- [ ] Open **two** Telegram chats side-by-side: the bot chat (customer) and the owner chat (where notifications land).
- [ ] Run `python bot.py` and confirm the log shows `Seeded the catalog with 9 demo products.`
- [ ] Send `/start` once to warm up the bot — kill that message before recording.

## Storyboard — what to show, in order

| Time     | Action                                                                          | Voice-over (suggested)                                                                                |
| -------- | ------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| 0:00–0:05 | Title card or zoom-in on the bot's chat header                                  | "This is Roastline Coffee — a Telegram bot I built for a specialty coffee shop."                       |
| 0:05–0:12 | Send `/start`, point to the four-button main menu                               | "The menu is fully inline — no slash commands needed for the customer."                                |
| 0:12–0:20 | Tap **Catalog** → tap **Single Origin Beans** → tap **Ethiopian Yirgacheffe**   | "Categories load from SQLite, products show a photo, description and price."                           |
| 0:20–0:28 | Tap **Add to cart** twice, then **🧺 Cart**                                      | "Quantities are managed in-place with plus and minus buttons."                                          |
| 0:28–0:35 | Hit **➕** to bump quantity, then **🗑** to remove a different item               | "Subtotals and the grand total recalculate on every change."                                           |
| 0:35–0:55 | Tap **Checkout**, type a name, phone, address; reach the review screen          | "Three-step FSM checkout with input validation — invalid phone numbers get rejected."                  |
| 0:55–1:05 | Tap **Confirm order**; show the customer success screen                         | "On confirm, the order is written to SQLite, the cart is cleared, and the customer gets a receipt."    |
| 1:05–1:15 | **Switch to the owner chat** — show the new-order notification arriving live    | "And here's the owner chat receiving the full order details and customer contact in real time."        |
| 1:15–1:25 | Switch to admin Telegram, send `/orders_all` showing the new order              | "Admins can review every order with a single command, plus add new products through a guided wizard."  |
| 1:25–1:30 | Cut back to the GitHub README; quick scroll through the project structure       | "Modular code, async SQLite, environment-based config. The full repo is on my GitHub."                 |

## Pro tips

- **Hide your API token.** Before recording, blur the terminal output if it shows the `BOT_TOKEN` log line. A clean recording is to set log level to `WARNING` for the demo.
- **Use the picture-in-picture trick.** When the owner notification arrives, scale the owner chat to a small floating window in the corner — clients love seeing the two sides of the system at once.
- **Speed up the typing parts** in post (1.5×). Nobody needs to watch you type "John Smith" in real time.
- **End with a 2-second freeze frame** of the GitHub URL — easy click-through for the prospect.

## Where to host

1. **YouTube (unlisted)** — share-link is tiny, embeds work in Upwork.
2. **Loom** — auto-generates a thumbnail and viewer analytics.
3. **Vimeo** — if you want a clean, ad-free player on your own portfolio site.

Paste the link in the Upwork "Project Link" field of this portfolio item, and again at the bottom of the description.
