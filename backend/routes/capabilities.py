from __future__ import annotations

import logging
import base64
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..services.product_capability_registry import (
    build_capability_registry,
    list_asset_providers,
    list_computer_use_actions,
    list_preview_types,
    list_workflow_templates,
    validate_workflow_definition,
)

router = APIRouter(prefix="/api/capabilities", tags=["capabilities"])
logger = logging.getLogger(__name__)


def _get_optional_user():
    from ..server import get_optional_user

    return get_optional_user


class WorkflowValidateRequest(BaseModel):
    name: str = "Untitled workflow"
    steps: List[Dict[str, Any]] = Field(default_factory=list)
    schedule: Dict[str, Any] = Field(default_factory=dict)


class ComputerUseQueueRequest(BaseModel):
    actions: List[Dict[str, Any]] = Field(default_factory=list)


class AssetRequestValidateBody(BaseModel):
    prompt: str
    asset_type: str = "image"
    provider: str | None = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AssetRequestGenerateBody(AssetRequestValidateBody):
    persist: bool = True


class ComputerUseRunRequest(BaseModel):
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    policy: Dict[str, Any] = Field(default_factory=dict)


class ScheduledTaskValidateBody(BaseModel):
    name: str = "Untitled scheduled task"
    owner_id: str | None = None
    schedule: Dict[str, Any] = Field(default_factory=dict)
    task: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _actor_id(user: dict | None) -> str:
    if isinstance(user, dict):
        return str(user.get("id") or user.get("user_id") or "anonymous")
    return "anonymous"


def _get_db_instance():
    try:
        from ..deps import get_db

        return get_db()
    except Exception:
        return None


async def _try_insert(collection_name: str, document: Dict[str, Any]) -> bool:
    db = _get_db_instance()
    if db is None:
        return False
    try:
        await getattr(db, collection_name).insert_one(document)
        return True
    except Exception as exc:  # pragma: no cover - best-effort audit persistence
        logger.info("capability foundation persistence skipped for %s: %s", collection_name, exc)
        return False


@router.get("/registry")
async def capability_registry(user: dict = Depends(_get_optional_user())):
    """Machine-readable honest registry of skills, tools, connectors, and foundations."""
    return build_capability_registry()


@router.get("/preview-types")
async def preview_types(user: dict = Depends(_get_optional_user())):
    """Rich preview support map with honest unsupported/config-required states."""
    return {"preview_types": list_preview_types()}


@router.get("/asset-providers")
async def asset_providers(user: dict = Depends(_get_optional_user())):
    """Asset generation provider readiness; does not generate or return fake images."""
    return {"providers": list_asset_providers()}


@router.get("/computer-use/actions")
async def computer_use_actions(user: dict = Depends(_get_optional_user())):
    """Safe computer-use action catalog. Execution stays disabled until worker + policy gates go live."""
    return {
        "execution_status": "disabled",
        "note": "Contract lists allowable actions for future governed execution; sandbox execution remains disabled.",
        "actions": list_computer_use_actions(),
    }


@router.get("/workflow-templates")
async def workflow_templates(user: dict = Depends(_get_optional_user())):
    """Workflow templates, including disabled/requires_config templates such as Chief-of-Staff."""
    return {"templates": list_workflow_templates()}


@router.post("/workflows/validate")
async def validate_workflow(body: WorkflowValidateRequest, user: dict = Depends(_get_optional_user())):
    """Validate a future daily-work automation workflow without executing it."""
    result = validate_workflow_definition({"name": body.name, "steps": body.steps, "schedule": body.schedule})
    return {
        "name": body.name,
        "execution_status": "validated_not_executed",
        "schedule": body.schedule,
        **result,
    }


@router.post("/computer-use/queue/validate")
async def validate_computer_use_queue(body: ComputerUseQueueRequest, user: dict = Depends(_get_optional_user())):
    """Validate see/click/type-style actions without executing them (foundation: execution gated off)."""
    known = {row["action"]: row for row in list_computer_use_actions()}
    queue_id = f"cuq_{uuid.uuid4().hex}"
    now = _now_iso()
    actor = _actor_id(user)
    queue = []
    blockers: List[Dict[str, Any]] = []
    for idx, action in enumerate(body.actions):
        name = str(action.get("action") or "").strip().lower()
        contract = known.get(name)
        status = contract["status"] if contract else "disabled"
        action_id = f"cua_{uuid.uuid4().hex}"
        item = {
            "id": action_id,
            "queue_id": queue_id,
            "index": idx,
            "action": name or "unknown",
            "status": status,
            "execution_status": "not_executed",
            "target": action.get("target"),
            "selector": action.get("selector"),
            "created_at": now,
            "audit_required": contract.get("audit_fields", []) if contract else ["action_id", "timestamp", "status", "error"],
        }
        queue.append(item)
        if not contract:
            blockers.append({"index": idx, "action": item["action"], "reason": "unknown_action"})
        else:
            blockers.append({"index": idx, "reason": "computer_use_execution_disabled"})
    task_doc = {
        "id": queue_id,
        "user_id": actor,
        "status": "validated",
        "execution_status": "disabled",
        "can_execute_now": False,
        "actions": queue,
        "blockers": blockers,
        "created_at": now,
        "updated_at": now,
        "audit_log": [
            {
                "event": "computer_use_queue_validated",
                "timestamp": now,
                "status": "disabled",
            }
        ],
    }
    persisted_task = await _try_insert("computer_use_tasks", task_doc)
    persisted_actions = 0
    for item in queue:
        action_doc = {
            **item,
            "id": item["id"],
            "user_id": actor,
            "status": item["status"],
            "error": None if item["status"] == "available" else "computer_use_action_not_available",
        }
        if await _try_insert("computer_use_actions", action_doc):
            persisted_actions += 1
    persisted_audit = await _try_insert(
        "audit_log",
        {
            "id": f"audit_{uuid.uuid4().hex}",
            "user_id": actor,
            "event": "computer_use_queue_validated",
            "resource_type": "computer_use_task",
            "resource_id": queue_id,
            "status": "validated",
            "created_at": now,
            "metadata": {"action_count": len(queue), "executed": False, "can_execute_now": False},
        },
    )
    return {
        "queue_id": queue_id,
        "execution_status": "disabled",
        "can_execute_now": False,
        "queue": queue,
        "blockers": blockers,
        "persisted": {
            "computer_use_tasks": persisted_task,
            "computer_use_actions": persisted_actions,
            "audit_log": persisted_audit,
        },
    }


def _safe_url(url: str) -> bool:
    parsed = urlparse(url or "")
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower()
    if not host or host in {"localhost", "127.0.0.1", "0.0.0.0"}:
        return False
    return True


@router.post("/computer-use/queue/run")
async def run_computer_use_queue(body: ComputerUseRunRequest, user: dict = Depends(_get_optional_user())):
    """Run a governed browser action queue with audit persistence."""
    if not body.actions:
        raise HTTPException(status_code=400, detail="actions are required")
    if len(body.actions) > int(body.policy.get("max_actions") or 12):
        raise HTTPException(status_code=400, detail="too many actions for governed runner")
    allow_interaction = bool(body.policy.get("allow_interaction"))
    queue_id = f"cuq_{uuid.uuid4().hex}"
    actor = _actor_id(user)
    now = _now_iso()
    events: List[Dict[str, Any]] = []
    screenshots: List[Dict[str, Any]] = []
    current_url = ""
    try:
        from playwright.async_api import async_playwright
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Playwright unavailable: {str(exc)[:180]}")

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = await browser.new_context(viewport={"width": 1280, "height": 900})
            page = await context.new_page()
            try:
                for idx, action in enumerate(body.actions):
                    name = str(action.get("action") or "").strip().lower()
                    target = str(action.get("target") or action.get("url") or "").strip()
                    item = {"index": idx, "action": name, "target": target, "status": "running", "timestamp": _now_iso()}
                    try:
                        if name == "navigate":
                            if not _safe_url(target):
                                raise ValueError("navigate target must be a public http(s) URL")
                            await page.goto(target, wait_until="domcontentloaded", timeout=15000)
                            current_url = page.url
                            item.update({"status": "success", "url": current_url})
                        elif name in {"see", "screenshot"}:
                            shot = await page.screenshot(full_page=False)
                            ref = f"data:image/png;base64,{base64.b64encode(shot).decode('ascii')}"
                            screenshots.append({"index": idx, "mime_type": "image/png", "data_url": ref})
                            item.update({"status": "success", "screenshot_ref": f"screenshot:{idx}"})
                        elif name == "wait":
                            ms = int(action.get("milliseconds") or 500)
                            await page.wait_for_timeout(max(0, min(ms, 5000)))
                            item.update({"status": "success", "milliseconds": ms})
                        elif name == "click":
                            if not allow_interaction:
                                raise ValueError("click requires policy.allow_interaction=true")
                            selector = action.get("selector") or action.get("selector_or_coordinates")
                            if not selector:
                                raise ValueError("selector is required")
                            await page.click(str(selector), timeout=5000)
                            item.update({"status": "success", "selector": selector})
                        elif name == "type":
                            if not allow_interaction:
                                raise ValueError("type requires policy.allow_interaction=true")
                            selector = str(action.get("selector") or action.get("target_selector") or "")
                            text = str(action.get("text") or "")
                            if not selector or not text:
                                raise ValueError("selector and text are required")
                            if any(word in selector.lower() for word in ["password", "secret", "token", "card"]):
                                raise ValueError("refusing to type into sensitive field selector")
                            await page.fill(selector, text[:500], timeout=5000)
                            item.update({"status": "success", "selector": selector, "redacted_text_summary": f"{len(text)} chars"})
                        else:
                            raise ValueError(f"unsupported action: {name}")
                    except Exception as exc:
                        item.update({"status": "failed", "error": str(exc)[:300]})
                    events.append(item)
            finally:
                await context.close()
                await browser.close()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Computer-use runner unavailable in this environment: {str(exc)[:220]}")

    success = all(e.get("status") == "success" for e in events)
    task_doc = {
        "id": queue_id,
        "user_id": actor,
        "status": "success" if success else "failed",
        "execution_status": "completed",
        "actions": events,
        "screenshot_count": len(screenshots),
        "current_url": current_url,
        "created_at": now,
        "updated_at": _now_iso(),
    }
    persisted_task = await _try_insert("computer_use_tasks", task_doc)
    for event in events:
        await _try_insert("computer_use_actions", {"id": f"cua_{uuid.uuid4().hex}", "queue_id": queue_id, "user_id": actor, **event})
    await _try_insert(
        "audit_log",
        {
            "id": f"audit_{uuid.uuid4().hex}",
            "user_id": actor,
            "event": "computer_use_queue_ran",
            "resource_type": "computer_use_task",
            "resource_id": queue_id,
            "status": task_doc["status"],
            "created_at": _now_iso(),
            "metadata": {"action_count": len(events), "screenshot_count": len(screenshots)},
        },
    )
    return {
        "queue_id": queue_id,
        "execution_status": "completed",
        "status": task_doc["status"],
        "actions": events,
        "screenshots": screenshots[:3],
        "persisted": {"computer_use_tasks": persisted_task},
    }


@router.post("/assets/requests/validate")
async def validate_asset_request(body: AssetRequestValidateBody, user: dict = Depends(_get_optional_user())):
    """Validate an asset generation request without calling a provider or fabricating an image."""
    providers = {p["name"]: p for p in list_asset_providers()}
    provider = providers.get(body.provider or "together_ai") or next(iter(providers.values()))
    status = provider["status"]
    request_id = f"asset_req_{uuid.uuid4().hex}"
    now = _now_iso()
    actor = _actor_id(user)
    request_payload = {
        "prompt": body.prompt,
        "asset_type": body.asset_type,
        "metadata": body.metadata,
    }
    request_doc = {
        "id": request_id,
        "user_id": actor,
        "status": "validated_not_executed",
        "execution_status": "validated_not_executed",
        "can_generate_now": status == "available",
        "provider": provider,
        "request": request_payload,
        "created_at": now,
        "updated_at": now,
        "artifact": None,
    }
    persisted_request = await _try_insert("asset_generation_requests", request_doc)
    persisted_audit = await _try_insert(
        "audit_log",
        {
            "id": f"audit_{uuid.uuid4().hex}",
            "user_id": actor,
            "event": "asset_generation_request_validated",
            "resource_type": "asset_generation_request",
            "resource_id": request_id,
            "status": "validated_not_executed",
            "created_at": now,
            "metadata": {"provider": provider["name"], "asset_type": body.asset_type, "generated": False},
        },
    )
    return {
        "request_id": request_id,
        "execution_status": "validated_not_executed",
        "can_generate_now": status == "available",
        "provider": provider,
        "request": request_payload,
        "artifact_contract": {
            "storage_scope": ["job", "project", "artifact"],
            "metadata_fields": ["provider", "prompt", "asset_type", "mime_type", "size_bytes", "created_at"],
        },
        "artifact": None,
        "persisted": {
            "asset_generation_requests": persisted_request,
            "audit_log": persisted_audit,
        },
    }


@router.post("/assets/requests/generate")
async def generate_asset_request(body: AssetRequestGenerateBody, user: dict = Depends(_get_optional_user())):
    """Generate an image through a configured provider and persist artifact metadata."""
    providers = {p["name"]: p for p in list_asset_providers()}
    provider = providers.get(body.provider or "together_ai") or next(iter(providers.values()))
    if provider["status"] != "available":
        raise HTTPException(
            status_code=503,
            detail={
                "error": "asset_provider_requires_config",
                "provider": provider["name"],
                "required_config": provider.get("required_config", []),
            },
        )
    request_id = f"asset_req_{uuid.uuid4().hex}"
    actor = _actor_id(user)
    now = _now_iso()
    image_ref = None
    if provider["name"] == "together_ai":
        from ..agents.image_generator import generate_image

        image_ref = await generate_image(body.prompt)
    else:
        raise HTTPException(status_code=501, detail=f"Provider {provider['name']} is not implemented")
    if not image_ref:
        raise HTTPException(status_code=502, detail="Image provider did not return an artifact")
    artifact = {
        "id": f"asset_{uuid.uuid4().hex}",
        "provider": provider["name"],
        "asset_type": body.asset_type,
        "prompt": body.prompt[:2000],
        "url": image_ref if image_ref.startswith("http") else None,
        "data_url": image_ref if image_ref.startswith("data:") else None,
        "mime_type": "image/png",
        "created_at": now,
        "metadata": body.metadata,
    }
    request_doc = {
        "id": request_id,
        "user_id": actor,
        "status": "generated",
        "execution_status": "generated",
        "provider": provider,
        "request": {"prompt": body.prompt, "asset_type": body.asset_type, "metadata": body.metadata},
        "artifact": artifact,
        "created_at": now,
        "updated_at": now,
    }
    persisted_request = await _try_insert("asset_generation_requests", request_doc) if body.persist else False
    await _try_insert(
        "audit_log",
        {
            "id": f"audit_{uuid.uuid4().hex}",
            "user_id": actor,
            "event": "asset_generation_request_generated",
            "resource_type": "asset_generation_request",
            "resource_id": request_id,
            "status": "generated",
            "created_at": now,
            "metadata": {"provider": provider["name"], "asset_type": body.asset_type},
        },
    )
    return {
        "request_id": request_id,
        "execution_status": "generated",
        "provider": provider,
        "artifact": artifact,
        "persisted": {"asset_generation_requests": persisted_request},
    }


@router.post("/scheduled-tasks/validate")
async def validate_scheduled_task(body: ScheduledTaskValidateBody, user: dict = Depends(_get_optional_user())):
    """Persist a future scheduled-task contract without starting a scheduler or fake run."""
    task_id = f"sched_{uuid.uuid4().hex}"
    now = _now_iso()
    actor = body.owner_id or _actor_id(user)
    schedule = dict(body.schedule or {})
    requested_enabled = bool(schedule.get("enabled"))
    schedule_type = str(schedule.get("type") or "manual").strip().lower()
    blockers = ["validation_endpoint_does_not_start_scheduler"]
    if requested_enabled:
        blockers.append("worker_must_enable_task_after_policy_check")
    if schedule_type == "cron" and not schedule.get("cron_expression"):
        blockers.append("cron_expression_required")
    if schedule_type == "run_at" and not schedule.get("run_at"):
        blockers.append("run_at_required")
    task_doc = {
        "id": task_id,
        "user_id": actor,
        "name": body.name,
        "status": "disabled",
        "execution_status": "validated_not_scheduled",
        "requested_enabled": requested_enabled,
        "enabled": False,
        "schedule": {
            "type": schedule_type,
            "cron_expression": schedule.get("cron_expression"),
            "run_at": schedule.get("run_at"),
            "timezone": schedule.get("timezone") or "UTC",
            "next_run_time": None,
            "last_run_result": None,
        },
        "task": body.task,
        "metadata": body.metadata,
        "blockers": blockers,
        "created_at": now,
        "updated_at": now,
    }
    persisted_task = await _try_insert("scheduled_tasks", task_doc)
    persisted_audit = await _try_insert(
        "audit_log",
        {
            "id": f"audit_{uuid.uuid4().hex}",
            "user_id": actor,
            "event": "scheduled_task_contract_validated",
            "resource_type": "scheduled_task",
            "resource_id": task_id,
            "status": "validated_not_scheduled",
            "created_at": now,
            "metadata": {"schedule_type": schedule_type, "enabled": False, "executed": False},
        },
    )
    return {
        "task_id": task_id,
        "execution_status": "validated_not_scheduled",
        "worker_required": True,
        "requested_enabled": requested_enabled,
        "enabled": False,
        "schedule": task_doc["schedule"],
        "blockers": blockers,
        "persisted": {
            "scheduled_tasks": persisted_task,
            "audit_log": persisted_audit,
        },
    }


# ── Stack Confidence Endpoint ──────────────────────────────────────────────


@router.get("/stacks")
async def list_supported_stacks(user: dict = Depends(_get_optional_user())):
    """Returns all supported stacks with confidence scores from the template registry."""
    try:
        from backend.agents.templates import list_templates

        templates = list_templates()
        return {
            "stacks": [
                {
                    "id": t["id"],
                    "language": t["language"],
                    "framework": t["framework"],
                    "confidence": t["confidence"],
                    "build_command": t.get("build_command", ""),
                    "run_command": t.get("run_command", ""),
                }
                for t in templates
            ],
            "total": len(templates),
        }
    except Exception as e:
        logger.warning("Failed to list supported stacks: %s", e)
        return {"stacks": [], "error": str(e), "total": 0}
