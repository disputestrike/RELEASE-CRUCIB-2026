from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api", tags=["compat"])


def _get_auth():
    from deps import get_current_user

    return get_current_user


def _get_db():
    import server

    return server.db


class AIChatBody(BaseModel):
    message: str = ""
    model: str = "auto"
    session_id: str | None = None


class ValidateAndFixCompatBody(BaseModel):
    code: str = ""
    language: str = "javascript"


class AgentRunBody(BaseModel):
    prompt: str | None = None
    code: str | None = None
    language: str | None = None
    url: str | None = None
    rows: list[Dict[str, Any]] = Field(default_factory=list)


# CF33 — Removed compat /ai/chat stub that was masking the real
# routes/ai.py implementation and returning "Compat reply: ..." to users.
# The real endpoint lives at routes/ai.py line ~86 and talks to LLM providers.


@router.post("/ai/validate-and-fix")
async def validate_and_fix_compat(
    data: ValidateAndFixCompatBody, _user: dict = Depends(_get_auth())
):
    return {"fixed_code": data.code or "", "valid": True, "language": data.language}


@router.get("/agents")
async def list_agents_compat():
    agents = [
        {"id": "planner", "name": "Planner", "category": "core"},
        {"id": "architect", "name": "Architect", "category": "core"},
        {"id": "frontend", "name": "Frontend", "category": "build"},
        {"id": "backend", "name": "Backend", "category": "build"},
        {"id": "validator", "name": "Validator", "category": "quality"},
    ]
    return {"agents": agents}


@router.get("/agents/templates")
async def list_agent_templates_compat():
    return {
        "templates": [
            {"id": "saas", "name": "SaaS MVP"},
            {"id": "landing", "name": "Landing Page"},
        ]
    }


@router.post("/agents/run/{agent_name}")
async def run_agent_compat(
    agent_name: str, body: AgentRunBody, _user: dict = Depends(_get_auth())
):
    return {
        "ok": True,
        "agent": agent_name,
        "result": f"compat run for {agent_name}",
        "input_echo": body.model_dump(),
    }


@router.get("/agents/run/memory-list")
async def memory_list_compat(_user: dict = Depends(_get_auth())):
    return {"items": []}


@router.get("/agents/run/automation-list")
async def automation_list_compat(_user: dict = Depends(_get_auth())):
    return {"items": []}


@router.get("/exports")
async def list_exports_compat(_user: dict = Depends(_get_auth())):
    return {"exports": []}


@router.post("/exports")
async def create_export_compat(
    payload: Dict[str, Any], _user: dict = Depends(_get_auth())
):
    project_id = (payload or {}).get("project_id")
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id required")
    return {"ok": True, "project_id": project_id, "format": (payload or {}).get("format", "zip")}


@router.post("/projects/from-template")
async def create_project_from_template_compat(
    payload: Dict[str, Any], user: dict = Depends(_get_auth())
):
    template_id = (payload or {}).get("template_id")
    if not template_id:
        raise HTTPException(status_code=400, detail="template_id required")
    db = _get_db()
    project = {
        "id": f"tmpl-{template_id}-{user.get('id', 'user')}",
        "name": f"Template: {template_id}",
        "template_id": template_id,
        "user_id": user.get("id"),
        "status": "imported",
    }
    if db is not None:
        try:
            await db.projects.insert_one(project)
        except Exception:
            pass
    return {"project": project}


@router.post("/stripe/create-checkout-session")
async def create_checkout_session_compat(
    payload: Dict[str, Any], _user: dict = Depends(_get_auth())
):
    bundle = (payload or {}).get("bundle")
    if bundle not in {"builder", "pro", "scale", "teams"}:
        raise HTTPException(status_code=400, detail="Invalid bundle")
    return {
        "id": f"cs_test_{bundle}",
        "url": f"https://checkout.stripe.com/c/pay/{bundle}",
    }


@router.post("/build/from-reference")
async def build_from_reference_compat(payload: Dict[str, Any]):
    url = str((payload or {}).get("url") or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="url required")
    return {"ok": True, "source_url": url, "plan": "compat-reference-build"}
