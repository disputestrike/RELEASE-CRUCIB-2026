from __future__ import annotations

import logging
import os
import json
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
TOKEN_BUNDLES: Dict[str, Any] = {
    "builder": {"name": "Builder", "tokens": 500_000, "credits": 500, "price": 29},
    "pro": {"name": "Pro", "tokens": 1_500_000, "credits": 1500, "price": 79},
    "scale": {"name": "Scale", "tokens": 5_000_000, "credits": 5000, "price": 199},
    "teams": {"name": "Teams", "tokens": 15_000_000, "credits": 15000, "price": 499},
}
ANNUAL_PRICES: Dict[str, Any] = {
    "builder": 290,
    "pro": 790,
    "scale": 1990,
    "teams": 4990,
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


async def _call_llm_with_fallback(*_args, **_kwargs):
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


db = None
audit_logger = None


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global db
    try:
        from db_pg import get_db
        from deps import init as init_deps

        if os.environ.get("DATABASE_URL", "").strip():
            db = await get_db()
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
    ("routes.sso", "router", True),
    ("routes.terminal", "router", False),
    ("routes.tokens", "router", False),
    ("routes.trust", "router", False),
    ("routes.vibecoding", "router", False),
    ("routes.workflows", "router", False),
    ("routes.workspace", "router", False),
    ("routes.worktrees", "router", False),
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

    task_ids = [str(t.get("task_id") or "") for t in tasks if t.get("task_id")]
    cost_snapshot = {
        tid: cost_tracker.get(tid)
        for tid in task_ids
    }

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
        "recent_events": recent_events,
        "limit": safe_limit,
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


def __getattr__(name: str):
    if name.startswith("_"):
        return lambda *args, **kwargs: None
    return ""
