from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from threadit_core.domain.errors import NotFoundError, ParentNotInPostError
from threadit_core.domain.models import Comment, Post
from threadit_core.repositories.keys import MaterializedPathBuilder
from threadit_core.repositories.ports import (
    CommentReadRepository,
    CommentWriteRepository,
    IdempotencyStore,
    PostWriteRepository,
)


def _now() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return uuid.uuid4().hex


@dataclass(slots=True)
class WriteService:
    posts: PostWriteRepository
    comments: CommentWriteRepository
    comment_reader: CommentReadRepository
    idempotency: IdempotencyStore
    path_builder: MaterializedPathBuilder

    def create_post(
        self,
        *,
        user_id: str,
        title: str,
        body: str,
        idempotency_key: str,
        image_key: str | None = None,
    ) -> Post:
        existing = self._replayed_target(idempotency_key)
        now = _now()
        post_id = existing or _new_id()
        post = Post(
            post_id=post_id,
            user_id=user_id,
            title=title,
            body=body,
            created_at=now,
            updated_at=now,
            image_key=image_key,
        )
        if existing is None and self.idempotency.try_claim(idempotency_key, post_id):
            self.posts.put_post(post)
        return post

    def create_comment(
        self,
        *,
        user_id: str,
        post_id: str,
        text: str,
        parent_id: str | None,
        idempotency_key: str,
    ) -> Comment:
        now = _now()
        comment_id = self._replayed_target(idempotency_key) or _new_id()

        if parent_id is None:
            path, depth, root = self.path_builder.top_level(now, comment_id)
        else:
            parent = self.comment_reader.get_comment(post_id, parent_id)
            if parent is None:
                raise NotFoundError("parent comment not found")
            if parent.post_id != post_id:
                raise ParentNotInPostError("parent belongs to a different post")
            path, depth, root = self.path_builder.child(
                parent.path, parent.depth, parent.root_comment_id, now, comment_id
            )

        comment = Comment(
            comment_id=comment_id,
            post_id=post_id,
            user_id=user_id,
            text=text,
            created_at=now,
            depth=depth,
            path=path,
            root_comment_id=root,
            parent_id=parent_id,
        )
        if self.idempotency.try_claim(idempotency_key, comment_id):
            self.comments.put_comment(comment)
        return comment

    def _replayed_target(self, idempotency_key: str) -> str | None:
        return self.idempotency.resolve_target(idempotency_key)
