#!/usr/bin/env bash
# ============================================================================
# Colibri "super-heavy" runtime — Qwen3.6-35B-A3B (35B MoE, 3B active).
# A SEPARATE inference engine (not llama.cpp), served on its own port.
#
#   ./scripts/colibri.sh start    launch coli serve (OpenAI API on :8000)
#   ./scripts/colibri.sh stop     stop and release RAM
#   ./scripts/colibri.sh status   running? model? RAM?
#
# Requires, OUTSIDE this repo:
#   - the colibri repo    (git clone https://github.com/JustVugg/colibri ~/colibri)
#   - the model on disk   (~/colibri-models/qwen36-35b, 23 GB)
#
# Knobs live in .env: COLIBRI_DIR, COLIBRI_MODEL, COLIBRI_PORT, COLIBRI_CAP,
# COLIBRI_CTX, COLIBRI_MODEL_ID. `--cap` (expert cache slots/layer) is the one
# that matters: the colibri auto-detect is far too conservative on 16 GB RAM.
# ============================================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[ -f "$REPO_DIR/.env" ] && source "$REPO_DIR/.env"

COLIBRI_DIR="${COLIBRI_DIR:-$HOME/colibri}"
COLIBRI_MODEL="${COLIBRI_MODEL:-$HOME/colibri-models/qwen36-35b}"
COLIBRI_PORT="${COLIBRI_PORT:-8000}"
COLIBRI_CAP="${COLIBRI_CAP:-120}"
COLIBRI_CTX="${COLIBRI_CTX:-16384}"
COLIBRI_MODEL_ID="${COLIBRI_MODEL_ID:-qwen3.6-colibri}"

RUNTIME_DIR="$REPO_DIR/runtime"
PID_FILE="$RUNTIME_DIR/colibri.pid"
LOG_FILE="$RUNTIME_DIR/colibri.log"
mkdir -p "$RUNTIME_DIR"

COLI_BIN="$COLIBRI_DIR/c/coli"

CMD="${1:-start}"

usage() {
  cat <<'EOF'
Usage: ./scripts/colibri.sh <start|stop|status>
EOF
}

die() { echo "error: $*" >&2; exit 1; }

check_installed() {
  [ -f "$COLI_BIN" ] || die "colibri not found at $COLIBRI_DIR — clone it: git clone https://github.com/JustVugg/colibri $COLIBRI_DIR"
  [ -d "$COLIBRI_MODEL" ] || die "model not found at $COLIBRI_MODEL — run: cd $COLIBRI_DIR && python3 c/coli setup --yes --model qwen36-35b --no-start"
}

is_running() {
  [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null
}

start() {
  check_installed
  if is_running; then
    echo "colibri already running (pid $(cat "$PID_FILE"), port $COLIBRI_PORT)"
    return 0
  fi
  if command -v fuser >/dev/null 2>&1 && fuser "$COLIBRI_PORT/tcp" >/dev/null 2>&1; then
    echo "port $COLIBRI_PORT already in use — colibri is probably already running"
    return 0
  fi
  echo "== starting colibri super-heavy ($COLIBRI_MODEL_ID) on http://127.0.0.1:$COLIBRI_PORT"
  echo "   model: $COLIBRI_MODEL"
  echo "   cap:   $COLIBRI_CAP experts/layer   ctx: $COLIBRI_CTX"
  cd "$COLIBRI_DIR"
  nohup python3 c/coli serve \
    --model "$COLIBRI_MODEL" \
    --cap "$COLIBRI_CAP" \
    --ctx "$COLIBRI_CTX" \
    --host 127.0.0.1 \
    --port "$COLIBRI_PORT" \
    --model-id "$COLIBRI_MODEL_ID" \
    >"$LOG_FILE" 2>&1 &
  COLI_PID=$!
  echo "$COLI_PID" > "$PID_FILE"
  cd "$REPO_DIR"
  echo "   pid:   $COLI_PID   log: $LOG_FILE"
  echo "   note:  loads in ~15-30 s; each turn's first token ~10-15 s (MoE disk prefill), then ~6 t/s"
  echo "   API:   http://127.0.0.1:$COLIBRI_PORT/v1   (model id: $COLIBRI_MODEL_ID)"
}

stop() {
  if [ -f "$COLI_BIN" ]; then
    python3 "$COLI_BIN" stop >/dev/null 2>&1 || true
  fi
  command -v fuser >/dev/null 2>&1 && fuser -k "$COLIBRI_PORT/tcp" >/dev/null 2>&1 || true
  rm -f "$PID_FILE"
  echo "colibri stopped — RAM released"
}

status() {
  if is_running; then
    PID="$(cat "$PID_FILE")"
    echo "status:   RUNNING (pid $PID, port $COLIBRI_PORT)"
    echo "rss:      $(awk '/VmRSS/{print $2" kB"}' "/proc/$PID/status" 2>/dev/null)"
  else
    echo "status:   STOPPED (no model loaded — RAM free)"
  fi
  if command -v curl >/dev/null 2>&1; then
    echo -n "health:   "
    curl -s -o /dev/null -w "http %{http_code}\n" "http://127.0.0.1:$COLIBRI_PORT/health" || echo "unreachable"
  fi
  echo "model:    $COLIBRI_MODEL"
  [ -d "$COLIBRI_MODEL" ] && echo "on disk:  $(du -sh "$COLIBRI_MODEL" 2>/dev/null | cut -f1)"
  echo "system RAM:"
  free -h | sed -n '1,2p'
}

case "$CMD" in
  start)  start ;;
  stop)   stop ;;
  status) status ;;
  help|--help|-h) usage ;;
  *) usage >&2; exit 2 ;;
esac
