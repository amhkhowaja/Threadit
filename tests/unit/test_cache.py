from __future__ import annotations

import threading
import time

from threadit_core.services.cache import SingleFlightCache


def test_fresh_hit_does_not_reload():
    c = SingleFlightCache(ttl=10, stale_ttl=10)
    assert c.get("k", lambda: "v1") == "v1"
    assert c.get("k", lambda: "v2") == "v1"  # still fresh
    assert c.loads == 1


def test_invalidate_forces_reload():
    c = SingleFlightCache(ttl=10)
    c.get("k", lambda: "v1")
    c.invalidate("k")
    assert c.get("k", lambda: "v2") == "v2"
    assert c.loads == 2


def test_expired_entry_reloads():
    t = [1000.0]
    c = SingleFlightCache(ttl=1, stale_ttl=0, jitter=0)
    c._clock = lambda: t[0]
    assert c.get("k", lambda: "v1") == "v1"
    t[0] += 5  # past fresh + stale
    assert c.get("k", lambda: "v2") == "v2"
    assert c.loads == 2


def test_single_flight_collapses_concurrent_misses():
    c = SingleFlightCache(ttl=10)
    calls = []

    def slow_loader():
        time.sleep(0.1)
        calls.append(1)
        return "v"

    threads = [threading.Thread(target=lambda: c.get("hot", slow_loader)) for _ in range(10)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()

    # all 10 concurrent misses collapse to a single loader call
    assert len(calls) == 1
    assert c.loads == 1
