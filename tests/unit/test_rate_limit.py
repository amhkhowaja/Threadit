from __future__ import annotations

from threadit_core.services.rate_limit import InMemoryCounter, InMemoryRateLimiter


def test_allows_up_to_limit_then_blocks_with_retry_after():
    t = [100.0]
    rl = InMemoryRateLimiter()
    rl._clock = lambda: t[0]
    for _ in range(5):
        assert rl.check("ip:1", limit=5, window_seconds=60).allowed
    blocked = rl.check("ip:1", limit=5, window_seconds=60)
    assert blocked.allowed is False
    assert blocked.retry_after > 0


def test_window_resets():
    t = [100.0]
    rl = InMemoryRateLimiter()
    rl._clock = lambda: t[0]
    for _ in range(5):
        rl.check("ip:1", limit=5, window_seconds=10)
    assert rl.check("ip:1", limit=5, window_seconds=10).allowed is False
    t[0] += 11  # next window
    assert rl.check("ip:1", limit=5, window_seconds=10).allowed is True


def test_keys_are_independent():
    rl = InMemoryRateLimiter()
    assert rl.check("a", limit=1, window_seconds=60).allowed
    assert rl.check("b", limit=1, window_seconds=60).allowed


def test_counter_incr_and_get():
    c = InMemoryCounter()
    assert c.incr("post:1:comments") == 1
    assert c.incr("post:1:comments", 2) == 3
    assert c.get("post:1:comments") == 3
    assert c.get("missing") == 0
