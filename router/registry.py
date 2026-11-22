"""Add-on registry and router settings (addons/registry.toml, config/router.toml)."""
from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO / "addons" / "registry.toml"
SETTINGS_PATH = REPO / "config" / "router.toml"

ADDON_TYPES = ("instructions", "skill", "tool", "lora")
SHARED = "shared"


def estimate_tokens(text: str) -> int:
    """Rough token count (~3.5 chars per token): good enough for budgeting."""
    return max(1, len(text) * 2 // 7)


def _strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2].lstrip()
    return text


@dataclass(frozen=True)
class Addon:
    id: str
    category: str
    type: str
    file: str
    label: str
    magika: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()

    @property
    def path(self) -> Path:
        return REPO / self.file

    @cached_property
    def text(self) -> str:
        return _strip_frontmatter(self.path.read_text(encoding="utf-8")).strip()

    @cached_property
    def tokens(self) -> int:
        return estimate_tokens(self.text)


@dataclass(frozen=True)
class Category:
    id: str
    label: str
    default_addons: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()


@dataclass
class Settings:
    backend: str = "auto"
    gliclass_model: str = "knowledgator/gliclass-edge-v3.0"
    threshold: float = 0.5
    history_messages: int = 3
    history_weight: float = 0.6
    max_addon_tokens: int = 4000
    magika: bool = True

    @classmethod
    def load(cls, path: Path = SETTINGS_PATH) -> Settings:
        if not path.is_file():
            return cls()
        data = tomllib.loads(path.read_text(encoding="utf-8")).get("router", {})
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**known)


@dataclass
class Registry:
    categories: dict[str, Category]
    addons: dict[str, Addon]
    catalog: dict[str, list[str]] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path = REGISTRY_PATH) -> Registry:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        categories = {
            cid: Category(
                id=cid,
                label=c.get("label", ""),
                default_addons=tuple(c.get("default_addons", [])),
                keywords=tuple(k.lower() for k in c.get("keywords", [])),
            )
            for cid, c in data.get("categories", {}).items()
        }
        addons = {
            aid: Addon(
                id=aid,
                category=a["category"],
                type=a.get("type", "instructions"),
                file=a["file"],
                label=a.get("label", aid),
                magika=tuple(a.get("magika", [])),
                keywords=tuple(k.lower() for k in a.get("keywords", [])),
            )
            for aid, a in data.get("addons", {}).items()
        }
        return cls(categories=categories, addons=addons, catalog=data.get("catalog", {}))

    @property
    def routable_categories(self) -> dict[str, Category]:
        """Categories the router may pick (the shared group is not one)."""
        return {cid: c for cid, c in self.categories.items() if cid != SHARED}

    def validate(self) -> list[str]:
        """Return a list of problems (empty = ok)."""
        problems = []
        for cat in self.categories.values():
            for aid in cat.default_addons:
                if aid not in self.addons:
                    problems.append(f"category {cat.id}: unknown default add-on '{aid}'")
        for a in self.addons.values():
            if a.category not in self.categories:
                problems.append(f"add-on {a.id}: unknown category '{a.category}'")
            if a.type not in ADDON_TYPES:
                problems.append(f"add-on {a.id}: unknown type '{a.type}'")
            if not a.path.is_file():
                problems.append(f"add-on {a.id}: file not found {a.file}")
        skills_dir = REPO / ".opencode" / "skills"
        for cat, skills in self.catalog.items():
            for s in skills:
                if not (skills_dir / s / "SKILL.md").is_file():
                    problems.append(f"catalog {cat}: skill '{s}' not found")
        return problems
