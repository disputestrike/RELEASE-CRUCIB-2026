"""Automation routes — create/list automations from builds."""
import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel
logger = logging.getLogger(__name__)
router = APIRouter()

def _get_auth():
    try:
        from server import get_current_user
        return get_current_user
    except Exception:
        from fastapi import Request
        async def noop(request: Request = None):
            return {"id": "anonymous"}
        return noop

class AutomationRequest(BaseModel):
    description: str
    schedule: str = ""
    webhook_url: str = ""

@router.post("/api/builds/{job_id}/automation")
async def create_automation(job_id: str, req: AutomationRequest, user: dict = Depends(_get_auth())):
    """Create an automation from a completed build."""
    try:
        from workflows import workflow_to_plan_goal, WORKFLOWS
        # Find closest matching workflow
        desc_lower = req.description.lower()
        matched = next(
            (k for k, w in WORKFLOWS.items()
             if any(word in desc_lower for word in w["name"].lower().split())),
            None
        )
        goal = workflow_to_plan_goal(matched, req.description) if matched else req.description
        return {
            "automationId": f"auto_{job_id[:8]}",
            "description": req.description,
            "workflowKey": matched,
            "goal": goal[:200],
            "status": "created",
            "schedule": req.schedule or "on_demand",
        }
    except Exception as e:
        logger.warning("create_automation: %s", e)
        return {"automationId": "", "status": "failed", "error": str(e)}
