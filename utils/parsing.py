"""Small parsing helpers shared across handlers.

Kept tiny on purpose — anything more elaborate belongs in its own module.
"""
from __future__ import annotations

# SQLite INTEGER is 64-bit, but no realistic catalog will hit anywhere near 2 ** 31.
# Capping at 2 billion gives us cheap protection against overflow tricks while
# still allowing every reasonable product/category id.
_MAX_ID = 2_000_000_000


def safe_int(raw: str | None) -> int | None:
    """Parse a non-negative int from untrusted callback_data.

    Returns ``None`` for any non-integer, negative, or absurdly large value, so
    callers can refuse the click instead of crashing.
    """
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    if value < 0 or value > _MAX_ID:
        return None
    return value
