"""Router: one classification pass -> category + add-ons (yes/no flags).

The user's prompt is never modified here: the router only DECIDES. Injection
into the context is done by router/compose.py.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from .detect import Detection, MagikaDetector
from .intent import IntentClassifier, make_classifier
from .registry import SHARED, Registry, Settings

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Pick:
    addon: str
    score: float
    reason: str          # "magika:<label>", "intent", "default:<category>"


@dataclass
class Decision:
    category: str | None              # None = below threshold, no guess
    category_score: float
    addons: list[Pick] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)   # over budget
    scores: dict[str, float] = field(default_factory=dict)
    detections: list[Detection] = field(default_factory=list)
    backend: str = ""

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "category_score": round(self.category_score, 3),
            "addons": [{"id": p.addon, "score": round(p.score, 3), "reason": p.reason} for p in self.addons],
            "skipped_over_budget": self.skipped,
            "detections": [{"label": d.label, "score": round(d.score, 3), "source": d.source} for d in self.detections],
            "scores": {k: round(v, 3) for k, v in sorted(self.scores.items(), key=lambda kv: -kv[1])},
            "backend": self.backend,
        }


class Router:
    def __init__(
        self,
        registry: Registry | None = None,
        settings: Settings | None = None,
        classifier: IntentClassifier | None = None,
        detector: MagikaDetector | None = None,
    ) -> None:
        self.registry = registry or Registry.load()
        self.settings = settings or Settings.load()
        self.classifier = classifier or make_classifier(
            self.registry,
            self.settings.backend,
            self.settings.gliclass_model,
            self.settings.tfidf_model,
        )
        if detector is None and self.settings.magika:
            detector = MagikaDetector()
        self.detector = detector

    def route(
        self,
        user_messages: list[str],
        files: list[Path] | None = None,
        loaded: set[str] | frozenset[str] = frozenset(),
        used_tokens: int = 0,
    ) -> Decision:
        """Classify the recent user messages (oldest -> newest).

        `loaded` / `used_tokens` describe add-ons already in this conversation:
        they are never re-added and count against the token budget.
        """
        s, reg = self.settings, self.registry
        window = [m for m in user_messages if m.strip()][-s.history_messages:]
        # The last message decides; older ones only help when it says nothing
        # (e.g. "e adesso?"). Weighted history: a topic change in the last
        # message beats an old keyword still sitting in the window.
        scores = self.classifier.scores(window[-1]) if window else {}
        if len(window) > 1:
            older = self.classifier.scores("\n\n".join(window[:-1]))
            # a pure follow-up (no signal at all in the last message) inherits
            # the previous topic in full
            weight = s.history_weight if any(scores.values()) else 1.0
            for key, value in older.items():
                scores[key] = max(scores.get(key, 0.0), value * weight)

        detections: list[Detection] = []
        if self.detector and self.detector.available:
            if window:
                detections += self.detector.detect_text(window[-1])
            detections += self.detector.detect_files(files or [])

        # Magika hits are strong evidence for an add-on and its category.
        magika_picks: dict[str, Pick] = {}
        for det in detections:
            for a in reg.addons.values():
                if det.label in a.magika and a.id not in magika_picks:
                    magika_picks[a.id] = Pick(a.id, det.score, f"magika:{det.label}")
                    ckey = f"cat:{a.category}"
                    if a.category != SHARED:
                        scores[ckey] = max(scores.get(ckey, 0.0), det.score)

        cat_scores = {cid: scores.get(f"cat:{cid}", 0.0) for cid in reg.routable_categories}
        best = max(cat_scores, key=cat_scores.get, default=None)
        best_score = cat_scores.get(best, 0.0) if best else 0.0
        category = best if best and best_score >= s.threshold else None

        picks: dict[str, Pick] = dict(magika_picks)
        for a in reg.addons.values():
            score = scores.get(f"addon:{a.id}", 0.0)
            if a.id in picks or score < s.threshold:
                continue
            if a.category in (category, SHARED):
                picks[a.id] = Pick(a.id, score, "intent")
        if category:
            for aid in reg.categories[category].default_addons:
                picks.setdefault(aid, Pick(aid, best_score, f"default:{category}"))

        ordered = sorted(
            (p for p in picks.values() if p.addon not in loaded),
            key=lambda p: (not p.reason.startswith("magika"), -p.score),
        )
        chosen, skipped, budget = [], [], s.max_addon_tokens - used_tokens
        for p in ordered:
            cost = reg.addons[p.addon].tokens
            if cost <= budget:
                chosen.append(p)
                budget -= cost
            else:
                skipped.append(p.addon)
        if skipped:
            log.warning("add-ons over budget, skipped: %s", ", ".join(skipped))

        return Decision(
            category=category,
            category_score=best_score,
            addons=chosen,
            skipped=skipped,
            scores=scores,
            detections=detections,
            backend=self.classifier.name,
        )
