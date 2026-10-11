from __future__ import annotations

import os
import time
import uuid

import boto3
import pytest
import urllib3
from threadit_core.repositories.opensearch import OpenSearchIndex
from threadit_core.repositories.search_index import PostDoc

pytestmark = pytest.mark.integration

ENDPOINT = os.environ.get("THREADIT_AWS_ENDPOINT_URL", "http://localhost:4566")
REGION = "us-east-1"


def _os_endpoint() -> str:
    c = boto3.client("opensearch", endpoint_url=ENDPOINT, region_name=REGION)
    name = "threadit-probe"
    try:
        c.create_domain(DomainName=name, EngineVersion="OpenSearch_2.11")
    except c.exceptions.ResourceAlreadyExistsException:
        pass
    for _ in range(30):
        d = c.describe_domain(DomainName=name)["DomainStatus"]
        if d.get("Created") and d.get("Endpoint"):
            ep = d["Endpoint"]
            return ep if ep.startswith("http") else f"http://{ep}"
        time.sleep(2)
    pytest.skip("OpenSearch domain not ready")


@pytest.fixture(scope="module")
def index():
    ep = _os_endpoint()
    http = urllib3.PoolManager()
    # wait for the engine to accept requests
    for _ in range(30):
        try:
            if http.request("GET", ep, timeout=3.0).status == 200:
                break
        except Exception:  # noqa: BLE001
            time.sleep(2)
    return OpenSearchIndex(ep, http=http)


def _doc(pid: str, title: str) -> PostDoc:
    return PostDoc(
        post_id=pid,
        user_id="u1",
        title=title,
        body="hello world",
        created_at="2026-01-01T00:00:00Z",
    )


def test_upsert_search_delete(index):
    pid = f"p-{uuid.uuid4().hex[:8]}"
    index.upsert_post(_doc(pid, "unicorn gardening tips"))
    time.sleep(2)  # refresh lag

    page = index.search_posts("unicorn", limit=10, cursor=None)
    assert any(h.post_id == pid for h in page.hits)

    index.delete_post(pid)
    time.sleep(2)
    page2 = index.search_posts("unicorn", limit=10, cursor=None)
    assert all(h.post_id != pid for h in page2.hits)
