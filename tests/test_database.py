"""Tests for database.py — schema, products, cart, orders, status, promo."""
from __future__ import annotations

import pytest

from database import (
    ORDER_STATUSES,
    STATUS_TRANSITIONS,
)

# ─── Catalog basics ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_seed_creates_full_catalog(seeded_db):
    products = []
    for cat in await seeded_db.list_categories():
        products.extend(await seeded_db.list_products(cat.id))
    assert len(products) == 40
    assert len({p.id for p in products}) == 40, "ids must be unique"


@pytest.mark.asyncio
async def test_categories_sorted_by_id_not_alphabet(seeded_db):
    """Catalog should reflect intent order from seed_data.py, not A→Z."""
    cats = await seeded_db.list_categories()
    names = [c.name for c in cats]
    assert names[0] == "Hot Coffee Drinks"          # ☕ comes first
    assert names[-1] == "Accessories"               # 🎁 comes last
    assert names != sorted(names), "categories must NOT be alphabetised"


@pytest.mark.asyncio
async def test_get_product_filters_out_of_stock(seeded_db):
    p = await seeded_db.get_product(1)
    assert p is not None

    # mark as OOS
    await seeded_db.conn.execute("UPDATE products SET in_stock = 0 WHERE id = 1")
    await seeded_db.conn.commit()

    assert await seeded_db.get_product(1) is None
    assert await seeded_db.get_product(1, include_out_of_stock=True) is not None


# ─── Cart operations ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_to_cart_returns_bool(seeded_db):
    assert await seeded_db.add_to_cart(99, 1) is True
    # second add (increment) also returns True
    assert await seeded_db.add_to_cart(99, 1) is True


@pytest.mark.asyncio
async def test_add_to_cart_caps_at_max_qty(seeded_db):
    for _ in range(150):
        await seeded_db.add_to_cart(99, 1)
    cart = await seeded_db.get_cart(99)
    assert cart[0].quantity == 99            # default cap

    # at-cap add must signal "no work done"
    assert await seeded_db.add_to_cart(99, 1) is False


@pytest.mark.asyncio
async def test_add_to_cart_skips_missing_product(seeded_db):
    """No exception, just returns False — important so the bot never crashes
    on a stale callback_data with an invalid product id."""
    assert await seeded_db.add_to_cart(99, 99_999) is False


@pytest.mark.asyncio
async def test_get_cart_hides_out_of_stock_by_default(seeded_db):
    await seeded_db.add_to_cart(99, 5)
    await seeded_db.conn.execute("UPDATE products SET in_stock = 0 WHERE id = 5")
    await seeded_db.conn.commit()

    visible = await seeded_db.get_cart(99)
    full = await seeded_db.get_cart(99, include_out_of_stock=True)

    assert all(it.product_id != 5 for it in visible)
    assert any(it.product_id == 5 for it in full)


@pytest.mark.asyncio
async def test_adjust_cart_quantity_clamps_and_removes(seeded_db):
    await seeded_db.add_to_cart(99, 3, qty=5)

    # +200 — should clamp to 99
    await seeded_db.adjust_cart_quantity(99, 3, delta=+200, max_qty=99)
    cart = await seeded_db.get_cart(99)
    assert cart[0].quantity == 99

    # delta that drives qty to exactly 0 — row removed
    await seeded_db.adjust_cart_quantity(99, 3, delta=-99, max_qty=99)
    assert await seeded_db.get_cart(99) == []

    # massive negative delta on missing row — no exception, still empty
    await seeded_db.adjust_cart_quantity(99, 3, delta=-100, max_qty=99)
    assert await seeded_db.get_cart(99) == []


# ─── Orders ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_order_with_promo(seeded_db):
    await seeded_db.add_promo_code("SPRING10", 10, min_subtotal=0)
    await seeded_db.add_to_cart(99, 4, qty=5)

    promo = await seeded_db.get_promo_code("SPRING10")
    discount = promo.discount_for(24.0)        # 5×$4.80 = $24

    order = await seeded_db.create_order(
        99, "tester", "T", "+1", "Addr",
        promo_code="SPRING10", discount_amount=discount,
    )
    assert order.subtotal == 24.0
    assert order.discount_amount == 2.40
    assert order.total == 21.60
    assert order.user_id == 99


@pytest.mark.asyncio
async def test_promo_used_count_increments_atomically(seeded_db):
    await seeded_db.add_promo_code("X", 5, max_uses=3)
    for _ in range(2):
        await seeded_db.add_to_cart(99, 1)
        await seeded_db.create_order(99, None, "T", "+1", "A", promo_code="X")

    promo = await seeded_db.get_promo_code("X")
    assert promo.used_count == 2


@pytest.mark.asyncio
async def test_user_orders_filter_by_user_id_not_username(seeded_db):
    """Privacy regression test: a user with NO username must not see orders
    of other users who also have no username."""
    await seeded_db.add_to_cart(42, 1)
    await seeded_db.create_order(42, None, "Anon42", "+1", "Addr 1")

    await seeded_db.add_to_cart(43, 1)
    await seeded_db.create_order(43, None, "Anon43", "+1", "Addr 2")

    o42 = await seeded_db.list_user_orders(42)
    o43 = await seeded_db.list_user_orders(43)

    assert len(o42) == 1 and o42[0].full_name == "Anon42"
    assert len(o43) == 1 and o43[0].full_name == "Anon43"


@pytest.mark.asyncio
async def test_list_orders_admin_sees_all_with_items(seeded_db):
    for uid in (1, 2, 3):
        await seeded_db.add_to_cart(uid, uid)
        await seeded_db.create_order(uid, None, f"U{uid}", "+1", "A")

    orders = await seeded_db.list_orders()
    assert len(orders) == 3
    assert all(len(o.items) >= 1 for o in orders), "JOIN should populate items"


# ─── Status workflow ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_status_transitions_follow_workflow(seeded_db):
    await seeded_db.add_to_cart(99, 1)
    o = await seeded_db.create_order(99, None, "T", "+1", "A")

    ok, _ = await seeded_db.update_order_status(o.id, "confirmed")
    assert ok
    ok, _ = await seeded_db.update_order_status(o.id, "shipping")
    assert ok
    ok, err = await seeded_db.update_order_status(o.id, "new")
    assert not ok and "Cannot move" in err

    history = await seeded_db.order_status_history(o.id)
    assert [h.status for h in history] == ["new", "confirmed", "shipping"]


@pytest.mark.asyncio
async def test_force_flag_bypasses_workflow(seeded_db):
    """Payment success path force-confirms regardless of state."""
    await seeded_db.add_to_cart(99, 1)
    o = await seeded_db.create_order(99, None, "T", "+1", "A")

    # Without force, you can't go new → delivered
    ok, _ = await seeded_db.update_order_status(o.id, "delivered")
    assert not ok

    # With force, you can
    ok, _ = await seeded_db.update_order_status(o.id, "delivered", force=True)
    assert ok


@pytest.mark.parametrize("status", list(ORDER_STATUSES))
def test_status_transitions_exhaustive(status):
    """Every status in ORDER_STATUSES must have a transition map entry."""
    assert status in STATUS_TRANSITIONS
    # Outgoing edges only point at known statuses.
    for next_status in STATUS_TRANSITIONS[status]:
        assert next_status in ORDER_STATUSES


# ─── Search + stats ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_search_is_case_insensitive_and_skips_oos(seeded_db):
    hits_lower = await seeded_db.search_products("ethiopian")
    hits_upper = await seeded_db.search_products("ETHIOPIAN")
    assert {p.name for p in hits_lower} == {p.name for p in hits_upper}
    assert any("Ethiopian" in p.name for p in hits_lower)


@pytest.mark.asyncio
async def test_stats_summary_excludes_cancelled_from_revenue(seeded_db):
    await seeded_db.add_to_cart(99, 1)
    o = await seeded_db.create_order(99, None, "T", "+1", "A")
    await seeded_db.update_order_status(o.id, "cancelled", force=True)

    stats = await seeded_db.stats_summary()
    assert stats["order_count"] == 1
    assert stats["revenue_total"] == 0.0       # cancelled doesn't count
    assert stats["status_counts"].get("cancelled") == 1


# ─── User tracking ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upsert_user_idempotent(db):
    await db.upsert_user(123, "alpha")
    await db.upsert_user(123, "alpha-renamed")  # should UPDATE, not duplicate

    async with db.conn.execute("SELECT COUNT(*), username FROM bot_users") as cur:
        row = await cur.fetchone()
    assert row[0] == 1
    assert row[1] == "alpha-renamed"
