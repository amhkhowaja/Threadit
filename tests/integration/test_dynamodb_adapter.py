from __future__ import annotations

from datetime import UTC, datetime

import pytest
from threadit_core.domain.models import Comment, Post
from threadit_core.repositories.dynamodb import DynamoDBIdempotencyStore, DynamoDBRepository

pytestmark = pytest.mark.integration

NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)


def _post(pid: str, uid: str) -> Post:
    return Post(post_id=pid, user_id=uid, title="t", body="b", created_at=NOW, updated_at=NOW)


def test_post_put_get_roundtrip(table):
    repo = DynamoDBRepository(table)
    repo.put_post(_post("p1", "u1"))
    got = repo.get_post("p1", consistent=True)
    assert got is not None
    assert got.post_id == "p1"
    assert got.user_id == "u1"


def test_idempotency_claim_then_replay(table):
    store = DynamoDBIdempotencyStore(table, ttl_seconds=3600)
    assert store.try_claim("key-1", "target-1") is True
    assert store.try_claim("key-1", "target-2") is False  # replay blocked
    assert store.resolve_target("key-1") == "target-1"


def test_threaded_comment_tree_in_order(table):
    repo = DynamoDBRepository(table)
    top = Comment(
        comment_id="c1",
        post_id="p1",
        user_id="u1",
        text="top",
        created_at=NOW,
        depth=0,
        path="20260102T030405000000Z#c1",
        root_comment_id="c1",
        parent_id=None,
    )
    child = Comment(
        comment_id="c2",
        post_id="p1",
        user_id="u1",
        text="reply",
        created_at=NOW,
        depth=1,
        path="20260102T030405000000Z#c1#20260102T030406000000Z#c2",
        root_comment_id="c1",
        parent_id="c1",
    )
    repo.put_comment(top)
    repo.put_comment(child)
    tree = repo.get_comment_tree("p1", limit=20, cursor=None)
    ids = [c.comment_id for c in tree.items]
    assert ids == ["c1", "c2"]  # materialized path keeps subtree contiguous + ordered


def test_list_user_posts_via_gsi2(table):
    repo = DynamoDBRepository(table)
    repo.put_post(_post("p1", "u1"))
    repo.put_post(_post("p2", "u2"))
    page = repo.list_user_posts("u1", limit=20, cursor=None)
    assert [p.post_id for p in page.items] == ["p1"]
