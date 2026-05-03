"""Tests for the sliding-window rate-limit middleware."""
from __future__ import annotations

from middlewares.rate_limit import RateLimitMiddleware


def test_blocks_after_exceeding_window():
    rl = RateLimitMiddleware(message_limit=3, window_seconds=10)
    for _ in range(3):
        assert not rl._is_over_limit(99, "msg", 3)
    # 4th request in the window must be blocked
    assert rl._is_over_limit(99, "msg", 3)


def test_per_user_isolation():
    rl = RateLimitMiddleware(message_limit=2, window_seconds=10)
    assert not rl._is_over_limit(1, "msg", 2)
    assert not rl._is_over_limit(1, "msg", 2)
    # User 2 has its own bucket — not affected by user 1's history.
    assert not rl._is_over_limit(2, "msg", 2)


def test_per_event_kind_isolation():
    """Messages and callbacks have independent quotas."""
    rl = RateLimitMiddleware(message_limit=1, callback_limit=5, window_seconds=10)
    assert not rl._is_over_limit(99, "msg", 1)
    assert rl._is_over_limit(99, "msg", 1)         # 2nd msg blocked
    # callback bucket still empty
    assert not rl._is_over_limit(99, "cb", 5)


def test_window_eviction_releases_capacity():
    """Old timestamps roll out of the sliding window."""
    rl = RateLimitMiddleware(message_limit=2, window_seconds=0.05)
    assert not rl._is_over_limit(99, "msg", 2)
    assert not rl._is_over_limit(99, "msg", 2)
    assert rl._is_over_limit(99, "msg", 2)
    import time
    time.sleep(0.1)
    # window has rolled — bucket is empty again
    assert not rl._is_over_limit(99, "msg", 2)
