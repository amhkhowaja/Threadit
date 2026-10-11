from __future__ import annotations

import json
from unittest import mock

from threadit_core.repositories.opensearch import OpenSearchIndex
from threadit_core.repositories.search_index import PostDoc


class _Resp:
    status = 200
    data = json.dumps({"hits": {"hits": []}}).encode()


class _CapturingHttp:
    def __init__(self):
        self.last_headers = None

    def request(self, method, url, body=None, headers=None):
        self.last_headers = headers or {}
        return _Resp()


def test_unsigned_has_no_authorization_header():
    http = _CapturingHttp()
    idx = OpenSearchIndex("http://localhost:4566", http=http, sign=False)
    idx.upsert_post(PostDoc("p1", "u1", "t", "b", "2026-01-01"))
    assert "Authorization" not in (http.last_headers or {})


def test_signed_adds_sigv4_authorization_header():
    http = _CapturingHttp()
    with mock.patch("boto3.Session") as sess:
        sess.return_value.get_credentials.return_value = mock.Mock(
            access_key="AKIA", secret_key="secret", token=None
        )
        idx = OpenSearchIndex("https://search.example", http=http, sign=True, region="us-east-1")
        idx.upsert_post(PostDoc("p1", "u1", "t", "b", "2026-01-01"))
    auth = (http.last_headers or {}).get("Authorization", "")
    assert auth.startswith("AWS4-HMAC-SHA256")
