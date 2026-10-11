from __future__ import annotations

import time
import uuid

import pytest
import urllib3

from tests.integration.test_opensearch import _os_endpoint
from threadit_core.repositories.opensearch import OpenSearchIndex
from threadit_core.services.stream_indexer import StreamIndexer

pytestmark = pytest.mark.integration


def _insert_record(pid: str, title: str) -> dict:
    return {
        "eventName": "INSERT",
        "dynamodb": {
            "NewImage": {
                "entityType": {"S": "Post"},
                "postId": {"S": pid},
                "userId": {"S": "u1"},
                "title": {"S": title},
                "body": {"S": "indexed via stream"},
                "createdAt": {"S": "2026-02-02T00:00:00+00:00"},
            }
        },
    }


def test_indexer_stream_to_search_end_to_end():
    index = OpenSearchIndex(_os_endpoint(), http=urllib3.PoolManager())
    indexer = StreamIndexer(index)

    pid = f"p-{uuid.uuid4().hex[:8]}"
    processed = indexer.handle_records([_insert_record(pid, "dragon husbandry quarterly")])
    assert processed == 1

    time.sleep(2)
    page = index.search_posts("dragon", limit=10, cursor=None)
    assert any(h.post_id == pid for h in page.hits)

    # REMOVE should delete from the index
    remove_rec = {
        "eventName": "REMOVE",
        "dynamodb": {"OldImage": {"entityType": {"S": "Post"}, "postId": {"S": pid}}},
    }
    indexer.handle_records([remove_rec])
    time.sleep(2)
    page2 = index.search_posts("dragon", limit=10, cursor=None)
    assert all(h.post_id != pid for h in page2.hits)
