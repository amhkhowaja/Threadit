from __future__ import annotations

from datetime import UTC, datetime

from threadit_core.domain.models import Comment, Post
from threadit_core.repositories.mapper import ItemMapper

NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)


def test_post_roundtrip():
    post = Post(post_id="p1", user_id="u1", title="t", body="b", created_at=NOW, updated_at=NOW)
    item = ItemMapper.post_to_item(post)
    assert item["PK"] == "POST#p1"
    assert item["SK"] == "META#p1"
    assert item["GSI1PK"].startswith("BUCKET#")
    assert item["GSI2PK"] == "USER#u1"
    assert item["entityType"] == "Post"
    assert ItemMapper.item_to_post(item) == post


def test_comment_roundtrip_top_level_has_no_parent():
    c = Comment(
        comment_id="c1",
        post_id="p1",
        user_id="u1",
        text="hi",
        created_at=NOW,
        depth=0,
        path="ts#c1",
        root_comment_id="c1",
        parent_id=None,
    )
    item = ItemMapper.comment_to_item(c)
    assert item["PK"] == "POST#p1"
    assert item["SK"] == "COMMENT#ts#c1"
    assert "parentId" not in item
    assert ItemMapper.item_to_comment(item) == c


def test_comment_roundtrip_child_keeps_parent():
    c = Comment(
        comment_id="c2",
        post_id="p1",
        user_id="u1",
        text="r",
        created_at=NOW,
        depth=1,
        path="ts#c1#ts#c2",
        root_comment_id="c1",
        parent_id="c1",
    )
    item = ItemMapper.comment_to_item(c)
    assert item["parentId"] == "c1"
    assert ItemMapper.item_to_comment(item) == c
