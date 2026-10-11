from __future__ import annotations

import pytest
from threadit_core.repositories.presigner import AttachmentPresigner
from threadit_core.services.attachment_service import (
    AttachmentService,
    PayloadTooLargeError,
    UnsupportedMediaTypeError,
)


class FakePresigner(AttachmentPresigner):
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def presign_put(self, *, object_key: str, content_type: str, expires_in: int) -> str:
        self.calls.append({"key": object_key, "ct": content_type})
        return f"https://s3.example/{object_key}?sig=x"


def _svc(max_bytes: int = 5 * 1024 * 1024) -> AttachmentService:
    return AttachmentService(presigner=FakePresigner(), max_bytes=max_bytes, expires_in=300)


def test_presign_ok_returns_url_and_key():
    svc = _svc()
    out = svc.presign(user_id="u1", post_id="p1", content_type="image/png", size_bytes=1000)
    assert out.url.startswith("https://s3.example/")
    assert out.object_key.startswith("users/u1/posts/p1/")
    assert out.object_key.endswith(".png")
    assert out.expires_in == 300


def test_unsupported_type_rejected():
    svc = _svc()
    with pytest.raises(UnsupportedMediaTypeError):
        svc.presign(user_id="u1", post_id="p1", content_type="application/pdf", size_bytes=10)


def test_oversized_rejected():
    svc = _svc(max_bytes=100)
    with pytest.raises(PayloadTooLargeError):
        svc.presign(user_id="u1", post_id="p1", content_type="image/png", size_bytes=101)


def test_zero_size_rejected():
    svc = _svc()
    with pytest.raises(PayloadTooLargeError):
        svc.presign(user_id="u1", post_id="p1", content_type="image/png", size_bytes=0)


def test_key_is_per_user_scoped():
    svc = _svc()
    out = svc.presign(user_id="alice", post_id="p9", content_type="image/jpeg", size_bytes=5)
    assert out.object_key.startswith("users/alice/posts/p9/")
