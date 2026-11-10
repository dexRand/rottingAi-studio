---
name: local-ai
description: Operate the local AI runtime (llama.cpp, native). Start/stop the inference server, pick a model role (coding/general/sysadmin), check status, run benchmarks, or troubleshoot the local LLM setup. Use when the user mentions "./ai", local models, llama-server, or asks to run/stop/switch a local model.
---

# Local AI Runtime

How to operate the rottingAi-studio local AI stack on this machine.

## The stack

- llama.cpp **native** (no daemon, on-demand). `llama-server` exposes an
  OpenAI-compatible API (`/v1`) plus a built-in web UI.
- Three roles + one alternative, **one model loaded at a time**:

| Role | Model | Alias | RAM (approx) | Notes |
|---|---|---|---|---|
| `coder` | Qwen2.5-Coder-7B-Instruct Q4_K_M | `qwen2.5-coder-7b` | ~5,5 GB | coding, backend OpenCode |
| `general` | Qwen3-8B Q4_K_M | `qwen3-8b` | ~6 GB | italiano, ragionamento |
| `sysadmin` | Qwen2.5-7B-Instruct Q5_K_M | `qwen2.5-7b` | ~6 GB | tecnico, veloce (default) |
| `sysadmin-heavy` | Gemma 3 12B Q4_K_M | `gemma-3-12b` | ~9 GB | opzionale: profondità, ctx 128K |

## Commands (dalla root della repo)

```bash
./scripts/ai chat [role]      # avvia il server + apre la web UI
./scripts/ai code             # modello coding
./scripts/ai sysadmin         # modello sysadmin (7B, veloce)
./scripts/ai sysadmin-heavy   # sysadmin pesante (12B, opzionale)
./scripts/ai start <role>     # solo llama-server
./scripts/ai stop             # ferma e libera la RAM
./scripts/ai status           # in esecuzione? modello? RAM?
./scripts/ai logs             # log del server
./scripts/ai download [role]  # scarica un modello
./scripts/ai benchmark <role> # misura t/s
./scripts/ai healthcheck      # integrità + health
```

## Regole (la reattività è la priorità assoluta)

- Carica **un solo modello alla volta** (`start` rifiuta un secondo).
- Mantieni `--threads` a 4 (core fisici; l'SMT raramente aiuta e scalda).
- `stop` libera subito la RAM (rilascio mmap). Nessun daemon a riposo.
- Non caricare il 12B (`sysadmin-heavy`) con app/Docker pesanti attivi:
  il default `sysadmin` (7B) è già veloce.
- Bind solo `127.0.0.1`: mai esporre la porta pubblicamente.

## Integrazione OpenCode

Con `config/opencode/opencode.jsonc` copiato nella root del progetto e
`llama-server` in esecuzione con `--jinja`, i modelli sono selezionabili come
`local/coder`, `local/general`, `local/sysadmin`, `local/sysadmin-heavy`.

## In caso di problemi

Vedi `../../docs/troubleshooting.md` e `../../docs/architecture.md`.
I preset dei ruoli sono in `../../config/llama.cpp/roles.conf`.
