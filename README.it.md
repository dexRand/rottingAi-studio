<!-- [English](README.md) | Italiano -->
# rottingAi-studio

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Inferenza: solo CPU](https://img.shields.io/badge/inferenza-solo%20CPU-important)](https://github.com/ggml-org/llama.cpp)
[![OS: CachyOS / Arch](https://img.shields.io/badge/OS-CachyOS%20%2F%20Arch-blue)](https://cachyos.org/)

Uno **stack di AI locale** minimale e riproducibile per macchine CPU-only
(16 GB di RAM, AVX2), costruito su **llama.cpp** e **OpenCode**. Nessun daemon,
nessun servizio a riposo, un modello alla volta — la macchina resta reattiva
mentre lavori.

> **In breve** — sei modelli GGUF per ruolo serviti on-demand da un
> `llama-server` nativo, gestiti da una piccola CLI `./ai`, e usabili da
> OpenCode e da qualunque client OpenAI-compatibile.

---

## Perché esiste

L'inferenza LLM locale è di solito o pesante (daemon Ollama, Docker, runtime GPU)
o un consiglio generico che non calza su una macchina specifica. Questa repo è
l'opposto: un setup **nativo e on-demand** tarato su un vincolo reale — una CPU
4 core/8 thread con AVX2 e 16 GB di RAM — dove la **reattività del desktop è la
priorità assoluta**.

- Carica un modello solo quando serve, scaricalo all'istante (rilascio mmap).
- Un modello alla volta, thread limitati, contesto moderato.
- Nessun servizio sempre attivo, nessun overhead container per l'inferenza.
- Completamente offline dopo il primo download.

## Funzionalità

- 🧠 **llama.cpp nativo** (`llama-server` + `llama-cli`), build AVX2/FMA/F16C.
- 🤖 **Sei modelli per ruolo** (coding / general / fast / ctf / sysadmin + pesante opzionale).
- 🖥️ **CLI `./ai`** — start/stop/status/chat/benchmark/upgrade in un comando.
- 🔌 **API OpenAI-compatibile** su `/v1` (raggiungibile in LAN, auth Bearer opzionale).
- 🧩 **42 skill** vendored offline (find-skills + skill dev addyosmani + skill CTF ljagiello + custom).
- 🔧 **Integrazione OpenCode V2** con tool calling (`--jinja`).
- 📦 Docker Compose opzionale per GUI/RAG — tutto spento di default.
- ✅ Download modelli con verifica checksum, benchmark riproducibili.

## Requisiti

- Linux x86_64 con **AVX2** (qualsiasi CPU Intel/AMD moderna)
- **16 GB di RAM** (swap zram consigliato)
- `git`, `cmake`, `make`, un compilatore C++ (`gcc`/`clang`) per buildare llama.cpp
- Arch / CachyOS (testato); qualsiasi Linux con i requisiti sopra va bene

## Avvio rapido

```bash
git clone https://github.com/dexRand/rottingAi-studio.git
cd rottingAi-studio

cp .env.example .env                # regola host / porta / API key se serve
./scripts/install.sh native         # builda llama.cpp con -march=native
./scripts/download-models.sh --all  # scarica i 6 GGUF (con checksum)

./ai chat                   # avvia + apre la web UI integrata (general)
./ai code                   # modello coding (Qwen2.5-Coder-7B)
./ai sysadmin               # modello sysadmin (Qwen2.5-7B)
./ai stop                   # ferma e libera la RAM
```

## Utilizzo

```text
./ai chat [role]        avvia il server (se serve) + apre la web UI integrata
./ai code               modello coding (Qwen2.5-Coder-7B)
./ai fast               superfast 4B (Qwen3.5-4B)
./ai ctf                helper sicurezza (WhiteRabbitNeo-2.5)
./ai sysadmin           modello sysadmin (Qwen2.5-7B Q5)
./ai sysadmin-heavy     sysadmin pesante opzionale (Gemma 3 12B)
./ai cli [role]         chat da terminale via llama-cli (senza server)
./ai start <role>       avvia solo llama-server
./ai stop               ferma e libera la RAM
./ai status             stato runtime + modello + RAM
./ai logs               segue il log del server
./ai download [--all|<role>]
./ai benchmark <role> [threads]
./ai upgrade [all|runtime|skills|check]
./ai healthcheck        integrità + health
```

## Modelli

| Ruolo | Modello | Quant | Dimensione | RAM | Uso |
|---|---|---|---|---|---|
| `coder` | Qwen2.5-Coder-7B-Instruct | Q4_K_M | 4,68 GB | ~5,5 GB | coding, backend OpenCode |
| `general` | Qwen3-8B | Q4_K_M | 5,03 GB | ~6 GB | multilingue, ragionamento, chat |
| `fast` | Qwen3.5-4B | Q4_K_M | 2,74 GB | ~3,5 GB | superfast, task veloci |
| `ctf` | WhiteRabbitNeo-2.5 (Qwen2.5-Coder-7B) | Q4_K_M | 4,68 GB | ~5,5 GB | sicurezza / CTF / pentesting |
| `sysadmin` | Qwen2.5-7B-Instruct | Q5_K_M | 5,44 GB | ~6 GB | tecnico, veloce |
| `sysadmin-heavy` | Gemma 3 12B | Q4_K_M | 7,30 GB | ~9 GB | opzionale: profondità, contesto 128K |

I modelli vivono **fuori dalla repo** (`MODELS_DIR`, default `~/local-ai/models`) e
non sono mai versionati. Quantizzazioni e fonti in `models/README.md`.

## Integrazione OpenCode

Copia `config/opencode/opencode.jsonc` nella root del progetto (o in
`~/.config/opencode/`) e avvia `./ai start <role>`. I ruoli llama.cpp appaiono
come `local/coder`, `local/general`, `local/fast`, `local/ctf`, `local/sysadmin`
e `local/sysadmin-heavy`, tutti con tool calling abilitato.

## Accesso API

`llama-server` espone un'API OpenAI-compatibile su `/v1`. Di default è in ascolto
su `127.0.0.1`; imposta `LLAMA_HOST=0.0.0.0` in `.env` per renderla raggiungibile
dalla LAN, e `LLAMA_API_KEY` per proteggerla con `Authorization: Bearer`.

```bash
curl http://127.0.0.1:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen3-8b","messages":[{"role":"user","content":"Ciao!"}]}'
```

## Skill

42 skill sono vendored offline in `.opencode/skills/`: `find-skills`
(scopri/installa skill da `skills.sh`), 25 skill di sviluppo da
`addyosmani/agent-skills`, 11 skill CTF da `ljagiello/ctf-skills`, e 5 custom
(`local-ai`, `arch-sysadmin`, `ctf-toolbox`, `docker`, `proxmox`).

## Aggiornamento e manutenzione

```bash
./ai upgrade          # repo + llama.cpp + skill vendored
./ai upgrade check    # versioni / stato (nessuna modifica)
./ai healthcheck      # integrità modelli + endpoint + RAM
```

Vedi `docs/upgrading.md` per il quadro completo (incluso il pinning di llama.cpp/modelli).

## Struttura

```
rottingAi-studio/
├── ai -> scripts/ai  # entry point principale
├── scripts/          # install, download, start/stop/status, benchmark, upgrade, ai
├── config/
│   ├── llama.cpp/roles.conf     # preset ruolo → modello/alias/contesto
│   └── opencode/opencode.jsonc  # provider locale OpenCode
├── .opencode/
│   ├── skills/       # 42 skill vendored
│   └── references/   # checklist condivise per le skill
├── models/           # istruzioni download + checksum (GGUF non versionati)
├── docs/             # architecture, models, upgrading, troubleshooting
├── tests/            # script di test
├── docker-compose.yml# servizi opzionali (GUI/RAG) — spenti di default
└── benchmarks/results/  # output benchmark misurati
```

## Sicurezza

- In ascolto su `127.0.0.1` di default; l'esposizione in LAN è opt-in via `LLAMA_HOST`.
- Nessun socket Docker montato nei container AI, nessun mount della root host,
  nessun `sudo` automatico, nessun invio dati fuori dalla macchina, approvazione
  esplicita dei comandi agentici.

## Licenza

[MIT](LICENSE) © 2026 dexRand. Le skill vendored mantengono le loro licenze MIT
(vedi `.opencode/skills/README.md`).
