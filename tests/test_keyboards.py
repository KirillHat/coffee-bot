"""Tests for keyboard builders — button counts and conditional buttons."""
from __future__ import annotations

from keyboards.inline import (
    cancel_kb,
    cart_kb,
    categories_kb,
    confirm_order_kb,
    main_menu_kb,
    product_kb,
    products_kb,
)


def _all_buttons(kb):
    return [b for row in kb.inline_keyboard for b in row]


def _callback_data(kb):
    return [b.callback_data for b in _all_buttons(kb) if b.callback_data]


def test_main_menu_without_webapp():
    kb = main_menu_kb(webapp_url="")
    cb = _callback_data(kb)
    assert {"catalog", "cart", "my_orders", "about"} == set(cb)


def test_main_menu_with_webapp_adds_button():
    kb = main_menu_kb(webapp_url="https://example.com/")
    btns = _all_buttons(kb)
    assert any(b.web_app for b in btns), "WebApp button missing"
    assert sum(1 for _ in btns) == 5


def test_confirm_order_kb_payment_toggle():
    kb_pay = confirm_order_kb(payments_enabled=True)
    kb_nopay = confirm_order_kb(payments_enabled=False)
    assert "pay_card" in _callback_data(kb_pay)
    assert "pay_card" not in _callback_data(kb_nopay)
    assert len(_all_buttons(kb_pay)) == len(_all_buttons(kb_nopay)) + 1


def test_cancel_kb_has_only_cancel():
    cb = _callback_data(cancel_kb())
    assert cb == ["order_cancel"]


# A couple of light-weight constructor tests using mock-shape data.

class _StubCategory:
    def __init__(self, _id, name, emoji):
        self.id, self.name, self.emoji = _id, name, emoji


class _StubProduct:
    def __init__(self, _id, name, price, cat_id=1):
        self.id, self.name, self.price, self.category_id = _id, name, price, cat_id


class _StubCartItem:
    def __init__(self, pid, name, qty):
        self.product_id, self.name, self.quantity = pid, name, qty


def test_categories_kb_includes_navigation():
    kb = categories_kb([_StubCategory(1, "X", "☕"), _StubCategory(2, "Y", "🧊")])
    cb = _callback_data(kb)
    assert "cat:1" in cb and "cat:2" in cb
    assert "cart" in cb and "home" in cb


def test_product_kb_links_back_to_category():
    kb = product_kb(_StubProduct(7, "X", 9.0, cat_id=3))
    cb = _callback_data(kb)
    assert "add:7" in cb
    assert "cat:3" in cb        # back-to-category preserves cat_id
    assert "cart" in cb


def test_cart_kb_renders_per_item_controls():
    items = [_StubCartItem(1, "A", 2), _StubCartItem(2, "B", 1)]
    kb = cart_kb(items)
    cb = _callback_data(kb)
    for pid in (1, 2):
        assert f"qty:{pid}:inc" in cb
        assert f"qty:{pid}:dec" in cb
        assert f"qty:{pid}:rm" in cb
    assert "checkout" in cb and "clear_cart" in cb


def test_products_kb_lists_each_product():
    products = [_StubProduct(i, f"P{i}", 1.0) for i in (1, 2, 3)]
    cb = _callback_data(products_kb(products))
    assert {"prod:1", "prod:2", "prod:3"} <= set(cb)
