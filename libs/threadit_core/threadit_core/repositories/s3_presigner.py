from __future__ import annotations

import boto3
from botocore.config import Config

from threadit_core.repositories.presigner import AttachmentPresigner


def build_s3_client(*, region: str, endpoint_url: str | None):
    # On real AWS, pin the REGIONAL endpoint + SigV4 virtual-hosted addressing so
    # presigned URLs target `<bucket>.s3.<region>.amazonaws.com`. Without this, boto3
    # can emit the legacy global host `<bucket>.s3.amazonaws.com`, which answers a
    # 307 redirect for PUTs to in-region buckets — and browsers don't follow 307 on a
    # PUT body (and CORS doesn't apply to the redirect), so uploads fail.
    # On Floci (endpoint_url set), keep path-style addressing.
    if endpoint_url:
        return boto3.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint_url,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )
    return boto3.client(
        "s3",
        region_name=region,
        endpoint_url=f"https://s3.{region}.amazonaws.com",
        config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
    )


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

    def presign_get(self, *, object_key: str, expires_in: int) -> str:
        return self._c.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": self._bucket, "Key": object_key},
            ExpiresIn=expires_in,
        )
