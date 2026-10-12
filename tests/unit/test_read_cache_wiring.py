from __future__ import annotations

from datetime import UTC, datetime

import pytest
from threadit_core.domain.errors import NotFoundError
from threadit_core.domain.models import Post
from threadit_core.services.cache import SingleFlightCache
from threadit_core.services.read_service import ReadService

from tests.fakes import FakeCommentRepo

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _post(pid: str, uid: str = "u1") -> Post:
    return Post(post_id=pid, user_id=uid, title="t", body="b", created_at=NOW, updated_at=NOW)


class CountingPostRepo:
    """Repo that counts how many times the backing store is actually hit."""

    def __init__(self):
        self.store: dict[str, Post] = {}
        self.get_calls = 0

    def put_post(self, post: Post) -> None:
        self.store[post.post_id] = post

    def get_post(self, post_id: str, *, consistent: bool = False) -> Post | None:
        self.get_calls += 1
        return self.store.get(post_id)

    def list_latest_posts(self, *, limit, cursor):  # unused here
        from threadit_core.domain.models import Page

        return Page(items=(), next_cursor=None)

    def list_user_posts(self, user_id, *, limit, cursor):
        from threadit_core.domain.models import Page

        return Page(items=(), next_cursor=None)


def _svc(repo, cache=None):
    return ReadService(
        posts=repo, comments=FakeCommentRepo(), default_limit=20, max_limit=100, post_cache=cache
    )


# --- contract -------------------------------------------------------------------


def test_cache_collapses_repeated_reads_to_one_load():
    repo = CountingPostRepo()
    repo.put_post(_post("p1"))
    svc = _svc(repo, cache=SingleFlightCache(ttl=10))
    for _ in range(5):
        assert svc.get_post("p1").post_id == "p1"
    assert repo.get_calls == 1  # 5 reads, 1 backend hit (cached)


def test_consistent_read_bypasses_cache():
    repo = CountingPostRepo()
    repo.put_post(_post("p1"))
    svc = _svc(repo, cache=SingleFlightCache(ttl=10))
    svc.get_post("p1")  # warms cache (1 hit)
    svc.get_post("p1", consistent=True)  # must bypass -> another hit
    svc.get_post("p1", consistent=True)
    assert repo.get_calls == 3  # 1 cached warm + 2 consistent passthroughs


def test_without_cache_every_read_hits_repo():
    repo = CountingPostRepo()
    repo.put_post(_post("p1"))
    svc = _svc(repo, cache=None)
    for _ in range(3):
        svc.get_post("p1")
    assert repo.get_calls == 3


def test_missing_post_raises_not_found_through_cache():
    repo = CountingPostRepo()
    svc = _svc(repo, cache=SingleFlightCache(ttl=10))
    with pytest.raises(NotFoundError):
        svc.get_post("nope")
