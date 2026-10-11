from __future__ import annotations

import base64
import json

import urllib3

from threadit_core.repositories.search_index import (
    PostDoc,
    SearchHit,
    SearchIndex,
    SearchPage,
)

_INDEX = "posts"


class OpenSearchIndex(SearchIndex):
    """Thin OpenSearch REST adapter (urllib3). Documents keyed by postId for idempotency.

    On real AWS, requests must be SigV4-signed (service "es"); on Floci they are unsigned.
    Signing is enabled via `sign=True` + region (config-driven, F11).
    """

    def __init__(
        self,
        endpoint: str,
        *,
        http: urllib3.PoolManager | None = None,
        sign: bool = False,
        region: str = "us-east-1",
    ) -> None:
        self._base = endpoint.rstrip("/")
        self._http = http or urllib3.PoolManager()
        self._ensured = False
        self._sign = sign
        self._region = region
        self._signer = None
        if sign:
            import boto3
            from botocore.auth import SigV4Auth

            creds = boto3.Session().get_credentials()
            self._signer = SigV4Auth(creds, "es", region)

    def _send(self, method: str, url: str, body_bytes: bytes | None) -> urllib3.BaseHTTPResponse:
        headers = {"Content-Type": "application/json"}
        if self._signer is not None:
            from botocore.awsrequest import AWSRequest

            aws_req = AWSRequest(method=method, url=url, data=body_bytes, headers=dict(headers))
            self._signer.add_auth(aws_req)
            headers = dict(aws_req.headers)
        return self._http.request(method, url, body=body_bytes, headers=headers)

    def _req(self, method: str, path: str, body: dict | None = None) -> dict:
        body_bytes = json.dumps(body).encode() if body is not None else None
        resp = self._send(method, f"{self._base}{path}", body_bytes)
        if resp.status >= 300 and resp.status != 404:
            raise RuntimeError(f"opensearch {method} {path} -> {resp.status}")
        return json.loads(resp.data) if resp.data else {}

    def _ensure_index(self) -> None:
        if self._ensured:
            return
        mapping = {
            "mappings": {
                "properties": {
                    "postId": {"type": "keyword"},
                    "userId": {"type": "keyword"},
                    "title": {"type": "text"},
                    "body": {"type": "text"},
                    "createdAt": {"type": "keyword"},
                }
            }
        }
        resp = self._send(
            "PUT", f"{self._base}/{_INDEX}", json.dumps(mapping).encode()
        )
        # 200 created, 400 already-exists (resource_already_exists_exception) are both fine.
        if resp.status not in (200, 400):
            raise RuntimeError(f"opensearch create index -> {resp.status}")
        self._ensured = True

    def upsert_post(self, doc: PostDoc) -> None:
        self._ensure_index()
        self._req(
            "PUT",
            f"/{_INDEX}/_doc/{doc.post_id}",
            {
                "postId": doc.post_id,
                "userId": doc.user_id,
                "title": doc.title,
                "body": doc.body,
                "createdAt": doc.created_at,
            },
        )

    def delete_post(self, post_id: str) -> None:
        self._req("DELETE", f"/{_INDEX}/_doc/{post_id}")

    def search_posts(self, keyword: str, *, limit: int, cursor: str | None) -> SearchPage:
        query = {
            "size": limit,
            "query": {"multi_match": {"query": keyword, "fields": ["title^2", "body"]}},
            "sort": [{"createdAt": "desc"}, {"postId": "desc"}],
        }
        after = _decode_cursor(cursor)
        if after is not None:
            query["search_after"] = after
        result = self._req("POST", f"/{_INDEX}/_search", query)
        hits = result.get("hits", {}).get("hits", [])
        out = tuple(
            SearchHit(
                post_id=h["_source"]["postId"],
                title=h["_source"]["title"],
                user_id=h["_source"]["userId"],
                created_at=h["_source"]["createdAt"],
            )
            for h in hits
        )
        next_cursor = _encode_cursor(hits[-1]["sort"]) if len(hits) == limit and hits else None
        return SearchPage(hits=out, next_cursor=next_cursor)


def _encode_cursor(sort_values: list) -> str:
    return base64.urlsafe_b64encode(json.dumps(sort_values).encode()).decode()


def _decode_cursor(cursor: str | None) -> list | None:
    if not cursor:
        return None
    try:
        return json.loads(base64.urlsafe_b64decode(cursor.encode()))
    except (ValueError, TypeError):
        return None
