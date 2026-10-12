#!/usr/bin/env python3
"""Scrape public, no-auth forum sources into a normalized Threadit seed snapshot.

Sources (no authentication, public APIs):
  * Hacker News (Firebase API)  -> posts with genuine threaded comment trees + usernames
  * Lemmy (lemmy.world API v3)  -> posts that carry real images + usernames

Output: scripts/seed/data/snapshot.json  — a normalized, source-agnostic structure
the seeder replays. Re-running refreshes the snapshot; the seeder is deterministic
given a snapshot, so seeding is repeatable.

Usage:
    python scripts/seed/scrape.py [--hn N] [--lemmy N] [--out PATH]
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

HN = "https://hacker-news.firebaseio.com/v0"
LEMMY = "https://lemmy.world/api/v3"
UA = "threadit-seed/0.1 (open-source demo seeder)"
IMAGE_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp")

_TAG = re.compile(r"<[^>]+>")


def _get(url: str, tries: int = 3) -> Any:
    last: Exception | None = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": UA, "Accept": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=15) as r:  # noqa: S310 (trusted public APIs)
                return json.loads(r.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(1.0 * (attempt + 1))
    raise RuntimeError(f"GET failed after {tries} tries: {url}: {last}")


def _clean(text: str | None) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = text.replace("<p>", "\n\n").replace("</p>", "")
    text = _TAG.sub("", text)
    return text.strip()


# A light sensitivity filter so the demo seed stays presentable. Not exhaustive;
# just drops the most obviously unsuitable items for a public demo.
_BLOCK = re.compile(
    r"\b(rape|rapist|nazi|slur|nsfw|porn|sex|genocide|kill|suicide|racist)\b",
    re.IGNORECASE,
)


def _too_edgy(text: str) -> bool:
    return bool(_BLOCK.search(text or ""))


# ---------------------------------------------------------------------------
# Hacker News: stories + nested comment trees
# ---------------------------------------------------------------------------
def scrape_hn(n_posts: int, max_comments_per_post: int = 12, max_depth: int = 4) -> list[dict]:
    ids = _get(f"{HN}/topstories.json")[: n_posts * 3]
    posts: list[dict] = []
    for sid in ids:
        if len(posts) >= n_posts:
            break
        item = _get(f"{HN}/item/{sid}.json")
        if not item or item.get("type") != "story" or item.get("dead") or item.get("deleted"):
            continue
        title = item.get("title")
        if not title:
            continue
        body = _clean(item.get("text")) or (item.get("url") or "")
        comments: list[dict] = []
        budget = {"n": max_comments_per_post}

        def walk(kid_id: int, depth: int, budget: dict = budget) -> dict | None:
            if budget["n"] <= 0 or depth > max_depth:
                return None
            c = _get(f"{HN}/item/{kid_id}.json")
            if not c or c.get("type") != "comment" or c.get("deleted") or c.get("dead"):
                return None
            text = _clean(c.get("text"))
            if not text:
                return None
            budget["n"] -= 1
            node = {"author": c.get("by") or "anon", "text": text[:9000], "replies": []}
            for grand in (c.get("kids") or [])[:3]:
                if budget["n"] <= 0:
                    break
                child = walk(grand, depth + 1)
                if child:
                    node["replies"].append(child)
            return node

        for kid in item.get("kids") or []:
            if budget["n"] <= 0:
                break
            node = walk(kid, 0)
            if node:
                comments.append(node)

        posts.append(
            {
                "source": "hackernews",
                "author": item.get("by") or "anon",
                "title": title[:300],
                "body": (body or title)[:9000],
                "image_url": None,
                "comments": comments,
            }
        )
        print(f"  HN  {len(posts):2d}/{n_posts}  '{title[:50]}'  ({_count(comments)} comments)")
    return posts


# ---------------------------------------------------------------------------
# Lemmy: image posts + a few comments
# ---------------------------------------------------------------------------
def scrape_lemmy(n_posts: int) -> list[dict]:
    posts: list[dict] = []
    for page in (1, 2, 3):
        if len(posts) >= n_posts:
            break
        data = _get(f"{LEMMY}/post/list?limit=50&page={page}&sort=TopWeek")
        for entry in data.get("posts", []):
            if len(posts) >= n_posts:
                break
            p = entry.get("post", {})
            url = p.get("url") or ""
            is_img = url.lower().endswith(IMAGE_EXT) or "pictrs/image" in url
            if p.get("nsfw") or p.get("removed") or p.get("deleted") or not is_img:
                continue
            if _too_edgy(p.get("name", "")) or _too_edgy(p.get("body", "") or ""):
                continue
            pid = p.get("id")
            comments: list[dict] = []
            try:
                cdata = _get(f"{LEMMY}/comment/list?post_id={pid}&limit=8&sort=Top&max_depth=2")
                for cv in cdata.get("comments", [])[:6]:
                    com = cv.get("comment", {})
                    path = com.get("path", "0.0")
                    if path.count(".") != 1:  # top-level only (0.<id>)
                        continue
                    text = _clean(com.get("content"))
                    if text and not _too_edgy(text):
                        comments.append(
                            {
                                "author": cv.get("creator", {}).get("name") or "anon",
                                "text": text[:4000],
                                "replies": [],
                            }
                        )
            except Exception:  # noqa: BLE001 - comments are best-effort
                pass
            posts.append(
                {
                    "source": "lemmy",
                    "author": entry.get("creator", {}).get("name") or "anon",
                    "title": (p.get("name") or "untitled")[:300],
                    "body": _clean(p.get("body")) or (p.get("name") or "")[:300],
                    "image_url": url,
                    "comments": comments,
                }
            )
            print(
                f"  LEM {len(posts):2d}/{n_posts}  "
                f"'{p.get('name', '')[:46]}'  (img, {len(comments)} comments)"
            )
    return posts


def _count(comments: list[dict]) -> int:
    return sum(1 + _count(c["replies"]) for c in comments)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hn", type=int, default=15, help="number of Hacker News posts")
    ap.add_argument("--lemmy", type=int, default=8, help="number of Lemmy image posts")
    ap.add_argument("--out", default=str(Path(__file__).parent / "data" / "snapshot.json"))
    args = ap.parse_args()

    print(f"==> Scraping Hacker News ({args.hn} posts, with threaded comments)")
    hn = scrape_hn(args.hn)
    print(f"==> Scraping Lemmy ({args.lemmy} image posts)")
    lemmy = scrape_lemmy(args.lemmy)

    posts = hn + lemmy
    total_comments = sum(_count(p["comments"]) for p in posts)
    users = sorted(
        {p["author"] for p in posts} | {c for p in posts for c in _authors(p["comments"])}
    )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    snapshot = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "sources": ["hackernews", "lemmy"],
        "stats": {"posts": len(posts), "comments": total_comments, "users": len(users)},
        "posts": posts,
    }
    out.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False))
    print(
        f"\n==> Wrote {out}\n    posts={len(posts)} (HN {len(hn)} + Lemmy {len(lemmy)}), "
        f"comments={total_comments}, distinct users={len(users)}, "
        f"image posts={sum(1 for p in posts if p['image_url'])}"
    )
    if len(posts) < 20:
        print(
            "WARNING: fewer than 20 posts scraped; re-run or raise --hn/--lemmy.", file=sys.stderr
        )
    return 0


def _authors(comments: list[dict]) -> list[str]:
    out: list[str] = []
    for c in comments:
        out.append(c["author"])
        out.extend(_authors(c["replies"]))
    return out


if __name__ == "__main__":
    raise SystemExit(main())
