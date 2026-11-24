#!/usr/bin/env bash
# ============================================================================
# Parse documents (PDF/DOCX/XLSX/PPTX/images) to Markdown — LOCAL, no network.
# Backend: LiteParse + OCRia-nano-1 (ONNX on CPU). Reconstructs tables; charts
# stay as images (nano has no chart model).
#
#   ./ai parse <file|folder>          → writes <name>.md into services/rag/docs/
#   ./ai parse <file|folder> --out DIR
# ============================================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LIT="${LIT_BIN:-$REPO_DIR/.venv/bin/lit}"
OUT="$REPO_DIR/services/rag/docs"

if [ "${1:-}" = "--out" ]; then
  OUT="$2"; shift 2
fi
src="${1:?usage: ./ai parse <file|folder> [--out DIR]}"

[ -x "$LIT" ] || {
  echo "liteparse non installato. Installa con:" >&2
  echo "  ./.venv/bin/pip install liteparse" >&2
  echo "  ./.venv/bin/lit models pull ocria-nano" >&2
  exit 1
}
[ -e "$src" ] || { echo "not found: $src" >&2; exit 1; }

mkdir -p "$OUT"

parse_one() {
  local f="$1" base
  base="$(basename "${f%.*}")"
  if "$LIT" parse "$f" --format markdown > "$OUT/$base.md" 2>/dev/null; then
    echo "  ✓ $base.md"
  else
    echo "  ✗ $f (parse failed)" >&2
  fi
}

n=0
if [ -d "$src" ]; then
  for f in "$src"/*; do
    [ -f "$f" ] || continue
    case "${f,,}" in
      *.pdf|*.docx|*.xlsx|*.pptx|*.png|*.jpg|*.jpeg|*.tiff|*.webp|*.bmp)
        parse_one "$f"; n=$((n+1)) ;;
    esac
  done
else
  parse_one "$src"; n=$((n+1))
fi

echo "parsed $n documenti → $OUT"
