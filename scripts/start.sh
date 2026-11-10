#!/usr/bin/env bash
# ============================================================================
# Start llama-server on-demand for a role. Loads ONE model at a time.
#   ./scripts/start.sh <role>   (coder | general | sysadmin | sysadmin-fast)
#   ./scripts/start.sh status
# ============================================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$REPO_DIR/config/llama.cpp/roles.conf"
[ -f "$REPO_DIR/.env" ] && source "$REPO_DIR/.env"

MODELS_DIR="${MODELS_DIR:-$HOME/local-ai/models}"
HOST="${LLAMA_HOST:-127.0.0.1}"
PORT="${LLAMA_PORT:-8080}"
LLAMA_SERVER_BIN="${LLAMA_SERVER_BIN:-llama-server}"
RUNTIME_DIR="$REPO_DIR/runtime"
PID_FILE="$RUNTIME_DIR/llama-server.pid"
LOG_FILE="$RUNTIME_DIR/llama-server.log"
mkdir -p "$RUNTIME_DIR"

ROLE="${1:-}"
[ -n "$ROLE" ] || { echo "usage: $0 <role> | status"; echo "roles: coder, general, sysadmin, sysadmin-fast"; exit 2; }

if [ "$ROLE" = "status" ]; then
  "$REPO_DIR/scripts/status.sh"
  exit $?
fi

# resolve role -> variables
MODEL_VAR="${ROLE^^}_MODEL"; ALIAS_VAR="${ROLE^^}_ALIAS"; CTX_VAR="${ROLE^^}_CTX"; THREADS_VAR="THREADS_${ROLE^^}"
MODEL="${!MODEL_VAR:-}"; ALIAS="${!ALIAS_VAR:-}"; CTX="${!CTX_VAR:-16384}"; THREADS="${!THREADS_VAR:-4}"
[ -n "$MODEL" ] || { echo "unknown role: $ROLE" >&2; exit 2; }

MODEL_PATH="$MODELS_DIR/$MODEL"
[ -f "$MODEL_PATH" ] || { echo "model not found: $MODEL_PATH (run ./scripts/download-models.sh $ROLE)" >&2; exit 1; }

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "llama-server already running (pid $(cat "$PID_FILE")). Stop it first: ./scripts/stop.sh" >&2
  exit 1
fi

echo "== starting llama-server ($ALIAS) on http://$HOST:$PORT"
echo "   model:  $MODEL ($(du -h "$MODEL_PATH" | cut -f1))"
echo "   ctx:    $CTX   threads: $THREADS"

nohup "$LLAMA_SERVER_BIN" \
  --model "$MODEL_PATH" \
  --alias "$ALIAS" \
  --host "$HOST" \
  --port "$PORT" \
  --ctx-size "$CTX" \
  --threads "$THREADS" \
  --jinja \
  >"$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"

echo "   pid:    $(cat "$PID_FILE")  log: $LOG_FILE"
echo "   web UI: http://$HOST:$PORT   (OpenAI API: http://$HOST:$PORT/v1)"
