"""
P7 — Orphan agents: subset of `not_fully_integrated_agent` from `docs/agent_audit.json`
that are safe to drop from *keyword-driven* selection and dependency closure.

We intentionally do **not** block every `not_fully_integrated` row: the audit flags many
swarm agents the planner still expects (e.g. Smart Contract Agent) until wiring lands.
This module targets **3D / WebGL / immersive** cluster agents that are common false
positives from short keywords ("ar", "vr", "canvas") without blocking blockchain / infra paths.
"""
from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import FrozenSet

logger = logging.getLogger(__name__)

_ORPHAN_FAMILY_RE = re.compile(
    r"(^3d\b|\b3d\b|webgl|babylon|cesium|\bar/vr\b|\bopenxr\b|\bunity\b|\bunreal\b)",
    re.IGNORECASE,
)


def _audit_json_path() -> Path:
    return Path(__file__).resolve().parents[2] / "docs" / "agent_audit.json"


@lru_cache(maxsize=1)
def agents_excluded_from_autorunner_selection() -> FrozenSet[str]:
    p = _audit_json_path()
    if not p.is_file():
        logger.warning("agent_audit_registry: missing %s — no orphan exclusions", p)
        return frozenset()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("agent_audit_registry: read failed %s: %s", p, e)
        return frozenset()
    out: set[str] = set()
    for row in data.get("agents") or []:
        if row.get("group") != "not_fully_integrated_agent":
            continue
        name = row.get("agent_name")
        if not isinstance(name, str) or not name.strip():
            continue
        name = name.strip()
        notes = str(row.get("notes") or "")
        hay = f"{name} {notes}"
        if _ORPHAN_FAMILY_RE.search(hay):
            out.add(name)
    return frozenset(out)
