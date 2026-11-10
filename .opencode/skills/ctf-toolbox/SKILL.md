---
name: ctf-toolbox
description: Drive the CTF Toolbox (StegSuite + web tools) for CTF and steg/forensics work — analyze files, autosolve challenges, crack passwords, read reports — via its MCP server or the ./ctf CLI. Use when working in the CTF repo (~/__Github/CTF) or on a challenge/steg file.
---

# CTF Toolbox (StegSuite)

How to drive the CTF Toolbox (repo at `~/__Github/CTF`) as an agent.

## Two ways to interact

1. **MCP (preferred)** — StegSuite exposes an MCP server (Streamable HTTP, JSON-RPC)
   at `http://127.0.0.1:19014/api/v1/mcp`. If configured in OpenCode under
   `mcp.servers`, call the tools directly.
2. **CLI** — `./ctf up|down|status|logs <service>` to manage the Docker services.

## Typical flow (MCP)

1. `create_ctf` (name, flag_format) — start a CTF event.
2. `add_challenge` (ctf_id, name, category, files/urls, start=true) — adds and analyzes.
   Or `analyze` (name, files/urls) for a standalone project.
3. `project_status` — poll until the analysis is done.
4. `get_flags` — flags found, each with the chain of files + tool output that proves it.
5. If no flag: `get_transcript` (full context) → `run_tools` (specific analyzers,
   with a `password` if locked) / `crack` + `crack_jobs` (wordlists/mask) / `read_file`.
6. `get_report` (lang `en`|`it`) — Markdown report.

## MCP tools

`list_ctfs`, `create_ctf`, `ctf_scoreboard`, `add_challenge`, `autosolve`,
`analyze`, `project_status`, `get_flags`, `get_report`, `get_transcript`,
`read_file`, `list_tools`, `run_tools`, `locked_files`, `crack`, `crack_jobs`,
`list_wordlists`, `set_challenge`, `toolbox_services`.

## Other web tools (`toolbox_services`)

CyberChef, ZAP (proxy), Wireshark, rev sandbox (pwntools + qemu + ttyd), and more.
All bound to `127.0.0.1`, ports `19000+` (see `compose.yaml` / `.env`).

## CLI (run from `~/__Github/CTF`)

```bash
./ctf up          # core services
./ctf up web      # core + web profile
./ctf up-all      # everything
./ctf down / ./ctf status / ./ctf logs <service>
```

## Conventions (from AGENTS.md)

- **Docker-first**: never install tools on the host.
- Ports always `19000+`; only `127.0.0.1`.
- API-first: every StegSuite function is a REST endpoint (and an MCP tool); the
  SPA consumes only the API. `docs/API.md` documents it.
- Use `./ctf` for management, not raw `docker compose`.

## OpenCode MCP config (add to the CTF repo's opencode.json)

```jsonc
{
  "mcp": {
    "servers": {
      "stegsuite": {
        "type": "remote",
        "url": "http://127.0.0.1:19014/api/v1/mcp"
      }
    }
  }
}
```

If `API_KEY` is set in the CTF `.env`, the MCP endpoint expects the same
`X-API-Key` header as the REST API.
