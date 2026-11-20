#!/usr/bin/env bash
# ============================================================================
# Show the stack status: model, router, RAM, health.
#   ./scripts/status.sh
# ============================================================================
set -uo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

if pid_alive "$LLAMA_PID_FILE" llama-server; then
  PID="$(cat "$LLAMA_PID_FILE")"
  echo "model:    RUNNING (pid $PID) $(tr '\0' ' ' < "/proc/$PID/cmdline" | grep -o -- "--alias [^ ]*" | cut -d' ' -f2)"
  echo "rss:      $(awk '/VmRSS/{print $2" kB"}' "/proc/$PID/status" 2>/dev/null)"
else
  echo "model:    STOPPED (no model loaded — RAM free)"
fi

if [ "$ROUTER_ENABLED" = "1" ]; then
  if pid_alive "$ROUTER_PID_FILE" "router serve"; then
    echo "router:   RUNNING (pid $(cat "$ROUTER_PID_FILE")) http://$ROUTER_HOST:$ROUTER_PORT"
  else
    echo "router:   STOPPED"
  fi
else
  echo "router:   disabled (ROUTER_ENABLED=0)"
fi

if command -v curl >/dev/null 2>&1; then
  echo -n "health:   llama-server "
  curl -s -o /dev/null -w "http %{http_code}\n" "http://127.0.0.1:$LLAMA_PORT/health" || echo "unreachable"
  if [ "$ROUTER_ENABLED" = "1" ]; then
    echo -n "          via router   "
    curl -s -o /dev/null -w "http %{http_code}\n" "http://127.0.0.1:$ROUTER_PORT/health" || echo "unreachable"
  fi
fi

echo "models dir: $MODELS_DIR"
if [ -d "$MODELS_DIR" ]; then
  ls -1 "$MODELS_DIR"/*.gguf 2>/dev/null | sed 's|.*/||' | sed 's|^|  - |' || true
fi

echo "system RAM:"
free -h | sed -n '1,2p'
