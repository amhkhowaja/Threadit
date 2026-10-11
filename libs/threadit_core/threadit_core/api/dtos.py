from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from threadit_core.domain.author import author_handle
from threadit_core.domain.models import Comment, Post

_MAX_TITLE = 300
_MAX_BODY = 40_000
_MAX_TEXT = 10_000


class CreatePostRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=_MAX_TITLE)
    body: str = Field(min_length=1, max_length=_MAX_BODY)
    imageKey: str | None = Field(default=None, max_length=256)


class CreateCommentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=_MAX_TEXT)
    parentId: str | None = Field(default=None, max_length=64)


class PostResponse(BaseModel):
    id: str
    userId: str
    authorName: str
    title: str
    body: str
    imageUrl: str | None = None
    createdAt: str
    updatedAt: str

    @classmethod
    def of(cls, p: Post, image_url: str | None = None) -> PostResponse:
        return cls(
            id=p.post_id,
            userId=p.user_id,
            authorName=author_handle(p.user_id),
            title=p.title,
            body=p.body,
            imageUrl=image_url,
            createdAt=p.created_at.isoformat(),
            updatedAt=p.updated_at.isoformat(),
        )

    @classmethod
    def of_hit(cls, h) -> PostResponse:
        return cls(
            id=h.post_id,
            userId=h.user_id,
            authorName=author_handle(h.user_id),
            title=h.title,
            body="",
            imageUrl=None,
            createdAt=h.created_at,
            updatedAt=h.created_at,
        )


class CommentResponse(BaseModel):
    id: str
    postId: str
    userId: str
    authorName: str
    text: str
    depth: int
    parentId: str | None
    rootCommentId: str
    createdAt: str

    @classmethod
    def of(cls, c: Comment) -> CommentResponse:
        return cls(
            id=c.comment_id,
            postId=c.post_id,
            userId=c.user_id,
            authorName=author_handle(c.user_id),
            text=c.text,
            depth=c.depth,
            parentId=c.parent_id,
            rootCommentId=c.root_comment_id,
            createdAt=c.created_at.isoformat(),
        )


class PageResponse(BaseModel):
    items: list
    nextCursor: str | None
    limit: int


class PresignRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    contentType: str = Field(min_length=1, max_length=128)
    sizeBytes: int = Field(gt=0)


class PresignResponse(BaseModel):
    url: str
    objectKey: str
    expiresIn: int
