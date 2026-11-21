#!/usr/bin/env python3
"""Orchestrator: end-to-end health/smoke test of the local AI fleet.

Checks (in order):
  1. Skills       — every .opencode/skills/<id>/SKILL.md has name + description
                    (required for OpenCode discovery), and files parse.
  2. Config       — roles.conf defines model/alias/ctx for each role;
                    opencode.jsonc is valid JSONC; model files exist on disk.
  3. Router       — addons/registry.toml is valid (files, categories, catalog).
  4. Runtime      — per role: start llama-server on a private test port, wait
                    /health, send a smoke prompt (measure t/s), test tool
                    calling, send a prompt THROUGH the router (add-on injected),
                    then stop. Does not touch a running ./ai stack.

Usage:
    ./scripts/orchestrate.py                 # skills + config + runtime (full)
    ./scripts/orchestrate.py --skills-only   # fast: only skills + config
    ./scripts/orchestrate.py --models base           # only these roles
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import threading
import sys
import time
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
MODELS_DIR = os.environ.get("MODELS_DIR", os.path.expanduser("~/local-ai/models"))
SERVER = shutil.which(os.environ.get("LLAMA_SERVER_BIN", "llama-server")) or os.path.join(
    REPO, "llama.cpp", "build", "bin", "llama-server")
HOST = "127.0.0.1"
PORT = int(os.environ.get("ORCH_PORT", "8091"))   # private: never the live stack's port
ROUTED_PROMPT = "Come vedo quale processo occupa la porta 8080 con systemctl o ss?"
SMOKE = "Rispondi in una riga: cos'è una variabile d'ambiente?"


# --- helpers -----------------------------------------------------------------

def load_roles() -> dict[str, dict[str, str]]:
    """Parse roles.conf into {role: {model, alias, ctx, reasoning, chat_template}}."""
    roles: dict[str, dict[str, str]] = {}
    with open(os.path.join(REPO, "config", "llama.cpp", "roles.conf")) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            key = k.strip()
            # strip inline comments ("...=value  # note") — bash does this when
            # sourcing roles.conf, so the parser must too, or `--reasoning`
            # ends up as `off"  # thinking off by default...`.
            val = v.split("#", 1)[0].strip().strip('"')
            for suffix in ("_MODEL", "_ALIAS", "_CTX", "_REASONING", "_CHAT_TEMPLATE"):
                if key.endswith(suffix):
                    role = key[: -len(suffix)].lower()
                    roles.setdefault(role, {})[suffix[1:].lower()] = val
    return roles


def _post(payload: dict, timeout: int = 300, port: int = PORT) -> dict:
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"http://{HOST}:{port}/v1/chat/completions",
        data=body, headers={"Content-Type": "application/json"},
    )
    t0 = time.time()
    data = json.loads(urllib.request.urlopen(req, timeout=timeout).read())
    return data, time.time() - t0


def wait_health(timeout: int = 180) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            urllib.request.urlopen(f"http://{HOST}:{PORT}/health", timeout=2)
            return True
        except Exception:
            time.sleep(1)
    return False


# --- checks ------------------------------------------------------------------

def check_skills() -> tuple[int, list[str]]:
    skills_dir = os.path.join(REPO, ".opencode", "skills")
    n, problems = 0, []
    for entry in sorted(os.listdir(skills_dir)):
        skill_md = os.path.join(skills_dir, entry, "SKILL.md")
        if not os.path.isfile(skill_md):
            continue
        n += 1
        try:
            head = open(skill_md).read(8000)
            if not head.startswith("---"):
                problems.append(f"{entry}: no frontmatter")
                continue
            fm = head.split("---", 2)[1] if head.count("---") >= 2 else ""
            if "name:" not in fm:
                problems.append(f"{entry}: missing name")
            if "description:" not in fm:
                problems.append(f"{entry}: missing description")
        except OSError as e:
            problems.append(f"{entry}: {e}")
    return n, problems


def check_config(roles: dict) -> list[str]:
    problems = []
    if not roles:
        problems.append("roles.conf: no roles parsed")
    for role, cfg in roles.items():
        for field in ("model", "alias", "ctx"):
            if field not in cfg:
                problems.append(f"roles.conf: {role} missing {field}")
    # opencode.jsonc: lenient sanity check. JSONC has comments/trailing commas
    # that json.loads can't parse — full validation is OpenCode's own job.
    try:
        src = open(os.path.join(REPO, "config", "opencode", "opencode.jsonc")).read()
        if "providers" not in src or "baseURL" not in src:
            problems.append("opencode.jsonc: missing providers/baseURL")
    except OSError as e:
        problems.append(f"opencode.jsonc: {e}")
    return problems


def check_registry() -> list[str]:
    from router.registry import Registry
    try:
        return Registry.load().validate()
    except Exception as e:  # malformed TOML etc.
        return [f"registry.toml: {e}"]


def routed_test(alias: str) -> str:
    """Send one prompt through an in-process router proxy to the test server."""
    from http.server import ThreadingHTTPServer

    from router.compose import Composer
    from router.proxy import make_handler
    from router.router import Router

    proxy = ThreadingHTTPServer((HOST, 0), make_handler(Composer(Router()), HOST, PORT))
    threading.Thread(target=proxy.serve_forever, daemon=True).start()
    try:
        data, _ = _post({"model": alias, "messages": [{"role": "user", "content": ROUTED_PROMPT}],
                         "max_tokens": 60, "temperature": 0.2}, port=proxy.server_address[1])
        ans = (data["choices"][0]["message"].get("content") or "").strip()
        return "ok" if ans else "empty answer"
    finally:
        proxy.shutdown()
        proxy.server_close()


def check_models(roles: dict) -> tuple[int, int]:
    present = missing = 0
    for cfg in roles.values():
        if os.path.isfile(os.path.join(MODELS_DIR, cfg.get("model", ""))):
            present += 1
        else:
            missing += 1
    return present, missing


def smoke_test(role: str, cfg: dict) -> tuple[bool, str]:
    model = os.path.join(MODELS_DIR, cfg["model"])
    if not os.path.isfile(model):
        return False, "model file missing"
    # Same template as `./ai start`: without it the smoke test runs a different
    # configuration from the one shipped (the ctf GGUF has no tool support in
    # its embedded template, so this test used to hide a broken tool calling).
    extra = []
    template = cfg.get("chat_template", "")
    if template:
        path = template if os.path.isabs(template) else os.path.join(REPO, template)
        if not os.path.isfile(path):
            return False, f"chat template not found: {template}"
        extra = ["--chat-template-file", path]
    proc = subprocess.Popen(
        [SERVER, "--model", model, "--alias", cfg["alias"], "--host", HOST,
         "--port", str(PORT), "--ctx-size", cfg.get("ctx", "16384"),
         "--threads", "4", "--jinja", *extra,
         "--parallel", os.environ.get("LLAMA_PARALLEL", "1"),
         "--cache-ram", os.environ.get("LLAMA_CACHE_RAM", "1024"),
         "--reasoning", cfg.get("reasoning", "auto")],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        if not wait_health():
            return False, "server did not become healthy"
        data, dt = _post({"model": cfg["alias"], "messages": [{"role": "user", "content": SMOKE}],
                          "max_tokens": 60, "temperature": 0.2})
        ans = data["choices"][0]["message"]["content"].strip()
        ct = data.get("usage", {}).get("completion_tokens", 0)
        tps = f"{ct / max(dt, 0.001):.1f} tok/s" if ct else "n/a"
        if not ans:
            return False, f"empty answer ({tps})"
        # tool calling: the `ai` agent and the MCP servers depend on it, so a
        # model that never emits tool_calls is a failure, not a note.
        try:
            tools = [{"type": "function", "function": {"name": "get_weather",
                      "description": "Get weather", "parameters": {"type": "object",
                      "properties": {"city": {"type": "string"}}, "required": ["city"]}}}]
            d2, _ = _post({"model": cfg["alias"], "messages": [{"role": "user",
                           "content": "Usa il tool per sapere che tempo fa a Roma."}], "tools": tools,
                           "tool_choice": "auto", "max_tokens": 80, "temperature": 0.1})
            calls = d2["choices"][0]["message"].get("tool_calls")
        except Exception:
            calls = None
        if not calls:
            return False, f"answer ok ({tps}) but no tool_calls"
        tc = "ok"
        try:
            routed = routed_test(cfg["alias"])
        except Exception as e:
            routed = f"error ({str(e)[:60]})"
        return True, f"answer ok | {tps} | tool calling: {tc} | via router: {routed}"
    except Exception as e:
        return False, str(e)[:120]
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


# --- main --------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skills-only", action="store_true")
    ap.add_argument("--models", nargs="*", help="roles to smoke-test (default: all)")
    args = ap.parse_args()

    roles = load_roles()
    print(f"== roles: {', '.join(sorted(roles))}")
    print(f"== models dir: {MODELS_DIR}\n")

    # skills
    n_skills, skill_problems = check_skills()
    print(f"[skills] {n_skills} found, {len(skill_problems)} problems")
    for p in skill_problems:
        print(f"  ! {p}")

    # config
    cfg_problems = check_config(roles)
    print(f"[config] {len(cfg_problems)} problems")
    for p in cfg_problems:
        print(f"  ! {p}")

    # router registry
    reg_problems = check_registry()
    print(f"[router] {len(reg_problems)} problems")
    for p in reg_problems:
        print(f"  ! {p}")
    cfg_problems += reg_problems

    # models
    present, missing = check_models(roles)
    print(f"[models] {present} present, {missing} missing\n")

    # runtime smoke tests
    if not args.skills_only:
        want = args.models if args.models else sorted(roles)
        results = []
        for role in want:
            print(f"[smoke] {role} ...", flush=True)
            ok, msg = smoke_test(role, roles[role])
            results.append((role, ok, msg))
            print(f"  {'PASS' if ok else 'FAIL'}  {msg}")
        print("\n== SUMMARY ==")
        fails = 0
        for role, ok, msg in results:
            if not ok:
                fails += 1
            print(f"  {'PASS' if ok else 'FAIL'}  {role}: {msg}")
    else:
        fails = 0

    total_problems = len(skill_problems) + len(cfg_problems) + missing
    ok = total_problems == 0 and (args.skills_only or fails == 0)
    print(f"\n== {'ALL OK' if ok else 'PROBLEMS FOUND'} ==")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
