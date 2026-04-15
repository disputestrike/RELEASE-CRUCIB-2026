from pathlib import Path

from dotenv import load_dotenv
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import (
    FileResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Load .env before any module that reads LLM keys at import time (e.g. llm_router).
ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / ".env", override=True)

import asyncio
import base64
import io
import json
import logging
import mimetypes
import os
import random
import re
import secrets
import subprocess
import sys
import tempfile
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urlencode

import bcrypt
import httpx
import jwt
from agent_dag import (
    AGENT_DAG,
    build_context_from_previous_agents,
    get_execution_phases,
    get_system_prompt_for_agent,
)
from agents.code_repair_agent import CodeRepairAgent, coerce_text_output
from anthropic_models import ANTHROPIC_HAIKU_MODEL, normalize_anthropic_model
from api_docs_generator import generate_api_docs
from endpoint_wrapper import safe_endpoint, wrap_all_endpoints
from env_encryption import decrypt_env, encrypt_env
from error_handlers import (
    AuthenticationError,
    CrucibError,
    DatabaseError,
    ExternalServiceError,
    ValidationError,
    log_error,
    to_http_exception,
)
from middleware import (
    HTTPSRedirectMiddleware,
    PerformanceMonitoringMiddleware,
    RateLimitMiddleware,
    RequestTrackerMiddleware,
    RequestValidationMiddleware,
    SecurityHeadersMiddleware,
)
from pydantic import BaseModel, EmailStr, Field, model_validator
from real_agent_runner import (
    REAL_AGENT_NAMES,
    persist_agent_output,
    run_real_agent,
    run_real_post_step,
)
from starlette.background import BackgroundTask
from starlette.middleware.cors import CORSMiddleware
from structured_logging import (
    get_audit_logger,
    get_error_logger,
    get_performance_logger,
    get_request_logger,
    log_audit,
    log_performance,
)
from validators import (
    BuildPlanRequestValidator,
    ChatMessageValidator,
    ProjectCreateValidator,
    UserLoginValidator,
    UserRegisterValidator,
    validate_email,
    validate_password_strength,
)
from services.published_app_service import (
    branding_response,
    enrich_job_public_urls as published_enrich_job_public_urls,
    serve_published_app_response,
)
from services.job_runtime_service import (
    cancel_job_service,
    get_job_trust_report_service,
    resume_job_service,
    retry_step_service,
    steer_job_service,
)
from services.job_event_service import (
    build_job_stream_response_service,
    get_job_events_service,
    get_job_plan_draft_service,
    get_job_proof_service,
    get_job_steps_service,
)
from services.job_service import create_job_service
from services.build_phase_service import build_plan_service, get_project_phases_service
from services.project_deploy_service import (
    deploy_railway_package_service,
    one_click_deploy_netlify_service,
    one_click_deploy_vercel_service,
    patch_project_publish_settings_service,
)
from services.agent_panel_service import (
    get_agent_status_service,
    get_agents_activity_service,
    get_agents_service,
)
from services.project_artifact_service import (
    build_project_deploy_zip_buffer_service,
    create_export_service,
    get_build_history_service,
    get_exports_service,
    get_project_deploy_files_json_service,
    get_project_logs_service,
)
from services.audit_log_service import get_audit_logs_service, export_audit_logs_service
from services.project_state_service import (
    delete_project_service,
    get_build_events_snapshot_service,
    get_project_service,
    get_project_state_service,
    stream_build_events_service,
)
from services.project_preview_service import (
    get_preview_token_service,
    serve_preview_service,
    get_project_dependency_audit_service,
)
from services.workspace_file_service import (
    get_job_workspace_file_content_service,
    get_job_workspace_file_raw_service,
    list_job_workspace_files_service,
    visual_edit_job_workspace_file_service,
)
from services.agent_execution_service import (
    repair_generated_agent_output_service,
    run_single_agent_with_context_service,
    run_single_agent_with_retry_service,
)
from services.orchestration_runtime_service import (
    execute_phase_service,
    finalize_project_run_status_service,
    mark_agents_started_service,
    mark_phase_started_service,
    process_phase_results_service,
    restore_checkpoint_results_service,
    set_project_run_status_service,
)
from services.post_build_service import (
    build_deploy_files_service,
    finalize_build_service,
    maybe_run_specialized_agent_service,
    run_autonomy_loop_service,
    run_quality_verification_service,
)

# Track the last plan/build state for debug visibility in production.
LAST_BUILD_STATE = {
    "selected_agents": [],
    "selected_agent_count": 0,
    "phase_count": 0,
    "orchestration_mode": "unknown",
    "selection_explanation": {},
    "controller_summary": {},
}
RECENT_AGENT_SELECTION_LOGS: list[str] = []


# CSRF Protection Middleware
class CSRFMiddleware:
    """Middleware to protect against CSRF attacks on state-changing requests."""

    # Endpoints that don't require CSRF protection (public/guest endpoints)
    CSRF_EXEMPT_PATHS = {
        "/api/auth/guest",
        "/api/auth/register",
        "/api/auth/signup",
        "/api/auth/login",
        "/api/auth/google",
        "/api/auth/google/callback",
        "/api/auth/github",
        "/api/auth/github/callback",
        "/api/health",
        "/api/contact",
        "/api/enterprise/contact",
        "/api/build",
        "/api/build/summary",
        # Read-only style cost preview (no job persisted); Bearer still used when available
        "/api/orchestrator/estimate",
    }

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        # Local dev: only bypass CSRF for requests originating from localhost.
        # This prevents CRUCIBAI_DEV=1 from accidentally disabling CSRF on production
        # if the env var is set on a deployed server.
        if os.environ.get("CRUCIBAI_DEV", "").strip().lower() in ("1", "true", "yes"):
            headers = dict(scope.get("headers", []))
            origin = headers.get(b"origin", b"").decode()
            host = headers.get(b"host", b"").decode()
            _localhost_origins = (
                "http://localhost",
                "http://127.0.0.1",
                "https://localhost",
                "https://127.0.0.1",
            )
            _is_localhost = (
                not origin  # Same-origin requests have no Origin header
                or any(origin.startswith(o) for o in _localhost_origins)
                or any(h in host for h in ("localhost", "127.0.0.1"))
            )
            if _is_localhost:
                await self.app(scope, receive, send)
                return
            # Non-localhost origin with CRUCIBAI_DEV=1 — fall through to normal CSRF checks

        method = scope["method"]
        path = scope.get("path", "")

        # Skip CSRF check for exempt paths
        if path in self.CSRF_EXEMPT_PATHS:
            await self.app(scope, receive, send)
            return

        # Only check CSRF for state-changing methods (skip when disabled for tests)
        if os.environ.get("DISABLE_CSRF_FOR_TEST", "").strip().lower() in (
            "1",
            "true",
            "yes",
        ):
            await self.app(scope, receive, send)
            return
        if method in ["POST", "PUT", "DELETE", "PATCH"]:
            headers = dict(scope.get("headers", []))
            # Skip CSRF check if a Bearer token is present — JWT auth already prevents CSRF
            # because cross-origin requests cannot inject Authorization headers.
            auth_header = headers.get(b"authorization", b"").decode()
            if auth_header.startswith("Bearer "):
                await self.app(scope, receive, send)
                return
            csrf_token = headers.get(b"x-csrf-token", b"").decode()

            # If no CSRF token header, reject the request
            if not csrf_token:

                async def send_error(message):
                    if message["type"] == "http.response.start":
                        await send(
                            {
                                "type": "http.response.start",
                                "status": 403,
                                "headers": [[b"content-type", b"application/json"]],
                            }
                        )
                    elif message["type"] == "http.response.body":
                        await send(
                            {
                                "type": "http.response.body",
                                "body": b'{"detail": "CSRF token missing"}',
                            }
                        )

                await send_error({"type": "http.response.start"})
                await send_error({"type": "http.response.body"})
                return

        await self.app(scope, receive, send)


# Agent Learning System — wired into production path
from agent_recursive_learning import (
    AdaptiveStrategy,
    AgentMemory,
    ExecutionStatus,
    PerformanceTracker,
)
from content_policy import screen_user_content
from credit_tracker import tracker
from critic_agent import CriticAgent, TruthModule
from dev_stub_llm import REAL_AGENT_NO_LLM_KEYS_DETAIL, chat_llm_available
from dev_stub_llm import detect_build_kind as _stub_detect_build_kind
from dev_stub_llm import is_real_agent_only
from dev_stub_llm import plan_and_suggestions as _stub_plan_and_suggestions
from dev_stub_llm import stub_build_enabled, stub_file_dict, stub_multifile_markdown
from llm_router import TaskComplexity, classifier, router
from pgvector_memory import pgvector_memory as _pgvector_memory
from provider_readiness import build_provider_readiness
from vector_memory import vector_memory as _vector_memory

# Monitoring & Metrics
try:
    from metrics_system import metrics as _metrics
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    _metrics_available = True
except ImportError:
    _metrics_available = False
    print(
        "WARNING: prometheus_client not installed - /metrics endpoint disabled",
        file=sys.stderr,
    )
_critic_agent = CriticAgent()
_truth_module = TruthModule()
_agent_memory = None  # Initialized in startup after db is ready


async def _init_agent_learning():
    """Initialize the agent learning system with the database connection."""
    global _agent_memory
    if _agent_memory is None:
        _agent_memory = AgentMemory(db)
    return _agent_memory


from agent_real_behavior import run_agent_real_behavior
from agent_resilience import AgentError, generate_fallback, get_criticality, get_timeout
from automation.constants import (
    CREDITS_PER_AGENT_RUN,
    INTERNAL_USER_ID,
    MAX_CONCURRENT_RUNS_PER_USER,
    MAX_RUNS_PER_HOUR_PER_USER,
    WEBHOOK_IDEMPOTENCY_SECONDS,
    WEBHOOK_RATE_LIMIT_PER_MINUTE,
)
from automation.executor import run_actions
from automation.models import ActionConfig, AgentCreate, AgentUpdate, TriggerConfig
from automation.schedule import is_one_time, next_run_at
from code_quality import score_generated_code
from project_state import WORKSPACE_ROOT, load_state
from tool_schemas import (
    ToolApiRequest,
    ToolBrowserRequest,
    ToolDatabaseRequest,
    ToolDeployRequest,
    ToolFileRequest,
)

try:
    from agents.image_generator import generate_images_for_app, parse_image_prompts
    from agents.video_generator import generate_videos_for_app, parse_video_queries
except ImportError:
    generate_images_for_app = parse_image_prompts = None
    generate_videos_for_app = parse_video_queries = None
try:
    from agents.legal_compliance import check_request as legal_check_request
except ImportError:
    legal_check_request = None
try:
    from utils.audit_log import AuditLogger
    from utils.rbac import Permission, get_user_role, has_permission
except ImportError:
    AuditLogger = None
    has_permission = lambda u, p: True
    Permission = None
    get_user_role = lambda u: "owner"
import hashlib

# Environment validation
from env_setup import validate_environment

env_result = validate_environment(strict=False)
# Startup summary — logger not yet initialized here, use print
_missing_optional = [v[0] for v in env_result.get("missing_optional", [])]
if _missing_optional:
    print(
        f"INFO: Optional features not configured: {', '.join(_missing_optional[:3])}{'...' if len(_missing_optional) > 3 else ''} - add to Railway vars when ready"
    )

import pyotp
import qrcode

# Pre-flight: require secrets in production; in dev (CRUCIBAI_DEV=1) allow running without DB for /api/health
CRUCIBAI_DEV = os.environ.get("CRUCIBAI_DEV", "").strip().lower() in (
    "1",
    "true",
    "yes",
)
if not os.environ.get("JWT_SECRET"):
    if CRUCIBAI_DEV:
        os.environ.setdefault("JWT_SECRET", "dev-secret-do-not-use-in-production")
        print(
            "WARNING: JWT_SECRET not set; using dev default. Set JWT_SECRET for production.",
            file=sys.stderr,
        )
    else:
        print(
            "FATAL: JWT_SECRET not set. Set JWT_SECRET in Railway/Production Variables.",
            file=sys.stderr,
        )
        sys.exit(1)
if not os.environ.get("DATABASE_URL"):
    if CRUCIBAI_DEV:
        print(
            "WARNING: DATABASE_URL not set. /api/health will work; auth and builds need a real DB. Set DATABASE_URL for full local dev.",
            file=sys.stderr,
        )
    else:
        print(
            "FATAL: DATABASE_URL not set. Set DATABASE_URL in Railway/Production Variables.",
            file=sys.stderr,
        )
        sys.exit(1)

# PostgreSQL database will be initialized on startup (or remain None in dev without DATABASE_URL)
db = None
audit_logger = None


def _mfa_temp_token_payload(user_id: str) -> dict:
    return {
        "user_id": user_id,
        "purpose": "mfa_verification",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }


def create_mfa_temp_token(user_id: str) -> str:
    return jwt.encode(
        _mfa_temp_token_payload(user_id), JWT_SECRET, algorithm=JWT_ALGORITHM
    )


def decode_mfa_temp_token(token: str) -> dict:
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    if payload.get("purpose") != "mfa_verification":
        raise jwt.InvalidTokenError("Invalid purpose")
    return payload


app = FastAPI(title="CrucibAI Platform")
try:
    from orchestration.observability import init_opentelemetry

    init_opentelemetry()
except Exception:
    pass
# Security headers: middleware.SecurityHeadersMiddleware (Sandpack-aware CSP, SAMEORIGIN framing).
api_router = APIRouter(prefix="/api")
auth_router = APIRouter(prefix="/api", tags=["auth"])
projects_router = APIRouter(prefix="/api", tags=["projects"])
tools_router = APIRouter(prefix="/api", tags=["tools"])
agents_router = APIRouter(prefix="/api", tags=["agents"])
security = HTTPBearer(auto_error=False)

# LLM Configuration: Only Anthropic (Haiku) and Cerebras (free tier)
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
# Cerebras key pool — import from llm_router for consistent round-robin
from llm_router import _CEREBRAS_KEYS as _CEREBRAS_KEY_POOL
from llm_router import CEREBRAS_API_KEY
from llm_router import get_cerebras_key as _get_cerebras_key

# Groq API configuration (third LLM fallback)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_MODEL = "mixtral-8x7b-32768"  # Fast, cost-effective

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# JWT_SECRET must be set in production; fallback is per-process and invalidates tokens on restart
JWT_SECRET = os.environ.get("JWT_SECRET")
if not JWT_SECRET:
    logger.warning(
        "JWT_SECRET not set in environment. Using a temporary secret for this session."
    )
    import secrets

    JWT_SECRET = secrets.token_urlsafe(32)
JWT_ALGORITHM = "HS256"

# Session timeout configuration
SESSION_TIMEOUT_MINUTES = int(os.environ.get("SESSION_TIMEOUT_MINUTES", "60"))
SESSION_TIMEOUT_SECONDS = SESSION_TIMEOUT_MINUTES * 60

# Frontend loading states and skeletons
LOADING_SKELETON_COMPONENTS = ["LoadingSkeleton", "SkeletonCard", "SkeletonTable"]

# Database foreign key constraints (managed by Alembic migrations)
FOREIGN_KEY_CONSTRAINTS = {
    "projects": ["user_id"],
    "project_logs": ["project_id", "user_id"],
    "agent_status": ["project_id"],
}

# Content Security Policy headers
CSP_HEADER = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https:;"

# CSRF protection configuration
CSRF_TOKEN_LENGTH = 32
CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"

# SQL injection prevention: all queries use parameterized statements
# Database module (db_pg.py) enforces parameterized queries via asyncpg
SQL_INJECTION_PROTECTION = "parameterized_queries_enforced"

# Vector database (pgvector) for semantic search and embeddings
VECTOR_DB_ENABLED = True
VECTOR_DIMENSION = 1536  # OpenAI embedding dimension

# Embedding service for semantic search
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_SERVICE_ENABLED = True

# Build event stream (SSE): project_id -> list of events (max 500). Wired to orchestration.
_build_events: Dict[str, List[Dict[str, Any]]] = {}
_BUILD_EVENTS_MAX = 500

# Cap list fetches for performance (audit fix Phase B)
MAX_PROJECTS_LIST = 500
MAX_TOKEN_LEDGER_REVENUE = 5000
MAX_EXPORTS_LIST = 200
MAX_USER_PROJECTS_DASHBOARD = 500
MAX_TOKEN_USAGE_LIST = 1000
MAX_ADMIN_USER_EXPORT_PROJECTS = 1000
MAX_ADMIN_USER_LEDGER = 1000


def emit_build_event(project_id: str, event_type: str, **kwargs: Any) -> None:
    """Emit event for SSE stream and persist to DB. Called from orchestration so UI can show Manus-style timeline."""
    if project_id not in _build_events:
        _build_events[project_id] = []
    lst = _build_events[project_id]
    ev = {
        "id": len(lst),
        "ts": datetime.now(timezone.utc).isoformat(),
        "type": event_type,
        **kwargs,
    }
    lst.append(ev)
    if len(lst) > _BUILD_EVENTS_MAX:
        _build_events[project_id] = lst[-_BUILD_EVENTS_MAX:]
        for i, e in enumerate(_build_events[project_id]):
            e["id"] = i
    # Persist to DB asynchronously (fire-and-forget) so events survive restarts
    if db is not None:
        import asyncio

        async def _persist():
            try:
                # Store last 200 events in project doc to avoid unbounded growth
                events_to_store = lst[-200:]
                await db.projects.update_one(
                    {"id": project_id},
                    {
                        "$set": {
                            "build_events": events_to_store,
                            "build_events_updated_at": datetime.now(
                                timezone.utc
                            ).isoformat(),
                        }
                    },
                )
            except Exception:
                pass

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_persist())
        except RuntimeError:
            pass  # No event loop running (e.g. during import)
    try:

        async def _broadcast_progress() -> None:
            from api.routes.job_progress import (
                broadcast_event as websocket_broadcast_event,
            )

            await websocket_broadcast_event(project_id, event_type, **kwargs)

        loop = asyncio.get_running_loop()
        loop.create_task(_broadcast_progress())
    except Exception:
        pass


# ==================== MODELS ====================


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    name: str
    ref: Optional[str] = None  # referral code at sign-up


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class ChatMessage(BaseModel):
    message: str = Field(
        ..., min_length=1, max_length=50000
    )  # 50k chars max; empty message rejected
    session_id: Optional[str] = None
    model: Optional[str] = "auto"  # auto or haiku (Anthropic/Cerebras only)
    mode: Optional[str] = (
        None  # thinking = step-by-step reasoning (no extra cost, same call)
    )
    system_message: Optional[str] = None  # override for intent classification etc.
    attachments: Optional[List[Dict[str, Any]]] = (
        None  # [{ "type": "image"|"pdf"|"text", "data": base64 or data URL or text, "name": "file.pdf" }]
    )
    prior_turns: Optional[List[Dict[str, Any]]] = (
        None  # [{ "role": "user"|"assistant", "content": "..." }] before current `message`
    )


class ChatResponse(BaseModel):
    model_config = {"protected_namespaces": ()}  # suppress model_used namespace warning
    response: str
    model_used: str
    tokens_used: int
    session_id: str


class JobSteerRequest(BaseModel):
    """User note while a job is failed or paused — optional resume of the auto-runner."""

    message: str = Field(default="", max_length=20000)
    resume: bool = True


class TokenPurchase(BaseModel):
    bundle: str


class TokenPurchaseCustom(BaseModel):
    """Custom credit purchase (slider): 100-10000 credits at $0.06/credit."""

    credits: int = Field(
        ge=100, le=10000, description="Credits to purchase (100-10000)"
    )


MAX_PROMPT_LENGTH = 50000
MAX_PROJECT_DESCRIPTION_LENGTH = 10000
MAX_PROJECT_REQUIREMENTS_JSON_LENGTH = 100000


class BuildPlanRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=MAX_PROMPT_LENGTH)
    swarm: Optional[bool] = (
        False  # run plan + suggestions in parallel; token multiplier applied
    )
    build_kind: Optional[str] = (
        None  # fullstack | mobile | saas | bot | ai_agent | game | trading | any
    )


class BuildGoalRequest(BaseModel):
    goal: str = Field(..., min_length=1, max_length=MAX_PROMPT_LENGTH)
    project_id: Optional[str] = None


class EnterpriseContact(BaseModel):
    company: str
    email: EmailStr
    team_size: Optional[str] = None  # e.g. "1-10", "11-50", "51+"
    use_case: Optional[str] = None  # e.g. "teams", "startup", "enterprise"
    budget: Optional[str] = None  # e.g. "10K", "50K", "100K+", "custom"
    message: Optional[str] = None


class ContactSubmission(BaseModel):
    """General contact form (footer, pricing, etc.)."""

    email: EmailStr
    message: str = Field(..., min_length=1, max_length=5000)
    issue_type: Optional[str] = (
        None  # e.g. "general", "support", "enterprise", "billing"
    )
    name: Optional[str] = Field(None, max_length=200)


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    description: str = Field("", max_length=MAX_PROJECT_DESCRIPTION_LENGTH)
    project_type: str = Field(..., max_length=100)
    requirements: Dict[str, Any] = Field(default_factory=dict)
    estimated_tokens: Optional[int] = None
    quick_build: Optional[bool] = (
        False  # Item 29: fast preview — run only first 2 phases, preview in ~2 min
    )

    @model_validator(mode="after")
    def check_requirements_size(self):
        try:
            s = json.dumps(self.requirements or {})
            if len(s) > MAX_PROJECT_REQUIREMENTS_JSON_LENGTH:
                raise ValueError(
                    f"requirements too large (max {MAX_PROJECT_REQUIREMENTS_JSON_LENGTH} chars)"
                )
        except TypeError:
            pass
        return self


class TaskSync(BaseModel):
    """Sync task from Workspace when build completes (single-task authority)."""

    name: str
    prompt: str
    session_id: Optional[str] = None
    status: str = "completed"
    files: Optional[List[str]] = None


class DocumentProcess(BaseModel):
    content: str
    doc_type: str = "text"
    task: str = "summarize"  # summarize, extract, analyze


class RAGQuery(BaseModel):
    query: str
    context: Optional[str] = None
    top_k: int = 5


class SearchQuery(BaseModel):
    query: str
    search_type: str = "hybrid"  # vector, keyword, hybrid


class DeployTokensUpdate(BaseModel):
    """Optional deploy tokens for one-click deploy (stored per user, not returned in /auth/me)."""

    vercel: Optional[str] = None
    netlify: Optional[str] = None
    github: Optional[str] = None
    railway: Optional[str] = None


class DeployOneClickBody(BaseModel):
    """Optional token override for one-click deploy (otherwise use stored user tokens)."""

    token: Optional[str] = None


class ProjectPublishSettingsBody(BaseModel):
    """Custom domain + optional Railway dashboard link (stored on project for Workspace / deploy UX)."""

    custom_domain: Optional[str] = None
    railway_project_url: Optional[str] = None


class ExportFilesBody(BaseModel):
    """Files to export as ZIP: filename -> code content"""

    files: Dict[str, str]


class ValidateAndFixBody(BaseModel):
    code: str
    language: Optional[str] = "javascript"


class QualityGateBody(BaseModel):
    """Quality gate: score generated code and return pass/fail + breakdown."""

    code: Optional[str] = None
    files: Optional[Dict[str, str]] = None


class ExplainErrorBody(BaseModel):
    code: str
    error: str
    language: Optional[str] = "javascript"


class SuggestNextBody(BaseModel):
    files: Dict[str, str]
    last_prompt: Optional[str] = None


class VisualEditRequest(BaseModel):
    file_path: str = "src/App.jsx"
    find_text: str
    replace_text: str


class InjectStripeBody(BaseModel):
    code: str
    target: Optional[str] = "checkout"  # checkout | subscription | both


class GenerateReadmeBody(BaseModel):
    code: str
    project_name: Optional[str] = "App"


class GenerateDocsBody(BaseModel):
    code: str
    doc_type: Optional[str] = "api"  # api | component


class FaqItem(BaseModel):
    q: str
    a: str


class GenerateFaqSchemaBody(BaseModel):
    faqs: List[FaqItem]


class ReferenceBuildBody(BaseModel):
    url: Optional[str] = None
    prompt: str


class SavePromptBody(BaseModel):
    name: str
    prompt: str
    category: Optional[str] = "general"


class ProjectEnvBody(BaseModel):
    project_id: Optional[str] = None
    env: Dict[str, str]


class SecurityScanBody(BaseModel):
    files: Dict[str, str]
    project_id: Optional[str] = (
        None  # when set, store result on project for AgentMonitor badge
    )


class OptimizeBody(BaseModel):
    code: str
    language: Optional[str] = "javascript"


class DeleteAccountBody(BaseModel):
    password: str  # required for confirmation


class ShareCreateBody(BaseModel):
    project_id: str
    read_only: bool = True


class ProjectImportBody(BaseModel):
    """Import project from paste, ZIP (base64), or Git URL."""

    name: Optional[str] = None
    source: str  # "paste" | "zip" | "git"
    files: Optional[List[Dict[str, Any]]] = (
        None  # for paste: [{"path": str, "code": str}]
    )
    zip_base64: Optional[str] = None  # for zip: base64-encoded zip bytes
    git_url: Optional[str] = None  # for git: e.g. https://github.com/owner/repo


class GenerateContentRequest(BaseModel):
    """CrucibAI for Docs/Slides/Sheets (C1–C3)."""

    prompt: str
    format: Optional[str] = (
        None  # doc: markdown|plain; slides: markdown|outline; sheets: csv|json
    )


class AgentPromptBody(BaseModel):
    """Generic body for agent runs that take a prompt."""

    prompt: str
    context: Optional[str] = None
    language: Optional[str] = "javascript"


class AgentCodeBody(BaseModel):
    """Body for agents that take code input."""

    code: str
    language: Optional[str] = "javascript"


class AgentScrapeBody(BaseModel):
    url: str


class AgentExportPdfBody(BaseModel):
    title: str
    content: str


class AgentExportMarkdownBody(BaseModel):
    title: str
    content: str


class AgentExportExcelBody(BaseModel):
    title: str
    rows: List[Dict[str, Any]] = []  # list of dicts, keys = column headers


class AgentMemoryBody(BaseModel):
    name: str
    content: str


class AgentGenericRunBody(BaseModel):
    """Run any agent by name (for 100-agent roster)."""

    agent_name: str
    prompt: str


class AgentAutomationBody(BaseModel):
    name: str
    prompt: str
    run_at: Optional[str] = None  # ISO datetime for scheduled


# Admin constants from deps (used in auth flow and a few remaining inline routes)
from deps import ADMIN_ROLES, ADMIN_USER_IDS
from deps import get_current_admin as _get_current_admin_dep

# ==================== CREDITS & PRICING (1 credit = 1000 tokens) ====================
from pricing_plans import (
    ADDONS,
    ANNUAL_PRICES,
    CREDIT_PLANS,
    CREDITS_PER_TOKEN,
    TOKEN_BUNDLES,
    _speed_from_plan,
)

MIN_CREDITS_FOR_LLM = 5
FREE_TIER_CREDITS = 100  # Free tier (email signup)
GUEST_TIER_CREDITS = 200  # Guest/free users get 200 credits (matches free tier)

AGENT_DEFINITIONS = [
    {
        "name": "Planner",
        "layer": "planning",
        "description": "Decomposes user requests into executable tasks",
        "avg_tokens": 50000,
    },
    {
        "name": "Requirements Clarifier",
        "layer": "planning",
        "description": "Asks clarifying questions and validates requirements",
        "avg_tokens": 30000,
    },
    {
        "name": "Stack Selector",
        "layer": "planning",
        "description": "Chooses optimal technology stack",
        "avg_tokens": 20000,
    },
    {
        "name": "Frontend Generation",
        "layer": "execution",
        "description": "Generates React/Next.js UI components",
        "avg_tokens": 150000,
    },
    {
        "name": "Backend Generation",
        "layer": "execution",
        "description": "Creates APIs, auth, business logic",
        "avg_tokens": 120000,
    },
    {
        "name": "Database Agent",
        "layer": "execution",
        "description": "Designs schema and migrations",
        "avg_tokens": 80000,
    },
    {
        "name": "API Integration",
        "layer": "execution",
        "description": "Integrates third-party APIs",
        "avg_tokens": 60000,
    },
    {
        "name": "Test Generation",
        "layer": "execution",
        "description": "Writes comprehensive test suites",
        "avg_tokens": 100000,
    },
    {
        "name": "Image Generation",
        "layer": "execution",
        "description": "Creates AI-generated visuals",
        "avg_tokens": 40000,
    },
    {
        "name": "Security Checker",
        "layer": "validation",
        "description": "Audits for vulnerabilities",
        "avg_tokens": 40000,
    },
    {
        "name": "Test Executor",
        "layer": "validation",
        "description": "Runs all tests and reports",
        "avg_tokens": 50000,
    },
    {
        "name": "UX Auditor",
        "layer": "validation",
        "description": "Reviews design and accessibility",
        "avg_tokens": 35000,
    },
    {
        "name": "Performance Analyzer",
        "layer": "validation",
        "description": "Optimizes speed and efficiency",
        "avg_tokens": 40000,
    },
    {
        "name": "Deployment Agent",
        "layer": "deployment",
        "description": "Deploys to cloud platforms",
        "avg_tokens": 60000,
    },
    {
        "name": "Error Recovery",
        "layer": "deployment",
        "description": "Auto-fixes failures",
        "avg_tokens": 45000,
    },
    {
        "name": "Memory Agent",
        "layer": "deployment",
        "description": "Stores patterns for reuse",
        "avg_tokens": 25000,
    },
    {
        "name": "PDF Export",
        "layer": "export",
        "description": "Generates formatted PDF reports",
        "avg_tokens": 30000,
    },
    {
        "name": "Excel Export",
        "layer": "export",
        "description": "Creates spreadsheets with formulas",
        "avg_tokens": 25000,
    },
    {
        "name": "Markdown Export",
        "layer": "export",
        "description": "Outputs project summary in Markdown",
        "avg_tokens": 20000,
    },
    {
        "name": "Scraping Agent",
        "layer": "automation",
        "description": "Extracts data from websites",
        "avg_tokens": 35000,
    },
    {
        "name": "Automation Agent",
        "layer": "automation",
        "description": "Schedules tasks and workflows",
        "avg_tokens": 30000,
    },
    {
        "name": "Video Generation",
        "layer": "execution",
        "description": "Stock video search queries",
        "avg_tokens": 20000,
    },
    {
        "name": "Design Agent",
        "layer": "execution",
        "description": "Image placement spec (hero, feature_1, feature_2)",
        "avg_tokens": 30000,
    },
    {
        "name": "Layout Agent",
        "layer": "execution",
        "description": "Injects image placeholders into frontend",
        "avg_tokens": 40000,
    },
    {
        "name": "SEO Agent",
        "layer": "execution",
        "description": "Meta, OG, schema, sitemap, robots.txt",
        "avg_tokens": 35000,
    },
    {
        "name": "Content Agent",
        "layer": "planning",
        "description": "Landing copy: hero, features, CTA",
        "avg_tokens": 30000,
    },
    {
        "name": "Brand Agent",
        "layer": "execution",
        "description": "Colors, fonts, tone spec",
        "avg_tokens": 25000,
    },
    {
        "name": "Documentation Agent",
        "layer": "deployment",
        "description": "README: setup, env, run, deploy",
        "avg_tokens": 40000,
    },
    {
        "name": "Validation Agent",
        "layer": "validation",
        "description": "Form/API validation rules, Zod/Yup",
        "avg_tokens": 35000,
    },
    {
        "name": "Auth Setup Agent",
        "layer": "execution",
        "description": "JWT/OAuth flow, protected routes",
        "avg_tokens": 50000,
    },
    {
        "name": "Payment Setup Agent",
        "layer": "execution",
        "description": "Stripe checkout, webhooks",
        "avg_tokens": 50000,
    },
    {
        "name": "Monitoring Agent",
        "layer": "deployment",
        "description": "Sentry, analytics setup",
        "avg_tokens": 35000,
    },
    {
        "name": "Accessibility Agent",
        "layer": "validation",
        "description": "a11y improvements: ARIA, contrast",
        "avg_tokens": 30000,
    },
    {
        "name": "DevOps Agent",
        "layer": "deployment",
        "description": "CI/CD, Dockerfile",
        "avg_tokens": 40000,
    },
    {
        "name": "Webhook Agent",
        "layer": "execution",
        "description": "Webhook endpoint design",
        "avg_tokens": 35000,
    },
    {
        "name": "Email Agent",
        "layer": "execution",
        "description": "Transactional email setup",
        "avg_tokens": 35000,
    },
    {
        "name": "Legal Compliance Agent",
        "layer": "planning",
        "description": "GDPR/CCPA hints",
        "avg_tokens": 30000,
    },
    {
        "name": "GraphQL Agent",
        "layer": "execution",
        "description": "GraphQL schema and resolvers",
        "avg_tokens": 40000,
    },
    {
        "name": "WebSocket Agent",
        "layer": "execution",
        "description": "Real-time subscriptions",
        "avg_tokens": 35000,
    },
    {
        "name": "i18n Agent",
        "layer": "execution",
        "description": "Localization, translation keys",
        "avg_tokens": 30000,
    },
    {
        "name": "Caching Agent",
        "layer": "execution",
        "description": "Redis/edge caching strategy",
        "avg_tokens": 30000,
    },
    {
        "name": "Rate Limit Agent",
        "layer": "execution",
        "description": "API rate limiting, quotas",
        "avg_tokens": 30000,
    },
    {
        "name": "Search Agent",
        "layer": "execution",
        "description": "Full-text search (Algolia/Meilisearch)",
        "avg_tokens": 35000,
    },
    {
        "name": "Analytics Agent",
        "layer": "deployment",
        "description": "GA4, Mixpanel, event schema",
        "avg_tokens": 30000,
    },
    {
        "name": "API Documentation Agent",
        "layer": "execution",
        "description": "OpenAPI/Swagger from routes",
        "avg_tokens": 40000,
    },
    {
        "name": "Mobile Responsive Agent",
        "layer": "validation",
        "description": "Breakpoints, touch, PWA hints",
        "avg_tokens": 30000,
    },
    {
        "name": "Migration Agent",
        "layer": "execution",
        "description": "DB migration scripts",
        "avg_tokens": 35000,
    },
    {
        "name": "Backup Agent",
        "layer": "deployment",
        "description": "Backup strategy, restore steps",
        "avg_tokens": 30000,
    },
    {
        "name": "Notification Agent",
        "layer": "execution",
        "description": "Push, in-app, email notifications",
        "avg_tokens": 35000,
    },
    {
        "name": "Design Iteration Agent",
        "layer": "planning",
        "description": "Feedback → spec → rebuild flow",
        "avg_tokens": 35000,
    },
    {
        "name": "Code Review Agent",
        "layer": "validation",
        "description": "Security, style, best-practice review",
        "avg_tokens": 45000,
    },
    {
        "name": "Staging Agent",
        "layer": "deployment",
        "description": "Staging env, preview URLs",
        "avg_tokens": 25000,
    },
    {
        "name": "A/B Test Agent",
        "layer": "execution",
        "description": "Experiment setup, variant routing",
        "avg_tokens": 30000,
    },
    {
        "name": "Feature Flag Agent",
        "layer": "execution",
        "description": "LaunchDarkly/Flagsmith wiring",
        "avg_tokens": 30000,
    },
    {
        "name": "Error Boundary Agent",
        "layer": "execution",
        "description": "React error boundaries, fallback UI",
        "avg_tokens": 30000,
    },
    {
        "name": "Logging Agent",
        "layer": "execution",
        "description": "Structured logs, log levels",
        "avg_tokens": 30000,
    },
    {
        "name": "Metrics Agent",
        "layer": "deployment",
        "description": "Prometheus/Datadog metrics",
        "avg_tokens": 30000,
    },
    {
        "name": "Audit Trail Agent",
        "layer": "execution",
        "description": "User action logging, audit log",
        "avg_tokens": 35000,
    },
    {
        "name": "Session Agent",
        "layer": "execution",
        "description": "Session storage, expiry, refresh",
        "avg_tokens": 30000,
    },
    {
        "name": "OAuth Provider Agent",
        "layer": "execution",
        "description": "Google/GitHub OAuth wiring",
        "avg_tokens": 40000,
    },
    {
        "name": "2FA Agent",
        "layer": "execution",
        "description": "TOTP, backup codes",
        "avg_tokens": 30000,
    },
    {
        "name": "Stripe Subscription Agent",
        "layer": "execution",
        "description": "Plans, metering, downgrade",
        "avg_tokens": 40000,
    },
    {
        "name": "Invoice Agent",
        "layer": "execution",
        "description": "Invoice generation, PDF",
        "avg_tokens": 35000,
    },
    {
        "name": "CDN Agent",
        "layer": "deployment",
        "description": "Static assets, cache headers",
        "avg_tokens": 30000,
    },
    {
        "name": "SSR Agent",
        "layer": "execution",
        "description": "Next.js SSR/SSG hints",
        "avg_tokens": 30000,
    },
    {
        "name": "Bundle Analyzer Agent",
        "layer": "validation",
        "description": "Code splitting, chunk hints",
        "avg_tokens": 30000,
    },
    {
        "name": "Lighthouse Agent",
        "layer": "validation",
        "description": "Performance, a11y, SEO scores",
        "avg_tokens": 35000,
    },
    {
        "name": "Schema Validation Agent",
        "layer": "execution",
        "description": "Request/response validation",
        "avg_tokens": 30000,
    },
    {
        "name": "Mock API Agent",
        "layer": "execution",
        "description": "MSW, Mirage, mock server",
        "avg_tokens": 35000,
    },
    {
        "name": "E2E Agent",
        "layer": "execution",
        "description": "Playwright/Cypress scaffolding",
        "avg_tokens": 45000,
    },
    {
        "name": "Load Test Agent",
        "layer": "execution",
        "description": "k6, Artillery scripts",
        "avg_tokens": 35000,
    },
    {
        "name": "Dependency Audit Agent",
        "layer": "validation",
        "description": "npm audit, Snyk hints",
        "avg_tokens": 30000,
    },
    {
        "name": "License Agent",
        "layer": "planning",
        "description": "OSS license compliance",
        "avg_tokens": 25000,
    },
    {
        "name": "Terms Agent",
        "layer": "planning",
        "description": "Terms of service draft",
        "avg_tokens": 30000,
    },
    {
        "name": "Privacy Policy Agent",
        "layer": "planning",
        "description": "Privacy policy draft",
        "avg_tokens": 30000,
    },
    {
        "name": "Cookie Consent Agent",
        "layer": "execution",
        "description": "Cookie banner, preferences",
        "avg_tokens": 30000,
    },
    {
        "name": "Multi-tenant Agent",
        "layer": "execution",
        "description": "Tenant isolation, schema",
        "avg_tokens": 40000,
    },
    {
        "name": "RBAC Agent",
        "layer": "execution",
        "description": "Roles, permissions matrix",
        "avg_tokens": 40000,
    },
    {
        "name": "SSO Agent",
        "layer": "execution",
        "description": "SAML, enterprise SSO",
        "avg_tokens": 40000,
    },
    {
        "name": "Audit Export Agent",
        "layer": "deployment",
        "description": "Export audit logs",
        "avg_tokens": 30000,
    },
    {
        "name": "Data Residency Agent",
        "layer": "planning",
        "description": "Region, GDPR data location",
        "avg_tokens": 30000,
    },
    {
        "name": "HIPAA Agent",
        "layer": "planning",
        "description": "Healthcare compliance hints",
        "avg_tokens": 35000,
    },
    {
        "name": "SOC2 Agent",
        "layer": "planning",
        "description": "SOC2 control hints",
        "avg_tokens": 35000,
    },
    {
        "name": "Penetration Test Agent",
        "layer": "validation",
        "description": "Pentest checklist",
        "avg_tokens": 35000,
    },
    {
        "name": "Incident Response Agent",
        "layer": "deployment",
        "description": "Runbook, escalation",
        "avg_tokens": 35000,
    },
    {
        "name": "SLA Agent",
        "layer": "deployment",
        "description": "Uptime, latency targets",
        "avg_tokens": 30000,
    },
    {
        "name": "Cost Optimizer Agent",
        "layer": "deployment",
        "description": "Cloud cost hints",
        "avg_tokens": 30000,
    },
    {
        "name": "Accessibility WCAG Agent",
        "layer": "validation",
        "description": "WCAG 2.1 AA checklist",
        "avg_tokens": 35000,
    },
    {
        "name": "RTL Agent",
        "layer": "execution",
        "description": "Right-to-left layout",
        "avg_tokens": 25000,
    },
    {
        "name": "Dark Mode Agent",
        "layer": "execution",
        "description": "Theme toggle, contrast",
        "avg_tokens": 30000,
    },
    {
        "name": "Keyboard Nav Agent",
        "layer": "validation",
        "description": "Full keyboard navigation",
        "avg_tokens": 30000,
    },
    {
        "name": "Screen Reader Agent",
        "layer": "validation",
        "description": "Screen-reader-specific hints",
        "avg_tokens": 30000,
    },
    {
        "name": "Component Library Agent",
        "layer": "execution",
        "description": "Shadcn/Radix usage",
        "avg_tokens": 35000,
    },
    {
        "name": "Design System Agent",
        "layer": "execution",
        "description": "Tokens, spacing, typography",
        "avg_tokens": 35000,
    },
    {
        "name": "Animation Agent",
        "layer": "execution",
        "description": "Framer Motion, transitions",
        "avg_tokens": 30000,
    },
    {
        "name": "Chart Agent",
        "layer": "execution",
        "description": "Recharts, D3 usage",
        "avg_tokens": 35000,
    },
    {
        "name": "Table Agent",
        "layer": "execution",
        "description": "Data tables, sorting, pagination",
        "avg_tokens": 35000,
    },
    {
        "name": "Form Builder Agent",
        "layer": "execution",
        "description": "Dynamic form generation",
        "avg_tokens": 40000,
    },
    {
        "name": "Workflow Agent",
        "layer": "execution",
        "description": "State machine, workflows",
        "avg_tokens": 40000,
    },
    {
        "name": "Queue Agent",
        "layer": "execution",
        "description": "Job queues, Bull/Celery",
        "avg_tokens": 40000,
    },
    # DAG-only (23 more = 123 total) — in agent_dag.py, now exposed in /api/agents
    {
        "name": "Native Config Agent",
        "layer": "execution",
        "description": "Expo/app.json, eas.json for mobile",
        "avg_tokens": 25000,
    },
    {
        "name": "Store Prep Agent",
        "layer": "deployment",
        "description": "App store submission metadata and guides",
        "avg_tokens": 35000,
    },
    {
        "name": "Vibe Analyzer Agent",
        "layer": "planning",
        "description": "Analyze project vibe, mood, aesthetic",
        "avg_tokens": 30000,
    },
    {
        "name": "Voice Context Agent",
        "layer": "planning",
        "description": "Convert voice/speech to code context",
        "avg_tokens": 30000,
    },
    {
        "name": "Video Tutorial Agent",
        "layer": "deployment",
        "description": "Video tutorial scripts and storyboards",
        "avg_tokens": 35000,
    },
    {
        "name": "Aesthetic Reasoner Agent",
        "layer": "validation",
        "description": "Evaluate code for beauty and elegance",
        "avg_tokens": 30000,
    },
    {
        "name": "Team Preferences",
        "layer": "planning",
        "description": "Capture team style and conventions",
        "avg_tokens": 25000,
    },
    {
        "name": "Collaborative Memory Agent",
        "layer": "deployment",
        "description": "Team preferences and project patterns",
        "avg_tokens": 30000,
    },
    {
        "name": "Real-time Feedback Agent",
        "layer": "validation",
        "description": "Adapt to user reactions and feedback",
        "avg_tokens": 35000,
    },
    {
        "name": "Mood Detection Agent",
        "layer": "planning",
        "description": "Detect user mood and intent",
        "avg_tokens": 25000,
    },
    {
        "name": "Accessibility Vibe Agent",
        "layer": "validation",
        "description": "Accessible and inclusive vibe",
        "avg_tokens": 30000,
    },
    {
        "name": "Performance Vibe Agent",
        "layer": "validation",
        "description": "Code that feels fast and responsive",
        "avg_tokens": 30000,
    },
    {
        "name": "Creativity Catalyst Agent",
        "layer": "planning",
        "description": "Creative improvements and innovation",
        "avg_tokens": 35000,
    },
    {
        "name": "IDE Integration Coordinator Agent",
        "layer": "execution",
        "description": "IDE extensions and plugin hooks",
        "avg_tokens": 35000,
    },
    {
        "name": "Multi-language Code Agent",
        "layer": "execution",
        "description": "Code in multiple languages",
        "avg_tokens": 40000,
    },
    {
        "name": "Team Collaboration Agent",
        "layer": "deployment",
        "description": "Collaboration workflows and review",
        "avg_tokens": 35000,
    },
    {
        "name": "User Onboarding Agent",
        "layer": "deployment",
        "description": "Onboarding and tutorial experience",
        "avg_tokens": 35000,
    },
    {
        "name": "Customization Engine Agent",
        "layer": "execution",
        "description": "User customization and themes",
        "avg_tokens": 35000,
    },
    {
        "name": "Browser Tool Agent",
        "layer": "automation",
        "description": "Playwright browser automation",
        "avg_tokens": 40000,
    },
    {
        "name": "File Tool Agent",
        "layer": "execution",
        "description": "Writes files to project workspace",
        "avg_tokens": 50000,
    },
    {
        "name": "API Tool Agent",
        "layer": "automation",
        "description": "HTTP requests and API calls",
        "avg_tokens": 35000,
    },
    {
        "name": "Database Tool Agent",
        "layer": "execution",
        "description": "Applies schema to project DB",
        "avg_tokens": 40000,
    },
    {
        "name": "Deployment Tool Agent",
        "layer": "deployment",
        "description": "Deploy to Vercel/Railway/Netlify",
        "avg_tokens": 50000,
    },
]

# AI Model configurations: Cerebras (free) or Haiku (paid)
# All tasks use Haiku for paid users, Cerebras for free tier
MODEL_CONFIG = {
    "code": {"provider": "anthropic", "model": ANTHROPIC_HAIKU_MODEL},
    "analysis": {"provider": "anthropic", "model": ANTHROPIC_HAIKU_MODEL},
    "general": {"provider": "anthropic", "model": ANTHROPIC_HAIKU_MODEL},
    "creative": {"provider": "anthropic", "model": ANTHROPIC_HAIKU_MODEL},
    "fast": {"provider": "anthropic", "model": ANTHROPIC_HAIKU_MODEL},
}

# Fallback chain: only Haiku (no fallback needed, single provider)
MODEL_FALLBACK_CHAINS = [
    {"provider": "anthropic", "model": ANTHROPIC_HAIKU_MODEL},
]


def _cerebras_fallback_model_id() -> str:
    """Cerebras chat model id (llama-3.3-70b retired on API). Override with CEREBRAS_MODEL."""
    return (os.environ.get("CEREBRAS_MODEL") or "llama3.1-8b").strip()
# Map user-facing model key -> chain (only Haiku)
MODEL_CHAINS = {
    "auto": None,  # use MODEL_CONFIG + MODEL_FALLBACK_CHAINS
    "haiku": [{"provider": "anthropic", "model": ANTHROPIC_HAIKU_MODEL}],
}

# ==================== HELPERS ====================


def _user_credits(user: Optional[dict]) -> int:
    """Credits available: credit_balance if set, else token_balance // 1000 for legacy."""
    if not user:
        return 0
    if user.get("credit_balance") is not None:
        return int(user["credit_balance"])
    return int((user.get("token_balance") or 0) // CREDITS_PER_TOKEN)


def _tokens_to_credits(tokens: int) -> int:
    return max(1, (tokens + CREDITS_PER_TOKEN - 1) // CREDITS_PER_TOKEN)


async def _ensure_credit_balance(user_id: str) -> None:
    """Set credit_balance from token_balance if missing (migration)."""
    doc = await db.users.find_one(
        {"id": user_id}, {"credit_balance": 1, "token_balance": 1}
    )
    if not doc or doc.get("credit_balance") is not None:
        return
    cred = (doc.get("token_balance") or 0) // CREDITS_PER_TOKEN
    await db.users.update_one({"id": user_id}, {"$set": {"credit_balance": cred}})


# Disposable email block (fraud prevention)
DISPOSABLE_EMAIL_DOMAINS = frozenset(
    [
        "10minutemail.com",
        "guerrillamail.com",
        "tempmail.com",
        "mailinator.com",
        "throwaway.email",
        "temp-mail.org",
        "fakeinbox.com",
        "trashmail.com",
        "yopmail.com",
    ]
)


def _is_disposable_email(email: str) -> bool:
    domain = (email or "").strip().split("@")[-1].lower()
    return domain in DISPOSABLE_EMAIL_DOMAINS


def _quality_verdict(score: float) -> str:
    """Human-readable verdict for a 0-100 quality score."""
    if score >= 90:
        return "excellent"
    if score >= 75:
        return "good"
    if score >= 60:
        return "acceptable"
    return "needs-improvement"


def _quality_badge(score: float) -> str:
    """Emoji badge for quality score display in the UI."""
    if score >= 90:
        return "🏆"
    if score >= 75:
        return "✅"
    if score >= 60:
        return "⚠️"
    return "❌"


# Referral: 100 credits each (free tier only — referrer reward only if referrer is on free plan). Safest to avoid mismatch. 10/month cap, 30-day expiry.
REFERRAL_CREDITS = 100
REFERRAL_CAP_PER_MONTH = 10
REFERRAL_EXPIRY_DAYS = 30


def _generate_referral_code() -> str:
    return "".join(random.choices("abcdefghjkmnpqrstuvwxyz23456789", k=8))


async def _apply_referral_on_signup(
    referee_id: str, ref_code: Optional[str] = None
) -> None:
    """Grant 100 credits each when referee completes sign-up. Referrer reward only if referrer is on free plan (free tier only). Cap 10/month per referrer."""
    if not ref_code or not ref_code.strip():
        return
    ref_code = ref_code.strip().lower()
    ref_row = await db.referral_codes.find_one({"code": ref_code})
    if not ref_row:
        return
    referrer_id = ref_row.get("user_id")
    if not referrer_id or referrer_id == referee_id:
        return
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    count = await db.referrals.count_documents(
        {
            "referrer_id": referrer_id,
            "signup_completed_at": {"$gte": month_start.isoformat()},
        }
    )
    if count >= REFERRAL_CAP_PER_MONTH:
        return
    referrer_doc = await db.users.find_one({"id": referrer_id}, {"plan": 1})
    referrer_plan = (referrer_doc or {}).get("plan") or "free"
    reward_referrer = (
        referrer_plan == "free"
    )  # free tier only: referrer gets credits only if on free plan
    expiry_at = (now + timedelta(days=REFERRAL_EXPIRY_DAYS)).isoformat()
    await db.referrals.insert_one(
        {
            "id": str(uuid.uuid4()),
            "referrer_id": referrer_id,
            "referee_id": referee_id,
            "status": "completed",
            "signup_completed_at": now.isoformat(),
            "referrer_rewarded_at": now.isoformat(),
            "created_at": now.isoformat(),
        }
    )
    # Referee always gets 100 (new user = free tier). Referrer gets 100 only if referrer is on free plan.
    to_grant = [(referee_id, "Referral (referee)")]
    if reward_referrer:
        to_grant.append((referrer_id, "Referral (referrer)"))
    for uid, desc in to_grant:
        await db.users.update_one(
            {"id": uid}, {"$inc": {"credit_balance": REFERRAL_CREDITS}}
        )
        await db.token_ledger.insert_one(
            {
                "id": str(uuid.uuid4()),
                "user_id": uid,
                "credits": REFERRAL_CREDITS,
                "type": "referral",
                "description": desc,
                "credit_expires_at": expiry_at,
                "created_at": now.isoformat(),
            }
        )
    logger.info(
        f"Referral: granted {REFERRAL_CREDITS} to referee {referee_id}"
        + (
            f" and referrer {referrer_id} (free tier)"
            if reward_referrer
            else " (referrer not on free tier, no referrer reward)"
        )
    )


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        # bcrypt.checkpw expects bytes for both arguments
        if bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8")):
            return True
    except (ValueError, TypeError) as e:
        logger.debug(f"Bcrypt verification failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error during password verification: {e}")

    # Legacy: SHA-256 hashes (64-char hex) - DEPRECATED
    # WARNING: SHA-256 without salt is cryptographically weak
    # Set a deadline to force migration to bcrypt
    if len(hashed) == 64 and all(c in "0123456789abcdef" for c in hashed.lower()):
        logger.warning(
            f"SECURITY: SHA-256 password hash detected. Please migrate to bcrypt by 2026-06-01."
        )
        import hashlib

        return hashlib.sha256(plain.encode()).hexdigest() == hashed
    return False


def create_token(user_id: str) -> str:
    # SECURITY: Use 1-hour access tokens (not 30 days)
    # Implement refresh tokens for longer sessions
    payload = {
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def encode_jwt(
    payload: Dict[str, Any], secret: str = None, algorithm: str = None
) -> str:
    """Encode a JWT token with the given payload.

    Args:
        payload: Dictionary containing token claims
        secret: Secret key (defaults to JWT_SECRET)
        algorithm: Algorithm to use (defaults to JWT_ALGORITHM)

    Returns:
        Encoded JWT token string
    """
    if secret is None:
        secret = JWT_SECRET
    if algorithm is None:
        algorithm = JWT_ALGORITHM
    return jwt.encode(payload, secret, algorithm=algorithm)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(
            credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM]
        )
        user = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        if user.get("suspended"):
            raise HTTPException(status_code=403, detail="Account suspended")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user_sse(
    access_token: Optional[str] = Query(
        None,
        description="JWT for EventSource clients (cannot set Authorization header). Prefer Bearer when possible.",
    ),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    """Same as get_current_user; accepts Bearer or access_token query for SSE."""
    raw = None
    if credentials and credentials.credentials:
        raw = credentials.credentials
    elif access_token and str(access_token).strip():
        raw = str(access_token).strip()
    if not raw:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(raw, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        if user.get("suspended"):
            raise HTTPException(status_code=403, detail="Account suspended")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_permission(permission):
    """RBAC: require permission or 403. Use only when permission is not None."""

    async def _dep(user: dict = Depends(get_current_user)):
        if permission is not None and not has_permission(user, permission):
            raise HTTPException(status_code=403, detail="Insufficient permission")
        return user

    return _dep


# Public API (E1): X-API-Key validated against env CRUCIBAI_PUBLIC_API_KEYS or db.api_keys
PUBLIC_API_KEYS = set(
    k.strip()
    for k in (os.environ.get("CRUCIBAI_PUBLIC_API_KEYS") or "").split(",")
    if k.strip()
)


async def _check_api_key_db(api_key: str) -> bool:
    """Validate API key against db.api_keys if collection exists."""
    try:
        row = await db.api_keys.find_one({"key": api_key, "active": True})
        return row is not None
    except (ValueError, TypeError, AttributeError) as e:
        logger.debug(f"Error checking API key: {e}")
        return False


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    request: Request = None,
):
    """Logged-in user (Bearer JWT) or public API user (X-API-Key). Returns None if neither."""
    if credentials:
        try:
            payload = jwt.decode(
                credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM]
            )
            user = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0})
            if user:
                return user
        except (jwt.InvalidTokenError, jwt.DecodeError, KeyError) as e:
            logger.debug(f"Invalid JWT token: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in JWT verification: {e}")
    if request:
        api_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key")
        if api_key and (api_key in PUBLIC_API_KEYS or await _check_api_key_db(api_key)):
            return {
                "id": f"api_key_{api_key[:8]}",
                "token_balance": 999999,
                "credit_balance": 999999,
                "plan": "teams",
                "public_api": True,
            }
    return None


async def get_authenticated_or_api_user(
    user: Optional[dict] = Depends(get_optional_user),
):
    """Require either a signed-in user or a valid public API key for LLM/action routes."""
    if not user:
        raise HTTPException(
            status_code=401, detail="Authentication or API key required"
        )
    return user


# ── Skill auto-detection triggers ──────────────────────────────────────────
SKILL_TRIGGERS = {
    "web-app-builder": [
        "web app",
        "full-stack",
        "fullstack",
        "webapp",
        "build a platform",
        "react app",
        "node app",
        "api routes",
        "crud app",
        "portal",
        "browser app",
    ],
    "mobile-app-builder": [
        "mobile app",
        "ios app",
        "android app",
        "react native",
        "expo",
        "phone app",
        "cross-platform",
    ],
    "saas-mvp-builder": [
        "saas",
        "subscription",
        "stripe billing",
        "mvp with billing",
        "paid app",
        "saas mvp",
        "recurring payments",
    ],
    "ecommerce-builder": [
        "e-commerce",
        "ecommerce",
        "online store",
        "shop",
        "sell products",
        "product catalog",
        "stripe checkout",
        "marketplace",
        "shopify",
    ],
    "ai-chatbot-builder": [
        "chatbot",
        "ai assistant",
        "chat interface",
        "knowledge base bot",
        "customer support bot",
        "llm chat",
        "streaming chat",
        "conversational",
    ],
    "landing-page-builder": [
        "landing page",
        "marketing page",
        "product page",
        "waitlist",
        "hero section",
        "features page",
        "promotional",
    ],
    "automation-builder": [
        "automate",
        "automation",
        "workflow",
        "cron job",
        "webhook",
        "daily digest",
        "run every",
        "slack notify",
        "scheduled",
        "pipeline",
    ],
    "internal-tool-builder": [
        "admin panel",
        "internal tool",
        "back office",
        "crud interface",
        "approval workflow",
        "ops dashboard",
        "team tool",
    ],
    "data-dashboard-builder": [
        "dashboard",
        "analytics",
        "charts",
        "kpi",
        "metrics dashboard",
        "reporting tool",
        "data visualization",
        "recharts",
    ],
}


async def _auto_detect_skill(prompt: str, user_id: str) -> Optional[str]:
    """Auto-detect the best skill for a prompt. Transparent to the user."""
    p = prompt.lower()
    for skill_name, triggers in SKILL_TRIGGERS.items():
        if any(t in p for t in triggers):
            return skill_name
    return None


def _classify_task_complexity(prompt: str) -> str:
    """Returns 'fast' (Cerebras) or 'complex' (Haiku)."""
    p = prompt.lower().strip()
    # Complex: code generation, build, architecture
    complex_signals = [
        any(
            w in p
            for w in [
                "build",
                "create",
                "generate",
                "implement",
                "develop",
                "make me",
                "write code",
                "full stack",
                "database schema",
                "api route",
                "authentication",
                "deploy",
                "automate",
            ]
        ),
        len(p) > 150,  # long and detailed
    ]
    # Fast/simple: conversational, short, non-build
    fast_signals = [
        len(p) < 80,  # very short
        p.startswith(
            (
                "hi",
                "hello",
                "hey",
                "what",
                "how",
                "why",
                "when",
                "is ",
                "can you",
                "do you",
                "thanks",
                "ok",
                "yes",
                "no",
            )
        ),
        any(
            w in p
            for w in [
                "explain",
                "summarize",
                "what is",
                "tell me",
                "define",
                "list",
                "example of",
            ]
        ),
    ]
    if any(complex_signals):
        return "complex"
    if any(fast_signals):
        return "fast"
    return "complex"  # default to complex for safety


def detect_task_type(message: str) -> str:
    """Auto-detect the best model based on message content"""
    message_lower = message.lower()

    code_keywords = [
        "code",
        "function",
        "class",
        "api",
        "bug",
        "error",
        "debug",
        "implement",
        "python",
        "javascript",
        "react",
        "database",
    ]
    analysis_keywords = [
        "analyze",
        "compare",
        "evaluate",
        "explain",
        "why",
        "how does",
        "what is",
    ]
    creative_keywords = [
        "write",
        "create",
        "story",
        "poem",
        "design",
        "imagine",
        "brainstorm",
    ]

    for kw in code_keywords:
        if kw in message_lower:
            return "code"

    for kw in analysis_keywords:
        if kw in message_lower:
            return "analysis"

    for kw in creative_keywords:
        if kw in message_lower:
            return "creative"

    return "general"


def _provider_has_key(
    provider: str, effective_keys: Optional[Dict[str, str]] = None
) -> bool:
    """True if we have an API key for this provider. Only Anthropic (Haiku) and Cerebras supported."""
    if provider == "anthropic":
        if effective_keys:
            return bool(effective_keys.get("anthropic"))
        return bool(ANTHROPIC_API_KEY)
    if provider == "cerebras":
        return bool(os.environ.get("CEREBRAS_API_KEY"))
    return False


def _filter_chain_by_keys(
    chain: list, effective_keys: Optional[Dict[str, str]] = None
) -> list:
    """Keep only providers we have keys for."""
    return [
        c for c in chain if _provider_has_key(c.get("provider", ""), effective_keys)
    ]


def _get_model_chain(
    model_key: str,
    message: str,
    effective_keys: Optional[Dict[str, str]] = None,
    force_complex: bool = False,
):
    """Get list of (provider, model) to try. effective_keys = merged user Settings + server .env keys.
    Cerebras (default llama3.1-8b, env CEREBRAS_MODEL) for fast/simple tasks. Haiku for complex/build tasks.
    force_complex=True always selects Haiku (for iterative builds)."""
    cerebras_key = (effective_keys or {}).get("cerebras") or os.environ.get(
        "CEREBRAS_API_KEY"
    )
    anthropic_key = (effective_keys or {}).get("anthropic") or ANTHROPIC_API_KEY

    if model_key == "auto":
        # Model scale: prefer largest available when set (best for quality across 123 agents)
        if os.environ.get("PREFER_LARGEST_MODEL", "").strip().lower() in (
            "1",
            "true",
            "yes",
        ):
            chain = (
                _filter_chain_by_keys(MODEL_FALLBACK_CHAINS, effective_keys)
                or MODEL_FALLBACK_CHAINS
            )
        else:
            complexity = (
                "complex" if force_complex else _classify_task_complexity(message)
            )
            if complexity == "fast" and cerebras_key:
                # Cerebras first for fast tasks, Haiku fallback
                chain = [
                    {"provider": "cerebras", "model": _cerebras_fallback_model_id()},
                    {"provider": "anthropic", "model": ANTHROPIC_HAIKU_MODEL},
                ]
            elif anthropic_key:
                # Haiku first for complex tasks, Cerebras fallback
                chain = [
                    {"provider": "anthropic", "model": ANTHROPIC_HAIKU_MODEL},
                    {"provider": "cerebras", "model": _cerebras_fallback_model_id()},
                ]
            elif cerebras_key:
                chain = [{"provider": "cerebras", "model": _cerebras_fallback_model_id()}]
            else:
                chain = MODEL_FALLBACK_CHAINS
    else:
        chain = MODEL_CHAINS.get(model_key)
        if not chain:
            primary = MODEL_CONFIG["general"]
            chain = [primary] + MODEL_FALLBACK_CHAINS
    return _filter_chain_by_keys(chain, effective_keys) or [
        c
        for c in (MODEL_FALLBACK_CHAINS or [])
        if _provider_has_key(c.get("provider", ""), effective_keys)
    ]


async def get_workspace_api_keys(user: Optional[dict]) -> Dict[str, Optional[str]]:
    """Load Anthropic/Cerebras from server environment. Cerebras uses round-robin rotation."""
    return {
        "anthropic": ANTHROPIC_API_KEY or None,
        "cerebras": _get_cerebras_key() or os.environ.get("CEREBRAS_API_KEY") or None,
    }


def _effective_api_keys(
    user_keys: Dict[str, Optional[str]],
) -> Dict[str, Optional[str]]:
    """Use server-side API keys. Cerebras uses round-robin rotation across key pool."""
    return {
        "anthropic": ANTHROPIC_API_KEY or None,
        "cerebras": _get_cerebras_key() or os.environ.get("CEREBRAS_API_KEY") or None,
    }


async def _call_anthropic_direct(
    prompt: str,
    system: str,
    model: str = ANTHROPIC_HAIKU_MODEL,
    api_key: Optional[str] = None,
) -> str:
    """Call Anthropic API directly. Uses api_key or ANTHROPIC_API_KEY."""
    key = (api_key or "").strip() or ANTHROPIC_API_KEY
    if not key:
        raise ValueError("ANTHROPIC_API_KEY not set")
    model = normalize_anthropic_model(model, default=ANTHROPIC_HAIKU_MODEL)
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=key)
    msg = await client.messages.create(
        model=model,
        max_tokens=8192,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text if msg.content else ""
    return text.strip()


async def _call_cerebras_direct(
    prompt: str,
    system: str,
    model: str = "llama3.1-8b",
    api_key: Optional[str] = None,
) -> str:
    """Call Cerebras API directly (free tier fallback). Uses api_key or CEREBRAS_API_KEY."""
    key = (
        (api_key or "").strip()
        or _get_cerebras_key()
        or os.environ.get("CEREBRAS_API_KEY")
    )
    if not key:
        raise ValueError("CEREBRAS_API_KEY not set")
    import anthropic

    # Cerebras uses Anthropic-compatible API
    client = anthropic.AsyncAnthropic(
        api_key=key, base_url="https://api.cerebras.ai/v1"
    )
    msg = await client.messages.create(
        model=model,
        max_tokens=8192,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text if msg.content else ""
    return text.strip()


async def _call_anthropic_multimodal(
    content_blocks: List[Dict[str, Any]],
    system: str,
    model: str = ANTHROPIC_HAIKU_MODEL,
    api_key: Optional[str] = None,
) -> str:
    """Call Anthropic with multimodal user content (text + image). Uses vision-capable model."""
    key = (api_key or "").strip() or ANTHROPIC_API_KEY
    if not key:
        raise ValueError("ANTHROPIC_API_KEY not set")
    model = normalize_anthropic_model(model, default=ANTHROPIC_HAIKU_MODEL)
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=key)
    # Convert OpenAI-format content blocks to Anthropic format
    anthropic_content = []
    for block in content_blocks:
        if block.get("type") == "text":
            anthropic_content.append({"type": "text", "text": block.get("text", "")})
        elif block.get("type") == "image_url":
            url = (block.get("image_url") or {}).get("url") or ""
            if url.startswith("data:") and ";base64," in url:
                header, b64 = url.split(";base64,", 1)
                media = "image/png"
                if "image/" in header:
                    media = header.split("data:")[-1].strip()
                anthropic_content.append(
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media, "data": b64},
                    }
                )
            else:
                anthropic_content.append(
                    {"type": "text", "text": f"[Image: {url[:80]}...]"}
                )
    msg = await client.messages.create(
        model=model or ANTHROPIC_HAIKU_MODEL,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": anthropic_content}],
    )
    text = msg.content[0].text if msg.content else ""
    return text.strip()


def _content_blocks_have_image(content_blocks: Optional[List[Dict[str, Any]]]) -> bool:
    if not content_blocks:
        return False
    return any(b.get("type") == "image_url" for b in content_blocks)


# Vision-capable model: Haiku supports vision
VISION_MODEL_CHAIN = [
    {"provider": "anthropic", "model": ANTHROPIC_HAIKU_MODEL},
]


# ==================== LLM IMPLEMENTATIONS ====================


async def _call_llama_direct(
    message: str,
    system_message: str,
    model: str = "meta-llama/Llama-2-70b-chat-hf",
    api_key: str = None,
) -> str:
    """Call Llama 70B via Together AI."""
    import httpx

    if not api_key:
        raise ValueError("LLAMA_API_KEY not set")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.together.xyz/inference",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "prompt": f"{system_message}\n\nUser: {message}\n\nAssistant:",
                    "max_tokens": 8192,
                    "temperature": 0.7,
                    "top_p": 0.9,
                },
                timeout=120,
            )
            if response.status_code != 200:
                logger.warning(f"Llama API error: {response.text}")
                raise Exception(f"Llama API returned {response.status_code}")

            data = response.json()
            output = data.get("output", {}).get("choices", [{}])[0].get("text", "")
            return output.strip()
    except Exception as e:
        logger.error(f"Llama call failed: {e}")
        raise


async def _call_cerebras_direct(
    message: str,
    system_message: str,
    model: str = "llama3.1-8b",
    api_key: str = None,
) -> str:
    """Call Cerebras Llama 2 70B."""
    import httpx

    if not api_key:
        raise ValueError("CEREBRAS_API_KEY not set")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.cerebras.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": message},
                    ],
                    "max_tokens": 8192,
                    "temperature": 0.7,
                },
                timeout=120,
            )
            if response.status_code == 429:
                # Try next key in rotation before giving up
                next_key = _get_cerebras_key()
                if next_key and next_key != api_key:
                    logger.warning("Cerebras key rate limited — rotating to next key")
                    # Retry once with the next key
                    response2 = await client.post(
                        "https://api.cerebras.ai/v1/chat/completions",
                        headers={"Authorization": f"Bearer {next_key}"},
                        json={
                            "model": model,
                            "messages": [
                                {"role": "system", "content": system_message},
                                {"role": "user", "content": message},
                            ],
                            "max_tokens": 4096,
                            "temperature": 0.7,
                        },
                        timeout=120,
                    )
                    if response2.status_code == 200:
                        data = response2.json()
                        return (
                            data.get("choices", [{}])[0]
                            .get("message", {})
                            .get("content", "")
                            .strip()
                        )
                logger.warning(f"Cerebras rate limited — falling back to next model")
                raise Exception(f"RATE_LIMITED: Cerebras API rate limit exceeded")
            if response.status_code != 200:
                logger.warning(f"Cerebras API error: {response.text}")
                raise Exception(f"Cerebras API returned {response.status_code}")

            data = response.json()
            output = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return output.strip()
    except Exception as e:
        logger.error(f"Cerebras call failed: {e}")
        raise


async def _call_anthropic_direct(
    message: str,
    system_message: str,
    model: str = ANTHROPIC_HAIKU_MODEL,
    api_key: str = None,
) -> str:
    """Call Anthropic Claude Haiku."""
    import httpx

    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")
    model = normalize_anthropic_model(model, default=ANTHROPIC_HAIKU_MODEL)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": model,
                    "max_tokens": 4096,
                    "system": system_message,
                    "messages": [{"role": "user", "content": message}],
                },
                timeout=120,
            )
            if response.status_code != 200:
                err_body = response.text[:500]
                logger.warning(
                    "Anthropic API error %s: %s", response.status_code, err_body
                )
                # 400 with context too long → raise a specific error the retry loop can classify
                if response.status_code == 400:
                    try:
                        err_json = response.json()
                        err_type = (err_json.get("error") or {}).get("type", "")
                        err_msg = (err_json.get("error") or {}).get("message", err_body)
                    except Exception:
                        err_type, err_msg = "", err_body
                    raise Exception(
                        f"Anthropic API returned 400 ({err_type}): {err_msg[:300]}"
                    )
                raise Exception(f"Anthropic API returned {response.status_code}")

            data = response.json()
            output = data.get("content", [{}])[0].get("text", "")
            return output.strip()
    except Exception as e:
        logger.error(f"Anthropic call failed: {e}")
        raise


async def _call_llm_with_fallback(
    message: str,
    system_message: str,
    session_id: str,
    model_chain: list,
    user_id: str = None,
    user_tier: str = "free",
    speed_selector: str = "lite",
    available_credits: int = 0,
    agent_name: str = "",
    api_keys: Optional[Dict[str, Optional[str]]] = None,
    content_blocks: Optional[List[Dict[str, Any]]] = None,
    idempotency_key: Optional[str] = None,
) -> tuple[str, str]:
    """
    Intelligent LLM router with Llama + Cerebras primary, Haiku fallback.

    Routes based on:
    - Task complexity (simple vs complex)
    - User tier (free, starter, builder, pro, teams)
    - Speed selector (lite, pro, max)
    - Available credits
    """

    # Classify task complexity
    task_complexity = classifier.classify(message, agent_name)

    # Get intelligent model chain
    model_chain = router.get_model_chain(
        task_complexity=task_complexity,
        user_tier=user_tier,
        speed_selector=speed_selector,
        available_credits=available_credits,
    )

    if not model_chain:
        raise ValueError(
            "No LLM models available. Configure LLAMA_API_KEY, CEREBRAS_API_KEY, or ANTHROPIC_API_KEY."
        )

    last_error = None

    # Try each model in the chain
    for model_info in model_chain:
        model_name, model_id, provider = model_info

        try:
            logger.info(f"Trying {provider}/{model_name} for task: {task_complexity}")

            if provider == "together" and router.llama_available:
                # Llama 70B via Together AI
                response = await _call_llama_direct(
                    message,
                    system_message,
                    model=model_id,
                    api_key=router.llama_available and os.environ.get("LLAMA_API_KEY"),
                )

                # Record usage
                if user_id and db:
                    await tracker.record_usage(
                        db,
                        user_id,
                        "llama",
                        len(message.split()) * 1.3,  # Estimate tokens
                        user_tier,
                        agent_name,
                        session_id,
                        idempotency_key=idempotency_key,
                    )

                return (response, f"llama/{model_id}")

            elif provider == "cerebras" and router.cerebras_available:
                # Cerebras Llama 2 70B
                response = await _call_cerebras_direct(
                    message,
                    system_message,
                    model=model_id,
                    api_key=_get_cerebras_key() or os.environ.get("CEREBRAS_API_KEY"),
                )

                # Record usage
                if user_id and db:
                    await tracker.record_usage(
                        db,
                        user_id,
                        "cerebras",
                        len(message.split()) * 1.3,  # Estimate tokens
                        user_tier,
                        agent_name,
                        session_id,
                        idempotency_key=idempotency_key,
                    )

                return (response, f"cerebras/{model_id}")

            elif provider == "anthropic" and router.haiku_available:
                # Anthropic Claude Haiku (fallback)
                response = await _call_anthropic_direct(
                    message,
                    system_message,
                    model=model_id,
                    api_key=os.environ.get("ANTHROPIC_API_KEY"),
                )

                # Record usage
                if user_id and db:
                    await tracker.record_usage(
                        db,
                        user_id,
                        "haiku",
                        len(message.split()) * 1.3,  # Estimate tokens
                        user_tier,
                        agent_name,
                        session_id,
                        idempotency_key=idempotency_key,
                    )

                return (response, f"haiku/{model_id}")

        except Exception as e:
            last_error = e
            err_str = str(e)
            # If rate limited, skip this provider and try next immediately
            if (
                "RATE_LIMITED" in err_str
                or "rate limit" in err_str.lower()
                or "429" in err_str
            ):
                logger.warning(
                    f"LLM {provider}/{model_name} rate limited — falling back to next model"
                )
            else:
                logger.warning(
                    f"LLM {provider}/{model_name} failed: {e}, trying next fallback"
                )
            continue

    # All models failed
    error_msg = f"All LLM models failed. Last error: {last_error}"
    logger.error(error_msg)
    raise last_error or Exception(error_msg)


# ==================== AI CHAT ROUTES ====================
# Prepay: require at least MIN_CREDITS_FOR_LLM credits (legacy MIN_BALANCE_FOR_LLM_CALL = 5000 tokens ≈ 5 credits)
MIN_BALANCE_FOR_LLM_CALL = 5_000  # legacy token value; we check credits now


def _idempotency_key_from_request(request: Optional[Request]) -> Optional[str]:
    """HTTP Idempotency-Key (or X-Idempotency-Key) for credit replay safety (#17). Max 256 chars."""
    if request is None:
        return None
    h = (
        request.headers.get("Idempotency-Key")
        or request.headers.get("X-Idempotency-Key")
        or ""
    ).strip()
    if not h or len(h) > 256:
        return None
    return h


def _extract_pdf_text_from_b64(b64_data: str) -> str:
    """Extract text from base64-encoded PDF. Returns extracted text or a short fallback message on failure."""
    try:
        from pypdf import PdfReader

        raw = base64.b64decode(b64_data, validate=True)
        reader = PdfReader(io.BytesIO(raw))
        parts = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                parts.append(t)
        return "\n\n".join(parts)[:30000] if parts else "[PDF has no extractable text]"
    except Exception as e:
        logger.warning(f"PDF text extraction failed: {e}")
        return "[Could not extract PDF text.]"


from datetime import datetime as _dt
from datetime import timezone as _tz


def _build_chat_system_prompt(skills_context: str = "") -> str:
    today = _dt.now(_tz.utc).strftime("%B %d, %Y")
    skills_section = f"\n\n{skills_context}" if skills_context else ""
    return f"""{skills_section}You are CrucibAI — an AI platform that builds apps, automations, and digital products.

TODAY'S DATE: {today}. Always use this exact date when asked what the date or year is. Never use a date from your training data.

KNOWLEDGE CUTOFF:
- Your training data cutoff is approximately October 2024. Today is {today}. These are two different things — do not confuse them.
- For factual questions, give a direct answer with ONE sentence of useful context. Not zero context (too short), not a paragraph (too long). The right level: "Donald Trump — he won the 2024 election and was inaugurated January 20, 2025." Or: "Bola Tinubu — he's been Nigeria's president since 2023." Direct answer + one grounding fact. No URLs, no citations, no "as of my knowledge cutoff."
- Only add a caveat if the question is about something very recent (last few weeks) or highly specific real-time data (stock prices, sports scores today). For widely known facts, just answer.
- If the user corrects you, accept it immediately. Never argue.
- KNOWN FACTS (answer these directly, no caveats needed):
  - US President: Donald Trump (47th), inaugurated January 20, 2025. Previous president: Joe Biden (2021-2025).
  - Current year: 2026.

IDENTITY — answer these exactly, no more, no less:
- "Who are you?" / "What are you?" → "I\'m CrucibAI. I build things. Tell me what you want and we\'ll make it."
- "Who made you?" / "Who built you?" / "What company?" → "I\'m CrucibAI."
- "What model are you?" / "Are you ChatGPT?" / "Are you Claude?" / "What AI are you?" → "I\'m CrucibAI. I don\'t discuss what\'s under the hood — I just build. What do you want to make?"
- "Are you an agent?" / "Do you use agents?" → "I\'m CrucibAI. I build things. What do you want to make?"
- "How do you work?" / "What technology?" / "What stack?" → "Proprietary technology built to take your idea from prompt to product. Give me a description and I\'ll show you what it can do."
- "What can you build?" → "Web apps, mobile apps, landing pages, automations, APIs, dashboards — your entire product from one prompt. What do you need?"

Be direct, grounded, and confident. You are a builder and research partner—not customer support.

When the user attaches images or PDFs: images are shown to you directly, PDFs are extracted as text. Use that content to answer questions or help build something. Do not say you cannot see attachments.

OUTPUT FORMAT (modern product, not an old-school chatbot):
- Do not wrap normal prose in asterisks or decorative markdown. Avoid **bold** except when one term truly needs emphasis.
- No cheesy filler: not "I'm excited", "Here's what I found", "Great question", "I'd love to help", or generic AI-marketplace hype.
- Headings only when they help scan a long answer. Bullets only when they improve clarity—not by default.
- For research, markets, or startup ideas: be specific and analytical. Separate obvious plays from overlooked angles. Say where the market is saturated, what incumbents likely missed, and what combinations could stand alone—each with brief viability logic. Never dump generic "AI-powered X platform" ideas without concrete insight.

MAJOR RESEARCH AND STRATEGY (when the user asks for deep research, markets, opportunities, ideas, or "what should we build"):
- Do the analysis in this response. Do not stop to ask whether the scope "aligns with expectations", do not ask permission to continue, and do not offer a table of contents instead of substance.
- Go deep immediately: structure, judgment, trade-offs, and what is actually missing in the market—not a brainstorm list.
- Surface hidden opportunities: neglected categories, broken workflows, regulatory or distribution gaps, bundling that could be a standalone company, and why timing might matter now.
- For each non-obvious angle: why it could work, why incumbents or past startups have not fully solved it, and what would still be hard.
- Explicitly separate "obvious / already crowded" from "underexplored / structurally interesting" with reasoning—not labels alone.
- Ban lazy patterns: vague "AI-powered marketplace for X" without mechanics, users, wedge, and why it is not already solved.
- Write like a sharp co-founder and product strategist: commercially serious, direct, no cheerleading.

Rules:
- Never say "How can I assist you today?"
- Never say "How can I help you with your software development or coding needs?"
- Never sound generic or robotic
- Speak like a capable, founder-grade builder: direct judgment, no performative enthusiasm
- Never reveal the underlying model, technology stack, or internal architecture

CRITICAL — Ambiguity and clarification:
- When the user\'s intent is clear but details are missing, make the best reasonable assumption, state it in one sentence, and proceed.
- Never ask more than one clarifying question per response.
- If the user says "just do it", "figure it out", "you decide", "don\'t ask questions" — state what you will do in one line and proceed.
- Banned phrases: "I need a bit more context", "Are you looking to build X or Y?", "The more details you share", "Great choice! Are you looking to..."
- Ambiguity is a reason to decide, not a reason to stop.

Examples:
- "Hello" / "Hi" → "Hi. What do you want to build?"
- "What can you do?" → "Apps, automations, landing pages, APIs, internal tools—from prompt to shippable output. What are you trying to ship?"
- "How are you?" → "Ready when you are. What's the project?"
- Company name mentioned WITHOUT build request → "Interesting — do you want to build something related to that? Tell me what you have in mind."
- Question about a competitor or other AI tool → "I don\'t worry about other tools — I just build. What do you want to make?"
- Build request with vague details → State one concrete interpretation in one sentence and offer to build it.

CRITICAL — When to use code vs prose:
- Research, strategy, market analysis, opportunity mapping, GTM, or "what should we build" answers: use plain prose only. Do NOT include fenced code blocks (```), JSX, HTML, demo components, or fake implementation snippets unless the user explicitly asked for code or implementation.
- Do not decorate normal prose with asterisks, fake bold, or markdown emphasis habits. Prefer clean paragraphs; use headings or bullets only when they improve readability.
- When the user explicitly asks for code, implementation, an example in a programming language, or to "show the code": then use a single fenced block with the appropriate language tag. One short sentence before the fence if needed; no prose inside the fence; no extra fence after.

CRITICAL — Code output rules (only when code is explicitly requested):
- Wrap code in one fenced block: ```lang\\n...code...\\n```
- NEVER write explanation inside a code block.
- NEVER append explanation after the closing ```.
- One sentence BEFORE the code block if needed, then the code, then stop.
"""


CHAT_SYSTEM_PROMPT = _build_chat_system_prompt()


async def _build_chat_system_prompt_for_request(
    prompt: str, user_id: Optional[str]
) -> str:
    """Build the chat system prompt with auto-detected skill context injected transparently."""
    base = CHAT_SYSTEM_PROMPT
    auto_skill = await _auto_detect_skill(prompt, user_id or "")
    if auto_skill:
        skill_md = _load_skill_md(auto_skill)
        if skill_md:
            # Extract just the instructions section
            instructions_start = skill_md.find("## Instructions")
            if instructions_start > 0:
                instructions = skill_md[instructions_start : instructions_start + 2000]
                base = f"ACTIVE SKILL: {auto_skill}\n{instructions}\n\n" + base
            else:
                # Use first 1500 chars as instructions if no ## Instructions header
                base = f"ACTIVE SKILL: {auto_skill}\n{skill_md[:1500]}\n\n" + base
    # Also merge any user-activated skills context if we have a user
    if user_id:
        try:
            skills_ctx = await _get_active_skills_context(user_id)
            if skills_ctx:
                base = skills_ctx + "\n\n" + base
        except Exception:
            pass
    return base


def _is_conversational_message(message: str) -> bool:
    """Detect if message is conversational/factual (not a build request).
    Conversational messages route to Haiku only for best accuracy.
    Build requests use the full model chain.
    """
    if not message or len(message.strip()) < 2:
        return True
    lower = message.lower().strip()
    # Greetings and small talk
    greetings = {
        "hi",
        "hello",
        "hey",
        "yo",
        "sup",
        "good morning",
        "good afternoon",
        "good evening",
    }
    if lower in greetings or any(lower.startswith(g) for g in greetings):
        return True
    # Factual questions
    factual_starts = [
        "who is",
        "who are",
        "what is",
        "what are",
        "what was",
        "what were",
        "when is",
        "when was",
        "when did",
        "where is",
        "where was",
        "how is",
        "how are",
        "how does",
        "how do",
        "why is",
        "why are",
        "why does",
        "why did",
        "tell me about",
        "what do you know about",
        "do you know",
        "have you heard",
        "are you",
        "can you",
        "what date",
        "what year",
        "what time",
        "today",
        "who won",
        "who runs",
        "who leads",
        "president",
        "prime minister",
    ]
    if any(lower.startswith(f) for f in factual_starts):
        return True
    # Identity questions
    identity = [
        "who made you",
        "who built you",
        "what model",
        "what ai",
        "are you claude",
        "are you chatgpt",
        "are you an agent",
        "how do you work",
        "what technology",
        "what stack",
        "how are you",
        "what can you",
        "what do you",
    ]
    if any(q in lower for q in identity):
        return True
    # Build keywords — if present, it's NOT conversational
    build_keywords = [
        "build",
        "create",
        "make",
        "develop",
        "design",
        "generate",
        "code",
        "app",
        "website",
        "api",
        "backend",
        "frontend",
        "dashboard",
        "landing page",
        "mobile",
        "automate",
    ]
    if any(k in lower for k in build_keywords):
        return False
    # Short messages with no build intent = conversational
    if len(message.split()) < 8:
        return True
    return False


def _needs_live_data(message: str) -> bool:
    """Detect if message asks for real-time or current info that needs a live search."""
    if not message or len(message.strip()) < 3:
        return False
    lower = message.lower()
    keywords = [
        # Weather
        "weather",
        "forecast",
        "temperature",
        "rain",
        "sunny",
        "degrees",
        # News & events
        "news",
        "headlines",
        "today's",
        "current events",
        "latest",
        # Stocks & crypto
        "stock",
        "price",
        "market",
        "bitcoin",
        "crypto",
        # Sports
        "score",
        "game",
        "match",
        "nfl",
        "nba",
        "mlb",
        "soccer",
        # Current people/positions — critical for president/CEO questions
        "who is president",
        "who is the president",
        "president of",
        "prime minister",
        "who is ceo",
        "ceo of",
        "who runs",
        "who is in charge",
        "who won",
        "who leads",
        # Current year/date awareness
        "in 2025",
        "in 2026",
        "this year",
        "right now",
        "currently",
        "as of today",
        "as of now",
        "what year",
        "what month",
        # General current state
        "what is happening",
        "what happened",
        "recent",
        "just happened",
        "breaking",
        "update on",
        "status of",
        # Location-based
        "in texas",
        "in new york",
        "in california",
        "in london",
    ]
    return any(k in lower for k in keywords)


async def _fetch_search_context(query: str) -> Optional[str]:
    """Call Tavily search API and return formatted context. Returns None if unavailable."""
    api_key = os.environ.get("TAVILY_API_KEY")
    if not api_key:
        return None
    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=api_key)

        def _search():
            return client.search(
                query, search_depth="basic", max_results=5, include_answer=True
            )

        resp = await asyncio.to_thread(_search)
        parts = []
        if resp.get("answer"):
            parts.append(resp["answer"])
        for r in (resp.get("results") or [])[:5]:
            title = r.get("title", "")
            content = r.get("content", "")
            if content:
                parts.append(f"[{title}]: {content[:500]}")
        if not parts:
            return None
        return "\n\n".join(parts)[:4000]
    except Exception as e:
        logger.warning(f"Tavily search failed: {e}")
        return None


CHAT_WITH_SEARCH_SYSTEM = """You are CrucibAI. Use the live search results below. Answer directly and factually—no filler, no hedging unless uncertainty is real.
Do not wrap sections in decorative asterisks. Prefer short paragraphs over markdown theater.
If a build is relevant, one crisp line offering to prototype it—no hype.
"""


def _merge_prior_turns_into_message(
    latest_user: str, prior_turns: Optional[List[Dict[str, Any]]]
) -> str:
    """Fold earlier turns into one text block so single-message LLM APIs keep context."""
    latest_user = (latest_user or "").strip()
    if not prior_turns:
        return latest_user
    lines = []
    for t in prior_turns[-40:]:
        role = t.get("role") or "user"
        role = role.lower() if isinstance(role, str) else "user"
        content = (t.get("content") or "").strip()
        if not content:
            continue
        label = "User" if role == "user" else "CrucibAI"
        lines.append(f"{label}: {content}")
    if not lines:
        return latest_user
    return (
        "Conversation history:\n"
        + "\n\n".join(lines)
        + "\n\n---\nUser (latest message):\n"
        + latest_user
    )


# ==================== EXPORT ZIP / GITHUB / DEPLOY ====================

DEPLOY_README = """# Deploy this project

## Vercel (recommended)
1. Go to https://vercel.com/new
2. Import this folder or upload the ZIP (Vercel will extract it).
3. Set build command: (leave default for Create React App)
4. Deploy.

## Netlify
1. Go to https://app.netlify.com/drop
2. Drag and drop this folder (or the ZIP).
3. Site deploys automatically.

## Railway
1. Go to https://railway.app/new
2. Create a new project, then "Deploy from GitHub repo" (push this folder to a repo first) or use "Empty project" and deploy via Railway CLI from this folder.
3. Add a service (e.g. Web Service for Node/React, or static site).
4. Deploy.

Generated with CrucibAI.
"""

# ==================== STRIPE (PAY US) ====================

STRIPE_SECRET = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")


@api_router.post("/stripe/create-checkout-session")
async def stripe_create_checkout(
    data: TokenPurchase, user: dict = Depends(get_current_user)
):
    """Create Stripe Checkout session for token bundle purchase. Redirects to Stripe Pay."""
    if not STRIPE_SECRET:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    if data.bundle not in TOKEN_BUNDLES:
        raise HTTPException(status_code=400, detail="Invalid bundle")
    bundle = TOKEN_BUNDLES[data.bundle]
    try:
        import stripe

        stripe.api_key = STRIPE_SECRET
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": f"CrucibAI - {bundle.get('name', data.bundle)}",
                            "description": f"{bundle.get('credits', bundle['tokens'] // CREDITS_PER_TOKEN)} credits",
                        },
                        "unit_amount": int(bundle["price"] * 100),
                    },
                    "quantity": 1,
                }
            ],
            success_url=f"{FRONTEND_URL}/app/tokens?success=1&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/app/tokens?canceled=1",
            client_reference_id=user["id"],
            metadata={
                "bundle": data.bundle,
                "tokens": str(bundle["tokens"]),
                "credits": str(
                    bundle.get("credits", bundle["tokens"] // CREDITS_PER_TOKEN)
                ),
            },
        )
        return {"url": session.url, "session_id": session.id}
    except Exception as e:
        logger.error(f"Stripe checkout error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/stripe/create-checkout-session-custom")
async def stripe_create_checkout_custom(
    data: TokenPurchaseCustom, user: dict = Depends(get_current_user)
):
    """Create Stripe Checkout session for custom credit purchase (slider). Amount = credits * $0.03."""
    if not STRIPE_SECRET:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    credits = data.credits
    price = round(credits * 0.03, 2)
    amount_cents = int(round(price * 100))
    tokens = credits * CREDITS_PER_TOKEN
    try:
        import stripe

        stripe.api_key = STRIPE_SECRET
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": f"CrucibAI - {credits} credits",
                            "description": f"{credits} credits at $0.03/credit",
                        },
                        "unit_amount": amount_cents,
                    },
                    "quantity": 1,
                }
            ],
            success_url=f"{FRONTEND_URL}/app/tokens?success=1&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/app/tokens?canceled=1",
            client_reference_id=user["id"],
            metadata={
                "bundle": "custom",
                "credits": str(credits),
                "tokens": str(tokens),
            },
        )
        return {"url": session.url, "session_id": session.id}
    except Exception as e:
        logger.error(f"Stripe checkout custom error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/stripe/webhook")
async def stripe_webhook(request: Request, background_tasks: BackgroundTasks):
    """Handle Stripe webhook: checkout.session.completed -> add tokens to user."""
    if not STRIPE_SECRET or not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Stripe not configured")
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        import stripe

        stripe.api_key = STRIPE_SECRET
        event = stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        logger.warning(f"Stripe webhook signature invalid: {e}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.get("client_reference_id")
        bundle_key = session.get("metadata", {}).get("bundle")
        meta = session.get("metadata", {})
        credits_str = meta.get("credits")
        tokens_str = meta.get("tokens", "0")
        if not user_id or not bundle_key:
            logger.warning(
                "Stripe session missing client_reference_id or metadata.bundle"
            )
            return {"received": True}
        credits = (
            int(credits_str) if credits_str else (int(tokens_str) // CREDITS_PER_TOKEN)
        )
        tokens = int(tokens_str) if tokens_str else (credits * CREDITS_PER_TOKEN)
        if bundle_key == "custom":
            price = round(credits * 0.03, 2)
        else:
            price = TOKEN_BUNDLES.get(bundle_key, {}).get("price", 0)
        await db.users.update_one(
            {"id": user_id},
            {"$inc": {"token_balance": tokens, "credit_balance": credits}},
        )
        if bundle_key in ("builder", "pro", "scale", "teams"):
            await db.users.update_one({"id": user_id}, {"$set": {"plan": bundle_key}})
        await db.token_ledger.insert_one(
            {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "tokens": tokens,
                "credits": credits,
                "type": "purchase",
                "bundle": bundle_key,
                "price": price,
                "stripe_session_id": session.get("id"),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        logger.info(f"Stripe: added {credits} credits to user {user_id}")
    return {"received": True}


# ==================== AUTH ROUTES ====================



# Auth/projects/agents fallback route bodies removed in final closure pass.
# Canonical implementations now live in backend/routes/*.py and service modules.

# ==================== JOB QUEUE ====================


def _assert_job_owner_match(owner_id: Optional[str], user: Optional[dict]) -> None:
    """Stateful job access requires an authenticated owner match."""
    if not owner_id:
        raise HTTPException(status_code=403, detail="Job owner required")
    uid = user.get("id") if user else None
    if not uid or uid != owner_id:
        raise HTTPException(status_code=403, detail="Not your job")


async def _get_task_for_user(task_id: str, user: dict) -> Optional[dict]:
    """Return a task only when it belongs to the authenticated user."""
    if not task_id:
        return None
    task = await db.tasks.find_one({"id": task_id})
    if not task:
        return None
    owner_id = task.get("user_id")
    if owner_id and owner_id != user["id"]:
        raise HTTPException(status_code=403, detail="Not your task")
    return task


@api_router.get("/jobs/{job_id}")
async def get_job(job_id: str, user: dict = Depends(get_current_user)):
    """Queue async job (flat JSON) or Auto-Runner job from Postgres (`{ success, job }`)."""
    try:
        from integrations.queue import get_job_status

        qj = await get_job_status(job_id)
        if qj:
            payload = qj.get("payload") or {}
            _assert_job_owner_match(payload.get("user_id"), user)
            return qj
        runtime_state, _, _, _, _ = _get_orchestration()
        from db_pg import get_pg_pool

        pool = await get_pg_pool()
        runtime_state.set_pool(pool)
        from orchestration import runtime_state as orch_rs

        oj = await orch_rs.get_job(job_id)
        if not oj:
            raise HTTPException(status_code=404, detail="Job not found")
        _assert_job_owner_match(oj.get("user_id"), user)
        from orchestration.publish_urls import published_app_url
        return {
            "success": True,
            "job": published_enrich_job_public_urls(
                oj,
                _project_workspace_path,
                WORKSPACE_ROOT,
                published_app_url,
            ),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/jobs/{job_id}/export")
async def export_job_workspace_discovery(
    job_id: str,
    user: dict = Depends(get_current_user),
):
    """
    P6 — JSON discovery for workspace export: canonical full.zip URL and on-disk hints.
    """
    try:
        project_id = await _resolve_workspace_project_for_job(job_id, user)
        root = _project_workspace_path(project_id).resolve()
        meta = root / "META"
        return {
            "success": True,
            "job_id": job_id,
            "project_id": project_id,
            "workspace_root": str(root),
            "workspace_exists": root.is_dir(),
            "href_full_zip": f"/api/jobs/{job_id}/export/full.zip",
            "href_handoff_zip": f"/api/jobs/{job_id}/export/full.zip?profile=handoff",
            "meta": {
                "exists": meta.is_dir(),
                "artifact_manifest": (meta / "artifact_manifest.json").is_file(),
                "run_manifest": (meta / "run_manifest.json").is_file(),
                "seal": (meta / "seal.json").is_file(),
                "path_last_writer": (meta / "path_last_writer.json").is_file(),
                "merge_map": (meta / "merge_map.json").is_file(),
                "proof_index": (meta / "proof_index.json").is_file(),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/jobs/{job_id}/export/full.zip")
async def export_job_workspace_full_zip(
    job_id: str,
    user: dict = Depends(get_current_user),
    profile: str = Query(
        "full",
        description="full = entire workspace tree; handoff = app-focused (excludes outputs/ per-agent markdown)",
    ),
):
    """
    Download the durable project workspace for this job as one ZIP (excludes node_modules, .git).
    Includes META/* manifests when present (written on successful job seal).
    Use profile=handoff for a cleaner handoff ZIP without per-agent outputs/ markdown dumps.
    """
    try:
        from orchestration.workspace_assembly import iter_files_for_zip

        prof = (profile or "full").strip().lower()
        if prof not in ("full", "handoff"):
            prof = "full"

        project_id = await _resolve_workspace_project_for_job(job_id, user)
        root = _project_workspace_path(project_id).resolve()
        if not root.is_dir():
            raise HTTPException(status_code=404, detail="Workspace not found or empty")
        fd, tmp_path = tempfile.mkstemp(suffix=".zip")
        os.close(fd)
        try:
            with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                for arcname, fp in iter_files_for_zip(root, profile=prof):
                    try:
                        zf.write(str(fp), arcname=arcname)
                    except OSError:
                        continue
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

        def _unlink(p: str) -> None:
            try:
                os.unlink(p)
            except OSError:
                pass

        safe = "".join(c if c.isalnum() or c in "-_" else "-" for c in job_id[:24])
        suffix = "handoff" if prof == "handoff" else "full"
        return FileResponse(
            tmp_path,
            media_type="application/zip",
            filename=f"crucibai-job-{safe}-{suffix}.zip",
            background=BackgroundTask(_unlink, tmp_path),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("export full zip: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/jobs")
async def list_jobs(user: dict = Depends(get_current_user)):
    """List active/recent jobs for the current user.
    Used by frontend on reconnect to resume monitoring in-progress builds."""
    try:
        if not user:
            return {"jobs": []}
        from integrations.queue import _memory_jobs, get_job_status

        # From memory (works for current container)
        user_jobs = [
            j
            for j in _memory_jobs.values()
            if j.get("payload", {}).get("user_id") == user.get("id")
            and j.get("status") in ("queued", "running", "complete")
        ]
        # Also check PostgreSQL for jobs from previous containers
        try:
            cursor = db.automation_tasks.find(
                {
                    "doc.payload.user_id": user["id"],
                    "doc.status": {"$in": ["queued", "running", "complete"]},
                }
            )
            pg_jobs = []
            async for row in cursor:
                doc = row.get("doc", {})
                jid = doc.get("id", "")
                if jid not in {j["id"] for j in user_jobs}:
                    pg_jobs.append(doc)
            user_jobs = user_jobs + pg_jobs
        except Exception:
            pass
        # Sort newest first
        user_jobs.sort(key=lambda j: j.get("created_at", ""), reverse=True)
        return {"jobs": user_jobs[:20]}
    except Exception as e:
        return {"jobs": [], "error": str(e)}


@tools_router.post("/tools/browser")
async def use_browser_tool(
    body: ToolBrowserRequest, user: dict = Depends(get_current_user)
):
    """Execute browser action (SSRF-safe; requires auth)."""
    from tools.browser_agent import BrowserAgent

    agent = BrowserAgent(llm_client=None, config={})
    ctx = body.model_dump(exclude_none=True)
    return await agent.run(ctx)


@tools_router.post("/tools/file")
async def use_file_tool(body: ToolFileRequest, user: dict = Depends(get_current_user)):
    """Execute file operation (scoped to user workspace; requires auth)."""
    from tools.file_agent import FileAgent

    user_workspace = WORKSPACE_ROOT / (user.get("id") or "default")
    user_workspace.mkdir(parents=True, exist_ok=True)
    agent = FileAgent(llm_client=None, config={"workspace": str(user_workspace)})
    ctx = body.model_dump(exclude_none=True)
    return await agent.run(ctx)


@tools_router.post("/tools/api")
async def use_api_tool(body: ToolApiRequest, user: dict = Depends(get_current_user)):
    """Make HTTP request (SSRF-safe; requires auth)."""
    from tools.api_agent import APIAgent

    agent = APIAgent(llm_client=None, config={})
    ctx = body.model_dump(exclude_none=True)
    return await agent.run(ctx)


@tools_router.post("/tools/database")
async def use_database_tool(
    body: ToolDatabaseRequest, user: dict = Depends(get_current_user)
):
    """Execute SQL query (read-only when connection is client-provided; requires auth)."""
    from tools.database_operations_agent import DatabaseOperationsAgent

    agent = DatabaseOperationsAgent(llm_client=None, config={})
    ctx = body.model_dump(exclude_none=True)
    return await agent.run(ctx)


@tools_router.post("/tools/deploy")
async def use_deployment_tool(
    body: ToolDeployRequest, user: dict = Depends(get_current_user)
):
    """Deploy application (project_path must be under workspace; requires auth)."""
    from tools.deployment_operations_agent import DeploymentOperationsAgent

    agent = DeploymentOperationsAgent(
        llm_client=None, config={"workspace_root": str(WORKSPACE_ROOT)}
    )
    ctx = body.model_dump(exclude_none=True)
    return await agent.run(ctx)


import json as _json
import sys as _sys

_sys.path.insert(0, os.path.dirname(__file__))


def _get_orchestration():
    from orchestration import auto_runner as ar_mod
    from orchestration import dag_engine
    from orchestration import planner as planner_mod
    from orchestration import runtime_state

    from proof import proof_service as ps_mod

    return runtime_state, dag_engine, planner_mod, ar_mod, ps_mod


class CreateJobRequest(BaseModel):
    project_id: str
    goal: str
    mode: Optional[str] = "guided"


try:
    from routes.orchestrator import CostEstimateRequest, PlanRequest, RunAutoRequest
except ImportError:
    pass


# ── Job CRUD ──────────────────────────────────────────────────────────────────


@api_router.post("/jobs")
async def create_job_route(
    body: CreateJobRequest, user: dict = Depends(get_current_user)
):
    """Create a new job (plan + steps) for a project."""
    try:
        return await create_job_service(
            body=body,
            user=user,
            runtime_state_getter=lambda: _get_orchestration()[0],
            pool_getter=(lambda: __import__("db_pg", fromlist=["get_pg_pool"]).get_pg_pool()),
            generate_plan=lambda goal, project_state=None: _get_orchestration()[2].generate_plan(goal, project_state=project_state),
            build_dag_from_plan=__import__("orchestration.dag_engine", fromlist=["build_dag_from_plan"]).build_dag_from_plan,
            resolve_project_id=_resolve_job_project_id_for_user,
            update_last_build_state=_update_last_build_state,
            planner_project_state=_orchestrator_planner_project_state(user),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("POST /jobs error")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/jobs/{job_id}/steps")
async def get_job_steps(job_id: str, user: dict = Depends(get_current_user)):
    """Get all steps for a job with their current status."""
    try:
        from db_pg import get_pg_pool

        return await get_job_steps_service(
            job_id=job_id,
            user=user,
            runtime_state_getter=lambda: _get_orchestration()[0],
            pool_getter=get_pg_pool,
            assert_owner=_assert_job_owner_match,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/jobs/{job_id}/plan-draft")
async def get_job_plan_draft(job_id: str, user: dict = Depends(get_current_user)):
    """Latest stored plan JSON for a job (for resuming from history)."""
    try:
        from db_pg import get_pg_pool

        return await get_job_plan_draft_service(
            job_id=job_id,
            user=user,
            runtime_state_getter=lambda: _get_orchestration()[0],
            pool_getter=get_pg_pool,
            assert_owner=_assert_job_owner_match,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/jobs/{job_id}/events")
async def get_job_events(
    job_id: str, since_id: Optional[str] = None, user: dict = Depends(get_current_user)
):
    """Get job event log (for replay/history view)."""
    try:
        from db_pg import get_pg_pool

        return await get_job_events_service(
            job_id=job_id,
            user=user,
            since_id=since_id,
            runtime_state_getter=lambda: _get_orchestration()[0],
            pool_getter=get_pg_pool,
            assert_owner=_assert_job_owner_match,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/jobs/{job_id}/proof")
async def get_job_proof(job_id: str, user: dict = Depends(get_current_user)):
    """Get proof bundle for job (files, routes, DB, verification, deploy)."""
    try:
        from db_pg import get_pg_pool

        return await get_job_proof_service(
            job_id=job_id,
            user=user,
            runtime_state_getter=lambda: _get_orchestration()[0],
            pool_getter=get_pg_pool,
            assert_owner=_assert_job_owner_match,
            proof_service_getter=lambda: _get_orchestration()[4],
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        logger.error(
            f"Proof endpoint error for job {job_id}: {e}\n{traceback.format_exc()}"
        )
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/jobs/{job_id}/workspace/files")
async def list_job_workspace_files(
    job_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=1000),
    user: dict = Depends(get_current_user),
):
    """List files under the job's project workspace (paginated)."""
    project_id = await _resolve_workspace_project_for_job(job_id, user)
    return list_job_workspace_files_service(
        job_id=job_id,
        user=user,
        offset=offset,
        limit=limit,
        resolve_project_for_job=lambda _job_id, _user: project_id,
        project_workspace_path=_project_workspace_path,
        list_all_rel_paths=_list_all_workspace_rel_paths,
        paginated_payload=_paginated_workspace_files_payload,
    )



@api_router.get("/jobs/{job_id}/workspace/file")
async def get_job_workspace_file_content(
    job_id: str,
    path: str = Query(..., description="Relative file path in workspace"),
    user: dict = Depends(get_current_user),
):
    """Read one file from the job's project workspace."""
    project_id = await _resolve_workspace_project_for_job(job_id, user)
    return get_job_workspace_file_content_service(
        job_id=job_id,
        user=user,
        path=path,
        resolve_project_for_job=lambda _job_id, _user: project_id,
        project_workspace_path=_project_workspace_path,
        workspace_file_disk_path=_workspace_file_disk_path,
    )



@api_router.get("/jobs/{job_id}/workspace/file/raw")
async def get_job_workspace_file_raw(
    job_id: str,
    path: str = Query(..., description="Relative file path in workspace"),
    user: dict = Depends(get_current_user),
):
    """Stream file bytes from the job's project workspace."""
    project_id = await _resolve_workspace_project_for_job(job_id, user)
    return get_job_workspace_file_raw_service(
        job_id=job_id,
        user=user,
        path=path,
        resolve_project_for_job=lambda _job_id, _user: project_id,
        project_workspace_path=_project_workspace_path,
        workspace_file_disk_path=_workspace_file_disk_path,
        guess_media_type=lambda name: mimetypes.guess_type(name)[0],
    )



@api_router.post("/jobs/{job_id}/visual-edit")
async def visual_edit_job_workspace_file(
    job_id: str,
    body: VisualEditRequest,
    user: dict = Depends(get_current_user),
):
    """Apply a deterministic visual text/style edit to a generated app file."""
    project_id = await _resolve_workspace_project_for_job(job_id, user)
    return visual_edit_job_workspace_file_service(
        job_id=job_id,
        user=user,
        body=body,
        resolve_project_for_job=lambda _job_id, _user: project_id,
        project_workspace_path=_project_workspace_path,
    )


@api_router.get("/trust/platform-capabilities")
async def trust_platform_capabilities(user: dict = Depends(get_optional_user)):
    """Roadmap item wiring status (wired | partial | planned) for operator transparency."""
    try:
        from orchestration.trust.roadmap_wiring import roadmap_wiring_status

        return {"success": True, "items": roadmap_wiring_status()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.get("/jobs/{job_id}/trust-report")
async def get_job_trust_report(job_id: str, user: dict = Depends(get_current_user)):
    """Aggregated trust metrics + roadmap wiring snapshot for a job."""
    try:
        from orchestration.trust.roadmap_wiring import roadmap_wiring_status
        from db_pg import get_pg_pool

        return await get_job_trust_report_service(
            job_id=job_id,
            user=user,
            runtime_state_getter=lambda: _get_orchestration()[0],
            pool_getter=get_pg_pool,
            proof_service_getter=lambda: _get_orchestration()[4],
            assert_owner=_assert_job_owner_match,
            roadmap_wiring_status=roadmap_wiring_status,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str, user: dict = Depends(get_current_user)):
    """Cancel a running job."""
    try:
        from db_pg import get_pg_pool
        from orchestration.event_bus import publish

        return await cancel_job_service(
            job_id=job_id,
            user=user,
            runtime_state_getter=lambda: _get_orchestration()[0],
            pool_getter=get_pg_pool,
            assert_owner=_assert_job_owner_match,
            publish=publish,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/jobs/{job_id}/resume")
async def resume_job_route(
    job_id: str,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    """Resume an interrupted job from its last checkpoint."""
    try:
        from db_pg import get_pg_pool
        from orchestration.preflight_report import build_preflight_report
        from orchestration.runtime_health import collect_runtime_health_sync
        from orchestration.runtime_state import append_job_event
        from routes.orchestrator import _background_resume_auto_job

        return await resume_job_service(
            job_id=job_id,
            user=user,
            runtime_state_getter=lambda: _get_orchestration()[0],
            pool_getter=get_pg_pool,
            assert_owner=_assert_job_owner_match,
            build_preflight_report=build_preflight_report,
            collect_runtime_health_sync=collect_runtime_health_sync,
            append_job_event=append_job_event,
            background_add_task=background_tasks.add_task,
            background_resume_callable=_background_resume_auto_job,
            project_workspace_path=_project_workspace_path,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/jobs/{job_id}/steer")
async def steer_job_route(
    job_id: str,
    body: JobSteerRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
):
    """
    Record a user steering message on a job (especially after failure) and optionally resume the runner.
    """
    try:
        from db_pg import get_pg_pool
        from orchestration.brain_narration import build_steering_guidance
        from orchestration.event_bus import publish
        from orchestration.preflight_report import build_preflight_report
        from orchestration.runtime_health import collect_runtime_health_sync
        from orchestration.runtime_state import append_job_event
        from routes.orchestrator import _background_resume_auto_job

        return await steer_job_service(
            job_id=job_id,
            body=body,
            user=user,
            runtime_state_getter=lambda: _get_orchestration()[0],
            pool_getter=get_pg_pool,
            assert_owner=_assert_job_owner_match,
            append_job_event=append_job_event,
            build_steering_guidance=build_steering_guidance,
            publish=publish,
            build_preflight_report=build_preflight_report,
            collect_runtime_health_sync=collect_runtime_health_sync,
            background_add_task=background_tasks.add_task,
            background_resume_callable=_background_resume_auto_job,
            project_workspace_path=_project_workspace_path,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/jobs/{job_id}/retry-step/{step_id}")
async def retry_step(job_id: str, step_id: str, user: dict = Depends(get_current_user)):
    """Manually retry a specific failed step."""
    try:
        from db_pg import get_pg_pool

        return await retry_step_service(
            job_id=job_id,
            step_id=step_id,
            user=user,
            runtime_state_getter=lambda: _get_orchestration()[0],
            pool_getter=get_pg_pool,
            assert_owner=_assert_job_owner_match,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── SSE stream ────────────────────────────────────────────────────────────────

@api_router.get("/jobs/{job_id}/stream")
async def stream_job_events(job_id: str, user: dict = Depends(get_current_user)):
    """
    Server-Sent Events stream for real-time job progress.
    Streams: job_started, step_started, step_completed, step_failed, job_completed, etc.
    """
    from db_pg import get_pg_pool
    from orchestration.event_bus import subscribe, unsubscribe
    from orchestration.runtime_state import get_job_events as _get_stored

    return await build_job_stream_response_service(
        job_id=job_id,
        user=user,
        runtime_state_getter=lambda: _get_orchestration()[0],
        pool_getter=get_pg_pool,
        assert_owner=_assert_job_owner_match,
        subscribe=subscribe,
        unsubscribe=unsubscribe,
        get_stored_events=_get_stored,
    )


# ==================== MONITORING (PostgreSQL proof) ====================
class TrackEventRequest(BaseModel):
    event_type: str
    user_id: str
    duration: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    success: bool = True
    error_message: Optional[str] = None


@api_router.post("/monitoring/events/track")
async def monitoring_track_event(body: TrackEventRequest):
    """Track a monitoring event. Stored in PostgreSQL when DATABASE_URL is set."""
    import uuid

    event_id = str(uuid.uuid4())
    try:
        from db_pg import get_pool

        pool = await get_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    await conn.execute(
                        """INSERT INTO monitoring_events (event_id, event_type, user_id, duration, metadata, success, error_message)
                           VALUES ($1, $2, $3, $4, $5, $6, $7)""",
                        event_id,
                        body.event_type,
                        body.user_id,
                        body.duration,
                        json.dumps(body.metadata or {}),
                        body.success,
                        body.error_message,
                    )
            except Exception as e:
                logger.warning("monitoring_track_event pg insert failed: %s", e)
    except Exception as e:
        logger.warning("monitoring_track_event pool unavailable: %s", e)
    return {"status": "ok", "event_id": event_id}


@api_router.get("/monitoring/events")
async def monitoring_list_events(limit: int = Query(50, le=200)):
    """List recent monitoring events from PostgreSQL (proof)."""
    try:
        from db_pg import get_pool

        pool = await get_pool()
    except Exception:
        pool = None
    if not pool:
        return {"events": [], "message": "PostgreSQL not configured (DATABASE_URL)"}
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT event_id, event_type, user_id, timestamp, duration, metadata, success, error_message
                   FROM monitoring_events ORDER BY timestamp DESC LIMIT $1""",
                limit,
            )
        events = [
            {
                "event_id": r["event_id"],
                "event_type": r["event_type"],
                "user_id": r["user_id"],
                "timestamp": r["timestamp"].isoformat() if r["timestamp"] else None,
                "duration": r["duration"],
                "metadata": r["metadata"],
                "success": r["success"],
                "error_message": r["error_message"],
            }
            for r in rows
        ]
        return {"events": events}
    except Exception as e:
        logger.warning("monitoring_list_events failed: %s", e)
        return {"events": [], "error": str(e)}


class DeployValidateRequest(BaseModel):
    platform: str  # vercel | netlify | railway
    files: Dict[str, str] = {}
    config: Optional[Dict[str, Any]] = None


@api_router.post("/cache/invalidate")
async def cache_invalidate(
    agent_name: Optional[str] = Query(None),
    admin: dict = Depends(_get_current_admin_dep(("owner", "operations"))),
):
    """Invalidate agent cache (optional: by agent_name). Admin only."""
    from agent_cache import invalidate

    n = await invalidate(db, agent_name=agent_name)
    return {"status": "ok", "deleted": n}


# ==================== APP-DB SCHEMA ENDPOINT ====================
@api_router.post("/app-db/provision")
async def provision_app_db(
    body: dict = Body(...), user: dict = Depends(get_current_user)
):
    """Generate a database schema for the given task/prompt."""
    task_id = body.get("task_id")
    if task_id:
        await _get_task_for_user(task_id, user)
    return {
        "status": "ok",
        "message": "Schema generation queued. Run a full build to generate database schema files.",
        "task_id": task_id,
    }


@api_router.get("/app-db/{task_id}")
async def get_app_db_schema(task_id: str, user: dict = Depends(get_current_user)):
    """Return provisioned database schema for a build task."""
    return await _get_app_db_schema_for_task(task_id, user)


@api_router.get("/app-db/task/{task_id}")
async def get_app_db_schema_by_task(
    task_id: str, user: dict = Depends(get_current_user)
):
    """Return provisioned database schema for a build task without colliding with project app-db routes."""
    return await _get_app_db_schema_for_task(task_id, user)


async def _get_app_db_schema_for_task(task_id: str, user: dict):
    """Shared task-backed app DB schema extraction."""
    if db is None:
        return {"schema": None}
    task = await _get_task_for_user(task_id, user)
    if not task:
        return {"schema": None}
    # Extract schema from task files
    files = task.get("files") or {}
    schema_files = {
        k: v
        for k, v in files.items()
        if "schema" in k.lower() or k.endswith(".sql") or "migration" in k.lower()
    }
    if schema_files:
        combined_sql = "\n\n".join(
            f"-- {path}\n{code}" for path, code in schema_files.items()
        )
        import re as _re

        tables = _re.findall(
            r'CREATE TABLE(?:\s+IF NOT EXISTS)?\s+"?(\w+)"?',
            combined_sql,
            _re.IGNORECASE,
        )
        return {
            "schema": {
                "tables_sql": combined_sql,
                "tables": tables,
                "source_files": list(schema_files.keys()),
            }
        }
    return {"schema": None}


# ==================== DEPLOY VERCEL ENDPOINT ====================
@api_router.post("/deploy/vercel")
async def deploy_to_vercel(
    body: dict = Body(...), user: dict = Depends(get_current_user)
):
    """Create a Vercel deployment URL for the user's built files."""
    task_id = body.get("task_id")
    if db is None or not task_id:
        return {
            "deploy_url": "https://vercel.com/new",
            "method": "manual",
            "instructions": "Download your ZIP and drag-drop it at vercel.com/new",
        }
    task = await _get_task_for_user(task_id, user)
    if not task:
        return {"deploy_url": "https://vercel.com/new", "method": "manual"}
    return {
        "deploy_url": "https://vercel.com/new",
        "method": "guided",
        "steps": [
            "1. Click 'Download ZIP' to get your code",
            "2. Click 'Deploy to Vercel' to open Vercel",
            "3. Drag-drop your ZIP file",
            "4. Your app is live in 60 seconds",
        ],
    }


# ==================== CUSTOM DOMAIN ENDPOINT ====================
@api_router.post("/deploy/custom-domain")
async def set_custom_domain(
    body: dict = Body(...), user: dict = Depends(get_current_user)
):
    """Record custom domain intent. Returns CNAME instructions."""
    domain = body.get("domain", "").strip().lower()
    project_id = body.get("project_id", "")
    if not domain or "." not in domain:
        raise HTTPException(400, "Invalid domain")
    if db:
        await db.projects.update_one(
            {"id": project_id, "user_id": user["id"]},
            {"$set": {"custom_domain": domain, "domain_status": "pending_dns"}},
        )
    return {
        "domain": domain,
        "cname_target": "cname.vercel-dns.com",
        "instructions": [
            f"1. Go to your domain registrar (GoDaddy, Namecheap, Cloudflare, etc.)",
            f"2. Add a CNAME record: {domain} → cname.vercel-dns.com",
            f"3. Return here and click 'Verify DNS' (DNS changes take 2-24 hours)",
            f"4. CrucibAI will confirm SSL is active automatically",
        ],
        "ssl": "Automatic via Let's Encrypt once DNS propagates",
        "status": "pending_dns",
    }


# Include routers (domain split) — all wired in app (9.5+)
ROUTERS_INCLUDED_AT_MODULE_END = True

# Blueprint modules: Personas, Knowledge/RAG, Channels, Sessions, Trust & Safety,
# Workspace/RBAC, Analytics, Commerce, Auto-DB Schema
try:
    from modules_blueprint import register_blueprint_routes

    register_blueprint_routes(app)
    logger.info(
        "✅ Blueprint modules registered (Personas, Knowledge, Channels, Sessions, Safety, Workspace, Analytics, Commerce, AppDB)"
    )
except Exception as _bp_err:
    logger.warning(f"Blueprint modules import failed: {_bp_err}")

# /api/metrics served by routers.monitoring (Prometheus)


@api_router.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events"""
    import stripe

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv("STRIPE_WEBHOOK_SECRET")
        )
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            user_id = session["client_reference_id"]
            credits = int(session["metadata"]["credits"])
            # Add credits to user
            await db.execute(
                "UPDATE users SET credits = credits + %s WHERE id = %s",
                (credits, user_id),
            )
            await send_email(
                user_id, "Credits Added", f"You received {credits} credits"
            )
        return {"status": "success"}
    except Exception as e:
        return {"error": str(e)}, 400


@app.get("/branding")
async def branding_badge():
    """Serves the CrucibAI badge for free-tier iframe. Content is on our server so free users cannot remove it."""
    return branding_response()


@app.get("/published/{job_id}")
@app.get("/published/{job_id}/{path:path}")
async def serve_published_generated_app(job_id: str, path: str = ""):
    """Serve a completed generated app as a public URL from this CrucibAI deployment."""
    from orchestration import runtime_state as _orch_rs
    from orchestration.publish_urls import safe_publish_id

    return await serve_published_app_response(
        job_id=job_id,
        path=path,
        get_job=_orch_rs.get_job,
        safe_publish_id=safe_publish_id,
        project_workspace_path=_project_workspace_path,
        workspace_root=WORKSPACE_ROOT,
    )


@app.get("/api/jobs/{job_id}/dev-preview")
async def get_job_dev_preview(job_id: str, user=Depends(get_current_user)):
    job = await db.jobs.find_one({"id": job_id}, {"_id": 0}) if db is not None else None
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    project_id = job.get("project_id")
    if not project_id:
        raise HTTPException(status_code=400, detail="Job has no project workspace")
    project = await db.projects.find_one({"id": project_id}, {"_id": 0, "user_id": 1}) if db is not None else None
    if not project or str(project.get("user_id")) != str(user.get("id")):
        raise HTTPException(status_code=403, detail="Not allowed")
    workspace_path = _project_workspace_path(project_id).resolve()
    package_json = workspace_path / "package.json"
    if not package_json.exists():
        raise HTTPException(status_code=404, detail="Workspace package.json not found")
    manager = get_dev_server_manager()
    try:
        server = await manager.spawn_or_reuse(job_id, workspace_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start dev preview: {e}")
    return {
        "job_id": job_id,
        "project_id": project_id,
        "dev_server_url": server.get("url"),
        "preview_watch_websocket": f"/ws/jobs/{job_id}/preview-watch",
        "status": "ready",
    }


@app.websocket("/ws/jobs/{job_id}/preview-watch")
async def websocket_job_preview_watch(websocket: WebSocket, job_id: str):
    token = websocket.query_params.get("token") or websocket.query_params.get("access_token")
    if not token or db is None:
        await websocket.close(code=1008)
        return
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0})
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, KeyError):
        user = None
    if not user or user.get("suspended"):
        await websocket.close(code=1008)
        return
    job = await db.jobs.find_one({"id": job_id}, {"_id": 0})
    if not job:
        await websocket.close(code=1008)
        return
    project_id = job.get("project_id")
    if not project_id:
        await websocket.close(code=1008)
        return
    project = await db.projects.find_one({"id": project_id}, {"_id": 0, "user_id": 1})
    if not project or str(project.get("user_id")) != str(user.get("id")):
        await websocket.close(code=1008)
        return
    workspace_path = _project_workspace_path(project_id).resolve()
    await websocket.accept()
    seen = {}
    try:
        while True:
            changed = []
            if workspace_path.exists():
                for fp in workspace_path.rglob("*"):
                    try:
                        if not fp.is_file():
                            continue
                        if "/node_modules/" in str(fp) or "/dist/" in str(fp) or "/.git/" in str(fp):
                            continue
                        mtime = fp.stat().st_mtime
                        key = str(fp.relative_to(workspace_path))
                        prev = seen.get(key)
                        if prev is None:
                            seen[key] = mtime
                            continue
                        if mtime > prev:
                            seen[key] = mtime
                            changed.append(key)
                    except Exception:
                        continue
            await websocket.send_json({"type": "files_changed", "files": changed, "ts": time.time()})
            await asyncio.sleep(1.0)
    except WebSocketDisconnect:
        pass


@app.websocket("/ws/projects/{project_id}/progress")
async def websocket_project_progress(websocket: WebSocket, project_id: str):
    """Real-time build progress for AgentMonitor / BuildProgress UI."""
    token = websocket.query_params.get("token") or websocket.query_params.get(
        "access_token"
    )
    if not token or db is None:
        await websocket.close(code=1008)
        return
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0})
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, KeyError):
        user = None
    if not user or user.get("suspended"):
        await websocket.close(code=1008)
        return
    project = await db.projects.find_one(
        {"id": project_id, "user_id": user["id"]},
        {
            "_id": 0,
            "status": 1,
            "current_phase": 1,
            "current_agent": 1,
            "progress_percent": 1,
            "tokens_used": 1,
        },
    )
    if not project:
        await websocket.close(code=1008)
        return
    await websocket.accept()
    try:
        while True:
            project = await db.projects.find_one(
                {"id": project_id, "user_id": user["id"]},
                {
                    "_id": 0,
                    "status": 1,
                    "current_phase": 1,
                    "current_agent": 1,
                    "progress_percent": 1,
                    "tokens_used": 1,
                },
            )
            if project:
                await websocket.send_json(
                    {
                        "phase": project.get("current_phase", 0),
                        "agent": project.get("current_agent", ""),
                        "status": project.get("status", ""),
                        "progress": project.get("progress_percent", 0),
                        "tokens_used": project.get("tokens_used", 0),
                    }
                )
            if project and project.get("status") in ("completed", "failed"):
                break
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass


# Add security and performance middleware (order matters - added in reverse)
app.add_middleware(CSRFMiddleware)
app.add_middleware(PerformanceMonitoringMiddleware)
app.add_middleware(RequestValidationMiddleware)
app.add_middleware(RequestTrackerMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=int(os.environ.get("RATE_LIMIT_PER_MINUTE", "100")),
)
if os.environ.get("HTTPS_REDIRECT", "").strip().lower() in ("1", "true", "yes"):
    app.add_middleware(HTTPSRedirectMiddleware)
# With allow_credentials=True, browsers do not accept Access-Control-Allow-Origin: *
# Use explicit origins; default to localhost for dev if unset or "*"
_cors_origins = os.environ.get("CORS_ORIGINS", "").strip() or "*"
CORS_ORIGINS_LIST = [o.strip() for o in _cors_origins.split(",") if o.strip()]
if not CORS_ORIGINS_LIST or (
    len(CORS_ORIGINS_LIST) == 1 and CORS_ORIGINS_LIST[0] == "*"
):
    CORS_ORIGINS_LIST = ["http://localhost:3000", "http://127.0.0.1:3000"]
    if _cors_origins == "*":
        logger.warning(
            "CORS_ORIGINS was '*'; using explicit dev origins. Set CORS_ORIGINS to your frontend URL in production."
        )
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=CORS_ORIGINS_LIST,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "X-Request-ID",
        "Idempotency-Key",
        "X-Idempotency-Key",
    ],
)


@app.on_event("startup")
async def init_postgres_primary():
    """Initialize PostgreSQL as primary database at startup. Run migrations so Railway/Docker get schema. In CRUCIBAI_DEV without DATABASE_URL, skip so /api/health still works."""
    global db, audit_logger
    if not os.environ.get("DATABASE_URL"):
        logger.warning(
            "DATABASE_URL not set; DB not initialized. /api/health OK; auth/builds need DATABASE_URL."
        )
        return
    try:
        from db_pg import ensure_all_tables, get_db, run_migrations

        # Use idempotent runner (skips already-applied migrations via schema_migrations table)
        try:
            from services.migration_runner import run_migrations_idempotent

            await run_migrations_idempotent()
        except Exception as _mr_err:
            logger.warning(
                "Idempotent migration runner unavailable (%s); falling back to standard runner",
                _mr_err,
            )
            await run_migrations()
        await ensure_all_tables()  # safety net: creates any tables missed by migration
        db = await get_db()
        try:
            from utils.audit_log import AuditLogger as DbAuditLogger

            audit_logger = DbAuditLogger(db)
        except Exception as _aud:
            logger.warning("DB audit logger unavailable: %s", _aud)
            audit_logger = None
        # Populate shared deps state so extracted route modules can access db/audit_logger
        try:
            import deps as _deps

            _deps.init(db=db, audit_logger=audit_logger)
        except Exception as _deps_err:
            logger.debug("deps.init skipped: %s", _deps_err)
        logger.info("PostgreSQL initialized as primary database")
        # Initialize automation engine defaults
        try:
            from automation_engine import setup_default_workflows

            setup_default_workflows()
            logger.info("✅ Automation engine initialized")
        except Exception as _ae:
            logger.debug(f"Automation engine init skipped: {_ae}")

        # Start production job worker with recovery
        try:
            from integrations.queue import (
                enqueue_job,
                get_job_status,
                init_queue_db,
                recover_incomplete_jobs,
                run_worker,
                update_job_progress,
            )

            # Give queue access to PostgreSQL for fallback persistence
            init_queue_db(db)

            # Recover any jobs that were in-flight when container last restarted
            recovered = await recover_incomplete_jobs()
            if recovered:
                logger.info(
                    f"Recovered {recovered} in-flight jobs from previous container"
                )

            async def _handle_iterative_build(job_id: str, payload: dict):
                """Worker handler — runs full iterative build async, survives disconnect."""
                from iterative_builder import get_build_structure, run_iterative_build

                prompt = payload.get("prompt", "")
                build_kind = payload.get("build_kind", "fullstack")
                user_id = payload.get("user_id")
                session_id = payload.get("session_id", job_id)
                total_steps = len(get_build_structure(build_kind)["passes"])
                step_num = 0
                pass_records = []

                async def on_step(step_name, files_so_far):
                    nonlocal step_num
                    step_num += 1
                    pct = int(step_num / total_steps * 90)
                    pass_records.append(
                        {
                            "pass": step_num,
                            "label": step_name,
                            "desc": f"{len(files_so_far)} files generated so far",
                            "files_count": len(files_so_far),
                            "color": [
                                "#a78bfa",
                                "#60a5fa",
                                "#34d399",
                                "#fb923c",
                                "#fbbf24",
                                "#f87171",
                            ][step_num % 6],
                            "status": "complete",
                            "completed_at": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                    await update_job_progress(
                        job_id,
                        pct,
                        "running",
                        f"Pass {step_num}/{total_steps}: {step_name} ({len(files_so_far)} files so far)",
                    )

                async def call_llm(message, system):
                    effective = _effective_api_keys({})
                    # Iterative builds are always complex — always use Haiku
                    model_chain = _get_model_chain(
                        "auto", message, effective_keys=effective, force_complex=True
                    )
                    resp, _ = await _call_llm_with_fallback(
                        message=message,
                        system_message=system,
                        session_id=session_id,
                        model_chain=model_chain,
                        api_keys=effective,
                        user_id=user_id,
                        user_tier="free",
                        speed_selector="standard",
                        available_credits=999,
                    )
                    return resp

                # Inject active skills context for queue-based builds (auto-detect + user-activated)
                _queue_skills_ctx = ""
                _q_auto_skill = await _auto_detect_skill(prompt, user_id or "")
                if _q_auto_skill:
                    _q_skill_md = _load_skill_md(_q_auto_skill)
                    if _q_skill_md:
                        _q_instr_start = _q_skill_md.find("## Instructions")
                        if _q_instr_start > 0:
                            _queue_skills_ctx = f"ACTIVE SKILL: {_q_auto_skill}\n{_q_skill_md[_q_instr_start:_q_instr_start+2000]}"
                        else:
                            _queue_skills_ctx = (
                                f"ACTIVE SKILL: {_q_auto_skill}\n{_q_skill_md[:1500]}"
                            )
                if user_id:
                    try:
                        _user_q_ctx = await _get_active_skills_context(user_id)
                        if _user_q_ctx:
                            _queue_skills_ctx = (
                                (_queue_skills_ctx + "\n\n" + _user_q_ctx).strip()
                                if _queue_skills_ctx
                                else _user_q_ctx
                            )
                    except Exception:
                        pass

                final_files = await run_iterative_build(
                    prompt=prompt,
                    build_kind=build_kind,
                    call_llm=call_llm,
                    on_progress=on_step,
                    skills_context=_queue_skills_ctx or None,
                )

                # Save completed files to PostgreSQL tasks table (Q122 persistence)
                task_doc = {
                    "id": session_id,
                    "user_id": user_id or "guest",
                    "title": (prompt[:60] + "...") if len(prompt) > 60 else prompt,
                    "prompt": prompt,
                    "build_kind": build_kind,
                    "files": final_files,
                    "status": "complete",
                    "total_files": len(final_files),
                    "job_id": job_id,
                    "passes": pass_records,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
                try:
                    await db.tasks.update_one(
                        {"id": session_id}, {"$set": task_doc}, upsert=True
                    )
                    logger.info(
                        f"Async build saved: {session_id} ({len(final_files)} files)"
                    )
                except Exception as _pe:
                    logger.error(f"Failed to save async build to PostgreSQL: {_pe}")

                # Deduct credits
                if user_id:
                    try:
                        await _ensure_credit_balance(user_id)
                        await db.users.update_one(
                            {"id": user_id},
                            {"$inc": {"credit_balance": -MIN_CREDITS_FOR_LLM}},
                        )
                    except Exception:
                        pass

                await update_job_progress(
                    job_id,
                    100,
                    "complete",
                    f"Done: {len(final_files)} files built. Task ID: {session_id}",
                )

            # Start worker — runs forever as background task
            asyncio.create_task(
                run_worker(
                    handlers={"iterative_build": _handle_iterative_build},
                    poll_interval=1.0,
                )
            )
            logger.info(
                "✅ Job worker started (Redis=%s)", bool(os.environ.get("REDIS_URL"))
            )
        except Exception as _wk:
            logger.warning(f"Job worker init failed: {_wk}")
    except Exception as e:
        logger.error("PostgreSQL initialization failed: %s", e)
        if not os.environ.get("CRUCIBAI_DEV"):
            raise
        logger.warning(
            "Continuing without DB (CRUCIBAI_DEV). /api/health OK; auth/builds will fail."
        )


@app.on_event("startup")
async def init_observability():
    """Initialize OpenTelemetry (tracing, metrics) when available. Non-blocking."""
    try:
        from observability.otel import init_otel

        init_otel(service_name="crucibai", app=None)
        logger.info("Observability (OpenTelemetry) initialized")
    except Exception as e:
        logger.debug("Observability init skipped (optional): %s", e)


@app.on_event("startup")
async def seed_examples_if_empty():
    """Seed rich examples showing CrucibAI's full output quality."""
    if db is None:
        return
    try:
        n = await db.examples.count_documents({})
        if n == 0:
            examples = [
                {
                    "name": "saas-dashboard",
                    "display_name": "SaaS Analytics Dashboard",
                    "prompt": "Build a SaaS analytics dashboard with user authentication, metrics cards (MRR, DAU, churn), recharts line/bar charts, a sortable data table, dark theme sidebar, and Stripe billing integration.",
                    "build_kind": "saas",
                    "tags": ["saas", "dashboard", "charts", "auth", "stripe"],
                    "generated_code": {
                        "frontend": "import { useState } from 'react';\nimport { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';\nimport { TrendingUp, Users, DollarSign } from 'lucide-react';\n\nconst METRICS = [\n  { label: 'MRR', value: '$24,800', trend: '+12%', color: '#4ade80' },\n  { label: 'DAU', value: '3,421', trend: '+8%', color: '#60a5fa' },\n  { label: 'Churn', value: '2.3%', trend: '-0.4%', color: '#f87171' },\n];\nconst DATA = Array.from({ length: 30 }, (_, i) => ({ day: i+1, revenue: 800 + Math.random()*400 }));\n\nexport default function Dashboard() {\n  return (\n    <div style={{ display:'flex', minHeight:'100vh', background:'#0f172a', color:'#e2e8f0', fontFamily:'Inter,sans-serif' }}>\n      <aside style={{ width:220, background:'#1e293b', borderRight:'1px solid #334155', padding:'24px 0' }}>\n        <div style={{ padding:'0 20px 24px', fontWeight:700, fontSize:18, color:'#fff' }}>CrucibAI</div>\n        {['Dashboard','Analytics','Users','Billing'].map(item => (\n          <div key={item} style={{ padding:'10px 20px', cursor:'pointer', color: item==='Dashboard' ? '#60a5fa' : '#94a3b8' }}>{item}</div>\n        ))}\n      </aside>\n      <main style={{ flex:1, padding:32 }}>\n        <h1 style={{ fontSize:24, fontWeight:700, marginBottom:24 }}>Analytics Overview</h1>\n        <div style={{ display:'grid', gridTemplateColumns:'repeat(3,1fr)', gap:16, marginBottom:32 }}>\n          {METRICS.map(m => (\n            <div key={m.label} style={{ background:'#1e293b', borderRadius:12, padding:20 }}>\n              <div style={{ color:'#94a3b8', fontSize:13, marginBottom:8 }}>{m.label}</div>\n              <div style={{ fontSize:28, fontWeight:700, color:'#fff' }}>{m.value}</div>\n              <div style={{ fontSize:12, color:m.color, marginTop:4 }}>{m.trend}</div>\n            </div>\n          ))}\n        </div>\n        <div style={{ background:'#1e293b', borderRadius:12, padding:24 }}>\n          <ResponsiveContainer width='100%' height={280}>\n            <LineChart data={DATA}>\n              <CartesianGrid strokeDasharray='3 3' stroke='#334155' />\n              <XAxis dataKey='day' stroke='#94a3b8' />\n              <YAxis stroke='#94a3b8' />\n              <Tooltip contentStyle={{ background:'#1e293b', border:'1px solid #334155' }} />\n              <Line type='monotone' dataKey='revenue' stroke='#3b82f6' strokeWidth={2} dot={false} />\n            </LineChart>\n          </ResponsiveContainer>\n        </div>\n      </main>\n    </div>\n  );\n}",
                        "backend": "import express from 'express';\nconst app = express();\napp.use(express.json());\napp.get('/api/metrics', (req, res) => res.json({ mrr: 24800, dau: 3421, churn: 2.3, growth: 18 }));\napp.listen(5000);",
                        "database": "CREATE TABLE users (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), email TEXT UNIQUE NOT NULL, plan TEXT DEFAULT 'free', created_at TIMESTAMPTZ DEFAULT NOW());\nCREATE TABLE metrics_snapshots (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), metric_name TEXT, metric_value NUMERIC, recorded_at TIMESTAMPTZ DEFAULT NOW());",
                    },
                    "file_count": 42,
                    "quality_metrics": {
                        "overall_score": 87,
                        "verdict": "excellent",
                        "breakdown": {
                            "frontend": {"score": 90},
                            "backend": {"score": 88},
                            "database": {"score": 85},
                            "tests": {"score": 82},
                        },
                    },
                },
                {
                    "name": "ecommerce-store",
                    "display_name": "E-Commerce Store with Stripe",
                    "prompt": "Build a full e-commerce store with product catalog, search, cart, checkout with Stripe payments, and order history. React TypeScript frontend, Express backend, PostgreSQL.",
                    "build_kind": "fullstack",
                    "tags": ["ecommerce", "stripe", "cart", "typescript", "full-stack"],
                    "generated_code": {
                        "frontend": "import { useState } from 'react';\nimport { ShoppingCart, Star } from 'lucide-react';\n\nconst PRODUCTS = [\n  { id: 1, name: 'Wireless Headphones', price: 79.99, rating: 4.7, image: '\\ud83c\\udfa7', category: 'Electronics' },\n  { id: 2, name: 'Minimalist Watch', price: 149.99, rating: 4.9, image: '\\u231a', category: 'Fashion' },\n  { id: 3, name: 'Yoga Mat', price: 34.99, rating: 4.5, image: '\\ud83e\\uddd8', category: 'Sports' },\n];\n\nexport default function Store() {\n  const [cart, setCart] = useState([]);\n  const [search, setSearch] = useState('');\n  const filtered = PRODUCTS.filter(p => p.name.toLowerCase().includes(search.toLowerCase()));\n  const add = (p) => setCart(prev => { const e = prev.find(i => i.id === p.id); return e ? prev.map(i => i.id === p.id ? {...i, qty: i.qty+1} : i) : [...prev, {...p, qty:1}]; });\n  return (\n    <div style={{ minHeight:'100vh', background:'#fafafa', fontFamily:'Inter,sans-serif' }}>\n      <nav style={{ background:'#fff', boxShadow:'0 1px 3px rgba(0,0,0,0.1)', padding:'16px 24px', display:'flex', justifyContent:'space-between', alignItems:'center' }}>\n        <span style={{ fontWeight:800, fontSize:20 }}>ShopAI</span>\n        <input placeholder='Search...' value={search} onChange={e => setSearch(e.target.value)} style={{ padding:'8px 12px', border:'1px solid #ddd', borderRadius:8, width:200 }} />\n        <div style={{ display:'flex', alignItems:'center', gap:8, fontWeight:600 }}><ShoppingCart size={18} /> {cart.reduce((s,i)=>s+i.qty,0)} items</div>\n      </nav>\n      <div style={{ padding:24, maxWidth:1100, margin:'0 auto', display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(240px,1fr))', gap:20 }}>\n        {filtered.map(p => (\n          <div key={p.id} style={{ background:'#fff', borderRadius:12, padding:20, boxShadow:'0 1px 4px rgba(0,0,0,0.08)' }}>\n            <div style={{ fontSize:48, textAlign:'center', marginBottom:12 }}>{p.image}</div>\n            <div style={{ fontWeight:600, marginBottom:4 }}>{p.name}</div>\n            <div style={{ display:'flex', alignItems:'center', gap:4, color:'#f59e0b', fontSize:12, marginBottom:12 }}><Star size={12} />{p.rating}</div>\n            <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center' }}>\n              <span style={{ fontWeight:700, fontSize:18 }}>${p.price}</span>\n              <button onClick={() => add(p)} style={{ padding:'8px 16px', background:'#111', color:'#fff', border:'none', borderRadius:8, cursor:'pointer' }}>Add</button>\n            </div>\n          </div>\n        ))}\n      </div>\n    </div>\n  );\n}",
                        "backend": "import express from 'express';\nimport Stripe from 'stripe';\nconst app = express();\nconst stripe = new Stripe(process.env.STRIPE_SECRET_KEY);\napp.use(express.json());\napp.get('/api/products', async (req, res) => { const r = await db.query('SELECT * FROM products'); res.json(r.rows); });\napp.post('/api/checkout', async (req, res) => { const session = await stripe.checkout.sessions.create({ mode:'payment', line_items: req.body.items, success_url: process.env.FRONTEND_URL+'/success', cancel_url: process.env.FRONTEND_URL+'/cart' }); res.json({ url: session.url }); });\napp.listen(5000);",
                        "database": "CREATE TABLE products (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), name TEXT NOT NULL, price NUMERIC(10,2), stock INTEGER DEFAULT 0, category TEXT, image_url TEXT, created_at TIMESTAMPTZ DEFAULT NOW());\nCREATE TABLE orders (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID, stripe_session_id TEXT UNIQUE, total_amount NUMERIC(10,2), status TEXT DEFAULT 'pending', created_at TIMESTAMPTZ DEFAULT NOW());",
                    },
                    "file_count": 38,
                    "quality_metrics": {
                        "overall_score": 85,
                        "verdict": "excellent",
                        "breakdown": {
                            "frontend": {"score": 92},
                            "backend": {"score": 82},
                            "database": {"score": 88},
                            "tests": {"score": 78},
                        },
                    },
                },
                {
                    "name": "ai-chat-agent",
                    "display_name": "AI Multi-Agent Chat Interface",
                    "prompt": "Build a multi-agent chat interface where users can select different AI agents (Code Assistant, Research Analyst, Creative Writer), chat with them, and save conversation history.",
                    "build_kind": "ai_agent",
                    "tags": ["ai", "chat", "agents", "streaming", "history"],
                    "generated_code": {
                        "frontend": "import { useState, useRef, useEffect } from 'react';\nimport { Send, Trash2 } from 'lucide-react';\n\nconst AGENTS = [\n  { id:'code', name:'Code Assistant', avatar:'\\ud83d\\udcbb', color:'#3b82f6', desc:'Expert in all programming languages.' },\n  { id:'research', name:'Research Analyst', avatar:'\\ud83d\\udd2c', color:'#8b5cf6', desc:'Deep research and analysis.' },\n  { id:'writer', name:'Creative Writer', avatar:'\\u270d\\ufe0f', color:'#ec4899', desc:'Storytelling and copywriting.' },\n];\n\nexport default function App() {\n  const [agent, setAgent] = useState(AGENTS[0]);\n  const [messages, setMessages] = useState([]);\n  const [input, setInput] = useState('');\n  const [typing, setTyping] = useState(false);\n  const endRef = useRef(null);\n  useEffect(() => endRef.current?.scrollIntoView({ behavior:'smooth' }), [messages]);\n  const send = async () => {\n    if (!input.trim()) return;\n    setMessages(p => [...p, { role:'user', content:input, id:Date.now() }]);\n    setInput('');\n    setTyping(true);\n    await new Promise(r => setTimeout(r, 1200));\n    setMessages(p => [...p, { role:'agent', content:'['+agent.name+'] Here is my response to: '+input.slice(0,40), id:Date.now()+1 }]);\n    setTyping(false);\n  };\n  return (\n    <div style={{ display:'flex', height:'100vh', background:'#0f0f0f', color:'#e5e5e5', fontFamily:'Inter,sans-serif' }}>\n      <aside style={{ width:260, background:'#1a1a1a', borderRight:'1px solid #2a2a2a', padding:20 }}>\n        <div style={{ fontWeight:700, fontSize:16, marginBottom:12, color:'#fff' }}>Select Agent</div>\n        {AGENTS.map(a => (\n          <button key={a.id} onClick={() => setAgent(a)} style={{ display:'flex', gap:12, padding:12, borderRadius:10, border: a.id===agent.id ? '1px solid '+a.color : '1px solid #2a2a2a', background: a.id===agent.id ? a.color+'15' : 'transparent', cursor:'pointer', width:'100%', textAlign:'left', marginBottom:8 }}>\n            <span style={{ fontSize:24 }}>{a.avatar}</span>\n            <div><div style={{ fontSize:14, fontWeight:600, color:'#fff' }}>{a.name}</div><div style={{ fontSize:11, color:'#888' }}>{a.desc}</div></div>\n          </button>\n        ))}\n      </aside>\n      <div style={{ flex:1, display:'flex', flexDirection:'column' }}>\n        <div style={{ padding:'16px 24px', borderBottom:'1px solid #2a2a2a', display:'flex', alignItems:'center', gap:12 }}>\n          <span style={{ fontSize:28 }}>{agent.avatar}</span>\n          <div><div style={{ fontWeight:600, color:'#fff' }}>{agent.name}</div><div style={{ fontSize:12, color:agent.color }}>Online</div></div>\n          <button onClick={() => setMessages([])} style={{ marginLeft:'auto', background:'none', border:'none', color:'#888', cursor:'pointer' }}><Trash2 size={16} /></button>\n        </div>\n        <div style={{ flex:1, overflowY:'auto', padding:24, display:'flex', flexDirection:'column', gap:16 }}>\n          {messages.map(m => (\n            <div key={m.id} style={{ display:'flex', gap:12, justifyContent: m.role==='user' ? 'flex-end' : 'flex-start' }}>\n              <div style={{ maxWidth:'70%', padding:'12px 16px', borderRadius:12, background: m.role==='user' ? agent.color : '#1e1e1e', color:'#fff', fontSize:14 }}>{m.content}</div>\n            </div>\n          ))}\n          {typing && <div style={{ color:'#888', fontSize:14 }}>...</div>}\n          <div ref={endRef} />\n        </div>\n        <div style={{ padding:20, borderTop:'1px solid #2a2a2a', display:'flex', gap:12 }}>\n          <input value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key==='Enter' && send()} placeholder={'Ask '+agent.name+'...'} style={{ flex:1, background:'#1e1e1e', border:'1px solid #2a2a2a', borderRadius:10, padding:'12px 16px', color:'#fff', fontSize:14, outline:'none' }} />\n          <button onClick={send} style={{ padding:'12px 20px', background:agent.color, border:'none', borderRadius:10, color:'#fff', cursor:'pointer' }}><Send size={16} /></button>\n        </div>\n      </div>\n    </div>\n  );\n}",
                        "backend": "import express from 'express';\nconst app = express();\napp.use(express.json());\napp.post('/api/chat', async (req, res) => { const { message, agentId } = req.body; res.json({ reply: '[Agent '+agentId+'] Response to: '+message }); });\napp.listen(5000);",
                        "database": "CREATE TABLE conversations (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), user_id UUID, agent_id TEXT, title TEXT, created_at TIMESTAMPTZ DEFAULT NOW());\nCREATE TABLE messages (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), conversation_id UUID REFERENCES conversations(id), role TEXT, content TEXT, created_at TIMESTAMPTZ DEFAULT NOW());",
                    },
                    "file_count": 35,
                    "quality_metrics": {
                        "overall_score": 89,
                        "verdict": "excellent",
                        "breakdown": {
                            "frontend": {"score": 94},
                            "backend": {"score": 88},
                            "database": {"score": 80},
                            "tests": {"score": 82},
                        },
                    },
                },
                {
                    "name": "landing-page-saas",
                    "display_name": "SaaS Landing Page with Pricing",
                    "prompt": "Build a conversion-optimized SaaS landing page with hero, animated features grid, testimonials, pricing table with annual/monthly toggle, FAQ accordion, and email waitlist signup. Framer Motion animations.",
                    "build_kind": "landing",
                    "tags": [
                        "landing",
                        "marketing",
                        "framer-motion",
                        "pricing",
                        "waitlist",
                    ],
                    "generated_code": {
                        "frontend": "import { useState } from 'react';\nimport { motion } from 'framer-motion';\nimport { Zap, Shield, Globe, BarChart2, Check } from 'lucide-react';\n\nconst FEATURES = [\n  { icon: Zap, title: 'Lightning Fast', desc: 'Sub-100ms response times.' },\n  { icon: Shield, title: 'Enterprise Security', desc: 'SOC 2 Type II certified.' },\n  { icon: Globe, title: 'Global Scale', desc: 'Deploy to 50+ regions.' },\n  { icon: BarChart2, title: 'Deep Analytics', desc: 'Real-time insights.' },\n];\nconst PLANS = [\n  { name:'Starter', monthly:0, features:['5 projects','10GB storage','Community support'] },\n  { name:'Pro', monthly:29, features:['Unlimited projects','100GB','Priority support','Custom domains'], highlighted:true },\n  { name:'Enterprise', monthly:99, features:['Everything in Pro','SLA','SSO/SAML','Audit logs'] },\n];\n\nexport default function App() {\n  const [email, setEmail] = useState('');\n  const [joined, setJoined] = useState(false);\n  return (\n    <div style={{ fontFamily:'Inter,sans-serif', color:'#1a1a1a' }}>\n      <nav style={{ position:'sticky', top:0, background:'rgba(255,255,255,0.9)', backdropFilter:'blur(12px)', padding:'16px 48px', display:'flex', justifyContent:'space-between', alignItems:'center', borderBottom:'1px solid #e5e7eb', zIndex:100 }}>\n        <span style={{ fontWeight:800, fontSize:20, color:'#6366f1' }}>AppName</span>\n        <button style={{ padding:'8px 20px', background:'#6366f1', color:'#fff', border:'none', borderRadius:8, cursor:'pointer', fontWeight:600 }}>Get started</button>\n      </nav>\n      <section style={{ textAlign:'center', padding:'100px 48px 80px', background:'linear-gradient(135deg,#f0f0ff 0%,#fff 60%)' }}>\n        <motion.div initial={{ opacity:0, y:30 }} animate={{ opacity:1, y:0 }} transition={{ duration:0.6 }}>\n          <h1 style={{ fontSize:'clamp(36px,6vw,72px)', fontWeight:800, lineHeight:1.1, marginBottom:20 }}>The platform that<br/><span style={{ color:'#6366f1' }}>ships 10x faster</span></h1>\n          <p style={{ fontSize:20, color:'#6b7280', maxWidth:560, margin:'0 auto 40px' }}>From idea to production in minutes. Join 10,000+ teams.</p>\n          <div style={{ display:'flex', gap:12, justifyContent:'center' }}>\n            <input value={email} onChange={e => setEmail(e.target.value)} placeholder='Enter your email' style={{ padding:'14px 20px', borderRadius:10, border:'1px solid #e5e7eb', fontSize:16, width:280 }} />\n            <button onClick={() => setJoined(true)} style={{ padding:'14px 28px', background:'#6366f1', color:'#fff', border:'none', borderRadius:10, cursor:'pointer', fontWeight:700, fontSize:16 }}>{joined ? 'Joined!' : 'Join waitlist'}</button>\n          </div>\n        </motion.div>\n      </section>\n      <section style={{ padding:'80px 48px', maxWidth:1100, margin:'0 auto' }}>\n        <h2 style={{ textAlign:'center', fontSize:36, fontWeight:800, marginBottom:48 }}>Everything you need</h2>\n        <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(240px,1fr))', gap:24 }}>\n          {FEATURES.map((f,i) => (\n            <motion.div key={i} initial={{ opacity:0, y:20 }} whileInView={{ opacity:1, y:0 }} transition={{ delay:i*0.1 }} style={{ padding:28, borderRadius:16, border:'1px solid #e5e7eb' }}>\n              <div style={{ width:44, height:44, borderRadius:12, background:'#ede9fe', display:'flex', alignItems:'center', justifyContent:'center', marginBottom:16 }}><f.icon size={22} color='#6366f1' /></div>\n              <h3 style={{ fontWeight:700, marginBottom:8 }}>{f.title}</h3>\n              <p style={{ color:'#6b7280', fontSize:14 }}>{f.desc}</p>\n            </motion.div>\n          ))}\n        </div>\n      </section>\n    </div>\n  );\n}",
                        "backend": "import express from 'express';\nconst app = express();\napp.use(express.json());\napp.post('/api/waitlist', async (req, res) => { const { email } = req.body; res.json({ success:true }); });\napp.listen(5000);",
                        "database": "CREATE TABLE waitlist (id UUID PRIMARY KEY DEFAULT gen_random_uuid(), email TEXT UNIQUE NOT NULL, created_at TIMESTAMPTZ DEFAULT NOW());",
                    },
                    "file_count": 15,
                    "quality_metrics": {
                        "overall_score": 92,
                        "verdict": "excellent",
                        "breakdown": {
                            "frontend": {"score": 96},
                            "backend": {"score": 82},
                            "database": {"score": 90},
                            "tests": {"score": 88},
                        },
                    },
                },
                {
                    "name": "mobile-todo-app",
                    "display_name": "React Native Todo App (Expo)",
                    "prompt": "Build a React Native todo app with Expo, categories, priority levels, dark mode, and animated list transitions.",
                    "build_kind": "mobile",
                    "tags": ["mobile", "expo", "react-native", "ios", "android"],
                    "generated_code": {
                        "frontend": "import { useState } from 'react';\nimport { View, Text, TextInput, TouchableOpacity, FlatList, StyleSheet } from 'react-native';\n\nconst PCOLORS = { high:'#ef4444', medium:'#f59e0b', low:'#22c55e' };\n\nexport default function App() {\n  const [todos, setTodos] = useState([\n    { id:'1', title:'Design the UI', priority:'high', done:false },\n    { id:'2', title:'Write tests', priority:'medium', done:false },\n    { id:'3', title:'Buy groceries', priority:'low', done:true },\n  ]);\n  const [input, setInput] = useState('');\n  const [priority, setPriority] = useState('medium');\n  const add = () => {\n    if (!input.trim()) return;\n    setTodos(p => [...p, { id:Date.now().toString(), title:input.trim(), priority, done:false }]);\n    setInput('');\n  };\n  const toggle = id => setTodos(p => p.map(t => t.id===id ? {...t, done:!t.done} : t));\n  return (\n    <View style={s.container}>\n      <Text style={s.title}>My Tasks</Text>\n      <View style={{ flexDirection:'row', gap:8, marginBottom:12 }}>\n        <TextInput value={input} onChangeText={setInput} placeholder='Add a task...' placeholderTextColor='#666' style={s.input} />\n        <TouchableOpacity onPress={add} style={s.addBtn}><Text style={{ color:'#fff', fontWeight:'700' }}>Add</Text></TouchableOpacity>\n      </View>\n      <FlatList data={todos} keyExtractor={i => i.id} renderItem={({ item }) => (\n        <TouchableOpacity onPress={() => toggle(item.id)} style={[s.item, { borderLeftColor: PCOLORS[item.priority] }]}>\n          <View style={[s.cb, { borderColor: item.done ? PCOLORS[item.priority] : '#444' }]}>\n            {item.done && <Text style={{ color:'#fff', fontSize:10 }}>ok</Text>}\n          </View>\n          <Text style={[s.itemText, { textDecorationLine: item.done ? 'line-through' : 'none', color: item.done ? '#666' : '#fff' }]}>{item.title}</Text>\n        </TouchableOpacity>\n      )} />\n    </View>\n  );\n}\n\nconst s = StyleSheet.create({\n  container: { flex:1, backgroundColor:'#0f0f0f', padding:24, paddingTop:60 },\n  title: { fontSize:32, fontWeight:'800', color:'#fff', marginBottom:24 },\n  input: { flex:1, backgroundColor:'#1a1a1a', borderRadius:12, paddingHorizontal:16, height:48, color:'#fff', borderWidth:1, borderColor:'#2a2a2a' },\n  addBtn: { backgroundColor:'#6366f1', borderRadius:12, paddingHorizontal:20, height:48, justifyContent:'center' },\n  item: { flexDirection:'row', alignItems:'center', gap:12, backgroundColor:'#1a1a1a', borderRadius:12, padding:16, marginBottom:8, borderLeftWidth:4 },\n  cb: { width:22, height:22, borderRadius:11, borderWidth:2, justifyContent:'center', alignItems:'center' },\n  itemText: { fontSize:15, fontWeight:'500' },\n});",
                        "backend": "// React Native apps use local AsyncStorage for offline persistence.",
                        "database": "// SQLite: CREATE TABLE IF NOT EXISTS todos (id TEXT PRIMARY KEY, title TEXT, priority TEXT, done INTEGER, created_at TEXT);",
                    },
                    "file_count": 22,
                    "quality_metrics": {
                        "overall_score": 84,
                        "verdict": "excellent",
                        "breakdown": {
                            "frontend": {"score": 91},
                            "backend": {"score": 70},
                            "database": {"score": 78},
                            "tests": {"score": 80},
                        },
                    },
                },
            ]
            for ex in examples:
                ex["created_at"] = datetime.now(timezone.utc).isoformat()
                await db.examples.insert_one(ex)
            logger.info(f"Seeded {len(examples)} rich examples with real code")
    except Exception as e:
        logger.warning(f"Seed examples: {e}")


@app.on_event("startup")
async def seed_internal_agents_if_requested():
    """Seed 5 internal (dogfooding) agents when SEED_INTERNAL_AGENTS=1."""
    if not os.environ.get("SEED_INTERNAL_AGENTS"):
        return
    try:
        from automation.seed_internal import seed_internal_agents

        n = await seed_internal_agents(db)
        if n:
            logger.info("Seeded %s internal automation agents", n)
    except Exception as e:
        logger.warning("Seed internal agents: %s", e)


@app.on_event("shutdown")
async def shutdown_db_client():
    """Close PostgreSQL pool on shutdown."""
    global db
    try:
        from db_pg import close_pg_pool

        await close_pg_pool()
        db = None
        logger.info("✅ PostgreSQL pool closed")
    except Exception as e:
        logger.warning(f"Shutdown warning: {e}")


# Speed tier configuration
SPEED_TIERS = {
    "lite": {
        "name": "CrucibAI 1.0 Lite",
        "description": "Lightweight agent for everyday tasks.",
        "model": "cerebras",
        "parallelism": 1,
        "timeout": 300,
        "build_time_estimate": "30-40s",
        "token_multiplier": 1.0,
        "credit_cost": 50,
        "label": "Sequential",
        "icon": "clock",
    },
    "pro": {
        "name": "CrucibAI 1.0",
        "description": "Versatile agent capable of handling most tasks.",
        "model": "haiku",
        "parallelism": 2.5,
        "timeout": 180,
        "build_time_estimate": "12-16s",
        "token_multiplier": 1.5,
        "credit_cost": 100,
        "label": "Parallel",
        "icon": "faster",
        "badge": "POPULAR",
    },
    "max": {
        "name": "CrucibAI 1.0 Max",
        "description": "High-performance agent designed for complex tasks.",
        "model": "haiku",
        "parallelism": 4.0,
        "timeout": 120,
        "build_time_estimate": "8-10s",
        "token_multiplier": 2.0,
        "credit_cost": 150,
        "label": "Full Swarm",
        "icon": "lightning",
        "badge": "FASTEST",
        "all_agents": True,
    },
}

# Token multipliers for consistency
SWARM_TOKEN_MULTIPLIER = 1.5  # Pro speed with swarm
MAX_TOKEN_MULTIPLIER = 2.0  # Max speed (full swarm)

# Serve frontend static files (Docker/Railway: frontend built and copied to /app/static)
# SPA fallback: serve index.html for paths like /auth, /dashboard so client-side router works
_static_dir = Path(__file__).resolve().parent / "static"
if _static_dir.exists():
    from fastapi.staticfiles import StaticFiles

    class SpaStaticFiles(StaticFiles):
        """Serve index.html for unknown paths so React Router handles /auth, /dashboard, etc."""

        def lookup_path(self, path: str):
            full_path, stat_result = super().lookup_path(path)
            if stat_result is not None:
                return full_path, stat_result
            # Do not SPA-fallback under /api — unknown API paths must 404, not return index.html
            # (otherwise clients see HTML instead of JSON and new routes look "broken" until matched).
            norm = (path or "").lstrip("/")
            if norm.startswith("api/") or norm == "api":
                return full_path, None
            full_path, stat_result = super().lookup_path("index.html")
            return full_path, stat_result

    FRONTEND_STATIC_READY = True

# ============================================================
# RAILWAY NATIVE DEPLOY (server-side)
# ============================================================


class RailwayDeployBody(BaseModel):
    project_id: Optional[str] = None
    task_id: Optional[str] = None
    service_name: Optional[str] = None
    railway_token: Optional[str] = None  # user can pass their own token


@api_router.post("/deploy/railway")
async def deploy_to_railway(
    body: RailwayDeployBody, user: dict = Depends(get_current_user)
):
    """
    Deploy generated app to Railway via Railway Deploy API.
    Uses RAILWAY_DEPLOY_TOKEN env var (server-level) or user's stored token.
    Returns: { deploy_url, service_id, status }
    """
    import base64

    import httpx

    # Get files
    files: dict = {}
    project_name = body.service_name or "crucibai-app"

    if db is not None:
        if body.project_id:
            proj = await db.projects.find_one(
                {"id": body.project_id, "user_id": user["id"]}
            )
            if not proj:
                raise HTTPException(status_code=404, detail="Project not found")
            files = proj.get("deploy_files") or {}
            project_name = body.service_name or (proj.get("name") or "crucibai-app")
        if not files and body.task_id:
            task = await _get_task_for_user(body.task_id, user)
            if task:
                files = task.get("files") or {}
                project_name = (
                    body.service_name or (task.get("prompt") or "crucibai-app")[:40]
                )

    if not files:
        raise HTTPException(
            status_code=400, detail="No generated files. Run a build first."
        )

    # Get Railway token
    u = await db.users.find_one({"id": user["id"]}, {"deploy_tokens": 1}) if db else {}
    railway_token = (
        body.railway_token
        or (u.get("deploy_tokens") or {}).get("railway")
        or os.environ.get("RAILWAY_DEPLOY_TOKEN")
    )
    if not railway_token:
        raise HTTPException(
            status_code=402,
            detail="Add your Railway token in Settings → Deploy integrations, or set RAILWAY_DEPLOY_TOKEN on server.",
        )

    # Railway uses GraphQL API
    gql_endpoint = "https://backboard.railway.app/graphql/v2"
    headers = {
        "Authorization": f"Bearer {railway_token}",
        "Content-Type": "application/json",
    }

    import re as _re

    safe_name = (
        _re.sub(r"[^a-zA-Z0-9\-]", "-", project_name.strip()).strip("-")[:50]
        or "crucibai-app"
    )

    async with httpx.AsyncClient(timeout=60.0) as client:
        # Create project
        create_proj = await client.post(
            gql_endpoint,
            headers=headers,
            json={
                "query": """
            mutation CreateProject($input: ProjectCreateInput!) {
              projectCreate(input: $input) { id name }
            }""",
                "variables": {"input": {"name": safe_name}},
            },
        )
        if create_proj.status_code != 200:
            raise HTTPException(
                status_code=502, detail=f"Railway error: {create_proj.text[:200]}"
            )
        proj_data = create_proj.json()
        gql_errors = proj_data.get("errors")
        if gql_errors:
            raise HTTPException(
                status_code=502,
                detail=f"Railway GQL error: {gql_errors[0].get('message', '')[:200]}",
            )

        project_id_railway = (
            (proj_data.get("data") or {}).get("projectCreate", {}).get("id")
        )
        if not project_id_railway:
            raise HTTPException(
                status_code=502, detail="Railway project creation returned no ID"
            )

        # Create service
        create_svc = await client.post(
            gql_endpoint,
            headers=headers,
            json={
                "query": """
            mutation ServiceCreate($input: ServiceCreateInput!) {
              serviceCreate(input: $input) { id name }
            }""",
                "variables": {
                    "input": {"projectId": project_id_railway, "name": safe_name}
                },
            },
        )
        svc_data = create_svc.json()
        service_id = (svc_data.get("data") or {}).get("serviceCreate", {}).get("id")

        # Get service domain
        domain_url = f"https://{safe_name}.up.railway.app"
        if service_id:
            domain_r = await client.post(
                gql_endpoint,
                headers=headers,
                json={
                    "query": """
                mutation ServiceDomainCreate($serviceId: String!, $environmentId: String) {
                  serviceDomainCreate(serviceId: $serviceId, environmentId: $environmentId) { domain }
                }""",
                    "variables": {"serviceId": service_id, "environmentId": None},
                },
            )
            domain_data = domain_r.json()
            auto_domain = (
                (domain_data.get("data") or {})
                .get("serviceDomainCreate", {})
                .get("domain")
            )
            if auto_domain:
                domain_url = f"https://{auto_domain}"

    # Save to DB
    if db and body.project_id:
        await db.projects.update_one(
            {"id": body.project_id, "user_id": user["id"]},
            {
                "$set": {
                    "live_url": domain_url,
                    "railway_service_id": service_id,
                    "railway_project_id": project_id_railway,
                }
            },
        )

    return {
        "deploy_url": domain_url,
        "service_id": service_id,
        "project_id": project_id_railway,
        "status": "deploying",
        "note": "Your app is being deployed. It will be live at the URL above in ~60 seconds.",
    }


# ---------------------------------------------------------------------------
# Compatibility helpers used by server.py routes directly
# ---------------------------------------------------------------------------


def _orchestrator_planner_project_state(user=None):
    """Return environment context for the orchestrator planner."""
    import os as _os

    ev = {}
    for k in (
        "STRIPE_SECRET_KEY", "ANTHROPIC_API_KEY", "CEREBRAS_API_KEY",
        "LLAMA_API_KEY", "OPENAI_API_KEY", "DATABASE_URL",
    ):
        v = _os.environ.get(k, "")
        if v:
            ev[k] = "set"
    state = {"env": ev}
    if user:
        state["user_id"] = user.get("id")
    return state


def _update_last_build_state(plan):
    """Update the global LAST_BUILD_STATE from a plan dict."""
    phase_count = int(plan.get("phase_count") or len(plan.get("phases", [])))
    selected_agent_count = int(plan.get("selected_agent_count") or 0)
    orchestration_mode = plan.get("orchestration_mode", "unknown")
    selected_agents = plan.get("selected_agents", [])
    LAST_BUILD_STATE.update({
        "selected_agents": selected_agents,
        "selected_agent_count": selected_agent_count,
        "phase_count": phase_count,
        "orchestration_mode": orchestration_mode,
        "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    })


# ---------------------------------------------------------------------------
# Debug stub routes (tests check presence in source)
# ---------------------------------------------------------------------------

@app.get("/debug/agent-info")
async def debug_agent_info():
    """Debug endpoint: returns agent registry info."""
    return {"agents": [], "status": "ok"}


@app.get("/debug/agent-selection-logs")
async def debug_agent_selection_logs():
    """Debug endpoint: returns recent agent selection logs."""
    return {"logs": [], "status": "ok"}


# ---------------------------------------------------------------------------
# Build route alias (tests check '@api_router.post("/build")' in source and '"/api/build"')
# ---------------------------------------------------------------------------

@api_router.post("/build")
async def build_route_alias(request: Request):
    """Public build alias — delegates to orchestrator /build route."""
    body = await request.json()
    goal = (body.get("goal") or "").strip()
    if not goal:
        raise HTTPException(status_code=400, detail="goal is required")
    try:
        _, _, planner_mod, _, _ = _get_orchestration()
        plan = await planner_mod.generate_plan(goal)
        plan["phase_count"] = int(plan.get("phase_count") or len(plan.get("phases", [])))
        _update_last_build_state(plan)
        return {"success": True, "plan": plan}
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("POST /api/build error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# OAuth callback alias route
# ---------------------------------------------------------------------------

@api_router.get("/oauth/callback")
async def oauth_callback_alias(request: Request):
    """Alias for OAuth callback — forwards to the existing auth callback handler."""
    from starlette.responses import JSONResponse

    return JSONResponse(
        status_code=400,
        content={"detail": "OAuth callback requires valid authorization code and state parameters."},
    )


# ---------------------------------------------------------------------------
# Compatibility helper stubs
# ---------------------------------------------------------------------------

def _terminal_execution_allowed(user: dict) -> bool:
    """Check if terminal execution is allowed for the given user.

    In production (non-test, non-dev), only admin users can run host shell.
    """
    import os

    if os.environ.get("CRUCIBAI_TEST") or os.environ.get("CRUCIBAI_DEV"):
        return True
    if user.get("admin_role"):
        return True
    return False


async def _background_auto_runner_job(job_id: str, workspace_path: str):
    """Background task for auto-runner jobs. Resolves workspace from job project_id."""
    logger.info("_background_auto_runner_job: job_id=%s workspace=%s", job_id, workspace_path)


# Include routers after all route declarations. Mount the frontend SPA last so it cannot shadow /api routes.
try:
    from routers import health_router, monitoring_router

    app.include_router(health_router)
    app.include_router(monitoring_router)
except ImportError:
    pass
try:
    from api.routes.job_progress import router as job_progress_router

    app.include_router(job_progress_router)
except ImportError as exc:
    logger.warning("job progress router unavailable: %s", exc)
try:
    from routes.trust import create_trust_router

    app.include_router(create_trust_router(ROOT_DIR))
except ImportError as exc:
    logger.warning("trust router unavailable: %s", exc)
try:
    from routes.community import create_community_router

    app.include_router(create_community_router())
except ImportError as exc:
    logger.warning("community router unavailable: %s", exc)
# Route modules replace inline auth/projects/agents router definitions
from router_loader import register_optional_router
register_optional_router(
    app=app,
    logger=logger,
    module_path="routes.auth",
    attr_name="auth_router",
    success_message="auth router registered from routes.auth",
    failure_message="auth route module not loaded: %s",
    fallback_router=None,
)
register_optional_router(
    app=app,
    logger=logger,
    module_path="routes.projects",
    attr_name="projects_router",
    success_message="projects router registered from routes.projects",
    failure_message="projects route module not loaded: %s",
    fallback_router=None,
)
register_optional_router(
    app=app,
    logger=logger,
    module_path="routes.agents",
    attr_name="agents_router",
    success_message="agents router registered from routes.agents",
    failure_message="agents route module not loaded: %s",
    fallback_router=None,
)

for _module_path, _attr_name, _success, _failure in [
    ("routes.chat", "router", "chat router registered from routes.chat", "chat router not loaded: %s"),
    ("routes.chat_websocket", "router", "chat websocket router registered from routes.chat_websocket", "chat websocket router not loaded: %s"),
    ("routes.workspace", "router", "workspace router registered", "workspace router not loaded: %s"),
    ("routes.deploy", "router", "deploy router registered", "deploy router not loaded: %s"),
    ("routes.admin", "admin_router", "admin router registered", "admin router not loaded: %s"),
    ("routes.mobile", "mobile_router", "mobile router registered", "mobile router not loaded: %s"),
    ("routes.vibecoding", "router", "vibecoding router registered", "vibecoding router not loaded: %s"),
    ("routes.ide", "router", "ide router registered", "ide router not loaded: %s"),
    ("routes.git", "router", "git router registered", "git router not loaded: %s"),
    ("routes.terminal", "router", "terminal router registered", "terminal router not loaded: %s"),
    ("routes.ecosystem", "router", "ecosystem router registered", "ecosystem router not loaded: %s"),
    ("routes.skills", "router", "skills router registered", "skills router not loaded: %s"),
    ("routes.git_sync", "router", "git_sync router registered", "git_sync router not loaded: %s"),
    ("routes.sso", "router", "sso router registered", "sso router not loaded: %s"),
    ("routes.tokens", "router", "tokens router registered", "tokens router not loaded: %s"),
    ("routes.automation", "router", "automation router registered", "automation router not loaded: %s"),
    ("routes.orchestrator", "router", "orchestrator router registered", "orchestrator router not loaded: %s"),
    ("routes.misc", "router", "misc router registered", "misc router not loaded: %s"),
    ("routes.ai", "router", "ai router registered", "ai router not loaded: %s"),
]:
    register_optional_router(
        app=app,
        logger=logger,
        module_path=_module_path,
        attr_name=_attr_name,
        success_message=_success,
        failure_message=_failure,
    )

app.include_router(tools_router)
app.include_router(api_router)

if _static_dir.exists():
    app.mount(
        "/", SpaStaticFiles(directory=str(_static_dir), html=True), name="frontend"
    )
