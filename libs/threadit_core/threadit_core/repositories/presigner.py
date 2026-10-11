from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PresignedUpload:
    url: str
    object_key: str
    expires_in: int


class AttachmentPresigner(ABC):
    @abstractmethod
    def presign_put(self, *, object_key: str, content_type: str, expires_in: int) -> str:
        """Return a presigned S3 PUT URL for object_key."""

    @abstractmethod
    def presign_get(self, *, object_key: str, expires_in: int) -> str:
        """Return a presigned S3 GET URL for object_key (viewable image)."""
