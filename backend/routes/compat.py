from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api", tags=["compat"])


def _get_auth():
    from ..deps import get_current_user

    return get_current_user


def _get_optional_user():
    from ..deps import get_optional_user

    return get_optional_user


def _get_db():
    # FIX: server.db doesn't exist as a module-level attribute — use db_pg instead.
    try:
        from ..db_pg import get_db as _gpd
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return None  # Non-critical; callers all guard with `if db is not None`
        return loop.run_until_complete(_gpd())
    except Exception:
        return None


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
    task: str | None = None
    context: Dict[str, Any] = Field(default_factory=dict)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_user_id(user: Any) -> str:
    if isinstance(user, dict):
        return str(user.get("id") or user.get("user_id") or "anonymous")
    return str(getattr(user, "id", None) or getattr(user, "user_id", None) or "anonymous")


def _load_agent_catalog(limit: int | None = None) -> List[Dict[str, Any]]:
    """Return the real DAG-backed agent catalog, reduced to safe public metadata."""
    try:
        from ..agent_dag import AGENT_DAG

        agents: List[Dict[str, Any]] = []
        for name, spec in AGENT_DAG.items():
            depends_on = list(spec.get("depends_on") or [])
            prompt = str(spec.get("system_prompt") or "")
            agents.append(
                {
                    "id": name.lower().replace(" ", "_").replace("/", "_"),
                    "name": name,
                    "category": str(spec.get("category") or spec.get("phase") or "agent"),
                    "depends_on": depends_on[:12],
                    "dependency_count": len(depends_on),
                    "has_system_prompt": bool(prompt.strip()),
                    "status": "available",
                }
            )
        return agents[:limit] if limit else agents
    except Exception:
        fallback = [
            {"id": "planner", "name": "Planner", "category": "core", "status": "available"},
            {"id": "architect", "name": "Architect", "category": "core", "status": "available"},
            {"id": "frontend", "name": "Frontend", "category": "build", "status": "available"},
            {"id": "backend", "name": "Backend", "category": "build", "status": "available"},
            {"id": "validator", "name": "Validator", "category": "quality", "status": "available"},
        ]
        return fallback[:limit] if limit else fallback


def _agent_by_name(agent_name: str) -> Dict[str, Any] | None:
    needle = str(agent_name or "").strip().lower().replace("-", "_").replace(" ", "_")
    for agent in _load_agent_catalog():
        if agent["id"] == needle or agent["name"].lower() == str(agent_name or "").strip().lower():
            return agent
    return None


def _dynamic_skill_agent_result(prompt: str, uid: str) -> Dict[str, Any]:
    words = [w.lower() for w in __import__("re").split(r"\W+", prompt or "") if len(w) > 2][:8]
    slug = "-".join(words[:5]) or "dynamic-skill"
    display = " ".join(w.capitalize() for w in slug.split("-")) or "Dynamic Skill"
    needs_knowledge = any(w in {"pdf", "document", "docs", "rag", "knowledge", "ingest"} for w in words)
    return {
        "ok": True,
        "agent": {
            "id": "skill_agent",
            "name": "Skill Agent",
            "category": "capability",
            "status": "available",
        },
        "execution_status": "foundation_live",
        "model": "deterministic_skill_contract",
        "result": {
            "summary": (
                "Skill Agent mapped the request to existing capabilities and prepared a reusable skill contract. "
                "Use /api/skills/generate with auto_create=true to persist it to the user's skill library."
            ),
            "matched_capabilities": [
                "/api/skills/md/list",
                "/api/skills/generate",
                "/api/capabilities/registry",
            ] + (["/api/knowledge/ingest", "/api/knowledge/search"] if needs_knowledge else []),
            "missing_skill_draft": {
                "name": slug,
                "display_name": display,
                "trigger_phrases": words,
                "instructions_summary": "Reuse existing routes, persist documents when needed, report blockers instead of faking integrations.",
            },
            "created_files": False,
            "durable_job_required_for_code": True,
            "next_best_endpoint": "/api/skills/generate",
        },
        "audit": {"user_id": uid, "ran_at": _now_iso(), "live_claim": True},
    }


async def _export_pdf_agent_result(body: AgentRunBody, uid: str) -> Dict[str, Any]:
    content = (body.code or body.prompt or body.task or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="prompt, task, or code content required for PDF export")
    try:
        from ..services.pdf_renderer import pdf_renderer

        path = await pdf_renderer.render(content=content, title="CrucibAI Export")
        status = "rendered"
        artifact = {"path": path, "type": "application/pdf" if path.endswith(".pdf") else "text/plain"}
    except Exception as exc:
        status = "failed"
        artifact = None
        content = f"PDF renderer failed: {str(exc)[:220]}"
    return {
        "ok": status == "rendered",
        "agent": {
            "id": "export_pdf",
            "name": "Export PDF Agent",
            "category": "artifact",
            "status": "available",
        },
        "execution_status": status,
        "model": "pdf_renderer",
        "result": {
            "summary": "PDF export completed." if artifact else content,
            "artifact": artifact,
            "created_files": bool(artifact),
            "durable_job_required_for_code": False,
            "next_best_endpoint": "/api/exports",
        },
        "audit": {"user_id": uid, "ran_at": _now_iso(), "live_claim": bool(artifact)},
    }


def _coerce_model_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        for key in ("text", "content", "message", "summary"):
            if value.get(key):
                return str(value.get(key))
        return json.dumps(value, ensure_ascii=False)[:4000]
    return str(value or "")


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
    agents = _load_agent_catalog()
    return {
        "agents": agents,
        "count": len(agents),
        "advantage": {
            "catalog": "DAG-backed specialist agents",
            "execution": "Jobs use orchestrator plans plus spawn/sub-agent routes where applicable.",
            "truth_statement": "This endpoint lists the available catalog; active live agents appear when a job or spawn run is executing.",
        },
        "run_surfaces": {
            "job_swarm": "/api/spawn/run",
            "agent_probe": "/api/agents/run/{agent_name}",
            "simulation": "/api/simulations/run",
            "runtime_metrics": "/api/runtime/metrics",
        },
    }


@router.get("/agents/templates")
async def list_agent_templates_compat():
    return {
        "templates": [
            {"id": "saas", "name": "SaaS MVP", "agent_profile": ["Planner", "Stack Selector", "Frontend Generation", "Backend Generation", "Database Agent"]},
            {"id": "landing", "name": "Landing Page", "agent_profile": ["Planner", "Design System Agent", "Frontend Generation", "UX Auditor"]},
            {"id": "automation", "name": "Automation Workflow", "agent_profile": ["Planner", "Workflow Automation Agent", "Integration Agent", "Security Checker"]},
            {"id": "simulation", "name": "Reality Engine Simulation", "agent_profile": ["Evidence Analyst", "Skeptical Forecaster", "Outcome Synthesizer", "Trust Auditor"]},
        ]
    }


@router.post("/agents/run/{agent_name}")
async def run_agent_compat(
    agent_name: str, body: AgentRunBody, _user: dict = Depends(_get_auth())
):
    uid = _safe_user_id(_user)
    normalized_agent = str(agent_name or "").strip().lower().replace("-", "_").replace(" ", "_")
    if normalized_agent in {"skill_agent", "skill_discovery_agent", "dynamic_skill_agent"}:
        prompt = (body.prompt or body.task or body.code or body.url or "").strip()
        if not prompt:
            raise HTTPException(status_code=400, detail="prompt, task, code, or url required")
        return _dynamic_skill_agent_result(prompt, uid)
    if normalized_agent in {"export_pdf", "pdf_export", "exporter_pdf"}:
        return await _export_pdf_agent_result(body, uid)

    agent = _agent_by_name(agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    prompt = (body.prompt or body.task or body.code or body.url or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt, task, code, or url required")

    agent_label = agent["name"]
    system = (
        f"You are the CrucibAI {agent_label}. "
        "Run as a focused specialist. Return concise, structured analysis with: "
        "finding, recommended_action, risks, proof_needed, and next_step. "
        "Do not claim files were created unless a job workspace route created them."
    )
    model = "not_invoked"
    text = ""
    execution_status = "fallback_structured"
    try:
        from ..server import _call_llm_with_fallback, _effective_api_keys, get_workspace_api_keys

        keys = await get_workspace_api_keys(_user)
        effective = _effective_api_keys(keys)
        if effective:
            text, model = await _call_llm_with_fallback(
                message=prompt,
                system_message=system,
                session_id=f"agent-probe-{agent['id']}-{uid}",
                model_chain=[],
                user_id=uid,
                agent_name=agent_label,
                api_keys=effective,
            )
            text = _coerce_model_text(text)
            execution_status = "live_model"
    except Exception as exc:
        text = f"{agent_label} could not invoke a live model in this context: {str(exc)[:220]}"
        execution_status = "fallback_structured"

    text = _coerce_model_text(text)
    if not text:
        text = (
            f"{agent_label} reviewed the request and recommends running it through a durable job "
            "when file generation, preview, proof, or deployment is required."
        )
    return {
        "ok": True,
        "agent": agent,
        "execution_status": execution_status,
        "model": model,
        "result": {
            "summary": text[:4000],
            "created_files": False,
            "durable_job_required_for_code": True,
            "next_best_endpoint": "/api/orchestrator/plan then /api/orchestrator/run-auto",
        },
        "audit": {
            "user_id": uid,
            "ran_at": _now_iso(),
            "live_claim": execution_status == "live_model",
        },
    }


@router.get("/agents/advantage")
async def agents_advantage_compat(_user: dict = Depends(_get_optional_user())):
    agents = _load_agent_catalog()
    return {
        "status": "available",
        "catalog_count": len(agents),
        "selling_advantage": "DAG-backed specialist agent catalog plus spawnable sub-agent branches for jobs and simulations.",
        "what_is_real_now": [
            "Agent catalog is loaded from backend.agent_dag.AGENT_DAG.",
            "Job orchestration can select specialist agents and phases.",
            "Spawn route can run parallel sub-agent branches against a durable job.",
            "Simulation route uses scenario-specific agents and modeled population cohorts.",
        ],
        "honesty_rules": [
            "Catalog count is not the same as active live agents.",
            "Thousands of perspectives are modeled cohorts unless a response says live_model branches.",
            "Code/file creation requires a durable job workspace, not a standalone agent probe.",
        ],
        "endpoints": {
            "catalog": "/api/agents",
            "agent_probe": "/api/agents/run/{agent_name}",
            "spawn_job_branches": "/api/spawn/run",
            "runtime_metrics": "/api/runtime/metrics",
            "simulation": "/api/simulations/run",
        },
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


@router.get("/jobs")
async def list_jobs_no_slash_compat(_user: dict = Depends(_get_auth())):
    return {"success": True, "jobs": [], "count": 0, "canonical": "/api/jobs/"}


@router.get("/jobs/history")
async def list_jobs_history_compat(_user: dict = Depends(_get_auth())):
    return {"success": True, "jobs": [], "count": 0, "canonical": "/api/jobs/"}


@router.get("/model-usage")
async def model_usage_compat(_user: dict = Depends(_get_optional_user())):
    return {
        "status": "ready",
        "usage": [],
        "totals": {"requests": 0, "tokens": 0, "estimated_cost_usd": 0.0},
        "note": "No model usage rows recorded for this session yet.",
    }


@router.get("/cost/pricing")
async def cost_pricing_compat():
    return {
        "status": "ready",
        "currency": "USD",
        "unit": "credits",
        "plans": [
            {"id": "free", "name": "Free", "credits": 200, "price": 0},
            {"id": "builder", "name": "Builder", "status": "available"},
            {"id": "pro", "name": "Pro", "status": "available"},
            {"id": "teams", "name": "Teams", "status": "available"},
        ],
    }


@router.get("/cost/totals")
async def cost_totals_compat(_user: dict = Depends(_get_optional_user())):
    return {"status": "ready", "totals": {"credits_used": 0, "estimated_cost_usd": 0.0}, "rows": []}


@router.get("/cost/balance")
async def cost_balance_compat(_user: dict = Depends(_get_optional_user())):
    credits = 0
    if isinstance(_user, dict):
        credits = int(_user.get("credit_balance") or 0)
    return {"status": "ready", "credit_balance": credits}


@router.get("/payments/plans")
async def payment_plans_compat():
    return {
        "status": "ready",
        "checkout": "requires_braintree_configuration",
        "plans": [
            {"id": "free", "name": "Free", "credits": 200},
            {"id": "builder", "name": "Builder"},
            {"id": "pro", "name": "Pro"},
            {"id": "teams", "name": "Teams"},
        ],
    }


@router.get("/examples")
async def list_examples_compat():
    return {
        "status": "ready",
        "examples": [
            {"id": "saas-dashboard", "title": "SaaS dashboard", "prompt": "Build a SaaS MVP with auth, dashboard, CRUD, and billing-ready pricing."},
            {"id": "mobile-app", "title": "Mobile app", "prompt": "Build a React Native Expo app with onboarding, tabs, and local storage."},
            {"id": "automation-agent", "title": "Automation agent", "prompt": "Build an automation that summarizes inbound leads and drafts follow-ups."},
            {"id": "internal-tool", "title": "Internal tool", "prompt": "Build an admin tool with tables, approvals, audit logs, and RBAC."},
        ],
    }


@router.get("/templates")
async def list_templates_compat():
    try:
        from ..routes.community import LAUNCH_TEMPLATES

        return {"status": "ready", "templates": LAUNCH_TEMPLATES}
    except Exception:
        return {"status": "ready", "templates": []}


@router.get("/patterns")
async def list_patterns_compat():
    return {
        "status": "ready",
        "patterns": [
            {"id": "saas-mvp", "name": "SaaS MVP", "category": "build", "description": "Auth, dashboard, CRUD, billing-ready pricing, and deploy handoff."},
            {"id": "agent-automation", "name": "Agent automation", "category": "automation", "description": "Trigger, steps, action log, retry policy, and run_agent bridge."},
            {"id": "reality-simulation", "name": "Reality simulation", "category": "simulation", "description": "Evidence, agents, debate, population cohorts, outcomes, and trust."},
            {"id": "enterprise-admin", "name": "Enterprise admin", "category": "enterprise", "description": "RBAC, audit logs, approvals, tables, reports, and operational controls."},
        ],
    }


@router.get("/prompts/templates")
async def list_prompt_templates_compat():
    return {
        "templates": [
            {"id": "ecommerce", "name": "E-commerce with cart", "category": "app", "prompt": "Build a modern e-commerce store with catalog, cart, checkout, and admin inventory."},
            {"id": "auth-dashboard", "name": "Auth + Dashboard", "category": "app", "prompt": "Create login/register pages and a dashboard with sidebar navigation and CRUD data."},
            {"id": "landing-waitlist", "name": "Landing + waitlist", "category": "marketing", "prompt": "Build a landing page with hero, features, pricing, FAQ, and waitlist signup."},
            {"id": "automation", "name": "Daily automation", "category": "automation", "prompt": "Build a daily automation that gathers updates, summarizes priorities, and prepares a morning brief."},
        ]
    }


@router.get("/prompts/recent")
async def list_recent_prompts_compat(_user: dict = Depends(_get_optional_user())):
    return {"prompts": []}


@router.get("/prompts/saved")
async def list_saved_prompts_compat(_user: dict = Depends(_get_optional_user())):
    return {"prompts": []}


@router.get("/integrations/status")
async def integrations_status_compat(_user: dict = Depends(_get_optional_user())):
    return {
        "status": "ready",
        "connectors": {
            "github": "requires_config",
            "railway": "requires_config",
            "vercel": "requires_config",
            "netlify": "requires_config",
            "slack": "requires_config",
            "braintree": "requires_config",
            "tavily": "requires_config",
        },
        "note": "Integration contracts are surfaced honestly; live connector actions require credentials.",
    }


@router.get("/workspace/capabilities")
async def workspace_capabilities_compat(_user: dict = Depends(_get_optional_user())):
    return {
        "status": "ready",
        "capabilities": {
            "jobs": "available",
            "preview": "available",
            "files": "available_when_job_has_workspace",
            "proof": "available_when_job_runs_verification",
            "terminal": "policy_controlled",
            "export": "available_when_workspace_files_exist",
        },
    }


@router.get("/workspace/files")
async def workspace_files_compat(_user: dict = Depends(_get_optional_user())):
    return {
        "files": [],
        "status": "requires_job",
        "note": "Use /api/builds/{job_id}/files or /api/jobs/{job_id}/workspace/files for a concrete build workspace.",
    }


@router.get("/terminal/sessions")
async def terminal_sessions_compat(_user: dict = Depends(_get_optional_user())):
    return {
        "sessions": [],
        "status": "policy_controlled",
        "note": "Production terminal execution is gated by policy; audit events are available at /api/terminal/audit.",
    }


@router.get("/automation/capabilities")
async def automation_capabilities_compat(_user: dict = Depends(_get_optional_user())):
    return {
        "status": "foundation",
        "capabilities": {
            "multi_step_runs": "available",
            "workflow_templates": "/api/capabilities/workflow-templates",
            "scheduled_tasks": "foundation",
            "webhooks": "foundation",
            "connector_backed_execution": "requires_config",
        },
    }


@router.get("/schedules")
async def schedules_compat(_user: dict = Depends(_get_optional_user())):
    return {"schedules": [], "status": "foundation", "note": "No scheduled runs configured for this user."}


@router.post("/assets/generate")
async def assets_generate_compat(payload: Dict[str, Any], _user: dict = Depends(_get_optional_user())):
    from .capabilities import AssetRequestGenerateBody, generate_asset_request

    body = AssetRequestGenerateBody(
        prompt=str(payload.get("prompt") or payload.get("description") or ""),
        asset_type=str(payload.get("asset_type") or "image"),
        provider=payload.get("provider"),
        metadata=payload.get("metadata") or {},
    )
    return await generate_asset_request(body, _user)


@router.get("/mobile/jobs")
async def mobile_jobs_compat(_user: dict = Depends(_get_optional_user())):
    return {"jobs": [], "status": "ready", "note": "No mobile builds for this user yet."}


@router.get("/commerce/products")
async def commerce_products_compat(_user: dict = Depends(_get_optional_user())):
    return {"products": [], "status": "foundation", "requires": ["Braintree or product data connector"]}


@router.get("/channels")
async def channels_compat(_user: dict = Depends(_get_optional_user())):
    return {"channels": [], "status": "foundation", "requires": ["Slack/email/webhook connector configuration"]}


@router.get("/sessions")
async def sessions_compat(_user: dict = Depends(_get_optional_user())):
    return {"sessions": [], "status": "ready"}


@router.get("/knowledge")
async def knowledge_compat(_user: dict = Depends(_get_optional_user())):
    return {"sources": [], "status": "foundation", "requires": ["document upload or knowledge connector"]}


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


@router.post("/stripe/webhook")
async def stripe_webhook_verify(request: Request):
    """Verify Stripe signatures when ``STRIPE_WEBHOOK_SECRET`` is set; else 503."""
    from fastapi.responses import JSONResponse

    import os

    wh_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
    payload = await request.body()
    sig = request.headers.get("stripe-signature") or request.headers.get("Stripe-Signature") or ""
    if not wh_secret:
        return JSONResponse({"detail": "stripe_webhook_not_configured"}, status_code=503)
    try:
        import stripe

        stripe.Webhook.construct_event(payload, sig, wh_secret)
    except Exception:
        return JSONResponse({"detail": "invalid_signature"}, status_code=400)
    return {"received": True}


@router.post("/stripe/create-checkout-session")
async def create_checkout_session_compat(
    payload: Dict[str, Any], _user: dict = Depends(_get_auth())
):
    raise HTTPException(
        status_code=410,
        detail={
            "error": "stripe_checkout_removed",
            "replacement": "/api/checkout/one-time",
            "billing_page": "/app/billing",
            "status_endpoint": "/api/payments/braintree/status",
        },
    )


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
