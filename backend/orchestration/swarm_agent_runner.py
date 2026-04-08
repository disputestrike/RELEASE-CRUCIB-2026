"""Agent swarm planning + execution bridge for Auto-Runner.

This module lets the relational Auto-Runner execute the existing AGENT_DAG
instead of falling back to small fixed frontend/backend phases for complex
multi-stack or enterprise-style requests.
"""
from __future__ import annotations

import hashlib
import os
import re
from typing import Any, Dict, List

from agent_dag import AGENT_DAG, get_execution_phases
from agent_resilience import get_criticality

from .agent_selection_logic import build_full_phases_from_dag, select_agents_for_goal
from .runtime_state import get_steps, load_checkpoint


SWARM_STEP_PREFIX = "agents"
_COMPLEX_SWARM_MARKERS = (
    "helios aegis command",
    "aegis omega",
    "elite autonomous system test",
    "crm",
    "quote workflow",
    "project workflow",
    "policy engine",
    "immutable audit",
    "compliance",
    "tenant isolation",
    "multi-tenant",
    "background jobs",
    "worker/job system",
    "integration adapters",
    "analytics/reporting",
)
_CORE_NO_FALLBACK_AGENTS = frozenset(
    {
        "Planner",
        "Requirements Clarifier",
        "Stack Selector",
        "Frontend Generation",
        "Backend Generation",
        "Database Agent",
        "File Tool Agent",
    }
)


def slugify_agent_name(agent_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", (agent_name or "").strip().lower())
    return slug.strip("_") or "agent"


def swarm_step_key(agent_name: str) -> str:
    return f"{SWARM_STEP_PREFIX}.{slugify_agent_name(agent_name)}"


def uses_agent_swarm(goal: str, stack_contract: Dict[str, Any] | None = None) -> bool:
    goal_lc = (goal or "").lower()
    contract = stack_contract or {}
    if contract.get("requires_full_system_builder"):
        return True
    hit_count = sum(1 for marker in _COMPLEX_SWARM_MARKERS if marker in goal_lc)
    return hit_count >= 4


def build_agent_swarm_phases(
    goal: str = "",
    stack_contract: Dict[str, Any] | None = None,
    selected_agents: List[str] | None = None,
) -> List[Dict[str, Any]]:
    phases: List[Dict[str, Any]] = []
    chosen_agents = selected_agents
    if chosen_agents is None:
        chosen_agents = (
            select_agents_for_goal(goal, stack_contract)
            if goal
            else list(AGENT_DAG.keys())
        )

    filtered = {name: AGENT_DAG[name] for name in chosen_agents if name in AGENT_DAG}
    phase_groups = (
        build_full_phases_from_dag(list(filtered.keys()), AGENT_DAG)
        if filtered
        else get_execution_phases(AGENT_DAG)
    )

    for idx, agent_names in enumerate(phase_groups, start=1):
        steps = []
        for agent_name in agent_names:
            deps = [
                swarm_step_key(dep)
                for dep in AGENT_DAG.get(agent_name, {}).get("depends_on", [])
                if dep in AGENT_DAG
            ]
            prompt = (AGENT_DAG.get(agent_name, {}).get("system_prompt") or "").strip()
            description = prompt.splitlines()[0][:180] if prompt else f"Run {agent_name}"
            steps.append(
                {
                    "key": swarm_step_key(agent_name),
                    "agent": agent_name,
                    "name": agent_name,
                    "description": description,
                    "depends_on": deps,
                }
            )
        phases.append(
            {
                "key": f"{SWARM_STEP_PREFIX}.phase_{idx:02d}",
                "label": f"Agent Swarm {idx:02d}",
                "steps": steps,
            }
        )
    return phases


def _safe_user_ref(user_id: str | None) -> Dict[str, str] | None:
    if user_id:
        return {"id": user_id}
    return None


def _workspace_file_snapshot(workspace_path: str) -> Dict[str, str]:
    snapshot: Dict[str, str] = {}
    if not workspace_path or not os.path.isdir(workspace_path):
        return snapshot
    for root, _, files in os.walk(workspace_path):
        for name in files:
            full = os.path.join(root, name)
            try:
                rel = os.path.relpath(full, workspace_path).replace("\\", "/")
                stat = os.stat(full)
                digest = hashlib.sha256(f"{stat.st_mtime_ns}:{stat.st_size}".encode("utf-8")).hexdigest()
                snapshot[rel] = digest
            except OSError:
                continue
    return snapshot


async def _load_previous_agent_outputs(job_id: str, current_step: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    previous_outputs: Dict[str, Dict[str, Any]] = {}
    try:
        all_steps = await get_steps(job_id)
    except Exception:
        return previous_outputs
    current_order = int(current_step.get("order_index") or 0)
    for step in all_steps:
        if not str(step.get("step_key") or "").startswith(f"{SWARM_STEP_PREFIX}."):
            continue
        if int(step.get("order_index") or 0) >= current_order:
            continue
        if step.get("status") != "completed":
            continue
        try:
            checkpoint = await load_checkpoint(job_id, step["step_key"])
        except Exception:
            checkpoint = None
        if not checkpoint:
            continue
        agent_name = step.get("agent_name") or checkpoint.get("agent_name") or step["step_key"]
        result = checkpoint.get("result")
        if isinstance(result, dict):
            previous_outputs[agent_name] = result
            continue
        output = checkpoint.get("output") or ""
        previous_outputs[agent_name] = {
            "output": output,
            "result": output,
            "status": checkpoint.get("status") or "completed",
        }
    return previous_outputs


async def _run_server_swarm_agent(
    *,
    project_id: str,
    user_id: str,
    agent_name: str,
    project_prompt: str,
    build_kind: str,
    previous_outputs: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    import server

    user_ref = _safe_user_ref(user_id)
    user_keys = await server.get_workspace_api_keys(user_ref)
    effective = server._effective_api_keys(user_keys)
    model_chain = server._get_model_chain(
        "auto",
        project_prompt,
        effective_keys=effective,
        force_complex=True,
    )

    user_tier = "free"
    available_credits = 0
    try:
        if user_id:
            user = await server.db.users.find_one({"id": user_id}, {"plan": 1, "credit_balance": 1})
            if user:
                user_tier = user.get("plan", "free")
                available_credits = user.get("credit_balance", 0) or 0
    except Exception:
        pass
    speed_selector = server._speed_from_plan(user_tier)

    return await server._run_single_agent_with_retry(
        project_id,
        user_id,
        agent_name,
        project_prompt,
        previous_outputs,
        effective,
        model_chain,
        build_kind=build_kind,
        user_tier=user_tier,
        speed_selector=speed_selector,
        available_credits=available_credits,
    )


async def run_swarm_agent_step(step: Dict[str, Any], job: Dict[str, Any], workspace_path: str = "") -> Dict[str, Any]:
    """Execute one AGENT_DAG step through the existing server-side swarm runtime."""
    agent_name = step.get("agent_name") or step.get("name") or ""
    if agent_name not in AGENT_DAG:
        raise RuntimeError(f"unknown_swarm_agent:{agent_name}")

    job_id = job.get("id") or ""
    project_id = job.get("project_id") or job_id
    user_id = job.get("user_id") or ""
    project_prompt = (job.get("goal") or "").strip()
    build_kind = (job.get("build_kind") or "").strip().lower() or "fullstack"

    previous_outputs = await _load_previous_agent_outputs(job_id, step)
    before = _workspace_file_snapshot(workspace_path)

    result = await _run_server_swarm_agent(
        project_id=project_id,
        user_id=user_id,
        agent_name=agent_name,
        project_prompt=project_prompt,
        build_kind=build_kind,
        previous_outputs=previous_outputs,
    )

    status = str(result.get("status") or "").lower()
    if status in ("failed", "failed_with_fallback", "skipped"):
        criticality = get_criticality(agent_name)
        if agent_name in _CORE_NO_FALLBACK_AGENTS or criticality in ("critical", "high"):
            raise RuntimeError(
                f"swarm_agent_failed:{agent_name}:{result.get('reason') or status}"
            )

    after = _workspace_file_snapshot(workspace_path)
    changed_files = sorted(
        rel for rel, digest in after.items()
        if before.get(rel) != digest
    )

    artifact_path = f"outputs/{slugify_agent_name(agent_name)}.md"
    artifacts = []
    if workspace_path and os.path.isfile(os.path.join(workspace_path, artifact_path.replace("/", os.sep))):
        artifacts.append({"kind": "agent_output", "path": artifact_path, "agent": agent_name})

    return {
        "output": result.get("output") or result.get("result") or "",
        "result": result,
        "output_files": changed_files,
        "artifacts": artifacts,
        "agent_name": agent_name,
        "execution_mode": "agent_swarm",
        "previous_output_count": len(previous_outputs),
    }
