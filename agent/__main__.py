"""`ai` — a small Claude-Code-style terminal agent on the local model.

    ai                   open a chat session in the current directory
    ai "prompt"          open the session with this prompt already running
    ai -p "prompt"       one shot: run the prompt, print, exit (scripts)
    ai -a "prompt"       auto mode: commands and file changes run WITHOUT asking
    (ai opens the chat in a new terminal window; --here keeps the current one)

The model can run shell commands and read / write / edit files. Every command
and file change asks for approval: [s]ì / [N]o / [a] sì a tutto (or /yes).

Shown while it works: router decision, the model's thinking, tool calls and
their output, and stats (prompt tokens processed vs. reused from the KV cache).
Everything is also logged to runtime/agent.log (JSON lines).
"""
from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import shutil
import subprocess
import sys
import termios
import threading
import time
import urllib.error
import urllib.request
import uuid
from datetime import date
from pathlib import Path

from .tools import SPECS, Toolbox

REPO = Path(__file__).resolve().parent.parent
LOG_FILE = REPO / "runtime" / "agent.log"
HISTORY_FILE = REPO / "runtime" / "agent_history"
# the user explicitly wants a whole file rewritten -> write_file may overwrite this turn
REWRITE_RE = re.compile(r"riscriv|rifai (tutto|il file|da capo)|da zero|sovrascriv|rewrite|from scratch|overwrite",
                        re.IGNORECASE)
MAX_STEPS = 20

SYSTEM = """You are a command-line agent running locally on the user's Linux machine.
Today is {today}. User: {user}. Current directory: {cwd}. Home: {home} (Desktop: {home}/Desktop).

You can act on the machine with tools: run_command, read_file, write_file, edit_file.
- Investigate before changing: read files and run commands to check facts. Never guess file contents.
- To fix code: read it, change it with edit_file, then RUN it to verify.
- Existing files: ALWAYS edit_file, one call per separate change, `old` = only the lines that change.
  write_file is for NEW files (it is refused on existing files unless the user asked for a rewrite).
- Change only what the task needs. Do not refactor, add docstrings/types, rename, reformat or "improve"
  code you were not asked about. Report only real bugs you verified.
- The user approves every command and file change. If something is denied, do not retry it: adapt or ask.
- Keep going with tools until the task is done or you are blocked, then stop calling tools.
- Final answer: short, in the user's language: what you found, what you changed, the result."""

HELP = """comandi:
  /help          questo aiuto
  /clear         nuova conversazione (contesto e add-on azzerati)
  /think on|off  ragionamento del modello (on = più lento, più accurato)
  /auto          auto mode: esegue comandi e modifiche senza chiedere (di nuovo: torna a chiedere)
  /exit          esci (anche Ctrl+D)
  Ctrl+C         interrompe la risposta in corso"""

# --- terminal output ------------------------------------------------------------
TTY = sys.stderr.isatty()
# stealth mode: no working chatter on the terminal, only the final notification
QUIET = False
COLORS = {"router": "36", "think": "2;3", "tool": "33", "output": "90", "stats": "35",
          "letto": "90", "error": "31", "info": "32", "dim": "2", "bold": "1"}


def paint(label: str, text: str) -> str:
    return f"\033[{COLORS.get(label, '0')}m{text}\033[0m" if TTY else text


def log(label: str, text: str) -> None:
    if QUIET:
        return
    print(paint(label, f"  {'⎿' if label in ('output', 'letto') else '●'} {text}"), file=sys.stderr, flush=True)


def jlog(event: str, **data) -> None:
    LOG_FILE.parent.mkdir(exist_ok=True)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"t": time.strftime("%H:%M:%S"), "event": event, **data}, ensure_ascii=False) + "\n")


class Spinner:
    """`⠋ leggo il prompt… 12s` on stderr until the first token arrives."""
    FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

    def __init__(self, text: str) -> None:
        self.text, self._stop = text, threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        t0, i = time.time(), 0
        while not self._stop.wait(0.1):
            print(f"\r{paint('dim', f'  {self.FRAMES[i % 10]} {self.text} {time.time() - t0:.0f}s')}",
                  end="", file=sys.stderr, flush=True)
            i += 1

    def __enter__(self) -> Spinner:
        if TTY and not QUIET:
            self._thread.start()
        return self

    def stop(self) -> None:
        if QUIET:
            self._stop.set()
            return
        if not self._stop.is_set():
            self._stop.set()
            if TTY:
                self._thread.join()
                print("\r\033[K", end="", file=sys.stderr, flush=True)

    def __exit__(self, *exc) -> None:
        self.stop()


class Keyboard:
    """While the model works, keys typed are neither echoed nor kept.

    Without this, text typed during a long generation sits in the terminal
    buffer and is read later as the next prompt, or as an approval answer.
    """

    def __init__(self) -> None:
        self.fd = sys.stdin.fileno() if sys.stdin.isatty() else None
        self.saved = termios.tcgetattr(self.fd) if self.fd is not None else None

    def lock(self) -> None:
        if self.fd is None:
            return
        quiet = termios.tcgetattr(self.fd)
        quiet[3] &= ~(termios.ECHO | termios.ICANON)       # Ctrl+C (ISIG) still works
        termios.tcsetattr(self.fd, termios.TCSADRAIN, quiet)

    def unlock(self) -> None:
        """Restore normal input and drop whatever was typed meanwhile."""
        if self.fd is None:
            return
        termios.tcflush(self.fd, termios.TCIFLUSH)
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self.saved)


KEYBOARD: Keyboard | None = None


# --- approvals -------------------------------------------------------------------
class Approver:
    def __init__(self, yes: bool) -> None:
        self.all = yes

    def __call__(self, kind: str, preview: str) -> bool:
        if not QUIET:
            print(paint("tool", f"  ┌─ {kind}"), file=sys.stderr)
            for line in preview.rstrip().splitlines():
                color = "info" if line.startswith("+") else "error" if line.startswith("-") else "0"
                print(paint("tool", "  │ ") + paint(color, line), file=sys.stderr)
        if self.all:
            if not QUIET:
                print(paint("tool", "  └─ approvato automaticamente"), file=sys.stderr)
            return True
        if KEYBOARD:
            KEYBOARD.unlock()          # fresh, visible input for the answer
        try:
            with open("/dev/tty") as tty:
                print(paint("tool", "  └─ eseguo? [s]ì / [N]o / [a] sì a tutto: "), end="", file=sys.stderr, flush=True)
                ans = tty.readline().strip().lower()
        except OSError:
            print(paint("error", "  └─ nessun terminale per confermare: negato (usa -y)"), file=sys.stderr)
            return False
        finally:
            if KEYBOARD:
                KEYBOARD.lock()
        if ans == "a":
            self.all = True
        ok = ans in ("s", "si", "sì", "y", "yes", "a")
        jlog("approval", kind=kind, preview=preview[:2000], approved=ok)
        return ok


# --- model call (streaming) --------------------------------------------------------
def chat(url: str, messages: list[dict], think: bool, headers: dict) -> dict:
    body = {"messages": messages, "tools": SPECS, "stream": True, "max_tokens": 4096,
            "temperature": 0.3, "chat_template_kwargs": {"enable_thinking": think}}
    req = urllib.request.Request(f"{url}/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", **headers})
    t0 = time.time()
    content, reasoning, calls, timings = [], [], {}, {}
    cat = addons = None
    mode = None                                    # what is being printed: think / answer
    last_progress = 0.0
    with Spinner("leggo il prompt…") as spin, urllib.request.urlopen(req, timeout=1800) as r:
        cat, addons = r.headers.get("X-Router-Category"), r.headers.get("X-Router-Addons")
        for raw in r:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data: ") or line == "data: [DONE]":
                continue
            chunk = json.loads(line[6:])
            timings = chunk.get("timings") or timings
            for ch in chunk.get("choices", []):
                d = ch.get("delta") or {}
                if d.get("reasoning_content"):
                    if mode != "think":
                        spin.stop()
                        if not QUIET:
                            print(paint("think", "  ✻ "), end="", file=sys.stderr)
                        mode = "think"
                    reasoning.append(d["reasoning_content"])
                    if not QUIET:
                        print(paint("think", d["reasoning_content"].replace("\n", "\n    ")),
                              end="", file=sys.stderr, flush=True)
                if d.get("content"):
                    if mode != "answer":
                        spin.stop()
                        if mode == "think" and not QUIET:
                            print("\n", file=sys.stderr)
                        mode = "answer"
                    content.append(d["content"])
                    if not QUIET:
                        print(d["content"], end="", flush=True)
                for tc in d.get("tool_calls") or []:
                    spin.stop()
                    if mode in ("think", "answer"):
                        if not QUIET:
                            print(file=sys.stderr if mode == "think" else sys.stdout, flush=True)
                        mode = "tool"
                    acc = calls.setdefault(tc.get("index", 0), {"id": "", "name": "", "arguments": ""})
                    acc["id"] = tc.get("id") or acc["id"]
                    fn = tc.get("function") or {}
                    acc["name"] += fn.get("name") or ""
                    acc["arguments"] += fn.get("arguments") or ""
                    # visible progress while long arguments (a whole file) are generated
                    if TTY and not QUIET and time.time() - last_progress > 0.25:
                        last_progress = time.time()
                        progress = f"  ✎ {acc['name'] or '...'}… {len(acc['arguments'])} caratteri"
                        print("\r\033[K" + paint("dim", progress), end="", file=sys.stderr, flush=True)
    if mode == "tool" or (calls and TTY):
        if not QUIET:
            print("\r\033[K", end="", file=sys.stderr, flush=True)
    elif mode:
        if not QUIET:
            print(file=sys.stderr if mode == "think" else sys.stdout, flush=True)
    t = timings
    route = f"router: {cat or 'nessuna categoria'}" + (f" +{addons}" if addons else "") if cat is not None else ""
    log("stats", f"{time.time() - t0:.0f}s · prompt {t.get('prompt_n', '?')} tok nuovi, "
                 f"{t.get('cache_n', '?')} dalla cache ({t.get('prompt_per_second', 0):.0f} t/s) · "
                 f"generati {t.get('predicted_n', '?')} ({t.get('predicted_per_second', 0):.1f} t/s)"
                 + (f" · {route}" if route else ""))
    jlog("model", reasoning="".join(reasoning), content="".join(content),
         tool_calls=list(calls.values()), timings=t, router={"category": cat, "addons": addons})
    msg: dict = {"role": "assistant", "content": "".join(content) or None}
    if reasoning:
        msg["reasoning_content"] = "".join(reasoning)
    if calls:
        msg["tool_calls"] = [{"id": c["id"] or f"call_{uuid.uuid4().hex[:8]}", "type": "function",
                              "function": {"name": c["name"], "arguments": c["arguments"] or "{}"}}
                             for c in calls.values()]
    return msg


def run_turn(url: str, messages: list[dict], tools: Toolbox, think: bool, headers: dict) -> str | None:
    """Let the model work on the last user message until it stops calling tools.

    Returns the final assistant answer, or None when MAX_STEPS is reached.
    """
    for _ in range(MAX_STEPS):
        msg = chat(url, messages, think, headers)
        messages.append(msg)
        if not msg.get("tool_calls"):
            return msg.get("content")
        for call in msg["tool_calls"]:
            name = call["function"]["name"]
            try:
                args = json.loads(call["function"]["arguments"] or "{}")
            except json.JSONDecodeError as err:
                result, args = f"error: arguments are not valid JSON ({err})", {}
            else:
                main_arg = args.get("command") or args.get("path") or ""
                log("tool", f"{name}({main_arg})")
                result = tools.call(name, args)
            jlog("tool", name=name, args=args, result=result[:4000])
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})
    log("error", f"fermato dopo {MAX_STEPS} passi senza conclusione")
    return None


# --- session ------------------------------------------------------------------------
def ensure_model(url: str) -> bool:
    """Start the stack with ./ai start if nothing answers on `url`."""
    def healthy() -> bool:
        try:
            with urllib.request.urlopen(f"{url}/health", timeout=2) as r:
                return r.status == 200
        except (urllib.error.URLError, OSError):
            return False

    if healthy():
        return True
    log("info", "modello spento: lo avvio (./ai start)…")
    if subprocess.run([str(REPO / "ai"), "start"], stdout=subprocess.DEVNULL,
                      stderr=subprocess.DEVNULL).returncode != 0:
        # `base` (the 9B default) is often not downloaded on a 16 GB machine:
        # fall back to `lite` instead of leaving the agent dead on first run.
        log("info", "modello di default (`base`) non avviabile: provo `lite`…")
        if subprocess.run([str(REPO / "ai"), "start", "lite"], stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL).returncode != 0:
            log("error", "avvio fallito: guarda ./ai logs")
            return False
    with Spinner("carico il modello…"):
        for _ in range(300):
            if healthy():
                return True
            time.sleep(1)
    log("error", "il modello non risponde dopo 5 minuti: guarda ./ai logs")
    return False


def setup_readline() -> None:
    try:
        import readline
    except ImportError:
        return
    HISTORY_FILE.parent.mkdir(exist_ok=True)
    try:
        readline.read_history_file(HISTORY_FILE)
    except OSError:
        pass
    readline.set_history_length(1000)
    import atexit
    atexit.register(lambda: readline.write_history_file(HISTORY_FILE))


def new_conversation(cwd: Path) -> list[dict]:
    return [{"role": "system", "content": SYSTEM.format(
        today=date.today().isoformat(), user=getpass.getuser(), cwd=cwd, home=Path.home())}]


def truncate(text: str, limit: int = 2000) -> str:
    if len(text) <= limit:
        return text
    return text[:limit - 1] + "…"


def notify(answer: str | None) -> None:
    """Send the final answer as a desktop notification; print it if that fails."""
    answer = answer or ""
    body = truncate(answer if answer.strip() else "ai: nessuna risposta")
    exe = shutil.which("notify-send")
    if exe:
        try:
            if subprocess.run([exe, "-a", "ai", "ai", body]).returncode == 0:
                return
        except (OSError, subprocess.SubprocessError):
            pass
    print(body, file=sys.stderr, flush=True)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="ai", description="local terminal agent")
    ap.add_argument("prompt", nargs="*", help="first prompt (optional)")
    ap.add_argument("-p", "--print", action="store_true", help="one shot: answer and exit")
    ap.add_argument("-a", "--auto", "-y", "--yes", dest="yes", action="store_true",
                    help="auto mode: run commands and file changes without asking")
    ap.add_argument("-s", "--stealth", action="store_true",
                    help="quiet one shot: notify the final answer, no terminal output")
    ap.add_argument("--here", action="store_true", help="(handled by ./ai) stay in this terminal")
    ap.add_argument("--no-think", action="store_true", help="disable the model's reasoning (faster)")
    ap.add_argument("--url", default=os.environ.get("AGENT_URL", "http://127.0.0.1:8080"))
    return ap


def main() -> int:
    args = build_parser().parse_args()
    if args.stealth:                   # no terminal: no approvals, one shot
        args.yes = True
        args.print = True

    global KEYBOARD, QUIET
    QUIET = args.stealth

    headers = {}
    if os.environ.get("LLAMA_API_KEY"):
        headers["Authorization"] = f"Bearer {os.environ['LLAMA_API_KEY']}"
    cwd = Path.cwd()
    approver = Approver(args.yes)
    tools = Toolbox(cwd=cwd, approve=approver, log=log)
    think = not args.no_think
    messages = new_conversation(cwd)

    KEYBOARD = Keyboard()
    if not ensure_model(args.url):
        return 1
    home = str(Path.home())
    where = str(cwd).replace(home, "~", 1) if str(cwd).startswith(home) else str(cwd)
    if not QUIET:
        print(paint("bold", "\n ✻ rottingAi") + paint("dim", f"  ·  modello locale  ·  {where}  ·  "
              f"think {'on' if think else 'off'}  ·  /help"), file=sys.stderr)
        if args.yes:
            print(paint("error", "   AUTO MODE: comandi e modifiche ai file vengono eseguiti senza chiedere"),
                  file=sys.stderr)
        print(file=sys.stderr)
    jlog("session", cwd=str(cwd), think=think, url=args.url)
    if not args.print:
        setup_readline()

    pending = " ".join(args.prompt).strip()
    while True:
        try:
            if pending:
                text, pending = pending, ""
                if not QUIET:
                    print(paint("info", "› ") + text, file=sys.stderr)
            elif args.print:
                return 0
            else:
                text = input(paint("info", "\n› ") if TTY else "› ").strip()
        except (KeyboardInterrupt, EOFError):
            print(file=sys.stderr)
            return 0

        if not text:
            continue
        if text.startswith("/"):
            cmd, _, arg = text.partition(" ")
            if cmd in ("/exit", "/quit", "/esci"):
                return 0
            if cmd == "/clear":
                messages = new_conversation(cwd)
                log("info", "nuova conversazione")
            elif cmd == "/think":
                think = arg.strip() != "off" if arg.strip() else not think
                log("info", f"think {'on' if think else 'off'}")
            elif cmd in ("/auto", "/yes"):
                approver.all = not approver.all
                log("error" if approver.all else "info",
                    "AUTO MODE attivo: niente conferme" if approver.all else "auto mode spento: chiedo conferma")
            else:
                print(paint("dim", HELP), file=sys.stderr)
            continue

        messages.append({"role": "user", "content": text})
        jlog("user", content=text)
        tools.allow_overwrite = bool(REWRITE_RE.search(text))
        answer = None
        KEYBOARD.lock()
        try:
            answer = run_turn(args.url, messages, tools, think, headers)
        except KeyboardInterrupt:
            if not QUIET:
                print(file=sys.stderr)
            log("error", "interrotto")
        except urllib.error.URLError as err:
            log("error", f"modello non raggiungibile su {args.url}: {err}")
        finally:
            KEYBOARD.unlock()
        if args.stealth:
            notify(answer)
        if args.print:
            return 0


if __name__ == "__main__":
    sys.exit(main())
