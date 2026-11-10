# Architettura

## Decisione chiave: llama.cpp nativo, non Docker

Per l'**inferenza** Docker non introduce penalità CPU misurabile (è un processo
nativo in un namespace), ma non porta alcun beneficio su questa macchina:

- nessuna GPU da passare al container (inferenza CPU-only);
- un solo binario statico (`llama-server`);
- mmap diretto dei file modello (caricamento veloce + rilascio immediato);
- controllo semplice di thread/memoria via flag.

Docker resta (già in uso sulla macchina) **solo** per i servizi ausiliari
opzionali — Open WebUI (`profile gui`), futuri RAG/web-search — tutti spenti di
default.

## Flusso a runtime

```
./ai chat <role>
   └─ scripts/start.sh <role>        # nohup llama-server --model ... --jinja
         └─ llama-server (host, mmap del GGUF, un solo modello alla volta)
   └─ xdg-open http://127.0.0.1:8080  # web UI integrata

./ai stop   → kill + rilascio RAM (mmap)     ./ai status → pid/RSS/health
```

- **Nessun daemon**: il server vive solo finché serve.
- **Un modello alla volta**: `start.sh` rifiuta di avviarne un secondo.
- **Reattività**: `--threads 4` (core fisici, non gli 8 thread logici), context
  moderato, GPU integrata lasciata libera per il desktop.

## Tool calling e OpenCode

`llama-server --jinja` abilita il tool calling in stile OpenAI (con template
nativi per Qwen/Gemma). OpenCode (V2) si collega via provider custom
`@opencode/ai/providers/openai-compatible` a `http://127.0.0.1:8080/v1`.
Config pronta in `config/opencode/opencode.jsonc`.

## Budget RAM (16 GB)

| Scenario | RAM usata | Reattività |
|---|---|---|
| Idle (nessun modello) | ~4,5 GB | perfetta |
| Coding 7B Q4 | ~10 GB | ottima |
| General 8B Q4 | ~10,5 GB | ottima |
| Sysadmin 12B Q4 | ~13,5 GB | accettabile (chiudere app pesanti) |

## Sicurezza e accesso API

- Bind configurabile via `LLAMA_HOST` in `.env`: `127.0.0.1` (solo locale) o
  `0.0.0.0` (raggiungibile dalla LAN/altre app via API OpenAI-compatibile `/v1`).
- Se esponi sulla LAN, imposta `LLAMA_API_KEY` (auth `Authorization: Bearer`).
- Nessun socket Docker ai container AI, nessun mount della root, nessun sudo
  automatico, nessun invio dati all'esterno, approvazione esplicita dei comandi
  via OpenCode `permissions`.
