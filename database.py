"""SQLite database layer for the shop bot.

Uses aiosqlite for async I/O so DB access never blocks the event loop.
Tables: categories, products, cart_items, orders, order_items.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import aiosqlite


SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    emoji       TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS products (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    description TEXT NOT NULL,
    price       REAL NOT NULL CHECK (price >= 0),
    photo_url   TEXT,
    in_stock    INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS cart_items (
    user_id     INTEGER NOT NULL,
    product_id  INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    quantity    INTEGER NOT NULL CHECK (quantity > 0),
    PRIMARY KEY (user_id, product_id)
);

CREATE TABLE IF NOT EXISTS orders (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL,
    username            TEXT,
    full_name           TEXT NOT NULL,
    phone               TEXT NOT NULL,
    address             TEXT NOT NULL,
    subtotal            REAL NOT NULL DEFAULT 0,
    discount_amount     REAL NOT NULL DEFAULT 0,
    promo_code          TEXT,
    total               REAL NOT NULL,
    status              TEXT NOT NULL DEFAULT 'new',
    payment_charge_id   TEXT,
    payment_provider    TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS order_items (
    order_id    INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id  INTEGER NOT NULL,
    name        TEXT NOT NULL,
    price       REAL NOT NULL,
    quantity    INTEGER NOT NULL,
    PRIMARY KEY (order_id, product_id)
);

CREATE TABLE IF NOT EXISTS order_status_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id    INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    status      TEXT NOT NULL,
    note        TEXT,
    changed_by  INTEGER,
    changed_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS promo_codes (
    code            TEXT PRIMARY KEY,
    discount_pct    INTEGER NOT NULL CHECK (discount_pct BETWEEN 1 AND 100),
    min_subtotal    REAL NOT NULL DEFAULT 0,
    valid_until     TEXT,
    max_uses        INTEGER,
    used_count      INTEGER NOT NULL DEFAULT 0,
    active          INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS bot_users (
    user_id     INTEGER PRIMARY KEY,
    username    TEXT,
    first_seen  TEXT NOT NULL DEFAULT (datetime('now')),
    last_seen   TEXT NOT NULL DEFAULT (datetime('now')),
    locale      TEXT
);

CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_status_history_order ON order_status_history(order_id);
CREATE INDEX IF NOT EXISTS idx_products_search ON products(name);
"""

# In-place migrations for users who already have a DB created with the older
# schema (pre-v2). Each entry is a (column-presence test, ALTER TABLE statement).
# Ran once on connect — SQLite shrugs off duplicate adds, but we guard anyway.
_ALTER_MIGRATIONS = [
    ("orders", "subtotal", "ALTER TABLE orders ADD COLUMN subtotal REAL NOT NULL DEFAULT 0"),
    ("orders", "discount_amount", "ALTER TABLE orders ADD COLUMN discount_amount REAL NOT NULL DEFAULT 0"),
    ("orders", "promo_code", "ALTER TABLE orders ADD COLUMN promo_code TEXT"),
    ("orders", "payment_charge_id", "ALTER TABLE orders ADD COLUMN payment_charge_id TEXT"),
    ("orders", "payment_provider", "ALTER TABLE orders ADD COLUMN payment_provider TEXT"),
]


# ---------------------------------------------------------------------------
# Order status workflow
# ---------------------------------------------------------------------------
ORDER_STATUSES: tuple[str, ...] = (
    "new",
    "confirmed",
    "shipping",
    "delivered",
    "cancelled",
)
STATUS_LABELS: dict[str, str] = {
    "new": "🆕 New",
    "confirmed": "✅ Confirmed",
    "shipping": "🚚 Shipping",
    "delivered": "📬 Delivered",
    "cancelled": "❌ Cancelled",
}
# Allowed transitions — protects history from going backwards or skipping
# cancelled. From `new` you can confirm or cancel; from `confirmed` ship or
# cancel; from `shipping` deliver or cancel; from terminal states — nothing.
STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    "new": frozenset({"confirmed", "cancelled"}),
    "confirmed": frozenset({"shipping", "cancelled"}),
    "shipping": frozenset({"delivered", "cancelled"}),
    "delivered": frozenset(),
    "cancelled": frozenset(),
}


@dataclass
class Category:
    id: int
    name: str
    emoji: str


@dataclass
class Product:
    id: int
    category_id: int
    name: str
    description: str
    price: float
    photo_url: str | None
    in_stock: bool


@dataclass
class CartItem:
    product_id: int
    name: str
    price: float
    quantity: int

    @property
    def subtotal(self) -> float:
        return round(self.price * self.quantity, 2)


@dataclass
class OrderSummary:
    id: int
    user_id: int
    username: str | None
    full_name: str
    phone: str
    address: str
    subtotal: float
    discount_amount: float
    promo_code: str | None
    total: float
    status: str
    payment_charge_id: str | None
    payment_provider: str | None
    created_at: str
    items: list[CartItem]


@dataclass
class PromoCode:
    code: str
    discount_pct: int
    min_subtotal: float
    valid_until: str | None
    max_uses: int | None
    used_count: int
    active: bool

    def can_apply(self, subtotal: float, *, now_iso: str) -> tuple[bool, str | None]:
        """Return (ok, reason_if_not). The reason is a user-facing string."""
        if not self.active:
            return False, "This promo code is no longer active."
        if self.valid_until and self.valid_until < now_iso:
            return False, "This promo code has expired."
        if self.max_uses is not None and self.used_count >= self.max_uses:
            return False, "This promo code has reached its usage limit."
        if subtotal < self.min_subtotal:
            return False, f"Minimum cart subtotal for this code is ${self.min_subtotal:.2f}."
        return True, None

    def discount_for(self, subtotal: float) -> float:
        return round(subtotal * (self.discount_pct / 100), 2)


@dataclass
class StatusEvent:
    status: str
    note: str | None
    changed_by: int | None
    changed_at: str


class Database:
    """Thin async wrapper around aiosqlite. One connection per app, FK on."""

    def __init__(self, path: Path):
        self.path = path
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA foreign_keys = ON")
        await self._conn.executescript(SCHEMA)
        await self._apply_alter_migrations()
        await self._conn.commit()

    async def _apply_alter_migrations(self) -> None:
        """Apply best-effort ADD COLUMN migrations for older DBs."""
        for table, column, alter_sql in _ALTER_MIGRATIONS:
            async with self._conn.execute(f"PRAGMA table_info({table})") as cur:
                cols = {row["name"] for row in await cur.fetchall()}
            if column not in cols:
                await self._conn.execute(alter_sql)

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if not self._conn:
            raise RuntimeError("Database is not connected. Call connect() first.")
        return self._conn

    # --- Categories -----------------------------------------------------

    async def list_categories(self) -> list[Category]:
        # Sorted by id (insertion order from seed_data.py) so the menu reflects
        # the deliberate flow — drinks → food → beans → equipment → accessories
        # — instead of being alphabetised.
        async with self.conn.execute("SELECT id, name, emoji FROM categories ORDER BY id") as cur:
            rows = await cur.fetchall()
        return [Category(**dict(r)) for r in rows]

    async def get_category(self, category_id: int) -> Category | None:
        async with self.conn.execute(
            "SELECT id, name, emoji FROM categories WHERE id = ?", (category_id,)
        ) as cur:
            row = await cur.fetchone()
        return Category(**dict(row)) if row else None

    async def add_category(self, name: str, emoji: str = "") -> int:
        async with self.conn.execute(
            "INSERT INTO categories (name, emoji) VALUES (?, ?) "
            "ON CONFLICT(name) DO UPDATE SET emoji = excluded.emoji RETURNING id",
            (name, emoji),
        ) as cur:
            row = await cur.fetchone()
        await self.conn.commit()
        return int(row["id"])

    # --- Products -------------------------------------------------------

    async def list_products(self, category_id: int) -> list[Product]:
        query = (
            "SELECT id, category_id, name, description, price, photo_url, in_stock "
            "FROM products WHERE category_id = ? AND in_stock = 1 ORDER BY name"
        )
        async with self.conn.execute(query, (category_id,)) as cur:
            rows = await cur.fetchall()
        return [_row_to_product(r) for r in rows]

    async def get_product(
        self, product_id: int, *, include_out_of_stock: bool = False
    ) -> Product | None:
        """Fetch a product. By default skips out-of-stock items so the catalog and
        cart can't accidentally surface a hidden product just because someone has
        a stale callback_data referencing it.
        """
        query = (
            "SELECT id, category_id, name, description, price, photo_url, in_stock "
            "FROM products WHERE id = ?"
        )
        if not include_out_of_stock:
            query += " AND in_stock = 1"
        async with self.conn.execute(query, (product_id,)) as cur:
            row = await cur.fetchone()
        return _row_to_product(row) if row else None

    async def add_product(
        self,
        category_id: int,
        name: str,
        description: str,
        price: float,
        photo_url: str | None = None,
    ) -> int:
        async with self.conn.execute(
            "INSERT INTO products (category_id, name, description, price, photo_url) "
            "VALUES (?, ?, ?, ?, ?) RETURNING id",
            (category_id, name, description, price, photo_url),
        ) as cur:
            row = await cur.fetchone()
        await self.conn.commit()
        return int(row["id"])

    async def count_products(self) -> int:
        async with self.conn.execute("SELECT COUNT(*) AS c FROM products") as cur:
            row = await cur.fetchone()
        return int(row["c"])

    # --- Cart -----------------------------------------------------------

    async def add_to_cart(
        self, user_id: int, product_id: int, qty: int = 1, *, max_qty: int = 99
    ) -> bool:
        """Insert or increment, refusing to add out-of-stock products and capping
        per-product quantity to ``max_qty`` atomically.

        Returns ``True`` if the product was actually added or its row updated,
        ``False`` if the product is missing/out-of-stock or the quantity was
        already at ``max_qty`` (no rows changed). Lets callers show an honest
        confirmation toast instead of always saying "Added".
        """
        if qty <= 0:
            return False
        clamped = min(qty, max_qty)
        cur = await self.conn.execute(
            """
            INSERT INTO cart_items (user_id, product_id, quantity)
            SELECT ?, ?, ? FROM products
            WHERE id = ? AND in_stock = 1
            ON CONFLICT(user_id, product_id) DO UPDATE
            SET quantity = MIN(quantity + excluded.quantity, ?)
            WHERE quantity < ?
            """,
            (user_id, product_id, clamped, product_id, max_qty, max_qty),
        )
        changed = cur.rowcount > 0
        await self.conn.commit()
        return changed

    async def adjust_cart_quantity(
        self,
        user_id: int,
        product_id: int,
        *,
        delta: int,
        max_qty: int = 99,
    ) -> None:
        """Atomically change quantity by ``delta`` (±1 etc).

        - Clamps to ``max_qty`` on the upper end.
        - If the resulting quantity would be ≤ 0, the row is removed.

        Each user has at most one row per product, and aiosqlite serialises all
        statements on a single connection, so two parallel '+' clicks against
        the same row can't lose an increment — the second UPDATE always reads
        the result of the first.
        """
        # First, clamp upward — only succeeds when the resulting value stays
        # within the CHECK (quantity > 0) constraint. The MIN/MAX is computed
        # inside SQLite so even a stale read can't widen past max_qty.
        await self.conn.execute(
            """
            UPDATE cart_items
            SET quantity = MIN(MAX(quantity + ?, 1), ?)
            WHERE user_id = ? AND product_id = ? AND quantity + ? > 0
            """,
            (delta, max_qty, user_id, product_id, delta),
        )
        # Then remove the row if the requested delta would have driven it to 0.
        await self.conn.execute(
            """
            DELETE FROM cart_items
            WHERE user_id = ? AND product_id = ? AND quantity + ? <= 0
            """,
            (user_id, product_id, delta),
        )
        await self.conn.commit()

    async def remove_from_cart(self, user_id: int, product_id: int) -> None:
        await self.conn.execute(
            "DELETE FROM cart_items WHERE user_id = ? AND product_id = ?",
            (user_id, product_id),
        )
        await self.conn.commit()

    async def clear_cart(self, user_id: int) -> None:
        await self.conn.execute("DELETE FROM cart_items WHERE user_id = ?", (user_id,))
        await self.conn.commit()

    async def get_cart(
        self, user_id: int, *, include_out_of_stock: bool = False
    ) -> list[CartItem]:
        """Return the user's cart. By default skips items whose product was
        deactivated since the cart was filled — they should not be shippable
        and the user should not see them as still purchasable."""
        query = """
            SELECT p.id AS product_id, p.name, p.price, c.quantity
            FROM cart_items c
            JOIN products p ON p.id = c.product_id
            WHERE c.user_id = ?
        """
        if not include_out_of_stock:
            query += " AND p.in_stock = 1"
        query += " ORDER BY p.name"
        async with self.conn.execute(query, (user_id,)) as cur:
            rows = await cur.fetchall()
        return [CartItem(**dict(r)) for r in rows]

    async def cart_total(self, user_id: int) -> float:
        items = await self.get_cart(user_id)
        return round(sum(item.subtotal for item in items), 2)

    # --- Orders ---------------------------------------------------------

    async def create_order(
        self,
        user_id: int,
        username: str | None,
        full_name: str,
        phone: str,
        address: str,
        *,
        promo_code: str | None = None,
        discount_amount: float = 0.0,
        payment_charge_id: str | None = None,
        payment_provider: str | None = None,
    ) -> OrderSummary:
        items = await self.get_cart(user_id)
        if not items:
            raise ValueError("Cart is empty")
        subtotal = round(sum(i.subtotal for i in items), 2)
        discount_amount = round(max(0.0, discount_amount), 2)
        total = round(max(0.0, subtotal - discount_amount), 2)

        async with self.conn.execute(
            """
            INSERT INTO orders (
                user_id, username, full_name, phone, address,
                subtotal, discount_amount, promo_code, total, status,
                payment_charge_id, payment_provider
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', ?, ?)
            RETURNING id, created_at
            """,
            (
                user_id, username, full_name, phone, address,
                subtotal, discount_amount, promo_code, total,
                payment_charge_id, payment_provider,
            ),
        ) as cur:
            row = await cur.fetchone()
        order_id = int(row["id"])
        created_at = row["created_at"]

        await self.conn.executemany(
            "INSERT INTO order_items (order_id, product_id, name, price, quantity) "
            "VALUES (?, ?, ?, ?, ?)",
            [(order_id, i.product_id, i.name, i.price, i.quantity) for i in items],
        )
        # Bookkeeping: log initial status so the history is non-empty from day one.
        await self.conn.execute(
            "INSERT INTO order_status_history (order_id, status, changed_by) VALUES (?, 'new', ?)",
            (order_id, user_id),
        )
        # Promo code usage counter — atomic, only if a code was applied.
        if promo_code:
            await self.conn.execute(
                "UPDATE promo_codes SET used_count = used_count + 1 WHERE code = ?",
                (promo_code.upper(),),
            )
        await self.conn.execute("DELETE FROM cart_items WHERE user_id = ?", (user_id,))
        await self.conn.commit()

        return OrderSummary(
            id=order_id,
            user_id=user_id,
            username=username,
            full_name=full_name,
            phone=phone,
            address=address,
            subtotal=subtotal,
            discount_amount=discount_amount,
            promo_code=promo_code,
            total=total,
            status="new",
            payment_charge_id=payment_charge_id,
            payment_provider=payment_provider,
            created_at=created_at,
            items=items,
        )

    async def get_order(self, order_id: int) -> OrderSummary | None:
        results = await self._fetch_orders(limit=1, order_id=order_id)
        return results[0] if results else None

    async def list_orders(self, limit: int = 20) -> list[OrderSummary]:
        """All orders, newest first. Admin-only — uses a single JOIN to avoid N+1."""
        return await self._fetch_orders(limit=limit)

    async def list_user_orders(self, user_id: int, limit: int = 20) -> list[OrderSummary]:
        """Orders belonging to a specific user. Always filter by user_id, never by username."""
        return await self._fetch_orders(limit=limit, user_id=user_id)

    async def _fetch_orders(
        self,
        limit: int,
        *,
        user_id: int | None = None,
        order_id: int | None = None,
    ) -> list[OrderSummary]:
        # Build the inner subquery that picks the most recent order ids for the
        # requested scope. Three literal branches — no user data is interpolated.
        if order_id is not None:
            inner_subquery = "SELECT id FROM orders WHERE id = ?"
            params: tuple = (order_id,)
        elif user_id is None:
            inner_subquery = "SELECT id FROM orders ORDER BY id DESC LIMIT ?"
            params = (limit,)
        else:
            inner_subquery = "SELECT id FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT ?"
            params = (user_id, limit)

        query = f"""
            SELECT
                o.id                  AS order_id,
                o.user_id             AS user_id,
                o.username            AS username,
                o.full_name           AS full_name,
                o.phone               AS phone,
                o.address             AS address,
                o.subtotal            AS subtotal,
                o.discount_amount     AS discount_amount,
                o.promo_code          AS promo_code,
                o.total               AS total,
                o.status              AS status,
                o.payment_charge_id   AS payment_charge_id,
                o.payment_provider    AS payment_provider,
                o.created_at          AS created_at,
                oi.product_id         AS product_id,
                oi.name               AS item_name,
                oi.price              AS item_price,
                oi.quantity           AS item_quantity
            FROM orders o
            LEFT JOIN order_items oi ON oi.order_id = o.id
            WHERE o.id IN ({inner_subquery})
            ORDER BY o.id DESC, oi.product_id ASC
        """
        async with self.conn.execute(query, params) as cur:
            rows = await cur.fetchall()

        # Group by order_id, preserving descending order.
        orders_map: dict[int, OrderSummary] = {}
        for row in rows:
            oid = row["order_id"]
            order = orders_map.get(oid)
            if order is None:
                order = OrderSummary(
                    id=oid,
                    user_id=row["user_id"],
                    username=row["username"],
                    full_name=row["full_name"],
                    phone=row["phone"],
                    address=row["address"],
                    subtotal=row["subtotal"] or 0.0,
                    discount_amount=row["discount_amount"] or 0.0,
                    promo_code=row["promo_code"],
                    total=row["total"],
                    status=row["status"],
                    payment_charge_id=row["payment_charge_id"],
                    payment_provider=row["payment_provider"],
                    created_at=row["created_at"],
                    items=[],
                )
                orders_map[oid] = order
            if row["product_id"] is not None:  # LEFT JOIN: skip orders with no items
                order.items.append(
                    CartItem(
                        product_id=row["product_id"],
                        name=row["item_name"],
                        price=row["item_price"],
                        quantity=row["item_quantity"],
                    )
                )
        return list(orders_map.values())

    # --- Order status workflow ------------------------------------------

    async def update_order_status(
        self,
        order_id: int,
        new_status: str,
        *,
        changed_by: int | None = None,
        note: str | None = None,
        force: bool = False,
    ) -> tuple[bool, str | None]:
        """Move an order to ``new_status``. Returns (ok, error_message_or_None).

        Refuses transitions that don't match ``STATUS_TRANSITIONS`` unless
        ``force`` is set (used for payment-driven flows that jump straight to
        confirmed). Always logs an entry to ``order_status_history``.
        """
        if new_status not in ORDER_STATUSES:
            return False, f"Unknown status: {new_status!r}"
        order = await self.get_order(order_id)
        if not order:
            return False, f"Order #{order_id} not found"
        if order.status == new_status:
            return False, f"Order is already {new_status!r}"
        if not force and new_status not in STATUS_TRANSITIONS.get(order.status, frozenset()):
            return False, (
                f"Cannot move from {order.status!r} to {new_status!r}. "
                f"Allowed: {sorted(STATUS_TRANSITIONS.get(order.status, frozenset()))}"
            )
        await self.conn.execute(
            "UPDATE orders SET status = ? WHERE id = ?", (new_status, order_id)
        )
        await self.conn.execute(
            "INSERT INTO order_status_history (order_id, status, note, changed_by) "
            "VALUES (?, ?, ?, ?)",
            (order_id, new_status, note, changed_by),
        )
        await self.conn.commit()
        return True, None

    async def order_status_history(self, order_id: int) -> list[StatusEvent]:
        async with self.conn.execute(
            "SELECT status, note, changed_by, changed_at FROM order_status_history "
            "WHERE order_id = ? ORDER BY id ASC",
            (order_id,),
        ) as cur:
            rows = await cur.fetchall()
        return [StatusEvent(**dict(r)) for r in rows]

    # --- Promo codes ----------------------------------------------------

    async def add_promo_code(
        self,
        code: str,
        discount_pct: int,
        *,
        min_subtotal: float = 0.0,
        valid_until: str | None = None,
        max_uses: int | None = None,
        active: bool = True,
    ) -> None:
        await self.conn.execute(
            """
            INSERT INTO promo_codes
                (code, discount_pct, min_subtotal, valid_until, max_uses, active)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(code) DO UPDATE SET
                discount_pct = excluded.discount_pct,
                min_subtotal = excluded.min_subtotal,
                valid_until = excluded.valid_until,
                max_uses = excluded.max_uses,
                active = excluded.active
            """,
            (code.upper(), discount_pct, min_subtotal, valid_until, max_uses, int(active)),
        )
        await self.conn.commit()

    async def get_promo_code(self, code: str) -> PromoCode | None:
        async with self.conn.execute(
            "SELECT code, discount_pct, min_subtotal, valid_until, max_uses, "
            "used_count, active FROM promo_codes WHERE code = ?",
            (code.upper(),),
        ) as cur:
            row = await cur.fetchone()
        if not row:
            return None
        data = dict(row)
        data["active"] = bool(data["active"])
        return PromoCode(**data)

    async def list_promo_codes(self) -> list[PromoCode]:
        async with self.conn.execute(
            "SELECT code, discount_pct, min_subtotal, valid_until, max_uses, "
            "used_count, active FROM promo_codes ORDER BY code"
        ) as cur:
            rows = await cur.fetchall()
        codes = []
        for r in rows:
            data = dict(r)
            data["active"] = bool(data["active"])
            codes.append(PromoCode(**data))
        return codes

    # --- Search ---------------------------------------------------------

    async def search_products(self, query: str, limit: int = 20) -> list[Product]:
        """Case-insensitive LIKE search over name + description."""
        like = f"%{query}%"
        async with self.conn.execute(
            """
            SELECT id, category_id, name, description, price, photo_url, in_stock
            FROM products
            WHERE in_stock = 1 AND (name LIKE ? COLLATE NOCASE OR description LIKE ? COLLATE NOCASE)
            ORDER BY name
            LIMIT ?
            """,
            (like, like, limit),
        ) as cur:
            rows = await cur.fetchall()
        return [_row_to_product(r) for r in rows]

    # --- Stats (admin) --------------------------------------------------

    async def stats_summary(self) -> dict[str, Any]:
        """Aggregate KPIs for the admin /stats command."""
        async def scalar(sql: str, params: tuple = ()) -> Any:
            async with self.conn.execute(sql, params) as cur:
                row = await cur.fetchone()
            return row[0] if row else None

        # Headline KPIs (excludes cancelled orders from revenue but counts them).
        revenue = await scalar(
            "SELECT COALESCE(SUM(total), 0) FROM orders WHERE status != 'cancelled'"
        )
        order_count = await scalar("SELECT COUNT(*) FROM orders")
        paid_count = await scalar("SELECT COUNT(*) FROM orders WHERE payment_charge_id IS NOT NULL")
        avg_order = await scalar(
            "SELECT COALESCE(AVG(total), 0) FROM orders WHERE status != 'cancelled'"
        )
        unique_customers = await scalar("SELECT COUNT(DISTINCT user_id) FROM orders")

        # Time buckets (today / 7d / 30d).
        revenue_today = await scalar(
            "SELECT COALESCE(SUM(total), 0) FROM orders "
            "WHERE status != 'cancelled' AND date(created_at) = date('now')"
        )
        revenue_week = await scalar(
            "SELECT COALESCE(SUM(total), 0) FROM orders "
            "WHERE status != 'cancelled' AND created_at >= datetime('now', '-7 days')"
        )
        revenue_month = await scalar(
            "SELECT COALESCE(SUM(total), 0) FROM orders "
            "WHERE status != 'cancelled' AND created_at >= datetime('now', '-30 days')"
        )

        # Status breakdown.
        async with self.conn.execute(
            "SELECT status, COUNT(*) AS c FROM orders GROUP BY status"
        ) as cur:
            status_rows = await cur.fetchall()
        status_counts = {row["status"]: row["c"] for row in status_rows}

        # Top-5 products by units sold (cancelled orders don't count).
        async with self.conn.execute(
            """
            SELECT oi.name AS name, SUM(oi.quantity) AS units, SUM(oi.quantity * oi.price) AS revenue
            FROM order_items oi
            JOIN orders o ON o.id = oi.order_id
            WHERE o.status != 'cancelled'
            GROUP BY oi.name
            ORDER BY units DESC
            LIMIT 5
            """
        ) as cur:
            top_rows = await cur.fetchall()
        top_products = [
            {"name": row["name"], "units": row["units"], "revenue": row["revenue"]}
            for row in top_rows
        ]

        return {
            "revenue_total": round(revenue or 0, 2),
            "revenue_today": round(revenue_today or 0, 2),
            "revenue_week": round(revenue_week or 0, 2),
            "revenue_month": round(revenue_month or 0, 2),
            "order_count": order_count or 0,
            "paid_count": paid_count or 0,
            "avg_order": round(avg_order or 0, 2),
            "unique_customers": unique_customers or 0,
            "status_counts": status_counts,
            "top_products": top_products,
        }

    # --- User tracking --------------------------------------------------

    async def upsert_user(self, user_id: int, username: str | None) -> None:
        """Track every user we see — used for /stats and GDPR purposes."""
        await self.conn.execute(
            """
            INSERT INTO bot_users (user_id, username) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE
            SET username = excluded.username, last_seen = datetime('now')
            """,
            (user_id, username),
        )
        await self.conn.commit()


def _row_to_product(row: aiosqlite.Row) -> Product:
    data: dict[str, Any] = dict(row)
    data["in_stock"] = bool(data["in_stock"])
    return Product(**data)
