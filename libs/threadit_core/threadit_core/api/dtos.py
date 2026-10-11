from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from threadit_core.domain.models import Comment, Post

_MAX_TITLE = 300
_MAX_BODY = 40_000
_MAX_TEXT = 10_000


class CreatePostRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=_MAX_TITLE)
    body: str = Field(min_length=1, max_length=_MAX_BODY)


class CreateCommentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=_MAX_TEXT)
    parentId: str | None = Field(default=None, max_length=64)


class PostResponse(BaseModel):
    id: str
    userId: str
    title: str
    body: str
    createdAt: str
    updatedAt: str

    @classmethod
    def of(cls, p: Post) -> PostResponse:
        return cls(
            id=p.post_id,
            userId=p.user_id,
            title=p.title,
            body=p.body,
            createdAt=p.created_at.isoformat(),
            updatedAt=p.updated_at.isoformat(),
        )


class CommentResponse(BaseModel):
    id: str
    postId: str
    userId: str
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
