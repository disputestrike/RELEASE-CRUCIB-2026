"""
Incremental execution for CrucibAI — re-run only what changed.
Given project state and previous run outputs, determines which agents/phases need re-execution.
"""

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


def input_fingerprint(agent_name: str, prompt: str, context: Dict[str, Any]) -> str:
    """Compute a fingerprint for agent input (prompt + relevant context)."""
    data = json.dumps(
        {
            "agent": agent_name,
            "prompt": prompt[:2000],
            "context_keys": sorted(context.keys()),
            "context": context,
        },
        sort_keys=True,
    )
    return hashlib.sha256(data.encode()).hexdigest()[:24]


def agents_to_rerun(
    previous_outputs: Dict[str, Any],
    current_prompt: str,
    current_context: Dict[str, Any],
    all_agent_names: List[str],
    dependency_order: Optional[Dict[str, List[str]]] = None,
) -> Set[str]:
    """
    Determine which agents need to run given previous outputs and current prompt/context.
    previous_outputs: { agent_name: output_or_fingerprint }
    If prompt or context changed, agents depending on that context need re-run.
    Simplified: if prompt changed, all agents; else return empty (full run not incremental).
    """
    # Minimal implementation: no persistent fingerprint store, so we recommend full run
    # When wired to project_state: compare stored fingerprints per agent and return subset
    return (
        set()
    )  # empty = caller should run full build; or return set(all_agent_names) for full


def phases_to_rerun(
    previous_phases_completed: List[int],
    agents_to_run: Set[str],
    phases: List[List[str]],
) -> List[int]:
    """Given which agents must run, return phase indices that contain at least one of those agents."""
    if not agents_to_run:
        return []
    out = []
    for idx, agent_list in enumerate(phases):
        if agents_to_run & set(agent_list):
            out.append(idx)
    return out
