from __future__ import annotations

import os
import time

import boto3

_table = boto3.resource("dynamodb", region_name=os.environ["THREADIT_AWS_REGION"]).Table(
    os.environ["THREADIT_TABLE_NAME"]
)


def _pct(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    k = max(0, min(len(s) - 1, int(round(p / 100 * (len(s) - 1)))))
    return round(s[k], 2)


def handler(event: dict, _context=None) -> dict:
    """Measure in-region DynamoDB GetItem latency (ms) from inside the VPC.

    event: {"post_id": "<id>", "iterations": 200}
    """
    post_id = event.get("post_id", "nonexistent")
    iterations = int(event.get("iterations", 200))
    pk = f"POST#{post_id}"
    sk = f"META#{post_id}"

    latencies: list[float] = []
    for _ in range(iterations):
        start = time.perf_counter()
        _table.get_item(Key={"PK": pk, "SK": sk})
        latencies.append((time.perf_counter() - start) * 1000)

    return {
        "iterations": iterations,
        "ddb_getitem_ms": {
            "p50": _pct(latencies, 50),
            "p95": _pct(latencies, 95),
            "p99": _pct(latencies, 99),
            "min": round(min(latencies), 2),
            "max": round(max(latencies), 2),
        },
    }
