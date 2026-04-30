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
        from ....server import get_current_user        return get_current_user
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
    import asyncio

    wf = get_workflow(body.workflow_key)
    if not wf:
        raise HTTPException(status_code=404, detail=f"Workflow '{body.workflow_key}' not found")

    goal = workflow_to_plan_goal(body.workflow_key, body.context or "")
    if not goal:
        raise HTTPException(status_code=400, detail="Could not generate goal for workflow")

    # Trigger execution via unified runtime engine.
    try:
        import uuid
        from ....services.runtime.runtime_engine import runtime_engine
        job_id = str(uuid.uuid4())
        response = await runtime_engine.execute_with_control(
            task_id=job_id,
            user_id=user.get("id", "anonymous"),
            request=goal,
            conversation_id=f"workflow-{body.workflow_key}-{job_id}",
        )

        return {
            "success": True,
            "job_id": response.get("task_id") or job_id,
            "workflow": wf["name"],
            "goal": goal[:200],
            "stream_url": f"/api/runtime/tasks/{response.get('task_id')}",
        }

    except Exception as e:
        logger.exception("workflow run error: %s", e)
        # Fallback: just return the goal for the frontend to submit normally
        return {
            "success": False,
            "fallback": True,
            "goal": goal,
            "workflow": wf["name"],
            "error": str(e),
        }
