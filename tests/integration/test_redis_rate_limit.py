from __future__ import annotations

import os
import uuid

import pytest
from threadit_core.repositories.redis_cache import RedisRateLimiter

pytestmark = pytest.mark.integration

# Runs ONLY when a reachable Redis/ElastiCache endpoint is provided; otherwise skips
# so `make check` stays green locally (ElastiCache is not emulated here).
REDIS_ENDPOINT = os.environ.get("THREADIT_REDIS_ENDPOINT", "")


@pytest.fixture()
def limiter():
    if not REDIS_ENDPOINT:
        pytest.skip("THREADIT_REDIS_ENDPOINT not set")
    import redis

    client = redis.Redis(host=REDIS_ENDPOINT, port=6379, socket_connect_timeout=3)
    client.ping()
    return RedisRateLimiter(client)


def test_shared_window_allows_then_blocks(limiter):
    key = f"write:{uuid.uuid4()}"
    for _ in range(3):
        assert limiter.check(key, limit=3, window_seconds=30).allowed
    blocked = limiter.check(key, limit=3, window_seconds=30)
    assert blocked.allowed is False
    assert blocked.retry_after > 0
