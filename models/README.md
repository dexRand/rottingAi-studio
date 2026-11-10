# Modelli — istruzioni di download e integrità

I file GGUF **non** sono versionati (troppo pesanti). Vengono scaricati in
`$MODELS_DIR` (default `~/local-ai/models`) tramite `scripts/download-models.sh`.

## Modelli raccomandati (verificati su Hugging Face il 2026-11-10)

| Ruolo | Modello | File | Dimensione | Fonte |
|---|---|---|---|---|
| Coding | Qwen2.5-Coder-7B-Instruct | `qwen2.5-coder-7b-instruct-q4_k_m.gguf` | 4,68 GB | ufficiale Qwen |
| General / IT | Qwen3-8B | `Qwen3-8B-Q4_K_M.gguf` | 5,03 GB | ufficiale Qwen |
| Sysadmin (qualità) | Gemma 3 12B | `google_gemma-3-12b-it-Q4_K_M.gguf` | 7,30 GB | community bartowski |
| Sysadmin (veloce) | Qwen2.5-7B-Instruct | `Qwen2.5-7B-Instruct-Q5_K_M.gguf` | 5,44 GB | community bartowski |

Quantizzazioni: `Q4_K_M` (≈4,5 bit) e `Q5_K_M` (≈5,5 bit) sono i K-quant
standard di llama.cpp. Non sono i pesi originali FP16 (≈15 GB per un 7B).

## Integrità

1. `huggingface-cli download` verifica automaticamente gli hash LFS.
2. Per fissare hash esatti e riverificare in futuro:
   ```bash
   cd ~/local-ai/models
   sha256sum *.gguf > SHA256SUMS
   sha256sum -c SHA256SUMS
   ```
   `scripts/healthcheck.sh` usa `SHA256SUMS` se presente.

## Opzioni alternative

- Quant dinamiche Unsloth (`UD-Q4_K_XL`, via bartowski/unsloth): utilizzabili
  dentro llama.cpp se vuoi risparmiare qualche punto di qualità/perplexità,
  senza alcun beneficio di velocità su CPU. Non necessarie.
- Tutto da un'unica fonte community: `bartowski/...` ripubblica anche
  Qwen3-8B e Qwen2.5-Coder, se preferisci uniformità di origine.
