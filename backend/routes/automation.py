from __future__ import annotations
import logging
from fastapi import APIRouter, Depends, HTTPException, Request

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["automation"])


def _get_auth():
    from server import get_current_user

    return get_current_user


# ==================== AUTOMATION ENGINE ====================


@router.get("/automation/workflows")
async def get_workflows(user: dict = Depends(_get_auth())):
    """List all automation workflows for this user."""
    try:
        from automation_engine import get_workflows

        workflows = get_workflows()
        return {"workflows": workflows}
    except Exception as e:
        return {"workflows": [], "error": str(e)}


@router.post("/automation/workflows")
async def create_automation_workflow(
    request: Request, user: dict = Depends(_get_auth())
):
    """Create a new automation workflow."""
    try:
        from automation_engine import create_workflow, TriggerType

        body = await request.json()
        wf_id = create_workflow(
            name=body.get("name", "New Workflow"),
            trigger=TriggerType(body.get("trigger", "manual")),
            steps=body.get("steps", []),
        )
        return {"workflow_id": wf_id, "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/automation/trigger/{trigger_type}")
async def fire_automation_trigger(
    trigger_type: str, request: Request, user: dict = Depends(_get_auth())
):
    """Manually fire a trigger (for testing)."""
    try:
        from automation_engine import fire_trigger, TriggerType

        data = await request.json()
        data["user"] = {"id": user["id"], "email": user.get("email", "")}
        await fire_trigger(TriggerType(trigger_type), data)
        return {"status": "fired", "trigger": trigger_type}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/automation/runs/{run_id}")
async def get_automation_run(run_id: str, user: dict = Depends(_get_auth())):
    """Get status of an automation run."""
    from automation_engine import get_run

    run = get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


# ==================== CLIENT ERROR LOGGING ====================


@router.post("/errors/log")
async def client_error_log(request: Request):
    """Accept client-side error reports (ErrorBoundary). No auth required; rate-limited by middleware. Sanitized and logged only."""
    try:
        body = await request.json()
        if isinstance(body, dict):
            message = str(body.get("message", ""))[:2000]
            stack = str(body.get("stack", ""))[:5000]
            url = str(body.get("url", ""))[:500]
            logger.warning(
                "Client error: %s | url=%s | stack=%s",
                message or "unknown",
                url or request.url.path,
                stack[:500] if stack else "",
            )
    except Exception:
        pass
    return {}
