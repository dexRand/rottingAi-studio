"""Unit tests for the agent's stealth helpers (stdlib only, no model needed).

    python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import contextlib
import io
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent import __main__ as agent  # noqa: E402
from agent.__main__ import build_parser, notify, truncate  # noqa: E402


class _Run:
    def __init__(self, returncode: int) -> None:
        self.returncode = returncode


class TruncateTests(unittest.TestCase):
    def test_short_text_unchanged(self) -> None:
        self.assertEqual(truncate("ciao"), "ciao")

    def test_empty_unchanged(self) -> None:
        self.assertEqual(truncate(""), "")

    def test_long_text_is_capped_and_ellipsised(self) -> None:
        out = truncate("x" * 5000)
        self.assertLessEqual(len(out), 2000)
        self.assertTrue(out.endswith("…"))


class NotifyTests(unittest.TestCase):
    def test_fallback_when_notify_send_missing(self) -> None:
        err = io.StringIO()
        with mock.patch.object(agent.shutil, "which", return_value=None), \
             mock.patch.object(agent.subprocess, "run") as run, \
             contextlib.redirect_stderr(err):
            notify("risposta")
        run.assert_not_called()
        self.assertIn("risposta", err.getvalue())

    def test_success_passes_list_and_truncates(self) -> None:
        calls = []

        def fake_run(*args, **kwargs):
            calls.append(args[0])
            return _Run(0)

        with mock.patch.object(agent.shutil, "which", return_value="/usr/bin/notify-send"), \
             mock.patch.object(agent.subprocess, "run", side_effect=fake_run):
            notify("x" * 5000)
        self.assertEqual(calls[0][:4], ["/usr/bin/notify-send", "-a", "ai", "ai"])
        self.assertEqual(len(calls[0]), 5)
        self.assertLessEqual(len(calls[0][4]), 2000)

    def test_fallback_on_nonzero_exit(self) -> None:
        err = io.StringIO()
        with mock.patch.object(agent.shutil, "which", return_value="/usr/bin/notify-send"), \
             mock.patch.object(agent.subprocess, "run", return_value=_Run(1)), \
             contextlib.redirect_stderr(err):
            notify("risposta")
        self.assertIn("risposta", err.getvalue())

    def test_fallback_on_oserror(self) -> None:
        err = io.StringIO()
        with mock.patch.object(agent.shutil, "which", return_value="/usr/bin/notify-send"), \
             mock.patch.object(agent.subprocess, "run", side_effect=OSError("boom")), \
             contextlib.redirect_stderr(err):
            notify("risposta")
        self.assertIn("risposta", err.getvalue())

    def test_empty_answer_gets_placeholder(self) -> None:
        calls = []

        def fake_run(*args, **kwargs):
            calls.append(args[0])
            return _Run(0)

        with mock.patch.object(agent.shutil, "which", return_value="/usr/bin/notify-send"), \
             mock.patch.object(agent.subprocess, "run", side_effect=fake_run):
            notify(None)
            notify("   ")
        self.assertEqual(calls[0][-1], "ai: nessuna risposta")
        self.assertEqual(calls[1][-1], "ai: nessuna risposta")


class ParserTests(unittest.TestCase):
    def test_short_stealth_flag(self) -> None:
        self.assertTrue(build_parser().parse_args(["-s", "hi"]).stealth)

    def test_long_stealth_flag(self) -> None:
        self.assertTrue(build_parser().parse_args(["--stealth"]).stealth)

    def test_print_is_not_stealth(self) -> None:
        args = build_parser().parse_args(["-p", "hi"])
        self.assertTrue(args.print)
        self.assertFalse(args.stealth)


if __name__ == "__main__":
    unittest.main()
