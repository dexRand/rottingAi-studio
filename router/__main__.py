"""Router CLI.

  python -m router route "testo" [--file F ...] [--history "msg" ...] [--backend B] [--show]
  python -m router serve [--host H] [--port P] [--upstream-port P]
  python -m router eval [dataset.jsonl] [--backend B] [-v]
  python -m router check
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from .registry import Registry, Settings


def cmd_route(args: argparse.Namespace) -> int:
    from .router import Router

    settings = Settings.load()
    if args.backend:
        settings.backend = args.backend
    router = Router(settings=settings)
    texts = [*args.history, args.text]
    decision = router.route(texts, files=[Path(f) for f in args.file])
    print(json.dumps(decision.to_dict(), ensure_ascii=False, indent=2))
    if args.show:
        from .compose import render_addons

        ids = [p.addon for p in decision.addons]
        print("\n--- text appended before the prompt ---")
        print(render_addons(router.registry, ids) if ids else "(nothing)")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from .compose import Composer
    from .proxy import serve
    from .router import Router

    composer = Composer(Router())
    serve(composer, args.host, args.port, "127.0.0.1", args.upstream_port)
    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    """Accuracy of a backend on a labelled JSONL file (text, category, addons)."""
    from .router import Router

    settings = Settings.load()
    if args.backend:
        settings.backend = args.backend
    router = Router(settings=settings)
    rows = [json.loads(line) for line in Path(args.dataset).read_text(encoding="utf-8").splitlines() if line.strip()]
    cat_ok = addon_ok = 0
    for row in rows:
        d = router.route([*row.get("history", []), row["text"]])
        got_addons = {p.addon for p in d.addons}
        c_ok = d.category == row.get("category")
        a_ok = got_addons == set(row.get("addons", []))
        cat_ok += c_ok
        addon_ok += a_ok
        if not (c_ok and a_ok) or args.verbose:
            mark = "ok " if c_ok and a_ok else "ERR"
            print(f"{mark} want {row.get('category')}/{sorted(row.get('addons', []))} "
                  f"got {d.category}/{sorted(got_addons)} | {row['text'][:60]!r}")
    n = len(rows) or 1
    print(f"backend={router.classifier.name} category {cat_ok}/{len(rows)} ({cat_ok / n:.0%}) "
          f"add-ons {addon_ok}/{len(rows)} ({addon_ok / n:.0%})")
    return 0


def cmd_check(_: argparse.Namespace) -> int:
    reg = Registry.load()
    settings = Settings.load()
    problems = reg.validate()
    print(f"categories: {', '.join(reg.routable_categories)} (+ shared)")
    total = 0
    for a in reg.addons.values():
        size = a.tokens if a.path.is_file() else 0
        total += size
        print(f"  {a.id:16} {a.category:9} {a.type:12} ~{size} tokens")
    print(f"all add-ons together: ~{total} tokens (budget per conversation: {settings.max_addon_tokens})")
    for a in reg.addons.values():
        if a.path.is_file() and a.tokens > settings.max_addon_tokens:
            problems.append(f"add-on {a.id} alone exceeds max_addon_tokens")
    for p in problems:
        print(f"  ! {p}")
    print("OK" if not problems else f"{len(problems)} problem(s)")
    return 0 if not problems else 1


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=os.environ.get("ROUTER_LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    ap = argparse.ArgumentParser(prog="router", description="category + add-on router")
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("route", help="classify a prompt and print the decision")
    r.add_argument("text")
    r.add_argument("--file", action="append", default=[], help="attached file (Magika)")
    r.add_argument("--history", action="append", default=[], help="earlier user message (repeatable, oldest first)")
    r.add_argument("--backend", choices=["auto", "gliclass", "keywords"])
    r.add_argument("--show", action="store_true", help="also print the injected add-on text")
    r.set_defaults(func=cmd_route)

    s = sub.add_parser("serve", help="run the OpenAI-compatible proxy")
    s.add_argument("--host", default=os.environ.get("ROUTER_HOST", "127.0.0.1"))
    s.add_argument("--port", type=int, default=int(os.environ.get("ROUTER_PORT", "8080")))
    s.add_argument("--upstream-port", type=int, default=int(os.environ.get("LLAMA_PORT", "8081")))
    s.set_defaults(func=cmd_serve)

    e = sub.add_parser("eval", help="measure accuracy on a labelled JSONL dataset")
    e.add_argument("dataset", nargs="?", default=str(Path(__file__).parent / "examples" / "smoke.jsonl"))
    e.add_argument("--backend", choices=["auto", "gliclass", "keywords"])
    e.add_argument("-v", "--verbose", action="store_true")
    e.set_defaults(func=cmd_eval)

    c = sub.add_parser("check", help="validate the registry and add-on sizes")
    c.set_defaults(func=cmd_check)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
