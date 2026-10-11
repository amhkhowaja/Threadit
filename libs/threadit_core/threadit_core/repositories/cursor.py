from __future__ import annotations

import base64
import json
import re
from typing import Any

from threadit_core.domain.errors import InvalidCursorError

_MAX_CURSOR_BYTES = 2048
_ALLOWED_KEY_NAMES = frozenset({"PK", "SK", "GSI1PK", "GSI1SK", "GSI2PK", "GSI2SK", "_b"})
_B64URL_RE = re.compile(r"^[A-Za-z0-9_-]+={0,2}$")


class CursorCodec:
    """Opaque forward-only cursor: base64url(JSON of a DynamoDB LastEvaluatedKey).

    Decoding is defensive (I7): strict base64, bounded size, and a key-name allow-list
    so a forged cursor cannot pivot the query to another partition/entity.
    """

    @staticmethod
    def encode(last_evaluated_key: dict[str, Any] | None) -> str | None:
        if not last_evaluated_key:
            return None
        raw = json.dumps(last_evaluated_key, separators=(",", ":"), sort_keys=True).encode()
        return base64.urlsafe_b64encode(raw).decode()

    @staticmethod
    def decode(cursor: str | None) -> dict[str, Any] | None:
        if cursor is None or cursor == "":
            return None
        if len(cursor) > _MAX_CURSOR_BYTES:
            raise InvalidCursorError("cursor too large")
        if not _B64URL_RE.match(cursor):
            raise InvalidCursorError("cursor is not valid base64url")
        try:
            raw = base64.urlsafe_b64decode(cursor.encode())
            data = json.loads(raw)
        except (ValueError, TypeError) as exc:
            raise InvalidCursorError("cursor is not valid base64url JSON") from exc
        if not isinstance(data, dict) or not data:
            raise InvalidCursorError("cursor must decode to a non-empty object")
        for key in data:
            if key not in _ALLOWED_KEY_NAMES:
                raise InvalidCursorError("cursor contains an unexpected key")
            if not isinstance(data[key], str | int):
                raise InvalidCursorError("cursor value has an unexpected type")
        return data
