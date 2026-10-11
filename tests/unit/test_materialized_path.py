from __future__ import annotations

from datetime import datetime, timezone

import pytest

from threadit_core.domain.errors import MaxDepthExceeded
from threadit_core.repositories.keys import KeyFactory, MaterializedPathBuilder

TS = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


def test_top_level_comment_has_depth_zero_and_self_root():
    b = MaterializedPathBuilder(max_depth=8)
    path, depth, root = b.top_level(TS, "c1")
    assert depth == 0
    assert root == "c1"
    assert path.endswith("#c1")


def test_child_extends_parent_path_and_keeps_root():
    b = MaterializedPathBuilder(max_depth=8)
    parent_path, _, parent_root = b.top_level(TS, "c1")
    path, depth, root = b.child(parent_path, 0, parent_root, TS, "c2")
    assert depth == 1
    assert root == "c1"
    assert path.startswith(parent_path + "#")
    assert path.endswith("#c2")


def test_depth_cap_raises_at_nine():
    b = MaterializedPathBuilder(max_depth=8)
    with pytest.raises(MaxDepthExceeded):
        b.child("some#path", 8, "c1", TS, "c9")


def test_comment_id_with_separator_rejected():
    b = MaterializedPathBuilder(max_depth=8)
    with pytest.raises(ValueError):
        b.top_level(TS, "bad#id")


def test_subtree_prefix_is_prefix_of_child_paths():
    b = MaterializedPathBuilder(max_depth=8)
    root_path, _, root = b.top_level(TS, "c1")
    child_path, _, _ = b.child(root_path, 0, root, TS, "c2")
    prefix = KeyFactory.comment_subtree_prefix(root_path)
    assert KeyFactory.comment_sk(child_path).startswith(prefix)
