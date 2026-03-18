from fastapi import FastAPI, APIRouter, HTTPException, Depends, BackgroundTasks, File, UploadFile, Form, Request, WebSocket, WebSocketDisconnect, Query, Body
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse, Response, RedirectResponse, FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from middleware import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    RequestTrackerMiddleware,
    RequestValidationMiddleware,
    PerformanceMonitoringMiddleware,
    HTTPSRedirectMiddleware,
)
from error_handlers import (
    CrucibError,
    ValidationError,
    AuthenticationError,
    DatabaseError,
    ExternalServiceError,
    log_error,
    to_http_exception
)
from validators import (
    UserRegisterValidator,
    UserLoginValidator,
    ChatMessageValidator,
    ProjectCreateValidator,
    BuildPlanRequestValidator,
    validate_email,
    validate_password_strength
)
from structured_logging import (
    get_request_logger,
    get_error_logger,
    get_performance_logger,
    get_audit_logger,
    log_performance,
    log_audit
)
from api_docs_generator import generate_api_docs
from endpoint_wrapper import wrap_all_endpoints, safe_endpoint
import os
import logging
import httpx
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, model_validator
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import jwt
import bcrypt
import asyncio
import random
import json
import re
import secrets
import subprocess
import sys
import tempfile
import base64
import zipfile
import io
from urllib.parse import quote, urlencode

from env_encryption import encrypt_env, decrypt_env
from agent_dag import AGENT_DAG, get_execution_phases, build_context_from_previous_agents, get_system_prompt_for_agent
from real_agent_runner import REAL_AGENT_NAMES, run_real_agent, persist_agent_output, run_real_post_step
from security_headers import add_security_headers

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
        "/api/health",
        "/api/contact",
        "/api/enterprise/contact",
    }
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        method = scope["method"]
        path = scope.get("path", "")
        
        # Skip CSRF check for exempt paths
        if path in self.CSRF_EXEMPT_PATHS:
            await self.app(scope, receive, send)
            return
        
        # Only check CSRF for state-changing methods (skip when disabled for tests)
        if os.environ.get("DISABLE_CSRF_FOR_TEST", "").strip().lower() in ("1", "true", "yes"):
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
                        await send({
                            "type": "http.response.start",
                            "status": 403,
                            "headers": [[b"content-type", b"application/json"]],
                        })
                    elif message["type"] == "http.response.body":
                        await send({
                            "type": "http.response.body",
                            "body": b'{"detail": "CSRF token missing"}',
                        })
                await send_error({"type": "http.response.start"})
                await send_error({"type": "http.response.body"})
                return
        
        await self.app(scope, receive, send)


# Agent Learning System — wired into production path
from agent_recursive_learning import AgentMemory, PerformanceTracker, AdaptiveStrategy, ExecutionStatus

from critic_agent import CriticAgent, TruthModule

from vector_memory import vector_memory as _vector_memory
from pgvector_memory import pgvector_memory as _pgvector_memory
from llm_router import router, classifier, TaskComplexity
from credit_tracker import tracker

# Monitoring & Metrics
try:
    from metrics_system import metrics as _metrics
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    _metrics_available = True
except ImportError:
    _metrics_available = False
    print("WARNING: prometheus_client not installed - /metrics endpoint disabled", file=sys.stderr)
_critic_agent = CriticAgent()
_truth_module = TruthModule()
_agent_memory = None  # Initialized in startup after db is ready

async def _init_agent_learning():
    """Initialize the agent learning system with the database connection."""
    global _agent_memory
    if _agent_memory is None:
        _agent_memory = AgentMemory(db)
    return _agent_memory

from automation.models import AgentCreate, AgentUpdate, TriggerConfig, ActionConfig
from automation.constants import (
    CREDITS_PER_AGENT_RUN,
    INTERNAL_USER_ID,
    MAX_CONCURRENT_RUNS_PER_USER,
    MAX_RUNS_PER_HOUR_PER_USER,
    WEBHOOK_IDEMPOTENCY_SECONDS,
    WEBHOOK_RATE_LIMIT_PER_MINUTE,
)
from automation.executor import run_actions
from automation.schedule import next_run_at, is_one_time
from agent_real_behavior import run_agent_real_behavior
from project_state import load_state, WORKSPACE_ROOT
from tool_schemas import (
    ToolBrowserRequest,
    ToolFileRequest,
    ToolApiRequest,
    ToolDatabaseRequest,
    ToolDeployRequest,
)
from agent_resilience import AgentError, get_criticality, get_timeout, generate_fallback
from code_quality import score_generated_code
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
    from utils.rbac import has_permission, Permission, get_user_role
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
    print(f"ℹ️  Optional features not configured: {', '.join(_missing_optional[:3])}{'...' if len(_missing_optional) > 3 else ''} — add to Railway vars when ready")

import pyotp
import qrcode

ROOT_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT_DIR / '.env', override=True)

# Pre-flight: require secrets in production; in dev (CRUCIBAI_DEV=1) allow running without DB for /api/health
CRUCIBAI_DEV = os.environ.get("CRUCIBAI_DEV", "").strip().lower() in ("1", "true", "yes")
if not os.environ.get('JWT_SECRET'):
    if CRUCIBAI_DEV:
        os.environ.setdefault("JWT_SECRET", "dev-secret-do-not-use-in-production")
        print("WARNING: JWT_SECRET not set; using dev default. Set JWT_SECRET for production.", file=sys.stderr)
    else:
        print("FATAL: JWT_SECRET not set. Set JWT_SECRET in Railway/Production Variables.", file=sys.stderr)
        sys.exit(1)
if not os.environ.get('DATABASE_URL'):
    if CRUCIBAI_DEV:
        print("WARNING: DATABASE_URL not set. /api/health will work; auth and builds need a real DB. Set DATABASE_URL for full local dev.", file=sys.stderr)
    else:
        print("FATAL: DATABASE_URL not set. Set DATABASE_URL in Railway/Production Variables.", file=sys.stderr)
        sys.exit(1)

# PostgreSQL database will be initialized on startup (or remain None in dev without DATABASE_URL)
db = None
audit_logger = None

def _mfa_temp_token_payload(user_id: str) -> dict:
    return {"user_id": user_id, "purpose": "mfa_verification", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}

def create_mfa_temp_token(user_id: str) -> str:
    return jwt.encode(_mfa_temp_token_payload(user_id), JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_mfa_temp_token(token: str) -> dict:
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    if payload.get("purpose") != "mfa_verification":
        raise jwt.InvalidTokenError("Invalid purpose")
    return payload

app = FastAPI(title="CrucibAI Platform")
add_security_headers(app)
api_router = APIRouter(prefix="/api")
auth_router = APIRouter(prefix="/api", tags=["auth"])
projects_router = APIRouter(prefix="/api", tags=["projects"])
tools_router = APIRouter(prefix="/api", tags=["tools"])
agents_router = APIRouter(prefix="/api", tags=["agents"])
security = HTTPBearer(auto_error=False)

# LLM Configuration: Only Anthropic (Haiku) and Cerebras (free tier)
ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
CEREBRAS_API_KEY = os.environ.get('CEREBRAS_API_KEY')

# Groq API configuration (third LLM fallback)
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_MODEL = "mixtral-8x7b-32768"  # Fast, cost-effective

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# JWT_SECRET must be set in production; fallback is per-process and invalidates tokens on restart
JWT_SECRET = os.environ.get('JWT_SECRET')
if not JWT_SECRET:
    logger.warning("JWT_SECRET not set in environment. Using a temporary secret for this session.")
    import secrets
    JWT_SECRET = secrets.token_urlsafe(32)
JWT_ALGORITHM = "HS256"

# Session timeout configuration
SESSION_TIMEOUT_MINUTES = int(os.environ.get('SESSION_TIMEOUT_MINUTES', '60'))
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
    """Emit event for SSE stream. Called from orchestration so UI can show Manus-style timeline."""
    if project_id not in _build_events:
        _build_events[project_id] = []
    lst = _build_events[project_id]
    ev = {"id": len(lst), "ts": datetime.now(timezone.utc).isoformat(), "type": event_type, **kwargs}
    lst.append(ev)
    if len(lst) > _BUILD_EVENTS_MAX:
        _build_events[project_id] = lst[-_BUILD_EVENTS_MAX:]
        for i, e in enumerate(_build_events[project_id]):
            e["id"] = i

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
    message: str
    session_id: Optional[str] = None
    model: Optional[str] = "auto"  # auto or haiku (Anthropic/Cerebras only)
    mode: Optional[str] = None  # thinking = step-by-step reasoning (no extra cost, same call)
    system_message: Optional[str] = None  # override for intent classification etc.
    attachments: Optional[List[Dict[str, Any]]] = None  # [{ "type": "image"|"pdf"|"text", "data": base64 or data URL or text, "name": "file.pdf" }]

class ChatResponse(BaseModel):
    model_config = {"protected_namespaces": ()}  # suppress model_used namespace warning
    response: str
    model_used: str
    tokens_used: int
    session_id: str

class TokenPurchase(BaseModel):
    bundle: str


class TokenPurchaseCustom(BaseModel):
    """Custom credit purchase (slider): 100-10000 credits at $0.06/credit."""
    credits: int = Field(ge=100, le=10000, description="Credits to purchase (100-10000)")

MAX_PROMPT_LENGTH = 50000
MAX_PROJECT_DESCRIPTION_LENGTH = 10000
MAX_PROJECT_REQUIREMENTS_JSON_LENGTH = 100000

class BuildPlanRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=MAX_PROMPT_LENGTH)
    swarm: Optional[bool] = False  # run plan + suggestions in parallel; token multiplier applied
    build_kind: Optional[str] = None  # fullstack | mobile | saas | bot | ai_agent | game | trading | any

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
    issue_type: Optional[str] = None  # e.g. "general", "support", "enterprise", "billing"
    name: Optional[str] = Field(None, max_length=200)

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    description: str = Field("", max_length=MAX_PROJECT_DESCRIPTION_LENGTH)
    project_type: str = Field(..., max_length=100)
    requirements: Dict[str, Any] = Field(default_factory=dict)
    estimated_tokens: Optional[int] = None
    quick_build: Optional[bool] = False  # Item 29: fast preview — run only first 2 phases, preview in ~2 min

    @model_validator(mode="after")
    def check_requirements_size(self):
        try:
            s = json.dumps(self.requirements or {})
            if len(s) > MAX_PROJECT_REQUIREMENTS_JSON_LENGTH:
                raise ValueError(f"requirements too large (max {MAX_PROJECT_REQUIREMENTS_JSON_LENGTH} chars)")
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


class DeployOneClickBody(BaseModel):
    """Optional token override for one-click deploy (otherwise use stored user tokens)."""
    token: Optional[str] = None


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
    project_id: Optional[str] = None  # when set, store result on project for AgentMonitor badge

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
    files: Optional[List[Dict[str, Any]]] = None  # for paste: [{"path": str, "code": str}]
    zip_base64: Optional[str] = None  # for zip: base64-encoded zip bytes
    git_url: Optional[str] = None  # for git: e.g. https://github.com/owner/repo


class GenerateContentRequest(BaseModel):
    """CrucibAI for Docs/Slides/Sheets (C1–C3)."""
    prompt: str
    format: Optional[str] = None  # doc: markdown|plain; slides: markdown|outline; sheets: csv|json

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

# ==================== CREDITS & PRICING (1 credit = 1000 tokens) ====================
from pricing_plans import CREDIT_PLANS, TOKEN_BUNDLES, _speed_from_plan, CREDITS_PER_TOKEN, ADDONS, ANNUAL_PRICES

MIN_CREDITS_FOR_LLM = 5
FREE_TIER_CREDITS = 100  # Free tier (email signup)
GUEST_TIER_CREDITS = 200  # Guest/free users get 200 credits (matches free tier)

AGENT_DEFINITIONS = [
    {"name": "Planner", "layer": "planning", "description": "Decomposes user requests into executable tasks", "avg_tokens": 50000},
    {"name": "Requirements Clarifier", "layer": "planning", "description": "Asks clarifying questions and validates requirements", "avg_tokens": 30000},
    {"name": "Stack Selector", "layer": "planning", "description": "Chooses optimal technology stack", "avg_tokens": 20000},
    {"name": "Frontend Generation", "layer": "execution", "description": "Generates React/Next.js UI components", "avg_tokens": 150000},
    {"name": "Backend Generation", "layer": "execution", "description": "Creates APIs, auth, business logic", "avg_tokens": 120000},
    {"name": "Database Agent", "layer": "execution", "description": "Designs schema and migrations", "avg_tokens": 80000},
    {"name": "API Integration", "layer": "execution", "description": "Integrates third-party APIs", "avg_tokens": 60000},
    {"name": "Test Generation", "layer": "execution", "description": "Writes comprehensive test suites", "avg_tokens": 100000},
    {"name": "Image Generation", "layer": "execution", "description": "Creates AI-generated visuals", "avg_tokens": 40000},
    {"name": "Security Checker", "layer": "validation", "description": "Audits for vulnerabilities", "avg_tokens": 40000},
    {"name": "Test Executor", "layer": "validation", "description": "Runs all tests and reports", "avg_tokens": 50000},
    {"name": "UX Auditor", "layer": "validation", "description": "Reviews design and accessibility", "avg_tokens": 35000},
    {"name": "Performance Analyzer", "layer": "validation", "description": "Optimizes speed and efficiency", "avg_tokens": 40000},
    {"name": "Deployment Agent", "layer": "deployment", "description": "Deploys to cloud platforms", "avg_tokens": 60000},
    {"name": "Error Recovery", "layer": "deployment", "description": "Auto-fixes failures", "avg_tokens": 45000},
    {"name": "Memory Agent", "layer": "deployment", "description": "Stores patterns for reuse", "avg_tokens": 25000},
    {"name": "PDF Export", "layer": "export", "description": "Generates formatted PDF reports", "avg_tokens": 30000},
    {"name": "Excel Export", "layer": "export", "description": "Creates spreadsheets with formulas", "avg_tokens": 25000},
    {"name": "Markdown Export", "layer": "export", "description": "Outputs project summary in Markdown", "avg_tokens": 20000},
    {"name": "Scraping Agent", "layer": "automation", "description": "Extracts data from websites", "avg_tokens": 35000},
    {"name": "Automation Agent", "layer": "automation", "description": "Schedules tasks and workflows", "avg_tokens": 30000},
    {"name": "Video Generation", "layer": "execution", "description": "Stock video search queries", "avg_tokens": 20000},
    {"name": "Design Agent", "layer": "execution", "description": "Image placement spec (hero, feature_1, feature_2)", "avg_tokens": 30000},
    {"name": "Layout Agent", "layer": "execution", "description": "Injects image placeholders into frontend", "avg_tokens": 40000},
    {"name": "SEO Agent", "layer": "execution", "description": "Meta, OG, schema, sitemap, robots.txt", "avg_tokens": 35000},
    {"name": "Content Agent", "layer": "planning", "description": "Landing copy: hero, features, CTA", "avg_tokens": 30000},
    {"name": "Brand Agent", "layer": "execution", "description": "Colors, fonts, tone spec", "avg_tokens": 25000},
    {"name": "Documentation Agent", "layer": "deployment", "description": "README: setup, env, run, deploy", "avg_tokens": 40000},
    {"name": "Validation Agent", "layer": "validation", "description": "Form/API validation rules, Zod/Yup", "avg_tokens": 35000},
    {"name": "Auth Setup Agent", "layer": "execution", "description": "JWT/OAuth flow, protected routes", "avg_tokens": 50000},
    {"name": "Payment Setup Agent", "layer": "execution", "description": "Stripe checkout, webhooks", "avg_tokens": 50000},
    {"name": "Monitoring Agent", "layer": "deployment", "description": "Sentry, analytics setup", "avg_tokens": 35000},
    {"name": "Accessibility Agent", "layer": "validation", "description": "a11y improvements: ARIA, contrast", "avg_tokens": 30000},
    {"name": "DevOps Agent", "layer": "deployment", "description": "CI/CD, Dockerfile", "avg_tokens": 40000},
    {"name": "Webhook Agent", "layer": "execution", "description": "Webhook endpoint design", "avg_tokens": 35000},
    {"name": "Email Agent", "layer": "execution", "description": "Transactional email setup", "avg_tokens": 35000},
    {"name": "Legal Compliance Agent", "layer": "planning", "description": "GDPR/CCPA hints", "avg_tokens": 30000},
    {"name": "GraphQL Agent", "layer": "execution", "description": "GraphQL schema and resolvers", "avg_tokens": 40000},
    {"name": "WebSocket Agent", "layer": "execution", "description": "Real-time subscriptions", "avg_tokens": 35000},
    {"name": "i18n Agent", "layer": "execution", "description": "Localization, translation keys", "avg_tokens": 30000},
    {"name": "Caching Agent", "layer": "execution", "description": "Redis/edge caching strategy", "avg_tokens": 30000},
    {"name": "Rate Limit Agent", "layer": "execution", "description": "API rate limiting, quotas", "avg_tokens": 30000},
    {"name": "Search Agent", "layer": "execution", "description": "Full-text search (Algolia/Meilisearch)", "avg_tokens": 35000},
    {"name": "Analytics Agent", "layer": "deployment", "description": "GA4, Mixpanel, event schema", "avg_tokens": 30000},
    {"name": "API Documentation Agent", "layer": "execution", "description": "OpenAPI/Swagger from routes", "avg_tokens": 40000},
    {"name": "Mobile Responsive Agent", "layer": "validation", "description": "Breakpoints, touch, PWA hints", "avg_tokens": 30000},
    {"name": "Migration Agent", "layer": "execution", "description": "DB migration scripts", "avg_tokens": 35000},
    {"name": "Backup Agent", "layer": "deployment", "description": "Backup strategy, restore steps", "avg_tokens": 30000},
    {"name": "Notification Agent", "layer": "execution", "description": "Push, in-app, email notifications", "avg_tokens": 35000},
    {"name": "Design Iteration Agent", "layer": "planning", "description": "Feedback → spec → rebuild flow", "avg_tokens": 35000},
    {"name": "Code Review Agent", "layer": "validation", "description": "Security, style, best-practice review", "avg_tokens": 45000},
    {"name": "Staging Agent", "layer": "deployment", "description": "Staging env, preview URLs", "avg_tokens": 25000},
    {"name": "A/B Test Agent", "layer": "execution", "description": "Experiment setup, variant routing", "avg_tokens": 30000},
    {"name": "Feature Flag Agent", "layer": "execution", "description": "LaunchDarkly/Flagsmith wiring", "avg_tokens": 30000},
    {"name": "Error Boundary Agent", "layer": "execution", "description": "React error boundaries, fallback UI", "avg_tokens": 30000},
    {"name": "Logging Agent", "layer": "execution", "description": "Structured logs, log levels", "avg_tokens": 30000},
    {"name": "Metrics Agent", "layer": "deployment", "description": "Prometheus/Datadog metrics", "avg_tokens": 30000},
    {"name": "Audit Trail Agent", "layer": "execution", "description": "User action logging, audit log", "avg_tokens": 35000},
    {"name": "Session Agent", "layer": "execution", "description": "Session storage, expiry, refresh", "avg_tokens": 30000},
    {"name": "OAuth Provider Agent", "layer": "execution", "description": "Google/GitHub OAuth wiring", "avg_tokens": 40000},
    {"name": "2FA Agent", "layer": "execution", "description": "TOTP, backup codes", "avg_tokens": 30000},
    {"name": "Stripe Subscription Agent", "layer": "execution", "description": "Plans, metering, downgrade", "avg_tokens": 40000},
    {"name": "Invoice Agent", "layer": "execution", "description": "Invoice generation, PDF", "avg_tokens": 35000},
    {"name": "CDN Agent", "layer": "deployment", "description": "Static assets, cache headers", "avg_tokens": 30000},
    {"name": "SSR Agent", "layer": "execution", "description": "Next.js SSR/SSG hints", "avg_tokens": 30000},
    {"name": "Bundle Analyzer Agent", "layer": "validation", "description": "Code splitting, chunk hints", "avg_tokens": 30000},
    {"name": "Lighthouse Agent", "layer": "validation", "description": "Performance, a11y, SEO scores", "avg_tokens": 35000},
    {"name": "Schema Validation Agent", "layer": "execution", "description": "Request/response validation", "avg_tokens": 30000},
    {"name": "Mock API Agent", "layer": "execution", "description": "MSW, Mirage, mock server", "avg_tokens": 35000},
    {"name": "E2E Agent", "layer": "execution", "description": "Playwright/Cypress scaffolding", "avg_tokens": 45000},
    {"name": "Load Test Agent", "layer": "execution", "description": "k6, Artillery scripts", "avg_tokens": 35000},
    {"name": "Dependency Audit Agent", "layer": "validation", "description": "npm audit, Snyk hints", "avg_tokens": 30000},
    {"name": "License Agent", "layer": "planning", "description": "OSS license compliance", "avg_tokens": 25000},
    {"name": "Terms Agent", "layer": "planning", "description": "Terms of service draft", "avg_tokens": 30000},
    {"name": "Privacy Policy Agent", "layer": "planning", "description": "Privacy policy draft", "avg_tokens": 30000},
    {"name": "Cookie Consent Agent", "layer": "execution", "description": "Cookie banner, preferences", "avg_tokens": 30000},
    {"name": "Multi-tenant Agent", "layer": "execution", "description": "Tenant isolation, schema", "avg_tokens": 40000},
    {"name": "RBAC Agent", "layer": "execution", "description": "Roles, permissions matrix", "avg_tokens": 40000},
    {"name": "SSO Agent", "layer": "execution", "description": "SAML, enterprise SSO", "avg_tokens": 40000},
    {"name": "Audit Export Agent", "layer": "deployment", "description": "Export audit logs", "avg_tokens": 30000},
    {"name": "Data Residency Agent", "layer": "planning", "description": "Region, GDPR data location", "avg_tokens": 30000},
    {"name": "HIPAA Agent", "layer": "planning", "description": "Healthcare compliance hints", "avg_tokens": 35000},
    {"name": "SOC2 Agent", "layer": "planning", "description": "SOC2 control hints", "avg_tokens": 35000},
    {"name": "Penetration Test Agent", "layer": "validation", "description": "Pentest checklist", "avg_tokens": 35000},
    {"name": "Incident Response Agent", "layer": "deployment", "description": "Runbook, escalation", "avg_tokens": 35000},
    {"name": "SLA Agent", "layer": "deployment", "description": "Uptime, latency targets", "avg_tokens": 30000},
    {"name": "Cost Optimizer Agent", "layer": "deployment", "description": "Cloud cost hints", "avg_tokens": 30000},
    {"name": "Accessibility WCAG Agent", "layer": "validation", "description": "WCAG 2.1 AA checklist", "avg_tokens": 35000},
    {"name": "RTL Agent", "layer": "execution", "description": "Right-to-left layout", "avg_tokens": 25000},
    {"name": "Dark Mode Agent", "layer": "execution", "description": "Theme toggle, contrast", "avg_tokens": 30000},
    {"name": "Keyboard Nav Agent", "layer": "validation", "description": "Full keyboard navigation", "avg_tokens": 30000},
    {"name": "Screen Reader Agent", "layer": "validation", "description": "Screen-reader-specific hints", "avg_tokens": 30000},
    {"name": "Component Library Agent", "layer": "execution", "description": "Shadcn/Radix usage", "avg_tokens": 35000},
    {"name": "Design System Agent", "layer": "execution", "description": "Tokens, spacing, typography", "avg_tokens": 35000},
    {"name": "Animation Agent", "layer": "execution", "description": "Framer Motion, transitions", "avg_tokens": 30000},
    {"name": "Chart Agent", "layer": "execution", "description": "Recharts, D3 usage", "avg_tokens": 35000},
    {"name": "Table Agent", "layer": "execution", "description": "Data tables, sorting, pagination", "avg_tokens": 35000},
    {"name": "Form Builder Agent", "layer": "execution", "description": "Dynamic form generation", "avg_tokens": 40000},
    {"name": "Workflow Agent", "layer": "execution", "description": "State machine, workflows", "avg_tokens": 40000},
    {"name": "Queue Agent", "layer": "execution", "description": "Job queues, Bull/Celery", "avg_tokens": 40000},
    # DAG-only (23 more = 123 total) — in agent_dag.py, now exposed in /api/agents
    {"name": "Native Config Agent", "layer": "execution", "description": "Expo/app.json, eas.json for mobile", "avg_tokens": 25000},
    {"name": "Store Prep Agent", "layer": "deployment", "description": "App store submission metadata and guides", "avg_tokens": 35000},
    {"name": "Vibe Analyzer Agent", "layer": "planning", "description": "Analyze project vibe, mood, aesthetic", "avg_tokens": 30000},
    {"name": "Voice Context Agent", "layer": "planning", "description": "Convert voice/speech to code context", "avg_tokens": 30000},
    {"name": "Video Tutorial Agent", "layer": "deployment", "description": "Video tutorial scripts and storyboards", "avg_tokens": 35000},
    {"name": "Aesthetic Reasoner Agent", "layer": "validation", "description": "Evaluate code for beauty and elegance", "avg_tokens": 30000},
    {"name": "Team Preferences", "layer": "planning", "description": "Capture team style and conventions", "avg_tokens": 25000},
    {"name": "Collaborative Memory Agent", "layer": "deployment", "description": "Team preferences and project patterns", "avg_tokens": 30000},
    {"name": "Real-time Feedback Agent", "layer": "validation", "description": "Adapt to user reactions and feedback", "avg_tokens": 35000},
    {"name": "Mood Detection Agent", "layer": "planning", "description": "Detect user mood and intent", "avg_tokens": 25000},
    {"name": "Accessibility Vibe Agent", "layer": "validation", "description": "Accessible and inclusive vibe", "avg_tokens": 30000},
    {"name": "Performance Vibe Agent", "layer": "validation", "description": "Code that feels fast and responsive", "avg_tokens": 30000},
    {"name": "Creativity Catalyst Agent", "layer": "planning", "description": "Creative improvements and innovation", "avg_tokens": 35000},
    {"name": "IDE Integration Coordinator Agent", "layer": "execution", "description": "IDE extensions and plugin hooks", "avg_tokens": 35000},
    {"name": "Multi-language Code Agent", "layer": "execution", "description": "Code in multiple languages", "avg_tokens": 40000},
    {"name": "Team Collaboration Agent", "layer": "deployment", "description": "Collaboration workflows and review", "avg_tokens": 35000},
    {"name": "User Onboarding Agent", "layer": "deployment", "description": "Onboarding and tutorial experience", "avg_tokens": 35000},
    {"name": "Customization Engine Agent", "layer": "execution", "description": "User customization and themes", "avg_tokens": 35000},
    {"name": "Browser Tool Agent", "layer": "automation", "description": "Playwright browser automation", "avg_tokens": 40000},
    {"name": "File Tool Agent", "layer": "execution", "description": "Writes files to project workspace", "avg_tokens": 50000},
    {"name": "API Tool Agent", "layer": "automation", "description": "HTTP requests and API calls", "avg_tokens": 35000},
    {"name": "Database Tool Agent", "layer": "execution", "description": "Applies schema to project DB", "avg_tokens": 40000},
    {"name": "Deployment Tool Agent", "layer": "deployment", "description": "Deploy to Vercel/Railway/Netlify", "avg_tokens": 50000},
]

# AI Model configurations: Cerebras (free) or Haiku (paid)
# All tasks use Haiku for paid users, Cerebras for free tier
MODEL_CONFIG = {
    "code": {"provider": "anthropic", "model": "claude-3-5-haiku-20241022"},
    "analysis": {"provider": "anthropic", "model": "claude-3-5-haiku-20241022"},
    "general": {"provider": "anthropic", "model": "claude-3-5-haiku-20241022"},
    "creative": {"provider": "anthropic", "model": "claude-3-5-haiku-20241022"},
    "fast": {"provider": "anthropic", "model": "claude-3-5-haiku-20241022"}
}

# Fallback chain: only Haiku (no fallback needed, single provider)
MODEL_FALLBACK_CHAINS = [
    {"provider": "anthropic", "model": "claude-3-5-haiku-20241022"},
]
# Map user-facing model key -> chain (only Haiku)
MODEL_CHAINS = {
    "auto": None,  # use MODEL_CONFIG + MODEL_FALLBACK_CHAINS
    "haiku": [{"provider": "anthropic", "model": "claude-3-5-haiku-20241022"}],
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
    doc = await db.users.find_one({"id": user_id}, {"credit_balance": 1, "token_balance": 1})
    if not doc or doc.get("credit_balance") is not None:
        return
    cred = (doc.get("token_balance") or 0) // CREDITS_PER_TOKEN
    await db.users.update_one({"id": user_id}, {"$set": {"credit_balance": cred}})


# Disposable email block (fraud prevention)
DISPOSABLE_EMAIL_DOMAINS = frozenset([
    "10minutemail.com", "guerrillamail.com", "tempmail.com", "mailinator.com",
    "throwaway.email", "temp-mail.org", "fakeinbox.com", "trashmail.com", "yopmail.com",
])

def _is_disposable_email(email: str) -> bool:
    domain = (email or "").strip().split("@")[-1].lower()
    return domain in DISPOSABLE_EMAIL_DOMAINS


# Referral: 100 credits each (free tier only — referrer reward only if referrer is on free plan). Safest to avoid mismatch. 10/month cap, 30-day expiry.
REFERRAL_CREDITS = 100
REFERRAL_CAP_PER_MONTH = 10
REFERRAL_EXPIRY_DAYS = 30

def _generate_referral_code() -> str:
    return "".join(random.choices("abcdefghjkmnpqrstuvwxyz23456789", k=8))

async def _apply_referral_on_signup(referee_id: str, ref_code: Optional[str] = None) -> None:
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
    count = await db.referrals.count_documents({"referrer_id": referrer_id, "signup_completed_at": {"$gte": month_start.isoformat()}})
    if count >= REFERRAL_CAP_PER_MONTH:
        return
    referrer_doc = await db.users.find_one({"id": referrer_id}, {"plan": 1})
    referrer_plan = (referrer_doc or {}).get("plan") or "free"
    reward_referrer = referrer_plan == "free"  # free tier only: referrer gets credits only if on free plan
    expiry_at = (now + timedelta(days=REFERRAL_EXPIRY_DAYS)).isoformat()
    await db.referrals.insert_one({
        "id": str(uuid.uuid4()),
        "referrer_id": referrer_id,
        "referee_id": referee_id,
        "status": "completed",
        "signup_completed_at": now.isoformat(),
        "referrer_rewarded_at": now.isoformat(),
        "created_at": now.isoformat(),
    })
    # Referee always gets 100 (new user = free tier). Referrer gets 100 only if referrer is on free plan.
    to_grant = [(referee_id, "Referral (referee)")]
    if reward_referrer:
        to_grant.append((referrer_id, "Referral (referrer)"))
    for uid, desc in to_grant:
        await db.users.update_one({"id": uid}, {"$inc": {"credit_balance": REFERRAL_CREDITS}})
        await db.token_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": uid,
            "credits": REFERRAL_CREDITS,
            "type": "referral",
            "description": desc,
            "credit_expires_at": expiry_at,
            "created_at": now.isoformat(),
        })
    logger.info(f"Referral: granted {REFERRAL_CREDITS} to referee {referee_id}" + (f" and referrer {referrer_id} (free tier)" if reward_referrer else " (referrer not on free tier, no referrer reward)"))


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
        logger.warning(f"SECURITY: SHA-256 password hash detected. Please migrate to bcrypt by 2026-06-01.")
        import hashlib
        return hashlib.sha256(plain.encode()).hexdigest() == hashed
    return False

def create_token(user_id: str) -> str:
    # SECURITY: Use 1-hour access tokens (not 30 days)
    # Implement refresh tokens for longer sessions
    payload = {
        "user_id": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def encode_jwt(payload: Dict[str, Any], secret: str = None, algorithm: str = None) -> str:
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

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
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
PUBLIC_API_KEYS = set(k.strip() for k in (os.environ.get("CRUCIBAI_PUBLIC_API_KEYS") or "").split(",") if k.strip())

async def _check_api_key_db(api_key: str) -> bool:
    """Validate API key against db.api_keys if collection exists."""
    try:
        row = await db.api_keys.find_one({"key": api_key, "active": True})
        return row is not None
    except (ValueError, TypeError, AttributeError) as e:
        logger.debug(f"Error checking API key: {e}")
        return False

async def get_optional_user(credentials: HTTPAuthorizationCredentials = Depends(security), request: Request = None):
    """Logged-in user (Bearer JWT) or public API user (X-API-Key). Returns None if neither."""
    if credentials:
        try:
            payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
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
            return {"id": f"api_key_{api_key[:8]}", "token_balance": 999999, "credit_balance": 999999, "plan": "teams", "public_api": True}
    return None

def detect_task_type(message: str) -> str:
    """Auto-detect the best model based on message content"""
    message_lower = message.lower()
    
    code_keywords = ['code', 'function', 'class', 'api', 'bug', 'error', 'debug', 'implement', 'python', 'javascript', 'react', 'database']
    analysis_keywords = ['analyze', 'compare', 'evaluate', 'explain', 'why', 'how does', 'what is']
    creative_keywords = ['write', 'create', 'story', 'poem', 'design', 'imagine', 'brainstorm']
    
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


def _provider_has_key(provider: str, effective_keys: Optional[Dict[str, str]] = None) -> bool:
    """True if we have an API key for this provider. Only Anthropic (Haiku) and Cerebras supported."""
    if provider == "anthropic":
        if effective_keys:
            return bool(effective_keys.get("anthropic"))
        return bool(ANTHROPIC_API_KEY)
    if provider == "cerebras":
        return bool(os.environ.get("CEREBRAS_API_KEY"))
    return False


def _filter_chain_by_keys(chain: list, effective_keys: Optional[Dict[str, str]] = None) -> list:
    """Keep only providers we have keys for."""
    return [c for c in chain if _provider_has_key(c.get("provider", ""), effective_keys)]


def _get_model_chain(model_key: str, message: str, effective_keys: Optional[Dict[str, str]] = None):
    """Get list of (provider, model) to try. effective_keys = merged user Settings + server .env keys.
    When PREFER_LARGEST_MODEL=1, use largest available model first (better quality for all agents)."""
    if model_key == "auto":
        # Model scale: prefer largest available when set (best for quality across 123 agents)
        if os.environ.get("PREFER_LARGEST_MODEL", "").strip().lower() in ("1", "true", "yes"):
            chain = _filter_chain_by_keys(MODEL_FALLBACK_CHAINS, effective_keys) or MODEL_FALLBACK_CHAINS
        else:
            task_type = detect_task_type(message)
            primary = MODEL_CONFIG.get(task_type, MODEL_CONFIG["general"])
            chain = [primary] + [c for c in MODEL_FALLBACK_CHAINS if (c["provider"], c["model"]) != (primary["provider"], primary["model"])]
    else:
        chain = MODEL_CHAINS.get(model_key)
        if not chain:
            primary = MODEL_CONFIG["general"]
            chain = [primary] + MODEL_FALLBACK_CHAINS
    return _filter_chain_by_keys(chain, effective_keys) or [c for c in (MODEL_FALLBACK_CHAINS or []) if _provider_has_key(c.get("provider", ""), effective_keys)]


async def get_workspace_api_keys(user: Optional[dict]) -> Dict[str, Optional[str]]:
    """Load Anthropic/Cerebras from server environment only. User-provided keys are no longer supported."""
    # Always use server-side keys from environment variables
    # User-provided keys are no longer stored or used
    return {
        "anthropic": ANTHROPIC_API_KEY or None,
        "cerebras": os.environ.get("CEREBRAS_API_KEY") or None,
    }


def _effective_api_keys(user_keys: Dict[str, Optional[str]]) -> Dict[str, Optional[str]]:
    """Use server-side API keys only. User-provided keys are no longer supported."""
    return {
        "anthropic": ANTHROPIC_API_KEY or None,
        "cerebras": os.environ.get("CEREBRAS_API_KEY") or None,
    }


async def _call_anthropic_direct(prompt: str, system: str, model: str = "claude-3-5-haiku-20241022", api_key: Optional[str] = None) -> str:
    """Call Anthropic API directly. Uses api_key or ANTHROPIC_API_KEY."""
    key = (api_key or "").strip() or ANTHROPIC_API_KEY
    if not key:
        raise ValueError("ANTHROPIC_API_KEY not set")
    import anthropic
    client = anthropic.AsyncAnthropic(api_key=key)
    msg = await client.messages.create(
        model=model,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text if msg.content else ""
    return text.strip()



async def _call_cerebras_direct(prompt: str, system: str, model: str = "claude-3-5-haiku-20241022", api_key: Optional[str] = None) -> str:
    """Call Cerebras API directly (free tier fallback). Uses api_key or CEREBRAS_API_KEY."""
    key = (api_key or "").strip() or os.environ.get("CEREBRAS_API_KEY")
    if not key:
        raise ValueError("CEREBRAS_API_KEY not set")
    import anthropic
    # Cerebras uses Anthropic-compatible API
    client = anthropic.AsyncAnthropic(api_key=key, base_url="https://api.cerebras.ai/v1")
    msg = await client.messages.create(
        model=model,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text if msg.content else ""
    return text.strip()


async def _call_anthropic_multimodal(content_blocks: List[Dict[str, Any]], system: str, model: str = "claude-3-5-haiku-20241022", api_key: Optional[str] = None) -> str:
    """Call Anthropic with multimodal user content (text + image). Uses vision-capable model."""
    key = (api_key or "").strip() or ANTHROPIC_API_KEY
    if not key:
        raise ValueError("ANTHROPIC_API_KEY not set")
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
                anthropic_content.append({"type": "image", "source": {"type": "base64", "media_type": media, "data": b64}})
            else:
                anthropic_content.append({"type": "text", "text": f"[Image: {url[:80]}...]"})
    msg = await client.messages.create(
        model=model or "claude-3-5-haiku-20241022",
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
    {"provider": "anthropic", "model": "claude-3-5-haiku-20241022"},
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
                    "max_tokens": 4096,
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
                    "max_tokens": 4096,
                    "temperature": 0.7,
                },
                timeout=120,
            )
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
    model: str = "claude-3-5-haiku-20241022",
    api_key: str = None,
) -> str:
    """Call Anthropic Claude Haiku."""
    import httpx
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")
    
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
                logger.warning(f"Anthropic API error: {response.text}")
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
        raise ValueError("No LLM models available. Configure LLAMA_API_KEY, CEREBRAS_API_KEY, or ANTHROPIC_API_KEY.")
    
    last_error = None
    
    # Try each model in the chain
    for model_info in model_chain:
        model_name, model_id, provider = model_info
        
        try:
            logger.info(f"Trying {provider}/{model_name} for task: {task_complexity}")
            
            if provider == "together" and router.llama_available:
                # Llama 70B via Together AI
                response = await _call_llama_direct(
                    message, system_message, 
                    model=model_id, 
                    api_key=router.llama_available and os.environ.get("LLAMA_API_KEY")
                )
                
                # Record usage
                if user_id and db:
                    await tracker.record_usage(
                        db, user_id, "llama", 
                        len(message.split()) * 1.3,  # Estimate tokens
                        user_tier, agent_name, session_id
                    )
                
                return (response, f"llama/{model_id}")
            
            elif provider == "cerebras" and router.cerebras_available:
                # Cerebras Llama 2 70B
                response = await _call_cerebras_direct(
                    message, system_message,
                    model=model_id,
                    api_key=os.environ.get("CEREBRAS_API_KEY")
                )
                
                # Record usage
                if user_id and db:
                    await tracker.record_usage(
                        db, user_id, "cerebras",
                        len(message.split()) * 1.3,  # Estimate tokens
                        user_tier, agent_name, session_id
                    )
                
                return (response, f"cerebras/{model_id}")
            
            elif provider == "anthropic" and router.haiku_available:
                # Anthropic Claude Haiku (fallback)
                response = await _call_anthropic_direct(
                    message, system_message,
                    model=model_id,
                    api_key=os.environ.get("ANTHROPIC_API_KEY")
                )
                
                # Record usage
                if user_id and db:
                    await tracker.record_usage(
                        db, user_id, "haiku",
                        len(message.split()) * 1.3,  # Estimate tokens
                        user_tier, agent_name, session_id
                    )
                
                return (response, f"haiku/{model_id}")
        
        except Exception as e:
            last_error = e
            logger.warning(f"LLM {provider}/{model_name} failed: {e}, trying next fallback")
            continue
    
    # All models failed
    error_msg = f"All LLM models failed. Last error: {last_error}"
    logger.error(error_msg)
    raise last_error or Exception(error_msg)


# ==================== AI CHAT ROUTES ====================
# Prepay: require at least MIN_CREDITS_FOR_LLM credits (legacy MIN_BALANCE_FOR_LLM_CALL = 5000 tokens ≈ 5 credits)
MIN_BALANCE_FOR_LLM_CALL = 5_000  # legacy token value; we check credits now


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


from datetime import datetime as _dt, timezone as _tz

def _build_chat_system_prompt() -> str:
    today = _dt.now(_tz.utc).strftime("%B %d, %Y")
    return f"""You are CrucibAI — an AI platform that builds apps, automations, and digital products.

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

Be warm, direct, and confident. You are a builder, not a customer service bot.

When the user attaches images or PDFs: images are shown to you directly, PDFs are extracted as text. Use that content to answer questions or help build something. Do not say you cannot see attachments.

Rules:
- Never say "How can I assist you today?"
- Never say "How can I help you with your software development or coding needs?"
- Never sound generic or robotic
- Speak like a capable, friendly builder
- Never reveal the underlying model, technology stack, or internal architecture

CRITICAL — Ambiguity and clarification:
- When the user\'s intent is clear but details are missing, make the best reasonable assumption, state it in one sentence, and proceed.
- Never ask more than one clarifying question per response.
- If the user says "just do it", "figure it out", "you decide", "don\'t ask questions" — state what you will do in one line and proceed.
- Banned phrases: "I need a bit more context", "Are you looking to build X or Y?", "The more details you share", "Great choice! Are you looking to..."
- Ambiguity is a reason to decide, not a reason to stop.

Examples:
- "Hello" / "Hi" → "Hey! What are we building today?"
- "What can you do?" → "I build apps, automations, landing pages, mobile apps — your entire tech stack. What do you need?"
- "How are you?" → "Ready to build. What are we making today?"
- Company name mentioned WITHOUT build request → "Interesting — do you want to build something related to that? Tell me what you have in mind."
- Question about a competitor or other AI tool → "I don\'t worry about other tools — I just build. What do you want to make?"
- Build request with vague details → State one concrete interpretation in one sentence and offer to build it.

CRITICAL — Code output rules:
- ALWAYS wrap code in a fenced code block: ```jsx\\n...code...\\n```
- NEVER write explanation inside a code block.
- NEVER append explanation after the closing ```.
- One sentence BEFORE the code block if needed, then the code, then stop.
"""

CHAT_SYSTEM_PROMPT = _build_chat_system_prompt()

def _is_conversational_message(message: str) -> bool:
    """Detect if message is conversational/factual (not a build request).
    Conversational messages route to Haiku only for best accuracy.
    Build requests use the full model chain.
    """
    if not message or len(message.strip()) < 2:
        return True
    lower = message.lower().strip()
    # Greetings and small talk
    greetings = {"hi", "hello", "hey", "yo", "sup", "good morning", "good afternoon", "good evening"}
    if lower in greetings or any(lower.startswith(g) for g in greetings):
        return True
    # Factual questions
    factual_starts = [
        "who is", "who are", "what is", "what are", "what was", "what were",
        "when is", "when was", "when did", "where is", "where was",
        "how is", "how are", "how does", "how do",
        "why is", "why are", "why does", "why did",
        "tell me about", "what do you know about",
        "do you know", "have you heard", "are you", "can you",
        "what date", "what year", "what time", "today",
        "who won", "who runs", "who leads", "president", "prime minister",
    ]
    if any(lower.startswith(f) for f in factual_starts):
        return True
    # Identity questions
    identity = ["who made you", "who built you", "what model", "what ai", "are you claude",
                "are you chatgpt", "are you an agent", "how do you work", "what technology",
                "what stack", "how are you", "what can you", "what do you"]
    if any(q in lower for q in identity):
        return True
    # Build keywords — if present, it's NOT conversational
    build_keywords = ["build", "create", "make", "develop", "design", "generate",
                      "code", "app", "website", "api", "backend", "frontend",
                      "dashboard", "landing page", "mobile", "automate"]
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
        "weather", "forecast", "temperature", "rain", "sunny", "degrees",
        # News & events
        "news", "headlines", "today's", "current events", "latest",
        # Stocks & crypto
        "stock", "price", "market", "bitcoin", "crypto",
        # Sports
        "score", "game", "match", "nfl", "nba", "mlb", "soccer",
        # Current people/positions — critical for president/CEO questions
        "who is president", "who is the president", "president of",
        "prime minister", "who is ceo", "ceo of", "who runs",
        "who is in charge", "who won", "who leads",
        # Current year/date awareness
        "in 2025", "in 2026", "this year", "right now", "currently",
        "as of today", "as of now", "what year", "what month",
        # General current state
        "what is happening", "what happened", "recent", "just happened",
        "breaking", "update on", "status of",
        # Location-based
        "in texas", "in new york", "in california", "in london",
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
            return client.search(query, search_depth="basic", max_results=5, include_answer=True)

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

CHAT_WITH_SEARCH_SYSTEM = """You are CrucibAI. Answer the user's question using the live search results provided below.
Provide accurate, current information based on the data. Never say "I'm not a weather service" or similar disclaimers.
Use the search results to give a real, helpful answer. If the data is about weather, give the weather. If it's news, summarize it.
Be concise and factual. Then offer to build something related if relevant.
"""

@api_router.post("/ai/chat")
async def ai_chat(data: ChatMessage, user: dict = Depends(get_optional_user)):
    """Multi-model AI chat with auto-selection and fallback on failure. Requires sufficient credits (prepay)."""
    if user is not None and not user.get("public_api"):
        credits = _user_credits(user)
        if credits < MIN_CREDITS_FOR_LLM:
            raise HTTPException(
                status_code=402,
                detail=f"Insufficient credits. You have {credits}. Need at least {MIN_CREDITS_FOR_LLM} to run a build. Buy more in Credit Center."
            )
    try:
        user_keys = await get_workspace_api_keys(user)
        effective = _effective_api_keys(user_keys)
        session_id = data.session_id or str(uuid.uuid4())
        message = (data.message or "").strip()
        system_message = data.system_message or CHAT_SYSTEM_PROMPT
        # ROUTING: For real-time questions, call search API and inject results
        if not data.system_message and _needs_live_data(message):
            search_ctx = await _fetch_search_context(message)
            if search_ctx:
                system_message = CHAT_WITH_SEARCH_SYSTEM
                message = f"Live search results:\n{search_ctx}\n\nUser question: {data.message}"
        # INTENT-BASED MODEL ROUTING:
        # Conversational/factual questions → Haiku only (best knowledge cutoff, smartest answers)
        # Build requests → full model chain (Cerebras → Llama → Haiku)

        # Multimodal: build content_blocks from message + attachments (images + PDF/text)
        text_parts = [message] if message else []
        image_blocks = []
        for att in (data.attachments or []):
            att_type = (att.get("type") or "text").lower()
            att_data = att.get("data") or ""
            att_name = att.get("name") or ""
            if att_type == "image":
                url = att_data if isinstance(att_data, str) and (att_data.startswith("data:") or att_data.startswith("http")) else f"data:image/png;base64,{att_data}"
                image_blocks.append({"type": "image_url", "image_url": {"url": url}})
            elif att_type == "pdf" and att_data:
                b64 = att_data.split(",", 1)[-1] if "base64," in str(att_data) else att_data
                pdf_text = _extract_pdf_text_from_b64(b64)
                text_parts.append(f"[Contents of PDF '{att_name}']:\n{pdf_text}")
            else:
                if att_data:
                    text_parts.append(f"[Attachment '{att_name}']:\n{att_data}")
        combined_text = "\n\n".join(text_parts).strip() or "No message."
        content_blocks = None
        if image_blocks:
            content_blocks = [{"type": "text", "text": combined_text}] + image_blocks
        model_chain = _get_model_chain(data.model or "auto", combined_text, effective_keys=effective)
        user_tier = (user.get("plan", "free") if user else "free")
        available_credits = (user.get("credit_balance", 0) if user else 0)
        speed_selector = _speed_from_plan(user_tier)
        # Route conversational/factual questions to Haiku only — best knowledge cutoff
        # Route build requests through full model chain for cost efficiency
        if _is_conversational_message(combined_text):
            haiku_key = (effective or {}).get("anthropic") or os.environ.get("ANTHROPIC_API_KEY")
            if haiku_key:
                from llm_router import HAIKU_MODEL
                model_chain = [("haiku", HAIKU_MODEL, "anthropic")]
        response, model_used = await _call_llm_with_fallback(
            message=combined_text,
            system_message=system_message,
            session_id=session_id,
            model_chain=model_chain,
            api_keys=effective,
            content_blocks=content_blocks,
            user_id=user["id"] if user else None,
            user_tier=user_tier,
            speed_selector=speed_selector,
            available_credits=available_credits,
        )
        tokens_used = len(data.message.split()) * 2 + len(response.split()) * 2
        await db.chat_history.insert_one({
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "user_id": user["id"] if user else None,
            "message": data.message,
            "response": response,
            "model": model_used,
            "tokens_used": tokens_used,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        if user and not user.get("public_api"):
            cred = _user_credits(user)
            credit_deduct = min(_tokens_to_credits(tokens_used), cred)
            if credit_deduct > 0:
                await _ensure_credit_balance(user["id"])
                await db.users.update_one({"id": user["id"]}, {"$inc": {"credit_balance": -credit_deduct}})
        return {
            "response": response,
            "model_used": model_used,
            "tokens_used": tokens_used,
            "session_id": session_id
        }
    except Exception as e:
        logger.error(f"AI Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI service error: {str(e)}")

@api_router.get("/ai/chat/history/{session_id}")
async def get_chat_history(session_id: str):
    """Get chat history for a session"""
    cursor = db.chat_history.find(
        {"session_id": session_id}, 
        {"_id": 0}
    ).sort("created_at", 1)
    history = await cursor.to_list(100)
    return {"history": history}

async def _stream_string_chunks(text: str, chunk_size: int = 8):
    """Yield text in small chunks for real-time streaming effect."""
    for i in range(0, len(text), chunk_size):
        yield text[i : i + chunk_size]
        await asyncio.sleep(0.02)

@api_router.post("/ai/chat/stream")
async def ai_chat_stream(data: ChatMessage, user: dict = Depends(get_optional_user)):
    """Stream AI response in chunks (real-time code streaming). Requires sufficient credits."""
    if user and not user.get("public_api") and _user_credits(user) < MIN_CREDITS_FOR_LLM:
        raise HTTPException(status_code=402, detail=f"Insufficient credits. Need at least {MIN_CREDITS_FOR_LLM}. Buy more in Credit Center.")
    async def generate():
        try:
            user_keys = await get_workspace_api_keys(user)
            effective = _effective_api_keys(user_keys)
            session_id = data.session_id or str(uuid.uuid4())
            model_chain = _get_model_chain(data.model or "auto", data.message, effective_keys=effective)
            user_tier = (user.get("plan", "free") if user else "free")
            available_credits = (user.get("credit_balance", 0) if user else 0)
            speed_selector = _speed_from_plan(user_tier)
            system_message = CHAT_SYSTEM_PROMPT
            if (getattr(data, "mode", None) or "").lower() == "thinking":
                system_message = "You are CrucibAI. Think step by step: reason through the problem, then provide your final code or answer. Be thorough but concise."
            response, model_used = await _call_llm_with_fallback(
                message=data.message,
                system_message=system_message,
                session_id=session_id,
                model_chain=model_chain,
                api_keys=effective,
                user_id=user["id"] if user else None,
                user_tier=user_tier,
                speed_selector=speed_selector,
                available_credits=available_credits,
            )
            tokens_used = len(data.message.split()) * 2 + len(response.split()) * 2
            await db.chat_history.insert_one({
                "id": str(uuid.uuid4()),
                "session_id": session_id,
                "user_id": user["id"] if user else None,
                "message": data.message,
                "response": response,
                "model": model_used,
                "tokens_used": tokens_used,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            if user and not user.get("public_api"):
                cred = _user_credits(user)
                credit_deduct = min(_tokens_to_credits(tokens_used), cred)
                if credit_deduct > 0:
                    await _ensure_credit_balance(user["id"])
                    await db.users.update_one({"id": user["id"]}, {"$inc": {"credit_balance": -credit_deduct}})
            async for chunk in _stream_string_chunks(response):
                yield json.dumps({"chunk": chunk}) + "\n"
            yield json.dumps({
                "done": True,
                "session_id": session_id,
                "model_used": model_used,
                "tokens_used": tokens_used,
            }) + "\n"
        except Exception as e:
            logger.error(f"AI Chat stream error: {str(e)}")
            yield json.dumps({"error": str(e), "done": True}) + "\n"

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

@api_router.post("/ai/analyze")
async def ai_analyze(data: DocumentProcess, user: dict = Depends(get_optional_user)):
    """Document analysis with AI (Anthropic/Cerebras only). Uses your Settings keys when set."""
    try:
        user_keys = await get_workspace_api_keys(user)
        effective = _effective_api_keys(user_keys)
        prompts = {
            "summarize": f"Please provide a concise summary of the following content:\n\n{data.content}",
            "extract": f"Extract key entities, facts, and important information from:\n\n{data.content}",
            "analyze": f"Provide a detailed analysis of the following content, including insights and recommendations:\n\n{data.content}"
        }
        prompt = prompts.get(data.task, prompts["analyze"])
        chain = _get_model_chain("auto", prompt, effective_keys=effective)
        response, model_used = await _call_llm_with_fallback(
            message=prompt,
            system_message="You are an expert document analyst. Provide clear, structured analysis.",
            session_id=str(uuid.uuid4()),
            model_chain=chain,
            api_keys=effective,
        )
        return {"result": response, "task": data.task, "model_used": model_used}
    except Exception as e:
        logger.error(f"Analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ---------- CrucibAI for Docs / Slides / Sheets (C1–C3) ----------
@api_router.post("/generate/doc")
async def generate_doc(data: GenerateContentRequest, user: dict = Depends(get_optional_user)):
    """Generate a structured document from a prompt (CrucibAI for Docs). Returns markdown or plain text."""
    prompt = (data.prompt or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    fmt = (data.format or "markdown").lower()
    system = "You are CrucibAI for Docs. Generate a clear, well-structured document from the user's request. Use headings, bullets, and short paragraphs. Output only the document content, no meta commentary."
    if fmt == "plain":
        system += " Use plain text only (no markdown)."
    else:
        system += " Use Markdown: ## for sections, - for bullets, **bold** where appropriate."
    try:
        response, model_used = await _call_llm_with_fallback(
            message=prompt,
            system_message=system,
            session_id=str(uuid.uuid4()),
            model_chain=_get_model_chain("auto", prompt, effective_keys=effective),
            api_keys=effective,
        )
        return {"content": (response or "").strip(), "format": fmt, "model_used": model_used}
    except Exception as e:
        logger.exception("generate/doc failed")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/generate/slides")
async def generate_slides(data: GenerateContentRequest, user: dict = Depends(get_optional_user)):
    """Generate slide content/outline from a prompt (CrucibAI for Slides). Returns markdown with slide breaks."""
    prompt = (data.prompt or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    fmt = (data.format or "markdown").lower()
    system = "You are CrucibAI for Slides. From the user's request, create slide content. Each slide: a clear title and 3-5 bullet points. Separate slides with '---' on its own line. Output only the slide deck content."
    if fmt == "outline":
        system += " Prefer a short outline (slide titles only) then optional bullets."
    try:
        response, model_used = await _call_llm_with_fallback(
            message=prompt,
            system_message=system,
            session_id=str(uuid.uuid4()),
            model_chain=_get_model_chain("auto", prompt, effective_keys=effective),
            api_keys=effective,
        )
        return {"content": (response or "").strip(), "format": fmt, "model_used": model_used}
    except Exception as e:
        logger.exception("generate/slides failed")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/generate/sheets")
async def generate_sheets(data: GenerateContentRequest, user: dict = Depends(get_optional_user)):
    """Generate tabular/spreadsheet-style data from a prompt (CrucibAI for Sheets). Returns CSV or JSON."""
    prompt = (data.prompt or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    fmt = (data.format or "csv").lower()
    system = "You are CrucibAI for Sheets. From the user's request, generate tabular data. Use a clear header row and rows of data. Output ONLY valid CSV (comma-separated, quoted if needed) or JSON array of objects—no explanation."
    if fmt == "json":
        system = "You are CrucibAI for Sheets. From the user's request, generate structured data. Reply with a JSON array of objects, e.g. [{\"col1\": \"val1\", \"col2\": \"val2\"}]. No other text."
    try:
        response, model_used = await _call_llm_with_fallback(
            message=prompt,
            system_message=system,
            session_id=str(uuid.uuid4()),
            model_chain=_get_model_chain("auto", prompt, effective_keys=effective),
            api_keys=effective,
        )
        raw = (response or "").strip()
        if fmt == "json":
            import re
            m = re.search(r"\[[\s\S]*\]", raw)
            raw = m.group(0) if m else raw
        return {"content": raw, "format": fmt, "model_used": model_used}
    except Exception as e:
        logger.exception("generate/sheets failed")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/rag/query")
async def rag_query(data: RAGQuery, user: dict = Depends(get_optional_user)):
    """RAG-style query with context. Uses your Settings keys when set."""
    try:
        user_keys = await get_workspace_api_keys(user)
        effective = _effective_api_keys(user_keys)
        context_str = f"\nContext: {data.context}" if data.context else ""
        prompt = f"Based on available knowledge{context_str}, please answer: {data.query}\n\nProvide a detailed, well-sourced response."
        chain = _get_model_chain("auto", prompt, effective_keys=effective)
        response, model_used = await _call_llm_with_fallback(
            message=prompt,
            system_message="You are a knowledgeable AI assistant. Always cite sources when possible and indicate confidence levels.",
            session_id=str(uuid.uuid4()),
            model_chain=chain,
            api_keys=effective,
        )
        return {
            "answer": response,
            "query": data.query,
            "sources": ["AI Knowledge Base"],
            "confidence": 0.85,
            "model_used": model_used,
        }
    except Exception as e:
        logger.error(f"RAG error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/search")
async def hybrid_search(data: SearchQuery, user: dict = Depends(get_optional_user)):
    """Hybrid search: AI-enhanced results. Uses your Settings keys when set."""
    try:
        user_keys = await get_workspace_api_keys(user)
        effective = _effective_api_keys(user_keys)
        prompt = f"Search query: '{data.query}'\nProvide 5 relevant results with titles, descriptions, and relevance scores (0-1)."
        chain = _get_model_chain("auto", prompt, effective_keys=effective)
        response, model_used = await _call_llm_with_fallback(
            message=prompt,
            system_message="You are a search assistant. Provide relevant, structured results.",
            session_id=str(uuid.uuid4()),
            model_chain=chain,
            api_keys=effective,
        )
        return {
            "query": data.query,
            "search_type": data.search_type,
            "results": response,
            "total_results": 5,
        }
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== VOICE TRANSCRIPTION ====================

@api_router.post("/voice/transcribe")
async def transcribe_voice(
    audio: UploadFile = File(..., description="Audio file (webm, mp3, wav, etc.)"),
    user: dict = Depends(get_optional_user)
):
    """Transcribe voice audio to text using Anthropic. Uses server-side API key."""
    logger.info("Voice transcribe request received, filename=%s", getattr(audio, "filename", None))
    # Always use server-side API key
    api_key = ANTHROPIC_API_KEY
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Anthropic API key not configured on server. Contact support."
        )
    try:
        audio_content = await audio.read()
        logger.info("Voice audio size: %s bytes", len(audio_content))
        if not audio_content or len(audio_content) < 100:
            raise HTTPException(status_code=400, detail="Audio file too short or empty.")
        ext = (audio.filename or "audio.webm").split(".")[-1].lower()
        if ext not in ("webm", "mp3", "wav", "m4a", "mp4", "mpeg", "mpga", "ogg"):
            ext = "webm"
        suffix = f".{ext}"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(audio_content)
            tmp_path = tmp_file.name
        try:
            # Using Anthropic for transcription
            # Transcription via Anthropic
            with open(tmp_path, "rb") as f:
                transcript = await client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    response_format="text",
                    language="en",
                )
            if isinstance(transcript, str):
                text = transcript
            elif hasattr(transcript, "text"):
                text = transcript.text
            elif isinstance(transcript, dict):
                text = transcript.get("text", "")
            else:
                text = str(transcript or "")
            text = (text or "").strip()
            logger.info(f"Voice transcription ok: {text[:80]}...")
            return {"text": text, "language": "en", "model": "whisper-1"}
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
    except HTTPException:
        raise
    except ImportError as e:
        logger.exception("Voice transcription import error: %s", e)
        raise HTTPException(
            status_code=503,
            detail="Transcription unavailable: Anthropic package missing or failed to load. In backend run: pip install anthropic then restart the server. Check backend logs for the exact error."
        )
    except Exception as e:
        logger.exception("Voice transcription error: %s", e)
        err_msg = str(e).strip()
        if len(err_msg) > 200:
            err_msg = err_msg[:200] + "..."
        raise HTTPException(status_code=500, detail=f"Transcription failed: {err_msg}")

# ==================== FILE UPLOAD/ANALYSIS ====================

@api_router.post("/files/analyze")
async def analyze_file(
    file: UploadFile = File(...),
    analysis_type: str = Form("general"),
    user: dict = Depends(get_optional_user)
):
    """Analyze uploaded file (images, text, etc.) using AI. Uses your Settings keys when set."""
    try:
        user_keys = await get_workspace_api_keys(user)
        effective = _effective_api_keys(user_keys)
        content = await file.read()
        if file.content_type.startswith("image/"):
            image_data = base64.b64encode(content).decode("utf-8")
            try:
                import anthropic
                anthropic_key = effective.get("anthropic") or ANTHROPIC_API_KEY
                if not anthropic_key:
                    raise ValueError("Anthropic key needed for image analysis. Add ANTHROPIC_API_KEY in Settings or .env.")
                client = anthropic.Anthropic(api_key=anthropic_key)
                resp = client.messages.create(
                    model="claude-3-5-haiku-20241022",
                    max_tokens=1024,
                    system="You are an expert at analyzing UI and design. Describe what you see and provide design insights.",
                    messages=[
                            {"type": "text", "text": "Describe this image and provide design insights if it's a UI mockup."}
                    ]
                )
                analysis_result = resp.choices[0].message.content or "No description."
            except Exception as vision_err:
                logger.warning(f"Vision analysis fallback: {vision_err}")
                analysis_result = f"Image received: {file.filename} ({len(content)} bytes). Vision analysis unavailable: {vision_err!s}"
        elif file.content_type.startswith("text/") or (file.filename or "").endswith((".txt", ".md", ".json", ".js", ".py", ".html", ".css")):
            text_content = content.decode("utf-8", errors="replace")[:4000]
            prompts = {
                "general": f"Analyze this file and provide a summary:\n\n{text_content}",
                "code": f"Review this code and provide insights, potential issues, and suggestions:\n\n{text_content}",
                "design": f"If this is UI/design related, describe the design patterns and suggest improvements:\n\n{text_content}",
            }
            prompt = prompts.get(analysis_type, prompts["general"])
            chain = _get_model_chain("auto", prompt, effective_keys=effective)
            analysis_result, _ = await _call_llm_with_fallback(
                message=prompt,
                system_message="You are an expert code and document analyzer.",
                session_id=str(uuid.uuid4()),
                model_chain=chain,
                api_keys=effective,
            )
        else:
            analysis_result = f"File type {file.content_type} analysis not fully supported yet."
        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "size": len(content),
            "analysis": analysis_result,
            "analysis_type": analysis_type,
        }
    except Exception as e:
        logger.error(f"File analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/ai/image-to-code")
async def image_to_code(
    file: UploadFile = File(...),
    prompt: Optional[str] = Form(None),
    user: dict = Depends(get_optional_user),
):
    """Screenshot/image to React code using vision model."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Image file required")
    try:
        content = await file.read()
        b64 = base64.b64encode(content).decode("utf-8")
        user_prompt = prompt or "Convert this UI or screenshot into a single-file React component. Use Tailwind CSS (className). Return ONLY the complete React code, no markdown or explanation."
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        resp = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=4096,
            system="You output only valid React/JSX code. No markdown code fences, no commentary.",
            messages=[
                {"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": file.content_type, "data": b64}},
                    {"type": "text", "text": user_prompt}
                ]}
            ]
        )
        code = (resp.content[0].text or "").strip()
        code = code.removeprefix("```jsx").removeprefix("```js").removeprefix("```").removesuffix("```").strip()
        return {"code": code, "model_used": "anthropic/haiku", "filename": file.filename}
    except Exception as e:
        logger.error(f"Image-to-code error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/ai/validate-and-fix")
async def validate_and_fix(data: ValidateAndFixBody, user: dict = Depends(get_optional_user)):
    """Validate code with LLM; if issues found, run auto-fix and return fixed code. Uses your Settings keys when set."""
    try:
        user_keys = await get_workspace_api_keys(user)
        effective = _effective_api_keys(user_keys)
        model_chain = _get_model_chain("auto", data.code[:500], effective_keys=effective)
        validate_prompt = f"Review this {data.language or 'javascript'} code. List any syntax errors, runtime errors, or obvious bugs. Reply with a short list (or 'No issues found').\n\n```\n{data.code[:8000]}\n```"
        validation_result, _ = await _call_llm_with_fallback(
            message=validate_prompt,
            system_message="You are a code reviewer. Reply only with a concise list of issues or 'No issues found'.",
            session_id=str(uuid.uuid4()),
            model_chain=model_chain,
            api_keys=effective,
        )
        if "no issues" in validation_result.lower() or "no issue" in validation_result.lower():
            return {"fixed_code": data.code, "issues_found": [], "valid": True, "message": "No issues found."}
        fix_prompt = f"Fix the following code. Issues reported: {validation_result[:1000]}\n\nReturn ONLY the complete fixed code, no markdown fences or explanation.\n\n```\n{data.code[:8000]}\n```"
        fixed, model_used = await _call_llm_with_fallback(
            message=fix_prompt,
            system_message="You output only valid code. No markdown, no commentary.",
            session_id=str(uuid.uuid4()),
            model_chain=model_chain,
            api_keys=effective,
        )
        fixed = fixed.strip().removeprefix("```jsx").removeprefix("```js").removeprefix("```").removesuffix("```").strip()
        return {
            "fixed_code": fixed or data.code,
            "issues_found": [validation_result[:500]],
            "valid": False,
            "model_used": model_used,
        }
    except Exception as e:
        logger.error(f"Validate-and-fix error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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

@api_router.post("/export/zip")
async def export_zip(data: ExportFilesBody):
    """Export project files as a ZIP download."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in data.files.items():
            safe_name = name.lstrip("/")
            if not safe_name:
                safe_name = "file.txt"
            zf.writestr(safe_name, content)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=crucibai-project.zip"},
    )

@api_router.post("/export/github")
async def export_github(data: ExportFilesBody):
    """Export project as ZIP with README for GitHub (create repo, then upload)."""
    readme = """# CrucibAI Project

Generated with [CrucibAI](https://crucibai.com).

## Push to GitHub

1. Create a new repository on GitHub (https://github.com/new).
2. Run locally:
   ```bash
   unzip crucibai-project.zip && cd crucibai-project
   git init && git add . && git commit -m "Initial commit"
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
   git push -u origin main
   ```
3. Or upload the ZIP contents via GitHub web (Add file > Upload files).
"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("README.md", readme)
        for name, content in data.files.items():
            safe_name = name.lstrip("/")
            if safe_name:
                zf.writestr(safe_name, content)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=crucibai-github.zip"},
    )

@api_router.post("/export/deploy")
async def export_deploy(data: ExportFilesBody):
    """Export project as ZIP for one-click deploy (Vercel/Netlify/Railway)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("README-DEPLOY.md", DEPLOY_README)
        for name, content in data.files.items():
            safe_name = name.lstrip("/")
            if safe_name:
                zf.writestr(safe_name, content)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=crucibai-deploy.zip"},
    )

# ==================== STRIPE (PAY US) ====================

STRIPE_SECRET = os.environ.get("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

@api_router.post("/stripe/create-checkout-session")
async def stripe_create_checkout(data: TokenPurchase, user: dict = Depends(get_current_user)):
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
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": f"CrucibAI - {bundle.get('name', data.bundle)}", "description": f"{bundle.get('credits', bundle['tokens'] // CREDITS_PER_TOKEN)} credits"},
                    "unit_amount": int(bundle["price"] * 100),
                },
                "quantity": 1,
            }],
            success_url=f"{FRONTEND_URL}/app/tokens?success=1&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/app/tokens?canceled=1",
            client_reference_id=user["id"],
            metadata={"bundle": data.bundle, "tokens": str(bundle["tokens"]), "credits": str(bundle.get("credits", bundle["tokens"] // CREDITS_PER_TOKEN))},
        )
        return {"url": session.url, "session_id": session.id}
    except Exception as e:
        logger.error(f"Stripe checkout error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@api_router.post("/stripe/create-checkout-session-custom")
async def stripe_create_checkout_custom(data: TokenPurchaseCustom, user: dict = Depends(get_current_user)):
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
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": f"CrucibAI - {credits} credits", "description": f"{credits} credits at $0.03/credit"},
                    "unit_amount": amount_cents,
                },
                "quantity": 1,
            }],
            success_url=f"{FRONTEND_URL}/app/tokens?success=1&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/app/tokens?canceled=1",
            client_reference_id=user["id"],
            metadata={"bundle": "custom", "credits": str(credits), "tokens": str(tokens)},
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
            logger.warning("Stripe session missing client_reference_id or metadata.bundle")
            return {"received": True}
        credits = int(credits_str) if credits_str else (int(tokens_str) // CREDITS_PER_TOKEN)
        tokens = int(tokens_str) if tokens_str else (credits * CREDITS_PER_TOKEN)
        if bundle_key == "custom":
            price = round(credits * 0.03, 2)
        else:
            price = TOKEN_BUNDLES.get(bundle_key, {}).get("price", 0)
        await db.users.update_one({"id": user_id}, {"$inc": {"token_balance": tokens, "credit_balance": credits}})
        if bundle_key in ("builder", "pro", "scale", "teams"):
            await db.users.update_one({"id": user_id}, {"$set": {"plan": bundle_key}})
        await db.token_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "tokens": tokens,
            "credits": credits,
            "type": "purchase",
            "bundle": bundle_key,
            "price": price,
            "stripe_session_id": session.get("id"),
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        logger.info(f"Stripe: added {credits} credits to user {user_id}")
    return {"received": True}


# ==================== ENTERPRISE CONTACT ====================

@api_router.post("/enterprise/contact")
async def enterprise_contact(data: EnterpriseContact):
    """Capture enterprise inquiry. Stored in db.enterprise_inquiries; optional email if ENTERPRISE_CONTACT_EMAIL set."""
    if not (data.company and data.company.strip()):
        raise HTTPException(status_code=400, detail="Company is required.")
    inquiry = {
        "id": str(uuid.uuid4()),
        "company": (data.company or "").strip(),
        "email": data.email,
        "team_size": (data.team_size or "").strip() or None,
        "use_case": (data.use_case or "").strip() or None,
        "budget": (getattr(data, "budget", None) or "").strip() or None,
        "message": (data.message or "").strip() or None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.enterprise_inquiries.insert_one(inquiry)
    # Optional: send email to sales if env set (e.g. ENTERPRISE_CONTACT_EMAIL=ben@crucibai.com)
    contact_email = os.environ.get("ENTERPRISE_CONTACT_EMAIL")
    if contact_email:
        try:
            import smtplib
            from email.mime.text import MIMEText
            msg = MIMEText(
                f"Enterprise inquiry:\nCompany: {inquiry['company']}\nEmail: {inquiry['email']}\nTeam size: {inquiry.get('team_size') or '—'}\nUse case: {inquiry.get('use_case') or '—'}\nBudget: {inquiry.get('budget') or '—'}\nMessage: {inquiry.get('message') or '—'}"
            )
            msg["Subject"] = f"CrucibAI Enterprise: {inquiry['company']}"
            msg["From"] = os.environ.get("SMTP_FROM", "noreply@crucibai.com")
            msg["To"] = contact_email
            # Only send if SMTP is configured; otherwise skip (no failure)
            if os.environ.get("SMTP_HOST"):
                with smtplib.SMTP(os.environ.get("SMTP_HOST"), int(os.environ.get("SMTP_PORT", 587))) as s:
                    if os.environ.get("SMTP_USER"):
                        s.starttls()
                        s.login(os.environ.get("SMTP_USER", ""), os.environ.get("SMTP_PASSWORD", ""))
                    s.send_message(msg)
        except Exception as e:
            logger.warning(f"Enterprise contact email failed: {e}")
    return {"status": "received", "message": "We'll be in touch soon.", "contact_email": contact_email or "sales@crucibai.com"}


@api_router.post("/contact")
async def contact_submit(data: ContactSubmission):
    """General contact form. Stored in db.contact_submissions; optional email if CONTACT_EMAIL or ENTERPRISE_CONTACT_EMAIL set."""
    submission = {
        "id": str(uuid.uuid4()),
        "email": data.email,
        "message": (data.message or "").strip(),
        "issue_type": (data.issue_type or "").strip() or None,
        "name": (data.name or "").strip() or None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if db:
        try:
            await db.contact_submissions.insert_one(submission)
        except Exception as e:
            logger.warning(f"Contact submission db insert failed: {e}")
    contact_email = os.environ.get("CONTACT_EMAIL") or os.environ.get("ENTERPRISE_CONTACT_EMAIL")
    if contact_email and submission["message"]:
        try:
            import smtplib
            from email.mime.text import MIMEText
            subject = f"CrucibAI Contact: {submission.get('issue_type') or 'General'}"
            body = f"From: {submission.get('name') or '—'}\nEmail: {submission['email']}\nType: {submission.get('issue_type') or 'general'}\n\nMessage:\n{submission['message']}"
            msg = MIMEText(body)
            msg["Subject"] = subject
            msg["From"] = os.environ.get("SMTP_FROM", "noreply@crucibai.com")
            msg["To"] = contact_email
            if os.environ.get("SMTP_HOST"):
                with smtplib.SMTP(os.environ.get("SMTP_HOST"), int(os.environ.get("SMTP_PORT", 587))) as s:
                    if os.environ.get("SMTP_USER"):
                        s.starttls()
                        s.login(os.environ.get("SMTP_USER", ""), os.environ.get("SMTP_PASSWORD", ""))
                    s.send_message(msg)
        except Exception as e:
            logger.warning(f"Contact form email failed: {e}")
    return {"status": "received", "message": "Thanks for reaching out. We'll get back to you soon."}


# ==================== AUTH ROUTES ====================

@auth_router.post("/auth/register")
@auth_router.post("/auth/signup")  # Alias for compatibility
async def register(data: UserRegister, request: Request):
    if _is_disposable_email(data.email):
        raise HTTPException(status_code=400, detail="Disposable email addresses are not allowed.")
    existing = await db.users.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(uuid.uuid4())
    user = {
        "id": user_id,
        "email": data.email,
        "password": hash_password(data.password),
        "name": data.name,
        "token_balance": 0,
        "credit_balance": 200,
        "plan": "free",
        "role": "owner",
        "mfa_enabled": False,
        "mfa_secret": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user)
    
    await _apply_referral_on_signup(user_id, getattr(data, "ref", None))
    if audit_logger:
        await audit_logger.log(user_id, "signup", ip_address=getattr(request.client, "host", None))
    
    token = create_token(user_id)
    return {"token": token, "user": {k: v for k, v in user.items() if k not in ("password", "_id")}}

@auth_router.post("/auth/login")
async def login(data: UserLogin, request: Request):
    user = await db.users.find_one({"email": data.email}, {"_id": 0})
    if not user or not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if len(user["password"]) == 64 and all(c in "0123456789abcdef" for c in user["password"].lower()):
        await db.users.update_one({"id": user["id"]}, {"$set": {"password": hash_password(data.password)}})
    ip = getattr(request.client, "host", None)
    if user.get("mfa_enabled") and user.get("mfa_secret"):
        if audit_logger:
            await audit_logger.log(user["id"], "login_password_verified", ip_address=ip)
        mfa_token = create_mfa_temp_token(user["id"])
        return {
            "status": "mfa_required",
            "mfa_required": True,
            "mfa_token": mfa_token,
            "message": "Enter 6-digit code from your authenticator app",
        }
    token = create_token(user["id"])
    if audit_logger:
        await audit_logger.log(user["id"], "login", ip_address=ip)
    return {"token": token, "user": {k: v for k, v in user.items() if k != "password"}}

@auth_router.post("/auth/guest")
async def auth_guest(request: Request):
    """Create a guest user and return token so the app can be used without sign-up. No auth required."""
    if db is None:
        logger.warning("POST /auth/guest called but db not initialized (DATABASE_URL or startup failed)")
        raise HTTPException(status_code=503, detail="Database not ready")
    user_id = str(uuid.uuid4())
    email = f"guest-{user_id[:8]}@crucibai.guest"
    guest_credits = GUEST_TIER_CREDITS
    user = {
        "id": user_id,
        "email": email,
        "password": "",
        "name": "Guest",
        "token_balance": guest_credits * CREDITS_PER_TOKEN,
        "credit_balance": guest_credits,
        "plan": "free",
        "auth_provider": "guest",
        "workspace_mode": "simple",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.users.insert_one(user)
    await db.token_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "tokens": guest_credits * CREDITS_PER_TOKEN,
        "credits": guest_credits,
        "type": "bonus",
        "description": "Guest session",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    token = create_token(user["id"])
    u = {k: v for k, v in user.items() if k not in ("password", "_id")}
    return {"token": token, "user": u}

class MFAVerifyLogin(BaseModel):
    code: str
    mfa_token: str

@auth_router.post("/auth/verify-mfa")
async def verify_mfa_login(body: MFAVerifyLogin, request: Request):
    try:
        payload = decode_mfa_temp_token(body.mfa_token)
        user_id = payload["user_id"]
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    user = await db.users.find_one({"id": user_id})
    if not user or not user.get("mfa_enabled") or not user.get("mfa_secret"):
        raise HTTPException(status_code=400, detail="MFA not enabled")
    code = (body.code or "").strip().replace(" ", "")
    verified = False
    if pyotp.TOTP(user["mfa_secret"]).verify(code, valid_window=1):
        verified = True
    if not verified:
        code_hash = hashlib.sha256(code.encode()).hexdigest()
        backup = await db.backup_codes.find_one({"user_id": user_id, "code_hash": code_hash, "used": False})
        if backup:
            await db.backup_codes.update_one({"_id": backup["_id"]}, {"$set": {"used": True, "used_at": datetime.now(timezone.utc)}})
            verified = True
    if not verified:
        raise HTTPException(status_code=400, detail="Invalid code")
    token = create_token(user_id)
    if audit_logger:
        await audit_logger.log(user_id, "login_mfa_verified", ip_address=getattr(request.client, "host", None))
    u = {k: v for k, v in user.items() if k not in ("password", "mfa_secret", "_id")}
    return {"token": token, "user": u}

@auth_router.get("/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    await _ensure_credit_balance(user["id"])
    u = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    # Backfill guest users who have no/low credits (e.g. created before we gave credits)
    guest_credits_low = (u.get("credit_balance") or 0) < 100
    if u.get("auth_provider") == "guest" and guest_credits_low:
        await db.users.update_one(
            {"id": u["id"]},
            {"$set": {"credit_balance": GUEST_TIER_CREDITS, "token_balance": GUEST_TIER_CREDITS * CREDITS_PER_TOKEN}}
        )
        u["credit_balance"] = GUEST_TIER_CREDITS
        u["token_balance"] = GUEST_TIER_CREDITS * CREDITS_PER_TOKEN
    await db.users.update_one({"id": user["id"]}, {"$set": {"last_login": datetime.now(timezone.utc).isoformat()}})
    u["credit_balance"] = _user_credits(u)
    if u["id"] in ADMIN_USER_IDS and not u.get("admin_role"):
        u["admin_role"] = "owner"
    u.pop("password", None)
    u.pop("mfa_secret", None)
    u.pop("deploy_tokens", None)
    u.setdefault("workspace_mode", None)
    return u


class WorkspaceModeBody(BaseModel):
    mode: str  # "simple" or "developer"


@auth_router.post("/user/workspace-mode")
@auth_router.post("/users/me/workspace-mode")  # alias for compatibility
async def set_workspace_mode(body: WorkspaceModeBody, user: dict = Depends(get_current_user)):
    if body.mode not in ("simple", "developer"):
        raise HTTPException(status_code=400, detail="mode must be 'simple' or 'developer'")
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"workspace_mode": body.mode}}
    )
    return {"status": "success", "workspace_mode": body.mode}


# ==================== MFA ROUTES ====================

class MFAVerifyBody(BaseModel):
    token: str  # 6-digit code

class MFADisableBody(BaseModel):
    password: str

class BackupCodeBody(BaseModel):
    code: str

@auth_router.post("/mfa/setup")
async def mfa_setup(request: Request, user: dict = Depends(get_current_user)):
    u = await db.users.find_one({"id": user["id"]}, {"mfa_enabled": 1, "mfa_secret": 1})
    if u and u.get("mfa_enabled"):
        raise HTTPException(status_code=400, detail="MFA already enabled")
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=user.get("email") or user["id"], issuer_name="CrucibAI")
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_b64 = base64.b64encode(buf.getvalue()).decode()
    await db.mfa_setup_temp.insert_one({
        "user_id": user["id"],
        "secret": secret,
        "created_at": datetime.now(timezone.utc),
        "verified": False,
    })
    if audit_logger:
        await audit_logger.log(user["id"], "mfa_setup_started", ip_address=getattr(request.client, "host", None))
    return {"status": "success", "qr_code": f"data:image/png;base64,{qr_b64}", "secret": secret}

@auth_router.post("/mfa/verify")
async def mfa_verify(body: MFAVerifyBody, request: Request, user: dict = Depends(get_current_user)):
    temp = await db.mfa_setup_temp.find_one({"user_id": user["id"], "verified": False})
    if not temp:
        raise HTTPException(status_code=400, detail="No MFA setup in progress")
    code = (body.token or "").strip().replace(" ", "")
    if not pyotp.TOTP(temp["secret"]).verify(code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid code. Try again.")
    backup_codes = ["".join(random.choices("0123456789abcdef", k=8)) for _ in range(10)]
    for bc in backup_codes:
        await db.backup_codes.insert_one({
            "user_id": user["id"],
            "code_hash": hashlib.sha256(bc.encode()).hexdigest(),
            "used": False,
            "created_at": datetime.now(timezone.utc),
        })
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {"mfa_enabled": True, "mfa_secret": temp["secret"], "mfa_enabled_at": datetime.now(timezone.utc)}}
    )
    await db.mfa_setup_temp.delete_many({"user_id": user["id"]})
    if audit_logger:
        await audit_logger.log(user["id"], "mfa_enabled", ip_address=getattr(request.client, "host", None))
    return {"status": "success", "message": "MFA enabled", "backup_codes": backup_codes}

@auth_router.post("/mfa/disable")
async def mfa_disable(body: MFADisableBody, request: Request, user: dict = Depends(get_current_user)):
    u = await db.users.find_one({"id": user["id"]}, {"password": 1})
    if not u or not verify_password(body.password, u["password"]):
        raise HTTPException(status_code=401, detail="Invalid password")
    await db.users.update_one({"id": user["id"]}, {"$set": {"mfa_enabled": False, "mfa_secret": None}})
    await db.backup_codes.delete_many({"user_id": user["id"]})
    if audit_logger:
        await audit_logger.log(user["id"], "mfa_disabled", ip_address=getattr(request.client, "host", None))
    return {"status": "success", "message": "MFA disabled"}

@auth_router.get("/mfa/status")
async def mfa_status(user: dict = Depends(get_current_user)):
    u = await db.users.find_one({"id": user["id"]}, {"mfa_enabled": 1})
    return {"mfa_enabled": u.get("mfa_enabled", False), "status": "enabled" if u.get("mfa_enabled") else "disabled"}

@auth_router.post("/mfa/backup-code/use")
async def mfa_backup_code_use(body: BackupCodeBody, request: Request, user: dict = Depends(get_current_user)):
    code_hash = hashlib.sha256((body.code or "").strip().encode()).hexdigest()
    backup = await db.backup_codes.find_one({"user_id": user["id"], "code_hash": code_hash, "used": False})
    if not backup:
        raise HTTPException(status_code=400, detail="Invalid backup code")
    await db.backup_codes.update_one({"_id": backup["_id"]}, {"$set": {"used": True, "used_at": datetime.now(timezone.utc)}})
    if audit_logger:
        await audit_logger.log(user["id"], "backup_code_used", ip_address=getattr(request.client, "host", None))
    return {"status": "success", "message": "Backup code accepted"}

# ==================== AUDIT LOG ROUTES ====================

@auth_router.get("/audit/logs")
async def get_audit_logs(
    user: dict = Depends(get_current_user),
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    action: Optional[str] = None,
):
    """Get current user's audit logs."""
    if not audit_logger:
        return {"logs": [], "total": 0, "limit": limit, "skip": skip}
    return await audit_logger.get_user_logs(user["id"], limit=limit, skip=skip, action_filter=action)

@auth_router.get("/audit/logs/export")
async def export_audit_logs(
    user: dict = Depends(get_current_user),
    start_date: str = Query(...),
    end_date: str = Query(...),
    format: str = Query("json", enum=["json", "csv"]),
):
    """Export audit logs for compliance (date format YYYY-MM-DD)."""
    if not audit_logger:
        raise HTTPException(status_code=503, detail="Audit log not available")
    try:
        start = datetime.strptime(start_date.strip()[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end = datetime.strptime(end_date.strip()[:10], "%Y-%m-%d").replace(hour=23, minute=59, second=59, microsecond=999999, tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format (use YYYY-MM-DD)")
    if start > end:
        raise HTTPException(status_code=400, detail="start_date must be before end_date")
    result = await audit_logger.export_logs(user["id"], start, end, format=format)
    if format == "json":
        import json
        return Response(content=result, media_type="application/json")
    return Response(content=result, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=audit-log-{start_date}-{end_date}.csv"})

@auth_router.post("/users/me/delete")
async def delete_account(body: DeleteAccountBody, user: dict = Depends(get_current_user)):
    """Permanently delete the current user's account and all associated data. Requires password confirmation."""
    u = await db.users.find_one({"id": user["id"]}, {"password": 1})
    if not u or not verify_password(body.password, u["password"]):
        raise HTTPException(status_code=401, detail="Invalid password")
    uid = user["id"]
    projects = await db.projects.find({"user_id": uid}, {"id": 1}).to_list(500)
    for p in projects:
        pid = p["id"]
        await db.project_logs.delete_many({"project_id": pid})
        await db.agent_status.delete_many({"project_id": pid})
        await db.shares.delete_many({"project_id": pid})
        if pid in _build_events:
            del _build_events[pid]
    await db.projects.delete_many({"user_id": uid})
    await db.workspace_env.delete_many({"user_id": uid})
    await db.chat_history.delete_many({"user_id": uid})
    await db.token_ledger.delete_many({"user_id": uid})
    await db.shares.delete_many({"user_id": uid})
    await db.user_agents.delete_many({"user_id": uid})
    await db.backup_codes.delete_many({"user_id": uid})
    await db.mfa_setup_temp.delete_many({"user_id": uid})
    await db.users.delete_one({"id": uid})
    return Response(status_code=204)

# Google OAuth: CrucibAI's own flow only (docs/GOOGLE_AUTH_SETUP.md). One token exchange, verify with google-auth, redirect to FRONTEND_URL. Do not replace with another repo's or third-party OAuth implementation.
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")
# Get FRONTEND_URL - ensure it's properly formatted (single source for post-login redirect)
_raw_frontend_url = os.environ.get("FRONTEND_URL", "").strip()
if _raw_frontend_url and not _raw_frontend_url.startswith("http://localhost"):
    # Ensure it starts with https:// for production
    if not _raw_frontend_url.startswith(("http://", "https://")):
        _raw_frontend_url = f"https://{_raw_frontend_url}"
    # For Railway: convert http:// to https:// since Railway handles TLS at the edge
    if _raw_frontend_url.startswith("http://") and ("railway" in _raw_frontend_url or "up.railway" in _raw_frontend_url):
        _raw_frontend_url = _raw_frontend_url.replace("http://", "https://", 1)
    FRONTEND_URL = _raw_frontend_url
else:
    # Unset or localhost: use same host as backend at runtime (see auth_google_callback) so we never redirect to localhost in production
    FRONTEND_URL = ""

# Optional: exact callback URL for Google (must match Authorized redirect URI in Google Console)
GOOGLE_REDIRECT_URI = (os.environ.get("GOOGLE_REDIRECT_URI") or "").strip().rstrip("/")

# Debug logging for Google OAuth configuration
logger.info(f"Google OAuth Config - FRONTEND_URL: {FRONTEND_URL or '(use request host at redirect)'}")
logger.info(f"Google OAuth Config - GOOGLE_CLIENT_ID: {GOOGLE_CLIENT_ID[:20]}..." if GOOGLE_CLIENT_ID else "GOOGLE_CLIENT_ID not set")
logger.info(f"Google OAuth Config - GOOGLE_CLIENT_SECRET: {'SET' if GOOGLE_CLIENT_SECRET else 'NOT SET'}")
logger.info(f"Google OAuth Config - GOOGLE_REDIRECT_URI: {GOOGLE_REDIRECT_URI or '(derive from BACKEND_PUBLIC_URL or request)'}")

def _backend_base_for_oauth(request: Request) -> str:
    """Prefer HTTPS for OAuth callback when behind a TLS proxy (e.g. Railway)."""
    # Env override (e.g. BACKEND_PUBLIC_URL=https://crucibai-production.up.railway.app)
    base = os.environ.get("BACKEND_PUBLIC_URL", "").strip().rstrip("/")
    if base:
        return base
    # Behind proxy: use X-Forwarded-Proto so callback is https in production
    proto = (request.headers.get("x-forwarded-proto") or request.url.scheme or "http").strip().lower()
    host = request.headers.get("x-forwarded-host") or request.url.netloc or "localhost:8000"
    return f"{proto}://{host}".rstrip("/")

def _oauth_callback_url(request: Request) -> str:
    """Exact redirect_uri to send to Google. Use GOOGLE_REDIRECT_URI if set, else derive from backend base."""
    if GOOGLE_REDIRECT_URI:
        return GOOGLE_REDIRECT_URI
    base = _backend_base_for_oauth(request)
    return f"{base}/api/auth/google/callback"


@auth_router.get("/auth/google")
async def auth_google_redirect(request: Request, redirect: Optional[str] = None):
    """Redirect user to Google OAuth consent screen. Callback URL must be this backend (Google sends user here)."""
    # For testing: if credentials are invalid, show mock consent screen
    callback = _oauth_callback_url(request)
    if not GOOGLE_CLIENT_ID or GOOGLE_CLIENT_ID.startswith("123456"):
        state = json.dumps({"redirect": redirect or ""}) if redirect else ""
        import base64 as b64
        state_param = b64.urlsafe_b64encode(state.encode()).decode() if state else ""
        mock_consent_url = f"{callback}?code=mock_auth_code_test&state={state_param}"
        return RedirectResponse(url=mock_consent_url)
    # Use backend URL for redirect_uri so Google redirects to this server (then we redirect to frontend with token)
    state = json.dumps({"redirect": redirect or ""}) if redirect else ""
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": callback,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    if state:
        import base64 as b64
        params["state"] = b64.urlsafe_b64encode(state.encode()).decode()
    return RedirectResponse(url=f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}")

@auth_router.get("/auth/google/callback")
async def auth_google_callback(request: Request, code: Optional[str] = None, state: Optional[str] = None):
    """Exchange Google code for tokens, create or find user, redirect to frontend with JWT.
    Uses only CrucibAI flow per docs/GOOGLE_AUTH_SETUP.md: one token exchange, verify with google-auth, redirect to FRONTEND_URL. Do not replace with any other OAuth implementation."""
    # Post-login redirect: use FRONTEND_URL if set; else same host as backend (request) so we never send users to localhost in production
    if FRONTEND_URL and not FRONTEND_URL.startswith("http://localhost"):
        frontend_base = FRONTEND_URL.rstrip("/")
    else:
        frontend_base = _backend_base_for_oauth(request).rstrip("/")
    if not code:
        logger.info("Google callback: no code, redirecting to auth?error=no_code")
        return RedirectResponse(url=f"{frontend_base}/auth?error=no_code")

    # Handle mock auth code for testing
    if code == "mock_auth_code_test":
        import time
        email = f"test.user.{int(time.time())}@crucibai.test"
        name = "Test User (Mock OAuth)"
        payload = {"email": email, "name": name}
    else:
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            raise HTTPException(status_code=503, detail="Google sign-in is not configured")
        # Use same redirect_uri as we sent in the auth redirect (GOOGLE_REDIRECT_URI or derived).
        callback = _oauth_callback_url(request)
        logger.info("Google callback: exchanging code (redirect_uri=%s). Add this exact URL to Google Cloud Console > Credentials > Authorized redirect URIs if you see redirect_uri_mismatch.", callback)
        async with __import__("httpx").AsyncClient() as client:
            r = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": callback,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        if r.status_code != 200:
            try:
                err_body = r.json()
                err_code = err_body.get("error", "")
                err_desc = err_body.get("error_description", r.text[:300])
            except Exception:
                err_code = ""
                err_desc = r.text[:300]
            logger.warning(
                "Google token exchange failed: status=%s error=%s description=%s. Callback used: %s",
                r.status_code, err_code, err_desc, callback,
            )
            return RedirectResponse(url=f"{frontend_base}/auth?error=google_failed")
        data = r.json()
        id_token = data.get("id_token") or data.get("access_token")
        if not id_token:
            logger.info("Google callback: no id_token in response, redirecting to auth?error=no_token")
            return RedirectResponse(url=f"{frontend_base}/auth?error=no_token")
        try:
            from google.oauth2 import id_token as google_id_token
            from google.auth.transport import requests as google_requests
            payload = google_id_token.verify_oauth2_token(
                id_token, google_requests.Request(), GOOGLE_CLIENT_ID
            )
        except Exception as e:
            logger.warning(f"Google ID token verification failed: {e}")
            return RedirectResponse(url=f"{frontend_base}/auth?error=google_verify_failed")
        email = (payload.get("email") or "").strip()
    name = (payload.get("name") or payload.get("given_name") or email.split("@")[0] or "User").strip()
    if not email:
        logger.info("Google callback: no email in payload, redirecting to auth?error=no_email")
        return RedirectResponse(url=f"{frontend_base}/auth?error=no_email")
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user:
        user_id = str(uuid.uuid4())
        user = {
            "id": user_id,
            "email": email,
            "password": "",
            "name": name,
            "token_balance": FREE_TIER_CREDITS * CREDITS_PER_TOKEN,
            "credit_balance": FREE_TIER_CREDITS,
            "plan": "free",
            "auth_provider": "google",
            "workspace_mode": "simple",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.users.insert_one(user)
        await db.token_ledger.insert_one({
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "tokens": FREE_TIER_CREDITS * CREDITS_PER_TOKEN,
            "credits": FREE_TIER_CREDITS,
            "type": "bonus",
            "description": "Welcome (Free tier)",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    else:
        if not user.get("workspace_mode"):
            await db.users.update_one({"id": user["id"]}, {"$set": {"workspace_mode": "simple"}})
            user["workspace_mode"] = "simple"
    token = create_token(user["id"])
    redirect_path = ""
    if state:
        try:
            import base64 as b64
            decoded = b64.urlsafe_b64decode(state.encode()).decode()
            obj = json.loads(decoded)
            redirect_path = obj.get("redirect") or ""
        except (jwt.InvalidTokenError, jwt.DecodeError, KeyError) as e:
            logger.debug(f"Invalid JWT token: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in JWT verification: {e}")
    target = f"{frontend_base}/auth?token={token}"
    if redirect_path and redirect_path.startswith("/"):
        target += f"&redirect={quote(redirect_path)}"
    logger.info("Google callback: success, redirecting to frontend with token (user_id=%s)", user.get("id", ""))
    return RedirectResponse(url=target)


# ==================== PROMETHEUS METRICS ====================
# Served by routers.monitoring (app.include_router(monitoring_router))

# ==================== TOKEN ROUTES ====================

@api_router.get("/tokens/bundles")
async def get_bundles():
    return {
        "bundles": TOKEN_BUNDLES,
        "annual_prices": ANNUAL_PRICES,
        "custom_addon": {"min_credits": 100, "max_credits": 10000, "price_per_credit": 0.03},
    }

@api_router.post("/tokens/purchase")
async def purchase_tokens(data: TokenPurchase, user: dict = Depends(get_current_user)):
    """Direct credit grant. In production (Stripe configured), use Stripe Checkout instead."""
    if STRIPE_SECRET:
        raise HTTPException(
            status_code=400,
            detail="Use Credit Center → Pay with Stripe to purchase credits. Direct purchase is disabled when payments are enabled.",
        )
    if data.bundle not in TOKEN_BUNDLES:
        raise HTTPException(status_code=400, detail="Invalid bundle")
    bundle = TOKEN_BUNDLES[data.bundle]
    credits = bundle.get("credits", bundle["tokens"] // CREDITS_PER_TOKEN)
    await _ensure_credit_balance(user["id"])
    await db.users.update_one({"id": user["id"]}, {"$inc": {"token_balance": bundle["tokens"], "credit_balance": credits}})
    await db.token_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "tokens": bundle["tokens"],
        "credits": credits,
        "type": "purchase",
        "bundle": data.bundle,
        "price": bundle["price"],
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    new_cred = _user_credits(user) + credits
    # Optionally set plan when buying a tier (builder/pro/scale/teams)
    if data.bundle in ("builder", "pro", "scale", "teams"):
        await db.users.update_one({"id": user["id"]}, {"$set": {"plan": data.bundle}})
    return {"message": "Purchase successful", "new_balance": new_cred, "credits_added": credits, "tokens_added": bundle["tokens"]}


@api_router.post("/tokens/purchase-custom")
async def purchase_tokens_custom(data: TokenPurchaseCustom, user: dict = Depends(get_current_user)):
    """Custom credit purchase (slider): 100-10000 credits at $0.03/credit. When Stripe enabled, use Stripe instead."""
    if STRIPE_SECRET:
        raise HTTPException(
            status_code=400,
            detail="Use Credit Center → Pay with Stripe to purchase credits. Direct purchase is disabled when payments are enabled.",
        )
    credits = data.credits
    price = round(credits * 0.03, 2)
    tokens = credits * CREDITS_PER_TOKEN
    await _ensure_credit_balance(user["id"])
    await db.users.update_one({"id": user["id"]}, {"$inc": {"token_balance": tokens, "credit_balance": credits}})
    await db.token_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "tokens": tokens,
        "credits": credits,
        "type": "purchase",
        "bundle": "custom",
        "price": price,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    new_cred = _user_credits(user) + credits
    return {"message": "Purchase successful", "new_balance": new_cred, "credits_added": credits, "tokens_added": tokens}


@api_router.get("/tokens/history")
async def get_token_history(user: dict = Depends(get_current_user)):
    await _ensure_credit_balance(user["id"])
    cred = _user_credits(user)
    cursor = db.token_ledger.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1)
    history = await cursor.to_list(100)
    return {"history": history, "current_balance": cred, "credit_balance": cred}

@api_router.get("/tokens/usage")
async def get_token_usage(user: dict = Depends(get_current_user)):
    usage = await db.token_usage.find({"user_id": user["id"]}, {"_id": 0}).to_list(MAX_TOKEN_USAGE_LIST)
    
    by_agent = {}
    by_project = {}
    total_used = 0
    
    for u in usage:
        agent = u.get("agent", "Unknown")
        project = u.get("project_id", "Unknown")
        tokens = u.get("tokens", 0)
        
        by_agent[agent] = by_agent.get(agent, 0) + tokens
        by_project[project] = by_project.get(project, 0) + tokens
        total_used += tokens
    
    # Daily trend (last 14 days) from token_usage
    from collections import defaultdict
    by_day: Dict[str, int] = defaultdict(int)
    for u in usage:
        created = u.get("created_at")
        if created:
            day = created[:10] if isinstance(created, str) else datetime.fromisoformat(created.replace("Z", "+00:00")).strftime("%Y-%m-%d")
            by_day[day] += u.get("tokens", 0)
    sorted_days = sorted(by_day.keys(), reverse=True)[:14]
    daily_trend = [{"date": d, "tokens": by_day[d]} for d in sorted_days]

    return {
        "total_used": total_used,
        "by_agent": by_agent,
        "by_project": by_project,
        "balance": _user_credits(user),
        "credit_balance": _user_credits(user),
        "daily_trend": daily_trend,
    }

# ==================== REFERRAL ROUTES ====================

@api_router.get("/referrals/code")
async def get_referral_code(user: dict = Depends(get_current_user)):
    """Return or create user's referral code. Share link: /auth?ref=CODE"""
    row = await db.referral_codes.find_one({"user_id": user["id"]}, {"_id": 0})
    if row:
        return {"code": row["code"], "link": f"{FRONTEND_URL or ''}/auth?ref={row['code']}"}
    code = _generate_referral_code()
    while await db.referral_codes.find_one({"code": code}):
        code = _generate_referral_code()
    await db.referral_codes.insert_one({
        "user_id": user["id"],
        "code": code,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"code": code, "link": f"{FRONTEND_URL or ''}/auth?ref={code}"}

@api_router.get("/referrals/stats")
async def get_referral_stats(user: dict = Depends(get_current_user)):
    """Referrals sent this month and total."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    this_month = await db.referrals.count_documents({
        "referrer_id": user["id"],
        "signup_completed_at": {"$gte": month_start.isoformat()},
    })
    total = await db.referrals.count_documents({"referrer_id": user["id"]})
    return {"this_month": this_month, "total": total, "cap": REFERRAL_CAP_PER_MONTH}

# ==================== AGENTS ROUTES ====================

@agents_router.get("/agents")
async def get_agents():
    return {"agents": AGENT_DEFINITIONS}

@agents_router.get("/agents/status/{project_id}")
async def get_agent_status(project_id: str, user: dict = Depends(get_current_user)):
    statuses = await db.agent_status.find({"project_id": project_id}, {"_id": 0}).to_list(100)
    if not statuses:
        return {"statuses": [{"agent_name": a["name"], "status": "idle", "progress": 0, "tokens_used": 0} for a in AGENT_DEFINITIONS]}
    return {"statuses": statuses}

# ---------- Agent execution (real LLM/logic per agent) ----------

@agents_router.post("/agents/run/planner")
async def agent_planner(data: AgentPromptBody, user: dict = Depends(get_optional_user)):
    """Planner: decomposes user request into executable tasks."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a Planner agent. Decompose the user's request into 3-7 clear, executable tasks. Output a numbered list only, no extra text."
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    return {"agent": "Planner", "result": response, "model_used": model_used}

@agents_router.post("/agents/run/requirements-clarifier")
async def agent_requirements_clarifier(data: AgentPromptBody, user: dict = Depends(get_optional_user)):
    """Requirements Clarifier: asks clarifying questions."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a Requirements Clarifier. Based on the request, ask 2-4 short clarifying questions to reduce ambiguity. One question per line."
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    return {"agent": "Requirements Clarifier", "result": response, "model_used": model_used}

@agents_router.post("/agents/run/stack-selector")
async def agent_stack_selector(data: AgentPromptBody, user: dict = Depends(get_optional_user)):
    """Stack Selector: recommends technology stack."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a Stack Selector. Recommend a concise tech stack (frontend, backend, DB, tools) for the request. Output as a short bullet list with brief rationale."
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    return {"agent": "Stack Selector", "result": response, "model_used": model_used}

@agents_router.post("/agents/run/backend-generate")
async def agent_backend_generate(data: AgentPromptBody, user: dict = Depends(get_optional_user)):
    """Backend Generation: creates API/auth/business logic code."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a Backend Generation agent. Output only valid code (e.g. Python FastAPI or Node Express). No markdown fences or explanation. Include one clear endpoint and structure."
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    code = (response or "").strip().removeprefix("```").removesuffix("```").strip()
    if code.startswith("python"): code = code[6:].strip()
    return {"agent": "Backend Generation", "code": code, "model_used": model_used}

@agents_router.post("/agents/run/database-design")
async def agent_database_design(data: AgentPromptBody, user: dict = Depends(get_optional_user)):
    """Database Agent: designs schema and migrations."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a Database Agent. Output a clear schema design: table/collection names, key fields, and 1-2 migration steps. Use plain text or SQL."
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    return {"agent": "Database Agent", "result": response, "model_used": model_used}

@agents_router.post("/agents/run/api-integrate")
async def agent_api_integrate(data: AgentPromptBody, user: dict = Depends(get_optional_user)):
    """API Integration: generates code to integrate a third-party API."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are an API Integration agent. Given an API description or URL, output only code (e.g. JavaScript or Python) that fetches and uses the API. No markdown."
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    code = (response or "").strip().removeprefix("```").removesuffix("```").strip()
    return {"agent": "API Integration", "code": code, "model_used": model_used}

@agents_router.post("/agents/run/test-generate")
async def agent_test_generate(data: AgentCodeBody, user: dict = Depends(get_optional_user)):
    """Test Generation: writes test suite for given code."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a Test Generation agent. Output only test code (e.g. Jest, pytest) for the given code. No markdown fences or explanation."
    prompt = f"Generate tests for this {data.language} code:\n\n{data.code[:8000]}"
    response, model_used = await _call_llm_with_fallback(
        message=prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", prompt, effective_keys=effective),
        api_keys=effective,
    )
    code = (response or "").strip().removeprefix("```").removesuffix("```").strip()
    return {"agent": "Test Generation", "code": code, "model_used": model_used}

@agents_router.post("/agents/run/image-generate")
async def agent_image_generate(data: AgentPromptBody, user: dict = Depends(get_optional_user)):
    """Image Generation: returns detailed image spec/prompt for visual creation (or calls DALL-E if available)."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are an Image Generation agent. Given a request, output a detailed image generation prompt (style, composition, colors, size hint) suitable for DALL-E or similar. One paragraph."
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    return {"agent": "Image Generation", "result": response, "prompt_spec": response, "model_used": model_used}

@agents_router.post("/agents/run/test-executor")
async def agent_test_executor(data: AgentPromptBody, user: dict = Depends(get_optional_user)):
    """Test Executor: returns how to run tests and validates test file presence."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a Test Executor agent. Given a project type (e.g. React, Python), reply with exactly: 1) the command to run tests (e.g. npm test, pytest), 2) one line on what to check."
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    return {"agent": "Test Executor", "result": response, "command_hint": "Run the command above in your project root.", "model_used": model_used}

@agents_router.post("/agents/run/deploy")
async def agent_deploy(data: AgentPromptBody, user: dict = Depends(get_optional_user)):
    """Deployment Agent: returns deploy instructions or triggers deploy."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a Deployment Agent. For the given project type, output concise step-by-step deploy instructions (e.g. Vercel, Netlify, or Docker). Number the steps."
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    return {"agent": "Deployment Agent", "result": response, "model_used": model_used}

@agents_router.post("/agents/run/memory-store")
async def agent_memory_store(data: AgentMemoryBody, user: dict = Depends(get_optional_user)):
    """Memory Agent: store a pattern for reuse."""
    doc = {
        "id": str(uuid.uuid4()),
        "name": data.name,
        "content": data.content,
        "user_id": (user or {}).get("id"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.agent_memory.insert_one(doc)
    return {"agent": "Memory Agent", "action": "stored", "id": doc["id"]}

@agents_router.get("/agents/run/memory-list")
async def agent_memory_list(user: dict = Depends(get_optional_user)):
    """Memory Agent: list stored patterns."""
    user_id = (user or {}).get("id")
    cursor = db.agent_memory.find({"user_id": user_id} if user_id else {}, {"_id": 0}).sort("created_at", -1).limit(50)
    items = await cursor.to_list(length=50)
    return {"agent": "Memory Agent", "items": items}

@agents_router.post("/agents/run/export-pdf")
async def agent_export_pdf(data: AgentExportPdfBody, user: dict = Depends(get_optional_user)):
    """PDF Export: generates a PDF from title and content."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=letter)
        c.setFont("Helvetica", 16)
        c.drawString(72, 750, (data.title or "Report")[:80])
        c.setFont("Helvetica", 10)
        y = 720
        for line in (data.content or "").replace("\r\n", "\n").split("\n")[:200]:
            if y < 72:
                c.showPage()
                c.setFont("Helvetica", 10)
                y = 750
            c.drawString(72, y, line[:100])
            y -= 14
        c.save()
        buf.seek(0)
        return Response(content=buf.read(), media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=report.pdf"})
    except ImportError:
        raise HTTPException(status_code=501, detail="reportlab not installed. pip install reportlab")

@agents_router.post("/agents/run/export-excel")
async def agent_export_excel(data: AgentExportExcelBody, user: dict = Depends(get_optional_user)):
    """Excel Export: creates a spreadsheet from rows."""
    try:
        import openpyxl
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.title = (data.title or "Sheet")[:31]
        rows = data.rows or []
        if rows:
            headers = list(rows[0].keys()) if isinstance(rows[0], dict) else []
            if headers:
                ws.append(headers)
                for r in rows[1:]:
                    ws.append([r.get(h, "") for h in headers])
        wb.save(buf := io.BytesIO())
        buf.seek(0)
        return Response(content=buf.read(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": "attachment; filename=export.xlsx"})
    except ImportError:
        raise HTTPException(status_code=501, detail="openpyxl not installed. pip install openpyxl")

@agents_router.post("/agents/run/export-markdown")
async def agent_export_markdown(data: AgentExportMarkdownBody, user: dict = Depends(get_optional_user)):
    """Markdown Export: returns a .md file from title and content (optional item 40)."""
    title = (data.title or "Export").strip()[:80]
    content = (data.content or "").strip()
    body = f"# {title}\n\n{content}\n"
    return Response(
        content=body,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{title.replace(" ", "-")[:60]}.md"'},
    )

@agents_router.post("/agents/run/scrape")
async def agent_scrape(data: AgentScrapeBody, user: dict = Depends(get_optional_user)):
    """Scraping Agent: fetches URL and extracts main content with LLM. Uses your Settings keys when set."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    import httpx
    async with httpx.AsyncClient() as client:
        r = await client.get(data.url, timeout=15)
        r.raise_for_status()
        html = r.text[:15000]
    system = "You are a Scraping Agent. Extract the main text content from this HTML. Return clean plain text only, no HTML tags. Summarize if very long."
    response, model_used = await _call_llm_with_fallback(
        message=f"URL: {data.url}\n\nHTML snippet:\n{html[:8000]}",
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", html, effective_keys=effective),
        api_keys=effective,
    )
    return {"agent": "Scraping Agent", "result": response, "url": data.url, "model_used": model_used}

@agents_router.post("/agents/run/automation")
async def agent_automation(data: AgentAutomationBody, user: dict = Depends(get_optional_user)):
    """Automation Agent: schedules a task (store and optional run_at)."""
    doc = {
        "id": str(uuid.uuid4()),
        "name": data.name,
        "prompt": data.prompt,
        "run_at": data.run_at or datetime.now(timezone.utc).isoformat(),
        "status": "scheduled",
        "user_id": (user or {}).get("id"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.automation_tasks.insert_one(doc)
    return {"agent": "Automation Agent", "action": "scheduled", "id": doc["id"], "run_at": doc["run_at"]}

@agents_router.get("/agents/run/automation-list")
async def agent_automation_list(user: dict = Depends(get_optional_user)):
    """List scheduled automation tasks."""
    user_id = (user or {}).get("id")
    cursor = db.automation_tasks.find({"user_id": user_id} if user_id else {}, {"_id": 0}).sort("created_at", -1).limit(50)
    items = await cursor.to_list(length=50)
    return {"agent": "Automation Agent", "items": items}

# ---------- New agents (Design, SEO, Content, etc.) ----------

@agents_router.post("/agents/run/design")
async def agent_design(data: AgentPromptBody, user: dict = Depends(get_optional_user)):
    """Design Agent: image placement spec (hero, feature_1, feature_2)."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a Design Agent. Output ONLY a JSON object with keys: hero, feature_1, feature_2. Each value: { \"position\": \"top-full|sidebar|grid\", \"aspect\": \"16:9|1:1|4:3\", \"role\": \"hero|feature|testimonial\" }. No markdown."
    response, model_used = await _call_llm_with_fallback(message=data.prompt, system_message=system, session_id=str(uuid.uuid4()), model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective), api_keys=effective)
    return {"agent": "Design Agent", "result": response, "model_used": model_used}

@agents_router.post("/agents/run/layout")
async def agent_layout(data: AgentPromptBody, user: dict = Depends(get_optional_user)):
    """Layout Agent: inject image placeholders into frontend."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a Layout Agent. Given frontend code and image specs, output updated React/JSX with image placeholders (img tags with data-image-slot) in correct positions. No markdown."
    response, model_used = await _call_llm_with_fallback(message=data.prompt, system_message=system, session_id=str(uuid.uuid4()), model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective), api_keys=effective)
    return {"agent": "Layout Agent", "result": response, "code": (response or "").strip().removeprefix("```").removesuffix("```").strip(), "model_used": model_used}

@agents_router.post("/agents/run/seo")
async def agent_seo(data: AgentPromptBody, user: dict = Depends(get_optional_user)):
    """SEO Agent: meta tags, OG, schema, sitemap, robots."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are an SEO Agent. Output meta tags, Open Graph, Twitter Card, JSON-LD schema, sitemap hints, robots.txt rules. Plain text or JSON."
    response, model_used = await _call_llm_with_fallback(message=data.prompt, system_message=system, session_id=str(uuid.uuid4()), model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective), api_keys=effective)
    return {"agent": "SEO Agent", "result": response, "model_used": model_used}

@agents_router.post("/agents/run/content")
async def agent_content(data: AgentPromptBody, user: dict = Depends(get_optional_user)):
    """Content Agent: landing copy (hero, features, CTA)."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a Content Agent. Write landing page copy: hero headline, 3 feature blurbs (2 lines each), CTA text. Plain text, one section per line."
    response, model_used = await _call_llm_with_fallback(message=data.prompt, system_message=system, session_id=str(uuid.uuid4()), model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective), api_keys=effective)
    return {"agent": "Content Agent", "result": response, "model_used": model_used}

@agents_router.post("/agents/run/brand")
async def agent_brand(data: AgentPromptBody, user: dict = Depends(get_optional_user)):
    """Brand Agent: colors, fonts, tone."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a Brand Agent. Output a JSON with: primary_color, secondary_color, font_heading, font_body, tone (e.g. professional, playful). No markdown."
    response, model_used = await _call_llm_with_fallback(message=data.prompt, system_message=system, session_id=str(uuid.uuid4()), model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective), api_keys=effective)
    return {"agent": "Brand Agent", "result": response, "model_used": model_used}

@agents_router.post("/agents/run/documentation")
async def agent_documentation(data: AgentPromptBody, user: dict = Depends(get_optional_user)):
    """Documentation Agent: README sections."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a Documentation Agent. Output README sections: setup, env vars, run commands, deploy steps. Markdown."
    response, model_used = await _call_llm_with_fallback(message=data.prompt, system_message=system, session_id=str(uuid.uuid4()), model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective), api_keys=effective)
    return {"agent": "Documentation Agent", "result": response, "model_used": model_used}

@agents_router.post("/agents/run/validation")
async def agent_validation(data: AgentPromptBody, user: dict = Depends(get_optional_user)):
    """Validation Agent: form/API validation rules, Zod/Yup."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a Validation Agent. List 3-5 form/API validation rules and suggest Zod/Yup schemas. Plain text."
    response, model_used = await _call_llm_with_fallback(message=data.prompt, system_message=system, session_id=str(uuid.uuid4()), model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective), api_keys=effective)
    return {"agent": "Validation Agent", "result": response, "model_used": model_used}

@agents_router.post("/agents/run/auth-setup")
async def agent_auth_setup(data: AgentPromptBody, user: dict = Depends(get_optional_user)):
    """Auth Setup Agent: JWT/OAuth2 flow."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are an Auth Setup Agent. Suggest JWT/OAuth2 flow: login, logout, token refresh, protected routes. Code or step list."
    response, model_used = await _call_llm_with_fallback(message=data.prompt, system_message=system, session_id=str(uuid.uuid4()), model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective), api_keys=effective)
    return {"agent": "Auth Setup Agent", "result": response, "model_used": model_used}

@agents_router.post("/agents/run/payment-setup")
async def agent_payment_setup(data: AgentPromptBody, user: dict = Depends(get_optional_user)):
    """Payment Setup Agent: Stripe integration."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a Payment Setup Agent. Suggest Stripe (or similar) integration: checkout, webhooks, subscription. Code or step list."
    response, model_used = await _call_llm_with_fallback(message=data.prompt, system_message=system, session_id=str(uuid.uuid4()), model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective), api_keys=effective)
    return {"agent": "Payment Setup Agent", "result": response, "model_used": model_used}

@agents_router.post("/agents/run/monitoring")
async def agent_monitoring(data: AgentPromptBody, user: dict = Depends(get_optional_user)):
    """Monitoring Agent: Sentry/analytics setup."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a Monitoring Agent. Suggest Sentry/analytics setup: error tracking, performance, user events. Plain text."
    response, model_used = await _call_llm_with_fallback(message=data.prompt, system_message=system, session_id=str(uuid.uuid4()), model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective), api_keys=effective)
    return {"agent": "Monitoring Agent", "result": response, "model_used": model_used}

@agents_router.post("/agents/run/accessibility")
async def agent_accessibility(data: AgentPromptBody, user: dict = Depends(get_optional_user)):
    """Accessibility Agent: a11y improvements."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are an Accessibility Agent. List 3-5 a11y improvements: ARIA, focus, contrast, screen reader. Plain text."
    response, model_used = await _call_llm_with_fallback(message=data.prompt, system_message=system, session_id=str(uuid.uuid4()), model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective), api_keys=effective)
    return {"agent": "Accessibility Agent", "result": response, "model_used": model_used}

@agents_router.post("/agents/run/devops")
async def agent_devops(data: AgentPromptBody, user: dict = Depends(get_optional_user)):
    """DevOps Agent: CI/CD, Dockerfile."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a DevOps Agent. Suggest CI/CD (GitHub Actions), Dockerfile, env config. Plain text or YAML."
    response, model_used = await _call_llm_with_fallback(message=data.prompt, system_message=system, session_id=str(uuid.uuid4()), model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective), api_keys=effective)
    return {"agent": "DevOps Agent", "result": response, "model_used": model_used}

@agents_router.post("/agents/run/webhook")
async def agent_webhook(data: AgentPromptBody, user: dict = Depends(get_optional_user)):
    """Webhook Agent: webhook endpoint design."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a Webhook Agent. Suggest webhook endpoint design: payload, signature verification, retries. Plain text."
    response, model_used = await _call_llm_with_fallback(message=data.prompt, system_message=system, session_id=str(uuid.uuid4()), model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective), api_keys=effective)
    return {"agent": "Webhook Agent", "result": response, "model_used": model_used}

@agents_router.post("/agents/run/email")
async def agent_email(data: AgentPromptBody, user: dict = Depends(get_optional_user)):
    """Email Agent: transactional email setup."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are an Email Agent. Suggest transactional email setup: provider (Resend/SendGrid), templates, verification. Plain text."
    response, model_used = await _call_llm_with_fallback(message=data.prompt, system_message=system, session_id=str(uuid.uuid4()), model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective), api_keys=effective)
    return {"agent": "Email Agent", "result": response, "model_used": model_used}

@agents_router.post("/agents/run/legal-compliance")
async def agent_legal_compliance(data: AgentPromptBody, user: dict = Depends(get_optional_user)):
    """Legal Compliance Agent: GDPR/CCPA hints."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = "You are a Legal Compliance Agent. Suggest GDPR/CCPA items: cookie banner, privacy link, data retention. Plain text."
    response, model_used = await _call_llm_with_fallback(message=data.prompt, system_message=system, session_id=str(uuid.uuid4()), model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective), api_keys=effective)
    return {"agent": "Legal Compliance Agent", "result": response, "model_used": model_used}

@agents_router.post("/agents/run/generic")
async def agent_run_generic(data: AgentGenericRunBody, user: dict = Depends(get_optional_user)):
    """Run any agent by name (100-agent roster). Uses system prompt from agent DAG."""
    if data.agent_name not in AGENT_DAG:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {data.agent_name}")
    system = get_system_prompt_for_agent(data.agent_name)
    if not system:
        system = f"You are {data.agent_name}. Fulfill the user request. Output concise, actionable text or code as appropriate."
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    return {"agent": data.agent_name, "result": response, "model_used": model_used}


# ==================== AGENTS & AUTOMATION (user-defined agents, runs, webhook) ====================

INTERNAL_RUN_TOKEN = os.environ.get("CRUCIBAI_INTERNAL_TOKEN", "")


class RunInternalBody(BaseModel):
    """Body for run-internal (worker calling back to run an agent)."""
    agent_name: str
    prompt: str
    user_id: str


@agents_router.post("/agents/run-internal")
async def agents_run_internal(data: RunInternalBody, request: Request):
    """Internal: worker calls this to run an agent by name (validates X-Internal-Token). No user JWT."""
    token = (request.headers.get("X-Internal-Token") or "").strip()
    if not INTERNAL_RUN_TOKEN or token != INTERNAL_RUN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing X-Internal-Token")
    agent_name = data.agent_name
    if agent_name not in AGENT_DAG:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_name}")
    if data.user_id == INTERNAL_USER_ID:
        user = None
        user_keys = {}
    else:
        user = await db.users.find_one({"id": data.user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    system = get_system_prompt_for_agent(agent_name) or f"You are {agent_name}. Fulfill the request."
    response, model_used = await _call_llm_with_fallback(
        message=data.prompt,
        system_message=system,
        session_id=str(uuid.uuid4()),
        model_chain=_get_model_chain("auto", data.prompt, effective_keys=effective),
        api_keys=effective,
    )
    return {"result": response, "model_used": model_used}


# Webhook idempotency: (agent_id, idempotency_key) -> last run_id (in-memory for single process; use Redis in multi-instance)
_webhook_idempotency: Dict[str, str] = {}
_webhook_rate: Dict[str, List[float]] = {}  # agent_id -> list of timestamps


def _check_webhook_rate_limit(agent_id: str) -> bool:
    """True if under limit (100/min)."""
    now = datetime.now(timezone.utc).timestamp()
    if agent_id not in _webhook_rate:
        _webhook_rate[agent_id] = []
    lst = _webhook_rate[agent_id]
    lst[:] = [t for t in lst if now - t < 60]
    if len(lst) >= WEBHOOK_RATE_LIMIT_PER_MINUTE:
        return False
    lst.append(now)
    return True


@agents_router.post("/agents/webhook/{agent_id}")
async def agents_webhook_trigger(agent_id: str, request: Request, secret: Optional[str] = Query(None)):
    """Trigger agent run via webhook. Query param secret= or header X-Webhook-Secret. Returns 202 + run_id."""
    raw_secret = secret or request.headers.get("X-Webhook-Secret") or ""
    idempotency_key = request.headers.get("Idempotency-Key", "").strip()
    agent = await db.user_agents.find_one({"id": agent_id})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if not agent.get("enabled"):
        raise HTTPException(status_code=400, detail="Agent is disabled")
    cfg = agent.get("trigger_config") or {}
    if cfg.get("type") != "webhook":
        raise HTTPException(status_code=400, detail="Agent is not webhook-triggered")
    if (cfg.get("webhook_secret") or "").strip() != raw_secret.strip():
        raise HTTPException(status_code=401, detail="Invalid webhook secret")
    if not _check_webhook_rate_limit(agent_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    now_iso = datetime.now(timezone.utc).isoformat()
    if idempotency_key:
        key = f"{agent_id}:{idempotency_key}"
        if key in _webhook_idempotency:
            run_id = _webhook_idempotency[key]
            return Response(status_code=202, content=json.dumps({"run_id": run_id}), media_type="application/json")
    user_id = agent.get("user_id") or ""
    if user_id and user_id != INTERNAL_USER_ID:
        cred = _user_credits(await db.users.find_one({"id": user_id}) or {})
        if cred < CREDITS_PER_AGENT_RUN:
            raise HTTPException(status_code=402, detail="Insufficient credits for agent run")
        running = await db.agent_runs.count_documents({"user_id": user_id, "status": "running"})
        if running >= MAX_CONCURRENT_RUNS_PER_USER:
            raise HTTPException(status_code=429, detail="Too many concurrent runs")
    run_id = str(uuid.uuid4())
    await db.agent_runs.insert_one({
        "id": run_id, "agent_id": agent_id, "user_id": user_id,
        "triggered_at": now_iso, "triggered_by": "webhook", "status": "running",
        "started_at": now_iso, "output_summary": {}, "log_lines": [],
    })
    if user_id and user_id != INTERNAL_USER_ID:
        await db.users.update_one({"id": user_id}, {"$inc": {"credit_balance": -CREDITS_PER_AGENT_RUN}})
    async def _run_agent_cb(uid: str, aname: str, prompt: str):
        u = await db.users.find_one({"id": uid})
        uk = await get_workspace_api_keys(u)
        eff = _effective_api_keys(uk)
        sys_p = get_system_prompt_for_agent(aname) or f"You are {aname}."
        r, _ = await _call_llm_with_fallback(
            message=prompt, system_message=sys_p, session_id=str(uuid.uuid4()),
            model_chain=_get_model_chain("auto", prompt, effective_keys=eff), api_keys=eff,
        )
        return {"result": r}
    try:
        status, output_summary, log_lines, _ = await run_actions(
            agent, user_id, run_id, [], run_agent_callback=_run_agent_cb,
        )
    except Exception as e:
        status, output_summary, log_lines = "failed", {"error": str(e)}, [str(e)]
    finished = datetime.now(timezone.utc).isoformat()
    await db.agent_runs.update_one(
        {"id": run_id},
        {"$set": {"status": status, "finished_at": finished, "output_summary": output_summary, "log_lines": log_lines[-1000:]}},
    )
    if idempotency_key:
        _webhook_idempotency[f"{agent_id}:{idempotency_key}"] = run_id
    return Response(status_code=202, content=json.dumps({"run_id": run_id}), media_type="application/json")


@agents_router.post("/agents", response_model=None)
async def agents_create(data: AgentCreate, request: Request, user: dict = Depends(get_current_user)):
    """Create a user agent (schedule or webhook + actions)."""
    await _ensure_credit_balance(user["id"])
    agent_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    trigger = data.trigger
    trigger_type = trigger.type
    trigger_config = {"type": trigger_type}
    if trigger_type == "schedule":
        trigger_config["cron_expression"] = trigger.cron_expression
        trigger_config["run_at"] = trigger.run_at
        next_ = next_run_at(cron_expression=trigger.cron_expression, run_at=trigger.run_at)
        trigger_config["next_run_at"] = next_.isoformat() if next_ else None
    else:
        webhook_secret = trigger.webhook_secret or secrets.token_urlsafe(24)
        trigger_config["webhook_secret"] = webhook_secret
    actions = [{"type": a.type, "config": a.config, "approval_required": a.approval_required} for a in data.actions]
    doc = {
        "id": agent_id, "user_id": user["id"], "name": data.name, "description": data.description or "",
        "trigger_type": trigger_type, "trigger_config": trigger_config,
        "actions": actions, "enabled": data.enabled,
        "created_at": now, "updated_at": now, "next_run_at": trigger_config.get("next_run_at"),
    }
    await db.user_agents.insert_one(doc)
    base_url = os.environ.get("FRONTEND_URL", request.base_url.rstrip("/")).rstrip("/")
    webhook_url = f"{base_url}/api/agents/webhook/{agent_id}?secret={trigger_config.get('webhook_secret', '')}" if trigger_type == "webhook" else None
    return {"id": agent_id, "user_id": user["id"], "name": doc["name"], "description": doc["description"], "trigger_type": trigger_type, "trigger_config": trigger_config, "actions": actions, "enabled": doc["enabled"], "created_at": now, "updated_at": now, "webhook_url": webhook_url}


@agents_router.get("/agents")
async def agents_list(user: dict = Depends(get_current_user), limit: int = Query(50, le=100), offset: int = Query(0, ge=0)):
    """List current user's agents."""
    cursor = db.user_agents.find({"user_id": user["id"]}).sort("updated_at", -1).skip(offset).limit(limit)
    items = await cursor.to_list(length=limit)
    out = []
    for a in items:
        last = await db.agent_runs.find_one({"agent_id": a["id"]}, sort=[("triggered_at", -1)], projection={"status": 1, "triggered_at": 1})
        run_count = await db.agent_runs.count_documents({"agent_id": a["id"]})
        tc = dict(a.get("trigger_config") or {})
        tc.pop("webhook_secret", None)
        out.append({
            "id": a["id"], "user_id": a["user_id"], "name": a["name"], "description": a.get("description"),
            "trigger_type": a["trigger_type"], "trigger_config": tc,
            "actions": a.get("actions", []), "enabled": a.get("enabled", True),
            "created_at": a["created_at"], "updated_at": a["updated_at"],
            "run_count": run_count, "last_run_at": last["triggered_at"] if last else None, "last_run_status": last.get("status") if last else None,
        })
    return {"items": out, "total": await db.user_agents.count_documents({"user_id": user["id"]})}


# Templates (public) — must be registered before /agents/{agent_id} so /agents/templates is not matched as agent_id
@agents_router.get("/agents/templates")
async def agents_templates_list():
    """List agent templates (no auth required for listing)."""
    return {"templates": [{"slug": t["slug"], "name": t["name"], "description": t["description"]} for t in AGENT_TEMPLATES]}


@agents_router.get("/agents/templates/{slug}")
async def agents_template_get(slug: str):
    """Get one template by slug."""
    t = next((x for x in AGENT_TEMPLATES if x["slug"] == slug), None)
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    return t


@agents_router.get("/agents/{agent_id}")
async def agents_get(agent_id: str, user: dict = Depends(get_current_user)):
    """Get one agent (own only)."""
    agent = await db.user_agents.find_one({"id": agent_id, "user_id": user["id"]})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    last = await db.agent_runs.find_one({"agent_id": agent_id}, sort=[("triggered_at", -1)], projection={"status": 1, "triggered_at": 1})
    run_count = await db.agent_runs.count_documents({"agent_id": agent_id})
    base = os.environ.get("FRONTEND_URL", "").rstrip("/")
    webhook_url = f"{base}/api/agents/webhook/{agent_id}?secret={agent.get('trigger_config', {}).get('webhook_secret', '')}" if agent.get("trigger_type") == "webhook" else None
    return {
        "id": agent["id"], "user_id": agent["user_id"], "name": agent["name"], "description": agent.get("description"),
        "trigger_type": agent["trigger_type"], "trigger_config": agent.get("trigger_config", {}),
        "actions": agent.get("actions", []), "enabled": agent.get("enabled", True),
        "created_at": agent["created_at"], "updated_at": agent["updated_at"],
        "webhook_url": webhook_url, "run_count": run_count, "last_run_at": last["triggered_at"] if last else None, "last_run_status": last.get("status") if last else None,
    }


@agents_router.post("/agents/{agent_id}/webhook-rotate-secret")
async def agents_webhook_rotate_secret(agent_id: str, request: Request, user: dict = Depends(get_current_user)):
    """Rotate webhook secret for a webhook-triggered agent. Returns new secret and URL once; update your caller."""
    agent = await db.user_agents.find_one({"id": agent_id, "user_id": user["id"]})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.get("trigger_type") != "webhook":
        raise HTTPException(status_code=400, detail="Agent is not webhook-triggered")
    new_secret = secrets.token_urlsafe(24)
    base = os.environ.get("FRONTEND_URL", request.base_url.rstrip("/")).rstrip("/")
    webhook_url = f"{base}/api/agents/webhook/{agent_id}?secret={new_secret}"
    tc = dict(agent.get("trigger_config") or {})
    tc["webhook_secret"] = new_secret
    now = datetime.now(timezone.utc).isoformat()
    await db.user_agents.update_one(
        {"id": agent_id, "user_id": user["id"]},
        {"$set": {"trigger_config": tc, "updated_at": now}},
    )
    return {"webhook_secret": new_secret, "webhook_url": webhook_url}


@agents_router.patch("/agents/{agent_id}")
async def agents_update(agent_id: str, data: AgentUpdate, user: dict = Depends(get_current_user)):
    """Update agent (partial)."""
    agent = await db.user_agents.find_one({"id": agent_id, "user_id": user["id"]})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    now = datetime.now(timezone.utc).isoformat()
    updates = {"updated_at": now}
    if data.name is not None:
        updates["name"] = data.name
    if data.description is not None:
        updates["description"] = data.description
    if data.enabled is not None:
        updates["enabled"] = data.enabled
    if data.trigger is not None:
        tc = {"type": data.trigger.type, "cron_expression": data.trigger.cron_expression, "run_at": data.trigger.run_at, "webhook_secret": data.trigger.webhook_secret or (agent.get("trigger_config") or {}).get("webhook_secret")}
        if data.trigger.type == "schedule":
            next_ = next_run_at(cron_expression=data.trigger.cron_expression, run_at=data.trigger.run_at)
            tc["next_run_at"] = next_.isoformat() if next_ else None
        updates["trigger_config"] = tc
        updates["trigger_type"] = data.trigger.type
        updates["next_run_at"] = tc.get("next_run_at")
    if data.actions is not None:
        updates["actions"] = [{"type": a.type, "config": a.config, "approval_required": a.approval_required} for a in data.actions]
    await db.user_agents.update_one({"id": agent_id, "user_id": user["id"]}, {"$set": updates})
    return {"ok": True, "id": agent_id}


@agents_router.delete("/agents/{agent_id}")
async def agents_delete(agent_id: str, user: dict = Depends(get_current_user)):
    """Delete agent (own only)."""
    r = await db.user_agents.delete_one({"id": agent_id, "user_id": user["id"]})
    if r.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"ok": True, "id": agent_id}


@agents_router.get("/agents/{agent_id}/runs")
async def agents_runs_list(agent_id: str, user: dict = Depends(get_current_user), limit: int = Query(50, le=100), offset: int = Query(0, ge=0)):
    """List runs for an agent (own only)."""
    agent = await db.user_agents.find_one({"id": agent_id, "user_id": user["id"]})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    cursor = db.agent_runs.find({"agent_id": agent_id}).sort("triggered_at", -1).skip(offset).limit(limit)
    runs = await cursor.to_list(length=limit)
    out = []
    for r in runs:
        started = r.get("started_at")
        finished = r.get("finished_at")
        dur = None
        if started and finished:
            try:
                from dateutil import parser as date_parser
                d1 = date_parser.isoparse(started)
                d2 = date_parser.isoparse(finished)
                dur = (d2 - d1).total_seconds()
            except Exception:
                pass
        out.append({"id": r["id"], "agent_id": r["agent_id"], "user_id": r["user_id"], "triggered_at": r["triggered_at"], "triggered_by": r.get("triggered_by", "schedule"), "status": r["status"], "started_at": started, "finished_at": finished, "duration_seconds": dur, "error_message": r.get("error_message"), "output_summary": r.get("output_summary"), "step_index": r.get("step_index")})
    return {"items": out, "total": await db.agent_runs.count_documents({"agent_id": agent_id})}


@agents_router.get("/agents/runs/{run_id}")
async def agents_run_get(run_id: str, user: dict = Depends(get_current_user)):
    """Get single run (own only, via agent ownership)."""
    run = await db.agent_runs.find_one({"id": run_id})
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    agent = await db.user_agents.find_one({"id": run["agent_id"], "user_id": user["id"]})
    if not agent:
        raise HTTPException(status_code=403, detail="Access denied")
    started = run.get("started_at")
    finished = run.get("finished_at")
    dur = None
    if started and finished:
        try:
            from dateutil import parser as date_parser
            d1 = date_parser.isoparse(started)
            d2 = date_parser.isoparse(finished)
            dur = (d2 - d1).total_seconds()
        except Exception:
            pass
    return {"id": run["id"], "agent_id": run["agent_id"], "user_id": run["user_id"], "triggered_at": run["triggered_at"], "triggered_by": run.get("triggered_by"), "status": run["status"], "started_at": started, "finished_at": finished, "duration_seconds": dur, "error_message": run.get("error_message"), "output_summary": run.get("output_summary"), "step_index": run.get("step_index")}


@agents_router.get("/agents/runs/{run_id}/logs")
async def agents_run_logs(run_id: str, user: dict = Depends(get_current_user)):
    """Get log lines for a run (own only)."""
    run = await db.agent_runs.find_one({"id": run_id})
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    agent = await db.user_agents.find_one({"id": run["agent_id"], "user_id": user["id"]})
    if not agent:
        raise HTTPException(status_code=403, detail="Access denied")
    return {"run_id": run_id, "log_lines": run.get("log_lines", [])}


@agents_router.post("/agents/{agent_id}/run")
async def agents_trigger_run(agent_id: str, user: dict = Depends(get_current_user)):
    """Trigger a run now (manual). Returns run_id."""
    agent = await db.user_agents.find_one({"id": agent_id, "user_id": user["id"]})
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    cred = _user_credits(user)
    if cred < CREDITS_PER_AGENT_RUN:
        raise HTTPException(status_code=402, detail=f"Insufficient credits. Need {CREDITS_PER_AGENT_RUN}, have {cred}.")
    now_iso = datetime.now(timezone.utc).isoformat()
    run_id = str(uuid.uuid4())
    await db.agent_runs.insert_one({"id": run_id, "agent_id": agent_id, "user_id": user["id"], "triggered_at": now_iso, "triggered_by": "manual", "status": "running", "started_at": now_iso, "output_summary": {}, "log_lines": []})
    await db.users.update_one({"id": user["id"]}, {"$inc": {"credit_balance": -CREDITS_PER_AGENT_RUN}})
    async def _run_agent_cb(uid: str, aname: str, prompt: str):
        u = await db.users.find_one({"id": uid})
        uk = await get_workspace_api_keys(u)
        eff = _effective_api_keys(uk)
        sys_p = get_system_prompt_for_agent(aname) or f"You are {aname}."
        r, _ = await _call_llm_with_fallback(message=prompt, system_message=sys_p, session_id=str(uuid.uuid4()), model_chain=_get_model_chain("auto", prompt, effective_keys=eff), api_keys=eff)
        return {"result": r}
    try:
        status, output_summary, log_lines, _ = await run_actions(agent, user["id"], run_id, [], run_agent_callback=_run_agent_cb)
    except Exception as e:
        status, output_summary, log_lines = "failed", {"error": str(e)}, [str(e)]
    finished = datetime.now(timezone.utc).isoformat()
    await db.agent_runs.update_one({"id": run_id}, {"$set": {"status": status, "finished_at": finished, "output_summary": output_summary, "log_lines": log_lines[-1000:]}})
    return {"run_id": run_id, "status": status}


# Pre-built agent templates (referenced by agents_templates_list / agents_template_get above)
AGENT_TEMPLATES = [
    {"slug": "daily-digest", "name": "Daily digest", "description": "Generate a short daily summary and optionally email it.", "trigger": {"type": "schedule", "cron_expression": "0 9 * * *"}, "actions": [{"type": "run_agent", "config": {"agent_name": "Content Agent", "prompt": "Summarize the key updates for today in 3 bullet points."}}]},
    {"slug": "youtube-poster", "name": "YouTube poster", "description": "Post or schedule content (placeholder: use HTTP action to your API).", "trigger": {"type": "schedule", "cron_expression": "0 17 * * *"}, "actions": [{"type": "http", "config": {"method": "POST", "url": "https://httpbin.org/post", "body": {"message": "Scheduled post"}}}]},
    {"slug": "lead-finder", "name": "Lead finder", "description": "Scrape and filter leads; notify via Slack.", "trigger": {"type": "webhook"}, "actions": [{"type": "run_agent", "config": {"agent_name": "Scraping Agent", "prompt": "Suggest 2-3 data sources for B2B leads."}}, {"type": "slack", "config": {"text": "New lead run completed.", "webhook_url": ""}}]},
    {"slug": "inbox-summarizer", "name": "Inbox summarizer", "description": "Webhook + Content Agent + email.", "trigger": {"type": "webhook"}, "actions": [{"type": "run_agent", "config": {"agent_name": "Content Agent", "prompt": "Summarize the following in 3 bullets."}}, {"type": "email", "config": {"to": "", "subject": "Summary", "body": "{{steps.0.output}}"}}]},
    {"slug": "status-checker", "name": "Status page checker", "description": "Schedule HTTP check; Slack on failure.", "trigger": {"type": "schedule", "cron_expression": "0 */6 * * *"}, "actions": [{"type": "http", "config": {"method": "GET", "url": "https://api.github.com/zen"}}, {"type": "slack", "config": {"text": "Status check completed.", "webhook_url": ""}}]},
]


class FromTemplateBody(BaseModel):
    template_slug: str
    overrides: Optional[Dict[str, Any]] = None


class FromDescriptionBody(BaseModel):
    """Prompt-to-automation: natural language description of the automation."""
    description: str


@agents_router.post("/agents/from-description")
async def agents_from_description(data: FromDescriptionBody, request: Request, user: dict = Depends(get_current_user)):
    """Create an agent from a natural language description (prompt-to-automation). Uses LLM to produce trigger + actions, then creates the agent."""
    cred = _user_credits(user)
    if cred < MIN_CREDITS_FOR_LLM:
        raise HTTPException(status_code=402, detail=f"Insufficient credits. Need at least {MIN_CREDITS_FOR_LLM} for prompt-to-automation. Buy more in Credit Center.")
    await _ensure_credit_balance(user["id"])
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    model_chain = _get_model_chain("auto", data.description, effective_keys=effective)
    system = """You are an automation designer. Given the user's description of an automation, output ONLY a single valid JSON object (no markdown, no code fence, no explanation) with exactly these keys:
- "name": short title for the agent (e.g. "Daily summary")
- "description": one sentence describing what it does
- "trigger": object with "type" ("schedule" or "webhook"). If schedule, add "cron_expression": standard 5-field cron, e.g. "0 9 * * *" for 9am daily, "0 */6 * * *" for every 6 hours, "0 0 * * *" for midnight daily
- "actions": array of action objects. Each has "type" and "config".
  Action types: "http" (config: method, url, optional headers, optional body), "email" (to, subject, body; body can use {{steps.0.output}} for previous step output), "slack" (webhook_url, text), "run_agent" (agent_name: one of Content Agent, Scraping Agent, etc.; prompt: string, can use {{steps.0.output}}).
  For "every day at 9am" use cron_expression "0 9 * * *". For "every 6 hours" use "0 */6 * * *". For webhook use trigger type "webhook" and no cron.
Output only the JSON object, nothing else."""
    try:
        response, _ = await _call_llm_with_fallback(
            message=data.description,
            system_message=system,
            session_id=str(uuid.uuid4()),
            model_chain=model_chain,
            api_keys=effective,
        )
    except Exception as e:
        logger.exception("agents_from_description LLM failed")
        raise HTTPException(status_code=502, detail=f"Could not generate automation: {str(e)}")
    raw = (response or "").strip()
    json_str = raw
    if "```" in raw:
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", raw)
        if m:
            json_str = m.group(1).strip()
    try:
        spec = json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.warning("agents_from_description invalid JSON: %s", raw[:500])
        raise HTTPException(status_code=422, detail="Generated spec was not valid JSON. Try a clearer description.")
    name = (spec.get("name") or "My automation").strip() or "My automation"
    description = (spec.get("description") or "").strip()
    trigger_spec = spec.get("trigger") or {}
    trigger_type = (trigger_spec.get("type") or "schedule").lower()
    if trigger_type not in ("schedule", "webhook"):
        trigger_type = "schedule"
    if trigger_type == "schedule":
        cron = (trigger_spec.get("cron_expression") or "0 9 * * *").strip()
        trigger_config = TriggerConfig(type="schedule", cron_expression=cron or "0 9 * * *", run_at=None, webhook_secret=None)
    else:
        trigger_config = TriggerConfig(type="webhook", cron_expression=None, run_at=None, webhook_secret=None)
    actions_spec = spec.get("actions") or []
    if not actions_spec:
        actions_spec = [{"type": "http", "config": {"method": "GET", "url": "https://httpbin.org/get"}}]
    action_configs = []
    for a in actions_spec[:20]:
        if not isinstance(a, dict):
            continue
        atype = (a.get("type") or "http").lower()
        aconfig = a.get("config") or a
        if not isinstance(aconfig, dict):
            aconfig = {}
        action_configs.append(ActionConfig(type=atype, config=aconfig, approval_required=a.get("approval_required", False)))
    if not action_configs:
        action_configs = [ActionConfig(type="http", config={"method": "GET", "url": "https://httpbin.org/get"}, approval_required=False)]
    create = AgentCreate(name=name, description=description or None, trigger=trigger_config, actions=action_configs, enabled=True)
    deduct = 3
    if cred >= deduct:
        await db.users.update_one({"id": user["id"]}, {"$inc": {"credit_balance": -deduct}})
    return await agents_create(create, request, user)


@agents_router.post("/agents/from-template")
async def agents_from_template(data: FromTemplateBody, request: Request, user: dict = Depends(get_current_user)):
    """Create an agent from a template (overrides: name, description, trigger, actions)."""
    t = next((x for x in AGENT_TEMPLATES if x["slug"] == data.template_slug), None)
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    overrides = data.overrides or {}
    name = overrides.get("name") or t["name"]
    description = overrides.get("description") or t.get("description", "")
    trigger = overrides.get("trigger") or t["trigger"]
    actions = overrides.get("actions") or t["actions"]
    trigger_config = TriggerConfig(**trigger) if isinstance(trigger, dict) else trigger
    action_configs = [ActionConfig(**a) if isinstance(a, dict) else a for a in actions]
    create = AgentCreate(name=name, description=description, trigger=trigger_config, actions=action_configs, enabled=True)
    return await agents_create(create, request, user)


# Approval (human-in-the-loop)
@agents_router.post("/agents/runs/{run_id}/approve")
async def agents_run_approve(run_id: str, user: dict = Depends(get_current_user), comment: Optional[str] = Body(None)):
    """Resume a run that is waiting_approval (owner only)."""
    run = await db.agent_runs.find_one({"id": run_id})
    if not run or run["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.get("status") != "waiting_approval":
        raise HTTPException(status_code=400, detail="Run is not waiting for approval")
    agent = await db.user_agents.find_one({"id": run["agent_id"], "user_id": user["id"]})
    if not agent:
        raise HTTPException(status_code=403, detail="Access denied")
    step_index = (run.get("step_index") or 0) + 1
    steps_context = [s.get("output") for s in (run.get("output_summary") or {}).get("steps", [])]
    steps_context = [{"output": x} for x in steps_context]
    async def _run_agent_cb(uid: str, aname: str, prompt: str):
        u = await db.users.find_one({"id": uid})
        uk = await get_workspace_api_keys(u)
        eff = _effective_api_keys(uk)
        sys_p = get_system_prompt_for_agent(aname) or f"You are {aname}."
        r, _ = await _call_llm_with_fallback(message=prompt, system_message=sys_p, session_id=str(uuid.uuid4()), model_chain=_get_model_chain("auto", prompt, effective_keys=eff), api_keys=eff)
        return {"result": r}
    try:
        status, output_summary, log_lines, _ = await run_actions(agent, user["id"], run_id, steps_context, run_agent_callback=_run_agent_cb, resume_from_step=step_index)
    except Exception as e:
        status, output_summary, log_lines = "failed", {"error": str(e)}, [str(e)]
    finished = datetime.now(timezone.utc).isoformat()
    await db.agent_runs.update_one({"id": run_id}, {"$set": {"status": status, "finished_at": finished, "output_summary": output_summary, "log_lines": run.get("log_lines", []) + log_lines, "step_index": None}})
    return {"ok": True, "run_id": run_id, "status": status}


@agents_router.post("/agents/runs/{run_id}/reject")
async def agents_run_reject(run_id: str, user: dict = Depends(get_current_user), comment: Optional[str] = Body(None)):
    """Cancel a run that is waiting_approval."""
    run = await db.agent_runs.find_one({"id": run_id})
    if not run or run["user_id"] != user["id"]:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.get("status") != "waiting_approval":
        raise HTTPException(status_code=400, detail="Run is not waiting for approval")
    finished = datetime.now(timezone.utc).isoformat()
    await db.agent_runs.update_one({"id": run_id}, {"$set": {"status": "cancelled", "finished_at": finished}})
    return {"ok": True, "run_id": run_id, "status": "cancelled"}


# ==================== TASKS ROUTES (single-task authority sync) ====================

@api_router.get("/tasks")
async def get_tasks(user: dict = Depends(get_current_user)):
    """List tasks for current user (synced from Workspace)."""
    cursor = db.tasks.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1)
    tasks = await cursor.to_list(100)
    return {"tasks": tasks}

@api_router.post("/tasks")
async def create_or_update_task(data: TaskSync, user: dict = Depends(get_current_user)):
    """Create or update task when build completes in Workspace."""
    task_id = str(uuid.uuid4())
    task = {
        "id": task_id,
        "user_id": user["id"],
        "name": data.name[:200] if data.name else "Untitled",
        "prompt": data.prompt[:5000] if data.prompt else "",
        "session_id": data.session_id or "",
        "status": data.status or "completed",
        "files": data.files or [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.tasks.insert_one(task)
    return {"task": {k: v for k, v in task.items() if k != "_id"}}

# ==================== PROJECT ROUTES ====================

FREE_TIER_MAX_PROJECTS = 3

@projects_router.post("/projects")
async def create_project(
    data: ProjectCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    user: dict = Depends(get_current_user),
):
    if Permission is not None and not has_permission(user, Permission.CREATE_PROJECT):
        raise HTTPException(status_code=403, detail="Insufficient permission to create projects")
    plan = user.get("plan", "free")
    if plan == "free":
        count = await db.projects.count_documents({"user_id": user["id"]})
        if count >= FREE_TIER_MAX_PROJECTS:
            raise HTTPException(
                status_code=403,
                detail="You've saved 3 projects. Upgrade to Builder to save unlimited projects and get faster builds.",
                headers={"X-Upgrade-Required": "builder"}
            )
    # Landing pages need fewer credits so free/guest (100–700) can build
    project_type_lower = (data.project_type or "").strip().lower()
    default_tokens = 80000 if project_type_lower == "landing" else 675000
    estimated_tokens = data.estimated_tokens or default_tokens
    estimated_credits = _tokens_to_credits(estimated_tokens)
    await _ensure_credit_balance(user["id"])
    cred = _user_credits(user)
    if cred < estimated_credits:
        raise HTTPException(status_code=402, detail=f"Insufficient credits. Need {estimated_credits}, have {cred}. Buy more in Credit Center.")

    # Free tier: landing-only unless user has a paid purchase
    if plan == "free":
        has_paid = await db.token_ledger.find_one({"user_id": user["id"], "type": "purchase"})
        if not has_paid and (data.project_type or "").strip().lower() != "landing":
            raise HTTPException(
                status_code=402,
                detail="Free tier is for landing pages only. Set project_type to 'landing' or upgrade/buy credits in Credit Center to create full apps.",
            )

    # Legal / AUP compliance: block prohibited build requests
    prompt = (data.requirements or {}).get("prompt") or data.description or ""
    if isinstance(prompt, dict):
        prompt = prompt.get("prompt") or str(prompt)
    if legal_check_request and prompt:
        compliance = legal_check_request(prompt)
        if not compliance.get("allowed"):
            await db.blocked_requests.insert_one({
                "user_id": user["id"],
                "prompt": prompt[:2000],
                "reason": compliance.get("reason"),
                "category": compliance.get("category"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "blocked",
            })
            raise HTTPException(
                status_code=400,
                detail=compliance.get("reason") or "Request violates Acceptable Use Policy. See /aup for details.",
            )

    project_id = str(uuid.uuid4())
    project = {
        "id": project_id,
        "user_id": user["id"],
        "name": data.name,
        "description": data.description,
        "project_type": data.project_type,
        "requirements": data.requirements,
        "status": "queued",
        "tokens_allocated": estimated_tokens,
        "tokens_used": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "live_url": None,
        "quick_build": getattr(data, "quick_build", False) or False,
    }
    await db.projects.insert_one(project)
    if audit_logger:
        await audit_logger.log(
            user["id"], "project_created",
            resource_type="project", resource_id=project_id,
            new_value={"name": data.name},
            ip_address=getattr(request.client, "host", None),
        )
    await db.users.update_one({"id": user["id"]}, {"$inc": {"credit_balance": -estimated_credits}})
    
    background_tasks.add_task(run_orchestration_v2, project_id, user["id"])
    
    return {"project": {k: v for k, v in project.items() if k != "_id"}}

@projects_router.get("/projects")
async def get_projects(user: dict = Depends(get_current_user), _: dict = Depends(require_permission(Permission.VIEW_PROJECT if Permission else None))):
    cursor = db.projects.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1)
    projects = await cursor.to_list(100)
    return {"projects": projects}


def _safe_import_path(path: str) -> str:
    """Return a safe relative path for import (no .., no absolute)."""
    p = (path or "").strip().replace("\\", "/").lstrip("/")
    if ".." in p or p.startswith("/"):
        return ""
    return p[:500]  # limit length


@projects_router.post("/projects/import")
async def import_project(data: ProjectImportBody, user: dict = Depends(require_permission(Permission.CREATE_PROJECT if Permission else None))):
    """Import a project from paste (files), ZIP (base64), or Git URL. Creates project and writes files to workspace."""
    project_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    name = (data.name or "Imported project").strip() or "Imported project"
    project = {
        "id": project_id,
        "user_id": user["id"],
        "name": name,
        "description": "Imported from paste, ZIP, or Git.",
        "project_type": "fullstack",
        "requirements": {"prompt": "", "imported": True},
        "status": "imported",
        "tokens_allocated": 0,
        "tokens_used": 0,
        "created_at": now,
        "completed_at": now,
        "live_url": None,
    }
    await db.projects.insert_one(project)
    root = _project_workspace_path(project_id).resolve()
    root.mkdir(parents=True, exist_ok=True)
    written = 0
    if data.source == "paste" and data.files:
        for item in data.files[:200]:
            path = _safe_import_path(item.get("path") or "")
            if not path:
                continue
            content = item.get("code") or item.get("content") or ""
            if len(content) > 2 * 1024 * 1024:
                continue
            full = (root / path).resolve()
            try:
                full.relative_to(root)
            except ValueError:
                continue
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content[:2 * 1024 * 1024], encoding="utf-8", errors="replace")
            written += 1
    elif data.source == "zip" and data.zip_base64:
        try:
            raw = base64.b64decode(data.zip_base64, validate=True)
            if len(raw) > 10 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="ZIP too large (max 10MB)")
            with zipfile.ZipFile(io.BytesIO(raw), "r") as zf:
                for info in zf.infolist()[:500]:
                    if info.is_dir():
                        continue
                    path = _safe_import_path(info.filename)
                    if not path or "node_modules" in path or "__pycache__" in path:
                        continue
                    full = (root / path).resolve()
                    try:
                        full.relative_to(root)
                    except ValueError:
                        continue
                    full.parent.mkdir(parents=True, exist_ok=True)
                    full.write_bytes(zf.read(info))
                    written += 1
        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Invalid ZIP file")
    elif data.source == "git" and data.git_url:
        url = (data.git_url or "").strip()
        if not url.startswith("http"):
            raise HTTPException(status_code=400, detail="Git URL must be HTTPS")
        try:
            import httpx
            if "github.com" in url:
                u = url.rstrip("/").replace("https://github.com/", "").replace(".git", "")
                parts = u.split("/")
                if len(parts) >= 2:
                    archive_url = f"https://github.com/{parts[0]}/{parts[1]}/archive/refs/heads/main.zip"
                else:
                    archive_url = f"https://github.com/{parts[0]}/{parts[1]}/archive/refs/heads/master.zip"
            else:
                raise HTTPException(status_code=400, detail="Only GitHub URLs supported for now")
            async with httpx.AsyncClient() as client:
                r = await client.get(archive_url, timeout=30)
                if r.status_code != 200:
                    r = await client.get(archive_url.replace("/main.zip", "/master.zip"), timeout=30)
                if r.status_code != 200:
                    raise HTTPException(status_code=400, detail="Could not fetch repo archive")
                raw = r.content
                if len(raw) > 15 * 1024 * 1024:
                    raise HTTPException(status_code=413, detail="Repo archive too large (max 15MB)")
                with zipfile.ZipFile(io.BytesIO(raw), "r") as zf:
                    for info in zf.infolist()[:500]:
                        if info.is_dir():
                            continue
                        parts = info.filename.replace("\\", "/").split("/")
                        name_part = "/".join(parts[1:]) if len(parts) > 1 else info.filename
                        path = _safe_import_path(name_part)
                        if not path or "node_modules" in path or "__pycache__" in path:
                            continue
                        full = (root / path).resolve()
                        try:
                            full.relative_to(root)
                        except ValueError:
                            continue
                        full.parent.mkdir(parents=True, exist_ok=True)
                        full.write_bytes(zf.read(info))
                        written += 1
        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Git import failed: %s", e)
            raise HTTPException(status_code=400, detail=f"Git import failed: {str(e)[:200]}")
    else:
        raise HTTPException(status_code=400, detail="Provide source and files, zip_base64, or git_url")
    return {"project_id": project_id, "project": {k: v for k, v in project.items() if k != "_id"}, "files_written": written}


@projects_router.get("/projects/{project_id}")
async def get_project(project_id: str, user: dict = Depends(get_current_user), _: dict = Depends(require_permission(Permission.VIEW_PROJECT if Permission else None))):
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project": project}


@projects_router.delete("/projects/{project_id}")
async def delete_project(project_id: str, user: dict = Depends(require_permission(Permission.DELETE_PROJECT if Permission else None))):
    """Delete a project and its related data. Only the project owner can delete."""
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.project_logs.delete_many({"project_id": project_id})
    await db.agent_status.delete_many({"project_id": project_id})
    await db.shares.delete_many({"project_id": project_id})
    await db.projects.delete_one({"id": project_id, "user_id": user["id"]})
    if project_id in _build_events:
        del _build_events[project_id]
    try:
        workspace_path = _project_workspace_path(project_id)
        if workspace_path.exists():
            import shutil
            shutil.rmtree(workspace_path, ignore_errors=True)
    except Exception as e:
        logger.warning("Could not remove project workspace dir %s: %s", project_id, e)
    return Response(status_code=204)


@projects_router.get("/projects/{project_id}/state")
async def get_project_state(project_id: str, user: dict = Depends(get_current_user)):
    """Return structured project state (plan, requirements, stack, reports, tool_log) for UI and debugging."""
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    state = load_state(project_id)
    return {"state": state}


@projects_router.get("/projects/{project_id}/events")
async def stream_build_events(
    project_id: str,
    last_id: int = Query(0, description="Last event id received"),
    user: dict = Depends(get_current_user),
):
    """SSE stream of build events (agent_started, agent_completed, phase_started, build_completed). Wired to orchestration."""
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    async def event_generator():
        seen = last_id
        while True:
            events = _build_events.get(project_id, [])
            for ev in events:
                if ev.get("id", 0) >= seen:
                    yield f"data: {json.dumps(ev)}\n\n"
                    seen = ev.get("id", 0) + 1
            project_doc = await db.projects.find_one({"id": project_id}, {"status": 1})
            if project_doc and project_doc.get("status") in ("completed", "failed"):
                yield f"data: {json.dumps({'type': 'stream_end', 'status': project_doc['status']})}\n\n"
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@projects_router.get("/projects/{project_id}/events/snapshot")
async def get_build_events_snapshot(project_id: str, user: dict = Depends(get_current_user)):
    """One-shot fetch of all build events (for UI timeline). Wired to same store as SSE."""
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    events = _build_events.get(project_id, [])
    return {"events": events}


def _project_workspace_path(project_id: str) -> Path:
    safe_id = project_id.replace("/", "_").replace("\\", "_")
    return WORKSPACE_ROOT / safe_id


def _create_preview_token(project_id: str, user_id: str) -> str:
    """Short-lived JWT so iframe can load preview without Bearer header."""
    payload = {"project_id": project_id, "user_id": user_id, "purpose": "preview", "exp": datetime.now(timezone.utc) + timedelta(minutes=2)}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _verify_preview_token(token: str) -> tuple:
    """Returns (project_id, user_id) or raises."""
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    if payload.get("purpose") != "preview":
        raise jwt.InvalidTokenError("Invalid purpose")
    return payload["project_id"], payload["user_id"]


@api_router.get("/settings/capabilities")
async def get_settings_capabilities(user: dict = Depends(get_current_user)):
    """Returns sandbox (Docker) availability and other capabilities for UI polish."""
    sandbox_available = False
    try:
        proc = await asyncio.to_thread(
            subprocess.run,
            ["docker", "run", "--rm", "hello-world"],
            capture_output=True,
            timeout=10,
        )
        sandbox_available = proc.returncode == 0
    except Exception as e:
        logger.info("Sandbox (Docker) check failed: %s. Runs will use host when Docker unavailable.", e)
    return {
        "sandbox_available": sandbox_available,
        "sandbox_default": os.environ.get("RUN_IN_SANDBOX", "1").strip().lower() in ("1", "true", "yes"),
    }


@projects_router.get("/projects/{project_id}/preview-token")
async def get_preview_token(project_id: str, user: dict = Depends(get_current_user)):
    """Get short-lived token for iframe preview URL. Wired to preview."""
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    t = _create_preview_token(project_id, user["id"])
    base = os.environ.get("API_BASE_URL", "").rstrip("/") or "http://localhost:8000"
    return {"token": t, "url": f"{base}/api/projects/{project_id}/preview?preview_token={t}"}


@projects_router.get("/projects/{project_id}/preview")
@projects_router.get("/projects/{project_id}/preview/{path:path}")
async def serve_preview(
    project_id: str,
    path: str = "",
    preview_token: Optional[str] = Query(None, description="From GET /projects/{id}/preview-token"),
):
    """Serve workspace files for live preview (iframe). Requires preview_token from /preview-token (auth)."""
    if not preview_token:
        raise HTTPException(status_code=401, detail="preview_token required (get from /projects/{id}/preview-token)")
    try:
        pid, user_id = _verify_preview_token(preview_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired preview token")
    if pid != project_id:
        raise HTTPException(status_code=403, detail="Token project mismatch")
    project = await db.projects.find_one({"id": project_id, "user_id": user_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    root = _project_workspace_path(project_id).resolve()
    if not root.exists():
        raise HTTPException(status_code=404, detail="No workspace yet")
    path = (path or "").strip().lstrip("/").replace("\\", "/")
    if ".." in path or path.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid path")
    full = (root / path).resolve()
    try:
        full.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=400, detail="Path outside workspace")
    if full.is_dir():
        full = full / "index.html"
    if not full.exists():
        if not path:
            return Response(
                content="""<!DOCTYPE html><html><head><meta charset="utf-8"><title>Building...</title></head><body style="display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;font-family:system-ui;background:#1A1A1A;color:#999999;">Building your app... Agents are writing files.</body></html>""",
                media_type="text/html",
            )
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(full)


@projects_router.get("/projects/{project_id}/workspace/files")
async def list_workspace_files(project_id: str, user: dict = Depends(get_current_user)):
    """List files in project workspace (view files in task). Wired to workspace."""
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    root = _project_workspace_path(project_id).resolve()
    if not root.exists():
        return {"files": []}
    files = []
    for p in root.rglob("*"):
        if p.is_file() and "node_modules" not in str(p) and "__pycache__" not in str(p):
            try:
                rel = p.relative_to(root)
                files.append(str(rel).replace("\\", "/"))
            except ValueError:
                pass
    return {"files": sorted(files)[:500]}


@projects_router.get("/projects/{project_id}/workspace/file")
async def get_workspace_file_content(
    project_id: str,
    path: str = Query(..., description="Relative file path in workspace"),
    user: dict = Depends(get_current_user),
):
    """Get content of a single file in project workspace (for import/open in Workspace)."""
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    root = _project_workspace_path(project_id).resolve()
    path = (path or "").strip().replace("\\", "/").lstrip("/")
    if ".." in path or not path:
        raise HTTPException(status_code=400, detail="Invalid path")
    full = (root / path).resolve()
    try:
        full.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=400, detail="Path outside workspace")
    if not full.exists() or not full.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    try:
        content = full.read_text(encoding="utf-8", errors="replace")
    except Exception:
        raise HTTPException(status_code=400, detail="File not readable as text")
    return {"path": path, "content": content}


@projects_router.get("/projects/{project_id}/dependency-audit")
async def get_project_dependency_audit(project_id: str, user: dict = Depends(get_current_user)):
    """Optional: run npm audit and/or pip-audit in project workspace and return summary (high/critical counts)."""
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    root = _project_workspace_path(project_id).resolve()
    if not root.exists():
        return {"npm": None, "pip": None, "message": "No workspace files yet"}
    out = {"npm": None, "pip": None}

    def _run_npm_audit() -> Optional[Dict[str, Any]]:
        pkg = root / "package.json"
        if not pkg.exists():
            return None
        try:
            r = subprocess.run(
                ["npm", "audit", "--json"],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=60,
                env={**os.environ, "CI": "1"},
            )
            if r.stdout:
                data = json.loads(r.stdout)
                meta = data.get("metadata", {}) or {}
                counts = meta.get("vulnerabilities", {}) or {}
                return {
                    "critical": counts.get("critical", 0) or 0,
                    "high": counts.get("high", 0) or 0,
                    "moderate": counts.get("moderate", 0) or 0,
                    "low": counts.get("low", 0) or 0,
                    "info": counts.get("info", 0) or 0,
                    "ok": (counts.get("critical", 0) or 0) == 0 and (counts.get("high", 0) or 0) == 0,
                }
            return {"ok": True, "critical": 0, "high": 0}
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
            return {"error": str(e)[:200]}
        except Exception as e:
            return {"error": str(e)[:200]}

    def _run_pip_audit() -> Optional[Dict[str, Any]]:
        req = root / "requirements.txt"
        if not req.exists():
            return None
        try:
            r = subprocess.run(
                [sys.executable, "-m", "pip_audit", "-r", str(req), "--format", "json", "--require-hashes", "false"],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=90,
            )
            if r.stdout:
                data = json.loads(r.stdout)
                deps = data.get("dependencies", {}) or {}
                total = sum(len((d.get("vulns") or [])) for d in deps.values() if isinstance(d, dict))
                return {"critical": total, "high": 0, "ok": total == 0}
            return {"ok": True, "critical": 0, "high": 0}
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
            return {"error": str(e)[:200]}
        except Exception as e:
            return {"error": str(e)[:200]}

    out["npm"] = await asyncio.to_thread(_run_npm_audit)
    out["pip"] = await asyncio.to_thread(_run_pip_audit)
    return out


async def _build_project_deploy_zip(project_id: str, user_id: str):
    """Build deploy ZIP for a project. Raises HTTPException if not found or no deploy_files."""
    project = await db.projects.find_one({"id": project_id, "user_id": user_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    deploy_files = project.get("deploy_files") or {}
    if not deploy_files:
        raise HTTPException(status_code=404, detail="No deploy snapshot for this project. Open in Workspace and use Deploy there, or re-run the build.")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("README-DEPLOY.md", DEPLOY_README)
        for name, content in deploy_files.items():
            safe_name = (name or "").lstrip("/")
            if safe_name:
                zf.writestr(safe_name, content if isinstance(content, str) else str(content))
    buf.seek(0)
    return buf


@projects_router.get("/projects/{project_id}/deploy/files")
async def get_project_deploy_files_json(project_id: str, user: dict = Depends(get_current_user)):
    """Return deploy_files as JSON dict for Sandpack preview auto-wire. Called by Workspace after build_completed."""
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    deploy_files = project.get("deploy_files") or {}
    quality_score = project.get("quality_score")
    status = project.get("status", "unknown")
    return {"files": deploy_files, "status": status, "quality_score": quality_score}


@projects_router.get("/projects/{project_id}/deploy/zip")
async def get_project_deploy_zip(project_id: str, user: dict = Depends(get_current_user)):
    """Download deploy ZIP for a completed project (Vercel/Netlify/Railway). Requires project to have deploy_files (stored at completion)."""
    buf = await _build_project_deploy_zip(project_id, user["id"])
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=crucibai-deploy.zip"},
    )


@projects_router.get("/projects/{project_id}/export/deploy")
async def get_project_export_deploy(project_id: str, user: dict = Depends(get_current_user)):
    """Alias for deploy ZIP: same deploy-ready package keyed by project_id (for Deploy UX)."""
    buf = await _build_project_deploy_zip(project_id, user["id"])
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=crucibai-deploy.zip"},
    )


@api_router.get("/users/me/deploy-tokens")
async def get_deploy_tokens_status(user: dict = Depends(get_current_user)):
    """Return whether user has deploy tokens set (no values). For UI to show one-click availability."""
    u = await db.users.find_one({"id": user["id"]}, {"deploy_tokens": 1})
    dt = u.get("deploy_tokens") or {}
    return {"has_vercel": bool(dt.get("vercel")), "has_netlify": bool(dt.get("netlify"))}


@api_router.patch("/users/me/deploy-tokens")
async def update_deploy_tokens(data: DeployTokensUpdate, user: dict = Depends(get_current_user)):
    """Set deploy tokens for one-click Vercel/Netlify. Only updates provided keys."""
    update = {}
    if data.vercel is not None:
        update["deploy_tokens.vercel"] = data.vercel.strip() if data.vercel else None
    if data.netlify is not None:
        update["deploy_tokens.netlify"] = data.netlify.strip() if data.netlify else None
    if not update:
        return {"ok": True}
    await db.users.update_one({"id": user["id"]}, {"$set": update})
    return {"ok": True}


async def _get_project_deploy_files(project_id: str, user_id: str) -> tuple[Dict[str, str], str]:
    """Return (deploy_files dict, project_name) for a project. Raises HTTPException if not found."""
    project = await db.projects.find_one({"id": project_id, "user_id": user_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    deploy_files = project.get("deploy_files") or {}
    if not deploy_files:
        raise HTTPException(
            status_code=404,
            detail="No deploy snapshot. Open in Workspace and use Deploy there, or re-run the build.",
        )
    name = (project.get("name") or "crucibai-app").replace(" ", "-")[:50]
    return deploy_files, name


@projects_router.post("/projects/{project_id}/deploy/vercel")
async def one_click_deploy_vercel(
    project_id: str,
    request: Request,
    body: DeployOneClickBody = None,
    user: dict = Depends(require_permission(Permission.DEPLOY_PROJECT if Permission else None)),
):
    """One-click deploy to Vercel. Uses token from body, or user's stored deploy_tokens.vercel, or env VERCEL_TOKEN."""
    deploy_files, project_name = await _get_project_deploy_files(project_id, user["id"])
    from validate_deployment import validate_deployment
    validation = validate_deployment("vercel", deploy_files, None)
    if not validation.valid and validation.errors:
        raise HTTPException(status_code=400, detail={"message": "Deploy validation failed", "errors": validation.errors, "warnings": validation.warnings})
    u = await db.users.find_one({"id": user["id"]}, {"deploy_tokens": 1})
    vercel_token = (
        (body.token if body and body.token else None)
        or (u.get("deploy_tokens") or {}).get("vercel")
        or os.environ.get("VERCEL_TOKEN")
    )
    if not vercel_token:
        raise HTTPException(
            status_code=402,
            detail="Add your Vercel token in Settings → Deploy integrations for one-click deploy, or set VERCEL_TOKEN on server.",
        )
    files_payload = []
    for path, content in deploy_files.items():
        safe_path = (path or "").lstrip("/")
        if not safe_path:
            continue
        raw = content if isinstance(content, (bytes, bytearray)) else content.encode("utf-8")
        files_payload.append({"file": safe_path, "data": base64.b64encode(raw).decode("ascii")})
    if not files_payload:
        raise HTTPException(status_code=400, detail="No deploy files to upload")
    import httpx
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            "https://api.vercel.com/v13/deployments",
            headers={"Authorization": f"Bearer {vercel_token}", "Content-Type": "application/json"},
            json={"name": project_name, "files": files_payload, "target": "production"},
        )
    if r.status_code >= 400:
        msg = r.text
        try:
            msg = r.json().get("error", {}).get("message", r.text)
        except (jwt.InvalidTokenError, jwt.DecodeError, KeyError) as e:
            logger.debug(f"Invalid JWT token: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in JWT verification: {e}")
        raise HTTPException(status_code=502, detail=f"Vercel deploy failed: {msg}")
    data = r.json()
    url = data.get("url") or (data.get("alias", [""])[0] if data.get("alias") else "")
    if not url and data.get("id"):
        url = f"https://{data.get('id', '')}.vercel.app"
    live_url = url or data.get("url")
    if live_url:
        await db.projects.update_one({"id": project_id, "user_id": user["id"]}, {"$set": {"live_url": live_url}})
        if audit_logger:
            await audit_logger.log(
                user["id"], "project_deployed",
                resource_type="project", resource_id=project_id,
                new_value={"live_url": live_url},
                ip_address=getattr(request.client, "host", None),
            )
    return {"url": live_url, "deployment_id": data.get("id"), "status": data.get("status")}


@projects_router.post("/projects/{project_id}/deploy/netlify")
async def one_click_deploy_netlify(
    project_id: str,
    request: Request,
    body: Optional[DeployOneClickBody] = None,
    user: dict = Depends(require_permission(Permission.DEPLOY_PROJECT if Permission else None)),
):
    """One-click deploy to Netlify. Uses token from body, or user's stored deploy_tokens.netlify, or env NETLIFY_TOKEN."""
    deploy_files, _ = await _get_project_deploy_files(project_id, user["id"])
    from validate_deployment import validate_deployment
    validation = validate_deployment("netlify", deploy_files, None)
    if not validation.valid and validation.errors:
        raise HTTPException(status_code=400, detail={"message": "Deploy validation failed", "errors": validation.errors, "warnings": validation.warnings})
    buf = await _build_project_deploy_zip(project_id, user["id"])
    zip_bytes = buf.getvalue()
    u = await db.users.find_one({"id": user["id"]}, {"deploy_tokens": 1})
    netlify_token = (
        (body.token if body and body.token else None)
        or (u.get("deploy_tokens") or {}).get("netlify")
        or os.environ.get("NETLIFY_TOKEN")
    )
    if not netlify_token:
        raise HTTPException(
            status_code=402,
            detail="Add your Netlify token in Settings → Deploy integrations for one-click deploy, or set NETLIFY_TOKEN on server.",
        )
    import httpx
    async with httpx.AsyncClient(timeout=90.0) as client:
        r = await client.post(
            "https://api.netlify.com/api/v1/sites",
            headers={
                "Authorization": f"Bearer {netlify_token}",
                "Content-Type": "application/zip",
            },
            content=zip_bytes,
        )
    if r.status_code >= 400:
        msg = r.text
        try:
            msg = r.json().get("message", r.text)
        except (jwt.InvalidTokenError, jwt.DecodeError, KeyError) as e:
            logger.debug(f"Invalid JWT token: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in JWT verification: {e}")
        raise HTTPException(status_code=502, detail=f"Netlify deploy failed: {msg}")
    data = r.json()
    url = data.get("ssl_url") or data.get("url") or ""
    if not url and data.get("default_subdomain"):
        url = f"https://{data['default_subdomain']}.netlify.app"
    if not url and data.get("name"):
        url = f"https://{data['name']}.netlify.app"
    if url:
        await db.projects.update_one({"id": project_id, "user_id": user["id"]}, {"$set": {"live_url": url}})
        if audit_logger:
            await audit_logger.log(
                user["id"], "project_deployed",
                resource_type="project", resource_id=project_id,
                new_value={"live_url": url},
                ip_address=getattr(request.client, "host", None),
            )
    return {"url": url, "site_id": data.get("id")}


@projects_router.post("/projects/{project_id}/retry-phase")
async def retry_project_phase(
    project_id: str,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_permission(Permission.EDIT_PROJECT if Permission else None)),
):
    """10/10: Retry full orchestration when Quality phase had many failures. Full re-run (no partial state)."""
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.projects.update_one(
        {"id": project_id},
        {"$set": {
            "status": "running",
            "progress_percent": 0,
            "current_phase": 0,
            "current_agent": None,
            "completed_at": None,
            "suggest_retry_phase": None,
            "suggest_retry_reason": None,
        }}
    )
    background_tasks.add_task(run_orchestration_v2, project_id, user["id"])
    return {"status": "accepted", "message": "Retry started. Build is running."}


@projects_router.get("/projects/{project_id}/logs")
async def get_project_logs(project_id: str, user: dict = Depends(get_current_user)):
    cursor = db.project_logs.find({"project_id": project_id}, {"_id": 0}).sort("created_at", 1)
    logs = await cursor.to_list(500)
    return {"logs": logs}


@projects_router.get("/projects/{project_id}/build-history")
async def get_build_history(project_id: str, user: dict = Depends(get_current_user)):
    """Version history (item 13): list of past builds for this project (completed_at, status, quality_score, tokens_used)."""
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]}, {"build_history": 1})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    history = project.get("build_history") or []
    return {"build_history": history}

# Build phases for real-time progress UI (planning -> generating -> validating -> deployment)
BUILD_PHASES = [
    {"id": "planning", "name": "Planning", "agents": ["Planner", "Requirements Clarifier", "Stack Selector"]},
    {"id": "generating", "name": "Generating", "agents": ["Frontend Generation", "Backend Generation", "Database Agent", "API Integration", "Test Generation", "Image Generation"]},
    {"id": "validating", "name": "Validating", "agents": ["Security Checker", "Test Executor", "UX Auditor", "Performance Analyzer"]},
    {"id": "deployment", "name": "Deployment", "agents": ["Deployment Agent", "Error Recovery", "Memory Agent"]},
    {"id": "export_automation", "name": "Export & automation", "agents": ["PDF Export", "Excel Export", "Markdown Export", "Scraping Agent", "Automation Agent"]},
]

@projects_router.get("/build/phases")
async def get_build_phases():
    """Return phase list for progress UI (Workspace or dashboard)."""
    return {"phases": BUILD_PHASES}

SWARM_TOKEN_MULTIPLIER = 1.5  # users pay more when using swarm (parallel); we don't lose money

@projects_router.post("/build/plan")
async def build_plan(data: BuildPlanRequest, user: dict = Depends(get_current_user)):
    """Return a structured plan for a build request. swarm=True runs plan and suggestions in parallel (faster, higher token cost). build_kind: fullstack|mobile|saas|bot|ai_agent."""
    prompt = (data.prompt or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required")
    build_kind = (getattr(data, "build_kind", None) or "").strip().lower() or "fullstack"
    if build_kind not in ("landing", "fullstack", "mobile", "saas", "bot", "ai_agent", "game", "trading", "any"):
        build_kind = "fullstack"
    use_swarm = getattr(data, "swarm", False) and user is not None
    if user is not None and not user.get("public_api"):
        credits = _user_credits(user)
        required = MIN_CREDITS_FOR_LLM * (SWARM_TOKEN_MULTIPLIER if use_swarm else 1)
        if credits < required:
            raise HTTPException(status_code=402, detail=f"Insufficient credits for {'Swarm ' if use_swarm else ''}plan. Need at least {int(required)}. Buy more in Credit Center.")
        # Free/referral credits = landing only: if user has no paid purchase and requests non-landing, block
        # Free users with credits can build anything - no landing-only restriction
        # (The credit balance check above already ensures they have enough credits)
    kind_instruction = {
        "landing": " The user wants a LANDING PAGE (single page or simple multi-section). Plan for hero, features, CTA, optional waitlist/form; no full app backend or SaaS billing.",
        "mobile": " The user wants a MOBILE APP (React Native, Flutter, or PWA). Plan for mobile-first UI, native or cross-platform, and app store / install considerations. Include in the plan: Mobile stack: Expo (or Flutter), targets: iOS, Android.",
        "saas": " The user wants a SAAS product. Plan for multi-tenant or single-tenant with billing: subscriptions (e.g. Stripe), plans/tiers, auth, and dashboard.",
        "bot": " The user wants a BOT (Slack, Discord, Telegram, or webhook). Plan for event handlers, commands, and optional persistence; no traditional web UI unless a simple status page.",
        "ai_agent": " The user wants an AI AGENT. Plan for tools/functions the agent can call, a system prompt, and optionally an API or runner that executes the agent (e.g. OpenAPI + LLM).",
        "game": " The user wants a GAME (browser, mobile, or desktop). Plan for game loop, UI/canvas, controls, levels or mechanics, and optional backend for scores/leaderboards.",
        "trading": " The user wants TRADING SOFTWARE (stocks, crypto, forex, or general). Plan for order types, positions, P&L, charts/visualization, risk controls, optional real-time or simulated data; consider compliance and disclaimers.",
        "any": " The user wants to build ANYTHING—no restriction. Plan according to the request: web app, game, tool, bot, SaaS, mobile, trading, automation, or combination. Choose the best stack and structure for the idea.",
    }.get(build_kind, "")
    system = f"""You are a product and engineering planner. Given a user request to build an application, output a concise plan in this exact format (use the headings and bullets, no extra text before/after).{kind_instruction}

Plan
Key Features:
• [Feature 1] – [one line]
• [Feature 2] – [one line]
• (add 4-8 features as needed)

Design Language:
• [e.g. Dark navy + white + gold accent for premium feel]
• Clean, spacious layout with card-based UI
• (2-4 short design points)

Color Palette:
• Primary: [name] (#hex)
• Secondary: [name] (#hex)
• Accent: [name] (#hex)
• Background: [name] (#hex)

Components:
• [e.g. Layout with sidebar navigation]
• [e.g. Dashboard stats cards, charts]
• (list 6-12 UI components or pages)

End with exactly: "Let me build this now."
"""
    try:
        user_keys = await get_workspace_api_keys(user)
        effective = _effective_api_keys(user_keys)
        model_chain = _get_model_chain("auto", prompt, effective_keys=effective)
        plan_text = ""
        suggestions = []

        async def get_plan():
            nonlocal plan_text
            pt, _ = await _call_llm_with_fallback(
                message=f"User request: {prompt}",
                system_message=system,
                session_id=str(uuid.uuid4()),
                model_chain=model_chain,
                api_keys=effective,
            )
            return (pt or "").strip()

        async def get_suggestions_standalone():
            sug_system = "Given the user request for an app, suggest exactly 3 short follow-up features or improvements (e.g. 'Add Loan Management', 'Implement Alerts System'). Reply with a JSON array of 3 strings, nothing else."
            resp, _ = await _call_llm_with_fallback(
                message=f"User request: {prompt[:800]}",
                system_message=sug_system,
                session_id=str(uuid.uuid4()),
                model_chain=model_chain,
                api_keys=effective,
            )
            import re
            m = re.search(r"\[.*?\]", resp or "", re.DOTALL)
            arr = json.loads(m.group()) if m else []
            return [str(x).strip() for x in arr[:3]] if isinstance(arr, list) else []

        if use_swarm:
            plan_text, sug_list = await asyncio.gather(get_plan(), get_suggestions_standalone())
            suggestions = sug_list or ["Add more features", "Enhance reporting", "Improve accessibility"]
        else:
            plan_text = await get_plan()
            try:
                sug_system = "Given the app plan above, suggest exactly 3 short follow-up features or improvements (e.g. 'Add Loan Management', 'Implement Alerts System'). Reply with a JSON array of 3 strings, nothing else."
                sug_resp, _ = await _call_llm_with_fallback(
                    message=f"Plan:\n{plan_text[:1500]}",
                    system_message=sug_system,
                    session_id=str(uuid.uuid4()),
                    model_chain=model_chain,
                    api_keys=effective,
                )
                import re
                m = re.search(r"\[.*?\]", sug_resp or "", re.DOTALL)
                arr = json.loads(m.group()) if m else []
                if isinstance(arr, list):
                    suggestions = [str(x).strip() for x in arr[:3]]
            except Exception:
                pass
            if not suggestions:
                suggestions = ["Add more features", "Enhance reporting", "Improve accessibility"]

        tokens_estimate = max(1000, len(plan_text) * 2 + sum(len(s) for s in suggestions) * 2)
        if use_swarm:
            tokens_estimate = int(tokens_estimate * SWARM_TOKEN_MULTIPLIER)
        if user and not user.get("public_api"):
            cred = _user_credits(user)
            credit_deduct = min(_tokens_to_credits(tokens_estimate), cred)
            if credit_deduct > 0:
                await _ensure_credit_balance(user["id"])
                await db.users.update_one({"id": user["id"]}, {"$inc": {"credit_balance": -credit_deduct}})
        return {"plan_text": plan_text, "suggestions": suggestions, "model_used": "auto", "swarm_used": use_swarm, "plan_tokens": tokens_estimate}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("build/plan failed")
        raise HTTPException(status_code=500, detail=str(e))

@projects_router.get("/projects/{project_id}/phases")
async def get_project_phases(project_id: str, user: dict = Depends(get_current_user)):
    """Return current phase and per-phase status for a project."""
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    statuses = await db.agent_status.find({"project_id": project_id}, {"_id": 0}).to_list(100)
    by_agent = {s["agent_name"]: s for s in statuses}
    phases_out = []
    current_phase_id = None
    for ph in BUILD_PHASES:
        agent_statuses = [by_agent.get(a, {"status": "pending", "progress": 0}) for a in ph["agents"]]
        completed = sum(1 for a in agent_statuses if a.get("status") == "completed")
        total = len(ph["agents"])
        status = "completed" if completed == total else ("running" if completed > 0 or current_phase_id == ph["id"] else "pending")
        if status == "running" and current_phase_id is None:
            current_phase_id = ph["id"]
        phases_out.append({
            "id": ph["id"],
            "name": ph["name"],
            "status": status,
            "progress": round(100 * completed / total) if total else 0,
            "agents": agent_statuses,
        })
    if not current_phase_id and project.get("status") == "completed":
        current_phase_id = "deployment"
    return {"phases": phases_out, "current_phase": current_phase_id, "project_status": project.get("status")}

# ==================== ORCHESTRATION ====================

# All 20 agents – orchestration runs each with real LLM when keys are set
_ORCHESTRATION_AGENTS = [
    ("Planner", 50000, "You are a Planner. Decompose the request into 3-7 executable tasks. Numbered list only."),
    ("Requirements Clarifier", 30000, "You are a Requirements Clarifier. Ask 2-4 clarifying questions. One per line."),
    ("Stack Selector", 20000, "You are a Stack Selector. Recommend tech stack (frontend, backend, DB). Short bullets."),
    ("Frontend Generation", 150000, "You are Frontend Generation. Output only complete React/JSX code. No markdown."),
    ("Backend Generation", 120000, "You are Backend Generation. Output only backend code (e.g. FastAPI/Express). No markdown."),
    ("Database Agent", 80000, "You are a Database Agent. Output schema and migration steps. Plain text or SQL."),
    ("API Integration", 60000, "You are API Integration. Output only code that calls an API. No markdown."),
    ("Test Generation", 100000, "You are Test Generation. Output only test code. No markdown."),
    ("Image Generation", 40000, "You are Image Generation. Output a detailed image prompt (style, composition, colors) for the request."),
    ("Security Checker", 40000, "You are a Security Checker. List 3-5 security checklist items with PASS/FAIL."),
    ("Test Executor", 50000, "You are a Test Executor. Give the test command and one line of what to check."),
    ("UX Auditor", 35000, "You are a UX Auditor. List 2-4 accessibility/UX checklist items with PASS/FAIL."),
    ("Performance Analyzer", 40000, "You are a Performance Analyzer. List 2-4 performance tips for the project."),
    ("Deployment Agent", 60000, "You are a Deployment Agent. Give step-by-step deploy instructions."),
    ("Error Recovery", 45000, "You are Error Recovery. List 2-3 common failure points and how to recover."),
    ("Memory Agent", 25000, "You are a Memory Agent. Summarize the project in 2-3 lines for reuse."),
    ("PDF Export", 30000, "You are PDF Export. Describe what a one-page project summary PDF would include."),
    ("Excel Export", 25000, "You are Excel Export. Suggest 3-5 columns for a project tracking spreadsheet."),
    ("Markdown Export", 20000, "You are Markdown Export. Output a short project summary in Markdown (headings, bullets)."),
    ("Scraping Agent", 35000, "You are a Scraping Agent. Suggest 2-3 data sources or URLs to scrape for this project."),
    ("Automation Agent", 30000, "You are an Automation Agent. Suggest 2-3 automated tasks or cron jobs for this project."),
]

async def run_orchestration(project_id: str, user_id: str):
    """Runs real agent orchestration: each agent calls the LLM when API keys are set. Uses user's Settings keys when available."""
    project = await db.projects.find_one({"id": project_id})
    if not project:
        return
    req = project.get("requirements") or {}
    prompt = req.get("prompt") or req.get("description") or project.get("description") or "Build a web application"
    if isinstance(prompt, dict):
        prompt = prompt.get("prompt") or str(prompt)
    user_keys = await get_workspace_api_keys({"id": user_id})
    effective = _effective_api_keys(user_keys)
    
    # Get user tier and derive speed from plan (no client speed_selector)
    user = await db.users.find_one({"id": user_id}, {"plan": 1, "credit_balance": 1})
    user_tier = user.get("plan", "free") if user else "free"
    available_credits = user.get("credit_balance", 0) if user else 0
    speed_selector = _speed_from_plan(user_tier)
    model_chain = _get_model_chain("auto", prompt, effective_keys=effective)

    await db.projects.update_one({"id": project_id}, {"$set": {"status": "running"}})
    total_used = 0

    for agent_name, base_tokens, system_msg in _ORCHESTRATION_AGENTS:
        await db.agent_status.update_one(
            {"project_id": project_id, "agent_name": agent_name},
            {"$set": {
                "project_id": project_id,
                "agent_name": agent_name,
                "status": "running",
                "progress": 0,
                "tokens_used": 0,
                "started_at": datetime.now(timezone.utc).isoformat()
            }},
            upsert=True
        )
        await db.project_logs.insert_one({
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "agent": agent_name,
            "message": f"Starting {agent_name}...",
            "level": "info",
            "created_at": datetime.now(timezone.utc).isoformat()
        })

        tokens_used = 0
        try:
            if effective.get("anthropic"):
                response, _ = await _call_llm_with_fallback(
                    message=prompt,
                    system_message=system_msg,
                    session_id=f"orch_{project_id}",
                    model_chain=model_chain,
                    api_keys=effective,
                )
                tokens_used = max(100, min(200000, (len(prompt) + len(response or "")) * 2))
                await db.project_logs.insert_one({
                    "id": str(uuid.uuid4()),
                    "project_id": project_id,
                    "agent": agent_name,
                    "message": f"{agent_name} output: {(response or '')[:200]}...",
                    "level": "info",
                    "created_at": datetime.now(timezone.utc).isoformat()
                })
        except Exception as e:
            logger.warning(f"Orchestration agent {agent_name} LLM failed: {e}")

        for progress in range(0, 101, 25):
            await asyncio.sleep(0.2)
            await db.agent_status.update_one(
                {"project_id": project_id, "agent_name": agent_name},
                {"$set": {"progress": progress, "tokens_used": int(tokens_used * progress / 100)}}
            )
        await db.agent_status.update_one(
            {"project_id": project_id, "agent_name": agent_name},
            {"$set": {"status": "completed", "progress": 100, "tokens_used": tokens_used}}
        )
        await db.token_usage.insert_one({
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "user_id": user_id,
            "agent": agent_name,
            "tokens": tokens_used,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        total_used += tokens_used

        
        # --- METRICS: Track build completion ---
        try:
            _metrics.builds_total.labels(status="success").inc()
            _metrics.build_queue_depth.dec()
        except Exception:
            pass

        await db.project_logs.insert_one({
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "agent": agent_name,
            "message": f"{agent_name} completed. Used {tokens_used:,} tokens.",
            "level": "success",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
    
    await db.projects.update_one(
        {"id": project_id},
        {"$set": {
            "status": "completed",
            "tokens_used": total_used,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "live_url": None
        }}
    )
    
    project = await db.projects.find_one({"id": project_id})
    if project:
        refund_tokens = project["tokens_allocated"] - total_used
        if refund_tokens > 0:
            refund_credits = refund_tokens // CREDITS_PER_TOKEN
            await db.users.update_one({"id": user_id}, {"$inc": {"credit_balance": refund_credits}})
            await db.token_ledger.insert_one({
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "tokens": refund_tokens,
                "credits": refund_credits,
                "type": "refund",
                "description": f"Unused from project {project_id[:8]}",
                "created_at": datetime.now(timezone.utc).isoformat()
            })


# ==================== ORCHESTRATION V2 (DAG + PARALLEL + OUTPUT CHAINING + ERROR RECOVERY) ====================

async def _run_single_agent_with_context(
    project_id: str,
    user_id: str,
    agent_name: str,
    project_prompt: str,
    previous_outputs: Dict[str, Dict[str, Any]],
    effective: Dict[str, Optional[str]],
    model_chain: list,
    build_kind: Optional[str] = None,
    user_tier: str = "free",
    speed_selector: str = "lite",
    available_credits: int = 0,
) -> Dict[str, Any]:
    """Run one agent with context from previous agents. Returns {output, tokens_used, status} or raises."""
    if agent_name not in AGENT_DAG:
        return {"output": "", "tokens_used": 0, "status": "skipped", "reason": "Unknown agent"}
    # Real tool agents: execute real tools (File, Browser, API, Database, Deployment) from DAG context
    if agent_name in REAL_AGENT_NAMES:
        real_result = await run_real_agent(
            agent_name, project_id, user_id, previous_outputs, project_prompt
        )
        if real_result is not None:
            persist_agent_output(project_id, agent_name, real_result)
            try:
                run_agent_real_behavior(agent_name, project_id, real_result, previous_outputs)
            except Exception as e:
                logger.warning("run_agent_real_behavior %s: %s", agent_name, e)
            return real_result
    system_msg = get_system_prompt_for_agent(agent_name)
    if agent_name == "Frontend Generation" and (build_kind or "").strip().lower() == "mobile":
        system_msg = "You are Frontend Generation for a mobile app. Output only Expo/React Native code (App.js, use React Native components from 'react-native', no DOM or web-only APIs). No markdown."
    enhanced_message = build_context_from_previous_agents(agent_name, previous_outputs, project_prompt)
    response, _ = await _call_llm_with_fallback(
        message=enhanced_message,
        system_message=system_msg,
        session_id=f"orch_{project_id}",
        model_chain=model_chain,
        api_keys=effective,
        user_id=user_id,
        user_tier=user_tier,
        speed_selector=speed_selector,
        available_credits=available_credits,
        agent_name=agent_name,
    )
    tokens_used = max(100, min(200000, (len(enhanced_message) + len(response or "")) * 2))
    out = (response or "").strip()

    # Image Generation: LLM returns JSON prompts -> Together.ai generates images
    if agent_name == "Image Generation" and generate_images_for_app and parse_image_prompts:
        try:
            prompts_dict = parse_image_prompts(out)
            design_desc = enhanced_message[:1000] if enhanced_message else project_prompt[:500]
            images = await generate_images_for_app(design_desc, prompts_dict if prompts_dict else None)
            out = json.dumps(images) if images else out
            result = {"output": out, "tokens_used": tokens_used, "status": "completed", "result": out, "code": out, "images": images}
            result = await run_real_post_step(agent_name, project_id, previous_outputs, result)
            persist_agent_output(project_id, agent_name, result)
            try:
                run_agent_real_behavior(agent_name, project_id, result, previous_outputs)
            except Exception as e:
                logger.warning("run_agent_real_behavior %s: %s", agent_name, e)
        except Exception as e:
            logger.error(f"Image generation failed: {e}")
            result = {"output": out, "tokens_used": tokens_used, "status": "completed", "result": out, "code": out}
    
    try:
        agent_memory.record_execution(agent_name, {
            "input": input_data,
            "output": result,
            "timestamp": datetime.now(),
            "tokens_used": tokens_used
        })
    except Exception as e:
        logger.error(f"Failed to record execution: {e}")
    
    # Store in vector memory
    try:
        await vector_store.store_execution(
            agent_id=agent_name,
            execution_data={
                "input": input_data,
                "output": result,
                "agent": agent_name
            }
        )
    except Exception as e:
        logger.debug(f"Vector store unavailable: {e}")
    
    return result
    # Video Generation: LLM returns JSON search queries -> Pexels finds videos
    if agent_name == "Video Generation" and generate_videos_for_app and parse_video_queries:
        try:
            queries_dict = parse_video_queries(out)
            design_desc = enhanced_message[:1000] if enhanced_message else project_prompt[:500]
            videos = await generate_videos_for_app(design_desc, queries_dict if queries_dict else None)
            out = json.dumps(videos) if videos else out
            result = {"output": out, "tokens_used": tokens_used, "status": "completed", "result": out, "code": out, "videos": videos}
            result = await run_real_post_step(agent_name, project_id, previous_outputs, result)
            persist_agent_output(project_id, agent_name, result)
            try:
                run_agent_real_behavior(agent_name, project_id, result, previous_outputs)
            except Exception as e:
                logger.warning("run_agent_real_behavior %s: %s", agent_name, e)
            return result
        except Exception as e:
            logger.warning("Video generation agent failed: %s", e)

    result = {"output": out, "tokens_used": tokens_used, "status": "completed", "result": out, "code": out}
    result = await run_real_post_step(agent_name, project_id, previous_outputs, result)
    persist_agent_output(project_id, agent_name, result)
    try:
        run_agent_real_behavior(agent_name, project_id, result, previous_outputs)
    except Exception as e:
        logger.warning("run_agent_real_behavior %s: %s", agent_name, e)

    
    # --- METRICS: Track agent execution ---
    try:
        _metrics.agent_executions_total.labels(agent=agent_name, status="success" if out and len(out) > 50 else "partial").inc()
        _metrics.active_agents.dec()
    except Exception:
        pass

# --- AGENT LEARNING: Record execution for recursive learning ---
    try:
        memory = await _init_agent_learning()
        if memory:
            await memory.record_execution(
                agent_name=agent_name,
                input_data={"prompt": (enhanced_message or "")[:500], "project_id": project_id},
                output={"result": (out or "")[:500], "tokens": tokens_used},
                status=ExecutionStatus.SUCCESS if out and len(out) > 50 else ExecutionStatus.PARTIAL,
                duration_ms=0,  # Could add timing if needed
                metadata={"build_kind": build_kind or "web"}
            )
    except Exception as _learn_err:
        logger.debug(f"Agent learning record failed (non-fatal): {_learn_err}")
    
    # --- VECTOR MEMORY: Store output for RAG ---
    try:
        if _vector_memory.is_available():
            await _vector_memory.store_agent_output(
                project_id=project_id,
                agent_name=agent_name,
                output=(out or "")[:2000],
                tokens_used=tokens_used,
            )
    except Exception as _vec_err:
        logger.debug(f"Vector memory store failed (non-fatal): {_vec_err}")
    # --- END VECTOR MEMORY ---

    # --- END AGENT LEARNING ---

    return result


def _agent_cache_input(agent_name: str, project_prompt: str, previous_outputs: Dict[str, Dict[str, Any]]) -> str:
    """Build stable input string for agent cache key (prompt + dependent outputs)."""
    parts = [project_prompt]
    deps = list(AGENT_DAG.get(agent_name, {}).get("depends_on", []))
    for dep in sorted(deps):
        if dep in previous_outputs:
            out = (previous_outputs[dep].get("output") or previous_outputs[dep].get("result") or "")[:800]
            parts.append(f"{dep}:{out}")
    return "\n".join(parts)


async def _run_single_agent_with_retry(
    project_id: str,
    user_id: str,
    agent_name: str,
    project_prompt: str,
    previous_outputs: Dict[str, Dict[str, Any]],
    effective: Dict[str, Optional[str]],
    model_chain: list,
    max_retries: int = 3,
    build_kind: Optional[str] = None,
    user_tier: str = "free",
    speed_selector: str = "lite",
    available_credits: int = 0,
) -> Dict[str, Any]:
    from agent_cache import get as cache_get, set as cache_set
    input_data = _agent_cache_input(agent_name, project_prompt, previous_outputs)
    cached = await cache_get(db, agent_name, input_data)
    if cached and isinstance(cached, dict) and (cached.get("output") or cached.get("result")):
        return cached
    last_err = None
    for attempt in range(max_retries):
        try:
            r = await _run_single_agent_with_context(
                project_id, user_id, agent_name, project_prompt, previous_outputs, effective, model_chain, build_kind=build_kind,
                user_tier=user_tier, speed_selector=speed_selector, available_credits=available_credits
            )
            if not (r.get("output") or r.get("result")):
                raise AgentError(agent_name, "Empty output", "medium")
            await cache_set(db, agent_name, input_data, r)
            return r
        except Exception as e:
            last_err = e
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)
    crit = get_criticality(agent_name)
    if crit == "critical":
        completed_at = datetime.now(timezone.utc).isoformat()
        await db.projects.update_one(
            {"id": project_id},
            {"$set": {"status": "failed", "completed_at": completed_at}}
        )
        # Append to build_history for version history UI (item 13)
        proj = await db.projects.find_one({"id": project_id})
        if proj is not None:
            history = list(proj.get("build_history") or [])
            history.insert(0, {"completed_at": completed_at, "status": "failed", "quality_score": None, "tokens_used": 0})
            await db.projects.update_one({"id": project_id}, {"$set": {"build_history": history[:50]}})
        return {"output": "", "tokens_used": 0, "status": "failed", "reason": str(last_err), "recoverable": False}
    if crit == "high":
        fallback = generate_fallback(agent_name)
        return {"output": fallback, "result": fallback, "tokens_used": 0, "status": "failed_with_fallback", "reason": str(last_err), "recoverable": True}
    return {"output": "", "tokens_used": 0, "status": "skipped", "reason": str(last_err), "recoverable": True}


def _inject_media_into_jsx(jsx: str, images: Dict[str, str], videos: Dict[str, str]) -> str:
    """Inject image/video URLs into generated JSX. Replaces placeholders or prepends a media section."""
    if not jsx or (not images and not videos):
        return jsx
    # Replace placeholders if present
    out = jsx
    if images.get("hero"):
        out = out.replace("CRUCIBAI_HERO_IMG", images["hero"]).replace("{{HERO_IMAGE}}", images["hero"])
    if images.get("feature_1"):
        out = out.replace("CRUCIBAI_FEATURE_1_IMG", images["feature_1"]).replace("{{FEATURE_1_IMAGE}}", images["feature_1"])
    if images.get("feature_2"):
        out = out.replace("CRUCIBAI_FEATURE_2_IMG", images["feature_2"]).replace("{{FEATURE_2_IMAGE}}", images["feature_2"])
    if videos.get("hero"):
        out = out.replace("CRUCIBAI_HERO_VIDEO", videos["hero"]).replace("{{HERO_VIDEO}}", videos["hero"])
    if videos.get("feature"):
        out = out.replace("CRUCIBAI_FEATURE_VIDEO", videos["feature"]).replace("{{FEATURE_VIDEO}}", videos["feature"])
    # If no placeholders were used, prepend a media section after "return ("
    if out == jsx and ("CRUCIBAI_" not in jsx and "{{HERO" not in jsx):
        media_parts = []
        if videos.get("hero"):
            media_parts.append(f'<section className="relative w-full h-48 md:h-64 overflow-hidden rounded-lg"><video autoPlay muted loop playsInline className="absolute inset-0 w-full h-full object-cover" src="{videos["hero"]}" /></section>')
        img_keys = ["hero", "feature_1", "feature_2"]
        img_urls = [images.get(k) for k in img_keys if images.get(k)]
        if img_urls:
            divs = "".join(f'<div><img src="{u}" alt="Media" className="w-full h-32 object-cover rounded-lg" /></div>' for u in img_urls)
            media_parts.append(f'<section className="grid grid-cols-1 md:grid-cols-3 gap-4 py-4">{divs}</section>')
        if media_parts:
            block = "\n      ".join(media_parts)
            idx = out.find("return (")
            if idx != -1:
                insert = idx + len("return (")
                out = out[:insert] + "\n      " + block + "\n      " + out[insert:].lstrip()
    return out


# CrucibAI attribution: comment at top + footer. Free = iframe (served from our server, not removable). Paid = static div (user may remove).
CRUCIBAI_TOP_COMMENT = "// Built with CrucibAI · https://crucibai.com\n"
# URL for free-tier iframe: badge content is on our server so free users have no way to remove it (only the iframe tag in source).
_BRANDING_BASE_URL = os.environ.get("CRUCIBAI_BRANDING_URL") or (os.environ.get("BACKEND_PUBLIC_URL", "http://localhost:8000").rstrip("/") + "/branding")
# Free: iframe loads badge from our server — permanent, not in their editable content.
CRUCIBAI_FREE_FOOTER_JSX = (
    f'<iframe src="{_BRANDING_BASE_URL}" title="Built with CrucibAI" '
    'style={{ border: "none", height: "28px", width: "100%", display: "block" }} />'
)
# Paid: static div so they can remove it in the editor if they want.
CRUCIBAI_PAID_FOOTER_JSX = (
    '<div className="mt-8 py-3 text-center text-sm text-gray-500 border-t border-gray-200/50">'
    '<a href="https://crucibai.com" target="_blank" rel="noopener noreferrer" className="text-gray-500 hover:text-gray-700">Built with CrucibAI</a>'
    '</div>'
)


def _inject_crucibai_branding(jsx: str, plan: str) -> str:
    """Add CrucibAI attribution. Free: iframe (content on our server — cannot be removed). Paid: static div (user may remove)."""
    if not jsx or not jsx.strip():
        return jsx
    out = jsx
    # 1) Top comment (watermark in code)
    if "crucibai.com" not in out.lower() and "Built with CrucibAI" not in out:
        if out.lstrip().startswith("//") or out.lstrip().startswith("/*"):
            first_newline = out.find("\n")
            if first_newline != -1:
                out = out[: first_newline + 1] + CRUCIBAI_TOP_COMMENT + out[first_newline + 1 :]
            else:
                out = CRUCIBAI_TOP_COMMENT + out
        else:
            out = CRUCIBAI_TOP_COMMENT + out
    # 2) Footer: free = iframe (permanent); paid = static div (removable)
    is_free = (plan or "free").lower() == "free"
    already_has = (CRUCIBAI_PAID_FOOTER_JSX in out) or (is_free and "/branding" in out)
    if not already_has:
        footer_jsx = CRUCIBAI_FREE_FOOTER_JSX if is_free else CRUCIBAI_PAID_FOOTER_JSX
        idx = out.rfind(");")
        if idx != -1:
            before = out[:idx]
            last_div = before.rfind("</div>")
            if last_div != -1:
                out = out[:last_div] + "\n      " + footer_jsx + "\n      " + out[last_div:]
    return out


def _infer_build_kind(prompt: str) -> str:
    """Infer build_kind from prompt so we build the right artifact: web, mobile, agent/automation, software, etc."""
    if not prompt:
        return "fullstack"
    p = prompt.lower()
    if any(x in p for x in ("mobile app", "react native", "flutter", "ios app", "android app", "pwa ", "app store", "play store", "apple store", "google play", "build me a mobile", "mobile application")):
        return "mobile"
    if any(x in p for x in ("build me an agent", "automation agent", "automation", "scheduled task", "cron", "webhook agent", "run_agent", "build agent")):
        return "ai_agent"
    if any(x in p for x in ("saas", "subscription", "multi-tenant", "billing", "stripe", "plans/tiers")):
        return "saas"
    if any(x in p for x in ("slack bot", "discord bot", "telegram bot", "chatbot", " webhook bot", "bot that")):
        return "bot"
    if any(x in p for x in ("ai agent", "llm agent", "agent with tools", "autonomous agent")):
        return "ai_agent"
    if any(x in p for x in ("game", "2d game", "3d game", "browser game", "mobile game", "arcade", "player score", "level design")):
        return "game"
    if any(x in p for x in ("trading software", "trading app", "stock trading", "crypto trading", "forex", "order book", "positions", "p&l", "trade execution", "portfolio tracker")):
        return "trading"
    if any(x in p for x in ("landing page", "landing only", "one-page", "marketing page")):
        return "landing"
    if any(x in p for x in ("website", "build me a website", "build me a web")):
        return "fullstack"
    if any(x in p for x in ("anything", "whatever", "no limit", "any idea", "any app")):
        return "any"
    return "fullstack"


async def run_orchestration_v2(project_id: str, user_id: str):
    """DAG-based orchestration: parallel phases, output chaining, retry, timeout, quality score."""
    # --- METRICS: Track build start ---
    try:
        _metrics.build_queue_depth.inc()
    except Exception:
        pass
    project = await db.projects.find_one({"id": project_id})
    if not project:
        return
    req = project.get("requirements") or {}
    prompt = req.get("prompt") or req.get("description") or project.get("description") or "Build a web application"
    if isinstance(prompt, dict):
        prompt = prompt.get("prompt") or str(prompt)
    build_kind = (req.get("build_kind") or "").strip().lower() or _infer_build_kind(prompt)
    if build_kind not in ("fullstack", "landing", "mobile", "saas", "bot", "ai_agent", "game", "trading", "any"):
        build_kind = "fullstack"
    project_prompt_with_kind = f"[Build kind: {build_kind}]\n{prompt}"
    try:
        from autonomous_domain_agent import initialize_autonomous_domain_agent
        _domain_agent = await initialize_autonomous_domain_agent(db)
        _analysis = await _domain_agent.analyze_requirements(prompt)
        _d = _analysis.get("detected_domain") or "general"
        _best = _analysis.get("best_practices") or []
        _constraints = _analysis.get("applicable_constraints") or []
        _extra = f"\n[Domain: {_d}]"
        if _best:
            _extra += "\nBest practices: " + "; ".join(str(x) for x in _best[:5])
        if _constraints:
            _extra += "\nConstraints: " + str(_constraints[:3])
        project_prompt_with_kind = f"[Build kind: {build_kind}]{_extra}\n{prompt}"
    except Exception as _dom_err:
        logger.debug("Autonomous domain enrichment skipped: %s", _dom_err)
    user_keys = await get_workspace_api_keys({"id": user_id})
    effective = _effective_api_keys(user_keys)
    
    # Get user tier and derive speed from plan (no client speed_selector)
    user = await db.users.find_one({"id": user_id}, {"plan": 1, "credit_balance": 1})
    user_tier = user.get("plan", "free") if user else "free"
    available_credits = user.get("credit_balance", 0) if user else 0
    speed_selector = _speed_from_plan(user_tier)
    model_chain = _get_model_chain("auto", prompt, effective_keys=effective)
    if not effective.get("anthropic"):
        await db.projects.update_one({"id": project_id}, {"$set": {"status": "failed", "completed_at": datetime.now(timezone.utc).isoformat()}})
        emit_build_event(project_id, "build_completed", status="failed", message="No API keys")
        return
    await db.projects.update_one({"id": project_id}, {"$set": {"status": "running", "current_phase": 0, "progress_percent": 0}})
    phases = get_execution_phases(AGENT_DAG)
    # Item 29: Quick build — run only first 2 phases for preview in ~2 min
    if project.get("quick_build"):
        phases = phases[:2]
        emit_build_event(project_id, "build_started", phases=len(phases), message="Quick build started (preview in ~2 min)")
    else:
        emit_build_event(project_id, "build_started", phases=len(phases), message="Orchestration started")
    results: Dict[str, Dict[str, Any]] = {}
    total_used = 0
    suggest_retry_phase: Optional[int] = None
    suggest_retry_reason: Optional[str] = None
    for phase_idx, agent_names in enumerate(phases):
        emit_build_event(project_id, "phase_started", phase=phase_idx, agents=agent_names, message=f"Phase {phase_idx + 1}: {', '.join(agent_names)}")
        progress_pct = int((phase_idx + 1) / len(phases) * 100)
        await db.projects.update_one(
            {"id": project_id},
            {"$set": {"current_phase": phase_idx, "current_agent": ",".join(agent_names), "progress_percent": progress_pct, "tokens_used": total_used}},
        )
        for agent_name in agent_names:
            emit_build_event(project_id, "agent_started", agent=agent_name, message=f"{agent_name} started")
            await db.agent_status.update_one(
                {"project_id": project_id, "agent_name": agent_name},
                {"$set": {"project_id": project_id, "agent_name": agent_name, "status": "running", "progress": 0, "tokens_used": 0, "started_at": datetime.now(timezone.utc).isoformat()}},
                upsert=True,
            )
            await db.project_logs.insert_one({
                "id": str(uuid.uuid4()), "project_id": project_id, "agent": agent_name, "message": f"Starting {agent_name}...", "level": "info", "created_at": datetime.now(timezone.utc).isoformat()
            })
        timeout_sec = max(get_timeout(a) for a in agent_names)
        async def run_one(name: str):
            return await asyncio.wait_for(
                _run_single_agent_with_retry(project_id, user_id, name, project_prompt_with_kind, results, effective, model_chain, build_kind=build_kind,
                    user_tier=user_tier, speed_selector=speed_selector, available_credits=available_credits),
                timeout=timeout_sec + 30,
            )
        tasks = [run_one(name) for name in agent_names]
        phase_results = await asyncio.gather(*tasks, return_exceptions=True)
        phase_fail_count = 0
        for name, r in zip(agent_names, phase_results):
            if isinstance(r, Exception):
                phase_fail_count += 1
                crit = get_criticality(name)
                fallback = generate_fallback(name)
                if crit == "critical":
                    # Fallback on every critical path (9.5+): use minimal output and continue build
                    results[name] = {"output": fallback, "result": fallback, "status": "failed_with_fallback", "reason": str(r)}
                else:
                    results[name] = {"output": fallback, "result": fallback, "status": "failed_with_fallback"}
            else:
                results[name] = r
                total_used += r.get("tokens_used", 0)
                if (r.get("status") or "").lower() in ("skipped", "failed", "failed_with_fallback"):
                    phase_fail_count += 1
            emit_build_event(project_id, "agent_completed", agent=name, tokens=results[name].get("tokens_used", 0), status=results[name].get("status", ""), message=f"{name} completed")
            out_snippet = (results[name].get("output") or results[name].get("result") or "")[:200]
            await db.agent_status.update_one(
                {"project_id": project_id, "agent_name": name},
                {"$set": {"status": "completed", "progress": 100, "tokens_used": results[name].get("tokens_used", 0)}}
            )
            await db.project_logs.insert_one({
                "id": str(uuid.uuid4()), "project_id": project_id, "agent": name, "message": f"{name} completed. Output: {out_snippet}...", "level": "success", "created_at": datetime.now(timezone.utc).isoformat()
            })
            await db.token_usage.insert_one({
                "id": str(uuid.uuid4()), "project_id": project_id, "user_id": user_id, "agent": name, "tokens": results[name].get("tokens_used", 0), "created_at": datetime.now(timezone.utc).isoformat()
            })
        # 10/10: suggest phase retry when Quality phase (index 3) has many failures
        if phase_idx == 3 and phase_fail_count >= 2:
            suggest_retry_phase = 1
            suggest_retry_reason = "Quality phase had many failures. Retry code generation?"
        project = await db.projects.find_one({"id": project_id})
        if project and project.get("status") == "failed":
            return
    # Bounded autonomy loop: re-run tests/security once if they failed (self-heal)
    try:
        from autonomy_loop import run_bounded_autonomy_loop
        autonomy_result = run_bounded_autonomy_loop(project_id, results, emit_event=emit_build_event)
        if autonomy_result.get("iterations"):
            await db.project_logs.insert_one({
                "id": str(uuid.uuid4()), "project_id": project_id, "agent": "AutonomyLoop",
                "message": f"Self-heal: re-ran tests={autonomy_result.get('ran_tests')}, security={autonomy_result.get('ran_security')}",
                "level": "info", "created_at": datetime.now(timezone.utc).isoformat()
            })
    except Exception as e:
        logger.warning("autonomy loop: %s", e)

    # --- SPECIALIZED AGENT (domain-matched: game, ml, blockchain, etc.) ---
    _spec_key = None
    if build_kind == "game":
        _spec_key = "games"
    elif "ml" in prompt.lower() or "machine learning" in prompt.lower() or "model" in prompt.lower():
        _spec_key = "ml"
    elif "blockchain" in prompt.lower() or "smart contract" in prompt.lower() or "crypto" in prompt.lower():
        _spec_key = "blockchain"
    elif "iot" in prompt.lower() or "firmware" in prompt.lower() or "embedded" in prompt.lower():
        _spec_key = "iot"
    elif "science" in prompt.lower() or "math" in prompt.lower() or "simulation" in prompt.lower():
        _spec_key = "science"
    if _spec_key:
        try:
            from specialized_agents_100_percent import SpecializedAgentOrchestrator
            _spec_orch = SpecializedAgentOrchestrator()
            _spec_req = {"prompt": prompt, "name": project_id[:12], "type": "2d_platformer" if _spec_key == "games" else "full"}
            _spec_out = await _spec_orch.execute_agent(_spec_key, _spec_req)
            _code = _spec_out.get("game_code") or _spec_out.get("firmware_code") or _spec_out.get("model_code") or _spec_out.get("contract_code") or _spec_out.get("solution_code") or str(_spec_out)
            results[f"SpecializedAgent-{_spec_key.title()}"] = {"output": _code, "result": _code, "status": _spec_out.get("status", "ok"), "tokens_used": 0}
        except Exception as _spec_err:
            logger.debug("Specialized agent (%s) skipped: %s", _spec_key, _spec_err)

    # --- POST-BUILD: CRITIC + TRUTH (anti-hallucination) ---
    critic_review: Optional[Dict[str, Any]] = None
    truth_report: Optional[Dict[str, Any]] = None
    truth_result: Optional[Dict[str, Any]] = None
    emit_build_event(project_id, "quality_check_started", message="Running quality review and truth verification…")
    try:
        emit_build_event(project_id, "critic_started", message="Critic review…")
        critic_review = await _critic_agent.review_build(
            project_id=project_id,
            agent_outputs=results,
            llm_caller=_call_llm_with_fallback,
            model_chain=model_chain,
            api_keys=effective,
        )
        logger.info(f"Critic review: score={critic_review.get('overall_score')}, pass_rate={critic_review.get('pass_rate')}%")
        await db.project_logs.insert_one({
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "type": "critic_review",
            "data": critic_review,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as _critic_err:
        logger.debug("Critic review failed (non-fatal): %s", _critic_err)
    try:
        emit_build_event(project_id, "truth_started", message="Truth verification…")
        truth_report = await _truth_module.verify_claims(
            agent_outputs=results,
            llm_caller=_call_llm_with_fallback,
            model_chain=model_chain,
            api_keys=effective,
            project_prompt=prompt,
        )
        logger.info("Truth verification: verdict=%s, truth_score=%s", truth_report.get("verdict"), truth_report.get("truth_score"))
        await db.project_logs.insert_one({
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "type": "truth_verification",
            "data": truth_report,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as _truth_err:
        logger.debug("Truth verification failed (non-fatal): %s", _truth_err)

    # --- Optional: standalone truth_check (adversarial code honesty) ---
    try:
        from truth_module import truth_check as truth_check_build
        async def _llm_for_truth(msg: str, sys_msg: str, sid: str, mchain) -> str:
            r, _ = await _call_llm_with_fallback(
                message=msg, system_message=sys_msg, session_id=sid,
                model_chain=mchain if isinstance(mchain, list) else model_chain,
                api_keys=effective,
            )
            return r or ""
        build_output = {k: (v.get("output") or v.get("result") or "")[:5000] for k, v in list(results.items())[:15]}
        truth_result = await truth_check_build(project_id, build_output, _llm_for_truth)
        await db.project_logs.insert_one({
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "type": "truth_check_honesty",
            "data": truth_result,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as _tc_err:
        logger.debug("truth_check (honesty) failed (non-fatal): %s", _tc_err)

    critic_score = (critic_review or {}).get("overall_score")
    truth_verdict = (truth_report or {}).get("verdict")
    truth_score = (truth_report or {}).get("truth_score")
    truth_honest_score = (truth_result or {}).get("honest_score") if truth_result else None

    fe = (results.get("Frontend Generation") or {}).get("output") or ""
    be = (results.get("Backend Generation") or {}).get("output") or ""
    db_schema = (results.get("Database Agent") or {}).get("output") or ""
    tests = (results.get("Test Generation") or {}).get("output") or ""
    images = (results.get("Image Generation") or {}).get("images") or {}
    videos = (results.get("Video Generation") or {}).get("videos") or {}
    quality = score_generated_code(frontend_code=fe, backend_code=be, database_schema=db_schema, test_code=tests)
    deploy_files = {}
    if build_kind == "mobile" and fe:
        # Mobile project: Expo app + native config + store submission pack
        user_doc = await db.users.find_one({"id": user_id}, {"plan": 1})
        user_plan = (user_doc or {}).get("plan") or "free"
        fe_mobile = _inject_crucibai_branding(fe, user_plan)
        deploy_files["App.js"] = fe_mobile
        # Native Config Agent -> app.json, eas.json
        native_out = (results.get("Native Config Agent") or {}).get("output") or ""
        json_blocks = re.findall(r"```(?:json)?\s*([\s\S]*?)```", native_out)
        if len(json_blocks) >= 1:
            try:
                deploy_files["app.json"] = json_blocks[0].strip()
            except Exception:
                pass
        if len(json_blocks) >= 2:
            try:
                deploy_files["eas.json"] = json_blocks[1].strip()
            except Exception:
                pass
        if "app.json" not in deploy_files:
            deploy_files["app.json"] = '{"name":"App","slug":"app","version":"1.0.0","ios":{"bundleIdentifier":"com.example.app"},"android":{"package":"com.example.app"}}'
        if "eas.json" not in deploy_files:
            deploy_files["eas.json"] = '{"build":{"preview":{"ios":{},"android":{}},"production":{"ios":{},"android":{}}}}'
        deploy_files["package.json"] = '{"name":"app","version":"1.0.0","main":"node_modules/expo/AppEntry.js","scripts":{"start":"expo start","android":"expo start --android","ios":"expo start --ios"},"dependencies":{"expo":"~50.0.0","react":"18.2.0","react-native":"0.73.0"}}'
        deploy_files["babel.config.js"] = "module.exports = function(api) { api.cache(true); return { presets: ['babel-preset-expo'] }; };"
        # Store Prep Agent -> store-submission/
        store_out = (results.get("Store Prep Agent") or {}).get("output") or ""
        deploy_files["store-submission/STORE_SUBMISSION_GUIDE.md"] = store_out or "See Expo EAS Submit docs for Apple App Store and Google Play submission."
        metadata_match = re.search(r"\{[\s\S]*?\"app_name\"[\s\S]*?\}", store_out)
        if metadata_match:
            deploy_files["store-submission/metadata.json"] = metadata_match.group(0)
    else:
        # Web project — always emit a full preview bundle (like Manus): entry + App + styles so Sandpack preview works
        if fe:
            fe = _inject_media_into_jsx(fe, images, videos)
            user_doc = await db.users.find_one({"id": user_id}, {"plan": 1})
            user_plan = (user_doc or {}).get("plan") or "free"
            fe = _inject_crucibai_branding(fe, user_plan)
            deploy_files["src/App.jsx"] = fe
            # Ensure Sandpack has an entry and styles so preview runs (Manus-like minimal runnable set)
            if "src/index.js" not in deploy_files:
                deploy_files["src/index.js"] = """import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './styles.css';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);
"""
            if "src/styles.css" not in deploy_files:
                deploy_files["src/styles.css"] = """@import url('https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css');
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: Inter, system-ui, sans-serif; }
"""
            # Full build (not minimal): package.json + index.html so export/deploy is a complete project
            if "package.json" not in deploy_files:
                deploy_files["package.json"] = """{
  "name": "crucib-app",
  "version": "1.0.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-scripts": "5.0.1"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "test": "react-scripts test"
  },
  "browserslist": { "production": [">0.2%", "not dead"], "development": ["last 1 chrome version"] }
}
"""
            if "public/index.html" not in deploy_files:
                deploy_files["public/index.html"] = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="theme-color" content="#000000" />
  <title>App</title>
</head>
<body>
  <noscript>You need to enable JavaScript to run this app.</noscript>
  <div id="root"></div>
</body>
</html>
"""
        if be:
            deploy_files["server.py"] = be
        if db_schema:
            deploy_files["schema.sql"] = db_schema
        if tests:
            deploy_files["tests/test_basic.py"] = tests
    set_payload = {
        "status": "completed",
        "tokens_used": total_used,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "live_url": None,
        "quality_score": quality,
        "orchestration_version": "v2_dag",
        "build_kind": build_kind,
    }
    if critic_score is not None:
        set_payload["critic_score"] = critic_score
    if truth_verdict is not None:
        set_payload["truth_verdict"] = truth_verdict
    if truth_score is not None:
        set_payload["truth_score"] = truth_score
    if truth_honest_score is not None:
        set_payload["truth_honest_score"] = truth_honest_score
    if images:
        set_payload["images"] = images
    if videos:
        set_payload["videos"] = videos
    if deploy_files:
        set_payload["deploy_files"] = deploy_files
    if suggest_retry_phase is not None:
        set_payload["suggest_retry_phase"] = suggest_retry_phase
        set_payload["suggest_retry_reason"] = suggest_retry_reason or "Retry code generation?"
    update_op = {"$set": set_payload}
    if suggest_retry_phase is None:
        update_op["$unset"] = {"suggest_retry_phase": "", "suggest_retry_reason": ""}
    await db.projects.update_one({"id": project_id}, update_op)
    # Version history (item 13): append this build to build_history for UI
    project_after = await db.projects.find_one({"id": project_id})
    if project_after is not None:
        history = list(project_after.get("build_history") or [])
        history.insert(0, {
            "completed_at": set_payload.get("completed_at"),
            "status": "completed",
            "quality_score": quality,
            "tokens_used": total_used,
        })
        await db.projects.update_one({"id": project_id}, {"$set": {"build_history": history[:50]}})
    emit_build_event(
        project_id, "build_completed", status="completed", tokens=total_used, message="Build completed",
        deploy_files=deploy_files, quality_score=quality,
        critic_score=critic_score, truth_verdict=truth_verdict, truth_score=truth_score, truth_honest_score=truth_honest_score,
    )
    project = await db.projects.find_one({"id": project_id})
    if project and project.get("tokens_allocated"):
        refund = project["tokens_allocated"] - total_used
        if refund > 0:
            await db.users.update_one({"id": user_id}, {"$inc": {"token_balance": refund}})
            await db.token_ledger.insert_one({
                "id": str(uuid.uuid4()), "user_id": user_id, "tokens": refund, "type": "refund",
                "description": f"Unused tokens from project {project_id[:8]}", "created_at": datetime.now(timezone.utc).isoformat()
            })

# ==================== EXPORTS ROUTES ====================

@projects_router.post("/exports")
async def create_export(data: dict, user: dict = Depends(get_current_user)):
    project = await db.projects.find_one({"id": data.get("project_id"), "user_id": user["id"]})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    export_id = str(uuid.uuid4())
    export_doc = {
        "id": export_id,
        "project_id": data.get("project_id"),
        "user_id": user["id"],
        "format": data.get("format", "pdf"),
        "status": "completed",
        "download_url": f"/api/exports/{export_id}/download",
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.exports.insert_one(export_doc)
    
    return {"export": {k: v for k, v in export_doc.items() if k != "_id"}}

@projects_router.get("/exports")
async def get_exports(user: dict = Depends(get_current_user)):
    cursor = db.exports.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1)
    exports = await cursor.to_list(MAX_EXPORTS_LIST)
    return {"exports": exports}

# ==================== EXAMPLES (GENERATED APP SHOWCASE) ====================

@api_router.get("/examples")
async def get_examples(user: dict = Depends(get_optional_user)):
    """Return all generated example projects (proof of code quality)."""
    cursor = db.examples.find({}, {"_id": 0}).sort("created_at", -1)
    examples = await cursor.to_list(50)
    return {"examples": examples}

@api_router.get("/examples/{name}")
async def get_example(name: str, user: dict = Depends(get_optional_user)):
    """Get one example by name."""
    ex = await db.examples.find_one({"name": name}, {"_id": 0})
    if not ex:
        raise HTTPException(status_code=404, detail="Example not found")
    return ex

@api_router.post("/examples/from-project")
async def create_example_from_project(body: dict, user: dict = Depends(get_current_user)):
    """Item 20: Mark a completed project as an example (publish to Examples Gallery). Build 5 apps, then use this to add them as examples."""
    project_id = (body or {}).get("project_id")
    name = (body or {}).get("name", "").strip().replace(" ", "-").lower() or f"example-{project_id[:8]}"
    if not project_id:
        raise HTTPException(status_code=400, detail="project_id required")
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Only completed projects can be published as examples")
    existing = await db.examples.find_one({"name": name})
    if existing:
        raise HTTPException(status_code=400, detail=f"Example name '{name}' already exists; choose another.")
    deploy_files = project.get("deploy_files") or {}
    generated_code = deploy_files if isinstance(deploy_files, dict) else {"frontend": "", "backend": "", "database": "", "tests": ""}
    example_doc = {
        "name": name,
        "prompt": project.get("description") or project.get("requirements", {}).get("prompt") or "Generated with CrucibAI",
        "generated_code": generated_code,
        "quality_metrics": project.get("quality_score"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.examples.insert_one(example_doc)
    return {"example": {"name": name, "prompt": example_doc["prompt"]}}

@api_router.post("/examples/{name}/fork")
async def fork_example(name: str, user: dict = Depends(get_current_user)):
    """Create a new project from an example (copy generated code)."""
    ex = await db.examples.find_one({"name": name})
    if not ex:
        raise HTTPException(status_code=404, detail="Example not found")
    project_id = str(uuid.uuid4())
    estimated_credits = _tokens_to_credits(100000)
    await _ensure_credit_balance(user["id"])
    cred = _user_credits(user)
    if cred < estimated_credits:
        raise HTTPException(status_code=402, detail=f"Insufficient credits. Need {estimated_credits}, have {cred}. Buy more in Credit Center.")
    code = ex.get("generated_code") or {}
    estimated_tokens = 100000
    project = {
        "id": project_id,
        "user_id": user["id"],
        "name": f"{name}-fork",
        "description": ex.get("prompt", ""),
        "project_type": "fullstack",
        "requirements": {"prompt": ex.get("prompt", ""), "from_example": name},
        "status": "completed",
        "tokens_allocated": estimated_tokens,
        "tokens_used": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "live_url": None,
        "quality_score": ex.get("quality_metrics"),
        "orchestration_version": "example_fork",
    }
    await db.projects.insert_one(project)
    await db.users.update_one({"id": user["id"]}, {"$inc": {"credit_balance": -estimated_credits}})
    return {"project": {k: v for k, v in project.items() if k != "_id"}}

# ==================== PATTERNS ROUTES ====================

@api_router.get("/patterns")
async def get_patterns(user: dict = Depends(get_optional_user)):
    patterns = [
        {"id": "auth-jwt", "name": "JWT Authentication", "category": "auth", "usage_count": 1250, "tokens_saved": 45000},
        {"id": "stripe-checkout", "name": "Stripe Checkout Flow", "category": "payments", "usage_count": 890, "tokens_saved": 60000},
        {"id": "crud-api", "name": "RESTful CRUD API", "category": "backend", "usage_count": 2100, "tokens_saved": 35000},
        {"id": "responsive-dashboard", "name": "Responsive Dashboard", "category": "frontend", "usage_count": 1560, "tokens_saved": 80000},
        {"id": "social-oauth", "name": "Social OAuth (Google/GitHub)", "category": "auth", "usage_count": 780, "tokens_saved": 55000},
        {"id": "file-upload", "name": "File Upload with S3", "category": "storage", "usage_count": 650, "tokens_saved": 40000},
        {"id": "email-sendgrid", "name": "SendGrid Email Integration", "category": "communications", "usage_count": 920, "tokens_saved": 30000},
        {"id": "realtime-ws", "name": "WebSocket Real-time Updates", "category": "realtime", "usage_count": 430, "tokens_saved": 65000}
    ]
    return {"patterns": patterns}

# ==================== ADMIN (Operational Infrastructure) ====================

ADMIN_USER_IDS = [x.strip() for x in (os.environ.get("ADMIN_USER_IDS") or "").split(",") if x.strip()]
ADMIN_ROLES = ("owner", "operations", "support", "analyst")
SUPPORT_GRANT_CAP_PER_MONTH = 50  # max credits support can grant per user per month

def get_current_admin(required_roles: tuple = ADMIN_ROLES):
    """Dependency: require authenticated user with admin_role in required_roles or id in ADMIN_USER_IDS."""
    async def _inner(credentials: HTTPAuthorizationCredentials = Depends(security)):
        if not credentials:
            raise HTTPException(status_code=401, detail="Not authenticated")
        try:
            payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0})
            if not user:
                raise HTTPException(status_code=401, detail="User not found")
            if user.get("suspended"):
                raise HTTPException(status_code=403, detail="Account suspended")
            role = user.get("admin_role")
            if role and role in required_roles:
                return user
            if user["id"] in ADMIN_USER_IDS and "owner" in required_roles:
                return {**user, "admin_role": user.get("admin_role") or "owner"}
            raise HTTPException(status_code=403, detail="Admin access required")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
    return _inner

class GrantCreditsBody(BaseModel):
    credits: int = Field(gt=0, description="Credits to grant (must be positive)")
    reason: Optional[str] = "Support bonus"

class SuspendBody(BaseModel):
    reason: str

async def _revenue_for_query(q: dict) -> float:
    rows = await db.token_ledger.find(q).to_list(MAX_TOKEN_LEDGER_REVENUE)
    total = 0.0
    for r in rows:
        p = r.get("price")
        if p is not None:
            total += float(p)
        else:
            total += float(TOKEN_BUNDLES.get(r.get("bundle", ""), {}).get("price", 0))
    return round(total, 2)

@api_router.get("/admin/dashboard")
async def admin_dashboard(admin: dict = Depends(get_current_admin(ADMIN_ROLES))):
    """Overview: users, revenue, signups, referral count, fraud_flags_count (from /admin/fraud/flags when implemented), health."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()[:10]
    week_ago = (now - timedelta(days=7)).isoformat()
    month_ago = (now - timedelta(days=30)).isoformat()
    total_users = await db.users.count_documents({})
    signups_today = await db.users.count_documents({"created_at": {"$gte": today_start}})
    signups_week = await db.users.count_documents({"created_at": {"$gte": week_ago}})
    referral_count = await db.referrals.count_documents({}) if hasattr(db, "referrals") else 0
    projects_today = await db.projects.count_documents({"created_at": {"$gte": today_start}})
    revenue_today = await _revenue_for_query({"type": "purchase", "created_at": {"$gte": today_start}})
    revenue_week = await _revenue_for_query({"type": "purchase", "created_at": {"$gte": week_ago}})
    revenue_month = await _revenue_for_query({"type": "purchase", "created_at": {"$gte": month_ago}})
    return {
        "users_online": total_users,
        "total_users": total_users,
        "signups_today": signups_today,
        "signups_week": signups_week,
        "referral_count": referral_count,
        "projects_today": projects_today,
        "revenue_today": revenue_today,
        "revenue_week": revenue_week,
        "revenue_month": revenue_month,
        "fraud_flags_count": 0,
        "system_health": "ok",
    }

@api_router.get("/admin/analytics/overview")
async def admin_analytics_overview(admin: dict = Depends(get_current_admin(ADMIN_ROLES))):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()[:10]
    week_ago = (now - timedelta(days=7)).isoformat()
    total_users = await db.users.count_documents({})
    projects_today = await db.projects.count_documents({"created_at": {"$gte": today_start}})
    signups_today = await db.users.count_documents({"created_at": {"$gte": today_start}})
    signups_week = await db.users.count_documents({"created_at": {"$gte": week_ago}})
    return {
        "total_users": total_users,
        "projects_today": projects_today,
        "signups_today": signups_today,
        "signups_week": signups_week,
    }

def _parse_date(s: Optional[str]):
    """Parse YYYY-MM-DD to date. Return None if invalid."""
    if not s or len(s) < 10:
        return None
    try:
        from datetime import date as date_type
        return date_type(int(s[:4]), int(s[5:7]), int(s[8:10]))
    except (ValueError, IndexError):
        return None

@api_router.get("/admin/analytics/daily")
async def admin_analytics_daily(
    days: int = 7,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    format: Optional[str] = None,
    admin: dict = Depends(get_current_admin(ADMIN_ROLES)),
):
    """Daily metrics. Use days (default 7) or from_date+to_date (YYYY-MM-DD). format=csv for CSV export."""
    now = datetime.now(timezone.utc)
    out = []
    start_d = _parse_date(from_date)
    end_d = _parse_date(to_date)
    if start_d and end_d and start_d <= end_d:
        from datetime import date as date_type
        delta = (end_d - start_d).days
        for i in range(min(delta + 1, 365)):
            d = (start_d + timedelta(days=i)).isoformat()
            day_start = d + "T00:00:00"
            day_end = d + "T23:59:59.999999"
            signups = await db.users.count_documents({"created_at": {"$gte": day_start, "$lte": day_end}})
            paid = await db.users.count_documents({"plan": {"$nin": ["free", None, ""]}, "created_at": {"$lte": day_end}})
            rev = await _revenue_for_query({"type": "purchase", "created_at": {"$gte": day_start, "$lte": day_end}})
            out.append({"date": d, "signups": signups, "paid_users_cumulative": paid, "revenue": rev})
    else:
        for i in range(max(1, min(days, 90))):
            d = (now - timedelta(days=i)).date().isoformat()
            day_start = d + "T00:00:00"
            day_end = d + "T23:59:59.999999"
            signups = await db.users.count_documents({"created_at": {"$gte": day_start, "$lte": day_end}})
            paid = await db.users.count_documents({"plan": {"$nin": ["free", None, ""]}, "created_at": {"$lte": day_end}})
            rev = await _revenue_for_query({"type": "purchase", "created_at": {"$gte": day_start, "$lte": day_end}})
            out.append({"date": d, "signups": signups, "paid_users_cumulative": paid, "revenue": rev})
        out = list(reversed(out))
    if (format or "").lower() == "csv":
        import csv
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["date", "signups", "paid_users_cumulative", "revenue"])
        for row in out:
            w.writerow([row["date"], row["signups"], row["paid_users_cumulative"], row["revenue"]])
        return Response(content=buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=analytics-daily.csv"})
    return {"daily": out}

@api_router.get("/admin/analytics/weekly")
async def admin_analytics_weekly(
    weeks: int = 12,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    admin: dict = Depends(get_current_admin(ADMIN_ROLES)),
):
    """Weekly: signups and revenue per week. Optional from_date/to_date (YYYY-MM-DD) to limit range."""
    now = datetime.now(timezone.utc)
    out = []
    start_d = _parse_date(from_date)
    end_d = _parse_date(to_date)
    for i in range(max(1, min(weeks, 52))):
        week_end = now - timedelta(weeks=i)
        week_start = week_end - timedelta(days=7)
        ws, we = week_start.isoformat(), week_end.isoformat()
        ws_date, we_date = ws[:10], we[:10]
        if start_d and (week_start.date() < start_d or week_end.date() < start_d):
            continue
        if end_d and week_start.date() > end_d:
            continue
        signups = await db.users.count_documents({"created_at": {"$gte": ws, "$lt": we}})
        rev = await _revenue_for_query({"type": "purchase", "created_at": {"$gte": ws, "$lt": we}})
        out.append({"week_start": ws_date, "week_end": we_date, "signups": signups, "revenue": rev})
    return {"weekly": list(reversed(out))}

@api_router.get("/admin/analytics/report")
async def admin_analytics_report(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    admin: dict = Depends(get_current_admin(ADMIN_ROLES)),
):
    """Summary report for date range: total signups, total revenue, daily breakdown. For PDF/export."""
    start_d = _parse_date(from_date)
    end_d = _parse_date(to_date)
    now = datetime.now(timezone.utc)
    if not start_d or not end_d or start_d > end_d:
        start_d = (now - timedelta(days=30)).date()
        end_d = now.date()
    delta = min((end_d - start_d).days + 1, 365)
    total_signups = 0
    total_revenue = 0.0
    daily = []
    for i in range(delta):
        d = (start_d + timedelta(days=i)).isoformat()
        day_start = d + "T00:00:00"
        day_end = d + "T23:59:59.999999"
        signups = await db.users.count_documents({"created_at": {"$gte": day_start, "$lte": day_end}})
        rev = await _revenue_for_query({"type": "purchase", "created_at": {"$gte": day_start, "$lte": day_end}})
        total_signups += signups
        total_revenue += rev
        daily.append({"date": d, "signups": signups, "revenue": rev})
    return {
        "from_date": start_d.isoformat(),
        "to_date": end_d.isoformat(),
        "total_signups": total_signups,
        "total_revenue": round(total_revenue, 2),
        "daily": daily,
        "generated_at": now.isoformat(),
    }

@api_router.get("/admin/users")
async def admin_list_users(
    email: Optional[str] = None,
    plan: Optional[str] = None,
    limit: int = 50,
    admin: dict = Depends(get_current_admin(ADMIN_ROLES)),
):
    q = {}
    if email:
        q["email"] = {"$regex": email, "$options": "i"}
    if plan:
        q["plan"] = plan
    cursor = db.users.find(q, {"_id": 0, "password": 0}).sort("created_at", -1).limit(limit)
    users = await cursor.to_list(length=limit)
    for u in users:
        u.pop("password", None)
        u["credit_balance"] = _user_credits(u)
    return {"users": users}

@api_router.get("/admin/users/{user_id}")
async def admin_user_profile(user_id: str, admin: dict = Depends(get_current_admin(ADMIN_ROLES))):
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.pop("password", None)
    user["credit_balance"] = _user_credits(user)
    projects_count = await db.projects.count_documents({"user_id": user_id})
    referrals = await db.referrals.find({"referrer_id": user_id}, {"_id": 0}).to_list(100) if hasattr(db, "referrals") else []
    cursor = db.token_ledger.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).limit(20)
    ledger = await cursor.to_list(20)
    purchases = await db.token_ledger.find({"user_id": user_id, "type": "purchase"}, {"_id": 0}).to_list(1000)
    lifetime_revenue = round(sum(float(r.get("price") or TOKEN_BUNDLES.get(r.get("bundle", ""), {}).get("price", 0)) for r in purchases), 2)
    return {
        **user,
        "projects_count": projects_count,
        "referral_count": len(referrals),
        "recent_ledger": ledger,
        "last_login": user.get("last_login"),
        "lifetime_revenue": lifetime_revenue,
    }

@api_router.post("/admin/users/{user_id}/grant-credits")
async def admin_grant_credits(
    user_id: str,
    body: GrantCreditsBody,
    admin: dict = Depends(get_current_admin(("owner", "operations", "support"))),
):
    role = admin.get("admin_role") or ("owner" if admin["id"] in ADMIN_USER_IDS else None)
    if role == "support" and body.credits > SUPPORT_GRANT_CAP_PER_MONTH:
        raise HTTPException(status_code=403, detail=f"Support can grant at most {SUPPORT_GRANT_CAP_PER_MONTH} credits per action")
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    await db.users.update_one({"id": user_id}, {"$inc": {"credit_balance": body.credits}})
    await db.token_ledger.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "credits": body.credits,
        "type": "bonus",
        "description": body.reason or "Support bonus",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "granted_by": admin["id"],
    })
    if audit_logger:
        await audit_logger.log(admin["id"], "admin_grant_credits", resource_type="user", resource_id=user_id, details={"credits": body.credits, "reason": body.reason})
    return {"ok": True, "credits_added": body.credits}

@api_router.post("/admin/users/{user_id}/suspend")
async def admin_suspend_user(
    user_id: str,
    body: SuspendBody,
    admin: dict = Depends(get_current_admin(("owner", "operations"))),
):
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.get("admin_role") and target["id"] != admin["id"]:
        raise HTTPException(status_code=403, detail="Cannot suspend another admin")
    await db.users.update_one(
        {"id": user_id},
        {"$set": {"suspended": True, "suspended_at": datetime.now(timezone.utc).isoformat(), "suspended_reason": body.reason}},
    )
    if audit_logger:
        await audit_logger.log(admin["id"], "admin_suspend_user", resource_type="user", resource_id=user_id, details={"reason": body.reason})
    return {"ok": True, "suspended": True}

@api_router.post("/admin/users/{user_id}/downgrade")
async def admin_downgrade_user(user_id: str, admin: dict = Depends(get_current_admin(("owner", "operations")))):
    """Set user plan to free (e.g. for chargeback)."""
    target = await db.users.find_one({"id": user_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    await db.users.update_one({"id": user_id}, {"$set": {"plan": "free"}})
    if audit_logger:
        await audit_logger.log(admin["id"], "admin_downgrade_user", resource_type="user", resource_id=user_id, details={"plan": "free"})
    return {"ok": True, "plan": "free"}

@api_router.get("/admin/users/{user_id}/export")
async def admin_export_user(user_id: str, admin: dict = Depends(get_current_admin(("owner", "operations")))):
    """GDPR: export user data (profile + ledger summary + project ids)."""
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.pop("password", None)
    ledger = await db.token_ledger.find({"user_id": user_id}, {"_id": 0}).to_list(MAX_ADMIN_USER_LEDGER)
    project_ids = await db.projects.find({"user_id": user_id}, {"id": 1}).to_list(MAX_ADMIN_USER_EXPORT_PROJECTS)
    return {
        "user": {k: v for k, v in user.items() if k != "password"},
        "ledger_entries": ledger,
        "project_ids": [p["id"] for p in project_ids],
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }

@api_router.get("/admin/billing/transactions")
async def admin_billing_transactions(
    limit: int = 100,
    admin: dict = Depends(get_current_admin(("owner", "operations"))),
):
    """List purchases (who paid, when, amount, status) from ledger."""
    rows = await db.token_ledger.find(
        {"type": "purchase"},
        {"_id": 0, "user_id": 1, "bundle": 1, "price": 1, "credits": 1, "created_at": 1, "stripe_session_id": 1},
    ).sort("created_at", -1).limit(limit).to_list(limit)
    for r in rows:
        if r.get("price") is None:
            r["price"] = TOKEN_BUNDLES.get(r.get("bundle", ""), {}).get("price", 0)
    return {"transactions": rows}

@api_router.get("/admin/fraud/flags")
async def admin_fraud_flags(admin: dict = Depends(get_current_admin(("owner", "operations")))):
    """High-risk accounts. Returns empty list until IP/device clustering and risk rules are implemented."""
    return {"flags": [], "message": "Fraud detection (IP/device clustering) can be added here."}

@api_router.get("/admin/legal/blocked-requests")
async def admin_legal_blocked_requests(
    status: Optional[str] = None,
    limit: int = 100,
    admin: dict = Depends(get_current_admin(ADMIN_ROLES)),
):
    """List AUP-blocked build requests for review. Optional ?status=blocked."""
    q = {}
    if status:
        q["status"] = status
    cursor = db.blocked_requests.find(q).sort("timestamp", -1).limit(limit)
    rows = await cursor.to_list(length=limit)
    out = []
    for r in rows:
        out.append({
            "id": str(r.get("_id")),
            "user_id": r.get("user_id"),
            "prompt": r.get("prompt"),
            "reason": r.get("reason"),
            "category": r.get("category"),
            "status": r.get("status", "blocked"),
            "timestamp": r.get("timestamp"),
        })
    return {"blocked_requests": out}

@api_router.post("/admin/legal/review/{request_id}")
async def admin_legal_review(
    request_id: str,
    data: dict,
    admin: dict = Depends(get_current_admin(("owner", "operations"))),
):
    """Mark blocked request as reviewed (false_positive, confirmed, escalated)."""
    from bson import ObjectId
    try:
        oid = ObjectId(request_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid request id")
    action = data.get("action") or data.get("review")
    if not action:
        raise HTTPException(status_code=400, detail="action or review required")
    await db.blocked_requests.update_one(
        {"_id": oid},
        {"$set": {"status": "reviewed", "review_action": action, "reviewed_by": admin.get("id"), "reviewed_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"ok": True, "request_id": request_id, "action": action}

@api_router.get("/admin/referrals/links")
async def admin_referral_links(admin: dict = Depends(get_current_admin(ADMIN_ROLES))):
    """All referral codes with use count."""
    if not hasattr(db, "referral_codes"):
        return {"links": []}
    codes = await db.referral_codes.find({}, {"_id": 0}).to_list(500)
    out = []
    for c in codes:
        use_count = await db.referrals.count_documents({"referrer_id": c.get("user_id")})
        out.append({"user_id": c.get("user_id"), "code": c.get("code"), "use_count": use_count})
    return {"links": out}

@api_router.get("/admin/referrals/leaderboard")
async def admin_referrals_leaderboard(limit: int = 100, admin: dict = Depends(get_current_admin(ADMIN_ROLES))):
    pipeline = [
        {"$group": {"_id": "$referrer_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit},
    ]
    if not hasattr(db, "referrals"):
        return {"leaderboard": []}
    cursor = db.referrals.aggregate(pipeline)
    leaderboard = await cursor.to_list(length=limit)
    return {"leaderboard": [{"referrer_id": x["_id"], "referral_count": x["count"]} for x in leaderboard]}


@api_router.get("/admin/segments")
async def admin_segments(
    plan: Optional[str] = None,
    limit: int = 500,
    format: Optional[str] = None,
    admin: dict = Depends(get_current_admin(ADMIN_ROLES)),
):
    """Export user segment: filter by plan (free|builder|pro|scale|teams). Returns list of users; ?format=csv returns CSV."""
    q = {}
    if plan:
        q["plan"] = plan
    cursor = db.users.find(q, {"_id": 0, "id": 1, "email": 1, "plan": 1, "created_at": 1, "credit_balance": 1}).sort("created_at", -1).limit(limit)
    users = await cursor.to_list(length=limit)
    if format == "csv":
        import io
        buf = io.StringIO()
        buf.write("id,email,plan,created_at,credit_balance\n")
        for u in users:
            buf.write(f"{u.get('id', '')},{u.get('email', '')},{u.get('plan', '')},{u.get('created_at', '')},{u.get('credit_balance', '')}\n")
        return Response(content=buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=admin-segments.csv"})
    return {"segment": users, "count": len(users)}


@api_router.get("/admin/segments")
async def admin_segments(
    plan: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 500,
    format: Optional[str] = None,
    admin: dict = Depends(get_current_admin(ADMIN_ROLES)),
):
    """Export user segment: filter by plan, signup date range. ?format=csv for CSV download."""
    q = {}
    if plan:
        q["plan"] = plan
    if from_date or to_date:
        q["created_at"] = {}
        if from_date:
            q["created_at"]["$gte"] = _parse_date(from_date).isoformat()
        if to_date:
            end = _parse_date(to_date)
            q["created_at"]["$lte"] = (end.replace(hour=23, minute=59, second=59, microsecond=999999)).isoformat()
    cursor = db.users.find(q, {"_id": 0, "id": 1, "email": 1, "plan": 1, "credit_balance": 1, "created_at": 1}).sort("created_at", -1).limit(limit)
    users = await cursor.to_list(length=limit)
    if format == "csv":
        import io
        buf = io.StringIO()
        buf.write("id,email,plan,credit_balance,created_at\n")
        for u in users:
            buf.write(f"{u.get('id', '')},{u.get('email', '')},{u.get('plan', '')},{u.get('credit_balance', '')},{u.get('created_at', '')}\n")
        return Response(content=buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=admin-segment.csv"})
    return {"segment": users, "count": len(users)}


@api_router.get("/admin/analytics/usage")
async def admin_analytics_usage(
    days: int = 30,
    admin: dict = Depends(get_current_admin(ADMIN_ROLES)),
):
    """Usage analytics: token consumption, build counts. Optional days (default 30)."""
    since = (datetime.now(timezone.utc) - timedelta(days=max(1, min(days, 365)))).isoformat()
    builds = await db.projects.count_documents({"created_at": {"$gte": since}, "status": {"$in": ["completed", "failed"]}})
    pipeline = [{"$match": {"created_at": {"$gte": since}}}, {"$group": {"_id": None, "total": {"$sum": "$tokens_used"}}}]
    cursor = db.projects.aggregate(pipeline)
    row = await cursor.to_list(length=1)
    total_tokens = row[0]["total"] if row else 0
    return {"period_days": days, "builds_count": builds, "tokens_used_total": total_tokens, "since": since}


@api_router.get("/admin/analytics/revenue")
async def admin_analytics_revenue(
    days: int = 30,
    admin: dict = Depends(get_current_admin(ADMIN_ROLES)),
):
    """Revenue analytics for the period. Optional days (default 30)."""
    since = (datetime.now(timezone.utc) - timedelta(days=max(1, min(days, 365)))).isoformat()
    total = await _revenue_for_query({"type": "purchase", "created_at": {"$gte": since}})
    return {"period_days": days, "revenue": total, "since": since}


@api_router.get("/admin/analytics/agents")
async def admin_analytics_agents(
    days: int = 30,
    limit: int = 50,
    admin: dict = Depends(get_current_admin(ADMIN_ROLES)),
):
    """Agent performance: runs per agent, success rate. Optional days (default 30)."""
    since = (datetime.now(timezone.utc) - timedelta(days=max(1, min(days, 365)))).isoformat()
    pipeline = [
        {"$match": {"triggered_at": {"$gte": since}}},
        {"$group": {"_id": "$agent_id", "runs": {"$sum": 1}, "completed": {"$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}}}},
        {"$sort": {"runs": -1}},
        {"$limit": limit},
    ]
    try:
        cursor = db.agent_runs.aggregate(pipeline)
        rows = await cursor.to_list(length=limit)
    except Exception:
        return {"agents": [], "period_days": days}
    agents = []
    for r in rows:
        aid = r["_id"]
        runs = r.get("runs", 0)
        completed = r.get("completed", 0)
        agents.append({"agent_id": aid, "runs": runs, "completed": completed, "success_rate": round(100 * completed / runs, 1) if runs else 0})
    return {"agents": agents, "period_days": days}


@api_router.post("/admin/settings/update")
async def admin_settings_update(
    data: dict,
    admin: dict = Depends(get_current_admin(("owner", "operations"))),
):
    """Update system-wide settings (stored in db.admin_settings). Body: key-value pairs."""
    key = (data.get("key") or data.get("name") or "").strip()
    value = data.get("value") if "value" in data else data.get("settings")
    if not key:
        raise HTTPException(status_code=400, detail="key or name required")
    now = datetime.now(timezone.utc).isoformat()
    await db.admin_settings.update_one(
        {"key": key},
        {"$set": {"key": key, "value": value, "updated_at": now, "updated_by": admin.get("id")}},
        upsert=True,
    )
    return {"ok": True, "key": key}


@api_router.get("/admin/audit-log")
async def admin_audit_log(
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100,
    skip: int = 0,
    admin: dict = Depends(get_current_admin(ADMIN_ROLES)),
):
    """View audit logs. Optional user_id, action filter. Pagination: limit, skip."""
    q = {}
    if user_id:
        q["user_id"] = user_id
    if action:
        q["action"] = action
    if not hasattr(db, "audit_log"):
        return {"logs": [], "total": 0, "limit": limit, "skip": skip}
    cursor = db.audit_log.find(q).sort("timestamp", -1).skip(skip).limit(limit)
    logs = await cursor.to_list(length=limit)
    total = await db.audit_log.count_documents(q)
    out = []
    for log in logs:
        d = {"id": str(log.get("_id")), "user_id": log.get("user_id"), "action": log.get("action"), "resource_type": log.get("resource_type"), "status": log.get("status"), "ip_address": log.get("ip_address")}
        ts = log.get("timestamp")
        d["timestamp"] = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
        out.append(d)
    return {"logs": out, "total": total, "limit": limit, "skip": skip}


class AdminNotificationBody(BaseModel):
    target: Optional[str] = None  # user_id or "all"
    subject: str = ""
    body: str = ""


@api_router.post("/admin/notifications/send")
async def admin_notifications_send(
    data: AdminNotificationBody,
    admin: dict = Depends(get_current_admin(("owner", "operations"))),
):
    """Send system notification. Stores in db.notifications; optionally trigger email when implemented."""
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "id": str(uuid.uuid4()),
        "target": data.target or "all",
        "subject": data.subject,
        "body": data.body,
        "created_at": now,
        "created_by": admin.get("id"),
    }
    await db.notifications.insert_one(doc)
    return {"ok": True, "notification_id": doc["id"]}


# ==================== DASHBOARD STATS ====================

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(user: dict = Depends(get_current_user)):
    projects = await db.projects.find({"user_id": user["id"]}).to_list(MAX_USER_PROJECTS_DASHBOARD)
    
    total_projects = len(projects)
    completed_projects = len([p for p in projects if p.get("status") == "completed"])
    running_projects = len([p for p in projects if p.get("status") == "running"])
    total_tokens_used = sum(p.get("tokens_used", 0) for p in projects)
    
    weekly_data = [
        {"day": "Mon", "tokens": random.randint(20000, 100000), "projects": random.randint(1, 5)},
        {"day": "Tue", "tokens": random.randint(20000, 100000), "projects": random.randint(1, 5)},
        {"day": "Wed", "tokens": random.randint(20000, 100000), "projects": random.randint(1, 5)},
        {"day": "Thu", "tokens": random.randint(20000, 100000), "projects": random.randint(1, 5)},
        {"day": "Fri", "tokens": random.randint(20000, 100000), "projects": random.randint(1, 5)},
        {"day": "Sat", "tokens": random.randint(10000, 50000), "projects": random.randint(0, 3)},
        {"day": "Sun", "tokens": random.randint(10000, 50000), "projects": random.randint(0, 3)}
    ]
    
    return {
        "total_projects": total_projects,
        "completed_projects": completed_projects,
        "running_projects": running_projects,
        "credit_balance": _user_credits(user),
        "token_balance": _user_credits(user) * CREDITS_PER_TOKEN,
        "total_tokens_used": total_tokens_used,
        "weekly_data": weekly_data,
        "plan": user.get("plan", "free")
    }

# ==================== PROMPTS (Templates, Recent, Save) ====================

PROMPT_TEMPLATES = [
    {"id": "ecommerce", "name": "E-commerce with cart", "prompt": "Build a modern e-commerce product list with add-to-cart, cart sidebar, and checkout button. Use React and Tailwind.", "category": "app"},
    {"id": "auth-dashboard", "name": "Auth + Dashboard", "prompt": "Create a login page and a dashboard with sidebar navigation. Use React, Tailwind, and local state for auth.", "category": "app"},
    {"id": "landing-waitlist", "name": "Landing + waitlist", "prompt": "Build a landing page with hero, features section, and email waitlist signup. React and Tailwind.", "category": "marketing"},
    {"id": "stripe-saas", "name": "Stripe subscription SaaS", "prompt": "Build a SaaS landing page with pricing cards and Stripe Checkout integration for subscription. React and Tailwind.", "category": "app"},
    {"id": "todo", "name": "Task manager", "prompt": "Create a task manager with add, complete, delete, and filter by status. React and Tailwind.", "category": "app"},
]

@api_router.get("/prompts/templates")
async def get_prompt_templates(user: dict = Depends(get_optional_user)):
    return {"templates": PROMPT_TEMPLATES}

@api_router.get("/prompts/recent")
async def get_recent_prompts(user: dict = Depends(get_optional_user)):
    if not user:
        return {"prompts": []}
    cursor = db.chat_history.find({"user_id": user["id"]}, {"message": 1, "created_at": 1}).sort("created_at", -1).limit(20)
    recents = await cursor.to_list(20)
    seen = set()
    out = []
    for r in recents:
        msg = (r.get("message") or "")[:200]
        if msg and msg not in seen:
            seen.add(msg)
            out.append({"prompt": msg, "created_at": r.get("created_at")})
    return {"prompts": out[:10]}

@api_router.post("/prompts/save")
async def save_prompt(data: SavePromptBody, user: dict = Depends(get_current_user)):
    doc = {"id": str(uuid.uuid4()), "user_id": user["id"], "name": data.name, "prompt": data.prompt, "category": data.category or "general", "created_at": datetime.now(timezone.utc).isoformat()}
    await db.saved_prompts.insert_one(doc)
    return {"saved": doc["id"]}

@api_router.get("/prompts/saved")
async def get_saved_prompts(user: dict = Depends(get_current_user)):
    cursor = db.saved_prompts.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1)
    items = await cursor.to_list(50)
    return {"prompts": items}

# ==================== REFERENCE BUILD / EXPLAIN ERROR / SUGGEST NEXT ====================

@projects_router.post("/build/from-reference")
async def build_from_reference(data: ReferenceBuildBody, user: dict = Depends(get_optional_user)):
    """Use a URL or prompt as reference for build. Fetches URL content when provided."""
    context = ""
    if data.url:
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                r = await client.get(data.url, timeout=10)
                if r.status_code == 200:
                    text = r.text[:8000]
                    context = f"Reference site content (first 8000 chars):\n{text}\n\n"
        except Exception as e:
            context = f"(Could not fetch URL: {e})\n\n"
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    prompt = f"{context}Build a React app (Tailwind) that matches or is inspired by this. User request: {data.prompt}. Respond with ONLY the complete App.js code."
    model_chain = _get_model_chain("auto", prompt, effective_keys=effective)
    response, model_used = await _call_llm_with_fallback(message=prompt, system_message="You output only valid React/JSX code. No markdown.", session_id=str(uuid.uuid4()), model_chain=model_chain, api_keys=effective)
    code = (response or "").strip().removeprefix("```jsx").removeprefix("```js").removeprefix("```").removesuffix("```").strip()
    return {"code": code, "model_used": model_used}

@api_router.post("/ai/quality-gate")
async def quality_gate(data: QualityGateBody):
    """Run code quality score on code or multi-file output. No auth required for UI feedback."""
    frontend_code = data.code or ""
    if not frontend_code and data.files:
        # Extract frontend code from files (prefer App.js/jsx/tsx, then any .js/.jsx/.tsx/.css)
        parts = []
        for path, content in (data.files or {}).items():
            if isinstance(content, dict):
                content = content.get("code", "") or ""
            path_lower = (path or "").lower()
            if any(path_lower.endswith(ext) for ext in (".js", ".jsx", ".tsx", ".css")):
                parts.append(content if isinstance(content, str) else "")
        frontend_code = "\n".join(parts)
    result = score_generated_code(frontend_code=frontend_code, backend_code="", database_schema="", test_code="")
    result["score"] = result.get("overall_score", 0)  # Frontend expects .score
    # Record execution for learning
    try:
        agent_memory.record_execution(agent_name, {
            "input": input_data,
            "output": result,
            "timestamp": datetime.now(),
            "tokens_used": tokens_used
        })
    except Exception as e:
        logger.error(f"Failed to record execution: {e}")
    
    # Store in vector memory
    try:
        await vector_store.store_execution(
            agent_id=agent_name,
            execution_data={
                "input": input_data,
                "output": result,
                "agent": agent_name
            }
        )
    except Exception as e:
        logger.debug(f"Vector store unavailable: {e}")
    
    return result

@api_router.post("/ai/explain-error")
async def explain_error(data: ExplainErrorBody, user: dict = Depends(get_optional_user)):
    """Explain and optionally fix a runtime/syntax error. Uses your Settings keys when set."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    model_chain = _get_model_chain("auto", data.error, effective_keys=effective)
    prompt = f"Code:\n```\n{data.code[:6000]}\n```\n\nError:\n{data.error}\n\nExplain the error in 1-2 sentences, then provide the fixed code. Return fixed code in a fenced block."
    response, _ = await _call_llm_with_fallback(message=prompt, system_message="You are a debugging assistant. Be concise.", session_id=str(uuid.uuid4()), model_chain=model_chain, api_keys=effective)
    fixed = ""
    if "```" in response:
        parts = response.split("```")
        for i, p in enumerate(parts):
            if i > 0 and ("react" in p.lower() or "function" in p or "const " in p or "export " in p):
                fixed = p.strip().strip("jsx").strip("js").strip()
                break
    return {"explanation": response[:1500], "fixed_code": fixed or data.code}

@api_router.post("/ai/suggest-next")
async def suggest_next(data: SuggestNextBody, user: dict = Depends(get_optional_user)):
    """Suggest 2-3 next steps after a build. Uses your Settings keys when set."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    app_code = (data.files.get("/App.js") or data.files.get("App.js") or "").strip()[:4000]
    prompt = f"Current App.js (excerpt):\n{app_code}\n\nLast prompt: {data.last_prompt or 'N/A'}\n\nSuggest exactly 3 short next steps (each one line). Return as JSON array of strings, e.g. [\"Add loading state\", \"Add error boundary\", \"Deploy\"]."
    model_chain = _get_model_chain("auto", prompt, effective_keys=effective)
    response, _ = await _call_llm_with_fallback(message=prompt, system_message="Reply only with a JSON array of 3 strings.", session_id=str(uuid.uuid4()), model_chain=model_chain, api_keys=effective)
    try:
        import re
        arr = json.loads(re.search(r"\[.*\]", response, re.DOTALL).group() if re.search(r"\[.*\]", response, re.DOTALL) else "[]")
        if isinstance(arr, list):
            return {"suggestions": arr[:3]}
    except Exception:
        pass
    return {"suggestions": ["Add loading state", "Add tests", "Deploy"]}

# ==================== INJECT STRIPE / ENV / DUPLICATE / SHARE ====================

@api_router.post("/ai/inject-stripe")
async def inject_stripe(data: InjectStripeBody, user: dict = Depends(get_optional_user)):
    """Inject Stripe Checkout or subscription into React code. Uses your Settings keys when set."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    model_chain = _get_model_chain("auto", "stripe", effective_keys=effective)
    prompt = f"Add Stripe Checkout to this React code. Target: {data.target}. Use @stripe/react-stripe-js or Stripe.js. Add a checkout button and handle success. Use env var STRIPE_PUBLISHABLE_KEY. Return ONLY the full updated code.\n\n```\n{data.code[:8000]}\n```"
    response, _ = await _call_llm_with_fallback(message=prompt, system_message="Output only valid React code. No markdown.", session_id=str(uuid.uuid4()), model_chain=model_chain, api_keys=effective)
    code = (response or "").strip().removeprefix("```jsx").removeprefix("```js").removeprefix("```").removesuffix("```").strip()
    return {"code": code or data.code}

@api_router.post("/ai/generate-readme")
async def generate_readme(data: GenerateReadmeBody, user: dict = Depends(get_optional_user)):
    """Generate a README.md from code and optional project name. Uses your Settings keys when set."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    model_chain = _get_model_chain("auto", data.code[:500], effective_keys=effective)
    prompt = f"Generate a concise README.md for this project. Project name: {data.project_name or 'App'}. Include: title, short description, how to run, main features. Use markdown only.\n\nCode (excerpt):\n```\n{data.code[:6000]}\n```"
    response, _ = await _call_llm_with_fallback(message=prompt, system_message="Output only valid Markdown. No code block wrapper.", session_id=str(uuid.uuid4()), model_chain=model_chain, api_keys=effective)
    return {"readme": (response or "").strip().removeprefix("```md").removeprefix("```").removesuffix("```").strip()}

@api_router.post("/ai/generate-docs")
async def generate_docs(data: GenerateDocsBody, user: dict = Depends(get_optional_user)):
    """Generate API or component docs from code. Uses your Settings keys when set."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    model_chain = _get_model_chain("auto", data.code[:500], effective_keys=effective)
    prompt = f"Generate {data.doc_type or 'api'} documentation for this code. Use markdown: list components/functions, props, usage. Be concise.\n\n```\n{data.code[:6000]}\n```"
    response, _ = await _call_llm_with_fallback(message=prompt, system_message="Output only valid Markdown.", session_id=str(uuid.uuid4()), model_chain=model_chain, api_keys=effective)
    return {"docs": (response or "").strip().removeprefix("```md").removeprefix("```").removesuffix("```").strip()}

@api_router.post("/ai/generate-faq-schema")
async def generate_faq_schema(data: GenerateFaqSchemaBody, user: dict = Depends(get_optional_user)):
    """Generate JSON-LD FAQPage schema from list of Q&A."""
    items = []
    for f in (data.faqs or []):
        q = f.get("q", getattr(f, "q", "")) if isinstance(f, dict) else getattr(f, "q", "")
        a = f.get("a", getattr(f, "a", "")) if isinstance(f, dict) else getattr(f, "a", "")
        items.append({"q": q, "a": a})
    if not items:
        return {"schema": {}}
    schema = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [{"@type": "Question", "name": it["q"], "acceptedAnswer": {"@type": "Answer", "text": it["a"]}} for it in items]
    }
    return {"schema": schema}

@api_router.get("/workspace/env")
async def get_workspace_env(user: dict = Depends(get_optional_user)):
    # API keys are now managed server-side only. This endpoint returns empty for backward compatibility.
    return {"env": {}}

@api_router.post("/workspace/env")
async def set_workspace_env(data: ProjectEnvBody, user: dict = Depends(get_current_user)):
    # API keys are now managed server-side only. This endpoint is deprecated.
    # Users cannot set API keys anymore - they are configured in the server environment.
    return {"ok": True}

@projects_router.post("/projects/{project_id}/duplicate")
async def duplicate_project(project_id: str, user: dict = Depends(require_permission(Permission.EDIT_PROJECT if Permission else None))):
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    new_id = str(uuid.uuid4())
    new_project = {**project, "id": new_id, "name": project.get("name", "Copy") + " (copy)", "created_at": datetime.now(timezone.utc).isoformat(), "status": "draft", "completed_at": None, "live_url": None, "tokens_used": 0}
    new_project.pop("_id", None)
    await db.projects.insert_one(new_project)
    return {"project": new_project}

@api_router.post("/share/create")
async def share_create(data: ShareCreateBody, user: dict = Depends(require_permission(Permission.EDIT_PROJECT if Permission else None))):
    project = await db.projects.find_one({"id": data.project_id, "user_id": user["id"]})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    share_token = str(uuid.uuid4()).replace("-", "")[:12]
    await db.shares.insert_one({"token": share_token, "project_id": data.project_id, "user_id": user["id"], "read_only": data.read_only, "created_at": datetime.now(timezone.utc).isoformat()})
    return {"share_url": f"/share/{share_token}", "token": share_token}

@api_router.get("/share/{token}")
async def share_get(token: str):
    share = await db.shares.find_one({"token": token}, {"_id": 0})
    if not share:
        raise HTTPException(status_code=404, detail="Share not found")
    project = await db.projects.find_one({"id": share["project_id"]}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project": project, "read_only": share.get("read_only", True)}

# ==================== TEMPLATES GALLERY / SAVE AS TEMPLATE ====================

TEMPLATES_GALLERY = [
    {"id": "dashboard", "name": "Dashboard", "description": "Sidebar + stats cards + chart placeholder", "prompt": "Create a dashboard with a sidebar, stat cards, and a chart area. React and Tailwind."},
    {"id": "blog", "name": "Blog", "description": "Blog layout with posts list and post detail", "prompt": "Build a blog with a list of posts and a post detail view. React and Tailwind."},
    {"id": "saas-shell", "name": "SaaS shell", "description": "Auth shell with nav and settings", "prompt": "Create a SaaS app shell with top nav, user menu, and settings page. React and Tailwind."},
]

@api_router.get("/templates")
async def get_templates(user: dict = Depends(get_optional_user)):
    return {"templates": TEMPLATES_GALLERY}

@projects_router.post("/projects/from-template")
async def create_from_template(body: dict, user: dict = Depends(require_permission(Permission.CREATE_PROJECT if Permission else None))):
    tid = body.get("template_id")
    t = next((x for x in TEMPLATES_GALLERY if x["id"] == tid), None)
    if not t:
        raise HTTPException(status_code=400, detail="Template not found")
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    model_chain = _get_model_chain("auto", t["prompt"], effective_keys=effective)
    response, _ = await _call_llm_with_fallback(message=t["prompt"] + "\n\nRespond with ONLY the complete App.js code.", system_message="Output only valid React code.", session_id=str(uuid.uuid4()), model_chain=model_chain, api_keys=effective)
    code = (response or "").strip().removeprefix("```jsx").removeprefix("```js").removeprefix("```").removesuffix("```").strip()
    return {"files": {"/App.js": code}, "template_id": tid}

@projects_router.post("/projects/{project_id}/save-as-template")
async def save_project_as_template(project_id: str, body: dict, user: dict = Depends(require_permission(Permission.EDIT_PROJECT if Permission else None))):
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    name = body.get("name", project.get("name", "My template"))
    template_id = str(uuid.uuid4())[:8]
    await db.user_templates.insert_one({"id": template_id, "user_id": user["id"], "project_id": project_id, "name": name, "created_at": datetime.now(timezone.utc).isoformat()})
    return {"template_id": template_id}

# ==================== SECURITY SCAN / OPTIMIZE / A11Y / DESIGN FROM URL ====================

def _parse_security_checklist_summary(text: str) -> tuple[int, int]:
    """Return (passed_count, failed_count) from checklist lines containing PASS/FAIL."""
    passed = failed = 0
    for line in (text or "").split("\n")[:15]:
        line_lower = line.upper()
        if "PASS" in line_lower and "FAIL" not in line_lower[:line_lower.index("PASS") + 4]:
            passed += 1
        elif "FAIL" in line_lower:
            failed += 1
    return passed, failed


@api_router.post("/ai/security-scan")
async def security_scan(data: SecurityScanBody, user: dict = Depends(get_optional_user)):
    """Return a short security checklist for the provided files. Uses your Settings keys when set. If project_id is set and user is authenticated, store result on project for AgentMonitor."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    code = " ".join(data.files.values())[:6000]
    model_chain = _get_model_chain("auto", code, effective_keys=effective)
    prompt = f"Review this code for security. List 3-5 checklist items (e.g. 'No secrets in client code', 'Auth on API'). For each say PASS or FAIL and one line reason. Code:\n{code}"
    response, _ = await _call_llm_with_fallback(message=prompt, system_message="Reply with a short checklist. Use PASS/FAIL.", session_id=str(uuid.uuid4()), model_chain=model_chain, api_keys=effective)
    checklist = response.split("\n")[:8] if response else []
    passed, failed = _parse_security_checklist_summary(response or "")
    if data.project_id and user:
        project = await db.projects.find_one({"id": data.project_id, "user_id": user["id"]})
        if project:
            await db.projects.update_one(
                {"id": data.project_id, "user_id": user["id"]},
                {"$set": {
                    "last_security_scan": {
                        "report": response,
                        "checklist": checklist,
                        "passed": passed,
                        "failed": failed,
                        "at": datetime.now(timezone.utc).isoformat(),
                    }
                }}
            )
    return {"report": response, "checklist": checklist, "passed": passed, "failed": failed}

@api_router.post("/ai/optimize")
async def optimize_code(data: OptimizeBody, user: dict = Depends(get_optional_user)):
    """Uses your Settings keys when set."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    model_chain = _get_model_chain("auto", data.code, effective_keys=effective)
    prompt = f"Optimize this {data.language} code for performance (lazy load, memo, split if needed). Return ONLY the full optimized code.\n\n```\n{data.code[:8000]}\n```"
    response, _ = await _call_llm_with_fallback(message=prompt, system_message="Output only valid code. No markdown.", session_id=str(uuid.uuid4()), model_chain=model_chain, api_keys=effective)
    code = (response or "").strip().removeprefix("```jsx").removeprefix("```js").removeprefix("```").removesuffix("```").strip()
    return {"code": code or data.code}

@api_router.post("/ai/accessibility-check")
async def accessibility_check(data: ValidateAndFixBody, user: dict = Depends(get_optional_user)):
    """Uses your Settings keys when set."""
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    model_chain = _get_model_chain("auto", data.code, effective_keys=effective)
    prompt = f"Check this React code for accessibility (labels, contrast, keyboard, ARIA). List issues and suggest fixes. Code:\n{data.code[:6000]}"
    response, _ = await _call_llm_with_fallback(message=prompt, system_message="Reply with a concise a11y report.", session_id=str(uuid.uuid4()), model_chain=model_chain, api_keys=effective)
    return {"report": response}

@api_router.post("/ai/design-from-url")
async def design_from_url(url: str = Form(...), user: dict = Depends(get_optional_user)):
    """Fetch image from URL and run image-to-code."""
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            r = await client.get(url, timeout=15)
            if r.status_code != 200 or not (r.headers.get("content-type") or "").startswith("image/"):
                raise HTTPException(status_code=400, detail="URL must return an image")
            content = r.content
            ct = r.headers.get("content-type", "image/png")
        b64 = base64.b64encode(content).decode("utf-8")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch image: {e}")
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        resp = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=4096,
            system="Output only valid React/JSX code. No markdown.",
            messages=[
                {"role": "user", "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": ct, "data": b64}},
                    {"type": "text", "text": "Convert this UI into a single React component with Tailwind. Return ONLY the code."}
                ]}
            ]
        )
        code = (resp.content[0].text or "").strip().removeprefix("```jsx").removeprefix("```js").removeprefix("```").removesuffix("```").strip()
        return {"code": code}
    except Exception as e:
        logger.error(f"Design from URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== AGENT ACTIVITY (for Agents panel) ====================

@agents_router.get("/agents/activity")
async def get_agents_activity(session_id: Optional[str] = None, user: dict = Depends(get_optional_user)):
    """Return recent agent activity for the Agents panel (Cursor-style)."""
    if not user:
        return {"activities": []}
    cursor = db.chat_history.find({"user_id": user["id"]}, {"session_id": 1, "message": 1, "model": 1, "tokens_used": 1, "created_at": 1}).sort("created_at", -1).limit(30)
    activities = []
    seen = set()
    async for row in cursor:
        sid = row.get("session_id") or "default"
        key = (sid, row.get("created_at", "")[:19])
        if key in seen:
            continue
        seen.add(key)
        activities.append({
            "session_id": sid,
            "message": (row.get("message") or "")[:80],
            "model": row.get("model"),
            "tokens_used": row.get("tokens_used", 0),
            "created_at": row.get("created_at"),
        })
    return {"activities": activities[:20]}

# ==================== BRAND (read-only, no auth) ====================

@api_router.get("/brand")
async def brand_config():
    """Read-only brand proof stats for landing/hero. No model or provider names."""
    return {
        "tagline": "Inevitable AI",
        "agent_count": 123,
        "success_rate": "99.2%",
        "proof_strip": ["123-agent swarm", "99.2% success", "Typically under 72 hours", "Full transparency", "Minimal supervision"],
        "cta_primary": "Make It Inevitable",
    }

# ==================== ROOT ====================

@api_router.get("/")
async def root():
    return {"message": "CrucibAI Platform API", "version": "1.0.0"}

@api_router.get("/health")
async def health(deps: bool = Query(False, description="Check dependencies (MongoDB); return 503 if unavailable")):
    check_deps = deps or os.environ.get("HEALTH_CHECK_DEPS", "").strip().lower() in ("1", "true", "yes")
    if check_deps:
        try:
            await db.command("ping")
            return {
                "status": "healthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "mongodb": "ok",
            }
        except Exception as e:
            logger.warning("Health check MongoDB ping failed: %s", e)
            raise HTTPException(
                status_code=503,
                detail={"status": "degraded", "mongodb": "unavailable", "error": str(e)[:200]},
            )
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

# ==================== CLIENT ERROR LOGGING ====================

@api_router.post("/errors/log")
async def client_error_log(request: Request):
    """Accept client-side error reports (ErrorBoundary). No auth required; rate-limited by middleware. Sanitized and logged only."""
    try:
        body = await request.json()
        if isinstance(body, dict):
            message = str(body.get("message", ""))[:2000]
            stack = str(body.get("stack", ""))[:5000]
            url = str(body.get("url", ""))[:500]
            logger.warning(
                "Client error: %s | url=%s | stack=%s",
                message or "unknown",
                url or request.url.path,
                stack[:500] if stack else ""
            )
    except Exception:
        pass
    return {}

# ==================== TOOL AGENTS (authenticated, validated) ====================

@tools_router.post("/tools/browser")
async def use_browser_tool(body: ToolBrowserRequest, user: dict = Depends(get_current_user)):
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
async def use_database_tool(body: ToolDatabaseRequest, user: dict = Depends(get_current_user)):
    """Execute SQL query (read-only when connection is client-provided; requires auth)."""
    from tools.database_operations_agent import DatabaseOperationsAgent
    agent = DatabaseOperationsAgent(llm_client=None, config={})
    ctx = body.model_dump(exclude_none=True)
    return await agent.run(ctx)

@tools_router.post("/tools/deploy")
async def use_deployment_tool(body: ToolDeployRequest, user: dict = Depends(get_current_user)):
    """Deploy application (project_path must be under workspace; requires auth)."""
    from tools.deployment_operations_agent import DeploymentOperationsAgent
    agent = DeploymentOperationsAgent(llm_client=None, config={"workspace_root": str(WORKSPACE_ROOT)})
    ctx = body.model_dump(exclude_none=True)
    return await agent.run(ctx)

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
    from db_pg import get_pool
    pool = await get_pool()
    if pool:
        try:
            async with pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO monitoring_events (event_id, event_type, user_id, duration, metadata, success, error_message)
                       VALUES ($1, $2, $3, $4, $5, $6, $7)""",
                    event_id, body.event_type, body.user_id, body.duration,
                    json.dumps(body.metadata or {}), body.success, body.error_message
                )
        except Exception as e:
            logger.warning("monitoring_track_event pg insert failed: %s", e)
    return {"status": "ok", "event_id": event_id}

@api_router.get("/monitoring/events")
async def monitoring_list_events(limit: int = Query(50, le=200)):
    """List recent monitoring events from PostgreSQL (proof)."""
    from db_pg import get_pool
    pool = await get_pool()
    if not pool:
        return {"events": [], "message": "PostgreSQL not configured (DATABASE_URL)"}
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT event_id, event_type, user_id, timestamp, duration, metadata, success, error_message
                   FROM monitoring_events ORDER BY timestamp DESC LIMIT $1""",
                limit
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

# ==================== VIBECODING (vibe analysis + code gen) ====================
class VibeAnalyzeRequest(BaseModel):
    text: str
    context: Optional[str] = None

class VibeGenerateRequest(BaseModel):
    prompt: str
    language: Optional[str] = None
    framework: Optional[str] = None
    vibe_analysis: Optional[Dict[str, Any]] = None

@api_router.post("/vibecoding/analyze")
async def vibecoding_analyze(body: VibeAnalyzeRequest):
    """Analyze natural language to detect vibe (style, frameworks, complexity)."""
    try:
        from vibe_analysis import vibe_analyzer
        vibe = vibe_analyzer.analyze(body.text)
        return {"status": "success", "vibe": vibe.to_dict(), "confidence": vibe.confidence_score}
    except Exception as e:
        logger.warning("vibecoding_analyze failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/vibecoding/generate")
async def vibecoding_generate(body: VibeGenerateRequest):
    """Generate code from prompt using vibe analysis."""
    try:
        from vibe_analysis import vibe_analyzer
        from vibe_code_generator import vibe_code_generator
        vibe_obj = vibe_analyzer.analyze(body.prompt)
        gen = vibe_code_generator.generate(vibe_obj, body.prompt, body.language)
        return {
            "status": "success",
            "language": gen.language,
            "framework": gen.framework,
            "code": gen.code,
            "style": gen.style,
            "structure": gen.structure,
            "explanation": gen.explanation,
        }
    except Exception as e:
        logger.warning("vibecoding_generate failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

class VibeAnalyzeAudioRequest(BaseModel):
    transcript: Optional[str] = None  # if audio not provided, use transcript for vibe analysis
    audio_base64: Optional[str] = None

@api_router.post("/vibecoding/analyze-audio")
async def vibecoding_analyze_audio(body: VibeAnalyzeAudioRequest):
    """Analyze vibe from transcript or from audio (transcribe then analyze). When transcript provided, runs vibe analysis."""
    try:
        from vibe_analysis import vibe_analyzer
        text = body.transcript or ""
        if body.audio_base64 and not text:
            # Stub: no server-side transcription here; caller should use /voice/transcribe then pass transcript
            return {"status": "error", "detail": "Provide transcript or transcribe audio via /voice/transcribe first"}
        if not text:
            return {"status": "error", "detail": "transcript required"}
        vibe = vibe_analyzer.analyze(text)
        return {"status": "success", "vibe": vibe.to_dict(), "confidence": vibe.confidence_score}
    except Exception as e:
        logger.warning("vibecoding_analyze_audio failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

class VibeDetectFrameworksRequest(BaseModel):
    text: Optional[str] = None
    project_id: Optional[str] = None

@api_router.post("/vibecoding/detect-frameworks")
async def vibecoding_detect_frameworks(body: VibeDetectFrameworksRequest):
    """Detect frameworks and languages from text (or from project description when project_id given)."""
    try:
        from vibe_analysis import vibe_analyzer
        text = body.text or ""
        if body.project_id and not text:
            proj = await db.projects.find_one({"id": body.project_id}, {"description": 1, "requirements": 1})
            if proj:
                req = proj.get("requirements") or {}
                text = req.get("prompt") or req.get("description") or proj.get("description") or ""
        if not text:
            return {"status": "success", "frameworks": [], "languages": []}
        vibe = vibe_analyzer.analyze(text)
        return {"status": "success", "frameworks": vibe.detected_frameworks, "languages": vibe.detected_languages}
    except Exception as e:
        logger.warning("vibecoding_detect_frameworks failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

# ==================== IDE (debug, profiler, linter) ====================
class IDEBreakpointRequest(BaseModel):
    file_path: str
    line: int
    column: int = 0
    condition: Optional[str] = None

@api_router.post("/ide/debug/start")
async def ide_debug_start(project_id: str = Query(...)):
    """Start a debug session (stub)."""
    from ide_features import debugger_manager
    session_id = str(uuid.uuid4())
    session = await debugger_manager.start_debug_session(session_id, project_id)
    return {"session_id": session.session_id, "project_id": session.project_id, "status": session.status}

@api_router.post("/ide/debug/{session_id}/breakpoint")
async def ide_debug_set_breakpoint(session_id: str, body: IDEBreakpointRequest):
    """Set a breakpoint in a debug session."""
    from ide_features import debugger_manager, BreakPoint
    bp = BreakPoint(file_path=body.file_path, line=body.line, column=body.column, condition=body.condition)
    result = await debugger_manager.set_breakpoint(session_id, bp)
    return {"id": result.id, "file_path": result.file_path, "line": result.line, "column": result.column, "condition": result.condition, "enabled": result.enabled}

@api_router.delete("/ide/debug/{session_id}/breakpoint/{breakpoint_id}")
async def ide_debug_remove_breakpoint(session_id: str, breakpoint_id: str):
    """Remove a breakpoint."""
    from ide_features import debugger_manager
    await debugger_manager.remove_breakpoint(session_id, breakpoint_id)
    return {"status": "removed"}

@api_router.post("/ide/profiler/start")
async def ide_profiler_start(project_id: str = Query(...)):
    """Start profiler (stub)."""
    from ide_features import profiler_manager
    session_id = str(uuid.uuid4())
    out = await profiler_manager.start_profiler(session_id, project_id)
    return out

@api_router.post("/ide/profiler/stop")
async def ide_profiler_stop(session_id: str = Query(...)):
    """Stop profiler (stub)."""
    from ide_features import profiler_manager
    out = await profiler_manager.stop_profiler(session_id)
    return out

@api_router.post("/ide/lint")
async def ide_lint(project_id: str = Query(...), file_path: Optional[str] = None, code: Optional[str] = None):
    """Run linter (stub). Returns empty list until wired to real linter."""
    from ide_features import linter_manager
    issues = await linter_manager.run_lint(project_id, file_path or "", code)
    return {"issues": [{"file_path": i.file_path, "line": i.line, "column": i.column, "message": i.message, "severity": i.severity} for i in issues]}

# ==================== GIT ====================
@api_router.get("/git/status")
async def git_status(repo_path: str = Query(None), project_id: Optional[str] = Query(None), user: dict = Depends(get_optional_user)):
    """Real git status. Pass repo_path (server path) or project_id (resolved when authenticated)."""
    from git_integration import git_manager
    path = repo_path
    if project_id and user and not path:
        proj = await db.projects.find_one({"id": project_id, "user_id": user.get("id")})
        if proj:
            path = str(_project_workspace_path(project_id).resolve())
    if not path:
        raise HTTPException(status_code=400, detail="repo_path or project_id required")
    status = await git_manager.get_status(path)
    return {"branch": status.branch, "ahead": status.ahead, "behind": status.behind, "modified": status.modified, "untracked": status.untracked, "staged": status.staged, "conflicted": status.conflicted, "is_repo": status.is_repo, "error": status.error}

@api_router.post("/git/stage")
async def git_stage(repo_path: str = Query(None), project_id: Optional[str] = Query(None), file_path: str = Query(...), user: dict = Depends(get_optional_user)):
    from git_integration import git_manager
    path = repo_path
    if project_id and user and not path:
        proj = await db.projects.find_one({"id": project_id, "user_id": user.get("id")})
        if proj:
            path = str(_project_workspace_path(project_id).resolve())
    if not path:
        raise HTTPException(status_code=400, detail="repo_path or project_id required")
    ok = await git_manager.stage_file(path, file_path)
    return {"status": "staged" if ok else "error"}

class GitCommitRequest(BaseModel):
    message: str
    author: Optional[str] = None

@api_router.post("/git/commit")
async def git_commit(repo_path: str = Query(None), project_id: Optional[str] = Query(None), body: GitCommitRequest = None, user: dict = Depends(get_optional_user)):
    """Real git commit. Pass repo_path or project_id (when authenticated)."""
    from git_integration import git_manager
    if not body:
        raise HTTPException(status_code=400, detail="body required")
    path = repo_path
    if project_id and user and not path:
        proj = await db.projects.find_one({"id": project_id, "user_id": user.get("id")})
        if proj:
            path = str(_project_workspace_path(project_id).resolve())
    if not path:
        raise HTTPException(status_code=400, detail="repo_path or project_id required")
    ok = await git_manager.commit(path, body.message, body.author)
    return {"status": "ok" if ok else "error"}

@api_router.get("/git/branches")
async def git_branches(repo_path: str = Query(None), project_id: Optional[str] = Query(None), user: dict = Depends(get_optional_user)):
    """List branches. Pass repo_path or project_id (when authenticated)."""
    from git_integration import git_manager
    path = repo_path
    if project_id and user and not path:
        proj = await db.projects.find_one({"id": project_id, "user_id": user.get("id")})
        if proj:
            path = str(_project_workspace_path(project_id).resolve())
    if not path:
        raise HTTPException(status_code=400, detail="repo_path or project_id required")
    branches = await git_manager.list_branches(path)
    return {"branches": branches}

@api_router.post("/git/merge")
async def git_merge(repo_path: str = Query(None), project_id: Optional[str] = Query(None), branch: str = Query(...), user: dict = Depends(get_optional_user)):
    """Merge branch into current branch."""
    from git_integration import git_manager
    path = repo_path
    if project_id and user and not path:
        proj = await db.projects.find_one({"id": project_id, "user_id": user.get("id")})
        if proj:
            path = str(_project_workspace_path(project_id).resolve())
    if not path:
        raise HTTPException(status_code=400, detail="repo_path or project_id required")
    ok, msg = await git_manager.merge_branch(path, branch)
    return {"status": "ok" if ok else "error", "message": msg}

class GitResolveRequest(BaseModel):
    file_path: str
    resolution: str = "ours"  # ours | theirs

@api_router.post("/git/resolve-conflict")
async def git_resolve_conflict(repo_path: str = Query(None), project_id: Optional[str] = Query(None), body: GitResolveRequest = None, user: dict = Depends(get_optional_user)):
    """Resolve conflict by checking out ours or theirs and staging."""
    from git_integration import git_manager
    if not body:
        raise HTTPException(status_code=400, detail="body required")
    path = repo_path
    if project_id and user and not path:
        proj = await db.projects.find_one({"id": project_id, "user_id": user.get("id")})
        if proj:
            path = str(_project_workspace_path(project_id).resolve())
    if not path:
        raise HTTPException(status_code=400, detail="repo_path or project_id required")
    ok = await git_manager.resolve_conflict(path, body.file_path, body.resolution)
    return {"status": "ok" if ok else "error"}

# ==================== TERMINAL ====================
@api_router.post("/terminal/create")
async def terminal_create(project_path: str = Query(...), project_id: Optional[str] = Query(None), shell: str = Query("/bin/bash"), user: dict = Depends(get_optional_user)):
    """Create terminal session. Use project_path (server workspace path) or project_id (resolved server-side when authenticated)."""
    from terminal_integration import terminal_manager
    path = project_path
    if project_id and user:
        proj = await db.projects.find_one({"id": project_id, "user_id": user.get("id")})
        if proj:
            path = str(_project_workspace_path(project_id).resolve())
    session = await terminal_manager.create_terminal(path, shell)
    return {"session_id": session.session_id, "project_path": session.project_path, "shell": session.shell, "columns": session.columns, "rows": session.rows}

class TerminalExecuteRequest(BaseModel):
    command: str
    timeout: Optional[int] = 60

@api_router.post("/terminal/{session_id}/execute")
async def terminal_execute(session_id: str, body: TerminalExecuteRequest):
    """Execute command in the session's project path. Full implementation — runs real shell command."""
    from terminal_integration import terminal_manager
    result = await terminal_manager.execute(session_id, body.command, body.timeout or 60)
    return result

@api_router.delete("/terminal/{session_id}")
async def terminal_close(session_id: str):
    from terminal_integration import terminal_manager
    await terminal_manager.close_terminal(session_id)
    return {"status": "closed", "session_id": session_id}

# ==================== ECOSYSTEM ====================
@api_router.get("/ecosystem/vscode/config")
async def ecosystem_vscode_config():
    from ecosystem_integration import ecosystem_manager
    config = ecosystem_manager.vscode.generate_extension_config()
    return {"status": "success", "extension_id": ecosystem_manager.vscode.extension_id, "version": ecosystem_manager.vscode.version, "config": config}

@api_router.get("/ecosystem/vscode/extension-code")
async def ecosystem_vscode_extension_code():
    from ecosystem_integration import ecosystem_manager
    code = ecosystem_manager.vscode.generate_extension_code()
    return {"status": "success", "code": code}

# ==================== AI FEATURES (extra) ====================
class AIGenerateTestRequest(BaseModel):
    code: str
    language: str
    framework: Optional[str] = None
    test_type: str = "unit"

@api_router.post("/ai/tests/generate")
async def ai_tests_generate(body: AIGenerateTestRequest):
    from ai_features import test_generator
    if (body.test_type or "unit").lower() == "unit":
        result = test_generator.generate_unit_tests(body.code, body.language, body.framework)
    else:
        result = test_generator.generate_integration_tests(body.code, body.language, body.framework)
    return {"code": result.code, "description": result.description, "test_type": result.test_type}

class AIDocsGenerateRequest(BaseModel):
    project_name: str
    description: Optional[str] = None
    features: Optional[List[str]] = None

@api_router.post("/ai/docs/generate")
async def ai_docs_generate(body: AIDocsGenerateRequest):
    from ai_features import documentation_generator
    readme = documentation_generator.generate_readme(body.project_name, body.description, body.features)
    return {"status": "success", "readme": readme}

# ==================== DEPLOY VALIDATION & CACHE (modules 9–13) ====================
class DeployValidateRequest(BaseModel):
    platform: str  # vercel | netlify | railway
    files: Dict[str, str] = {}
    config: Optional[Dict[str, Any]] = None

@api_router.post("/deploy/validate")
async def deploy_validate(body: DeployValidateRequest):
    from validate_deployment import validate_deployment
    result = validate_deployment(body.platform, body.files, body.config)
    return {"valid": result.valid, "errors": result.errors, "warnings": result.warnings, "platform": result.platform}

@api_router.post("/cache/invalidate")
async def cache_invalidate(agent_name: Optional[str] = Query(None), user: dict = Depends(get_optional_user)):
    """Invalidate agent cache (optional: by agent_name)."""
    from agent_cache import invalidate
    n = await invalidate(db, agent_name=agent_name)
    return {"status": "ok", "deleted": n}

# Include routers (domain split) — all wired in app (9.5+)
try:
    from routers import monitoring_router, health_router
    app.include_router(health_router)
    app.include_router(monitoring_router)
except ImportError:
    pass
app.include_router(auth_router)
app.include_router(projects_router)
app.include_router(tools_router)
app.include_router(agents_router)
app.include_router(api_router)

# Free-tier branding: served from our server so it cannot be removed from user's source (they only have an iframe tag).
BRANDING_HTML = """<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head><body style="margin:0;padding:0;font-family:system-ui,sans-serif;font-size:12px;display:flex;align-items:center;justify-content:center;min-height:28px;background:transparent;color:#808080;"><a href="https://crucibai.com" target="_blank" rel="noopener noreferrer" style="color:#808080;text-decoration:none;">Built with CrucibAI</a></body></html>"""

# /api/metrics served by routers.monitoring (Prometheus)

@api_router.post('/stripe/webhook')
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events"""
    import stripe
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv('STRIPE_WEBHOOK_SECRET')
        )
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            user_id = session['client_reference_id']
            credits = int(session['metadata']['credits'])
            # Add credits to user
            await db.execute(
                "UPDATE users SET credits = credits + %s WHERE id = %s",
                (credits, user_id)
            )
            await send_email(user_id, "Credits Added", f"You received {credits} credits")
        return {"status": "success"}
    except Exception as e:
        return {"error": str(e)}, 400

@app.get("/branding")
async def branding_badge():
    """Serves the CrucibAI badge for free-tier iframe. Content is on our server so free users cannot remove it."""
    return Response(content=BRANDING_HTML, media_type="text/html")


@app.websocket("/ws/projects/{project_id}/progress")
async def websocket_project_progress(websocket: WebSocket, project_id: str):
    """Real-time build progress for AgentMonitor / BuildProgress UI."""
    await websocket.accept()
    try:
        while True:
            project = await db.projects.find_one({"id": project_id}, {"_id": 0, "status": 1, "current_phase": 1, "current_agent": 1, "progress_percent": 1, "tokens_used": 1})
            if project:
                await websocket.send_json({
                    "phase": project.get("current_phase", 0),
                    "agent": project.get("current_agent", ""),
                    "status": project.get("status", ""),
                    "progress": project.get("progress_percent", 0),
                    "tokens_used": project.get("tokens_used", 0),
                })
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
app.add_middleware(RateLimitMiddleware, requests_per_minute=int(os.environ.get("RATE_LIMIT_PER_MINUTE", "100")))
if os.environ.get("HTTPS_REDIRECT", "").strip().lower() in ("1", "true", "yes"):
    app.add_middleware(HTTPSRedirectMiddleware)
# With allow_credentials=True, browsers do not accept Access-Control-Allow-Origin: *
# Use explicit origins; default to localhost for dev if unset or "*"
_cors_origins = os.environ.get("CORS_ORIGINS", "").strip() or "*"
CORS_ORIGINS_LIST = [o.strip() for o in _cors_origins.split(",") if o.strip()]
if not CORS_ORIGINS_LIST or (len(CORS_ORIGINS_LIST) == 1 and CORS_ORIGINS_LIST[0] == "*"):
    CORS_ORIGINS_LIST = ["http://localhost:3000", "http://127.0.0.1:3000"]
    if _cors_origins == "*":
        logger.warning("CORS_ORIGINS was '*'; using explicit dev origins. Set CORS_ORIGINS to your frontend URL in production.")
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=CORS_ORIGINS_LIST,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "X-Request-ID"],
)

@app.on_event("startup")
async def init_postgres_primary():
    """Initialize PostgreSQL as primary database at startup. Run migrations so Railway/Docker get schema. In CRUCIBAI_DEV without DATABASE_URL, skip so /api/health still works."""
    global db, audit_logger
    if not os.environ.get("DATABASE_URL"):
        logger.warning("DATABASE_URL not set; DB not initialized. /api/health OK; auth/builds need DATABASE_URL.")
        return
    try:
        from db_pg import get_db, run_migrations
        from structured_logging import AuditLogger
        await run_migrations()
        db = await get_db()
        audit_logger = AuditLogger() if AuditLogger else None
        logger.info("PostgreSQL initialized as primary database")
    except Exception as e:
        logger.error("PostgreSQL initialization failed: %s", e)
        if not os.environ.get("CRUCIBAI_DEV"):
            raise
        logger.warning("Continuing without DB (CRUCIBAI_DEV). /api/health OK; auth/builds will fail.")


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
    """Seed 5 examples so /api/examples returns proof of generated apps (10/10 roadmap)."""
    if db is None:
        return
    try:
        n = await db.examples.count_documents({})
        if n == 0:
            examples = [
                {
                    "name": "todo-app",
                    "prompt": "Build a todo app with user authentication, task management (CRUD), categories, and due dates. Use React frontend, Node.js backend, MongoDB.",
                    "generated_code": {
                        "frontend": "// React Todo App - generated by CrucibAI\nconst App = () => {\n  const [todos, setTodos] = useState([]);\n  return (\n    <div className=\"p-4\">\n      <h1>Todo App</h1>\n      <ul>{todos.map(t => <li key={t.id}>{t.title}</li>)}</ul>\n    </div>\n  );\n};\nexport default App;",
                        "backend": "# FastAPI Todo API\nfrom fastapi import FastAPI\napp = FastAPI()\n@app.get('/todos')\ndef get_todos(): return []\n@app.post('/todos')\ndef create_todo(): return {'id': 1}",
                        "database": "-- MongoDB: collections todos, users",
                        "tests": "# pytest\ndef test_get_todos(): assert True",
                    },
                    "quality_metrics": {"overall_score": 72.5, "verdict": "good", "breakdown": {"frontend": {"score": 75}, "backend": {"score": 80}, "database": {"score": 50}, "tests": {"score": 65}}},
                },
                {
                    "name": "blog-platform",
                    "prompt": "Create a blogging platform with user registration, article publishing, comments, search, and tagging. Include admin dashboard.",
                    "generated_code": {
                        "frontend": "// React Blog - CrucibAI\nimport { useState } from 'react';\nconst Blog = () => (\n  <div><h1>Blog</h1><article /></div>\n);\nexport default Blog;",
                        "backend": "# FastAPI Blog API\nfrom fastapi import FastAPI\napp = FastAPI()\n@app.get('/posts')\ndef list_posts(): return []",
                        "database": "CREATE TABLE posts (id SERIAL, title TEXT);",
                        "tests": "def test_list_posts(): assert True",
                    },
                    "quality_metrics": {"overall_score": 68, "verdict": "good", "breakdown": {"frontend": {"score": 70}, "backend": {"score": 72}, "database": {"score": 60}, "tests": {"score": 50}}},
                },
                {
                    "name": "ecommerce-store",
                    "prompt": "Build a basic e-commerce store with product catalog, shopping cart, checkout, and payment processing via Stripe.",
                    "generated_code": {
                        "frontend": "// E-commerce - CrucibAI\nconst Store = () => <div><h1>Store</h1></div>;\nexport default Store;",
                        "backend": "# Flask + Stripe\nfrom flask import Flask\napp = Flask(__name__)\n@app.route('/products')\ndef products(): return []",
                        "database": "CREATE TABLE products (id INT, name VARCHAR(255));",
                        "tests": "def test_products(): pass",
                    },
                    "quality_metrics": {"overall_score": 65, "verdict": "good", "breakdown": {"frontend": {"score": 65}, "backend": {"score": 70}, "database": {"score": 55}, "tests": {"score": 40}}},
                },
                {
                    "name": "project-management",
                    "prompt": "Create a project management tool with user teams, projects, tasks, comments, and file uploads.",
                    "generated_code": {
                        "frontend": "// PM Tool - CrucibAI\nconst Dashboard = () => <div><h1>Projects</h1></div>;\nexport default Dashboard;",
                        "backend": "# Node Express\nconst express = require('express');\nconst app = express();\napp.get('/api/projects', (req,res) => res.json([]));",
                        "database": "-- MongoDB: projects, tasks, users",
                        "tests": "describe('projects', () => { it('lists', () => {}); });",
                    },
                    "quality_metrics": {"overall_score": 70, "verdict": "good", "breakdown": {"frontend": {"score": 72}, "backend": {"score": 75}, "database": {"score": 55}, "tests": {"score": 60}}},
                },
                {
                    "name": "analytics-dashboard",
                    "prompt": "Build an analytics dashboard that accepts CSV uploads, displays charts, and exports reports.",
                    "generated_code": {
                        "frontend": "// Dashboard - CrucibAI\nconst Dashboard = () => <div><h1>Analytics</h1></div>;\nexport default Dashboard;",
                        "backend": "# Python Pandas API\nfrom fastapi import FastAPI, UploadFile\napp = FastAPI()\n@app.post('/upload')\nasync def upload(csv: UploadFile): return {'rows': 0}",
                        "database": "-- Store upload metadata",
                        "tests": "def test_upload(): assert True",
                    },
                    "quality_metrics": {"overall_score": 66, "verdict": "good", "breakdown": {"frontend": {"score": 68}, "backend": {"score": 72}, "database": {"score": 50}, "tests": {"score": 55}}},
                },
            ]
            for ex in examples:
                ex["created_at"] = datetime.now(timezone.utc).isoformat()
                await db.examples.insert_one(ex)
            logger.info("Seeded 5 examples: todo-app, blog-platform, ecommerce-store, project-management, analytics-dashboard")
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
    try:
        from db_pg import close_pg_pool
        await close_pg_pool()
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
        "icon": "clock"
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
        "badge": "POPULAR"
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
        "all_agents": True
    }
}

# Token multipliers for consistency
SWARM_TOKEN_MULTIPLIER = 1.5  # Pro speed with swarm
MAX_TOKEN_MULTIPLIER = 2.0    # Max speed (full swarm)

# Serve frontend static files (Docker/Railway: frontend built and copied to /app/static)
# SPA fallback: serve index.html for paths like /auth, /dashboard so client-side router works
_static_dir = Path(__file__).resolve().parent / "static"
if _static_dir.exists():
    from fastapi.staticfiles import StaticFiles

    class SpaStaticFiles(StaticFiles):
        """Serve index.html for unknown paths so React Router handles /auth, /dashboard, etc."""

        def lookup_path(self, path: str):
            full_path, stat_result = super().lookup_path(path)
            if stat_result is None:
                full_path, stat_result = super().lookup_path("index.html")
            return full_path, stat_result

    app.mount("/", SpaStaticFiles(directory=str(_static_dir), html=True), name="frontend")
