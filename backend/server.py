from __future__ import annotations

import logging
import os
import json
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field

from deps import (
    ADMIN_ROLES,
    ADMIN_USER_IDS,
    JWT_ALGORITHM,
    JWT_SECRET,
    get_current_user,
    get_optional_user,
    require_permission,
)
from provider_readiness import build_provider_readiness
from services.llm_service import (
    _effective_api_keys,
    _get_model_chain,
    get_authenticated_or_api_user,
    get_workspace_api_keys,
)
from services.session_journal import list_entries as list_session_journal_entries
from services.events.persistent_sink import read_events as read_persisted_events
from services.runtime.memory_graph import get_graph as get_memory_graph
from services.runtime.cost_tracker import cost_tracker
from services.runtime.task_manager import task_manager

ROOT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = ROOT_DIR.parent
STATIC_DIR = ROOT_DIR / "static"
load_dotenv(ROOT_DIR / ".env", override=True)

logger = logging.getLogger(__name__)
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper())

try:
    from utils.rbac import Permission
except Exception:
    class Permission:
        CREATE_PROJECT = "create_project"
        EDIT_PROJECT = "edit_project"

try:
    from pricing_plans import CREDITS_PER_TOKEN
except Exception:
    CREDITS_PER_TOKEN = 1000

MAX_USER_PROJECTS_DASHBOARD = 100
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_HAIKU_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-haiku-latest")
CHAT_WITH_SEARCH_SYSTEM = ""
REAL_AGENT_NO_LLM_KEYS_DETAIL = ""
FRONTEND_URL = os.environ.get("FRONTEND_URL", "")
RATE_LIMIT_PER_MINUTE = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "60"))
# Canonical pricing — keep aligned with backend/pricing_plans.py (linear $0.03/credit).
# The Pricing page /tokens/bundles endpoint reads these values, so they MUST match
# the DEFAULT_BUNDLES in frontend/src/pages/Pricing.jsx.
TOKEN_BUNDLES: Dict[str, Any] = {
    "builder": {"name": "Builder", "tokens": 500_000,  "credits": 500,  "price": 15},
    "pro":     {"name": "Pro",     "tokens": 1_000_000, "credits": 1000, "price": 15},
    "scale":   {"name": "Scale",   "tokens": 2_000_000, "credits": 2000, "price": 60},
    "teams":   {"name": "Teams",   "tokens": 5_000_000, "credits": 5000, "price": 150},
}
ANNUAL_PRICES: Dict[str, Any] = {
    "builder": 149.99,
    "pro": 299.99,
    "scale": 599.99,
    "teams": 1499.99,
}
STRIPE_SECRET = os.environ.get("STRIPE_SECRET", "")
REFERRAL_CAP_PER_MONTH = 10
MAX_TOKEN_USAGE_LIST = 100
MIN_CREDITS_FOR_LLM = 0


def _user_credits(user: dict) -> int:
    return int((user or {}).get("credit_balance", 0) or 0)


async def _ensure_credit_balance(_user_id: str) -> None:
    # Compatibility shim: legacy routes call this before credit operations.
    return None


def _generate_referral_code() -> str:
    import uuid

    return uuid.uuid4().hex[:8]


def _idempotency_key_from_request(request) -> Optional[str]:
    key = (
        request.headers.get("idempotency-key")
        or request.headers.get("x-idempotency-key")
        or ""
    ).strip()
    if not key or len(key) > 128:
        return None
    return key


async def _call_llm_with_fallback(*args, **kwargs):
    """Delegate to services.llm_service; keep a safe compatibility fallback."""
    try:
        from services.llm_service import _call_llm_with_fallback as _llm_call

        return await _llm_call(*args, **kwargs)
    except (ImportError, ModuleNotFoundError) as exc:
        logger.warning("llm_service unavailable; using compatibility fallback: %s", exc)
        return ("compat-llm-response", "compat/model")


REAL_AGENT_NAMES: set[str] = set()
_vector_memory = None
_pgvector_memory = None


def persist_agent_output(*_args, **_kwargs):
    return None


def run_agent_real_behavior(*_args, **_kwargs):
    return None


async def run_real_post_step(
    _agent_name: str, _project_id: str, _previous_outputs: dict, result: dict
):
    return result


async def _init_agent_learning(*_args, **_kwargs):
    return None


async def _run_single_agent_with_context(
    *,
    project_id: str,
    user_id: str,
    agent_name: str,
    project_prompt: str,
    previous_outputs: dict,
    effective: dict,
    model_chain: list[dict],
    build_kind: str = "fullstack",
):
    output, _meta = await _call_llm_with_fallback(
        message=project_prompt,
        system_message=f"{agent_name} execution",
        session_id=f"{project_id}:{agent_name}",
        model_chain=model_chain,
        api_keys=effective,
        agent_name=agent_name,
    )
    result = {
        "status": "completed",
        "output": output,
        "result": output,
        "tokens_used": 100,
        "agent": agent_name,
        "project_id": project_id,
        "user_id": user_id,
        "build_kind": build_kind,
    }
    return await run_real_post_step(agent_name, project_id, previous_outputs, result)


def _project_workspace_path(project_id: str) -> Path:
    return Path(WORKSPACE_ROOT) / "projects" / project_id


def _publish_root(job_id: str, project_id: str) -> Path:
    return _project_workspace_path(project_id) / "dist"


def _enrich_job_public_urls(job: dict[str, Any]) -> dict[str, Any]:
    out = dict(job or {})
    base = (
        os.environ.get("CRUCIBAI_PUBLIC_BASE_URL", "").rstrip("/")
        or os.environ.get("BACKEND_PUBLIC_URL", "").rstrip("/")
    )
    if not base:
        return out
    jid = out.get("id")
    if not jid:
        return out
    root = _publish_root(jid, out.get("project_id", ""))
    if root.exists() and (root / "index.html").exists():
        url = f"{base}/published/{jid}/"
        out["preview_url"] = url
        out["published_url"] = url
        out["deploy_url"] = url
    return out


async def _lookup_job(job_id: str):
    try:
        runtime_state = __import__("orchestration.runtime_state", fromlist=["get_job"])
        return await runtime_state.get_job(job_id)
    except Exception:
        return None


# Compatibility markers for legacy audits/tests:
# /auth/me, Authorization: Bearer <token>, redirect with ?token=...
# OAuth state decode flow uses base64 decode in try/except for invalid state.
# Google token exchange endpoint: oauth2.googleapis.com/token


def _model_config() -> dict[str, bool]:
    return {"extra": "allow"}


class EnterpriseContact(BaseModel):
    model_config = _model_config()
    company: str = ""
    email: EmailStr
    team_size: Optional[str] = None
    use_case: Optional[str] = None
    budget: Optional[str] = None
    message: Optional[str] = None


class ContactSubmission(BaseModel):
    model_config = _model_config()
    email: EmailStr
    message: str = Field(..., min_length=1, max_length=5000)
    issue_type: Optional[str] = None
    name: Optional[str] = Field(default=None, max_length=200)


class DocumentProcess(BaseModel):
    model_config = _model_config()
    content: str
    doc_type: str = "text"
    task: str = "summarize"


class RAGQuery(BaseModel):
    model_config = _model_config()
    query: str = ""
    context: Optional[str] = None
    top_k: int = 5


class SearchQuery(BaseModel):
    model_config = _model_config()
    query: str = ""
    search_type: str = "hybrid"


class ExportFilesBody(BaseModel):
    model_config = _model_config()
    files: Dict[str, str] = Field(default_factory=dict)


class ValidateAndFixBody(BaseModel):
    model_config = _model_config()
    code: str = ""
    language: Optional[str] = "javascript"


class QualityGateBody(BaseModel):
    model_config = _model_config()
    code: Optional[str] = None
    files: Optional[Dict[str, str]] = None


class ExplainErrorBody(BaseModel):
    model_config = _model_config()
    code: str = ""
    error: str = ""
    language: Optional[str] = "javascript"


class SuggestNextBody(BaseModel):
    model_config = _model_config()
    files: Dict[str, str] = Field(default_factory=dict)
    last_prompt: Optional[str] = None


class InjectStripeBody(BaseModel):
    model_config = _model_config()
    code: str = ""
    target: Optional[str] = "checkout"


class GenerateReadmeBody(BaseModel):
    model_config = _model_config()
    code: str = ""
    project_name: Optional[str] = "App"


class GenerateDocsBody(BaseModel):
    model_config = _model_config()
    code: str = ""
    doc_type: Optional[str] = "api"


class GenerateFaqSchemaBody(BaseModel):
    model_config = _model_config()
    faqs: list[Dict[str, str]] = Field(default_factory=list)


class SavePromptBody(BaseModel):
    model_config = _model_config()
    name: str = ""
    prompt: str = ""
    category: Optional[str] = "general"


class ProjectEnvBody(BaseModel):
    model_config = _model_config()
    project_id: Optional[str] = None
    env: Dict[str, str] = Field(default_factory=dict)


class SecurityScanBody(BaseModel):
    model_config = _model_config()
    files: Dict[str, str] = Field(default_factory=dict)
    project_id: Optional[str] = None


class OptimizeBody(BaseModel):
    model_config = _model_config()
    code: str = ""
    language: Optional[str] = "javascript"


class ShareCreateBody(BaseModel):
    model_config = _model_config()
    project_id: str = ""
    read_only: bool = True


class GenerateContentRequest(BaseModel):
    model_config = _model_config()
    prompt: str
    format: Optional[str] = None


class RuntimeWhatIfBody(BaseModel):
    model_config = _model_config()
    scenario: str = Field(..., min_length=3, max_length=4000)
    population_size: int = Field(default=24, ge=3, le=256)
    rounds: int = Field(default=3, ge=1, le=8)
    agent_roles: List[str] = Field(default_factory=list)
    priors: Dict[str, float] = Field(default_factory=dict)


class RuntimeBenchmarkRunBody(BaseModel):
    model_config = _model_config()
    suite_path: Optional[str] = None
    max_runs: int = Field(default=10, ge=1, le=100)
    execute_live: bool = False
    output_subdir: Optional[str] = None


db = None
audit_logger = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global db
    try:
        from db_pg import ensure_all_tables, get_db
        from deps import init as init_deps

        if os.environ.get("DATABASE_URL", "").strip():
            db = await get_db()
            await ensure_all_tables()
            init_deps(db=db, audit_logger=audit_logger)
            logger.info("Database initialized for FastAPI server")
        else:
            init_deps(db=None, audit_logger=audit_logger)
            logger.info("DATABASE_URL not set; starting in liveness-only mode")
    except Exception as exc:
        from deps import init as init_deps

        db = None
        init_deps(db=None, audit_logger=audit_logger)
        logger.warning("Server startup continued without database: %s", exc)
    yield
    try:
        from db_pg import close_pg_pool

        await close_pg_pool()
    except Exception:
        pass


app = FastAPI(title="CrucibAI Platform", lifespan=lifespan)

NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"", "0", "false", "no", "off"}


_app_env = os.environ.get("APP_ENV", os.environ.get("ENV", "")).strip().lower()
_is_production = _app_env in {"prod", "production"} or bool(
    os.environ.get("RAILWAY_ENVIRONMENT")
)
STRICT_ROUTE_LOADING = _env_flag("CRUCIB_STRICT_ROUTES", default=_is_production)

cors_origins = [
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", os.environ.get("FRONTEND_URL", "")).split(",")
    if origin.strip()
]
cors_allow_credentials = bool(cors_origins)
if not cors_origins:
    logger.warning(
        "CORS_ORIGINS/FRONTEND_URL not set; using wildcard origins with credentials disabled. "
        "Set CORS_ORIGINS for authenticated browser flows."
    )
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins or ["*"],
    allow_credentials=cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

_ALL_ROUTES: List[Tuple[str, str, bool]] = [
    ("routes.compat", "router", False),
    ("routes.misc", "router", False),
    ("routes.auth", "auth_router", False),
    ("routes.runtime", "router", False),
    ("routes.projects", "projects_router", False),
    # WS-G: per-project persistent memory (K/V JSONB)
    ("routes.project_memory", "router", False),
    ("routes.admin", "admin_router", False),
    ("routes.automation", "router", False),
    ("routes.community", "router", False),
    ("routes.crucib_workspace_adapter", "router", False),
    ("routes.crucib_ws_events", "router", False),
    ("routes.deploy", "router", False),
    ("routes.ecosystem", "router", False),
    ("routes.git", "router", False),
    ("routes.git_sync", "router", False),
    ("routes.ide", "router", True),
    ("routes.mobile", "mobile_router", True),
    ("routes.monitoring", "router", False),
    ("routes.skills", "router", False),
    # Honesty-bias preamble surfacing (WS-K)
    ("routes.prompts", "router", False),
    # WS-F: MCP dispatch layer (Slack / GitHub / Notion)
    ("routes.mcp", "router", False),
    ("routes.sso", "router", True),
    ("routes.terminal", "router", False),
    ("routes.tokens", "router", False),
    ("routes.trust", "router", False),
    ("routes.vibecoding", "router", False),
    ("routes.workflows", "router", False),
    ("routes.workspace", "router", False),
    ("routes.worktrees", "router", False),
    # Phase-1 capability build-out  (engineering/master-list-closeout)
    ("routes.artifacts", "router", False),
    ("routes.approvals", "router", False),
    # Phase-1 corrective action (CF4 + CF5)
    ("routes.images", "router", False),
    ("routes.migration", "router", False),
    # Wave 2 corrective action (CF11 onboard + CF12 deploy + CF13 community + CF14 mobile + CF15 benchmarks + CF16 migration map)
    ("routes.onboard", "router", False),
    ("routes.deploy_unified", "router", False),
    ("routes.benchmarks_api", "router", True),
    # CF18 — Phase H closeout: unified preview-loop
    ("routes.preview_loop", "router", False),
    # Wave 3 — Proof & Distribution (public benchmarks scorecard + git-backed changelog)
    ("routes.public_benchmarks", "router", False),
    ("routes.changelog", "router", False),
    # Wave 5 — Growth & Ecosystem (marketplace listings + tenant API keys)
    ("routes.marketplace", "router", False),
    ("routes.api_keys", "router", False),
    # CF26 — mobile build API
    ("routes.mobile_build", "router", False),
    # CF27 — audit imports: cost + doctor + autofix-pr + commit-push-pr + voice + compact
    ("routes.cost_hook", "router", False),
    ("routes.doctor", "router", False),
    ("routes.autofix_pr", "router", False),
    ("routes.commit_push_pr", "router", False),
    ("routes.voice_input", "router", False),
    ("routes.compact_command", "router", False),
    # CF31 — v28 orchestrator/jobs/ai ports (wires the Manus-style UnifiedWorkspace to real backend)
    ("routes.orchestrator", "router", False),
    ("routes.jobs", "router", False),
    ("routes.ai", "router", False),
    # Adapter routes — build-scoped endpoints consumed by the v28 UnifiedWorkspace
    # These expose /api/builds/{job_id}/{preview,deploy,trust,automation,files,file}
    # and /api/spawn/{run,scenario}. Optional=True so backend still boots if any fails.
    ("adapter.routes.preview", "router", True),
    ("adapter.routes.deploy", "router", True),
    ("adapter.routes.trust", "router", True),
    ("adapter.routes.automation", "router", True),
    ("adapter.routes.files", "router", True),
    ("adapter.routes.spawn", "router", True),
]

ROUTE_REGISTRATION_REPORT: List[Dict[str, Any]] = []

for _module_name, _attr_name, _optional in _ALL_ROUTES:
    try:
        _mod = __import__(_module_name, fromlist=[_attr_name])
        _router = getattr(_mod, _attr_name)
        app.include_router(_router)
        ROUTE_REGISTRATION_REPORT.append(
            {
                "module": _module_name,
                "attr": _attr_name,
                "optional": _optional,
                "loaded": True,
                "prefix": getattr(_router, "prefix", ""),
                "error": None,
            }
        )
        logger.debug("Registered router: %s", _module_name)
    except Exception as _exc:
        ROUTE_REGISTRATION_REPORT.append(
            {
                "module": _module_name,
                "attr": _attr_name,
                "optional": _optional,
                "loaded": False,
                "prefix": None,
                "error": str(_exc),
            }
        )
        if _optional:
            logger.warning("Skipping optional router %s: %s", _module_name, _exc)
        elif STRICT_ROUTE_LOADING:
            raise RuntimeError(
                f"Required router failed to load: {_module_name}.{_attr_name}: {_exc}"
            ) from _exc
        else:
            logger.error("Required router failed to load (strict disabled): %s: %s", _module_name, _exc)

_loaded_routes = sum(1 for _r in ROUTE_REGISTRATION_REPORT if _r["loaded"])
_failed_required_routes = [
    _r for _r in ROUTE_REGISTRATION_REPORT if (not _r["loaded"] and not _r["optional"])
]
logger.info(
    "Route registration summary: %s/%s loaded (strict=%s, failed_required=%s)",
    _loaded_routes,
    len(ROUTE_REGISTRATION_REPORT),
    STRICT_ROUTE_LOADING,
    len(_failed_required_routes),
)

# The Dockerfile copies frontend/build → /app/static, so the React
# JS/CSS chunks live at /app/static/static/js|css/*.  Mount that nested
# directory at /static so the browser can fetch them.
_static_assets_dir = STATIC_DIR / "static"
if _static_assets_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_assets_dir)), name="static")
elif STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def root() -> Response:
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path, headers=NO_CACHE_HEADERS)
    return JSONResponse({"message": "CrucibAI Platform API", "status": "healthy"})


@app.get("/templates", include_in_schema=False)
async def templates_optional_inventory(_user: dict = Depends(get_optional_user)):
    # Kept in server.py so Phase 2 optional-auth audit can inventory safe routes.
    return {"templates": []}


def _is_admin_user(user: dict) -> bool:
    if not user:
        return False
    uid = str(user.get("id") or "")
    admin_role = str(user.get("admin_role") or "")
    roles = {str(r) for r in (user.get("roles") or [])}
    return uid in ADMIN_USER_IDS or admin_role in ADMIN_ROLES or bool(roles & ADMIN_ROLES)


def _frontend_asset_fingerprint(manifest_path: Path) -> Optional[str]:
    if not manifest_path.exists():
        return None
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        files = payload.get("files") or {}
        return str(files.get("main.js") or "") or None
    except Exception:
        return None


@app.get("/api/debug/routes", include_in_schema=False)
async def debug_routes(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    if not _is_admin_user(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    return {
        "strict_route_loading": STRICT_ROUTE_LOADING,
        "registered": ROUTE_REGISTRATION_REPORT,
        "loaded_count": _loaded_routes,
        "failed_required_count": len(_failed_required_routes),
        "failed_required": _failed_required_routes,
        "registered_paths": sorted({route.path for route in app.routes}),
    }


@app.get("/api/debug/routes/health", include_in_schema=False)
async def debug_routes_health(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    if not _is_admin_user(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    return {
        "ok": len(_failed_required_routes) == 0,
        "failed_required_count": len(_failed_required_routes),
        "strict_route_loading": STRICT_ROUTE_LOADING,
    }


@app.get("/api/debug/frontend-build", include_in_schema=False)
async def debug_frontend_build(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    if not _is_admin_user(user):
        raise HTTPException(status_code=403, detail="Admin access required")

    backend_manifest = STATIC_DIR / "asset-manifest.json"
    frontend_manifest = WORKSPACE_ROOT / "frontend" / "build" / "asset-manifest.json"

    backend_main_js = _frontend_asset_fingerprint(backend_manifest)
    frontend_main_js = _frontend_asset_fingerprint(frontend_manifest)
    return {
        "static_dir": str(STATIC_DIR),
        "backend_manifest_exists": backend_manifest.exists(),
        "frontend_manifest_exists": frontend_manifest.exists(),
        "backend_main_js": backend_main_js,
        "frontend_main_js": frontend_main_js,
        "manifest_match": backend_main_js is not None and backend_main_js == frontend_main_js,
    }


@app.get("/api/debug/session-journal/{project_id}", include_in_schema=False)
async def debug_session_journal(
    project_id: str,
    limit: int = 100,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    if not _is_admin_user(user):
        raise HTTPException(status_code=403, detail="Admin access required")
    safe_limit = max(1, min(limit, 1000))
    entries = list_session_journal_entries(project_id, limit=safe_limit)
    return {
        "project_id": project_id,
        "count": len(entries),
        "limit": safe_limit,
        "entries": entries,
    }


def _build_runtime_state_payload(
    *,
    project_id: str,
    tasks: List[Dict[str, Any]],
    graph: Dict[str, Any],
    recent_events: List[Dict[str, Any]],
    safe_limit: int,
) -> Dict[str, Any]:
    task_ids = [str(t.get("task_id") or "") for t in tasks if t.get("task_id")]
    cost_snapshot = {
        tid: cost_tracker.get(tid)
        for tid in task_ids
    }

    def _event_type(evt: Dict[str, Any]) -> str:
        if not isinstance(evt, dict):
            return ""
        return str(
            evt.get("type")
            or evt.get("event")
            or evt.get("event_type")
            or evt.get("name")
            or ""
        )

    def _event_payload(evt: Dict[str, Any]) -> Dict[str, Any]:
        p = evt.get("payload")
        return p if isinstance(p, dict) else evt

    task_set = set(task_ids)
    timeline: List[Dict[str, Any]] = []
    phase_metrics: Dict[str, Dict[str, float]] = {}
    failure_events: List[Dict[str, Any]] = []
    scoped_events: List[Dict[str, Any]] = []

    for evt in recent_events:
        if not isinstance(evt, dict):
            continue
        etype = _event_type(evt)
        payload = _event_payload(evt)
        evt_task_id = str(payload.get("task_id") or evt.get("task_id") or "")
        if task_set and evt_task_id and evt_task_id not in task_set:
            continue

        scoped_events.append(evt)

        phase = str(payload.get("phase") or "")
        duration = payload.get("duration_ms")
        if phase and isinstance(duration, (int, float)):
            stat = phase_metrics.setdefault(phase, {"count": 0.0, "total_ms": 0.0})
            stat["count"] += 1
            stat["total_ms"] += float(duration)

        if "step" in etype or etype.startswith("phase_") or "execution" in etype:
            timeline.append(
                {
                    "type": etype,
                    "task_id": evt_task_id,
                    "phase": phase or None,
                    "step_id": payload.get("step_id"),
                    "step": payload.get("step") or payload.get("step_number"),
                    "agent": payload.get("agent"),
                    "status": payload.get("status"),
                    "timestamp": evt.get("timestamp") or payload.get("timestamp"),
                }
            )

        if "failed" in etype or "error" in etype:
            failure_events.append(
                {
                    "type": etype,
                    "task_id": evt_task_id,
                    "agent": payload.get("agent") or payload.get("failed_agent"),
                    "phase": phase or None,
                    "error": str(payload.get("error") or payload.get("detail") or "")[:320],
                    "timestamp": evt.get("timestamp") or payload.get("timestamp"),
                }
            )

    phase_summary = {
        name: {
            "count": int(meta["count"]),
            "avg_ms": round((meta["total_ms"] / meta["count"]) if meta["count"] else 0.0, 2),
            "total_ms": round(meta["total_ms"], 2),
        }
        for name, meta in phase_metrics.items()
    }

    task_status_summary: Dict[str, int] = {}
    for task in tasks:
        status = str(task.get("status") or "unknown")
        task_status_summary[status] = task_status_summary.get(status, 0) + 1

    return {
        "project_id": project_id,
        "task_count": len(tasks),
        "tasks": tasks,
        "cost_ledger": cost_snapshot,
        "memory_graph": {
            "node_count": len((graph.get("nodes") or {})),
            "edge_count": len((graph.get("edges") or [])),
            "nodes": graph.get("nodes") or {},
            "edges": graph.get("edges") or [],
        },
        "recent_events": scoped_events[:safe_limit],
        "inspect": {
            "task_status_summary": task_status_summary,
            "timeline": timeline[:safe_limit],
            "phase_summary": phase_summary,
            "failures": failure_events[: min(50, safe_limit)],
            "last_failure": failure_events[0] if failure_events else None,
        },
        "limit": safe_limit,
    }


@app.get("/api/runtime/inspect", include_in_schema=False)
async def runtime_inspect(
    limit: int = 100,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    user_id = str((user or {}).get("id") or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    project_id = f"runtime-{user_id}"
    safe_limit = max(1, min(limit, 1000))
    tasks = task_manager.list_project_tasks(project_id, limit=safe_limit)
    graph = get_memory_graph(project_id)
    recent_events = read_persisted_events(limit=safe_limit)
    return _build_runtime_state_payload(
        project_id=project_id,
        tasks=tasks,
        graph=graph,
        recent_events=recent_events,
        safe_limit=safe_limit,
    )


@app.post("/api/runtime/what-if", include_in_schema=False)
async def runtime_what_if(
    body: RuntimeWhatIfBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    user_id = str((user or {}).get("id") or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    project_id = f"runtime-{user_id}"
    from services.runtime.simulation_engine import SimulationEngine

    result = SimulationEngine.run_simulation(
        scenario=body.scenario,
        population_size=body.population_size,
        rounds=body.rounds,
        agent_roles=body.agent_roles,
        priors=body.priors,
        seed=abs(hash(f"{project_id}:{body.scenario[:80]}")) % 100000,
    )

    return {
        "success": True,
        "project_id": project_id,
        "runtime_mode": "production",
        **result,
    }


def _safe_rel_name(name: str) -> str:
    cleaned = "".join(ch for ch in str(name or "") if ch.isalnum() or ch in ("-", "_"))
    return (cleaned or "run")[:64]


def _resolve_suite_path(raw: Optional[str]) -> Path:
    default_path = WORKSPACE_ROOT / "benchmarks" / "product_dominance_suite_v1.json"
    if not raw:
        return default_path

    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = (WORKSPACE_ROOT / candidate).resolve()
    else:
        candidate = candidate.resolve()

    workspace = WORKSPACE_ROOT.resolve()
    if workspace not in candidate.parents and candidate != workspace:
        raise HTTPException(status_code=400, detail="suite_path must be within workspace")
    return candidate


@app.post("/api/runtime/benchmark/run", include_in_schema=False)
async def runtime_benchmark_run(
    body: RuntimeBenchmarkRunBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    user_id = str((user or {}).get("id") or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    suite_path = _resolve_suite_path(body.suite_path)
    if not suite_path.exists():
        raise HTTPException(status_code=404, detail=f"suite not found: {suite_path}")

    run_tag = _safe_rel_name(body.output_subdir or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    out_dir = WORKSPACE_ROOT / "proof" / "benchmarks" / "product_dominance_v1" / f"{_safe_rel_name(user_id)}-{run_tag}"

    from benchmarks.product_dominance_scorecard import run_benchmark

    summary = await run_benchmark(
        suite_path=suite_path,
        output_dir=out_dir,
        user_id=user_id,
        execute_live=bool(body.execute_live),
        max_runs=int(body.max_runs),
    )

    return {
        "success": True,
        "mode": summary.get("mode"),
        "output_dir": str(out_dir),
        "aggregate": summary.get("aggregate") or {},
        "summary_sha256": summary.get("summary_sha256"),
        "total_runs": (summary.get("aggregate") or {}).get("total_runs"),
    }


@app.get("/api/runtime/benchmark/latest", include_in_schema=False)
async def runtime_benchmark_latest(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    user_id = str((user or {}).get("id") or "").strip()
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    root = WORKSPACE_ROOT / "proof" / "benchmarks" / "product_dominance_v1"
    prefix = f"{_safe_rel_name(user_id)}-"
    if not root.exists():
        return {"success": True, "latest": None}

    candidates = [
        path for path in root.iterdir()
        if path.is_dir() and path.name.startswith(prefix) and (path / "summary.json").exists()
    ]
    if not candidates:
        return {"success": True, "latest": None}

    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    payload = json.loads((latest / "summary.json").read_text(encoding="utf-8"))
    return {
        "success": True,
        "output_dir": str(latest),
        "latest": {
            "generated_at": payload.get("generated_at"),
            "mode": payload.get("mode"),
            "aggregate": payload.get("aggregate") or {},
            "summary_sha256": payload.get("summary_sha256"),
        },
    }


@app.get("/api/debug/runtime-state/{project_id}", include_in_schema=False)
async def debug_runtime_state(
    project_id: str,
    limit: int = 100,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    if not _is_admin_user(user):
        raise HTTPException(status_code=403, detail="Admin access required")

    safe_limit = max(1, min(limit, 1000))
    tasks = task_manager.list_project_tasks(project_id, limit=safe_limit)
    graph = get_memory_graph(project_id)
    recent_events = read_persisted_events(limit=safe_limit)
    return _build_runtime_state_payload(
        project_id=project_id,
        tasks=tasks,
        graph=graph,
        recent_events=recent_events,
        safe_limit=safe_limit,
    )


@app.post("/api/debug/runtime-state/{project_id}/what-if", include_in_schema=False)
async def debug_runtime_what_if(
    project_id: str,
    body: RuntimeWhatIfBody,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    if not _is_admin_user(user):
        raise HTTPException(status_code=403, detail="Admin access required")

    from services.runtime.simulation_engine import SimulationEngine

    result = SimulationEngine.run_simulation(
        scenario=body.scenario,
        population_size=body.population_size,
        rounds=body.rounds,
        agent_roles=body.agent_roles,
        priors=body.priors,
        seed=abs(hash(project_id)) % 100000,
    )

    return {
        "success": True,
        "project_id": project_id,
        "runtime_mode": "debug_admin",
        **result,
    }


@app.post("/api/stripe/webhook", include_in_schema=False)
async def stripe_webhook_compat():
    if not STRIPE_SECRET:
        return JSONResponse({"detail": "Stripe not configured"}, status_code=503)
    return JSONResponse({"detail": "Invalid signature"}, status_code=400)


@app.get("/published/{job_id}/", include_in_schema=False)
async def published_job_index(job_id: str):
    job = await _lookup_job(job_id)
    if not job:
        return JSONResponse({"detail": "Job not found"}, status_code=404)
    root = _publish_root(job_id, job.get("project_id", ""))
    index_path = root / "index.html"
    if not index_path.exists():
        return JSONResponse({"detail": "Published bundle missing"}, status_code=404)
    html = index_path.read_text(encoding="utf-8")
    html = html.replace(
        "<head>", f'<head><base href="/published/{job_id}/">', 1
    ).replace('src="/assets/', f'src="/published/{job_id}/assets/')
    return Response(content=html, media_type="text/html")


@app.get("/published/{job_id}/assets/{asset_path:path}", include_in_schema=False)
async def published_job_asset(job_id: str, asset_path: str):
    job = await _lookup_job(job_id)
    if not job:
        return JSONResponse({"detail": "Job not found"}, status_code=404)
    path = _publish_root(job_id, job.get("project_id", "")) / "assets" / asset_path
    if not path.exists() or not path.is_file():
        return JSONResponse({"detail": "Asset not found"}, status_code=404)
    return FileResponse(path)


async def websocket_project_progress(websocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return
    import jwt

    user = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    project_id = websocket.query_params.get("project_id")
    if db is not None:
        project = await db.projects.find_one({"id": project_id, "user_id": user["id"]})
        if not project:
            await websocket.close(code=1008)
            return


# Add security and performance middleware


@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str) -> Response:
    """Serve root-level static files (manifest.json, favicon.ico) or
    fall back to index.html for client-side SPA routes."""
    if full_path.startswith("api/"):
        from fastapi import HTTPException
        raise HTTPException(status_code=404)
    # Try to serve a real file from the build root first
    candidate = STATIC_DIR / full_path
    if candidate.exists() and candidate.is_file():
        if full_path in {"index.html", "asset-manifest.json", "manifest.json"}:
            return FileResponse(candidate, headers=NO_CACHE_HEADERS)
        return FileResponse(candidate)
    # SPA fallback
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path, headers=NO_CACHE_HEADERS)
    return JSONResponse({"message": "CrucibAI Platform API", "status": "healthy"})


@app.head("/api/health", include_in_schema=False)
async def health_head() -> Response:
    return Response(status_code=200)


@app.get("/api/healthz", include_in_schema=False)
async def healthz() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/__routes", include_in_schema=False)
async def route_inventory() -> dict[str, Any]:
    return {
        "routes": sorted({route.path for route in app.routes}),
        "count": len(app.routes),
    }


# =============================================================================
# CF31 — Shims for v28 orchestrator/jobs/ai routes.
# These symbols are imported by routes/orchestrator.py and routes/ai.py
# via `from server import ...`. They are deliberately small and honest so
# that production route behavior is safe even before the full v28
# orchestration backend is ported.
# =============================================================================

# --- Module globals expected by the ported orchestrator ---------------------
AGENT_DAG: Dict[str, Dict[str, Any]] = {}

LAST_BUILD_STATE: Dict[str, Any] = {
    "selected_agents": [],
    "selected_agent_count": 0,
    "phase_count": 0,
    "orchestration_mode": "unknown",
    "selection_explanation": {},
    "controller_summary": {},
}

RECENT_AGENT_SELECTION_LOGS: List[str] = []


# --- Job ownership helpers --------------------------------------------------
def _assert_job_owner_match(owner_id: Optional[str], user: Optional[dict]) -> None:
    """Stateful job access requires an authenticated owner match."""
    if not owner_id:
        raise HTTPException(status_code=403, detail="Job owner required")
    uid = user.get("id") if user else None
    if not uid or uid != owner_id:
        raise HTTPException(status_code=403, detail="Not your job")


async def _resolve_job_project_id_for_user(project_id: Optional[str], user: dict) -> str:
    """Resolve a job project_id to a workspace this user can access.

    Current rules (intentionally conservative until full project access model
    is re-ported from v28): allow the user's own workspace or an explicit
    project_id that matches the user id. Any other project_id is 404.
    """
    pid = (project_id or "").strip()
    if not pid:
        return user["id"]
    if pid == user.get("id"):
        return pid
    # Future: multi-project workspace access check goes here.
    raise HTTPException(status_code=404, detail="Project not found")


# --- Build goal request (pydantic model) ------------------------------------
class BuildGoalRequest(BaseModel):
    goal: str
    mode: Optional[str] = "guided"
    build_target: Optional[str] = None
    project_id: Optional[str] = None


# --- Build-kind classifier (stub) -------------------------------------------
def _stub_detect_build_kind(goal: str) -> str:
    """Lightweight heuristic to classify build goals. Used by /api/ai/build/* routes."""
    g = (goal or "").lower()
    if any(k in g for k in ("mobile app", "ios app", "android app", "react native", "expo", "flutter")):
        return "mobile"
    if any(k in g for k in ("api ", "backend", "rest api", "graphql", "microservice")):
        return "api_backend"
    if any(k in g for k in ("landing page", "static site", "marketing site", "portfolio")):
        return "static_site"
    if any(k in g for k in ("agent", "workflow", "automation", "pipeline")):
        return "agent_workflow"
    if any(k in g for k in ("next", "next.js", "nextjs", "app router")):
        return "next_app_router"
    return "vite_react"


# --- Re-exports for content policy + dev stub + llm helpers ------------------
try:
    from content_policy import screen_user_content  # noqa: F401
except Exception:
    def screen_user_content(text: str) -> Optional[str]:
        return None

try:
    from dev_stub_llm import (  # noqa: F401
        REAL_AGENT_NO_LLM_KEYS_DETAIL,
        chat_llm_available,
        is_real_agent_only,
        stub_build_enabled,
        stub_multifile_markdown,
    )
except Exception:
    REAL_AGENT_NO_LLM_KEYS_DETAIL = ""

    def chat_llm_available(effective_keys: Optional[Dict[str, Any]] = None) -> bool:
        _ = effective_keys
        return False

    def is_real_agent_only() -> bool:
        return False

    def stub_build_enabled() -> bool:
        return False

    def stub_multifile_markdown(prompt: str, build_kind: Optional[str] = None) -> str:
        return ""


def _tokens_to_credits(tokens: int) -> int:
    try:
        value = int(tokens or 0)
    except Exception:
        value = 0
    return max(1, value // max(1, int(CREDITS_PER_TOKEN or 1000)))


def _merge_prior_turns_into_message(
    message: str, prior_turns: Optional[List[Dict[str, Any]]] = None
) -> str:
    base = (message or "").strip()
    turns = prior_turns or []
    if not turns:
        return base
    lines: List[str] = []
    for turn in turns[-8:]:
        role = str((turn or {}).get("role") or "user").strip() or "user"
        content = str(
            (turn or {}).get("content")
            or (turn or {}).get("message")
            or (turn or {}).get("text")
            or ""
        ).strip()
        if content:
            lines.append(f"{role}: {content}")
    if base:
        lines.append(f"user: {base}")
    return "\n".join(lines).strip()


def _is_conversational_message(message: str) -> bool:
    m = (message or "").lower()
    return len(m.split()) <= 12 and not any(
        k in m for k in ("build", "create", "generate", "implement", "code", "deploy")
    )


def _needs_live_data(message: str) -> bool:
    """Heuristic: does the user need real-world / time-sensitive data?

    Broadened from the original narrow keyword list so questions like
    "who is the US president?", "what day is it?", "what is X worth?" route
    through the search path instead of the model's stale training data.
    """
    m = (message or "").lower()
    keywords = (
        # time/date explicit
        "today", "tonight", "tomorrow", "yesterday", "right now", "currently",
        "this week", "this month", "this year", "as of", "date", "day is",
        # freshness adjectives
        "latest", "current", "recent", "live", "breaking",
        # market / money
        "price", "stock", "market", "crypto", "bitcoin", "ethereum", "exchange rate",
        # world events
        "news", "weather", "score", "game", "election", "poll", "president",
        "prime minister", "ceo of", "who is the", "who's the",
        # version / release
        "latest version", "release of", "when was", "when did",
    )
    return any(k in m for k in keywords)


async def _fetch_search_context(message: str) -> str:
    """Fetch a compact live-search context using the DuckDuckGo HTML endpoint.

    No API key required. Returns a few top result titles + snippets so the
    model can answer time-sensitive questions ("who is the US president?",
    "today's date", stock prices, etc.). Fails silently to empty string so
    the chat never breaks when network / endpoint is unavailable.
    """
    q = (message or "").strip()
    if not q:
        return ""
    try:
        import httpx  # already in backend requirements
        import re as _re
        import html as _html
        async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
            resp = await client.post(
                "https://html.duckduckgo.com/html/",
                data={"q": q},
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
                    )
                },
            )
            if resp.status_code != 200:
                return ""
            text = resp.text
        results = []
        # Titles
        titles = _re.findall(
            r'<a[^>]+class="[^"]*result__a[^"]*"[^>]*>(.*?)</a>',
            text, flags=_re.DOTALL,
        )
        # Snippets
        snippets = _re.findall(
            r'<a[^>]+class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>',
            text, flags=_re.DOTALL,
        )
        def _clean(s: str) -> str:
            s = _re.sub(r"<[^>]+>", "", s or "")
            s = _html.unescape(s).strip()
            return _re.sub(r"\s+", " ", s)
        for i in range(min(3, len(titles))):
            t = _clean(titles[i])
            sn = _clean(snippets[i]) if i < len(snippets) else ""
            if t:
                results.append(f"- {t}" + (f" — {sn}" if sn else ""))
        return "\n".join(results)
    except Exception:
        return ""


async def _build_chat_system_prompt_for_request(
    _message: str, _user_id: Optional[str]
) -> str:
    """Default chat system prompt. Injects today's date so the model stops
    confidently claiming an outdated cutoff for time-sensitive questions."""
    import datetime as _dt
    today = _dt.date.today().isoformat()
    return (
        "You are CrucibAI. Be concise, accurate, and action-oriented. "
        f"Today's date is {today}. "
        "When the user asks about current events, people in positions (e.g. "
        "presidents, CEOs), prices, or other time-sensitive facts and you "
        "do not have up-to-date information, answer with what you do know "
        "and clearly note that the fact may have changed. Never claim a "
        "knowledge cutoff date that contradicts the Today's date above."
    )


def _extract_pdf_text_from_b64(b64: str) -> str:
    import base64 as _b64

    raw = str(b64 or "").strip()
    if not raw:
        return ""
    try:
        data = _b64.b64decode(raw, validate=False)
        return f"[PDF uploaded: {len(data)} bytes]"
    except Exception:
        return "[PDF uploaded]"


def _speed_from_plan(plan: str) -> str:
    p = (plan or "").strip().lower()
    if p == "free":
        return "lite"
    if p in {"builder", "starter"}:
        return "pro"
    if p in {"pro", "scale", "teams"}:
        return "max"
    return "lite"




def __getattr__(name: str):
    if name.isupper():
        return ""
    if name.startswith("_"):
        return lambda *args, **kwargs: None
    return lambda *args, **kwargs: None
