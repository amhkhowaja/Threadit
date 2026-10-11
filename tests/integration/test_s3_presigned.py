from __future__ import annotations

import os
import uuid

import boto3
import pytest
import urllib3

from threadit_core.repositories.s3_presigner import S3AttachmentPresigner
from threadit_core.services.attachment_service import AttachmentService

pytestmark = pytest.mark.integration

ENDPOINT = os.environ.get("THREADIT_AWS_ENDPOINT_URL", "http://localhost:4566")
REGION = "us-east-1"


@pytest.fixture()
def bucket():
    name = f"threadit-it-img-{uuid.uuid4().hex[:8]}"
    c = boto3.client("s3", endpoint_url=ENDPOINT, region_name=REGION)
    c.create_bucket(Bucket=name)
    yield name
    objs = c.list_objects_v2(Bucket=name).get("Contents", [])
    for o in objs:
        c.delete_object(Bucket=name, Key=o["Key"])
    c.delete_bucket(Bucket=name)


def test_presigned_put_uploads_object(bucket):
    client = boto3.client("s3", endpoint_url=ENDPOINT, region_name=REGION)
    svc = AttachmentService(presigner=S3AttachmentPresigner(client, bucket))

    out = svc.presign(user_id="u1", post_id="p1", content_type="image/png", size_bytes=10)

    http = urllib3.PoolManager()
    resp = http.request(
        "PUT", out.url, body=b"\x89PNG\r\n\x1a\n", headers={"Content-Type": "image/png"}
    )
    assert resp.status in (200, 204), resp.status

    head = client.head_object(Bucket=bucket, Key=out.object_key)
    assert head["ResponseMetadata"]["HTTPStatusCode"] == 200
