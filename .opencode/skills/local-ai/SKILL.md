---
name: local-ai
description: Operate the local AI runtime (llama.cpp + router, native). Start/stop the base model and the router, check status, see which add-ons the router picks, run benchmarks, or troubleshoot the local LLM setup. Use when the user mentions "./ai", local models, llama-server, the router, add-ons, or asks to run/stop the local model.
---

# Local AI Runtime

How to operate the rottingAi-studio local AI stack on this machine.

## The stack

- **One base model always loaded** in a native `llama-server` (internal,
  `127.0.0.1:8081`). No model switching: it would throw away the KV cache.
- A **router proxy** in front (`127.0.0.1:8080`, OpenAI API `/v1`) picks a
  category (`coding`, `sysadmin`) and add-ons for each request and appends them
  at the end of the context. The user's prompt stays intact.

| Role | Model | Alias | Notes |
|---|---|---|---|
| `base` | Qwen3.5-9B Q4_K_M | `qwen3.5-9b` | default, always on, thinking off |
| `lite` | Qwen3.5-4B Q4_K_M | `qwen3.5-4b` | faster alternative, instead of base |
| `ctf` | WhiteRabbitNeo-2.5 Q4_K_M | `whiterabbitneo-7b` | rare exception, security / CTF |

## Commands (from the repo root)

```bash
./ai chat                 # model + router + web UI
./ai start [role]         # model + router only
./ai stop                 # stop everything, free RAM
./ai status               # model, router, RAM, health
./ai logs [router]        # llama-server or router log
./ai route "testo" --show # which category/add-ons the router would add
./ai route-eval           # router accuracy on router/examples/*.jsonl
./ai router-check         # validate addons/registry.toml
./ai benchmark [role]     # measure t/s
./ai healthcheck          # integrity + health
```

## Rules

- **One model at a time**: `start` refuses a second one; `./ai stop` first.
- Keep `THREADS` at the physical core count; SMT rarely helps.
- Add-ons are never unloaded mid-conversation; a new conversation starts clean.
- Bind only `127.0.0.1` unless the user explicitly wants LAN access
  (`ROUTER_HOST=0.0.0.0` + `LLAMA_API_KEY`).
- `ROUTER_ENABLED=0` runs llama-server alone (no add-ons), for comparisons.

## Adding an add-on

1. Write a dense Markdown file under `addons/<category>/`.
2. Add an `[addons.<id>]` entry in `addons/registry.toml` (category, type, file,
   label, magika labels, keywords).
3. `./ai router-check`, then `./ai route "..." --show` to see it triggered.

## OpenCode

With `config/opencode/opencode.jsonc` in the project and `./ai start` running,
the model is `local/base` (tool calling on), served through the router.

## Troubleshooting

See `../../docs/troubleshooting.md` and `../../docs/architecture.md`.
Model presets: `../../config/llama.cpp/roles.conf`; router settings:
`../../config/router.toml`.
