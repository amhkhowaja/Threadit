from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class _Entry(Generic[T]):
    value: T
    fresh_until: float
    stale_until: float


@dataclass(slots=True)
class SingleFlightCache(Generic[T]):
    """In-process read cache with request coalescing + stale-while-revalidate (ADR-005, R12).

    - Concurrent misses for the same key collapse to a single loader call (single-flight).
    - Values are fresh for ttl seconds, then served stale (once) for stale_ttl while one
      caller refreshes — preventing a thundering herd on hot-key expiry.
    - TTL carries jitter to avoid synchronized expiry.
    """

    ttl: float = 2.0
    stale_ttl: float = 10.0
    jitter: float = 0.5
    _store: dict[str, _Entry[T]] = field(default_factory=dict)
    _locks: dict[str, threading.Lock] = field(default_factory=dict)
    _guard: threading.Lock = field(default_factory=threading.Lock)
    _clock: Callable[[], float] = time.monotonic
    loads: int = 0

    def _key_lock(self, key: str) -> threading.Lock:
        with self._guard:
            return self._locks.setdefault(key, threading.Lock())

    def get(self, key: str, loader: Callable[[], T]) -> T:
        now = self._clock()
        entry = self._store.get(key)
        if entry and now < entry.fresh_until:
            return entry.value

        lock = self._key_lock(key)
        if not lock.acquire(blocking=entry is not None and now < entry.stale_until):
            # someone else is refreshing and we still have a usable stale value
            return entry.value  # type: ignore[union-attr]
        try:
            entry = self._store.get(key)
            now = self._clock()
            if entry and now < entry.fresh_until:
                return entry.value
            value = loader()
            self.loads += 1
            self._store[key] = _Entry(
                value=value,
                fresh_until=now + self.ttl + (self.jitter * 0.5),
                stale_until=now + self.ttl + self.stale_ttl,
            )
            return value
        finally:
            lock.release()

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)
