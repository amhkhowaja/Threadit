from __future__ import annotations

from datetime import datetime

from threadit_core.domain.errors import MaxDepthExceeded

_SEP = "#"


def _ts(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%S%fZ")


def _bucket(dt: datetime) -> str:
    return dt.strftime("%Y%m%d%H")


class KeyFactory:
    """Owns every PK/SK/GSI key string for the single table `threadit`."""

    @staticmethod
    def post_pk(post_id: str) -> str:
        return f"POST{_SEP}{post_id}"

    @staticmethod
    def post_sk(post_id: str) -> str:
        return f"META{_SEP}{post_id}"

    @staticmethod
    def gsi1_latest(created_at: datetime, post_id: str) -> tuple[str, str]:
        return f"BUCKET{_SEP}{_bucket(created_at)}", f"TS{_SEP}{_ts(created_at)}{_SEP}{post_id}"

    @staticmethod
    def gsi2_user(user_id: str, created_at: datetime, entity_id: str) -> tuple[str, str]:
        return f"USER{_SEP}{user_id}", f"TS{_SEP}{_ts(created_at)}{_SEP}{entity_id}"

    @staticmethod
    def user_pk(user_id: str) -> str:
        return f"USER{_SEP}{user_id}"

    @staticmethod
    def user_sk(user_id: str) -> str:
        return f"PROFILE{_SEP}{user_id}"

    @staticmethod
    def idempo_key(key: str) -> str:
        return f"IDEMPO{_SEP}{key}"

    @staticmethod
    def comment_sk(path: str) -> str:
        return f"COMMENT{_SEP}{path}"

    @staticmethod
    def comment_subtree_prefix(root_path: str) -> str:
        return f"COMMENT{_SEP}{root_path}"

    @staticmethod
    def comment_tree_prefix() -> str:
        return f"COMMENT{_SEP}"


class MaterializedPathBuilder:
    """Builds threaded comment paths and enforces the depth cap (D3)."""

    def __init__(self, max_depth: int = 8) -> None:
        self._max_depth = max_depth

    def top_level(self, own_ts: datetime, comment_id: str) -> tuple[str, int, str]:
        if _SEP in comment_id:
            raise ValueError("comment_id must not contain the path separator")
        path = f"{_ts(own_ts)}{_SEP}{comment_id}"
        return path, 0, comment_id

    def child(
        self,
        parent_path: str,
        parent_depth: int,
        parent_root: str,
        own_ts: datetime,
        comment_id: str,
    ) -> tuple[str, int, str]:
        depth = parent_depth + 1
        if depth > self._max_depth:
            raise MaxDepthExceeded(f"max comment depth {self._max_depth} exceeded")
        if _SEP in comment_id:
            raise ValueError("comment_id must not contain the path separator")
        path = f"{parent_path}{_SEP}{_ts(own_ts)}{_SEP}{comment_id}"
        return path, depth, parent_root
