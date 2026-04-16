from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Response
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
TOKEN_BUNDLES: Dict[str, Any] = {}
ANNUAL_PRICES: Dict[str, Any] = {}
STRIPE_SECRET = os.environ.get("STRIPE_SECRET", "")
REFERRAL_CAP_PER_MONTH = 10
MAX_TOKEN_USAGE_LIST = 100
MIN_CREDITS_FOR_LLM = 0


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

cors_origins = [
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", os.environ.get("FRONTEND_URL", "")).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_ALL_ROUTES: list[tuple[str, str]] = [
    ("routes.misc", "router"),
    ("routes.auth", "auth_router"),
    ("routes.runtime", "router"),
    ("routes.admin", "admin_router"),
    ("routes.automation", "router"),
    ("routes.community", "router"),
    ("routes.crucib_workspace_adapter", "router"),
    ("routes.crucib_ws_events", "router"),
    ("routes.deploy", "router"),
    ("routes.ecosystem", "router"),
    ("routes.git", "router"),
    ("routes.git_sync", "router"),
    ("routes.ide", "router"),
    ("routes.mobile", "mobile_router"),
    ("routes.monitoring", "router"),
    ("routes.skills", "router"),
    ("routes.sso", "router"),
    ("routes.terminal", "router"),
    ("routes.tokens", "router"),
    ("routes.trust", "router"),
    ("routes.vibecoding", "router"),
    ("routes.workflows", "router"),
    ("routes.workspace", "router"),
    ("routes.worktrees", "router"),
]

for _module_name, _attr_name in _ALL_ROUTES:
    try:
        _mod = __import__(_module_name, fromlist=[_attr_name])
        app.include_router(getattr(_mod, _attr_name))
        logger.debug("Registered router: %s", _module_name)
    except Exception as _exc:
        logger.warning("Skipping optional router %s: %s", _module_name, _exc)

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
        return FileResponse(index_path)
    return JSONResponse({"message": "CrucibAI Platform API", "status": "healthy"})


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
        return FileResponse(candidate)
    # SPA fallback
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
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
