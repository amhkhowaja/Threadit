from __future__ import annotations

from abc import ABC, abstractmethod

from threadit_core.domain.models import Comment, Page, Post


class PostWriteRepository(ABC):
    @abstractmethod
    def put_post(self, post: Post) -> None: ...


class PostReadRepository(ABC):
    @abstractmethod
    def get_post(self, post_id: str, *, consistent: bool = False) -> Post | None: ...

    @abstractmethod
    def list_latest_posts(self, *, limit: int, cursor: str | None) -> Page: ...

    @abstractmethod
    def list_user_posts(self, user_id: str, *, limit: int, cursor: str | None) -> Page: ...


class CommentWriteRepository(ABC):
    @abstractmethod
    def put_comment(self, comment: Comment) -> None: ...


class CommentReadRepository(ABC):
    @abstractmethod
    def get_comment_tree(self, post_id: str, *, limit: int, cursor: str | None) -> Page: ...

    @abstractmethod
    def get_comment_subtree(
        self, post_id: str, root_comment_id: str, *, limit: int, cursor: str | None
    ) -> Page: ...

    @abstractmethod
    def get_comment(self, post_id: str, comment_id: str) -> Comment | None: ...


class IdempotencyStore(ABC):
    @abstractmethod
    def try_claim(self, key: str, target_id: str) -> bool:
        """Return True if claimed first time; False on replay (key already present)."""

    @abstractmethod
    def resolve_target(self, key: str) -> str | None: ...
