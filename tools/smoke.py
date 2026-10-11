from __future__ import annotations

import os
import sys
import uuid

os.environ.setdefault("THREADIT_AWS_ENDPOINT_URL", "http://localhost:4566")
os.environ.setdefault("THREADIT_AWS_REGION", "us-east-1")
os.environ.setdefault("THREADIT_TABLE_NAME", "threadit")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "test")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "test")

from fastapi.testclient import TestClient  # noqa: E402

from services.post_read.app import create_app as read_app  # noqa: E402
from services.post_write.app import create_app as write_app  # noqa: E402
from services.post_write.app import require_user_id  # noqa: E402

USER = str(uuid.uuid4())


def _k() -> str:
    return str(uuid.uuid4())


def main() -> int:
    w = write_app()
    w.dependency_overrides[require_user_id] = lambda: USER

    with TestClient(w) as wc, TestClient(read_app()) as rc:
        r = wc.post(
            "/v1/posts", json={"title": "hello", "body": "world"}, headers={"Idempotency-Key": _k()}
        )
        assert r.status_code == 201, r.text
        pid = r.json()["id"]
        print(f"created post {pid}")

        top = wc.post(
            f"/v1/posts/{pid}/comments", json={"text": "top"}, headers={"Idempotency-Key": _k()}
        ).json()
        wc.post(
            f"/v1/posts/{pid}/comments",
            json={"text": "reply", "parentId": top["id"]},
            headers={"Idempotency-Key": _k()},
        )
        print("created threaded comment + reply")

        got = rc.get(f"/v1/posts/{pid}").json()
        assert got["id"] == pid and got["userId"] == USER

        tree = rc.get(f"/v1/posts/{pid}/comments").json()
        depths = sorted(c["depth"] for c in tree["items"])
        assert depths == [0, 1], depths
        print(f"read post + comment tree back; depths={depths}")

        search = rc.get("/v1/posts", params={"search_keyword": "x"})
        assert search.status_code == 501
        print("search_keyword -> 501 as expected")

    print("SMOKE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
