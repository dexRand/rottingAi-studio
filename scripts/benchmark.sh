#!/usr/bin/env bash
# ============================================================================
# Reproducible benchmark with llama-bench (reports load time, prompt processing
# and generation speed across thread counts). Results saved under
# benchmarks/results/<timestamp>/.
#
#   ./scripts/benchmark.sh <role> [threads...]
#   ./scripts/benchmark.sh coder "4 6 8"
#
# Everything written to benchmarks/results/ is MEASURED on this machine.
# Peak RAM is best checked while serving: ./scripts/ai status
# ============================================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$REPO_DIR/config/llama.cpp/roles.conf"
[ -f "$REPO_DIR/.env" ] && source "$REPO_DIR/.env"

MODELS_DIR="${MODELS_DIR:-$HOME/local-ai/models}"
LLAMA_BENCH_BIN="${LLAMA_BENCH_BIN:-llama-bench}"
if ! command -v "$LLAMA_BENCH_BIN" >/dev/null 2>&1; then
  if [ -x "$REPO_DIR/llama.cpp/build/bin/llama-bench" ]; then
    LLAMA_BENCH_BIN="$REPO_DIR/llama.cpp/build/bin/llama-bench"
  else
    echo "llama-bench not found. Install it: ./scripts/install.sh" >&2
    exit 1
  fi
fi

ROLE="${1:-}"
THREADS="${2:-"2 4 6 8"}"
[ -n "$ROLE" ] || { echo "usage: $0 <role> [threads]"; exit 2; }

MODEL_VAR="${ROLE^^}_MODEL"
MODEL="${!MODEL_VAR:-}"
[ -n "$MODEL" ] || { echo "unknown role: $ROLE" >&2; exit 2; }
MODEL_PATH="$MODELS_DIR/$MODEL"
[ -f "$MODEL_PATH" ] || { echo "model not found: $MODEL_PATH" >&2; exit 1; }

TS="$(date +%Y%m%d-%H%M%S)"
OUT="$REPO_DIR/benchmarks/results/$ROLE-$TS"
mkdir -p "$OUT"

{
  echo "# benchmark $ROLE ($MODEL) — $(date)"
  echo "# hardware: $(lscpu | sed -n 's/^Model name:[[:space:]]*/CPU: /p')"
  echo "# method: llama-bench -m <model> -t <threads> -p 512 -n 128 -r 3"
  echo
} | tee "$OUT/summary.txt"

for t in $THREADS; do
  echo "== threads=$t"
  "$LLAMA_BENCH_BIN" -m "$MODEL_PATH" -t "$t" -p 512 -n 128 -r 3 2>&1 \
    | tee -a "$OUT/bench-$t.txt"
  echo
done

echo "Results in: $OUT/"
echo "Key columns: pp512 (prompt t/s), tg128 (generation t/s), load (ms)."
echo "Peak RAM while serving: ./scripts/ai start <role> && ./scripts/ai status"
