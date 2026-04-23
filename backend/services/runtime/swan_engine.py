"""SWAN engine: scalable subagent branch planning without fixed hard cap."""

from __future__ import annotations

import os
import uuid
from typing import Dict, List, Optional


class SwanEngine:
    ROLE_MAP = {
        "swan": ["architect", "engineer", "critic", "validator", "optimizer", "integrator"],
        "classic": ["engineer", "reviewer", "synthesizer"],
        "diverse_priors": ["architect", "engineer", "reviewer", "optimizer"],
        "role_based": ["frontend", "backend", "database", "security"],
    }

    @classmethod
    def resolve_branches(cls, requested: int) -> Dict[str, Optional[int]]:
        n = max(1, int(requested))
        cap_env = os.environ.get("CRUCIB_SWARM_MAX_BRANCHES")
        cap = int(cap_env) if cap_env and cap_env.isdigit() else None
        actual = min(n, cap) if cap else n
        return {
            "requested": n,
            "actual": actual,
            "hard_limit": cap,
            "unbounded": cap is None,
        }

    @classmethod
    def build_subagents(
        cls,
        count: int,
        mode: str = "swan",
        strategy: Optional[str] = None,
        predefined_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, str]]:
        count = max(1, int(count))
        roster_key = strategy or mode or "swan"
        roster = cls.ROLE_MAP.get(roster_key, cls.ROLE_MAP["swan"])
        items: List[Dict[str, str]] = []
        for i in range(count):
            pid = None
            if predefined_ids and i < len(predefined_ids):
                pid = str(predefined_ids[i]).strip() or None
            sid = pid or str(uuid.uuid4())
            items.append({"id": sid, "role": roster[i % len(roster)]})
        return items
