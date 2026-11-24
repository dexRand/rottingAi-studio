"""Local knowledge base for the agent: SQLite FTS5 over dropped documents.

Ingestion: put .md / .txt files in services/rag/docs/ and re-index explicitly:

    ./ai rag-index

Query: `search()` returns the top-k fragments (BM25 / lexical only in v1).
Everything is stdlib (sqlite3); no embeddings, no network, no Docker.
"""
from __future__ import annotations

import os
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DOCS_DIR = ROOT / "services" / "rag" / "docs"
DB_PATH = ROOT / "services" / "rag" / "kb.sqlite3"

CHUNK_SIZE = 800
HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.*)$", re.MULTILINE)


def _source_files(docs_dir: Path) -> list[Path]:
    """Top-level non-hidden .md / .txt files, sorted (v1: no subdirectories)."""
    docs_dir = Path(docs_dir)
    if not docs_dir.is_dir():
        return []
    return [
        p for p in sorted(docs_dir.iterdir())
        if p.is_file()
        and not p.name.startswith(".")
        and p.suffix.lower() in (".md", ".txt")
    ]


def _md_sections(text: str) -> list[tuple[str, str]]:
    """Split Markdown into (heading title, body) sections.

    A preamble before the first heading is kept and joined to the first section.
    Returns [] when the document has no heading at all.
    """
    headings = list(HEADING_RE.finditer(text))
    if not headings:
        return []
    preamble = text[:headings[0].start()].strip()
    sections: list[tuple[str, str]] = []
    for i, match in enumerate(headings):
        title = match.group(2).strip()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        body = text[match.end():end].strip()
        if i == 0 and preamble:
            body = preamble + ("\n\n" + body if body else "")
        sections.append((title, body))
    return sections


def _split_words(text: str, limit: int) -> list[str]:
    """Hard-wrap an over-long unit at word boundaries (mid-word only if unavoidable)."""
    chunks: list[str] = []
    current = ""
    for word in text.split():
        if len(word) > limit:
            if current:
                chunks.append(current)
                current = ""
            while len(word) > limit:
                chunks.append(word[:limit])
                word = word[limit:]
            current = word
            continue
        candidate = f"{current} {word}" if current else word
        if len(candidate) <= limit:
            current = candidate
        else:
            chunks.append(current)
            current = word
    if current:
        chunks.append(current)
    return chunks


def _split_long(text: str, limit: int) -> list[str]:
    """Split at sentence / newline boundaries, then at words; never mid-word if avoidable."""
    units = [u.strip() for u in re.split(r"(?<=[.!?])\s+|\n+", text) if u.strip()]
    chunks: list[str] = []
    current = ""
    for unit in units:
        if len(unit) > limit:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_split_words(unit, limit))
            continue
        candidate = f"{current} {unit}" if current else unit
        if len(candidate) <= limit:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = unit
    if current:
        chunks.append(current)
    return chunks


def _chunk_text(text: str, limit: int = CHUNK_SIZE) -> list[str]:
    """Split text into <= limit chunks: paragraphs first, then sentences/words."""
    text = text.strip()
    if not text:
        return []
    chunks: list[str] = []
    current = ""
    for paragraph in re.split(r"\n\s*\n", text):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = ""
        if len(paragraph) <= limit:
            current = paragraph
        else:
            pieces = _split_long(paragraph, limit)
            chunks.extend(pieces[:-1])
            current = pieces[-1] if pieces else ""
    if current:
        chunks.append(current)
    return chunks


def reindex(docs_dir: Path = DOCS_DIR, db_path: Path = DB_PATH) -> int:
    """Rebuild the FTS5 index from docs_dir and return the number of chunks."""
    rows: list[tuple[str, str, str]] = []
    for path in _source_files(docs_dir):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not text.strip():
            continue
        rel = os.path.relpath(path, ROOT)
        if path.suffix.lower() == ".md":
            sections = _md_sections(text) or [(path.name, text)]
        else:
            sections = [(path.name, text)]
        for title, body in sections:
            for chunk in _chunk_text(body):
                rows.append((rel, title, chunk))

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        with conn:
            conn.execute("DROP TABLE IF EXISTS chunks")
            conn.execute("CREATE VIRTUAL TABLE chunks USING fts5(file UNINDEXED, title, body)")
            conn.executemany("INSERT INTO chunks (file, title, body) VALUES (?, ?, ?)", rows)
    finally:
        conn.close()
    return len(rows)


def _fts_query(query: str) -> str:
    """Turn a raw user query into safe FTS5 MATCH syntax (quoted word tokens)."""
    terms = re.findall(r"\w+", query or "", re.UNICODE)
    return " ".join(f'"{term}"' for term in terms)


def search(query: str, k: int = 5, db_path: Path = DB_PATH) -> list[dict]:
    """Return up to k fragments ordered by BM25 relevance; [] if the DB is absent."""
    db_path = Path(db_path)
    if not db_path.is_file():
        return []
    match = _fts_query(query)
    if not match:
        return []
    try:
        conn = sqlite3.connect(db_path)
    except sqlite3.Error:
        return []
    try:
        rows = conn.execute(
            "SELECT file, title, body FROM chunks WHERE chunks MATCH ? "
            "ORDER BY bm25(chunks) LIMIT ?",
            (match, k),
        ).fetchall()
    except sqlite3.Error:
        return []
    finally:
        conn.close()
    return [{"file": file, "title": title, "body": body} for file, title, body in rows]


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    command = argv[0] if argv else "reindex"
    if command != "reindex":
        print("usage: python3 -m services.rag.kb reindex", file=sys.stderr)
        return 2
    sources = _source_files(DOCS_DIR)
    if not sources:
        print(f"no .md/.txt files in {DOCS_DIR}")
        return 0
    chunks = reindex()
    files = 0
    for path in sources:
        try:
            if path.read_text(encoding="utf-8", errors="replace").strip():
                files += 1
        except OSError:
            pass
    print(f"indexed {chunks} chunks from {files} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
