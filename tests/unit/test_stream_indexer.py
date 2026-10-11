from __future__ import annotations

from threadit_core.repositories.search_index import PostDoc, SearchIndex, SearchPage
from threadit_core.services.stream_indexer import StreamIndexer


class FakeIndex(SearchIndex):
    def __init__(self) -> None:
        self.docs: dict[str, PostDoc] = {}

    def upsert_post(self, doc: PostDoc) -> None:
        self.docs[doc.post_id] = doc

    def delete_post(self, post_id: str) -> None:
        self.docs.pop(post_id, None)

    def search_posts(self, keyword, *, limit, cursor) -> SearchPage:
        return SearchPage(hits=(), next_cursor=None)


def _post_image(pid: str, title: str = "t") -> dict:
    return {
        "entityType": {"S": "Post"},
        "postId": {"S": pid},
        "userId": {"S": "u1"},
        "title": {"S": title},
        "body": {"S": "b"},
        "createdAt": {"S": "2026-01-01T00:00:00+00:00"},
    }


def _rec(event: str, new=None, old=None) -> dict:
    ddb = {}
    if new is not None:
        ddb["NewImage"] = new
    if old is not None:
        ddb["OldImage"] = old
    return {"eventName": event, "dynamodb": ddb}


def test_insert_upserts_post():
    idx = FakeIndex()
    n = StreamIndexer(idx).handle_records([_rec("INSERT", new=_post_image("p1"))])
    assert n == 1
    assert idx.docs["p1"].title == "t"


def test_modify_updates_post():
    idx = FakeIndex()
    si = StreamIndexer(idx)
    si.handle_records([_rec("INSERT", new=_post_image("p1", "old"))])
    si.handle_records([_rec("MODIFY", new=_post_image("p1", "new"))])
    assert idx.docs["p1"].title == "new"


def test_remove_deletes_post():
    idx = FakeIndex()
    si = StreamIndexer(idx)
    si.handle_records([_rec("INSERT", new=_post_image("p1"))])
    si.handle_records([_rec("REMOVE", old=_post_image("p1"))])
    assert "p1" not in idx.docs


def test_non_post_items_ignored():
    idx = FakeIndex()
    comment = {"entityType": {"S": "Comment"}, "postId": {"S": "p1"}}
    n = StreamIndexer(idx).handle_records([_rec("INSERT", new=comment)])
    assert n == 0
    assert idx.docs == {}


def test_insert_is_idempotent_on_replay():
    idx = FakeIndex()
    si = StreamIndexer(idx)
    rec = _rec("INSERT", new=_post_image("p1"))
    si.handle_records([rec, rec, rec])  # at-least-once replay
    assert list(idx.docs) == ["p1"]
