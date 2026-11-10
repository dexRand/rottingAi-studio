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
  exec "$REPO_DIR/scripts/status.sh"
fi

# resolve role -> variables
MODEL_VAR="${ROLE^^}_MODEL"; ALIAS_VAR="${ROLE^^}_ALIAS"; CTX_VAR="${ROLE^^}_CTX"; THREADS_VAR="THREADS_${ROLE^^}"
MODEL="${!MODEL_VAR:-}"; ALIAS="${!ALIAS_VAR:-}"; CTX="${!CTX_VAR:-16384}"; THREADS="${!THREADS_VAR:-4}"
[ -n "$MODEL" ] || { echo "unknown role: $ROLE" >&2; exit 2; }

MODEL_PATH="$MODELS_DIR/$MODEL"
[ -f "$MODEL_PATH" ] || { echo "model not found: $MODEL_PATH (run ./scripts/download-models.sh $ROLE)" >&2; exit 1; }

# locate the server binary (allow a source build under llama.cpp/build/bin)
if ! command -v "$LLAMA_SERVER_BIN" >/dev/null 2>&1; then
  if [ -x "$REPO_DIR/llama.cpp/build/bin/llama-server" ]; then
    LLAMA_SERVER_BIN="$REPO_DIR/llama.cpp/build/bin/llama-server"
  else
    echo "llama-server not found. Install it: ./scripts/install.sh" >&2
    exit 1
  fi
fi

# already running? (verify the PID really is llama-server to avoid stale-PID mistakes)
if [ -f "$PID_FILE" ]; then
  PID="$(cat "$PID_FILE")"
  if kill -0 "$PID" 2>/dev/null && tr '\0' ' ' < "/proc/$PID/cmdline" 2>/dev/null | grep -q llama-server; then
    echo "llama-server already running (pid $PID). Stop it first: ./scripts/stop.sh" >&2
    exit 1
  fi
fi

API_KEY_ARGS=()
[ -n "${LLAMA_API_KEY:-}" ] && API_KEY_ARGS=(--api-key "$LLAMA_API_KEY")

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
  "${API_KEY_ARGS[@]}" \
  >"$LOG_FILE" 2>&1 &
echo $! > "$PID_FILE"

echo "   pid:    $(cat "$PID_FILE")  log: $LOG_FILE"
echo "   web UI: http://$HOST:$PORT   (OpenAI API: http://$HOST:$PORT/v1)"
