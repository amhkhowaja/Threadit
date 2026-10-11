from __future__ import annotations

from threadit_core.repositories.presigner import AttachmentPresigner


class ImageUrlResolver:
    """Resolves a stored image key to a viewable URL.

    Prod: CloudFront domain + key (served via OAC from the private bucket).
    Local/dev: short-lived presigned S3 GET.
    """

    def __init__(
        self,
        *,
        cloudfront_domain: str = "",
        presigner: AttachmentPresigner | None = None,
        get_ttl: int = 3600,
    ) -> None:
        self._cf = cloudfront_domain.rstrip("/")
        self._presigner = presigner
        self._ttl = get_ttl

    def url_for(self, image_key: str | None) -> str | None:
        if not image_key:
            return None
        if self._cf:
            return f"https://{self._cf}/{image_key}"
        if self._presigner is not None:
            return self._presigner.presign_get(object_key=image_key, expires_in=self._ttl)
        return None
