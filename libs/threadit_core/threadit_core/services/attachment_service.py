from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from threadit_core.domain.errors import DomainError
from threadit_core.repositories.presigner import AttachmentPresigner, PresignedUpload

_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_EXT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}


class UnsupportedMediaTypeError(DomainError):
    status = 415
    error_type = "https://threadit/errors/unsupported-media-type"
    title = "Unsupported attachment type"


class PayloadTooLargeError(DomainError):
    status = 413
    error_type = "https://threadit/errors/payload-too-large"
    title = "Attachment too large"


@dataclass(slots=True)
class AttachmentService:
    presigner: AttachmentPresigner
    max_bytes: int = 5 * 1024 * 1024
    expires_in: int = 300
    allowed_types: frozenset[str] = field(default_factory=lambda: frozenset(_ALLOWED_TYPES))

    def presign(
        self, *, user_id: str, post_id: str, content_type: str, size_bytes: int
    ) -> PresignedUpload:
        self._validate(content_type, size_bytes)
        key = f"users/{user_id}/posts/{post_id}/{uuid.uuid4().hex}.{_EXT[content_type]}"
        return self._issue(key, content_type)

    def presign_draft(
        self, *, user_id: str, content_type: str, size_bytes: int
    ) -> PresignedUpload:
        # Used during compose, before a post exists; key is user-scoped under drafts/.
        self._validate(content_type, size_bytes)
        key = f"users/{user_id}/drafts/{uuid.uuid4().hex}.{_EXT[content_type]}"
        return self._issue(key, content_type)

    def _validate(self, content_type: str, size_bytes: int) -> None:
        if content_type not in self.allowed_types:
            allowed = sorted(self.allowed_types)
            raise UnsupportedMediaTypeError(f"content_type must be one of {allowed}")
        if size_bytes <= 0 or size_bytes > self.max_bytes:
            raise PayloadTooLargeError(f"size must be 1..{self.max_bytes} bytes")

    def _issue(self, key: str, content_type: str) -> PresignedUpload:
        url = self.presigner.presign_put(
            object_key=key, content_type=content_type, expires_in=self.expires_in
        )
        return PresignedUpload(url=url, object_key=key, expires_in=self.expires_in)
