"""
Generation policy — minimal coherent workspaces (source-of-truth for gating).

Problem addressed
-----------------
ZIP-2-style breadth came from:
1. ``rule:default_support`` always adding ~9 “support” agents on every intelligent run,
   then ``_dependency_closure`` pulling their full dependency cones from ``AGENT_DAG``.
2. Over-broad ``AGENT_KEYWORDS`` (e.g. word ``api`` matching almost every web spec).
3. ``build_agent_swarm_phases`` falling back to **all** DAG keys when no goal.
4. Fixed Auto-Runner phases always running Auth + full database migration/seed even when
   integrations did not call for them.
5. ``ensure_standard_workspace_scaffold`` pre-creating empty top-level product dirs
   (client/server/docs/…) before any agent wrote real files.

Policy (summary)
----------------
* Intelligent selection: BASE agents + keyword/contract hits + dependency closure only.
  No unconditional “default support” pack unless ``CRUCIBAI_LEGACY_BROAD_AGENT_SUPPORT=1``.
* Keyword registry: avoid single-token triggers that match most specs; prefer phrases.
* Swarm fallback without goal: BASE agents only — never ``list(AGENT_DAG.keys())``.
* Fixed planner: auth step only if ``auth`` integration; DB phase + models only if
  ``database`` integration or ``frontend`` build_kind skips DB entirely.
* Scaffold: default ``minimal`` (META only); set ``CRUCIBAI_WORKSPACE_SCAFFOLD_MODE=full``
  to restore legacy empty dirs.
"""
from __future__ import annotations

import os
import re
from typing import List


def legacy_broad_agent_support_enabled() -> bool:
    return os.environ.get("CRUCIBAI_LEGACY_BROAD_AGENT_SUPPORT", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def workspace_scaffold_mode() -> str:
    return os.environ.get("CRUCIBAI_WORKSPACE_SCAFFOLD_MODE", "minimal").strip().lower() or "minimal"


def fixed_planner_skip_database(build_kind: str, integrations: List[str]) -> bool:
    """Omit Database-agent model + DB phase when not a data-backed build."""
    if (build_kind or "").strip().lower() == "frontend":
        return True
    return "database" not in (integrations or [])


def fixed_planner_skip_auth(integrations: List[str]) -> bool:
    return "auth" not in (integrations or [])


def goal_suggests_database(goal: str) -> bool:
    """Heuristic when integrations missed 'database' but the goal clearly needs persistence."""
    g = (goal or "").lower()
    return bool(
        re.search(
            r"\b(postgres|postgresql|mysql|mongodb|sqlite|drizzle|prisma|sqlalchemy|"
            r"typeorm|sequelize|orm|migrations?|schema\.sql)\b",
            g,
        )
    )
