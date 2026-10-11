from __future__ import annotations

from threadit_core.domain.models import Comment, Page, Post
from threadit_core.repositories.ports import (
    CommentReadRepository,
    CommentWriteRepository,
    IdempotencyStore,
    PostReadRepository,
    PostWriteRepository,
)


class FakePostRepo(PostWriteRepository, PostReadRepository):
    def __init__(self) -> None:
        self.posts: dict[str, Post] = {}

    def put_post(self, post: Post) -> None:
        self.posts[post.post_id] = post

    def get_post(self, post_id: str, *, consistent: bool = False) -> Post | None:
        return self.posts.get(post_id)

    def list_latest_posts(self, *, limit: int, cursor: str | None) -> Page:
        items = tuple(sorted(self.posts.values(), key=lambda p: p.created_at, reverse=True)[:limit])
        return Page(items=items, next_cursor=None)

    def list_user_posts(self, user_id: str, *, limit: int, cursor: str | None) -> Page:
        items = tuple(p for p in self.posts.values() if p.user_id == user_id)[:limit]
        return Page(items=items, next_cursor=None)


class FakeCommentRepo(CommentWriteRepository, CommentReadRepository):
    def __init__(self) -> None:
        self.comments: dict[tuple[str, str], Comment] = {}

    def put_comment(self, comment: Comment) -> None:
        self.comments[(comment.post_id, comment.comment_id)] = comment

    def get_comment(self, post_id: str, comment_id: str) -> Comment | None:
        return self.comments.get((post_id, comment_id))

    def get_comment_tree(self, post_id: str, *, limit: int, cursor: str | None) -> Page:
        matching = (c for c in self.comments.values() if c.post_id == post_id)
        items = tuple(sorted(matching, key=lambda c: c.path))[:limit]
        return Page(items=items, next_cursor=None)

    def get_comment_subtree(
        self, post_id: str, root_comment_id: str, *, limit: int, cursor: str | None
    ) -> Page:
        items = tuple(
            sorted(
                (
                    c
                    for c in self.comments.values()
                    if c.post_id == post_id and c.root_comment_id == root_comment_id
                ),
                key=lambda c: c.path,
            )
        )[:limit]
        return Page(items=items, next_cursor=None)


class FakeIdempotencyStore(IdempotencyStore):
    def __init__(self) -> None:
        self.claims: dict[str, str] = {}

    def try_claim(self, key: str, target_id: str) -> bool:
        if key in self.claims:
            return False
        self.claims[key] = target_id
        return True

    def resolve_target(self, key: str) -> str | None:
        return self.claims.get(key)
