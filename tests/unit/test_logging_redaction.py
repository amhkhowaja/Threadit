from __future__ import annotations

from threadit_core.logging import redact_processor


def test_denylisted_keys_are_masked():
    out = redact_processor(None, "", {"authorization": "Bearer abc", "token": "x", "ok": "keep"})
    assert out["authorization"] == "***REDACTED***"
    assert out["token"] == "***REDACTED***"
    assert out["ok"] == "keep"


def test_bearer_pattern_masked_in_free_text():
    out = redact_processor(None, "", {"event": "called with Bearer eyJabc.def.ghi token"})
    assert "Bearer eyJabc.def.ghi" not in out["event"]
    assert "***REDACTED***" in out["event"]


def test_jwt_pattern_masked():
    out = redact_processor(None, "", {"msg": "eyJhbGciOiJItesttesttest.payload.sig"})
    assert "***REDACTED***" in out["msg"]


def test_nested_dict_redacted():
    out = redact_processor(None, "", {"ctx": {"idempotency-key": "k", "n": 1}})
    assert out["ctx"]["idempotency-key"] == "***REDACTED***"
    assert out["ctx"]["n"] == 1
