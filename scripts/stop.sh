#!/usr/bin/env bash
# ============================================================================
# Stop the router and llama-server, releasing the model from RAM (mmap is
# freed on exit).
#   ./scripts/stop.sh
# ============================================================================
set -euo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"

stop_pid "$ROUTER_PID_FILE" "router serve" "router"
stop_pid "$LLAMA_PID_FILE" llama-server "llama-server"
# Note: with mmap (default) the model pages are dropped from RAM automatically
# once the process exits — nothing else to do.
