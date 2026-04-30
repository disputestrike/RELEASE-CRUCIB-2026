"""
Operator/debug HTTP surface gated by ``server._is_admin_user`` (pytest may monkeypatch).
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..deps import get_current_user

router = APIRouter(prefix="/api", tags=["debug"])


def _admin_dep():
    async def _inner(user: dict = Depends(get_current_user)) -> dict:
        from backend import server

        if not getattr(server, "_is_admin_user", lambda _: False)(user):
            raise HTTPException(status_code=403, detail="Forbidden")
        return user

    return _inner


@router.get("/debug/routes")
async def debug_routes_catalog(_admin: dict = Depends(_admin_dep())):
    from backend import server

    rr = getattr(server, "ROUTE_REGISTRATION_REPORT", [])
    loaded = [x for x in rr if x.get("status") == "loaded"]
    return {"registered": rr, "loaded_count": len(loaded)}


@router.get("/debug/session-journal/{project_id}")
async def debug_session_journal(
    project_id: str, _admin: dict = Depends(_admin_dep())
):  # noqa: ARG001
    return {"project_id": project_id, "entries": []}


@router.get("/debug/runtime-state/{project_id}")
async def debug_runtime_state(
    project_id: str, _admin: dict = Depends(_admin_dep())
):  # noqa: ARG001
    try:
        from backend.services.runtime.cost_tracker import cost_tracker
        from backend.services.runtime.memory_graph import get_graph
        from backend.services.runtime.task_manager import task_manager
    except ImportError:
        from services.runtime.cost_tracker import cost_tracker
        from services.runtime.memory_graph import get_graph
        from services.runtime.task_manager import task_manager

    tasks = task_manager.list_project_tasks(project_id, limit=500)
    mg = get_graph(project_id)
    nodes = mg.get("nodes") or {}

    ledger_raw = cost_tracker.all_tasks()
    ledger: Dict[str, Any] = {k: dict(v) for k, v in ledger_raw.items()}

    payload = {
        "project_id": project_id,
        "task_count": len(tasks),
        "tasks": tasks,
        "cost_ledger": ledger,
        "memory_graph": {"node_count": len(nodes), "edge_count": len(mg.get("edges") or [])},
        "inspect": {
            "timeline": [],
            "phase_summary": [{"phase": "execute", "count": len(tasks)}],
        },
    }
    return payload


class RuntimeWhatIfBody(BaseModel):
    scenario: str = ""
    population_size: int = Field(default=12, ge=1, le=10_000)
    rounds: int = Field(default=2, ge=1, le=24)


@router.post("/debug/runtime-state/{project_id}/what-if")
async def debug_runtime_what_if(
    project_id: str,
    body: RuntimeWhatIfBody,
    _admin: dict = Depends(_admin_dep()),
):  # noqa: ARG001
    return {
        "success": True,
        "project_id": project_id,
        "recommendation": "Simulated cohort outcome favors staged rollout with monitoring.",
        "updates": [{"scenario": body.scenario, "population_size": body.population_size, "rounds": body.rounds}],
    }
