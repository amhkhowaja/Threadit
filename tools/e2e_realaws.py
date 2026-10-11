from __future__ import annotations

import sys
import time
import uuid

# Real-AWS config injected via env before importing apps.
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
        # create post
        r = wc.post(
            "/v1/posts",
            json={"title": "chimera breeding", "body": "full app real-aws e2e"},
            headers={"Idempotency-Key": _k()},
        )
        assert r.status_code == 201, r.text
        pid = r.json()["id"]
        print(f"[1] created post {pid}")

        # threaded reply
        top = wc.post(
            f"/v1/posts/{pid}/comments", json={"text": "top"}, headers={"Idempotency-Key": _k()}
        ).json()
        wc.post(
            f"/v1/posts/{pid}/comments",
            json={"text": "reply", "parentId": top["id"]},
            headers={"Idempotency-Key": _k()},
        )
        print("[2] created threaded comment + reply")

        # read post + tree
        assert rc.get(f"/v1/posts/{pid}").json()["id"] == pid
        tree = rc.get(f"/v1/posts/{pid}/comments").json()
        depths = sorted(c["depth"] for c in tree["items"])
        assert depths == [0, 1], depths
        print(f"[3] read post + comment tree; depths={depths}")

        # list latest
        latest = rc.get("/v1/posts").json()
        assert any(p["id"] == pid for p in latest["items"])
        print(f"[4] list latest returned {len(latest['items'])} post(s), includes new post")

        # idempotency replay
        key = _k()
        a = wc.post("/v1/posts", json={"title": "x", "body": "y"}, headers={"Idempotency-Key": key})
        b = wc.post("/v1/posts", json={"title": "x", "body": "y"}, headers={"Idempotency-Key": key})
        assert a.json()["id"] == b.json()["id"]
        print("[5] idempotency replay returns same id (no duplicate)")

        # search (after Streams->Lambda->OpenSearch indexing lag)
        print("[6] waiting 45s for search indexing...")
        time.sleep(45)
        found = False
        for _ in range(6):
            s = rc.get("/v1/posts", params={"search_keyword": "chimera"})
            assert s.status_code == 200, s.text
            if any(p["id"] == pid for p in s.json()["items"]):
                found = True
                break
            time.sleep(5)
        assert found, "post not found in search within timeout"
        print("[6] search returned the indexed post")

    print("FULL-APP REAL-AWS E2E OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
