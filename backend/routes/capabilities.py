from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends
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
    """Safe computer-use action contract. Execution remains disabled until a governed runner is attached."""
    return {
        "execution_status": "disabled",
        "note": "Action queue contract only; real computer-use execution is not live.",
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
    """Validate see/click/type-style actions without executing them."""
    known = {row["action"]: row for row in list_computer_use_actions()}
    queue = []
    blockers = []
    for idx, action in enumerate(body.actions):
        name = str(action.get("action") or "").strip().lower()
        contract = known.get(name)
        status = contract["status"] if contract else "disabled"
        item = {
            "index": idx,
            "action": name or "unknown",
            "status": status,
            "execution_status": "not_executed",
            "audit_required": contract.get("audit_fields", []) if contract else ["action_id", "timestamp", "status", "error"],
        }
        queue.append(item)
        blockers.append({"index": idx, "action": item["action"], "reason": "computer_use_execution_disabled"})
    return {
        "execution_status": "disabled",
        "can_execute_now": False,
        "queue": queue,
        "blockers": blockers,
    }


@router.post("/assets/requests/validate")
async def validate_asset_request(body: AssetRequestValidateBody, user: dict = Depends(_get_optional_user())):
    """Validate an asset generation request without calling a provider or fabricating an image."""
    providers = {p["name"]: p for p in list_asset_providers()}
    provider = providers.get(body.provider or "together_ai") or next(iter(providers.values()))
    status = provider["status"]
    return {
        "execution_status": "validated_not_executed",
        "can_generate_now": status == "available",
        "provider": provider,
        "request": {
            "prompt": body.prompt,
            "asset_type": body.asset_type,
            "metadata": body.metadata,
        },
        "artifact_contract": {
            "storage_scope": ["job", "project", "artifact"],
            "metadata_fields": ["provider", "prompt", "asset_type", "mime_type", "size_bytes", "created_at"],
        },
    }
