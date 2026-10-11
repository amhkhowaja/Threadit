from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class Post:
    post_id: str
    user_id: str
    title: str
    body: str
    created_at: datetime
    updated_at: datetime
    schema_version: int = SCHEMA_VERSION


@dataclass(frozen=True, slots=True)
class Comment:
    comment_id: str
    post_id: str
    user_id: str
    text: str
    created_at: datetime
    depth: int
    path: str
    root_comment_id: str
    parent_id: str | None = None
    schema_version: int = SCHEMA_VERSION


@dataclass(frozen=True, slots=True)
class User:
    user_id: str
    display_name: str
    created_at: datetime
    schema_version: int = SCHEMA_VERSION


@dataclass(frozen=True, slots=True)
class Page:
    """A page of domain items plus an opaque forward cursor (None = end)."""

    items: tuple
    next_cursor: str | None
