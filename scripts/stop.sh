#!/usr/bin/env bash
# Stop all locally-launched Threadit processes (frontend + backend services)
# started by scripts/run-floci.sh or scripts/run-aws.sh. Floci itself is left
# running (stop it with `make floci-down`).
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="$ROOT/.run"

kill_pidfile() {
  local f="$1"
  [[ -f "$f" ]] || return 0
  local pid; pid="$(cat "$f")"
  if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
    echo "  stopping $(basename "$f" .pid) (pid $pid)"
    kill "$pid" 2>/dev/null || true
  fi
  rm -f "$f"
}

echo "==> Stopping Threadit local processes"
if [[ -d "$RUN_DIR" ]]; then
  for f in "$RUN_DIR"/*.pid; do kill_pidfile "$f"; done
fi

# Belt-and-suspenders: free the known ports if anything is still holding them.
if command -v fuser >/dev/null; then
  fuser -k 5173/tcp 8080/tcp 8081/tcp 2>/dev/null || true
fi

echo "==> Done. (Floci still running; 'make floci-down' to stop it.)"
