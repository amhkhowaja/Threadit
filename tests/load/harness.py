"""Real multi-user NFR/load harness for Threadit (httpx + asyncio).

Drives the running services over HTTP with many concurrent virtual users.
Backend (AWS real / Floci) is selected by the services' env at launch; this harness
only needs the base URLs. Cost-bounded by small user counts + short durations.
"""

from __future__ import annotations

import asyncio
import statistics
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field


@dataclass
class Sample:
    latency_ms: float
    status: int
    ok: bool


@dataclass
class Stats:
    name: str
    samples: list[Sample] = field(default_factory=list)

    def record(self, latency_ms: float, status: int, ok: bool) -> None:
        self.samples.append(Sample(latency_ms, status, ok))

    @property
    def count(self) -> int:
        return len(self.samples)

    @property
    def errors(self) -> int:
        return sum(1 for s in self.samples if not s.ok)

    @property
    def availability(self) -> float:
        if not self.samples:
            return 0.0
        non_5xx = sum(1 for s in self.samples if s.status < 500)
        return non_5xx / len(self.samples)

    def pct(self, p: float) -> float:
        if not self.samples:
            return 0.0
        xs = sorted(s.latency_ms for s in self.samples)
        k = max(0, min(len(xs) - 1, int(round(p / 100 * (len(xs) - 1)))))
        return xs[k]

    def summary(self) -> dict:
        return {
            "name": self.name,
            "count": self.count,
            "errors": self.errors,
            "availability": round(self.availability, 5),
            "p50_ms": round(self.pct(50), 1),
            "p95_ms": round(self.pct(95), 1),
            "p99_ms": round(self.pct(99), 1),
            "mean_ms": round(statistics.mean(s.latency_ms for s in self.samples), 1)
            if self.samples
            else 0.0,
        }


async def timed(stats: Stats, coro: Awaitable) -> object:
    start = time.perf_counter()
    status, ok, result = 599, False, None
    try:
        resp = await coro
        status = resp.status_code
        ok = status < 400
        result = resp
    except Exception:  # noqa: BLE001 - a transport error is a failed request, not a crash
        status, ok = 599, False
    finally:
        stats.record((time.perf_counter() - start) * 1000, status, ok)
    return result


async def run_users(
    *,
    users: int,
    duration_s: float,
    user_fn: Callable[[int, Stats], Awaitable[None]],
    stats: Stats,
) -> Stats:
    """Run `users` concurrent virtual users for `duration_s`, each looping user_fn."""
    deadline = time.monotonic() + duration_s

    async def one(uid: int) -> None:
        while time.monotonic() < deadline:
            await user_fn(uid, stats)

    await asyncio.gather(*(one(i) for i in range(users)))
    return stats
