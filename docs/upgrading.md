# Aggiornamento e manutenzione

## Comando unico

```bash
./scripts/ai upgrade            # repo + llama.cpp + skills (il solito)
./scripts/ai upgrade check      # mostra versioni/stato (nessuna modifica)
./scripts/ai upgrade runtime    # ricompila solo llama.cpp
./scripts/ai upgrade skills     # ri-sincronizza le skill addyosmani
```

## Cosa si aggiorna e come

| Componente | Come | Frequenza |
|---|---|---|
| **Repo** (script, config, docs) | `git pull` (via `upgrade`) | quando serve |
| **llama.cpp** | `upgrade runtime` (git pull + `cmake --build`) | spesso (release frequenti con speedup CPU) |
| **Skill addyosmani** | `upgrade skills` (ri-clona e ricopia `skills/` + `references/`) | quando serve |
| **Skill custom** (`local-ai`, `arch-sysadmin`) | manuale (sono tue, non toccate da `skills`) | quando vuoi |
| **find-skills** | `npx skills update` o ri-copia da vercel-labs/skills | raro |
| **Modelli** | manuale (vedi sotto) | quando esce un modello/quant migliore |

## Aggiornare i modelli (manuale, voluto)

I modelli sono una scelta "pinnata", non si aggiornano da soli. Per cambiare
modello/quant:

1. Scegli il nuovo GGUF e il suo file/alias.
2. Aggiorna `config/llama.cpp/roles.conf` (file + alias + ctx).
3. Aggiorna `config/opencode/opencode.jsonc` (il `modelID` deve combaciare con
   l'alias).
4. `./scripts/ai download <role>` e `./scripts/ai benchmark <role>`.

## Riproducibilità / pinning (opzionale)

Per congelare una configurazione nota-buona:

- **llama.cpp**: fare `git -C llama.cpp checkout <tag>` prima del build
  (es. un tag di release), invece di inseguire l'ultimo commit.
- **Modelli**: il checksum in `models/SHA256SUMS` garantisce l'integrità.
- **Repo**: i tag git (`git tag`) fissano uno snapshot.

## Manutenzione quotidiana

```bash
./scripts/ai healthcheck   # integrità modelli + health endpoint + RAM
./scripts/ai status        # runtime + modello + RAM
./scripts/ai logs          # log del server
```
