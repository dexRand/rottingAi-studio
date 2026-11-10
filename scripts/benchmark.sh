#!/usr/bin/env bash
# ============================================================================
# Reproducible benchmark. Measures tokens/s (prompt + generation), load time
# and peak RSS for a given model across thread counts. Results are saved under
# benchmarks/results/<timestamp>/.
#
#   ./scripts/benchmark.sh <role> [threads...]
#   ./scripts/benchmark.sh coder "4 6 8"
#
# Distinguishes MEASURED results (this script) from third-party numbers:
# everything written to benchmarks/results/ is measured on THIS machine.
# ============================================================================
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$REPO_DIR/config/llama.cpp/roles.conf"
[ -f "$REPO_DIR/.env" ] && source "$REPO_DIR/.env"

MODELS_DIR="${MODELS_DIR:-$HOME/local-ai/models}"
LLAMA_BENCH_BIN="${LLAMA_BENCH_BIN:-llama-bench}"
# accept the source-build path if the binary is not on PATH
if ! command -v "$LLAMA_BENCH_BIN" >/dev/null 2>&1 && [ -x "$REPO_DIR/llama.cpp/build/bin/llama-bench" ]; then
  LLAMA_BENCH_BIN="$REPO_DIR/llama.cpp/build/bin/llama-bench"
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

echo "# benchmark $ROLE ($MODEL) — $(date)" | tee "$OUT/summary.txt"
echo "# hardware: $(lscpu | sed -n 's/^Model name:[[:space:]]*/CPU: /p')" | tee -a "$OUT/summary.txt"

echo "== load time (model -> first token ready)"
/usr/bin/time -f "load_time_seconds=%e peak_rss_kb=%M" -o "$OUT/load.txt" \
  "$(command -v llama-server || echo "$REPO_DIR/llama.cpp/build/bin/llama-server")" \
  --model "$MODEL_PATH" --port 0 --ctx-size 0 --threads 4 2>&1 | grep -m1 "model loaded" || true
cat "$OUT/load.txt" | tee -a "$OUT/summary.txt"

echo "== token speed (llama-bench, pp512 / tg128, 3 repeats)"
for t in $THREADS; do
  echo "--- threads=$t ---" | tee -a "$OUT/summary.txt"
  "$LLAMA_BENCH_BIN" -m "$MODEL_PATH" -t "$t" -p 512 -n 128 -r 3 2>&1 \
    | tee -a "$OUT/bench-$t.txt" \
    | grep -E "pp512|tg128|model_(size|params)" || true
done

echo
echo "Results in: $OUT/"
echo "Compare with the native-vs-docker run: same binary, model and params."
