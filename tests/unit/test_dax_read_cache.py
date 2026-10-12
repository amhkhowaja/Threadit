from __future__ import annotations

import importlib
import sys
import types

import pytest

read_app = importlib.import_module("services.post_read.app")


class _Settings:
    """Minimal settings stand-in for build_read_service (no pydantic env needed)."""

    def __init__(self, *, dax_endpoint: str = "", opensearch_endpoint: str = ""):
        self.dax_endpoint = dax_endpoint
        self.opensearch_endpoint = opensearch_endpoint
        self.opensearch_sign = False
        self.table_name = "threadit"
        self.aws_region = "eu-central-1"
        self.aws_endpoint_url = None
        self.default_page_limit = 20
        self.max_page_limit = 100
        self.read_cache_ttl_s = 0  # cache off in these builder-selection tests
        self.read_cache_stale_ttl_s = 10.0


@pytest.fixture
def spy_builders(monkeypatch):
    """Record which table builder the read service calls, without touching AWS."""
    calls: dict[str, dict] = {}

    def fake_dax(**kw):
        calls["dax"] = kw
        return object()

    def fake_direct(**kw):
        calls["direct"] = kw
        return object()

    monkeypatch.setattr(read_app, "build_dax_table", fake_dax)
    monkeypatch.setattr(read_app, "build_table", fake_direct)
    # Repo wraps whatever table it's given; keep it inert.
    monkeypatch.setattr(read_app, "DynamoDBRepository", lambda table: types.SimpleNamespace())
    return calls


# --- contract: builder selection -------------------------------------------------


def test_read_service_uses_dax_when_endpoint_set(spy_builders):
    read_app.build_read_service(_Settings(dax_endpoint="daxs://my-dax:8111"))
    assert "dax" in spy_builders and "direct" not in spy_builders


def test_read_service_uses_direct_dynamodb_when_dax_empty(spy_builders):
    read_app.build_read_service(_Settings(dax_endpoint=""))
    assert "direct" in spy_builders and "dax" not in spy_builders


def test_dax_builder_receives_endpoint_and_table(spy_builders):
    read_app.build_read_service(_Settings(dax_endpoint="daxs://host:8111"))
    kw = spy_builders["dax"]
    assert kw["dax_endpoint"] == "daxs://host:8111"
    assert kw["table_name"] == "threadit"
    assert kw["region"] == "eu-central-1"


# --- contract: build_dax_table delegates to the amazondax resource API -----------


def test_build_dax_table_uses_amazondax_resource(monkeypatch):
    """build_dax_table must construct an amazondax resource and return its Table,
    exposing the same resource interface the repository already uses."""
    from threadit_core.repositories import dynamodb as dd

    seen: dict = {}

    class FakeTable:
        pass

    class FakeResource:
        def Table(self, name):  # noqa: N802 - mirrors boto3 resource API
            seen["table_name"] = name
            return FakeTable()

    class FakeDaxClient:
        @staticmethod
        def resource(*, endpoint_url, region_name):
            seen["endpoint_url"] = endpoint_url
            seen["region_name"] = region_name
            return FakeResource()

    # Inject a fake `amazondax` module so the import inside build_dax_table resolves.
    fake_mod = types.ModuleType("amazondax")
    fake_mod.AmazonDaxClient = FakeDaxClient
    monkeypatch.setitem(sys.modules, "amazondax", fake_mod)

    table = dd.build_dax_table(
        table_name="threadit", region="eu-central-1", dax_endpoint="daxs://h:8111"
    )
    assert isinstance(table, FakeTable)
    assert seen == {
        "endpoint_url": "daxs://h:8111",
        "region_name": "eu-central-1",
        "table_name": "threadit",
    }


# --- contract: DAX-backed repo still honors ConsistentRead (RYOW) ----------------


def test_consistent_read_passes_through_dax_backed_repo():
    """Read-your-own-write must still use ConsistentRead even when the table is
    DAX-backed (DAX forwards consistent reads to DynamoDB). We assert the repo
    forwards consistent=True to the underlying table's get_item."""
    from threadit_core.repositories.dynamodb import DynamoDBRepository

    captured: dict = {}

    class FakeTable:
        def get_item(self, **kw):
            captured.update(kw)
            return {"Item": None}

    repo = DynamoDBRepository(FakeTable())
    repo.get_post("p1", consistent=True)
    assert captured.get("ConsistentRead") is True
