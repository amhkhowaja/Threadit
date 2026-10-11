from __future__ import annotations

from datetime import UTC, datetime

import pytest
from threadit_core.domain.errors import NotFoundError, SearchNotAvailableError
from threadit_core.domain.models import Comment, Post
from threadit_core.services.read_service import ReadService

from tests.fakes import FakeCommentRepo, FakePostRepo

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _svc() -> ReadService:
    return ReadService(
        posts=FakePostRepo(),
        comments=FakeCommentRepo(),
        default_limit=20,
        max_limit=100,
    )


def _post(pid: str, uid: str) -> Post:
    return Post(post_id=pid, user_id=uid, title="t", body="b", created_at=NOW, updated_at=NOW)


def test_get_missing_post_raises_not_found():
    svc = _svc()
    with pytest.raises(NotFoundError):
        svc.get_post("missing")


def test_get_existing_post():
    svc = _svc()
    svc.posts.put_post(_post("p1", "u1"))
    assert svc.get_post("p1").post_id == "p1"


def test_search_keyword_raises_501():
    svc = _svc()
    with pytest.raises(SearchNotAvailableError):
        svc.list_posts(search_keyword="hello")


def test_limit_is_clamped_to_max():
    svc = _svc()
    for i in range(5):
        svc.posts.put_post(_post(f"p{i}", "u1"))
    page = svc.list_posts(limit=10_000)
    assert len(page.items) <= 100


def test_list_by_user_filters():
    svc = _svc()
    svc.posts.put_post(_post("p1", "u1"))
    svc.posts.put_post(_post("p2", "u2"))
    page = svc.list_posts(user_id="u1")
    assert all(p.user_id == "u1" for p in page.items)


def test_comment_tree_vs_subtree():
    svc = _svc()
    top = Comment(
        comment_id="c1",
        post_id="p1",
        user_id="u1",
        text="t",
        created_at=NOW,
        depth=0,
        path="ts#c1",
        root_comment_id="c1",
        parent_id=None,
    )
    child = Comment(
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
    other = Comment(
        comment_id="c3",
        post_id="p1",
        user_id="u1",
        text="o",
        created_at=NOW,
        depth=0,
        path="ts#c3",
        root_comment_id="c3",
        parent_id=None,
    )
    for c in (top, child, other):
        svc.comments.put_comment(c)
    tree = svc.list_comments("p1")
    assert {c.comment_id for c in tree.items} == {"c1", "c2", "c3"}
    sub = svc.list_comments("p1", root_comment_id="c1")
    assert {c.comment_id for c in sub.items} == {"c1", "c2"}
