"""
dag_engine.py — Dependency-aware DAG scheduler for job steps.
- Topological resolution of ready nodes
- Parallel execution of independent nodes
- Node-level retry (never reruns whole job)
- Downstream blocking on unrecoverable failure
"""
import json
import logging
from typing import List, Dict, Any, Set, Optional

from .runtime_state import get_steps, update_step_state

logger = logging.getLogger(__name__)


async def get_ready_steps(job_id: str) -> List[Dict[str, Any]]:
    """Return steps whose dependencies are all completed and are still pending."""
    steps = await get_steps(job_id)
    by_key: Dict[str, Dict] = {s["step_key"]: s for s in steps}

    ready = []
    for step in steps:
        if step["status"] != "pending":
            continue
        deps = json.loads(step.get("depends_on_json") or "[]")
        all_done = all(
            by_key.get(dep, {}).get("status") == "completed"
            for dep in deps
        )
        if all_done:
            ready.append(step)
    return ready


async def all_steps_finished(job_id: str) -> bool:
    """True when every step is in a terminal state."""
    steps = await get_steps(job_id)
    terminal = {"completed", "failed", "skipped"}
    return all(s["status"] in terminal for s in steps)


async def has_blocking_failure(job_id: str) -> bool:
    """True if any step failed and has unblocked dependents that can't proceed."""
    steps = await get_steps(job_id)
    failed_keys = {s["step_key"] for s in steps if s["status"] == "failed"}
    if not failed_keys:
        return False
    # Check if any pending step depends on a failed step
    for step in steps:
        if step["status"] == "pending":
            deps = json.loads(step.get("depends_on_json") or "[]")
            if any(d in failed_keys for d in deps):
                return True
    return False


async def block_dependents(job_id: str, failed_step_key: str) -> None:
    """Mark downstream steps as 'blocked' when a required dep fails."""
    steps = await get_steps(job_id)
    for step in steps:
        if step["status"] not in ("pending",):
            continue
        deps = json.loads(step.get("depends_on_json") or "[]")
        if failed_step_key in deps:
            await update_step_state(step["id"], "blocked",
                                    {"error_message": f"Blocked by failed dep: {failed_step_key}"})
            logger.info("dag_engine: blocked step %s (dep %s failed)", step["step_key"], failed_step_key)
            # Recursively block transitive dependents
            await block_dependents(job_id, step["step_key"])


def build_dag_from_plan(plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert a planner output to a flat list of step definitions.
    Returns list of dicts: {step_key, agent_name, phase, depends_on, order_index}
    """
    steps = []
    order = 0
    prev_phase_keys: List[str] = []

    for phase in plan.get("phases", []):
        phase_key = phase["key"]
        current_phase_keys = []

        for step in phase.get("steps", []):
            step_key = step.get("key") or f"{phase_key}.{step.get('name', str(order))}"
            explicit_deps = step.get("depends_on", [])
            # If no explicit deps, depend on all steps from previous phase
            deps = explicit_deps if explicit_deps else list(prev_phase_keys)

            steps.append({
                "step_key": step_key,
                "agent_name": step.get("agent", phase_key),
                "phase": phase_key,
                "depends_on": deps,
                "order_index": order,
                "description": step.get("description", ""),
            })
            current_phase_keys.append(step_key)
            order += 1

        prev_phase_keys = current_phase_keys

    return steps
