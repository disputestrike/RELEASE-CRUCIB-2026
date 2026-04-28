"""
Runtime control routes: task lifecycle, event feed, and swarm capability introspection.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

try:
    from ..services.events import event_bus
    from ..services.runtime.task_manager import task_manager
except ImportError:  # compatibility for legacy tests importing `routes.runtime`
    try:
        from services.events import event_bus
        from services.runtime.task_manager import task_manager
    except ImportError:
        from backend.services.events import event_bus
        from backend.services.runtime.task_manager import task_manager

router = APIRouter(prefix="/api/runtime", tags=["runtime"])


def _get_auth():
    try:
        from ..deps import get_current_user
    except ImportError:  # compatibility for legacy tests importing `routes.runtime`
        from backend.deps import get_current_user

    return get_current_user


def _get_optional_user():
    try:
        from ..deps import get_optional_user
    except ImportError:  # compatibility for legacy tests importing `routes.runtime`
        from backend.deps import get_optional_user

    return get_optional_user


def _agent_catalog_count() -> Optional[int]:
    try:
        try:
            from ..agent_dag import AGENT_DAG
        except ImportError:  # compatibility for legacy tests importing `routes.runtime`
            from backend.agent_dag import AGENT_DAG

        return len(AGENT_DAG)
    except Exception:
        return None


class CreateTaskBody(BaseModel):
    project_id: str = Field(..., min_length=2, max_length=240)
    description: str = Field(..., min_length=1, max_length=4000)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class UpdateTaskStatusBody(BaseModel):
    project_id: str = Field(..., min_length=2, max_length=240)
    status: str = Field(..., min_length=3, max_length=40)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class KillTaskBody(BaseModel):
    project_id: str = Field(..., min_length=2, max_length=240)
    reason: str = Field(default="manual_kill", max_length=400)


class PauseTaskBody(BaseModel):
    project_id: str = Field(..., min_length=2, max_length=240)
    reason: str = Field(default="manual_pause", max_length=400)


class ResumeTaskBody(BaseModel):
    project_id: str = Field(..., min_length=2, max_length=240)
    reason: str = Field(default="manual_resume", max_length=400)


@router.post("/tasks")
async def create_runtime_task(body: CreateTaskBody, user: dict = Depends(_get_auth())):
    task = task_manager.create_task(
        project_id=body.project_id,
        description=body.description,
        metadata={"owner": user.get("id"), **(body.metadata or {})},
    )
    return {"success": True, "task": task}


@router.get("/tasks")
async def list_runtime_tasks(
    project_id: str = Query(..., min_length=2, max_length=240),
    limit: int = Query(100, ge=1, le=1000),
    _user: dict = Depends(_get_auth()),
):
    rows = task_manager.list_project_tasks(project_id, limit=limit)
    return {"success": True, "tasks": rows, "count": len(rows)}


@router.get("/tasks/{task_id}")
async def get_runtime_task(
    task_id: str,
    project_id: str = Query(..., min_length=2, max_length=240),
    _user: dict = Depends(_get_auth()),
):
    task = task_manager.get_task(project_id, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True, "task": task}


@router.post("/tasks/{task_id}/kill")
async def kill_runtime_task(task_id: str, body: KillTaskBody, _user: dict = Depends(_get_auth())):
    task = task_manager.kill_task(body.project_id, task_id, reason=body.reason)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True, "task": task}


@router.post("/tasks/{task_id}/pause")
async def pause_runtime_task(task_id: str, body: PauseTaskBody, _user: dict = Depends(_get_auth())):
    task = task_manager.pause_task(body.project_id, task_id, reason=body.reason)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True, "task": task}


@router.post("/tasks/{task_id}/resume")
async def resume_runtime_task(task_id: str, body: ResumeTaskBody, _user: dict = Depends(_get_auth())):
    task = task_manager.resume_task(body.project_id, task_id, reason=body.reason)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True, "task": task}


@router.post("/tasks/{task_id}/status")
async def set_runtime_task_status(task_id: str, body: UpdateTaskStatusBody, _user: dict = Depends(_get_auth())):
    normalized = body.status.strip().lower()
    if normalized not in {"running", "completed", "failed", "killed", "queued", "pending"}:
        raise HTTPException(status_code=400, detail="Invalid status")
    task = task_manager.update_task(body.project_id, task_id, status=normalized, metadata=body.metadata or {})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True, "task": task}


@router.delete("/tasks/{task_id}")
async def delete_runtime_task(
    task_id: str,
    project_id: str = Query(..., min_length=2, max_length=240),
    _user: dict = Depends(_get_auth()),
):
    ok = task_manager.delete_task(project_id, task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True, "task_id": task_id, "deleted": True}


@router.get("/events/recent")
async def runtime_recent_events(limit: int = Query(100, ge=1, le=500), _user: dict = Depends(_get_auth())):
    rows = event_bus.recent_events(limit=limit)
    events = [
        {"type": r.event_type, "payload": r.payload, "ts": r.ts}
        for r in rows
    ]
    return {"success": True, "events": events, "count": len(events)}


@router.get("/metrics")
async def runtime_metrics(_user: dict = Depends(_get_optional_user())):
    """Production-safe runtime summary used by dashboard/home surfaces.

    This endpoint intentionally reports observable in-process/runtime facts and
    capability status. It does not pretend background workers or live agents are
    running when there are no active tasks in this process.
    """
    rows = event_bus.recent_events(limit=200)
    event_counts: Dict[str, int] = {}
    for row in rows:
        event_counts[row.event_type] = event_counts.get(row.event_type, 0) + 1
    active_tasks = [
        task
        for task in getattr(task_manager, "tasks", {}).values()
        if str(task.get("status") or "").lower() in {"running", "queued", "pending"}
    ]
    return {
        "success": True,
        "status": "operational",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "active_tasks": len(active_tasks),
        "recent_event_count": len(rows),
        "recent_event_types": event_counts,
        "agent_catalog_count": _agent_catalog_count(),
        "agent_execution": {
            "catalog": "available",
            "spawn_runtime": "available",
            "live_count": len(active_tasks),
            "note": "Active agent count reflects current runtime tasks, not the total DAG catalog.",
        },
    }


@router.get("/inspect")
async def runtime_inspect(
    limit: int = Query(50, ge=1, le=200),
    user: dict = Depends(_get_auth()),
):
    """Per-user runtime snapshot aligned with checkpoint/debug inspectors (tasks, costs, graph)."""
    try:
        from services.runtime.cost_tracker import cost_tracker
        from services.runtime.memory_graph import get_graph
        from services.runtime.task_manager import task_manager as _tm
    except ImportError:
        from backend.services.runtime.cost_tracker import cost_tracker
        from backend.services.runtime.memory_graph import get_graph
        from backend.services.runtime.task_manager import task_manager as _tm

    uid = str((user or {}).get("id") or "guest")
    project_id = f"runtime-{uid}"
    tasks = _tm.list_project_tasks(project_id, limit=limit)
    mg = get_graph(project_id)
    nodes = mg.get("nodes") or {}
    ledger_raw = cost_tracker.all_tasks()
    ledger = {k: dict(v) for k, v in ledger_raw.items()}

    return {
        "success": True,
        "status": "available",
        "project_id": project_id,
        "task_count": len(tasks),
        "tasks": tasks,
        "cost_ledger": ledger,
        "memory_graph": {
            "node_count": len(nodes),
            "edge_count": len(mg.get("edges") or []),
        },
        "inspect": {
            "timeline": [],
            "phase_summary": [{"phase": "execute", "count": len(tasks)}],
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/swarm/capabilities")
async def swarm_capabilities(_user: dict = Depends(_get_optional_user())):
    max_branches_env: Optional[str] = os.environ.get("CRUCIB_SWARM_MAX_BRANCHES")
    hard_cap = int(max_branches_env) if max_branches_env and max_branches_env.isdigit() else None

    agent_count = _agent_catalog_count()

    return {
        "success": True,
        "mode": "SWAN",
        "spawn_limit": hard_cap,
        "spawn_unbounded": hard_cap is None,
        "estimated_agent_catalog_count": agent_count,
        "truth_statement": "Core agent catalog is real; large population claims are modeled cohorts unless explicitly marked as live LLM branches.",
    }


# ── What-If Simulation ──────────────────────────────────────────────────────
class WhatIfBody(BaseModel):
    scenario: str = Field(..., min_length=1, max_length=8000)
    mode: str = Field(default="decision") # decision, forecast, market_reaction
    depth: str = Field(default="balanced")
    population_size: int = Field(default=1000, ge=3, le=10000)
    rounds: int = Field(default=4, ge=1, le=8)
    priors: Dict[str, float] = Field(default_factory=dict)
    agent_roles: Optional[list] = None


@router.post("/what-if")
async def run_what_if(body: WhatIfBody, user: dict = Depends(_get_auth())):
    """
    Run a What-If scenario simulation without requiring a pre-existing job.
    Spawns a population of agent personas, runs multi-round debate simulation,
    and returns clusters, sentiment shifts, and a recommendation.
    """
    from ..services.simulation.reality_engine import reality_engine
    uid = str((user or {}).get("id") or "guest")

    simulation = await reality_engine.create_simulation(
        user_id=uid,
        prompt=body.scenario,
        assumptions=[],
        attachments=[],
        metadata={"compatibility_route": "/api/runtime/what-if", "requested_mode": body.mode},
    )

    result = await reality_engine.run_simulation(
        simulation_id=simulation["id"],
        user_id=uid,
        prompt=body.scenario,
        assumptions=[],
        attachments=[],
        depth=body.depth,
        population_size=max(100, min(10000, int(body.population_size or 1000))),
        rounds=body.rounds,
        agent_count=max(3, min(24, int(body.population_size or 8))),
        metadata={"compatibility_route": "/api/runtime/what-if", "requested_mode": body.mode},
    )

    return {
        "success": True,
        "jobId": simulation["id"],
        "project_id": simulation["id"],
        "runtime_mode": "production",
        "simulationId": simulation["id"],
        "runId": (result.get("run") or {}).get("id"),
        "scenario": body.scenario,
        "updates": [
            {
                "round": row.get("round_number"),
                "purpose": row.get("purpose"),
                "consensus_emerging": False,
                "clusters": result.get("clusters") or [],
            }
            for row in result.get("rounds", [])
        ],
        **result,
    }


class BenchmarkRunPayload(BaseModel):
    execute_live: bool = False
    max_runs: int = Field(3, ge=1, le=64)
    output_subdir: str = Field("bench", max_length=240)


_benchmark_latest: Dict[str, Any] = {}


@router.post("/benchmark/run")
async def runtime_benchmark_run(
    body: BenchmarkRunPayload,
    _user: dict = Depends(_get_auth()),
):  # noqa: ARG001
    n = int(body.max_runs or 3)
    aggregate = {"p50_ms": 72.4, "p95_ms": 180.5, "samples": max(3, n * 30)}
    out = {
        "success": True,
        "mode": "simulated",
        "total_runs": n,
        "aggregate": aggregate,
        "output_subdir": body.output_subdir,
    }
    global _benchmark_latest
    _benchmark_latest = out
    return out


@router.get("/benchmark/latest")
async def runtime_benchmark_latest(_user: dict = Depends(_get_auth())):  # noqa: ARG001
    snap = dict(_benchmark_latest) if _benchmark_latest else {}
    return {"success": True, "latest": snap or None}
