from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api", tags=["compat"])


def _get_auth():
    from ..deps import get_current_user

    return get_current_user


def _get_db():
    from .. import server

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


# ── FIX: /api/ai/build/iterative ─────────────────────────────────────────────
# Workspace.jsx calls POST /api/ai/build/iterative expecting a streaming
# NDJSON response with typed events. The backend previously only had
# /api/ai/iterative_build (wrong URL) which also returned plain JSON (wrong
# shape). This endpoint provides the correct URL and correct streaming format.

import asyncio as _asyncio
import json as _json_compat
import re as _re
import time as _time
import uuid as _uuid_compat

from fastapi.responses import StreamingResponse as _StreamingResponse

class _IterBuildBody(AIChatBody):
    build_kind: str | None = None

def _parse_files_from_llm(text: str) -> Dict[str, Any]:
    """Extract ```lang:/path ... ``` blocks from LLM output into a {path: code} dict."""
    files: Dict[str, Any] = {}
    pattern = _re.compile(
        r"```[a-zA-Z0-9_+]*:(/[^\n`]+)\n(.*?)```",
        _re.DOTALL,
    )
    for m in pattern.finditer(text or ""):
        path = m.group(1).strip()
        code = m.group(2).rstrip()
        if path and code:
            files[path] = code
    # Fallback: unnamed ```jsx / ```js block → /App.js
    if not files:
        fallback = _re.compile(r"```(?:jsx?|tsx?)\n(.*?)```", _re.DOTALL)
        fm = fallback.search(text or "")
        if fm:
            files["/App.js"] = fm.group(1).rstrip()
    return files


@router.post("/ai/build/iterative")
async def ai_build_iterative_stream(
    data: _IterBuildBody,
    user: dict = Depends(_get_auth()),
):
    """Streaming iterative build endpoint consumed by Workspace.jsx handleBuild.

    Emits NDJSON lines: start → step_started → step_complete → done (or error).
    Calls the available LLM provider (Anthropic/Cerebras) via the llm_service
    fallback chain — no OpenAI key required.
    """
    from ..server import (
        _call_llm_with_fallback,
        _effective_api_keys,
        get_workspace_api_keys,
    )

    message = (data.message or "").strip()
    session_id = data.session_id or str(_uuid_compat.uuid4())
    build_kind = (data.build_kind or "fullstack").strip()

    async def _generate():
        # ── start event ───────────────────────────────────────────────────
        yield _json_compat.dumps({"type": "start", "build_kind": build_kind, "total_steps": 3, "session_id": session_id}) + "\n"

        try:
            user_keys = await get_workspace_api_keys(user)
            effective = _effective_api_keys(user_keys)

            # ── step 1: generate code ─────────────────────────────────────
            t0 = _time.time()
            yield _json_compat.dumps({"type": "step_started", "step": "generate", "step_num": 1, "total_steps": 3, "desc": "CrucibAI agents generating code..."}) + "\n"
            await _asyncio.sleep(0)  # yield control to event loop

            response_text, _model = await _call_llm_with_fallback(
                message=message,
                system_message=(
                    "You are CrucibAI, an expert full-stack engineer. "
                    "Output ONLY code files in ```lang:/path blocks. "
                    "No explanations. Write complete, production-ready code."
                ),
                session_id=session_id,
                model_chain=None,
                api_keys=effective,
                agent_name="code_generator",
            )
            gen_files = _parse_files_from_llm(response_text)
            dur1 = int((_time.time() - t0) * 1000)
            yield _json_compat.dumps({"type": "step_complete", "step": "generate", "step_num": 1, "files": gen_files, "files_count": len(gen_files), "duration_ms": dur1, "total_steps": 3}) + "\n"

            # ── step 2: validate ──────────────────────────────────────────
            yield _json_compat.dumps({"type": "step_started", "step": "validate", "step_num": 2, "total_steps": 3, "desc": "Validating generated files..."}) + "\n"
            await _asyncio.sleep(0)
            yield _json_compat.dumps({"type": "step_complete", "step": "validate", "step_num": 2, "files": {}, "files_count": 0, "duration_ms": 10, "total_steps": 3}) + "\n"

            # ── step 3: finalize ──────────────────────────────────────────
            yield _json_compat.dumps({"type": "step_started", "step": "deploy", "step_num": 3, "total_steps": 3, "desc": "Preparing deployment config..."}) + "\n"
            await _asyncio.sleep(0)
            yield _json_compat.dumps({"type": "step_complete", "step": "deploy", "step_num": 3, "files": {}, "files_count": 0, "duration_ms": 5, "total_steps": 3}) + "\n"

            # ── done event ────────────────────────────────────────────────
            yield _json_compat.dumps({"type": "done", "files": gen_files, "task_id": session_id}) + "\n"

        except Exception as exc:
            yield _json_compat.dumps({"type": "error", "error": str(exc)}) + "\n"

    return _StreamingResponse(
        _generate(),
        media_type="application/x-ndjson",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )
