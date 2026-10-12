#!/usr/bin/env bash
# One-command setup for new contributors. Prepares everything needed to run the
# full app locally on Floci (no AWS account required).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> Checking prerequisites"
missing=0
for bin in python3 node npm docker; do
  if command -v "$bin" >/dev/null; then
    echo "    ok: $bin ($($bin --version 2>&1 | head -1))"
  else
    echo "    MISSING: $bin"; missing=1
  fi
done
[[ "$missing" == "0" ]] || { echo "Install the missing prerequisites above, then re-run."; exit 1; }

echo "==> Python venv + backend dependencies (make install)"
make install

echo "==> Frontend dependencies (npm install)"
( cd frontend && npm install )

echo "==> Playwright browsers (for E2E; optional, continues on failure)"
( cd frontend && npx playwright install --with-deps chromium ) || echo "    (skipped — run 'npx playwright install' later if you want E2E)"

echo "==> Pre-pulling the Floci image"
docker compose pull >/dev/null 2>&1 || true

cat <<'EOF'

============================================================
  Setup complete.

  Run the full app locally (no AWS needed):
      make app-floci        # -> http://localhost:5173

  Stop it:
      make app-stop

  Run against real AWS (requires a deployed stack + creds):
      make aws-up           # deploy backend to AWS (billing!)
      make app-aws          # local frontend -> AWS backend
      make aws-down         # tear the AWS stack down

  Verify the codebase:
      make check            # lint + 62 tests
============================================================
EOF
