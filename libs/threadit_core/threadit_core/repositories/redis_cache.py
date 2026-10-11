from __future__ import annotations

from threadit_core.services.rate_limit import Counter, RateDecision, RateLimiter


class RedisCounter(Counter):
    def __init__(self, client) -> None:
        self._r = client

    def incr(self, key: str, amount: int = 1) -> int:
        return int(self._r.incrby(key, amount))

    def get(self, key: str) -> int:
        v = self._r.get(key)
        return int(v) if v is not None else 0


class RedisRateLimiter(RateLimiter):
    """Fixed-window limiter in Redis: INCR a per-window key with EXPIRE (atomic enough for P2)."""

    def __init__(self, client) -> None:
        self._r = client

    def check(self, key: str, *, limit: int, window_seconds: int) -> RateDecision:
        import time

        window = int(time.time()) // window_seconds
        bucket = f"rl:{key}:{window}"
        count = int(self._r.incr(bucket))
        if count == 1:
            self._r.expire(bucket, window_seconds)
        if count > limit:
            ttl = int(self._r.ttl(bucket))
            return RateDecision(allowed=False, retry_after=max(1, ttl))
        return RateDecision(allowed=True, retry_after=0)
