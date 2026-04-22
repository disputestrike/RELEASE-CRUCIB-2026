"""Hot-reloadable skills loader.

Each skill lives in an *.md file with YAML frontmatter, for example:

    ---
    name: starter-coder
    description: A pragmatic coding assistant.
    triggers: ["code", "refactor", "bug"]
    model: claude-sonnet-4-6
    ---

    You are a pragmatic software engineer. Prefer reading the code over
    guessing. When unsure, use tools...

Drop a new file in backend/skills/, hit POST /api/skills/reload, and it
goes live without a redeploy.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import Optional

logger = logging.getLogger(__name__)

# yaml is a hard dependency of FastAPI / pydantic stacks already, but guard
# so this file is still importable in reduced environments.
try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover
    yaml = None  # type: ignore


@dataclass
class Skill:
    name: str
    description: str
    body: str
    triggers: list[str] = field(default_factory=list)
    model: Optional[str] = None
    path: Optional[str] = None
    mtime: float = 0.0

    def to_public(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "triggers": list(self.triggers),
            "model": self.model,
            "path": self.path,
        }

    def to_full(self) -> dict:
        out = self.to_public()
        out["body"] = self.body
        return out


class SkillRegistry:
    """In-memory registry of file-based skills with mtime-driven reload."""

    def __init__(self, directory: str | Path):
        self._dir = Path(directory)
        self._skills: dict[str, Skill] = {}
        self._lock = Lock()
        self._last_loaded_at: float = 0.0

    # ----- public API ---------------------------------------------------

    def load_directory(self, directory: str | Path | None = None) -> int:
        """(Re)load every *.md in the directory. Returns count loaded."""
        if directory is not None:
            self._dir = Path(directory)
        self._dir.mkdir(parents=True, exist_ok=True)
        loaded: dict[str, Skill] = {}
        for p in sorted(self._dir.glob("*.md")):
            skill = self._parse_file(p)
            if skill is None:
                continue
            loaded[skill.name] = skill
        with self._lock:
            self._skills = loaded
            self._last_loaded_at = time.time()
        logger.info("SkillRegistry: loaded %d skills from %s", len(loaded), self._dir)
        return len(loaded)

    def reload(self) -> int:
        return self.load_directory()

    def get(self, name: str) -> Optional[Skill]:
        with self._lock:
            return self._skills.get(name)

    def list_all(self) -> list[Skill]:
        with self._lock:
            return list(self._skills.values())

    def match_by_trigger(self, text: str) -> list[Skill]:
        text_low = (text or "").lower()
        out: list[Skill] = []
        with self._lock:
            for s in self._skills.values():
                if any(t.lower() in text_low for t in s.triggers):
                    out.append(s)
        return out

    @property
    def directory(self) -> str:
        return str(self._dir)

    @property
    def last_loaded_at(self) -> float:
        return self._last_loaded_at

    # ----- internal -----------------------------------------------------

    def _parse_file(self, path: Path) -> Optional[Skill]:
        try:
            raw = path.read_text(encoding="utf-8")
        except Exception as exc:
            logger.warning("SkillRegistry: read failed %s: %s", path, exc)
            return None
        meta, body = _split_frontmatter(raw)
        name = meta.get("name") or path.stem
        description = meta.get("description", "").strip()
        triggers = meta.get("triggers") or []
        if isinstance(triggers, str):
            triggers = [t.strip() for t in triggers.split(",") if t.strip()]
        model = meta.get("model")
        return Skill(
            name=str(name),
            description=str(description),
            body=body.strip(),
            triggers=[str(t) for t in triggers],
            model=str(model) if model else None,
            path=str(path),
            mtime=path.stat().st_mtime,
        )


def _split_frontmatter(raw: str) -> tuple[dict, str]:
    """Return (frontmatter_dict, body). Missing frontmatter -> ({}, raw)."""
    if not raw.startswith("---"):
        return {}, raw
    end = raw.find("\n---", 3)
    if end < 0:
        return {}, raw
    fm_text = raw[3:end].strip()
    body = raw[end + 4 :].lstrip("\n")
    meta: dict = {}
    if yaml is not None:
        try:
            parsed = yaml.safe_load(fm_text) or {}
            if isinstance(parsed, dict):
                meta = parsed
        except Exception as exc:
            logger.warning("SkillRegistry: YAML parse failed: %s", exc)
    else:  # minimal fallback: key: value lines only
        for line in fm_text.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip().strip('"\'')
    return meta, body


# ----- process-singleton -------------------------------------------------

_registry: Optional[SkillRegistry] = None
_DEFAULT_DIR = Path(__file__).resolve().parent.parent.parent / "skills"


def get_registry(directory: str | Path | None = None) -> SkillRegistry:
    """Return the process-wide registry, initializing on first call."""
    global _registry
    if _registry is None:
        _registry = SkillRegistry(directory or _DEFAULT_DIR)
        try:
            _registry.load_directory()
        except Exception as exc:
            logger.warning("SkillRegistry initial load failed: %s", exc)
    elif directory is not None:
        _registry.load_directory(directory)
    return _registry
