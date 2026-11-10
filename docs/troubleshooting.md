# Troubleshooting

| Sintomo | Causa probabile | Rimedio |
|---|---|---|
| `model not found` | GGUF non scaricato / path errato | `./ai download <role>`; controlla `MODELS_DIR` in `.env` |
| `already running` con modello diverso | un solo modello alla volta | `./ai stop` poi `./ai start <role>` |
| `unknown role` | ruolo non valido | ruoli: `coder general sysadmin sysadmin-fast` |
| endpoint non risponde | server non avviato | `./ai start <role>`; `./ai logs` |
| OpenCode "model unavailable" | alias non allineati | `--alias` in `start.sh` deve combaciare con `modelID` in `opencode.jsonc` |
| t/s bassi / PC bloccato | troppi thread (SMT) o swap | ridurre `THREADS_*` (4); contesto più basso; chiudere app pesanti |
| RAM saturata | modello 12B + Docker | `./ai stop`; usare `sysadmin-fast` |
| checksum mismatch | download interrotto/corrotto | ri-scaricare; `sha256sum -c SHA256SUMS` |

## Note OpenCode

- Config in `opencode.jsonc` si ricarica a caldo (niente restart).
- `limit.context` è impostato esplicitamente: OpenCode assume 200k di default
  per i modelli non in catalogo, che qui non reggerebbe.
- `capabilities.tools: true` abilita il tool calling; il server deve girare con
  `--jinja` (già impostato in `start.sh`).
