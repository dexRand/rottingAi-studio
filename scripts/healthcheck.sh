#!/usr/bin/env bash
# ============================================================================
# Quick health + integrity check.
#   ./scripts/healthcheck.sh
# Exit 0 = healthy, 1 = degraded.
# ============================================================================
set -uo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[ -f "$REPO_DIR/.env" ] && source "$REPO_DIR/.env"
HOST="${LLAMA_HOST:-127.0.0.1}"
PORT="${LLAMA_PORT:-8080}"
MODELS_DIR="${MODELS_DIR:-$HOME/local-ai/models}"
RC=0

echo "== runtime"
if command -v llama-server >/dev/null 2>&1 || [ -x "$REPO_DIR/llama.cpp/build/bin/llama-server" ]; then
  echo "  llama-server: ok"
else
  echo "  llama-server: MISSING (run ./scripts/install.sh)"
  RC=1
fi

echo "== endpoint"
if curl -s -o /dev/null -w "%{http_code}" "http://$HOST:$PORT/health" 2>/dev/null | grep -q 200; then
  echo "  http://$HOST:$PORT/health: ok"
else
  echo "  http://$HOST:$PORT/health: not responding (start with ./scripts/start.sh <role>)"
  RC=1
fi

echo "== models (integrity)"
if [ -f "$MODELS_DIR/SHA256SUMS" ]; then
  if (cd "$MODELS_DIR" && sha256sum -c SHA256SUMS >/dev/null 2>&1); then
    echo "  SHA256SUMS: ok"
  else
    echo "  SHA256SUMS: MISMATCH"
    RC=1
  fi
else
  echo "  SHA256SUMS: not present yet (generate after download: sha256sum *.gguf > SHA256SUMS)"
fi

echo "== RAM headroom"
free -h | awk '/Mem:/{printf "  used %s / total %s (available %s)\n", $3, $2, $7}'

exit $RC
