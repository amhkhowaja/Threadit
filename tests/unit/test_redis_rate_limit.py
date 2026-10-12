from __future__ import annotations

import importlib
import sys
import types

write_app = importlib.import_module("services.post_write.app")


class _Settings:
    def __init__(self, *, redis_endpoint: str = ""):
        self.redis_endpoint = redis_endpoint


class _FakeRedis:
    """Minimal in-memory Redis stand-in supporting the ops RedisRateLimiter uses."""

    def __init__(self):
        self.store: dict[str, int] = {}
        self.ttls: dict[str, int] = {}

    def incr(self, key):
        self.store[key] = self.store.get(key, 0) + 1
        return self.store[key]

    def incrby(self, key, amount):
        self.store[key] = self.store.get(key, 0) + amount
        return self.store[key]

    def get(self, key):
        return self.store.get(key)

    def expire(self, key, seconds):
        self.ttls[key] = seconds

    def ttl(self, key):
        return self.ttls.get(key, -1)


# --- contract: limiter selection ------------------------------------------------


def test_build_rate_limiter_uses_redis_when_endpoint_set(monkeypatch):
    from threadit_core.repositories.redis_cache import RedisRateLimiter

    # Stub the `redis` module so no real connection is attempted.
    fake_redis_mod = types.ModuleType("redis")
    fake_redis_mod.Redis = lambda host, port: _FakeRedis()
    monkeypatch.setitem(sys.modules, "redis", fake_redis_mod)

    limiter = write_app._build_rate_limiter(_Settings(redis_endpoint="my-cache:6379"))
    assert isinstance(limiter, RedisRateLimiter)


def test_build_rate_limiter_falls_back_to_in_memory_when_unset():
    from threadit_core.services.rate_limit import InMemoryRateLimiter

    limiter = write_app._build_rate_limiter(_Settings(redis_endpoint=""))
    assert isinstance(limiter, InMemoryRateLimiter)


# --- contract: RedisRateLimiter fixed-window behavior ---------------------------


def test_redis_limiter_allows_then_blocks_with_retry_after():
    from threadit_core.repositories.redis_cache import RedisRateLimiter

    rl = RedisRateLimiter(_FakeRedis())
    for _ in range(5):
        assert rl.check("write:u1", limit=5, window_seconds=60).allowed
    blocked = rl.check("write:u1", limit=5, window_seconds=60)
    assert blocked.allowed is False
    assert blocked.retry_after > 0


def test_redis_limiter_sets_expiry_on_first_hit():
    from threadit_core.repositories.redis_cache import RedisRateLimiter

    fake = _FakeRedis()
    rl = RedisRateLimiter(fake)
    rl.check("write:u2", limit=3, window_seconds=45)
    # exactly one window key created, with the window TTL applied
    assert len(fake.ttls) == 1
    assert next(iter(fake.ttls.values())) == 45


def test_redis_limiter_keys_are_independent_per_user():
    from threadit_core.repositories.redis_cache import RedisRateLimiter

    rl = RedisRateLimiter(_FakeRedis())
    assert rl.check("write:a", limit=1, window_seconds=60).allowed
    assert rl.check("write:b", limit=1, window_seconds=60).allowed  # different user, own window
