#!/usr/bin/env bash
# ============================================================================
# Shared settings for the scripts. Source it, do not run it:
#   source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
# ============================================================================
# shellcheck disable=SC2034  # variables are used by the scripts that source this

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$REPO_DIR/config/llama.cpp/roles.conf"
[ -f "$REPO_DIR/.env" ] && source "$REPO_DIR/.env"

MODELS_DIR="${MODELS_DIR:-$HOME/local-ai/models}"

# Public endpoint = the router proxy. llama-server stays internal on localhost.
ROUTER_ENABLED="${ROUTER_ENABLED:-1}"
ROUTER_HOST="${ROUTER_HOST:-${LLAMA_HOST:-127.0.0.1}}"   # LLAMA_HOST: pre-router .env files
ROUTER_PORT="${ROUTER_PORT:-8080}"
LLAMA_PORT="${LLAMA_PORT:-8081}"

if [ "$ROUTER_ENABLED" = "1" ] && [ "$LLAMA_PORT" = "$ROUTER_PORT" ]; then
  echo "config error: LLAMA_PORT and ROUTER_PORT are both $ROUTER_PORT." >&2
  echo "  llama-server is now internal: set LLAMA_PORT=8081 in .env (see .env.example)." >&2
  exit 2
fi

RUNTIME_DIR="$REPO_DIR/runtime"
LLAMA_PID_FILE="$RUNTIME_DIR/llama-server.pid"
LLAMA_LOG_FILE="$RUNTIME_DIR/llama-server.log"
ROUTER_PID_FILE="$RUNTIME_DIR/router.pid"
ROUTER_LOG_FILE="$RUNTIME_DIR/router.log"

# Where clients connect: the router, or llama-server directly if disabled.
if [ "$ROUTER_ENABLED" = "1" ]; then
  PUBLIC_HOST="$ROUTER_HOST"; PUBLIC_PORT="$ROUTER_PORT"
else
  PUBLIC_HOST="127.0.0.1"; PUBLIC_PORT="$LLAMA_PORT"
fi

# Python for the router: the repo venv (./ai router-install) if present.
router_python() {
  if [ -x "$REPO_DIR/.venv/bin/python" ]; then
    echo "$REPO_DIR/.venv/bin/python"
  else
    echo "python3"
  fi
}

# Resolve a llama.cpp binary: PATH first, then a source build in ./llama.cpp.
llama_bin() {
  local name="$1" override="$2"
  if command -v "$override" >/dev/null 2>&1; then
    command -v "$override"
  elif [ -x "$REPO_DIR/llama.cpp/build/bin/$name" ]; then
    echo "$REPO_DIR/llama.cpp/build/bin/$name"
  else
    return 1
  fi
}

# Is the PID in <pidfile> alive AND its command line matching <pattern>?
# (guards against stale pid files and PID reuse)
pid_alive() {
  local pid_file="$1" pattern="$2" pid cmd
  [ -f "$pid_file" ] || return 1
  pid="$(cat "$pid_file")"
  kill -0 "$pid" 2>/dev/null || return 1
  # no `tr | grep -q` pipe: with pipefail, grep's early exit SIGPIPEs tr -> false negative
  cmd="$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null)"
  [[ "$cmd" == *"$pattern"* ]]
}

# Stop the process of <pidfile> (TERM, then KILL after ~5 s).
stop_pid() {
  local pid_file="$1" pattern="$2" name="$3" pid
  if ! pid_alive "$pid_file" "$pattern"; then
    [ -f "$pid_file" ] && echo "$name: not running (stale pid file)" || echo "$name: not running"
    rm -f "$pid_file"
    return 0
  fi
  pid="$(cat "$pid_file")"
  echo "== stopping $name (pid $pid)..."
  kill "$pid"
  for _ in $(seq 1 20); do
    kill -0 "$pid" 2>/dev/null || break
    sleep 0.25
  done
  kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null || true
  rm -f "$pid_file"
  echo "   stopped."
}
