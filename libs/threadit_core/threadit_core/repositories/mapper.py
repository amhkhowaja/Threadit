from __future__ import annotations

from datetime import datetime

from threadit_core.domain.models import Comment, Post
from threadit_core.repositories.keys import KeyFactory


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value)


class ItemMapper:
    """Domain <-> single-table item. Owns all attribute names (SYSTEM_ARCHITECTURE §4)."""

    @staticmethod
    def post_to_item(post: Post) -> dict:
        gsi1pk, gsi1sk = KeyFactory.gsi1_latest(post.created_at, post.post_id)
        gsi2pk, gsi2sk = KeyFactory.gsi2_user(post.user_id, post.created_at, post.post_id)
        return {
            "PK": KeyFactory.post_pk(post.post_id),
            "SK": KeyFactory.post_sk(post.post_id),
            "GSI1PK": gsi1pk,
            "GSI1SK": gsi1sk,
            "GSI2PK": gsi2pk,
            "GSI2SK": gsi2sk,
            "entityType": "Post",
            "postId": post.post_id,
            "userId": post.user_id,
            "title": post.title,
            "body": post.body,
            "createdAt": _iso(post.created_at),
            "updatedAt": _iso(post.updated_at),
            "schemaVersion": post.schema_version,
        }

    @staticmethod
    def item_to_post(item: dict) -> Post:
        return Post(
            post_id=item["postId"],
            user_id=item["userId"],
            title=item["title"],
            body=item["body"],
            created_at=_parse(item["createdAt"]),
            updated_at=_parse(item["updatedAt"]),
            schema_version=int(item["schemaVersion"]),
        )

    @staticmethod
    def comment_to_item(comment: Comment) -> dict:
        gsi2pk, gsi2sk = KeyFactory.gsi2_user(
            comment.user_id, comment.created_at, comment.comment_id
        )
        item = {
            "PK": KeyFactory.post_pk(comment.post_id),
            "SK": KeyFactory.comment_sk(comment.path),
            "GSI2PK": gsi2pk,
            "GSI2SK": gsi2sk,
            "entityType": "Comment",
            "commentId": comment.comment_id,
            "postId": comment.post_id,
            "userId": comment.user_id,
            "text": comment.text,
            "depth": comment.depth,
            "path": comment.path,
            "rootCommentId": comment.root_comment_id,
            "createdAt": _iso(comment.created_at),
            "schemaVersion": comment.schema_version,
        }
        if comment.parent_id is not None:
            item["parentId"] = comment.parent_id
        return item

    @staticmethod
    def item_to_comment(item: dict) -> Comment:
        return Comment(
            comment_id=item["commentId"],
            post_id=item["postId"],
            user_id=item["userId"],
            text=item["text"],
            created_at=_parse(item["createdAt"]),
            depth=int(item["depth"]),
            path=item["path"],
            root_comment_id=item["rootCommentId"],
            parent_id=item.get("parentId"),
            schema_version=int(item["schemaVersion"]),
        )
