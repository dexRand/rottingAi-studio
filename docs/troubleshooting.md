# Troubleshooting

| Sintomo | Causa probabile | Rimedio |
|---|---|---|
| `model not found` | GGUF non scaricato / path errato | `./ai download <role>`; controlla `MODELS_DIR` in `.env` |
| `already running` con modello diverso | un solo modello alla volta | `./ai stop` poi `./ai start <role>` |
| `config error: LLAMA_PORT and ROUTER_PORT` | `.env` di prima del router (`LLAMA_PORT=8080`) | `LLAMA_PORT=8081`, `ROUTER_PORT=8080` (vedi `.env.example`) |
| `router failed to start` | porta occupata / errore Python | `./ai logs router`; `ss -tlpn \| grep 8080` |
| il router non aggiunge add-on | punteggio sotto soglia / parole chiave mancanti | `./ai route "..." --show`; aggiungi keyword in `addons/registry.toml` |
| 502 dal router | llama-server non partito o ancora in caricamento | `./ai status`; `./ai logs` |
| `unknown role` | ruolo non valido | ruoli: `base lite ctf` |
| endpoint non risponde | server non avviato | `./ai start`; `./ai logs` |
| OpenCode "model unavailable" | alias non allineati | `--alias` in `start.sh` deve combaciare con `modelID` in `opencode.jsonc` |
| t/s bassi / PC bloccato | troppi thread (SMT) o swap | ridurre `THREADS` (4); contesto più basso; chiudere app pesanti; provare `lite` |
| RAM saturata | modello 9B + Docker / app pesanti | `./ai stop`; usare `lite` (4B) |
| checksum mismatch | download interrotto/corrotto | ri-scaricare; `sha256sum -c SHA256SUMS` |

## Note OpenCode

- Config in `opencode.jsonc` si ricarica a caldo (niente restart).
- `limit.context` è impostato esplicitamente: OpenCode assume 200k di default
  per i modelli non in catalogo, che qui non reggerebbe.
- `capabilities.tools: true` abilita il tool calling; il server deve girare con
  `--jinja` (già impostato in `start.sh`).
