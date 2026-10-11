from __future__ import annotations

import base64
import json

import pytest
from threadit_core.domain.errors import InvalidCursorError
from threadit_core.repositories.cursor import CursorCodec


def test_roundtrip():
    lek = {"PK": "POST#1", "SK": "META#1"}
    cur = CursorCodec.encode(lek)
    assert CursorCodec.decode(cur) == lek


def test_encode_none_is_none():
    assert CursorCodec.encode(None) is None
    assert CursorCodec.encode({}) is None


def test_decode_empty_is_none():
    assert CursorCodec.decode(None) is None
    assert CursorCodec.decode("") is None


def test_decode_garbage_raises():
    with pytest.raises(InvalidCursorError):
        CursorCodec.decode("!!!not base64!!!")


def test_decode_rejects_unknown_key_name():
    forged = base64.urlsafe_b64encode(json.dumps({"EVIL": "x"}).encode()).decode()
    with pytest.raises(InvalidCursorError):
        CursorCodec.decode(forged)


def test_decode_rejects_oversized():
    big = base64.urlsafe_b64encode(json.dumps({"PK": "x" * 5000}).encode()).decode()
    with pytest.raises(InvalidCursorError):
        CursorCodec.decode(big)
