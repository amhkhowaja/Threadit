from __future__ import annotations

import time
from datetime import UTC, datetime

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from threadit_core.domain.models import Comment, Page, Post
from threadit_core.repositories.cursor import CursorCodec
from threadit_core.repositories.keys import KeyFactory
from threadit_core.repositories.mapper import ItemMapper
from threadit_core.repositories.ports import (
    CommentReadRepository,
    CommentWriteRepository,
    IdempotencyStore,
    PostReadRepository,
    PostWriteRepository,
)


def build_table(*, table_name: str, region: str, endpoint_url: str | None):
    resource = boto3.resource("dynamodb", region_name=region, endpoint_url=endpoint_url)
    return resource.Table(table_name)


class DynamoDBRepository(
    PostWriteRepository,
    PostReadRepository,
    CommentWriteRepository,
    CommentReadRepository,
):
    def __init__(self, table) -> None:
        self._t = table

    # --- posts ---
    def put_post(self, post: Post) -> None:
        self._t.put_item(Item=ItemMapper.post_to_item(post))

    def get_post(self, post_id: str, *, consistent: bool = False) -> Post | None:
        resp = self._t.get_item(
            Key={"PK": KeyFactory.post_pk(post_id), "SK": KeyFactory.post_sk(post_id)},
            ConsistentRead=consistent,
        )
        item = resp.get("Item")
        return ItemMapper.item_to_post(item) if item else None

    def list_latest_posts(self, *, limit: int, cursor: str | None) -> Page:
        # NOTE: single-bucket read for P1; LatestPostsPaginator (multi-bucket walk)
        # is wired in P2 when load testing tunes bucket granularity.
        return self._query_posts("GSI1", "GSI1PK", self._current_bucket(), limit, cursor)

    def list_user_posts(self, user_id: str, *, limit: int, cursor: str | None) -> Page:
        return self._query_posts("GSI2", "GSI2PK", KeyFactory.user_pk(user_id), limit, cursor)

    def _query_posts(self, index: str, pk_name: str, pk_value: str, limit: int, cursor) -> Page:
        kwargs = {
            "IndexName": index,
            "KeyConditionExpression": Key(pk_name).eq(pk_value),
            "Limit": limit,
            "ScanIndexForward": False,
        }
        start = CursorCodec.decode(cursor)
        if start:
            kwargs["ExclusiveStartKey"] = start
        resp = self._t.query(**kwargs)
        items = tuple(ItemMapper.item_to_post(i) for i in resp.get("Items", []))
        return Page(items=items, next_cursor=CursorCodec.encode(resp.get("LastEvaluatedKey")))

    @staticmethod
    def _current_bucket() -> str:
        return KeyFactory.gsi1_latest(datetime.now(UTC), "")[0]

    # --- comments ---
    def put_comment(self, comment: Comment) -> None:
        self._t.put_item(Item=ItemMapper.comment_to_item(comment))

    def get_comment(self, post_id: str, comment_id: str) -> Comment | None:
        resp = self._t.query(
            KeyConditionExpression=Key("PK").eq(KeyFactory.post_pk(post_id))
            & Key("SK").begins_with(KeyFactory.comment_tree_prefix()),
            FilterExpression=Key("commentId").eq(comment_id),
        )
        items = resp.get("Items", [])
        return ItemMapper.item_to_comment(items[0]) if items else None

    def get_comment_tree(self, post_id: str, *, limit: int, cursor: str | None) -> Page:
        return self._query_comments(post_id, KeyFactory.comment_tree_prefix(), limit, cursor)

    def get_comment_subtree(
        self, post_id: str, root_comment_id: str, *, limit: int, cursor: str | None
    ) -> Page:
        # root path prefix is reconstructed from the stored root comment's path at call site;
        # here we filter on rootCommentId which is indexed within the collection.
        resp = self._query_comments(post_id, KeyFactory.comment_tree_prefix(), limit, cursor)
        items = tuple(c for c in resp.items if c.root_comment_id == root_comment_id)
        return Page(items=items, next_cursor=resp.next_cursor)

    def _query_comments(self, post_id: str, sk_prefix: str, limit: int, cursor) -> Page:
        kwargs = {
            "KeyConditionExpression": Key("PK").eq(KeyFactory.post_pk(post_id))
            & Key("SK").begins_with(sk_prefix),
            "Limit": limit,
            "ScanIndexForward": True,
        }
        start = CursorCodec.decode(cursor)
        if start:
            kwargs["ExclusiveStartKey"] = start
        resp = self._t.query(**kwargs)
        items = tuple(ItemMapper.item_to_comment(i) for i in resp.get("Items", []))
        return Page(items=items, next_cursor=CursorCodec.encode(resp.get("LastEvaluatedKey")))


class DynamoDBIdempotencyStore(IdempotencyStore):
    def __init__(self, table, *, ttl_seconds: int) -> None:
        self._t = table
        self._ttl = ttl_seconds

    def try_claim(self, key: str, target_id: str) -> bool:
        sentinel = KeyFactory.idempo_key(key)
        try:
            self._t.put_item(
                Item={
                    "PK": sentinel,
                    "SK": sentinel,
                    "entityType": "Idempo",
                    "targetId": target_id,
                    "ttl": int(time.time()) + self._ttl,
                },
                ConditionExpression="attribute_not_exists(PK)",
            )
            return True
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return False
            raise

    def resolve_target(self, key: str) -> str | None:
        sentinel = KeyFactory.idempo_key(key)
        resp = self._t.get_item(Key={"PK": sentinel, "SK": sentinel})
        item = resp.get("Item")
        return item.get("targetId") if item else None
