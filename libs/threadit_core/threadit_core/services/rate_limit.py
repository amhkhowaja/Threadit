from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class RateDecision:
    allowed: bool
    retry_after: int


class RateLimiter(ABC):
    @abstractmethod
    def check(self, key: str, *, limit: int, window_seconds: int) -> RateDecision: ...


class Counter(ABC):
    @abstractmethod
    def incr(self, key: str, amount: int = 1) -> int: ...

    @abstractmethod
    def get(self, key: str) -> int: ...


@dataclass(slots=True)
class InMemoryRateLimiter(RateLimiter):
    """Fixed-window limiter for tests / single-process dev. Prod uses the Redis impl."""

    _hits: dict[str, tuple[int, float]] = field(default_factory=dict)
    _clock: Callable[[], float] = time.monotonic

    def check(self, key: str, *, limit: int, window_seconds: int) -> RateDecision:
        now = self._clock()
        count, window_start = self._hits.get(key, (0, now))
        if now - window_start >= window_seconds:
            count, window_start = 0, now
        count += 1
        self._hits[key] = (count, window_start)
        if count > limit:
            retry_after = max(1, int(window_seconds - (now - window_start)))
            return RateDecision(allowed=False, retry_after=retry_after)
        return RateDecision(allowed=True, retry_after=0)


@dataclass(slots=True)
class InMemoryCounter(Counter):
    _c: dict[str, int] = field(default_factory=dict)

    def incr(self, key: str, amount: int = 1) -> int:
        self._c[key] = self._c.get(key, 0) + amount
        return self._c[key]

    def get(self, key: str) -> int:
        return self._c.get(key, 0)
