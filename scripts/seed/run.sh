#!/usr/bin/env bash
# Seed a clean local Floci Threadit with real forum content (Hacker News threaded
# posts/comments + Lemmy image posts), each item posted as its original author.
#
# Repeatable: wipes the local threadit table first (clean slate), then replays.
# Requires the local stack running (make app-floci). If the backend services
# aren't up, this prints how to start them and exits.
#
# Usage:
#   scripts/seed/run.sh            # scrape if needed, then seed clean
#   RESCRAPE=1 scripts/seed/run.sh # force a fresh scrape
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"
PY="$ROOT/.venv/bin/python"
SNAP="$ROOT/scripts/seed/data/snapshot.json"

READ="${THREADIT_SEED_READ:-http://127.0.0.1:8080}"
WRITE="${THREADIT_SEED_WRITE:-http://127.0.0.1:8081}"

[[ -x "$PY" ]] || { echo "ERROR: venv missing. Run: make install"; exit 1; }

# Backend must be running (seeder talks HTTP to it, like the real frontend).
if ! curl -s -m 4 "$WRITE/healthz" >/dev/null 2>&1; then
  echo "ERROR: write service not reachable at $WRITE."
  echo "       Start the local app first:  make app-floci"
  exit 1
fi

# Floci env for the clean-slate table wipe (local only; the seeder refuses non-Floci).
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-test}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-test}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-us-east-1}"
export THREADIT_AWS_ENDPOINT_URL="${THREADIT_AWS_ENDPOINT_URL:-http://localhost:4566}"
export THREADIT_AWS_REGION="${THREADIT_AWS_REGION:-us-east-1}"
export THREADIT_TABLE_NAME="${THREADIT_TABLE_NAME:-threadit}"
export THREADIT_ATTACHMENTS_BUCKET="${THREADIT_ATTACHMENTS_BUCKET:-threadit-dev-images}"

if [[ "${RESCRAPE:-0}" == "1" || ! -f "$SNAP" ]]; then
  echo "==> Scraping fresh content (Hacker News + Lemmy, no auth)"
  "$PY" scripts/seed/scrape.py
else
  echo "==> Using cached snapshot: $SNAP  (set RESCRAPE=1 to refresh)"
fi

echo "==> Seeding clean-slate Floci Threadit"
"$PY" scripts/seed/seed.py --read "$READ" --write "$WRITE" --snapshot "$SNAP"

echo
echo "==> Done. Open the app:  http://localhost:5173"
