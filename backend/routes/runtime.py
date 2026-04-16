"""
Runtime control routes: task lifecycle, event feed, and swarm capability introspection.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from services.events import event_bus
from services.runtime.task_manager import task_manager

router = APIRouter(prefix="/api/runtime", tags=["runtime"])


def _get_auth():
    from deps import get_current_user

    return get_current_user


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


@router.get("/swarm/capabilities")
async def swarm_capabilities(_user: dict = Depends(_get_auth())):
    max_branches_env: Optional[str] = os.environ.get("CRUCIB_SWARM_MAX_BRANCHES")
    hard_cap = int(max_branches_env) if max_branches_env and max_branches_env.isdigit() else None

    agent_count: Optional[int] = None
    try:
        from routes.projects import _ORCHESTRATION_AGENTS

        agent_count = len(_ORCHESTRATION_AGENTS)
    except Exception:
        agent_count = None

    return {
        "success": True,
        "mode": "SWAN",
        "spawn_limit": hard_cap,
        "spawn_unbounded": hard_cap is None,
        "estimated_agent_catalog_count": agent_count,
    }
