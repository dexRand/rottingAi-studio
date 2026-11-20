"""File/code-type detection with Magika (optional dependency).

Magika gives ONE content type per input. Mixed code (e.g. SQL inside Python)
is left to the intent classifier / keyword rules.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger(__name__)

FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
MIN_CONFIDENCE = 0.6
MIN_SNIPPET_CHARS = 20


@dataclass(frozen=True)
class Detection:
    label: str
    score: float
    source: str          # "file:<name>" or "code-block"


class MagikaDetector:
    def __init__(self) -> None:
        self._magika = None
        try:
            from magika import Magika
        except ImportError:
            log.info("magika not installed: file/code detection disabled")
            return
        self._magika = Magika()

    @property
    def available(self) -> bool:
        return self._magika is not None

    def _identify(self, data: bytes, source: str) -> Detection | None:
        if self._magika is None or len(data) < MIN_SNIPPET_CHARS:
            return None
        res = self._magika.identify_bytes(data)
        label = getattr(res.output, "label", None) or getattr(res.output, "ct_label", "unknown")
        score = float(getattr(res, "score", 0.0) or getattr(res.output, "score", 0.0))
        if label in ("unknown", "txt", "empty") or score < MIN_CONFIDENCE:
            return None
        return Detection(label=label, score=score, source=source)

    def detect_text(self, text: str) -> list[Detection]:
        """Detect the language of fenced code blocks inside a prompt."""
        found = []
        for block in FENCE_RE.findall(text):
            det = self._identify(block.encode("utf-8"), "code-block")
            if det:
                found.append(det)
        return found

    def detect_files(self, paths: list[Path]) -> list[Detection]:
        found = []
        for p in paths:
            det = self._identify(p.read_bytes()[:65536], f"file:{p.name}")
            if det:
                found.append(det)
        return found
