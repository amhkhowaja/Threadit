from __future__ import annotations

import boto3

from threadit_core.repositories.presigner import AttachmentPresigner


def build_s3_client(*, region: str, endpoint_url: str | None):
    return boto3.client("s3", region_name=region, endpoint_url=endpoint_url)


class S3AttachmentPresigner(AttachmentPresigner):
    def __init__(self, client, bucket: str) -> None:
        self._c = client
        self._bucket = bucket

    def presign_put(self, *, object_key: str, content_type: str, expires_in: int) -> str:
        return self._c.generate_presigned_url(
            ClientMethod="put_object",
            Params={"Bucket": self._bucket, "Key": object_key, "ContentType": content_type},
            ExpiresIn=expires_in,
        )
