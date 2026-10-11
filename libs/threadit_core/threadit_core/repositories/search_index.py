from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PostDoc:
    post_id: str
    user_id: str
    title: str
    body: str
    created_at: str


@dataclass(frozen=True, slots=True)
class SearchHit:
    post_id: str
    title: str
    user_id: str
    created_at: str


@dataclass(frozen=True, slots=True)
class SearchPage:
    hits: tuple[SearchHit, ...]
    next_cursor: str | None


class SearchIndex(ABC):
    @abstractmethod
    def upsert_post(self, doc: PostDoc) -> None: ...

    @abstractmethod
    def delete_post(self, post_id: str) -> None: ...

    @abstractmethod
    def search_posts(self, keyword: str, *, limit: int, cursor: str | None) -> SearchPage: ...
