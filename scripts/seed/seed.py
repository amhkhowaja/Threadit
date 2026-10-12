#!/usr/bin/env python3
"""Seed a CLEAN Floci Threadit from a scraped snapshot, as many different users.

What it does, repeatably:
  1. Wipes the local Floci `threadit` DynamoDB table (clean slate; LOCAL only).
  2. Reads scripts/seed/data/snapshot.json (produced by scrape.py).
  3. For every post, acts as that post's ORIGINAL author (dev x-user-id header),
     creates the post, uploads its image via the presign+PUT flow (if any), then
     replays its threaded comment tree, each comment as ITS author.

This talks HTTP to the running local services (post_read :8080, post_write :8081),
exactly like the real frontend, so it exercises the same code paths.

Safety: refuses to run unless the write service points at a Floci endpoint
(THREADIT_AWS_ENDPOINT_URL set) so it can never wipe real AWS.

Usage:
    python scripts/seed/seed.py [--read URL] [--write URL] [--snapshot PATH] [--no-wipe]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
import urllib.request
import uuid
from pathlib import Path

import boto3

READ_DEFAULT = os.environ.get("THREADIT_SEED_READ", "http://127.0.0.1:8080")
WRITE_DEFAULT = os.environ.get("THREADIT_SEED_WRITE", "http://127.0.0.1:8081")
FLOCI_ENDPOINT = os.environ.get("THREADIT_AWS_ENDPOINT_URL", "http://localhost:4566")
REGION = os.environ.get("THREADIT_AWS_REGION", "us-east-1")
TABLE = os.environ.get("THREADIT_TABLE_NAME", "threadit")
IMAGES_BUCKET = os.environ.get("THREADIT_ATTACHMENTS_BUCKET", "threadit-dev-images")
PLACEHOLDER = "https://picsum.photos/seed/{seed}/900/600"  # open image service fallback


def _uid(handle: str) -> str:
    """Stable per-author dev user id (slug of the real forum handle)."""
    slug = re.sub(r"[^a-zA-Z0-9_-]", "-", handle).strip("-").lower() or "anon"
    return f"seed-{slug}"


def _http(
    method: str,
    url: str,
    *,
    user: str | None = None,
    body: dict | None = None,
    raw: bytes | None = None,
    content_type: str | None = None,
    timeout: int = 20,
):
    headers = {}
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    elif raw is not None:
        data = raw
        headers["Content-Type"] = content_type or "application/octet-stream"
    if user:
        headers["x-user-id"] = user
        headers["Idempotency-Key"] = str(uuid.uuid4())
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 (localhost)
        payload = r.read()
        return r.status, (json.loads(payload) if payload else {})


def wipe_table() -> None:
    """Delete every item in the local Floci threadit table (clean slate)."""
    ddb = boto3.resource("dynamodb", region_name=REGION, endpoint_url=FLOCI_ENDPOINT)
    table = ddb.Table(TABLE)
    key_schema = [k["AttributeName"] for k in table.key_schema]
    scanned = 0
    with table.batch_writer() as batch:
        resp = table.scan(
            ProjectionExpression=", ".join(f"#{k}" for k in key_schema),
            ExpressionAttributeNames={f"#{k}": k for k in key_schema},
        )
        while True:
            for item in resp.get("Items", []):
                batch.delete_item(Key={k: item[k] for k in key_schema})
                scanned += 1
            lek = resp.get("LastEvaluatedKey")
            if not lek:
                break
            resp = table.scan(
                ProjectionExpression=", ".join(f"#{k}" for k in key_schema),
                ExpressionAttributeNames={f"#{k}": k for k in key_schema},
                ExclusiveStartKey=lek,
            )
    print(f"==> Wiped {scanned} items from '{TABLE}' (clean slate)")


def _fetch_image(post: dict) -> bytes | None:
    """Get image bytes for an image post. Try the source URL; fall back to an
    open placeholder keyed by the title so re-runs are deterministic."""
    url = post.get("image_url")
    candidates = []
    if url:
        candidates.append(url)
    seed = hashlib.sha1(post["title"].encode()).hexdigest()[:10]  # noqa: S324 (non-crypto)
    candidates.append(PLACEHOLDER.format(seed=seed))
    for cand in candidates:
        try:
            req = urllib.request.Request(cand, headers={"User-Agent": "threadit-seed/0.1"})
            with urllib.request.urlopen(req, timeout=20) as r:  # noqa: S310
                ct = r.headers.get("Content-Type", "")
                if r.status == 200 and ct.startswith("image/"):
                    return r.read()
        except Exception:  # noqa: BLE001, S112 - try next image candidate
            continue
    return None


def _upload_image(write_url: str, user: str, img: bytes) -> str | None:
    status, out = _http(
        "POST",
        f"{write_url}/v1/attachments:presign",
        user=user,
        body={"contentType": "image/jpeg", "sizeBytes": len(img)},
    )
    if status not in (200, 201):
        return None
    put_url, key = out["url"], out["objectKey"]
    ps, _ = _http("PUT", put_url, raw=img, content_type="image/jpeg")
    return key if ps in (200, 204) else None


def _post_comments(
    write_url: str, post_id: str, comments: list[dict], parent_id: str | None, counters: dict
) -> None:
    for c in comments:
        user = _uid(c["author"])
        body = {"text": c["text"]}
        if parent_id:
            body["parentId"] = parent_id
        try:
            status, out = _http(
                "POST", f"{write_url}/v1/posts/{post_id}/comments", user=user, body=body
            )
            if status == 201:
                counters["comments"] += 1
                counters["users"].add(user)
                if c.get("replies"):
                    _post_comments(write_url, post_id, c["replies"], out["id"], counters)
        except Exception as exc:  # noqa: BLE001 - keep seeding on individual failures
            print(f"    ! comment failed ({user}): {exc}")


def seed(read_url: str, write_url: str, snapshot_path: Path, do_wipe: bool) -> int:
    snap = json.loads(snapshot_path.read_text())
    posts = snap["posts"]
    print(
        f"==> Snapshot: {len(posts)} posts, "
        f"{snap['stats']['comments']} comments, {snap['stats']['users']} users"
    )

    if do_wipe:
        wipe_table()
        time.sleep(1)

    counters = {"posts": 0, "comments": 0, "images": 0, "users": set()}
    for i, p in enumerate(posts, 1):
        author = _uid(p["author"])
        counters["users"].add(author)
        image_key = None
        if p.get("image_url"):
            img = _fetch_image(p)
            if img:
                image_key = _upload_image(write_url, author, img)
                if image_key:
                    counters["images"] += 1
        try:
            status, out = _http(
                "POST",
                f"{write_url}/v1/posts",
                user=author,
                body={"title": p["title"], "body": p["body"], "imageKey": image_key},
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  [{i:2d}] post FAILED ({author}): {exc}")
            continue
        if status != 201:
            print(f"  [{i:2d}] post {status} ({author}): {out}")
            continue
        counters["posts"] += 1
        pid = out["id"]
        img_tag = " +img" if image_key else ""
        print(f"  [{i:2d}] {p['source']:10s} {author:22s} '{p['title'][:42]}'{img_tag}")
        _post_comments(write_url, pid, p["comments"], None, counters)

    print(
        f"\n==> Seed complete: {counters['posts']} posts, {counters['comments']} comments, "
        f"{counters['images']} images, {len(counters['users'])} distinct users"
    )
    # verify via the read API
    try:
        _, latest = _http("GET", f"{read_url}/v1/posts?limit=50")
        print(f"==> Read API now lists {len(latest.get('items', []))} posts")
    except Exception as exc:  # noqa: BLE001
        print(f"    (read verify skipped: {exc})")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--read", default=READ_DEFAULT)
    ap.add_argument("--write", default=WRITE_DEFAULT)
    ap.add_argument("--snapshot", default=str(Path(__file__).parent / "data" / "snapshot.json"))
    ap.add_argument("--no-wipe", action="store_true", help="append instead of clean-slate")
    args = ap.parse_args()

    if "4566" not in FLOCI_ENDPOINT and "localhost" not in FLOCI_ENDPOINT:
        print(
            f"REFUSING: THREADIT_AWS_ENDPOINT_URL={FLOCI_ENDPOINT!r} is not a Floci/local "
            "endpoint. This seeder only targets local Floci, never real AWS."
        )
        return 2

    snapshot = Path(args.snapshot)
    if not snapshot.exists():
        print(f"ERROR: {snapshot} not found. Run: python scripts/seed/scrape.py")
        return 1

    return seed(args.read, args.write, snapshot, do_wipe=not args.no_wipe)


if __name__ == "__main__":
    raise SystemExit(main())
