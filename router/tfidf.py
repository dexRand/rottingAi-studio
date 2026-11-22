"""Trained tf-idf intent backend (scikit-learn, optional).

Predicts the CATEGORY only (`cat:<id>` scores): add-ons come from the router's
`default_addons` + Magika logic once the category is known. It is an explicit
backend (`--backend tfidf` / `backend = "tfidf"`), never chosen by `auto` and
never the default.

Train:  ./ai route-train router/examples/smoke.jsonl
Eval:   ./ai route-eval --backend tfidf

sklearn imports are lazy: `import router.tfidf` works without scikit-learn.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .registry import REPO, Registry

NONE = "none"
DEFAULT_MODEL = "runtime/intent-tfidf.joblib"


def _known_categories(known_categories: set[str] | None) -> set[str]:
    if known_categories is not None:
        return set(known_categories)
    return set(Registry.load().routable_categories)


def load_labeled_jsonl(
    paths: Iterable[str | Path],
    known_categories: set[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Read labeled JSONL rows as (texts, labels).

    Any `category` that is null or not a routable id becomes `NONE`. Empty
    texts are skipped; a file with zero usable rows is an error.
    """
    known = _known_categories(known_categories)
    texts: list[str] = []
    labels: list[str] = []
    for path in paths:
        path = Path(path)
        usable = 0
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            text = row.get("text") or ""
            if not text.strip():
                continue
            category = row.get("category")
            labels.append(category if category in known else NONE)
            texts.append(text)
            usable += 1
        if usable == 0:
            raise ValueError(f"no usable labeled rows in {path} (need non-empty text + category)")
    return texts, labels


def build_pipeline():
    """Untrained tf-idf + LinearSVC pipeline (imports sklearn inside)."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.pipeline import Pipeline
    from sklearn.svm import LinearSVC

    return Pipeline([
        ("tfidf", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4))),
        ("svc", LinearSVC(dual="auto", max_iter=2000)),
    ])


def cross_validate(X, y, folds: int = 5, seed: int = 0) -> tuple[float, float]:
    """Plain KFold accuracy (mean, std): tiny data, some classes have <5 rows."""
    from sklearn.model_selection import KFold, cross_val_score

    cv = KFold(n_splits=folds, shuffle=True, random_state=seed)
    scores = cross_val_score(build_pipeline(), X, y, cv=cv, scoring="accuracy")
    return float(scores.mean()), float(scores.std())


def _resolve(model_path: str | Path) -> Path:
    path = Path(model_path)
    return path if path.is_absolute() else REPO / path


def train(datasets: Iterable[str | Path], model_path: str | Path = DEFAULT_MODEL) -> dict:
    """Fit the classifier on labeled JSONL, save it, and report stats."""
    try:
        import sklearn  # noqa: F401
    except ImportError as err:
        raise ImportError(
            "scikit-learn not installed — run ./ai router-install --tfidf"
        ) from err

    X, y = load_labeled_jsonl(datasets)
    pipeline = build_pipeline()
    pipeline.fit(X, y)

    out = _resolve(model_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    import joblib

    joblib.dump(pipeline, out)

    mean, std = cross_validate(X, y)
    counts: dict[str, int] = {}
    for label in y:
        counts[label] = counts.get(label, 0) + 1
    return {
        "examples": len(X),
        "classes": dict(sorted(counts.items())),
        "cv_mean": mean,
        "cv_std": std,
        "model": str(out),
    }


class TfidfClassifier:
    name = "tfidf"

    def __init__(self, registry: Registry, model_path: str | Path) -> None:
        try:
            import joblib
            import sklearn  # noqa: F401
        except ImportError as err:
            raise ImportError(
                "scikit-learn not installed — run ./ai router-install --tfidf"
            ) from err

        path = _resolve(model_path)
        if not path.is_file():
            raise FileNotFoundError(
                f"no trained model at {path} — run ./ai route-train <dataset.jsonl...>"
            )
        self._pipe = joblib.load(path)

    def scores(self, text: str) -> dict[str, float]:
        """Softmax over the class margins, dropping the `none` class."""
        import numpy as np

        decision = np.atleast_1d(self._pipe.decision_function([text])[0])
        if decision.shape[0] == 1:
            # Binary LinearSVC returns a single signed margin (class at index 1).
            decision = np.array([-decision[0], decision[0]])
        exp = np.exp(decision - np.max(decision))
        probs = exp / exp.sum()
        return {
            f"cat:{label}": float(prob)
            for label, prob in zip(self._pipe.classes_, probs)
            if label != NONE
        }
