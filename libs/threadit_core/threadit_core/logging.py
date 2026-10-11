from __future__ import annotations

import contextvars
import logging
import re
import uuid
from typing import Any

import structlog

_correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="")

_DENY_KEYS = frozenset(
    {
        "authorization",
        "token",
        "access_token",
        "refresh_token",
        "id_token",
        "jwt",
        "bearer",
        "password",
        "secret",
        "apikey",
        "api_key",
        "cookie",
        "set-cookie",
        "idempotency-key",
        "idempotency_key",
    }
)
_BEARER_RE = re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]+")
_JWT_RE = re.compile(r"eyJ[A-Za-z0-9._\-]{10,}")
_MASK = "***REDACTED***"


def set_correlation_id(value: str | None) -> str:
    cid = value or str(uuid.uuid4())
    _correlation_id.set(cid)
    return cid


def get_correlation_id() -> str:
    return _correlation_id.get()


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        value = _BEARER_RE.sub(_MASK, value)
        value = _JWT_RE.sub(_MASK, value)
        return value
    if isinstance(value, dict):
        return {
            k: (_MASK if k.lower() in _DENY_KEYS else _redact_value(v)) for k, v in value.items()
        }
    if isinstance(value, list | tuple):
        return type(value)(_redact_value(v) for v in value)
    return value


def redact_processor(_logger: Any, _name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    return {
        k: (_MASK if k.lower() in _DENY_KEYS else _redact_value(v)) for k, v in event_dict.items()
    }


def _correlation_processor(_logger: Any, _name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    cid = get_correlation_id()
    if cid:
        event_dict.setdefault("correlationId", cid)
    return event_dict


def configure_logging(level: str = "INFO") -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            _correlation_processor,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            redact_processor,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level.upper())),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
