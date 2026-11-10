# rottingAi-studio

Ecosistema AI locale minimale e riproducibile per **CPU-only, 16 GB RAM, Arch/CachyOS**.

**Filosofia:** llama.cpp nativo, nessun daemon, un modello alla volta, reattività del PC al primo posto. Docker solo per servizi ausiliari opzionali (spenti di default).

## Requisiti hardware di riferimento

- CPU Intel quad-core con AVX2 (testato su i5-8350U)
- 16 GB RAM (zram come swap)
- GPU integrata **non** usata per l'inferenza

## Struttura

```
rottingAi-studio/
├── docker-compose.yml        # solo servizi opzionali (profilo gui/rag/web-search)
├── .env.example              # copia in .env e adatta
├── config/
│   ├── llama.cpp/roles.conf  # preset per ruolo (modello, alias, ctx)
│   └── opencode/opencode.jsonc
├── scripts/                  # install, download, start/stop/status, benchmark, ai
├── models/                   # istruzioni + checksum (i GGUF NON sono in repo)
├── .opencode/
│   ├── skills/               # 28 skill (find-skills + addyosmani dev + 2 custom)
│   └── references/           # checklist condivise per le skill
├── docs/                     # architecture, models, troubleshooting
└── tests/
```

## Avvio rapido

```bash
cp .env.example .env
./scripts/install.sh native        # build llama.cpp (AVX2)  [dopo tua approvazione]
./scripts/download-models.sh --all  # scarica i 4 GGUF + checksum
./scripts/ai chat                  # web UI integrata (general)
./scripts/ai code                  # coding
./scripts/ai sysadmin              # sysadmin
./scripts/ai stop                  # ferma e libera la RAM
```

## Integrazione OpenCode

Copia `config/opencode/opencode.jsonc` nella root del progetto (o in `~/.config/opencode/`) e avvia `./scripts/ai start <role>`. I modelli appaiono come `local/coder`, `local/general`, `local/sysadmin`, `local/sysadmin-fast`.

## Skill

Il progetto include skill OpenCode vendored (offline) in `.opencode/skills/`:
`find-skills` (scoperta/installazione skill dall'ecosistema `skills.sh`) + le 25
skill di sviluppo di `addyosmani/agent-skills` (TDD, code review, debugging,
security, performance, ecc.). Elenco e licenze in `.opencode/skills/README.md`.

Vedi `docs/` per dettagli su architettura, scelta dei modelli e troubleshooting.
