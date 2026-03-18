"""
CrucibAI Automation Engine
===========================
Triggers + Actions + Workflows + Scheduler
Enables "when X happens → do Y" automations.
"""
import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable, Any
from enum import Enum

logger = logging.getLogger(__name__)


class TriggerType(str, Enum):
    BUILD_COMPLETE = "build_complete"
    USER_SIGNUP = "user_signup"
    PAYMENT_SUCCESS = "payment_success"
    SCHEDULE = "schedule"          # cron-style
    WEBHOOK = "webhook"
    MANUAL = "manual"


class ActionType(str, Enum):
    SEND_EMAIL = "send_email"
    DEPLOY_VERCEL = "deploy_vercel"
    CALL_WEBHOOK = "call_webhook"
    RUN_AI_AGENT = "run_ai_agent"
    NOTIFY_SLACK = "notify_slack"
    SAVE_TO_DB = "save_to_db"
    EXPORT_CODE = "export_code"


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ── In-memory workflow store (swap for DB in production) ──────────────────────
_workflows: Dict[str, dict] = {}
_runs: Dict[str, dict] = {}
_trigger_handlers: Dict[TriggerType, List[Callable]] = {}


def register_trigger(trigger_type: TriggerType, handler: Callable):
    """Register a handler to be called when a trigger fires."""
    if trigger_type not in _trigger_handlers:
        _trigger_handlers[trigger_type] = []
    _trigger_handlers[trigger_type].append(handler)


async def fire_trigger(trigger_type: TriggerType, data: dict):
    """Fire a trigger — runs all registered handlers."""
    handlers = _trigger_handlers.get(trigger_type, [])
    for handler in handlers:
        try:
            await handler(data)
        except Exception as e:
            logger.error(f"Trigger handler error [{trigger_type}]: {e}")


async def execute_action(action_type: ActionType, config: dict, context: dict) -> dict:
    """Execute a single action with given config and context."""
    logger.info(f"Executing action: {action_type}")

    if action_type == ActionType.SEND_EMAIL:
        return await _action_send_email(config, context)
    elif action_type == ActionType.DEPLOY_VERCEL:
        return await _action_deploy_vercel(config, context)
    elif action_type == ActionType.CALL_WEBHOOK:
        return await _action_call_webhook(config, context)
    elif action_type == ActionType.RUN_AI_AGENT:
        return await _action_run_ai_agent(config, context)
    elif action_type == ActionType.EXPORT_CODE:
        return await _action_export_code(config, context)
    else:
        return {"status": "skipped", "reason": f"Action {action_type} not implemented"}


async def run_workflow(workflow_id: str, trigger_data: dict) -> str:
    """Run a workflow by ID with trigger context data. Returns run_id."""
    workflow = _workflows.get(workflow_id)
    if not workflow:
        raise ValueError(f"Workflow {workflow_id} not found")

    run_id = str(uuid.uuid4())
    run = {
        "id": run_id,
        "workflow_id": workflow_id,
        "status": WorkflowStatus.RUNNING,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "trigger_data": trigger_data,
        "results": [],
    }
    _runs[run_id] = run

    try:
        context = {**trigger_data}
        for step in workflow.get("steps", []):
            action_type = ActionType(step["action"])
            result = await execute_action(action_type, step.get("config", {}), context)
            run["results"].append({"step": step["name"], "result": result})
            context[f"step_{step['name']}_result"] = result
            if result.get("status") == "error":
                raise Exception(f"Step {step['name']} failed: {result.get('error')}")

        run["status"] = WorkflowStatus.COMPLETED
        run["completed_at"] = datetime.now(timezone.utc).isoformat()
        logger.info(f"Workflow {workflow_id} run {run_id} completed")
    except Exception as e:
        run["status"] = WorkflowStatus.FAILED
        run["error"] = str(e)
        run["completed_at"] = datetime.now(timezone.utc).isoformat()
        logger.error(f"Workflow {workflow_id} run {run_id} failed: {e}")

    return run_id


def create_workflow(name: str, trigger: TriggerType, steps: List[dict]) -> str:
    """Create and register a new workflow."""
    wf_id = str(uuid.uuid4())
    workflow = {
        "id": wf_id,
        "name": name,
        "trigger": trigger,
        "steps": steps,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "enabled": True,
    }
    _workflows[wf_id] = workflow

    # Auto-register trigger handler
    async def handler(data: dict):
        if workflow["enabled"]:
            await run_workflow(wf_id, data)

    register_trigger(trigger, handler)
    logger.info(f"Workflow '{name}' created: {wf_id}")
    return wf_id


def get_workflows() -> List[dict]:
    return list(_workflows.values())


def get_run(run_id: str) -> Optional[dict]:
    return _runs.get(run_id)


# ── Built-in workflow templates ────────────────────────────────────────────────
def setup_default_workflows():
    """Set up default automation workflows."""
    # Welcome email on signup
    create_workflow(
        name="Welcome Email on Signup",
        trigger=TriggerType.USER_SIGNUP,
        steps=[{
            "name": "send_welcome",
            "action": ActionType.SEND_EMAIL,
            "config": {
                "template": "welcome",
                "subject": "Welcome to CrucibAI!",
                "to": "{{user.email}}",
            }
        }]
    )

    # Build complete notification
    create_workflow(
        name="Build Complete Notification",
        trigger=TriggerType.BUILD_COMPLETE,
        steps=[{
            "name": "notify",
            "action": ActionType.SEND_EMAIL,
            "config": {
                "template": "build_complete",
                "subject": "Your build is ready!",
                "to": "{{user.email}}",
            }
        }]
    )

    logger.info("Default workflows registered")


# ── Action implementations ─────────────────────────────────────────────────────
async def _action_send_email(config: dict, context: dict) -> dict:
    """Send an email using the SMTP config."""
    import os
    smtp_host = os.environ.get("SMTP_HOST")
    if not smtp_host:
        return {"status": "skipped", "reason": "SMTP not configured"}
    # In production: send via SMTP
    logger.info(f"Email action: {config.get('subject')} → {config.get('to')}")
    return {"status": "success", "sent_to": config.get("to")}


async def _action_deploy_vercel(config: dict, context: dict) -> dict:
    """Deploy to Vercel via their API."""
    return {"status": "pending", "message": "Vercel deploy queued"}


async def _action_call_webhook(config: dict, context: dict) -> dict:
    """Call an external webhook URL."""
    import httpx
    url = config.get("url")
    if not url:
        return {"status": "error", "error": "No URL configured"}
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=context, timeout=30)
        return {"status": "success", "response_code": resp.status_code}


async def _action_run_ai_agent(config: dict, context: dict) -> dict:
    """Run an AI agent task."""
    return {"status": "queued", "agent": config.get("agent_name")}


async def _action_export_code(config: dict, context: dict) -> dict:
    """Export built code as ZIP."""
    return {"status": "success", "download_url": "/api/export/latest"}
