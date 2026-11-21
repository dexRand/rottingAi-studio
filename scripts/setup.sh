#!/usr/bin/env bash
# ============================================================================
# One-command setup: verify the llama.cpp binaries, download the models, and
# install the router dependencies (Magika -> file/code detection).
#
#   ./ai setup              binaries + default model + router deps
#   ./ai setup --all        + lite and ctf models
#   ./ai setup --no-router  skip the router venv
#
# Nothing is versioned: models go to $MODELS_DIR (outside the repo).
# ============================================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$REPO_DIR/scripts/lib.sh"

ALL=0
ROUTER=1
for arg in "$@"; do
  case "$arg" in
    --all)        ALL=1 ;;
    --no-router)  ROUTER=0 ;;
    *)            echo "unknown option: $arg (see ./ai setup --help)" >&2; exit 2 ;;
  esac
done

# --- 1. llama.cpp binaries ---------------------------------------------------
if ! llama_bin llama-server "${LLAMA_SERVER_BIN:-llama-server}" >/dev/null 2>&1; then
  echo "== llama-server not found."
  echo "   Build/install it first:  ./scripts/install.sh"
  echo "   (or symlink a prebuilt llama-server into ~/.local/bin)"
  exit 1
fi
echo "== llama-server: $(llama_bin llama-server "${LLAMA_SERVER_BIN:-llama-server}")"

# --- 2. models ---------------------------------------------------------------
if [ "$ALL" = "1" ]; then
  "$REPO_DIR/scripts/download-models.sh" --all
else
  "$REPO_DIR/scripts/download-models.sh" "$DEFAULT_ROLE"
fi

# --- 3. router dependencies (Magika: file / code detection) ------------------
if [ "$ROUTER" = "1" ]; then
  if [ -x "$REPO_DIR/.venv/bin/python" ]; then
    echo "== router venv already present: $REPO_DIR/.venv"
  else
    echo "== installing router deps (Magika) into $REPO_DIR/.venv"
    "$REPO_DIR/ai" router-install
  fi
fi

echo
echo "Setup complete. Next:"
echo "  ./ai start          # start base model + router"
echo "  ./ai chat           # start + open the web UI"
echo "  ./ai                # terminal agent in the current folder"
echo "  ./ai status         # model + router + RAM"
