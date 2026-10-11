from __future__ import annotations

import pytest
from threadit_core.domain.errors import MaxDepthExceeded, NotFoundError
from threadit_core.repositories.keys import MaterializedPathBuilder
from threadit_core.services.write_service import WriteService

from tests.fakes import FakeCommentRepo, FakeIdempotencyStore, FakePostRepo


def _svc(max_depth: int = 8) -> WriteService:
    posts = FakePostRepo()
    comments = FakeCommentRepo()
    return WriteService(
        posts=posts,
        comments=comments,
        comment_reader=comments,
        idempotency=FakeIdempotencyStore(),
        path_builder=MaterializedPathBuilder(max_depth=max_depth),
    )


def test_create_post_persists_with_caller_user_id():
    svc = _svc()
    post = svc.create_post(user_id="u1", title="t", body="b", idempotency_key="k1")
    assert post.user_id == "u1"
    assert svc.posts.posts[post.post_id].user_id == "u1"


def test_create_post_idempotent_replay_returns_same_id_no_duplicate():
    svc = _svc()
    p1 = svc.create_post(user_id="u1", title="t", body="b", idempotency_key="k1")
    p2 = svc.create_post(user_id="u1", title="t", body="b", idempotency_key="k1")
    assert p1.post_id == p2.post_id
    assert len(svc.posts.posts) == 1


def test_top_level_comment_depth_zero():
    svc = _svc()
    post = svc.create_post(user_id="u1", title="t", body="b", idempotency_key="kp")
    c = svc.create_comment(
        user_id="u2", post_id=post.post_id, text="hi", parent_id=None, idempotency_key="kc"
    )
    assert c.depth == 0
    assert c.root_comment_id == c.comment_id
    assert c.user_id == "u2"


def test_reply_increments_depth_and_keeps_root():
    svc = _svc()
    post = svc.create_post(user_id="u1", title="t", body="b", idempotency_key="kp")
    top = svc.create_comment(
        user_id="u1", post_id=post.post_id, text="t", parent_id=None, idempotency_key="k0"
    )
    child = svc.create_comment(
        user_id="u1",
        post_id=post.post_id,
        text="r",
        parent_id=top.comment_id,
        idempotency_key="k1",
    )
    assert child.depth == 1
    assert child.root_comment_id == top.comment_id


def test_depth_cap_rejects_ninth_level():
    svc = _svc(max_depth=2)
    post = svc.create_post(user_id="u1", title="t", body="b", idempotency_key="kp")
    parent = svc.create_comment(
        user_id="u1", post_id=post.post_id, text="t", parent_id=None, idempotency_key="k0"
    )
    for i in range(1, 3):
        parent = svc.create_comment(
            user_id="u1",
            post_id=post.post_id,
            text="r",
            parent_id=parent.comment_id,
            idempotency_key=f"k{i}",
        )
    with pytest.raises(MaxDepthExceeded):
        svc.create_comment(
            user_id="u1",
            post_id=post.post_id,
            text="too deep",
            parent_id=parent.comment_id,
            idempotency_key="kx",
        )


def test_reply_to_parent_in_other_post_not_found():
    # Comments are stored under PK=POST#<postId>, so a parent from another post
    # cannot be found when scoped to this post -> NotFoundError (the real behavior).
    svc = _svc()
    p_a = svc.create_post(user_id="u1", title="a", body="b", idempotency_key="ka")
    p_b = svc.create_post(user_id="u1", title="b", body="b", idempotency_key="kb")
    parent = svc.create_comment(
        user_id="u1", post_id=p_a.post_id, text="t", parent_id=None, idempotency_key="k0"
    )
    with pytest.raises(NotFoundError):
        svc.create_comment(
            user_id="u1",
            post_id=p_b.post_id,
            text="x",
            parent_id=parent.comment_id,
            idempotency_key="k1",
        )
