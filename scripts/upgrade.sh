#!/usr/bin/env bash
# ============================================================================
# Upgrade / maintain the local AI stack.
#   ./scripts/upgrade.sh [all|runtime|skills|check]
#   all      (default) repo + llama.cpp + vendored skills
#   runtime  rebuild llama.cpp (source) or point to pacman
#   skills   re-sync vendored addyosmani skills + shared references
#   check    show versions / status (no changes)
# ============================================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[ -f "$REPO_DIR/.env" ] && source "$REPO_DIR/.env"
MODELS_DIR="${MODELS_DIR:-$HOME/local-ai/models}"
MODE="${1:-all}"

repo_pull() {
  echo "== repo"
  if git -C "$REPO_DIR" remote >/dev/null 2>&1; then
    git -C "$REPO_DIR" pull --ff-only || echo "   (pull failed — check network / local changes)"
  else
    echo "   no git remote configured; skip"
  fi
}

runtime_upgrade() {
  echo "== llama.cpp runtime"
  if [ -d "$REPO_DIR/llama.cpp/.git" ]; then
    git -C "$REPO_DIR/llama.cpp" pull --ff-only || true
    if [ -d "$REPO_DIR/llama.cpp/build" ]; then
      cmake --build "$REPO_DIR/llama.cpp/build" -j"$(nproc)"
      echo "   rebuilt -> llama.cpp/build/bin/"
    else
      echo "   no build dir; run: ./scripts/install.sh native"
    fi
  elif command -v llama-server >/dev/null 2>&1; then
    echo "   installed from distro; upgrade with: sudo pacman -Syu llama.cpp"
  else
    echo "   llama.cpp not present; run: ./scripts/install.sh native"
  fi
}

skills_sync() {
  echo "== skills (re-sync addyosmani/agent-skills)"
  local tmp
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT
  if git clone --depth 1 --quiet https://github.com/addyosmani/agent-skills "$tmp" 2>/dev/null; then
    cp -r "$tmp/skills/." "$REPO_DIR/.opencode/skills/"
    cp -r "$tmp/references/." "$REPO_DIR/.opencode/references/"
    echo "   synced. custom skills (local-ai, arch-sysadmin) untouched."
    echo "   note: skills removed upstream are NOT deleted here — remove manually if needed."
  else
    echo "   (network unavailable — skill sync skipped)"
  fi
}

check() {
  echo "== repo"
  git -C "$REPO_DIR" log --oneline -1
  echo "== runtime"
  if [ -d "$REPO_DIR/llama.cpp/.git" ]; then
    echo "   llama.cpp commit: $(git -C "$REPO_DIR/llama.cpp" rev-parse --short HEAD 2>/dev/null)"
  fi
  if command -v llama-server >/dev/null 2>&1; then
    echo "   llama-server: $(command -v llama-server)"
    llama-server --version 2>/dev/null | head -1 || true
  elif [ -x "$REPO_DIR/llama.cpp/build/bin/llama-server" ]; then
    echo "   llama-server: $REPO_DIR/llama.cpp/build/bin/llama-server"
  else
    echo "   llama-server: NOT installed (run ./scripts/install.sh)"
  fi
  echo "== models ($MODELS_DIR)"
  if [ -d "$MODELS_DIR" ]; then
    ls -1 "$MODELS_DIR"/*.gguf 2>/dev/null | sed 's|.*/||' | sed 's|^|   |' || echo "   (none)"
  else
    echo "   models dir not found"
  fi
  echo "== skills"
  echo "   count: $(ls -1 "$REPO_DIR/.opencode/skills" | grep -v README | wc -l)"
}

case "$MODE" in
  all)      repo_pull; runtime_upgrade; skills_sync ;;
  runtime)  runtime_upgrade ;;
  skills)   skills_sync ;;
  check)    check ;;
  *) echo "usage: $0 [all|runtime|skills|check]" >&2; exit 2 ;;
esac
