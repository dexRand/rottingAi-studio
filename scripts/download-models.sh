#!/usr/bin/env bash
# ============================================================================
# Download the GGUF models (never versioned). Run from anywhere.
#   ./scripts/download-models.sh [--all | <role>]
#
# Roles: coder, general, fast, ctf, sysadmin, sysadmin-heavy
# Uses `huggingface-cli` when available (verifies LFS integrity); falls back
# to curl with resume support.
# ============================================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[ -f "$REPO_DIR/.env" ] && source "$REPO_DIR/.env"
MODELS_DIR="${MODELS_DIR:-$HOME/local-ai/models}"
mkdir -p "$MODELS_DIR"

# repo -> filename  (verified against Hugging Face on 2026-11-10)
declare -A SPECS=(
  ["coder"]="Qwen/Qwen2.5-Coder-7B-Instruct-GGUF|qwen2.5-coder-7b-instruct-q4_k_m.gguf"
  ["general"]="Qwen/Qwen3-8B-GGUF|Qwen3-8B-Q4_K_M.gguf"
  ["fast"]="unsloth/Qwen3.5-4B-GGUF|Qwen3.5-4B-Q4_K_M.gguf"
  ["ctf"]="bartowski/WhiteRabbitNeo-2.5-Qwen-2.5-Coder-7B-GGUF|WhiteRabbitNeo-2.5-Qwen-2.5-Coder-7B-Q4_K_M.gguf"
  ["sysadmin"]="bartowski/Qwen2.5-7B-Instruct-GGUF|Qwen2.5-7B-Instruct-Q5_K_M.gguf"
  ["sysadmin-heavy"]="bartowski/google_gemma-3-12b-it-GGUF|google_gemma-3-12b-it-Q4_K_M.gguf"
)

wanted="${1:---all}"

download_one() {
  local role="$1" repo="$2" file="$3" target="$MODELS_DIR/$file"
  if [ -f "$target" ]; then
    echo "== $role: already present ($target) — skip"
    return 0
  fi
  echo "== $role: downloading $repo/$file"
  if command -v huggingface-cli >/dev/null 2>&1; then
    huggingface-cli download "$repo" "$file" --local-dir "$MODELS_DIR"
  else
    local url="https://huggingface.co/$repo/resolve/main/$file"
    if command -v curl >/dev/null 2>&1; then
      curl -L -C - -o "$target" "$url"
    elif command -v wget >/dev/null 2>&1; then
      wget -c -O "$target" "$url"
    else
      echo "error: need huggingface-cli, curl or wget" >&2
      return 1
    fi
  fi
}

run() {
  for role in "${!SPECS[@]}"; do
    IFS='|' read -r repo file <<<"${SPECS[$role]}"
    [ "$wanted" = "--all" ] || [ "$wanted" = "$role" ] || continue
    download_one "$role" "$repo" "$file"
  done
  echo
  echo "Done. Integrity note:"
  echo "  - huggingface-cli verifies LFS hashes automatically."
  echo "  - To pin exact hashes, run: sha256sum $MODELS_DIR/*.gguf > $MODELS_DIR/SHA256SUMS"
  echo "    then re-verify any time with: cd $MODELS_DIR && sha256sum -c SHA256SUMS"
}

if [ "$wanted" != "--all" ] && [ -z "${SPECS[$wanted]:-}" ]; then
  echo "usage: $0 [--all | coder | general | fast | ctf | sysadmin | sysadmin-heavy]" >&2
  exit 2
fi

run
