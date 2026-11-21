"""Inject router-selected add-ons into a chat, KV-cache safe.

Rules (CLAUDE.md):
  - add-ons go at the END of the context: inside the newest user turn, before
    the user's original text (which stays intact). Not as a mid-conversation
    `system` message: Qwen chat templates reject a system message that is not
    first.
  - once injected, an add-on stays at the SAME position for the rest of the
    conversation (never unloaded or moved), so every later request shares the
    same prefix and llama-server reuses its KV cache.
  - a new conversation (different first user message) starts clean.

OpenAI-style clients are stateless (they resend the whole history), so the
composer remembers, per conversation, at which message index each add-on was
injected and re-applies it identically on every request.
"""
from __future__ import annotations

import copy
import hashlib
import json
import threading
from collections import OrderedDict
from dataclasses import dataclass, field

from .registry import Registry
from .router import Decision, Router

HEADER = "[Add-on context selected by the router: instructions for you, not written by the user]"
FOOTER = "[End of add-on context. The user's message follows.]"
MAX_SESSIONS = 64


def message_text(msg: dict) -> str:
    content = msg.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text")
    return ""


def render_addons(registry: Registry, addon_ids: list[str]) -> str:
    parts = [HEADER]
    for aid in addon_ids:
        parts.append(f'<addon id="{aid}">\n{registry.addons[aid].text}\n</addon>')
    parts.append(FOOTER)
    return "\n".join(parts)


def _with_prefix(msg: dict, prefix: str) -> dict:
    out = copy.deepcopy(msg)
    content = out.get("content")
    if isinstance(content, list):
        out["content"] = [{"type": "text", "text": prefix}, *content]
    else:
        out["content"] = f"{prefix}\n\n{content or ''}"
    return out


def conversation_key(messages: list[dict]) -> str | None:
    """Identify a conversation by everything up to its first user message."""
    for i, m in enumerate(messages):
        if m.get("role") == "user":
            head = [(x.get("role"), message_text(x)) for x in messages[: i + 1]]
            return hashlib.sha256(json.dumps(head, ensure_ascii=False).encode()).hexdigest()[:16]
    return None


@dataclass
class Session:
    injected: dict[int, list[str]] = field(default_factory=dict)   # msg index -> add-on ids
    routed: set[int] = field(default_factory=set)                  # user turns already classified
    decisions: dict[int, dict] = field(default_factory=dict)       # for /router/status

    def loaded(self) -> set[str]:
        return {a for ids in self.injected.values() for a in ids}


class Composer:
    def __init__(self, router: Router) -> None:
        self.router = router
        self._sessions: OrderedDict[str, Session] = OrderedDict()
        self._lock = threading.Lock()

    def _session(self, key: str) -> Session:
        with self._lock:
            sess = self._sessions.pop(key, None) or Session()
            self._sessions[key] = sess
            while len(self._sessions) > MAX_SESSIONS:
                self._sessions.popitem(last=False)
            return sess

    def sessions(self) -> dict[str, dict]:
        with self._lock:
            return {
                k: {"injected": {str(i): ids for i, ids in s.injected.items()}, "decisions": s.decisions}
                for k, s in self._sessions.items()
            }

    def process(self, messages: list[dict]) -> tuple[list[dict], Decision | None]:
        """Return (messages to send to the model, new decision or None)."""
        key = conversation_key(messages)
        if key is None:
            return messages, None
        sess = self._session(key)
        reg = self.router.registry
        decision = None

        with self._lock:
            # history edited/truncated by the client: forget what is gone
            def still_there(i: int) -> bool:
                return i < len(messages) and messages[i].get("role") == "user"

            sess.injected = {i: ids for i, ids in sess.injected.items() if still_there(i)}
            sess.routed = {i for i in sess.routed if still_there(i)}

            last = len(messages) - 1
            if messages[last].get("role") == "user" and last not in sess.routed:
                user_texts = [message_text(m) for m in messages if m.get("role") == "user"]
                loaded = sess.loaded()
                used = sum(reg.addons[a].tokens for a in loaded if a in reg.addons)
                decision = self.router.route(user_texts, loaded=loaded, used_tokens=used)
                sess.routed.add(last)
                sess.decisions[last] = decision.to_dict()
                if decision.addons:
                    sess.injected[last] = [p.addon for p in decision.addons]

            injected = dict(sess.injected)

        out = list(messages)
        for i, ids in injected.items():
            ids = [a for a in ids if a in reg.addons]
            if ids:
                out[i] = _with_prefix(messages[i], render_addons(reg, ids))
        return out, decision
