# Seed data for Threadit (local Floci demo)

Populate a clean local Threadit with realistic content so the app looks alive for
demos and manual testing. Everything here targets **local Floci only** and never
touches real AWS.

## One command

```bash
make app-floci   # start the full local stack first (if not already running)
make seed        # scrape (first run) + clean-slate seed
```

Open http://localhost:5173 and you will see ~23 posts, threaded comments, and images.

## What it does

1. **Scrape** (`scrape.py`) pulls from two public, no-authentication sources:
   - **Hacker News** (Firebase API): stories with their genuine nested comment
     trees and real usernames (maps onto Threadit's threaded comments).
   - **Lemmy** (`lemmy.world` API v3): posts that carry real images, with a few
     top-level comments.
   The normalized result is cached at `data/snapshot.json`. A light sensitivity
   filter drops obviously unsuitable items.

2. **Seed** (`seed.py`), repeatably:
   - **Wipes** the local Floci `threadit` table (clean slate).
   - Replays every post over HTTP against the running services (`:8080`/`:8081`),
     each post and comment attributed to **its original author** via a stable
     `seed-<handle>` dev user id (the `x-user-id` dev-auth path).
   - Uploads each image post's picture through the real presign + PUT flow, so the
     image-serving path is exercised end to end. If a source image is unreachable,
     it falls back to an open placeholder (picsum.photos) keyed by the title, so
     runs stay deterministic.

Re-running `make seed` always lands on the same clean state (it wipes first).

## Flags

```bash
RESCRAPE=1 make seed              # force a fresh scrape before seeding
python scripts/seed/scrape.py --hn 20 --lemmy 10   # scrape more
python scripts/seed/seed.py --no-wipe              # append instead of clean-slate
```

## Notes on data

- Scraped content (`data/snapshot.json`) is **gitignored**: it is third-party
  user content fetched at runtime, not redistributed in this repo. Regenerate it
  anytime with `make seed`.
- The seeder refuses to run unless `THREADIT_AWS_ENDPOINT_URL` points at a
  Floci/local endpoint, so it cannot wipe or seed a real AWS table.
