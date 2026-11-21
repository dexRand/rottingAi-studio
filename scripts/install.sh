#!/usr/bin/env bash
# ============================================================================
# Install the runtime. NOT run automatically — review first.
#   ./scripts/install.sh native   -> build llama.cpp from source (best AVX2)
#   ./scripts/install.sh pacman   -> install from Arch/CachyOS repos (simpler)
# ============================================================================
set -euo pipefail

MODE="${1:-native}"

install_deps() {
  echo "== Installing helper tools (huggingface_hub for model downloads)..."
  # huggingface-cli from the python-huggingface-hub package (official repos)
  if ! command -v huggingface-cli >/dev/null 2>&1; then
    # No `pip install --user`: Debian/Arch Python is externally managed (PEP 668).
    if command -v pipx >/dev/null 2>&1; then
      pipx install huggingface_hub
    else
      echo "note: huggingface-cli not installed (optional): downloads fall back to curl." >&2
      echo "      to get it: pipx install huggingface_hub" >&2
    fi
  fi
}

case "$MODE" in
  native)
    echo "== Building llama.cpp from source (GGML_NATIVE=ON: AVX2/FMA/F16C)..."
    cd "$(dirname "${BASH_SOURCE[0]}")/.."
    if [ ! -d llama.cpp ]; then
      git clone --depth 1 https://github.com/ggml-org/llama.cpp.git
    fi
    # LLAMA_CURL only lets llama.cpp download models itself (-hf); we download
    # with ./ai download, so enable it only when the libcurl headers exist.
    CURL=OFF
    pkg-config --exists libcurl 2>/dev/null && CURL=ON
    cmake -S llama.cpp -B llama.cpp/build \
      -DCMAKE_BUILD_TYPE=Release \
      -DGGML_NATIVE=ON \
      -DGGML_OPENMP=ON \
      -DLLAMA_CURL="$CURL"
    cmake --build llama.cpp/build -j"$(nproc)"
    echo
    echo "Binaries built in: llama.cpp/build/bin/"
    echo "Add to PATH (or symlink into ~/.local/bin):"
    echo "  ln -s \"$(pwd)/llama.cpp/build/bin/llama-server\" ~/.local/bin/llama-server"
    echo "  ln -s \"$(pwd)/llama.cpp/build/bin/llama-cli\"   ~/.local/bin/llama-cli"
    echo "  ln -s \"$(pwd)/llama.cpp/build/bin/llama-bench\" ~/.local/bin/llama-bench"
    ;;
  pacman)
    echo "== Installing llama.cpp from repos..."
    sudo pacman -S --needed llama.cpp python-huggingface-hub
    ;;
  *)
    echo "usage: $0 [native|pacman]" >&2
    exit 2
    ;;
esac

install_deps

echo
echo "Next: install OpenCode (https://opencode.ai/docs):"
echo "  curl -fsSL https://opencode.ai/install | bash"
echo "Then download models: ./scripts/download-models.sh --all"
