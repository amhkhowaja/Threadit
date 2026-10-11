from __future__ import annotations

from dataclasses import dataclass

from threadit_core.repositories.search_index import PostDoc, SearchIndex


def _attr(image: dict, name: str, kind: str = "S") -> str | None:
    v = image.get(name)
    if v is None:
        return None
    return v.get(kind)


def _is_post(image: dict) -> bool:
    return _attr(image, "entityType") == "Post"


@dataclass(slots=True)
class StreamIndexer:
    """Projects DynamoDB Stream records for Post items into the search index.

    Only Post items are indexed in P2. Comment/idempo/user items are ignored.
    Operations are idempotent (upsert/delete by postId), so at-least-once stream
    delivery is safe to replay.
    """

    index: SearchIndex

    def handle_records(self, records: list[dict]) -> int:
        processed = 0
        for record in records:
            if self._handle_one(record):
                processed += 1
        return processed

    def _handle_one(self, record: dict) -> bool:
        event = record.get("eventName")
        ddb = record.get("dynamodb", {})
        new_image = ddb.get("NewImage")
        old_image = ddb.get("OldImage")

        if event in ("INSERT", "MODIFY") and new_image and _is_post(new_image):
            self.index.upsert_post(self._to_doc(new_image))
            return True
        if event == "REMOVE" and old_image and _is_post(old_image):
            post_id = _attr(old_image, "postId")
            if post_id:
                self.index.delete_post(post_id)
                return True
        return False

    @staticmethod
    def _to_doc(image: dict) -> PostDoc:
        return PostDoc(
            post_id=_attr(image, "postId") or "",
            user_id=_attr(image, "userId") or "",
            title=_attr(image, "title") or "",
            body=_attr(image, "body") or "",
            created_at=_attr(image, "createdAt") or "",
        )
