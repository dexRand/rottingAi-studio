#!/usr/bin/env bash
# ============================================================================
# Start the stack: ONE model in llama-server + the router proxy in front.
#   ./scripts/start.sh [role]     role: base (default) | lite | ctf
#   ./scripts/start.sh status
#
#   clients -> router  http://$ROUTER_HOST:$ROUTER_PORT  (public, adds add-ons)
#           -> llama-server http://127.0.0.1:$LLAMA_PORT (internal)
# Set ROUTER_ENABLED=0 in .env to run llama-server alone (no add-ons).
# ============================================================================
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
mkdir -p "$RUNTIME_DIR"

ROLE="${1:-$DEFAULT_ROLE}"
if [ "$ROLE" = "status" ]; then
  exec "$REPO_DIR/scripts/status.sh"
fi

# resolve role -> variables
MODEL_VAR="${ROLE^^}_MODEL"; ALIAS_VAR="${ROLE^^}_ALIAS"; CTX_VAR="${ROLE^^}_CTX"; THREADS_VAR="THREADS_${ROLE^^}"; REASONING_VAR="${ROLE^^}_REASONING"
MODEL="${!MODEL_VAR:-}"; ALIAS="${!ALIAS_VAR:-}"; CTX="${!CTX_VAR:-16384}"; THREADS="${!THREADS_VAR:-${THREADS:-4}}"; REASONING="${!REASONING_VAR:-auto}"
TEMPLATE_VAR="${ROLE^^}_CHAT_TEMPLATE"; TEMPLATE="${!TEMPLATE_VAR:-}"
[ -n "$MODEL" ] || { echo "unknown role: $ROLE (roles: base, lite, ctf)" >&2; exit 2; }

MODEL_PATH="$MODELS_DIR/$MODEL"
[ -f "$MODEL_PATH" ] || { echo "model not found: $MODEL_PATH (run ./ai download $ROLE)" >&2; exit 1; }

LLAMA_SERVER="$(llama_bin llama-server "${LLAMA_SERVER_BIN:-llama-server}")" \
  || { echo "llama-server not found. Install it: ./scripts/install.sh" >&2; exit 1; }

# --- llama-server (one model at a time) --------------------------------------
if pid_alive "$LLAMA_PID_FILE" llama-server; then
  RUNNING="$(tr '\0' ' ' < "/proc/$(cat "$LLAMA_PID_FILE")/cmdline" | grep -o -- "--alias [^ ]*" | cut -d' ' -f2)"
  if [ "$RUNNING" = "$ALIAS" ]; then
    echo "llama-server already running with $ALIAS (pid $(cat "$LLAMA_PID_FILE"))"
  else
    echo "llama-server already running with $RUNNING. One model at a time: ./ai stop first." >&2
    exit 1
  fi
else
  API_KEY_ARGS=()
  [ -n "${LLAMA_API_KEY:-}" ] && API_KEY_ARGS=(--api-key "$LLAMA_API_KEY")
  # Memory: llama-server's defaults (4 slots x full context, prompt cache up to
  # 8 GB) took 7.8 GB of RAM on a 16 GB machine and pushed the model weights
  # out of memory -> re-read from disk at every token (1 t/s). One user, one
  # conversation: 1 slot, and a small prompt cache to swap conversations.
  MEM_ARGS=(--parallel "${LLAMA_PARALLEL:-1}" --cache-ram "${LLAMA_CACHE_RAM:-1024}")
  TEMPLATE_ARGS=()
  if [ -n "$TEMPLATE" ]; then
    [ -f "$REPO_DIR/$TEMPLATE" ] || { echo "chat template not found: $TEMPLATE" >&2; exit 1; }
    TEMPLATE_ARGS=(--chat-template-file "$REPO_DIR/$TEMPLATE")
  fi

  echo "== starting llama-server ($ALIAS) on http://127.0.0.1:$LLAMA_PORT (internal)"
  echo "   model:  $MODEL ($(du -h "$MODEL_PATH" | cut -f1))"
  echo "   ctx:    $CTX   threads: $THREADS   reasoning: $REASONING   slots: ${LLAMA_PARALLEL:-1}   prompt cache: ${LLAMA_CACHE_RAM:-1024} MiB"
  [ -n "$TEMPLATE" ] && echo "   template: $TEMPLATE"

  # Bound to localhost on purpose: LAN access goes through the router.
  nohup "$LLAMA_SERVER" \
    --model "$MODEL_PATH" \
    --alias "$ALIAS" \
    --host 127.0.0.1 \
    --port "$LLAMA_PORT" \
    --ctx-size "$CTX" \
    --threads "$THREADS" \
    --jinja \
    --reasoning "$REASONING" \
    "${MEM_ARGS[@]}" "${API_KEY_ARGS[@]}" "${TEMPLATE_ARGS[@]}" \
    >"$LLAMA_LOG_FILE" 2>&1 &
  echo $! > "$LLAMA_PID_FILE"
  echo "   pid:    $(cat "$LLAMA_PID_FILE")  log: $LLAMA_LOG_FILE"
fi

# --- router proxy ------------------------------------------------------------
if [ "$ROUTER_ENABLED" = "1" ]; then
  if pid_alive "$ROUTER_PID_FILE" "router serve"; then
    echo "router already running (pid $(cat "$ROUTER_PID_FILE"))"
  else
    PY="$(router_python)"
    echo "== starting router on http://$ROUTER_HOST:$ROUTER_PORT ($PY)"
    # no ( subshell ): $! must be the router's own pid, not a forked shell's
    cd "$REPO_DIR"
    nohup "$PY" -m router serve \
      --host "$ROUTER_HOST" --port "$ROUTER_PORT" --upstream-port "$LLAMA_PORT" \
      >"$ROUTER_LOG_FILE" 2>&1 &
    echo $! > "$ROUTER_PID_FILE"
    sleep 0.5
    if ! pid_alive "$ROUTER_PID_FILE" "router serve"; then
      echo "   router failed to start, see $ROUTER_LOG_FILE:" >&2
      tail -5 "$ROUTER_LOG_FILE" >&2
      exit 1
    fi
    echo "   pid:    $(cat "$ROUTER_PID_FILE")  log: $ROUTER_LOG_FILE"
  fi
else
  echo "== router disabled (ROUTER_ENABLED=0): clients talk to llama-server directly"
fi

echo "   web UI: http://$PUBLIC_HOST:$PUBLIC_PORT   (OpenAI API: http://$PUBLIC_HOST:$PUBLIC_PORT/v1)"
