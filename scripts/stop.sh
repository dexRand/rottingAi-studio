#!/usr/bin/env bash
# ============================================================================
# Stop llama-server and release the model from RAM (mmap is freed on exit).
#   ./scripts/stop.sh
# ============================================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PID_FILE="$REPO_DIR/runtime/llama-server.pid"

if [ ! -f "$PID_FILE" ]; then
  echo "not running (no pid file)"
  exit 0
fi

PID="$(cat "$PID_FILE")"

# Only kill if the PID really belongs to llama-server (guards against PID reuse).
if kill -0 "$PID" 2>/dev/null && tr '\0' ' ' < "/proc/$PID/cmdline" 2>/dev/null | grep -q llama-server; then
  echo "== stopping llama-server (pid $PID)..."
  kill "$PID"
  for _ in $(seq 1 20); do
    kill -0 "$PID" 2>/dev/null || break
    sleep 0.25
  done
  if kill -0 "$PID" 2>/dev/null; then
    kill -9 "$PID" 2>/dev/null || true
  fi
  echo "   stopped."
else
  echo "not running (stale pid file)"
fi

rm -f "$PID_FILE"
# Note: with mmap (default) the model pages are dropped from RAM automatically
# once the process exits — nothing else to do.
