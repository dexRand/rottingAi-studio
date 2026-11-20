#!/usr/bin/env bash
# ============================================================================
# Quick health + integrity check.
#   ./scripts/healthcheck.sh
# Exit 0 = healthy, 1 = degraded.
# ============================================================================
set -uo pipefail

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
RC=0

check_url() {
  local name="$1" url="$2"
  if curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null | grep -q 200; then
    echo "  $name $url: ok"
  else
    echo "  $name $url: not responding (start with ./ai start)"
    RC=1
  fi
}

echo "== runtime"
if llama_bin llama-server "${LLAMA_SERVER_BIN:-llama-server}" >/dev/null; then
  echo "  llama-server: ok"
else
  echo "  llama-server: MISSING (run ./scripts/install.sh)"
  RC=1
fi

echo "== router"
if (cd "$REPO_DIR" && "$(router_python)" -m router check >/dev/null 2>&1); then
  echo "  registry: ok ($(router_python))"
else
  echo "  registry: PROBLEMS (run ./ai router-check)"
  RC=1
fi

echo "== endpoints"
check_url "llama-server" "http://127.0.0.1:$LLAMA_PORT/health"
[ "$ROUTER_ENABLED" = "1" ] && check_url "router      " "http://127.0.0.1:$ROUTER_PORT/health"

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
