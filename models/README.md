# Modelli — istruzioni di download e integrità

I file GGUF **non** sono versionati (troppo pesanti). Vengono scaricati in
`$MODELS_DIR` (default `~/local-ai/models`) con `./ai download [ruolo|--all]`.

## Modelli (verificati su Hugging Face il 2026-11-20)

| Ruolo | Modello | File | Dimensione | Fonte |
|---|---|---|---|---|
| `base` | Qwen3.5-9B | `Qwen3.5-9B-Q4_K_M.gguf` | 5,68 GB | unsloth/Qwen3.5-9B-GGUF |
| `lite` | Qwen3.5-4B | `Qwen3.5-4B-Q4_K_M.gguf` | 2,74 GB | unsloth/Qwen3.5-4B-GGUF |
| `ctf` | WhiteRabbitNeo-2.5 (Qwen2.5-Coder-7B) | `WhiteRabbitNeo-2.5-Qwen-2.5-Coder-7B-Q4_K_M.gguf` | 4,68 GB | bartowski |

Di norma serve solo `base` (`./ai download`). `Q4_K_M` (≈4,5 bit) è il K-quant
standard di llama.cpp.

## Integrità

1. `huggingface-cli download` verifica automaticamente gli hash LFS.
2. Per fissare hash esatti e riverificare in futuro:
   ```bash
   cd ~/local-ai/models
   sha256sum *.gguf > SHA256SUMS
   sha256sum -c SHA256SUMS
   ```
   `./ai healthcheck` usa `SHA256SUMS` se presente.

## Opzioni alternative

- Quant dinamiche Unsloth (`UD-Q4_K_XL`): un po' più di qualità per bit, nessun
  beneficio di velocità su CPU. Non necessarie.
