"""Agent tools: run shell commands, read / write / edit files.

Everything that changes the machine (commands, writes, edits) needs the user's
approval unless the agent runs with --yes. Reading is free.
"""
from __future__ import annotations

import difflib
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

MAX_OUTPUT = 6000          # chars returned to the model per tool call
COMMAND_TIMEOUT = 120      # seconds

SPECS = [
    {"type": "function", "function": {
        "name": "run_command",
        "description": "Run a bash command on the user's Linux machine and return exit code + output "
                       "(stdout and stderr). Use it to inspect the system, run scripts and tests.",
        "parameters": {"type": "object", "properties": {
            "command": {"type": "string", "description": "the bash command line"}},
            "required": ["command"]}}},
    {"type": "function", "function": {
        "name": "read_file",
        "description": "Read a text file and return its content with line numbers.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "file path (~ allowed)"}},
            "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "write_file",
        "description": "Create a NEW text file with the given content. To change an existing file "
                       "use edit_file instead (refused on existing files unless the user asked to rewrite).",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"]}}},
    {"type": "function", "function": {
        "name": "edit_file",
        "description": "Change an existing file: replace an exact snippet with new text. `old` must "
                       "appear exactly once (copy it exactly, including indentation). Keep `old` small: "
                       "only the lines that must change. Call it once per separate change.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "old": {"type": "string"}, "new": {"type": "string"}},
            "required": ["path", "old", "new"]}}},
    {"type": "function", "function": {
        "name": "web_search",
        "description": "Search the web and return the top results (title + URL + snippet). Use it "
                       "only when the user asks for current or live information the model cannot know. "
                       "Fails with a clear message if there is no internet.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "the search query"}},
            "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "parse_document",
        "description": "Parse a document (PDF, DOCX, XLSX, image) into Markdown using a local OCR "
                       "(LiteParse + OCRia-nano). Reconstructs tables. Use it when the user asks to "
                       "read a document, invoice, report or scan. Fully local, no network.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "path to the document file"}},
            "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "kb_search",
        "description": "Search the LOCAL knowledge base (documents the user indexed into "
                       "services/rag/docs/). Returns the top fragments with their source file. "
                       "Read-only. Use it when the user asks about documentation you may not "
                       "have memorised.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string", "description": "the search query"},
            "k": {"type": "integer", "description": "number of fragments, 1-10",
                  "default": 5, "minimum": 1, "maximum": 10}},
            "required": ["query"]}}},
]


def _clip(text: str, limit: int = MAX_OUTPUT) -> str:
    if len(text) <= limit:
        return text
    half = limit // 2
    return f"{text[:half]}\n... [{len(text) - limit} chars cut] ...\n{text[-half:]}"


def _diff(path: Path, old: str, new: str) -> str:
    lines = difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True),
                                 fromfile=str(path), tofile=str(path), n=2)
    return "".join(lines) or "(no changes)"


@dataclass
class Toolbox:
    cwd: Path
    approve: Callable[[str, str], bool]     # (kind, preview) -> allowed?
    log: Callable[[str, str], None]          # (label, text)
    denied: list[str] = field(default_factory=list)
    allow_overwrite: bool = False           # set per user turn: did the user ask to rewrite?

    def _path(self, p: str) -> Path:
        path = Path(p).expanduser()
        return path if path.is_absolute() else (self.cwd / path)

    def call(self, name: str, args: dict) -> str:
        fn = getattr(self, f"t_{name}", None)
        if fn is None:
            return f"error: unknown tool '{name}'"
        try:
            return fn(**args)
        except TypeError as err:
            return f"error: bad arguments for {name}: {err}"
        except OSError as err:
            return f"error: {err}"

    # --- tools ----------------------------------------------------------------
    def t_run_command(self, command: str) -> str:
        if not self.approve("comando", command):
            self.denied.append(command)
            return "DENIED by the user: the command was not run. Do not retry it; adapt or ask."
        try:
            res = subprocess.run(["bash", "-c", command], cwd=self.cwd, capture_output=True,
                                 text=True, timeout=COMMAND_TIMEOUT)
        except subprocess.TimeoutExpired:
            return f"error: timeout after {COMMAND_TIMEOUT}s"
        out = (res.stdout + (("\n[stderr]\n" + res.stderr) if res.stderr else "")).strip()
        self.log("output", f"exit {res.returncode}\n{_clip(out, 1500) or '(nessun output)'}")
        return f"exit code {res.returncode}\n{_clip(out) or '(no output)'}"

    def t_read_file(self, path: str) -> str:
        p = self._path(path)
        text = p.read_text(encoding="utf-8", errors="replace")
        self.log("letto", f"{p} ({len(text.splitlines())} righe)")
        numbered = "\n".join(f"{i:4}| {line}" for i, line in enumerate(text.splitlines(), 1))
        return _clip(numbered, 12000)

    def t_write_file(self, path: str, content: str) -> str:
        p = self._path(path)
        if p.is_file() and not self.allow_overwrite:
            self.log("letto", f"write_file su file esistente rifiutato: {p} (usa edit_file)")
            return (f"REFUSED: {p} already exists. Do not rewrite whole files: use edit_file to change only "
                    "the lines that need it, one call per change. write_file on an existing file is allowed "
                    "only when the user explicitly asks to rewrite it.")
        old = p.read_text(encoding="utf-8") if p.is_file() else ""
        if not self.approve("scrittura", _diff(p, old, content)):
            return "DENIED by the user: the file was not written."
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"ok: wrote {p} ({len(content.splitlines())} lines)"

    def t_edit_file(self, path: str, old: str, new: str) -> str:
        p = self._path(path)
        text = p.read_text(encoding="utf-8")
        count = text.count(old)
        if count != 1:
            return f"error: `old` found {count} times in {p}, it must appear exactly once. Re-read the file."
        updated = text.replace(old, new, 1)
        if not self.approve("modifica", _diff(p, text, updated)):
            return "DENIED by the user: the file was not changed."
        p.write_text(updated, encoding="utf-8")
        return f"ok: edited {p}"

    def t_web_search(self, query: str) -> str:
        try:
            from ddgs import DDGS
        except ImportError:
            try:
                from duckduckgo_search import DDGS
            except ImportError:
                return "error: web search not installed. Install it with: ./.venv/bin/pip install ddgs"
        try:
            with DDGS() as d:
                results = list(d.text(query, max_results=5))
        except Exception as e:
            return f"error: web search failed (offline or blocked): {type(e).__name__}: {e}"
        if not results:
            return "no results."
        out = []
        for i, r in enumerate(results, 1):
            title = r.get("title") or ""
            url = r.get("href") or r.get("url") or ""
            body = (r.get("body") or "").strip()
            out.append(f"{i}. {title}\n   {url}" + (f"\n   {body}" if body else ""))
        return "\n".join(out)

    def t_kb_search(self, query: str, k: int = 5) -> str:
        try:
            k = int(k)
        except (TypeError, ValueError):
            k = 5
        k = max(1, min(10, k))
        from services.rag.kb import search
        hits = search(query, k=k)
        if not hits:
            return ("no results in the knowledge base. Drop .md/.txt files into "
                    "services/rag/docs/ and run ./ai rag-index.")
        out = [f"{i}. {h['file']} — {h['title']}\n{h['body']}" for i, h in enumerate(hits, 1)]
        return _clip("\n\n".join(out))

    def t_parse_document(self, path: str) -> str:
        p = self._path(path)
        if not p.is_file():
            return f"error: file not found: {p}"
        # The agent runs on the venv python, so `lit` is its sibling (NOT the
        # LLVM `lit` on PATH, which is a different tool).
        lit = Path(sys.executable).with_name("lit")
        try:
            r = subprocess.run([str(lit), "parse", str(p), "--format", "markdown"],
                               capture_output=True, text=True, timeout=600)
        except FileNotFoundError:
            return "error: liteparse not installed (pip install liteparse && lit models pull ocria-nano)"
        except subprocess.TimeoutExpired:
            return "error: parse timed out"
        if r.returncode != 0:
            return f"error: parse failed: {(r.stderr or '').strip()[:400]}"
        return (r.stdout or "").strip()[:12000]
