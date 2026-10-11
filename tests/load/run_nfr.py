from __future__ import annotations

import asyncio
import contextlib
import json
import os
import socket
import time
import uuid

import httpx
import uvicorn

from tests.load.harness import Stats, run_users, timed

WRITE_PORT = int(os.environ.get("NFR_WRITE_PORT", "8091"))
READ_PORT = int(os.environ.get("NFR_READ_PORT", "8090"))
WRITE_URL = f"http://127.0.0.1:{WRITE_PORT}"
READ_URL = f"http://127.0.0.1:{READ_PORT}"

# Cost-bounded defaults; override via env.
USERS = int(os.environ.get("NFR_USERS", "20"))
DURATION = float(os.environ.get("NFR_DURATION", "8"))

# SLO targets (SYSTEM_ARCHITECTURE §7 / PLANNING §3.7).
SLO_READ_P99_MS = float(os.environ.get("NFR_SLO_READ_P99", "150"))
SLO_WRITE_P99_MS = float(os.environ.get("NFR_SLO_WRITE_P99", "300"))
SLO_AVAILABILITY = float(os.environ.get("NFR_SLO_AVAIL", "0.999"))
SLO_SEARCH_LAG_S = float(os.environ.get("NFR_SLO_SEARCH_LAG", "10"))


def _uid() -> str:
    return str(uuid.uuid4())


class _Server:
    def __init__(self, app_path: str, port: int):
        self._app_path = app_path
        self._port = port
        self._server: uvicorn.Server | None = None
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        config = uvicorn.Config(
            self._app_path, host="127.0.0.1", port=self._port, log_level="warning", workers=1
        )
        self._server = uvicorn.Server(config)
        self._task = asyncio.create_task(self._server.serve())
        for _ in range(100):
            with contextlib.suppress(OSError):
                with socket.create_connection(("127.0.0.1", self._port), timeout=0.5):
                    return
            await asyncio.sleep(0.1)
        raise RuntimeError(f"server {self._app_path} did not start")

    async def stop(self) -> None:
        if self._server:
            self._server.should_exit = True
        if self._task:
            with contextlib.suppress(Exception):
                await self._task


async def _seed_posts(client: httpx.AsyncClient, n: int) -> list[str]:
    ids = []
    for _ in range(n):
        r = await client.post(
            f"{WRITE_URL}/v1/posts",
            json={"title": f"seed {_uid()[:8]}", "body": "seed body"},
            headers={"x-user-id": _uid(), "Idempotency-Key": _uid()},
        )
        if r.status_code == 201:
            ids.append(r.json()["id"])
    return ids


async def scenario_latency(client, post_ids) -> dict:
    read = Stats("read_latency")
    write = Stats("write_latency")

    async def user(uid: int, _s: Stats) -> None:
        pid = post_ids[uid % len(post_ids)]
        await timed(read, client.get(f"{READ_URL}/v1/posts/{pid}"))
        await timed(read, client.get(f"{READ_URL}/v1/posts"))
        await timed(
            write,
            client.post(
                f"{WRITE_URL}/v1/posts",
                json={"title": "lat", "body": "b"},
                headers={"x-user-id": _uid(), "Idempotency-Key": _uid()},
            ),
        )

    await run_users(users=USERS, duration_s=DURATION, user_fn=user, stats=read)
    return {"read": read.summary(), "write": write.summary()}


async def scenario_throughput_availability(client, post_ids) -> dict:
    s = Stats("throughput")
    start = time.monotonic()

    async def user(uid: int, _s: Stats) -> None:
        pid = post_ids[uid % len(post_ids)]
        await timed(s, client.get(f"{READ_URL}/v1/posts/{pid}"))

    await run_users(users=USERS, duration_s=DURATION, user_fn=user, stats=s)
    elapsed = time.monotonic() - start
    out = s.summary()
    out["rps"] = round(s.count / elapsed, 1)
    out["availability"] = s.availability
    return out


async def scenario_eventual_consistency(client) -> dict:
    uid = _uid()
    r = await client.post(
        f"{WRITE_URL}/v1/posts",
        json={"title": f"ryow {_uid()[:6]}", "body": "read your own write"},
        headers={"x-user-id": uid, "Idempotency-Key": _uid()},
    )
    pid = r.json()["id"]
    consistent = await client.get(f"{READ_URL}/v1/posts/{pid}?consistent=true")
    return {
        "read_your_own_write_consistent": consistent.status_code == 200,
        "post_id": pid,
    }


async def scenario_search_lag(client) -> dict:
    kw = f"zxq{uuid.uuid4().hex[:6]}"
    r = await client.post(
        f"{WRITE_URL}/v1/posts",
        json={"title": f"lag {kw}", "body": "search lag probe"},
        headers={"x-user-id": _uid(), "Idempotency-Key": _uid()},
    )
    if r.status_code != 201:
        return {"skipped": "write failed"}
    pid = r.json()["id"]
    start = time.monotonic()
    lag = None
    search_enabled = True
    for _ in range(40):
        s = await client.get(f"{READ_URL}/v1/posts", params={"search_keyword": kw})
        if s.status_code == 501:
            search_enabled = False
            break
        if s.status_code == 200 and any(p["id"] == pid for p in s.json().get("items", [])):
            lag = time.monotonic() - start
            break
        await asyncio.sleep(0.5)
    return {"search_enabled": search_enabled, "indexing_lag_s": round(lag, 2) if lag else None}


async def scenario_caching(client, post_ids) -> dict:
    # Repeated concurrent reads of ONE hot post; the read service's single-flight cache
    # (if wired) collapses load. We measure p99 + that burst reads succeed under contention.
    s = Stats("cache_hot_post")
    hot = post_ids[0]

    async def user(uid: int, _s: Stats) -> None:
        await timed(s, client.get(f"{READ_URL}/v1/posts/{hot}"))

    await run_users(users=USERS, duration_s=DURATION, user_fn=user, stats=s)
    return s.summary()


async def scenario_rate_limit(client) -> dict:
    # Hammer the write path from one identity; if an app-level limiter is active we expect 429.
    uid = _uid()
    statuses = []
    for _ in range(60):
        r = await client.post(
            f"{WRITE_URL}/v1/posts",
            json={"title": "rl", "body": "b"},
            headers={"x-user-id": uid, "Idempotency-Key": _uid()},
        )
        statuses.append(r.status_code)
    got_429 = 429 in statuses
    note = (
        "app-level limiter active"
        if got_429
        else "no app-limit in P2 hot path (WAF/stage-throttle is edge-only, F2)"
    )
    return {
        "requests": len(statuses),
        "got_429": got_429,
        "note": note,
    }


async def main() -> int:
    backend = "AWS" if os.environ.get("THREADIT_OPENSEARCH_SIGN") == "true" else "Floci/local"
    write_srv = _Server("services.post_write.app:app", WRITE_PORT)
    read_srv = _Server("services.post_read.app:app", READ_PORT)
    await write_srv.start()
    await read_srv.start()
    report: dict = {"backend": backend, "users": USERS, "duration_s": DURATION}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            post_ids = await _seed_posts(client, max(5, USERS // 2))
            report["seeded_posts"] = len(post_ids)
            report["latency"] = await scenario_latency(client, post_ids)
            report["throughput_availability"] = await scenario_throughput_availability(
                client, post_ids
            )
            report["eventual_consistency"] = await scenario_eventual_consistency(client)
            report["search_lag"] = await scenario_search_lag(client)
            report["caching"] = await scenario_caching(client, post_ids)
            report["rate_limit"] = await scenario_rate_limit(client)
    finally:
        await write_srv.stop()
        await read_srv.stop()

    # SLO verdicts
    verdicts = {
        "read_p99_within_slo": report["latency"]["read"]["p99_ms"] <= SLO_READ_P99_MS,
        "write_p99_within_slo": report["latency"]["write"]["p99_ms"] <= SLO_WRITE_P99_MS,
        "availability_within_slo": report["throughput_availability"]["availability"]
        >= SLO_AVAILABILITY,
        "read_your_own_write": report["eventual_consistency"]["read_your_own_write_consistent"],
    }
    lag = report["search_lag"].get("indexing_lag_s")
    if report["search_lag"].get("search_enabled"):
        verdicts["search_lag_within_slo"] = lag is not None and lag <= SLO_SEARCH_LAG_S
    report["slo_verdicts"] = verdicts

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
