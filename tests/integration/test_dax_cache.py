from __future__ import annotations

import os
from datetime import UTC, datetime

import pytest
from threadit_core.domain.models import Post
from threadit_core.repositories.dynamodb import DynamoDBRepository, build_dax_table

pytestmark = pytest.mark.integration

# DAX is prod-only (FLOCI compatibility finding F3 — the emulator does not provide a
# DAX cluster). This test runs ONLY when a real DAX endpoint is supplied via
# THREADIT_DAX_ENDPOINT (e.g. an in-VPC runner during a staging pass); otherwise it
# skips so `make check` stays green locally.
DAX_ENDPOINT = os.environ.get("THREADIT_DAX_ENDPOINT", "")
REGION = os.environ.get("THREADIT_AWS_REGION", "eu-central-1")
TABLE = os.environ.get("THREADIT_TABLE_NAME", "threadit")

NOW = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture()
def dax_repo():
    if not DAX_ENDPOINT:
        pytest.skip("THREADIT_DAX_ENDPOINT not set (DAX is prod-only; F3)")
    table = build_dax_table(table_name=TABLE, region=REGION, dax_endpoint=DAX_ENDPOINT)
    return DynamoDBRepository(table)


def _post(pid: str, uid: str) -> Post:
    return Post(post_id=pid, user_id=uid, title="t", body="b", created_at=NOW, updated_at=NOW)


def test_dax_cached_read_roundtrip(dax_repo):
    """A written post is readable back through the DAX-backed repo (cache or
    pass-through)."""
    dax_repo.put_post(_post("dax-p1", "u1"))
    got = dax_repo.get_post("dax-p1")
    assert got is not None and got.post_id == "dax-p1"


def test_dax_consistent_read_your_own_write(dax_repo):
    """ConsistentRead through DAX forwards to DynamoDB, so a just-written post is
    immediately visible (read-your-own-write preserved)."""
    dax_repo.put_post(_post("dax-p2", "u2"))
    got = dax_repo.get_post("dax-p2", consistent=True)
    assert got is not None and got.user_id == "u2"
