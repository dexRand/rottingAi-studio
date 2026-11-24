"""Unit tests for the local RAG knowledge base (stdlib only, temp dirs only).

    python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent.tools import SPECS, Toolbox  # noqa: E402
from services.rag import kb  # noqa: E402


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


class ReindexTests(unittest.TestCase):
    def test_indexes_md_and_txt_ignores_other_and_hidden(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp) / "docs"
            docs.mkdir()
            db = Path(tmp) / "kb.sqlite3"
            _write(docs / "alpha.md",
                   "# Alpha\n\npacman updates the system.\n\n## Beta\n\nsystemd units.\n")
            _write(docs / "notes.txt", "plain text about docker compose.\n")
            _write(docs / "skip.pdf", "ignored")
            _write(docs / ".hidden.md", "ignored hidden")

            count = kb.reindex(docs, db)

            self.assertEqual(count, 3)          # two md sections + one txt chunk
            self.assertTrue(db.is_file())
            hits = kb.search("pacman", db_path=db)
            self.assertTrue(hits)
            self.assertTrue(hits[0]["file"].endswith("alpha.md"))


class SearchTests(unittest.TestCase):
    def test_orders_by_relevance_and_respects_k(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp) / "docs"
            docs.mkdir()
            db = Path(tmp) / "kb.sqlite3"
            _write(docs / "short.md", "# Kernel\n\nkernel kernel kernel\n")
            _write(docs / "long.md", "# Other\n\nkernel " + "filler word " * 100 + "\n")
            kb.reindex(docs, db)

            hits = kb.search("kernel", k=2, db_path=db)
            self.assertEqual(len(hits), 2)
            self.assertTrue(hits[0]["file"].endswith("short.md"))
            limited = kb.search("kernel", k=1, db_path=db)
            self.assertEqual(len(limited), 1)
            self.assertEqual(limited[0]["file"], hits[0]["file"])


class EdgeCaseTests(unittest.TestCase):
    def test_empty_dir_and_missing_db(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp) / "docs"
            docs.mkdir()
            db = Path(tmp) / "kb.sqlite3"

            self.assertEqual(kb.reindex(docs, db), 0)
            self.assertTrue(db.is_file())
            self.assertEqual(kb.search("anything", db_path=Path(tmp) / "absent.sqlite3"), [])

    def test_reindex_refreshes_removed_documents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp) / "docs"
            docs.mkdir()
            db = Path(tmp) / "kb.sqlite3"
            keep = docs / "keep.md"
            drop = docs / "drop.md"
            _write(keep, "# Keep\n\nthe quokka lives here.\n")
            _write(drop, "# Drop\n\nthe zebrafish lives here.\n")

            self.assertGreater(kb.reindex(docs, db), 0)
            self.assertTrue(kb.search("zebrafish", db_path=db))

            drop.unlink()
            kb.reindex(docs, db)

            self.assertEqual(kb.search("zebrafish", db_path=db), [])
            self.assertTrue(kb.search("quokka", db_path=db))

    def test_special_characters_do_not_raise(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp) / "docs"
            docs.mkdir()
            db = Path(tmp) / "kb.sqlite3"
            _write(docs / "arch.md",
                   "# Pacman\n\npacman -Syu updates. C:\\temp is a path.\n")
            kb.reindex(docs, db)

            for query in ("pacman -Syu", "C:\\temp", "a:b OR (c)"):
                self.assertIsInstance(kb.search(query, db_path=db), list)


class ToolTests(unittest.TestCase):
    def _toolbox(self) -> Toolbox:
        return Toolbox(cwd=Path("."), approve=lambda *a: True, log=lambda *a: None)

    def test_kb_search_spec_registered(self) -> None:
        specs = {spec["function"]["name"]: spec["function"] for spec in SPECS}
        self.assertIn("kb_search", specs)
        params = specs["kb_search"]["parameters"]
        self.assertIn("query", params["required"])
        self.assertIn("k", params["properties"])

    def test_empty_kb_returns_graceful_message(self) -> None:
        with mock.patch("services.rag.kb.search", return_value=[]):
            out = self._toolbox().t_kb_search("anything")
        self.assertEqual(
            out,
            "no results in the knowledge base. Drop .md/.txt files into "
            "services/rag/docs/ and run ./ai rag-index.")

    def test_formats_hits_and_clamps_k(self) -> None:
        hits = [{"file": "services/rag/docs/a.md", "title": "Arch", "body": "pacman -Syu"}]
        with mock.patch("services.rag.kb.search", return_value=hits) as fake:
            out = self._toolbox().t_kb_search("pacman", k=99)
        fake.assert_called_once_with("pacman", k=10)
        self.assertIn("1. services/rag/docs/a.md — Arch", out)
        self.assertIn("pacman -Syu", out)

        with mock.patch("services.rag.kb.search", return_value=[]) as fake:
            self._toolbox().t_kb_search("pacman", k=0)
        fake.assert_called_once_with("pacman", k=1)


if __name__ == "__main__":
    unittest.main()
