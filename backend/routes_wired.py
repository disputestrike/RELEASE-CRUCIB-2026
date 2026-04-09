"""
Compatibility route shim for older feature-wire tests.

This route now delegates to the live planner/controller path instead of
maintaining a toy executor. It is intentionally not mounted by default; the
authoritative production endpoints live in ``backend/server.py``.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, HTTPException

try:  # pragma: no cover - import style depends on PYTHONPATH
    from orchestration.planner import generate_plan
except ImportError:  # pragma: no cover
    from backend.orchestration.planner import generate_plan

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/api/build-wired")
async def build_wired(
    requirements: str = Body(...),
    project_id: Optional[str] = Body(None),
) -> Dict[str, Any]:
    """
    Read-only compatibility endpoint.

    Returns the same planning/controller metadata that powers the public
    ``/api/build`` planner alias so older callers see the real orchestration
    story, not a fake mini-runtime.
    """
    goal = (requirements or "").strip()
    if not goal:
        raise HTTPException(status_code=400, detail="requirements is required")

    resolved_project_id = project_id or f"proj-{uuid.uuid4().hex[:8]}"
    try:
        plan = await generate_plan(goal, project_state={"project_id": resolved_project_id})
        plan["phase_count"] = int(plan.get("phase_count") or len(plan.get("phases", [])))
        return {
            "status": "success",
            "project_id": resolved_project_id,
            "plan": plan,
            "controller_summary": plan.get("controller_summary") or {},
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("build_wired failed")
        raise HTTPException(status_code=500, detail=str(exc))


__all__ = ["router", "build_wired"]
