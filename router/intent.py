"""Intent classifiers: multi-label yes/no scores for categories and add-ons.

Two backends with the same interface:
  - KeywordClassifier: rules from addons/registry.toml, no dependencies.
  - GLiClassClassifier: zero-shot GLiClass (prototype; English-trained).
The final version (mmBERT-small / SetFit trained on Italian examples) will be a
third backend with the same `scores()` method.
"""
from __future__ import annotations

import logging
import re
from typing import Protocol

from .registry import Registry

log = logging.getLogger(__name__)


class IntentClassifier(Protocol):
    name: str

    def scores(self, text: str) -> dict[str, float]:
        """Return {"cat:<id>": score, "addon:<id>": score} in [0, 1]."""
        ...


def _kw_pattern(keyword: str) -> re.Pattern[str]:
    # word boundaries only where the keyword starts/ends with a word char
    start = r"\b" if keyword[:1].isalnum() else ""
    end = r"\b" if keyword[-1:].isalnum() else ""
    return re.compile(start + re.escape(keyword.strip()) + end, re.IGNORECASE)


def _hits_to_score(hits: int) -> float:
    return {0: 0.0, 1: 0.6, 2: 0.8}.get(hits, 0.95)


class KeywordClassifier:
    name = "keywords"

    def __init__(self, registry: Registry) -> None:
        self._rules: dict[str, list[re.Pattern[str]]] = {}
        for cat in registry.routable_categories.values():
            self._rules[f"cat:{cat.id}"] = [_kw_pattern(k) for k in cat.keywords]
        for a in registry.addons.values():
            self._rules[f"addon:{a.id}"] = [_kw_pattern(k) for k in a.keywords]
        # an add-on keyword is also evidence for its category
        self._addon_cat = {f"addon:{a.id}": f"cat:{a.category}" for a in registry.addons.values()}

    def scores(self, text: str) -> dict[str, float]:
        hits = {key: sum(1 for p in pats if p.search(text)) for key, pats in self._rules.items()}
        for akey, ckey in self._addon_cat.items():
            if ckey in hits:
                hits[ckey] += hits[akey]
        return {key: _hits_to_score(n) for key, n in hits.items()}


class GLiClassClassifier:
    name = "gliclass"

    def __init__(self, registry: Registry, model_name: str) -> None:
        from gliclass import GLiClassModel, ZeroShotClassificationPipeline
        from transformers import AutoTokenizer

        model = GLiClassModel.from_pretrained(model_name)
        tokenizer = AutoTokenizer.from_pretrained(model_name, add_prefix_space=True)
        self._pipe = ZeroShotClassificationPipeline(
            model, tokenizer, classification_type="multi-label", device="cpu", progress_bar=False
        )
        self._labels: dict[str, str] = {}
        for cat in registry.routable_categories.values():
            self._labels[cat.label] = f"cat:{cat.id}"
        for a in registry.addons.values():
            self._labels[a.label] = f"addon:{a.id}"

    def scores(self, text: str) -> dict[str, float]:
        out = self._pipe(text, list(self._labels), threshold=0.0)[0]
        result = dict.fromkeys(self._labels.values(), 0.0)
        for item in out:
            key = self._labels.get(item["label"])
            if key:
                result[key] = float(item["score"])
        return result


def make_classifier(registry: Registry, backend: str, gliclass_model: str) -> IntentClassifier:
    if backend in ("auto", "gliclass"):
        try:
            return GLiClassClassifier(registry, gliclass_model)
        except Exception as err:  # not installed, or model not downloadable (offline)
            if backend == "gliclass":
                raise
            log.warning("gliclass unavailable (%s): using the keyword backend", err)
    elif backend != "keywords":
        raise ValueError(f"unknown router backend: {backend}")
    return KeywordClassifier(registry)
