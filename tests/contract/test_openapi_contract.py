from __future__ import annotations

import json
from pathlib import Path

from tools.gen_openapi import build_spec

_SPEC = Path(__file__).resolve().parents[2] / "openapi" / "v1.json"


def test_committed_spec_matches_generated():
    committed = json.loads(_SPEC.read_text())
    generated = json.loads(json.dumps(build_spec(), sort_keys=True))
    assert generated == committed, "OpenAPI drift: run `make openapi` and commit openapi/v1.json"


def test_contract_has_all_v1_endpoints():
    spec = json.loads(_SPEC.read_text())
    paths = spec["paths"]
    assert "post" in paths["/v1/posts"]
    assert "get" in paths["/v1/posts"]
    assert "post" in paths["/v1/posts/{post_id}/comments"]
    assert "get" in paths["/v1/posts/{post_id}/comments"]
    assert "get" in paths["/v1/posts/{post_id}"]


def test_create_requests_forbid_extra_fields():
    spec = json.loads(_SPEC.read_text())
    for schema_name in ("CreatePostRequest", "CreateCommentRequest"):
        schema = spec["components"]["schemas"][schema_name]
        assert schema.get("additionalProperties") is False, schema_name
