#!/usr/bin/env bash
# ============================================================================
# Show llama-server status: running? which model? RAM? health?
#   ./scripts/status.sh
# ============================================================================
set -uo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[ -f "$REPO_DIR/.env" ] && source "$REPO_DIR/.env"
HOST="${LLAMA_HOST:-127.0.0.1}"
PORT="${LLAMA_PORT:-8080}"
PID_FILE="$REPO_DIR/runtime/llama-server.pid"

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  PID="$(cat "$PID_FILE")"
  echo "status:   RUNNING (pid $PID)"
  echo "command:  $(tr '\0' ' ' < "/proc/$PID/cmdline" 2>/dev/null | tr -s ' ')"
  echo "rss:      $(awk '/VmRSS/{print $2" kB"}' "/proc/$PID/status" 2>/dev/null)"
else
  echo "status:   STOPPED (no model loaded — RAM free)"
fi

if command -v curl >/dev/null 2>&1; then
  echo -n "health:   "
  curl -s -o /dev/null -w "http %{http_code}\n" "http://$HOST:$PORT/health" || echo "unreachable"
fi

MODELS_DIR="${MODELS_DIR:-$HOME/local-ai/models}"
echo "models dir: $MODELS_DIR"
if [ -d "$MODELS_DIR" ]; then
  ls -1 "$MODELS_DIR"/*.gguf 2>/dev/null | sed 's|.*/||' | sed 's|^|  - |' || true
fi

echo "system RAM:"
free -h | sed -n '1,2p'
