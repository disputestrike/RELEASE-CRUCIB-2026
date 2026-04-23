"""Canonical orchestration brain policy (JSON shim).

Loaded from ``brain_policy.json`` beside this module. Disable with
``CRUCIBAI_BRAIN_POLICY=0`` if needed for experiments.
"""

from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_POLICY_FILE = Path(__file__).resolve().parent / "brain_policy.json"
_DISABLED = os.environ.get("CRUCIBAI_BRAIN_POLICY", "").strip().lower() in (
    "0",
    "off",
    "false",
    "disabled",
)


@lru_cache(maxsize=1)
def load_brain_policy() -> Dict[str, Any]:
    if _DISABLED:
        return {}
    try:
        with open(_POLICY_FILE, encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {}
            return data
    except FileNotFoundError:
        logger.warning("brain_policy: missing file %s", _POLICY_FILE)
        return {}
    except Exception as exc:
        logger.warning("brain_policy: could not load %s: %s", _POLICY_FILE, exc)
        return {}


def clear_brain_policy_cache() -> None:
    """For tests only."""
    load_brain_policy.cache_clear()


def policy_version() -> str:
    return str(load_brain_policy().get("version") or "")


def get_system_directive_text() -> str:
    return str(load_brain_policy().get("system_directive_text") or "").strip()


def repair_route_for(classification: str) -> Optional[str]:
    p = load_brain_policy()
    repair = p.get("repair") or {}
    routes = repair.get("route_to") or {}
    if not isinstance(routes, dict):
        return None
    return routes.get(classification)


def agent_selection_warn_threshold() -> Optional[int]:
    p = load_brain_policy()
    sel = p.get("agent_selection") or {}
    raw = sel.get("warn_if_selected_agents_exceed")
    try:
        n = int(raw)
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


def agent_selection_hard_cap() -> Optional[int]:
    """Upper bound on swarm agents after dependency closure (governor). None = disabled."""
    p = load_brain_policy()
    sel = p.get("agent_selection") or {}
    raw = sel.get("hard_max_selected_agents")
    try:
        n = int(raw)
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


def get_agent_governor_preface() -> str:
    """Short block prepended to swarm agent prompts (policy enforcement at router)."""
    if not load_brain_policy():
        return ""
    directive = get_system_directive_text()
    if len(directive) > 900:
        directive = directive[:900].rstrip() + "…"
    lines = [
        "[GOVERNOR — orchestration policy]",
        "Implement only this step's scope. Honor node manifest allowed_paths and verification when present.",
        "Match syntax to file extension (.ts/.tsx/.js/.jsx → JavaScript/TypeScript only; .py → Python; .sql → SQL).",
        "Prefer minimal patches; do not rewrite unrelated modules.",
    ]
    if directive:
        lines.append("Pinned directive: " + directive)
    return "\n".join(lines)


def attach_brain_policy_to_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    """Mutate plan with policy metadata, acceptance lines, and optional governor warnings."""
    p = load_brain_policy()
    if not p:
        return plan
    plan["brain_policy"] = {
        "version": p.get("version"),
        "name": p.get("name"),
        "system_directive_text": p.get("system_directive_text"),
    }
    crit: List[str] = list(plan.get("acceptance_criteria") or [])
    extras = [
        "Orchestration brain: keep agent activation relevant to the goal; expand dependencies only when the DAG requires them.",
        "Verify touched scopes at phase boundaries; do not rely on a single late gate for syntax, imports, or types.",
        "Treat failures as checkpointed state: persist progress, classify errors, repair the smallest surface, then re-run targeted checks.",
    ]
    for line in extras:
        if line not in crit:
            crit.append(line)
    plan["acceptance_criteria"] = crit

    thresh = agent_selection_warn_threshold()
    n = int(plan.get("selected_agent_count") or 0)
    if thresh and n > thresh:
        warns = list(plan.get("governor_warnings") or [])
        msg = (
            f"Selected {n} swarm agents exceeds brain_policy threshold ({thresh}); "
            "review keyword rules and goal specificity to reduce irrelevant activation."
        )
        if msg not in warns:
            warns.append(msg)
        plan["governor_warnings"] = warns
    return plan


def job_started_policy_meta() -> Dict[str, str]:
    p = load_brain_policy()
    if not p:
        return {}
    return {
        "brain_policy_version": str(p.get("version") or ""),
        "brain_policy_name": str(p.get("name") or ""),
    }
