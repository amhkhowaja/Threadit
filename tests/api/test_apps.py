from __future__ import annotations

import importlib

from fastapi.testclient import TestClient
from threadit_core.repositories.keys import MaterializedPathBuilder
from threadit_core.services.read_service import ReadService
from threadit_core.services.write_service import WriteService

from tests.fakes import FakeCommentRepo, FakeIdempotencyStore, FakePostRepo

write_app = importlib.import_module("services.post_write.app")
read_app = importlib.import_module("services.post_read.app")

UID = "11111111-1111-1111-1111-111111111111"
IDEM = "22222222-2222-2222-2222-222222222222"


def _wire():
    posts = FakePostRepo()
    comments = FakeCommentRepo()
    write = WriteService(
        posts=posts,
        comments=comments,
        comment_reader=comments,
        idempotency=FakeIdempotencyStore(),
        path_builder=MaterializedPathBuilder(max_depth=8),
    )
    read = ReadService(posts=posts, comments=comments, default_limit=20, max_limit=100)
    return write, read


def _write_client(write: WriteService) -> TestClient:
    app = write_app.create_app()
    app.dependency_overrides[write_app.require_user_id] = lambda: UID
    app.dependency_overrides[write_app.enforce_rate_limit] = lambda: UID
    app.state.write_service = write
    app.state.attachment_service = None
    return TestClient(app)


def _read_client(read: ReadService) -> TestClient:
    from threadit_core.services.image_url import ImageUrlResolver

    app = read_app.create_app()
    app.state.read_service = read
    app.state.image_resolver = ImageUrlResolver()
    return TestClient(app)


def test_create_post_sets_user_from_identity_not_body():
    write, _ = _wire()
    c = _write_client(write)
    # body attempts to smuggle userId -> must be rejected (extra=forbid)
    r = c.post(
        "/v1/posts",
        json={"title": "hello", "body": "world", "userId": "attacker"},
        headers={"Idempotency-Key": IDEM},
    )
    assert r.status_code == 400  # mass-assignment rejected


def test_create_post_ok():
    write, _ = _wire()
    c = _write_client(write)
    r = c.post(
        "/v1/posts",
        json={"title": "hello", "body": "world"},
        headers={"Idempotency-Key": IDEM},
    )
    assert r.status_code == 201
    assert r.json()["userId"] == UID


def test_missing_idempotency_key_rejected():
    write, _ = _wire()
    c = _write_client(write)
    r = c.post("/v1/posts", json={"title": "t", "body": "b"})
    assert r.status_code in (400, 422)


def test_search_keyword_returns_501():
    _, read = _wire()
    c = _read_client(read)
    r = c.get("/v1/posts", params={"search_keyword": "x"})
    assert r.status_code == 501
    assert r.headers["content-type"].startswith("application/problem+json")


def test_get_missing_post_404_problem_json():
    _, read = _wire()
    c = _read_client(read)
    r = c.get("/v1/posts/nope")
    assert r.status_code == 404
    body = r.json()
    assert body["status"] == 404
    assert "correlationId" in body


def test_rate_limit_returns_429_with_retry_after():
    import uuid

    from threadit_core.services.rate_limit import InMemoryRateLimiter

    write, _ = _wire()
    app = write_app.create_app()
    app.dependency_overrides[write_app.require_user_id] = lambda: UID
    app.state.write_service = write
    app.state.attachment_service = None
    app.state.rate_limiter = InMemoryRateLimiter()
    app.state.rate_limit = 2
    app.state.rate_window = 60
    c = TestClient(app)

    def _post():
        return c.post(
            "/v1/posts",
            json={"title": "a", "body": "b"},
            headers={"Idempotency-Key": str(uuid.uuid4())},
        )

    assert _post().status_code == 201
    assert _post().status_code == 201
    blocked = _post()
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0


def test_create_then_read_roundtrip_with_threaded_reply():
    write, read = _wire()
    wc = _write_client(write)
    rc = _read_client(read)
    pid = wc.post(
        "/v1/posts", json={"title": "t", "body": "b"}, headers={"Idempotency-Key": IDEM}
    ).json()["id"]
    top = wc.post(
        f"/v1/posts/{pid}/comments",
        json={"text": "top"},
        headers={"Idempotency-Key": "33333333-3333-3333-3333-333333333333"},
    ).json()
    wc.post(
        f"/v1/posts/{pid}/comments",
        json={"text": "reply", "parentId": top["id"]},
        headers={"Idempotency-Key": "44444444-4444-4444-4444-444444444444"},
    )
    tree = rc.get(f"/v1/posts/{pid}/comments").json()
    depths = sorted(c["depth"] for c in tree["items"])
    assert depths == [0, 1]
