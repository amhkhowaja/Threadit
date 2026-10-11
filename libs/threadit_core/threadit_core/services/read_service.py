from __future__ import annotations

from dataclasses import dataclass

from threadit_core.domain.errors import DomainError, NotFoundError, SearchNotAvailableError
from threadit_core.domain.models import Page, Post
from threadit_core.repositories.ports import CommentReadRepository, PostReadRepository
from threadit_core.repositories.search_index import SearchIndex


class SearchDegradedError(DomainError):
    status = 503
    error_type = "https://threadit/errors/search-degraded"
    title = "Search temporarily unavailable"
    retryable = True


@dataclass(slots=True)
class ReadService:
    posts: PostReadRepository
    comments: CommentReadRepository
    default_limit: int = 20
    max_limit: int = 100
    search: SearchIndex | None = None

    def _clamp(self, limit: int | None) -> int:
        if limit is None:
            return self.default_limit
        return max(1, min(limit, self.max_limit))

    def get_post(self, post_id: str, *, consistent: bool = False) -> Post:
        post = self.posts.get_post(post_id, consistent=consistent)
        if post is None:
            raise NotFoundError("post not found")
        return post

    def list_posts(
        self,
        *,
        user_id: str | None = None,
        search_keyword: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> Page:
        n = self._clamp(limit)
        if search_keyword:
            return self._search(search_keyword, limit=n, cursor=cursor)
        if user_id:
            return self.posts.list_user_posts(user_id, limit=n, cursor=cursor)
        return self.posts.list_latest_posts(limit=n, cursor=cursor)

    def _search(self, keyword: str, *, limit: int, cursor: str | None) -> Page:
        if self.search is None:
            raise SearchNotAvailableError("search is not available in this phase")
        try:
            result = self.search.search_posts(keyword, limit=limit, cursor=cursor)
        except Exception as exc:  # noqa: BLE001 - degrade search only, never other reads
            raise SearchDegradedError("search backend unavailable") from exc
        return Page(items=tuple(result.hits), next_cursor=result.next_cursor)

    def list_comments(
        self,
        post_id: str,
        *,
        root_comment_id: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> Page:
        n = self._clamp(limit)
        if root_comment_id:
            return self.comments.get_comment_subtree(
                post_id, root_comment_id, limit=n, cursor=cursor
            )
        return self.comments.get_comment_tree(post_id, limit=n, cursor=cursor)
