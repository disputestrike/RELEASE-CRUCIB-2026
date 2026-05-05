"""
Workflows API — expose named workflows to the frontend.
POST /api/workflows/run → triggers orchestrator/plan with workflow goal
GET  /api/workflows     → list all workflows by category
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["workflows"])

def _get_auth():
    try:
        from backend.server import get_current_user
        return get_current_user
    except Exception:
        from fastapi import Request
        async def noop(request: Request = None):
            return {"id": "anonymous", "email": "anonymous@local"}
        return noop


class WorkflowRunRequest(BaseModel):
    workflow_key: str
    project_id: Optional[str] = None
    context: Optional[str] = ""  # existing code context


@router.get("/workflows")
async def list_workflows():
    """List all workflows grouped by category."""
    from workflows import get_workflows_by_category, WORKFLOWS
    return {
        "workflows": get_workflows_by_category(),
        "total": len(WORKFLOWS),
    }


@router.post("/workflows/run")
async def run_workflow(
    body: WorkflowRunRequest,
    user: dict = Depends(_get_auth()),
):
    """Trigger a named workflow — creates a plan and starts execution."""
    from workflows import get_workflow, workflow_to_plan_goal, WORKFLOWS

    wf = get_workflow(body.workflow_key)
    if not wf:
        raise HTTPException(status_code=404, detail=f"Workflow '{body.workflow_key}' not found")

    goal = workflow_to_plan_goal(body.workflow_key, body.context or "")
    if not goal:
        raise HTTPException(status_code=400, detail="Could not generate goal for workflow")

    return {
        "success": False,
        "requires_workspace_job": True,
        "workflow": wf["name"],
        "goal": goal,
        "message": "Start this workflow from the workspace so it uses the single build runtime.",
    }
