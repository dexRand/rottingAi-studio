<!-- English | [Italiano](README.it.md) -->
# rottingAi-studio

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Inference: CPU-only](https://img.shields.io/badge/inference-CPU--only-important)](https://github.com/ggml-org/llama.cpp)
[![OS: CachyOS / Arch](https://img.shields.io/badge/OS-CachyOS%20%2F%20Arch-blue)](https://cachyos.org/)

A minimal, reproducible **local AI stack** for CPU-only machines (16 GB RAM, AVX2),
built on **llama.cpp** and **OpenCode**. No daemons, no idle services, one model at
a time — the machine stays responsive while you work.

> **TL;DR** — three GGUF models (coding / general / sysadmin) served on demand by a
> native `llama-server`, driven by a small `./ai` CLI, and usable from OpenCode and
> any OpenAI-compatible client.

---

## Why this exists

Local LLM inference is usually either heavy (Ollama daemon, Docker, GPU runtimes)
or generic advice that doesn't fit a specific machine. This repo is the opposite:
a **native, on-demand** setup tuned for a real constraint — a 4-core/8-thread CPU
with AVX2 and 16 GB of RAM — where **desktop responsiveness is the top priority**.

- Load a model only when you need it, unload it instantly (mmap release).
- One model at a time, bounded threads, moderate context.
- No always-on services, no container overhead for inference.
- Fully offline after the first download.

## Features

- 🧠 **Native llama.cpp** (`llama-server` + `llama-cli`), AVX2/FMA/F16C build.
- 🤖 **Three role-tuned models** + a fast alternative (see [Models](#models)).
- 🖥️ **`./ai` CLI** — start/stop/status/chat/benchmark/upgrade in one command.
- 🔌 **OpenAI-compatible API** on `/v1` (LAN-reachable, optional Bearer auth).
- 🧩 **28 skills** vendored offline (find-skills + addyosmani dev skills + 2 custom).
- 🔧 **OpenCode V2** integration with tool calling (`--jinja`).
- 📦 Optional Docker Compose for GUI/RAG — all off by default.
- ✅ Checksum-verified model downloads, reproducible benchmarks.

## Requirements

- Linux x86_64 with **AVX2** (any modern Intel/AMD CPU)
- **16 GB RAM** (zram swap recommended)
- `git`, `cmake`, `make`, a C++ compiler (`gcc`/`clang`) to build llama.cpp
- Arch / CachyOS (tested); any Linux with the above works too

## Quick start

```bash
git clone https://github.com/dexRand/rottingAi-studio.git
cd rottingAi-studio

cp .env.example .env                # adjust host / port / API key if needed
./scripts/install.sh native         # build llama.cpp with -march=native
./scripts/download-models.sh --all  # download the 4 GGUFs (with checksums)

./scripts/ai chat                   # start + open the built-in web UI (general)
./scripts/ai code                   # coding model (Qwen2.5-Coder-7B)
./scripts/ai sysadmin               # sysadmin model (Gemma 3 12B)
./scripts/ai stop                   # stop and free the RAM
```

## Usage

```text
./ai chat [role]        start server (if needed) + open the built-in web UI
./ai code               coding model (Qwen2.5-Coder-7B)
./ai fast               superfast 4B model (Qwen3.5-4B)
./ai ctf                security helper (WhiteRabbitNeo-2.5)
./ai sysadmin           sysadmin model (Qwen2.5-7B Q5)
./ai sysadmin-heavy     optional heavy sysadmin (Gemma 3 12B)
./ai cli [role]         terminal chat via llama-cli (no server)
./ai start <role>       start llama-server only
./ai stop               stop and free RAM
./ai status             runtime + model + RAM status
./ai logs               follow the server log
./ai download [--all|<role>]
./ai benchmark <role> [threads]
./ai upgrade [all|runtime|skills|check]
./ai healthcheck        integrity + health
```

## Models

| Role | Model | Quant | Size | RAM | Use |
|---|---|---|---|---|---|
| `coder` | Qwen2.5-Coder-7B-Instruct | Q4_K_M | 4.68 GB | ~5.5 GB | coding, OpenCode backend |
| `general` | Qwen3-8B | Q4_K_M | 5.03 GB | ~6 GB | Italian, reasoning, chat |
| `fast` | Qwen3.5-4B | Q4_K_M | 2.74 GB | ~3.5 GB | superfast, quick tasks |
| `ctf` | WhiteRabbitNeo-2.5 (Qwen2.5-Coder-7B) | Q4_K_M | 4.68 GB | ~5.5 GB | security / CTF / pentesting |
| `sysadmin` | Qwen2.5-7B-Instruct | Q5_K_M | 5.44 GB | ~6 GB | technical, fast |
| `sysadmin-heavy` | Gemma 3 12B | Q4_K_M | 7.30 GB | ~9 GB | optional: depth, 128K context |

Models live **outside the repo** (`MODELS_DIR`, default `~/local-ai/models`) and are
never versioned. Quant types and sources are documented in `models/README.md`.

## OpenCode integration

Copy `config/opencode/opencode.jsonc` to your project root (or
`~/.config/opencode/`) and start `./ai start <role>`. The models appear as
`local/coder`, `local/general`, `local/sysadmin`, `local/sysadmin-heavy` with tool
calling enabled.

## API access

`llama-server` exposes an OpenAI-compatible API at `/v1`. By default it binds to
`127.0.0.1`; set `LLAMA_HOST=0.0.0.0` in `.env` to make it reachable from the LAN,
and `LLAMA_API_KEY` to protect it with `Authorization: Bearer`.

```bash
curl http://127.0.0.1:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen3-8b","messages":[{"role":"user","content":"Hello!"}]}'
```

## Skills

28 skills are vendored offline in `.opencode/skills/`:
`find-skills` (discover/install skills from `skills.sh`), 25 development skills from
`addyosmani/agent-skills`, and two custom ones (`local-ai`, `arch-sysadmin`).

## Upgrading & maintenance

```bash
./ai upgrade          # repo + llama.cpp + vendored skills
./ai upgrade check    # versions / status (no changes)
./ai healthcheck      # model integrity + endpoint + RAM
```

See `docs/upgrading.md` for the full picture (including pinning llama.cpp/models).

## Project structure

```
rottingAi-studio/
├── scripts/          # install, download, start/stop/status, benchmark, upgrade, ai
├── config/
│   ├── llama.cpp/roles.conf     # role → model/alias/context presets
│   └── opencode/opencode.jsonc  # OpenCode local provider
├── .opencode/
│   ├── skills/       # 28 vendored skills
│   └── references/   # shared checklists for the skills
├── models/           # download instructions + checksums (GGUFs not versioned)
├── docs/             # architecture, models, upgrading, troubleshooting
├── tests/            # test scripts
├── docker-compose.yml# optional services (GUI/RAG) — off by default
└── benchmarks/results/  # measured benchmark output
```

## Security

- Binds to `127.0.0.1` by default; LAN exposure is opt-in via `LLAMA_HOST`.
- No Docker socket mounted into AI containers, no root host mounts, no automatic
  `sudo`, no data sent off-machine, explicit approval for agent commands.

## License

[MIT](LICENSE) © 2026 dexRand. Vendored skills retain their own MIT licenses
(see `.opencode/skills/README.md`).
