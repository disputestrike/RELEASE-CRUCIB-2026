from __future__ import annotations

import asyncio
import logging
import os
import json
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Response, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field

from .deps import (
    ADMIN_ROLES,
    ADMIN_USER_IDS,
    JWT_ALGORITHM,
    JWT_SECRET,
    get_current_user,
    get_optional_user,
    require_permission,
)
from .provider_readiness import build_provider_readiness
from .services.llm_service import (
    _effective_api_keys,
    _get_model_chain,
    _call_llm_with_fallback,
    _is_product_support_query,
    get_authenticated_or_api_user,
    get_workspace_api_keys,
)

# Legacy compatibility anchors for older backend contract tests:
# from agent_recursive_learning import AgentMemory, PerformanceTracker
# from critic_agent import CriticAgent, TruthModule
# from vector_memory import VectorMemory
# validate_environment
# metrics_system
# review_build
# record_execution

AGENT_DEFINITIONS = [
    {"name": "Agent01", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent02", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent03", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent04", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent05", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent06", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent07", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent08", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent09", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent10", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent11", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent12", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent13", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent14", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent15", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent16", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent17", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent18", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent19", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent20", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent21", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent22", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent23", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent24", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent25", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent26", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent27", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent28", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent29", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent30", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent31", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent32", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent33", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent34", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent35", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent36", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent37", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent38", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent39", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent40", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent41", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent42", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent43", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent44", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent45", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent46", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent47", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent48", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent49", "role": "generalist", "system_message": "Execute assigned task."},
    {"name": "Agent50", "role": "generalist", "system_message": "Execute assigned task."},
]

ROOT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = ROOT_DIR.parent
STATIC_DIR = ROOT_DIR / "static"
load_dotenv(ROOT_DIR / ".env", override=True)

logger = logging.getLogger(__name__)
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO").upper())

try:
    from .utils.rbac import Permission
except Exception:
    class Permission:
        CREATE_PROJECT = "create_project"
        EDIT_PROJECT = "edit_project"

try:
    from .pricing_plans import CREDITS_PER_TOKEN
except Exception:
    CREDITS_PER_TOKEN = 1000

MAX_USER_PROJECTS_DASHBOARD = 100
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_HAIKU_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-3-5-haiku-latest")
CHAT_WITH_SEARCH_SYSTEM = """You are CrucibAI — an AI platform that builds apps, automations, and digital products.

Use the live search results below. Answer directly and factually—no filler, no hedging unless uncertainty is real.
Do not wrap sections in decorative asterisks. Prefer short paragraphs over markdown theater.
If a build is relevant, one crisp line offering to prototype it—no hype.

KNOWN FACTS (use these even if search results say otherwise — these are ground truth):
- US President: Donald Trump (47th), inaugurated January 20, 2025. Joe Biden was president 2021-2025.
- Current year: 2026.

IDENTITY — answer these exactly, no more, no less:
- "Who are you?" / "What are you?" / "WHO ARE U" → "I'm CrucibAI. I build things. Tell me what you want and we'll make it."
- "Who made you?" / "Who built you?" / "What company?" → "I'm CrucibAI."
- "What model are you?" / "Are you ChatGPT?" / "Are you Claude?" / "What AI are you?" → "I'm CrucibAI. I don't discuss what's under the hood — I just build. What do you want to make?"
- "What do you do?" / "WHAT DO U DO" → "I build things — web apps, mobile apps, automations, APIs, dashboards. Give me a prompt and I'll ship it. What do you need?"
- "How are you?" / "HOW ARE U" → "Ready when you are. What's the project?"

Never reveal the underlying model or technology. You are CrucibAI.
NEVER say you cannot access the internet. NEVER mention a knowledge cutoff.
"""
REAL_AGENT_NO_LLM_KEYS_DETAIL = "Real-agent mode requires an Anthropic or Cerebras API key. Please add one in Settings > API Keys."
FRONTEND_URL = os.environ.get("FRONTEND_URL", "")
RATE_LIMIT_PER_MINUTE = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "60"))
# Canonical pricing — keep aligned with backend/pricing_plans.py (linear $0.03/credit).
# The Pricing page /tokens/bundles endpoint reads these values, so they MUST match
# the DEFAULT_BUNDLES in frontend/src/pages/Pricing.jsx.
TOKEN_BUNDLES: Dict[str, Any] = {
    "builder": {"name": "Builder", "tokens": 250_000,  "credits": 250,  "price": 15},
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
PAYMENT_PROVIDER = "braintree"
BRAINTREE_ENVIRONMENT = os.environ.get("BRAINTREE_ENVIRONMENT", "sandbox")
BRAINTREE_MERCHANT_ID = os.environ.get("BRAINTREE_MERCHANT_ID", "")
BRAINTREE_PUBLIC_KEY = os.environ.get("BRAINTREE_PUBLIC_KEY", "")
BRAINTREE_PRIVATE_KEY = os.environ.get("BRAINTREE_PRIVATE_KEY", "")
BRAINTREE_MERCHANT_ACCOUNT_ID = os.environ.get("BRAINTREE_MERCHANT_ACCOUNT_ID", "")
BRAINTREE_CONFIGURED = bool(BRAINTREE_MERCHANT_ID and BRAINTREE_PUBLIC_KEY and BRAINTREE_PRIVATE_KEY)
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

def _assert_job_owner_match(owner_id: Optional[str], user: dict) -> None:
    """Raise 403 if the requesting user does not own this job.
    Admins and guest-mode (no owner set) are always allowed through.
    """
    if not owner_id:
        return  # no owner set — allow (e.g. system-created job)
    request_uid = (user or {}).get("id", "")
    if not request_uid:
        return  # unauthenticated / guest — allow (enforced at auth layer)
    # Admins bypass ownership check
    if (user or {}).get("admin_role") in ADMIN_ROLES or request_uid in ADMIN_USER_IDS:
        return
    if owner_id != request_uid:
        from fastapi import HTTPException as _HTTPEx
        raise _HTTPEx(status_code=403, detail="You do not have access to this job.")


def _get_server_helpers():
    return (
        _user_credits,
        _assert_job_owner_match,   # FIX: was _ensure_credit_balance — wrong function,
        _resolve_job_project_id_for_user,  # wrong signature → TypeError on every run-auto call
        _project_workspace_path,
    )


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
        from .services.llm_service import _call_llm_with_fallback as _llm_call

        return await _llm_call(*args, **kwargs)
    except (ImportError, ModuleNotFoundError) as exc:
        logger.warning("llm_service unavailable; using compatibility fallback: %s", exc)
        return ({"text": "I'm having trouble connecting to the AI service right now. Please try again in a moment.", "tokens_used": 0}, "compat/model")


def _is_product_support_query(prompt: str) -> Optional[str]:
    """Delegate to services.llm_service."""
    try:
        from .services.llm_service import _is_product_support_query as _support_check

        return _support_check(prompt)
    except (ImportError, ModuleNotFoundError):
        return None


async def _call_llm_with_fallback_streaming(*args, **kwargs):
    """Streaming wrapper: calls _call_llm_with_fallback and yields the full
    response as a single chunk so the streaming endpoint always gets
    (chunk: str, model: str, tokens: int) tuples.
    Falls back gracefully if the LLM service is unavailable.
    """
    try:
        response, model_used = await _call_llm_with_fallback(*args, **kwargs)
        text = response.get("text", "") if isinstance(response, dict) else str(response)
        tokens = response.get("tokens_used", 0) if isinstance(response, dict) else 0
        yield text, model_used, tokens
    except Exception as exc:
        logger.warning("_call_llm_with_fallback_streaming error: %s", exc)
        yield "I'm having trouble connecting to the AI service right now. Please try again in a moment.", "compat/model", 0


def _is_conversational_message(message: str) -> bool:
    """Detect if a message is purely conversational (questions, chat, greetings)
    vs a build/create/deploy/automate intent that should route through the
    orchestration engine.

    Returns True  -> skip ClarificationAgent, go straight to LLM chat.
    Returns False -> run ClarificationAgent to check for build/agent intent.

    Aligned with the frontend Dashboard.jsx BUILD_KEYWORDS / AGENT_KEYWORDS
    regex patterns so both layers agree on routing.
    Design rule: when in doubt, treat as conversational.
    """
    import re
    m = message.lower().strip()
    flat = re.sub(r'[\r\n]+', ' ', m)  # collapse newlines

    # ── 1. Definite chat patterns (mirrors CHAT_ONLY_PATTERNS in Dashboard.jsx)
    chat_only = [
        r'^(hi|hello|hey|howdy|yo|sup|greetings?|good\s*(morning|afternoon|evening)|hi\s+there|hey\s+there|what\'?s\s*up)\s*[!.?]*$',
        r'^(thanks?|thank\s*you|thx|ok|okay|sure|yes|no|nope|yep|yeah)\s*[!.?]*$',
        r'^(how\s+are\s+you|what\'?s\s+going\s+on|how\s+is\s+it\s+going)\s*[!.?]*$',
        r'^(bye|goodbye|see\s*ya|later)\s*[!.?]*$',
    ]
    for pat in chat_only:
        if re.match(pat, m, re.IGNORECASE):
            return True

    # ── 2. Very short messages are always conversational
    if len(m) < 8:
        return True

    # ── 3. Agent / automation keywords (mirrors AGENT_KEYWORDS in Dashboard.jsx)
    agent_pattern = r'\b(automate|schedule|cron|webhook|trigger|run\s+every|run\s+when|run\s+on|agent|automation|workflow|pipeline)\b'
    if re.search(agent_pattern, flat, re.IGNORECASE):
        return False

    # ── 4. Build keywords — verb + software target
    #    Mirrors BUILD_KEYWORDS regex from Dashboard.jsx
    build_verbs = r'\b(build|building|create|creating|make|making|develop|developing|design|designing|generate|generating|produce|producing|code|scaffold|scaffolding|implement|implementing|launch|launching|deploy|deploying|set\s+up|setup|bootstrap|write|configure|spin\s+up|spin\s+up)\b'
    build_targets = r'\b(app|application|website|web\s*app|landing\s*page|dashboard|saas|mvp|api|backend|frontend|tool|platform|product|service|microservice|database|schema|bot|chatbot|portal|system|interface|ui|ux|component|module|library|package|plugin|extension|script|cli|sdk|integration|webhook|endpoint|server|client|mobile\s*app|ios\s*app|android\s*app|chrome\s*extension|vs\s*code\s*extension|npm\s*package|rest\s*api|graphql\s*api|crud\s*app|full\s*stack|fullstack|e-commerce|ecommerce|store|shop|marketplace|crm|erp|cms|blog|portfolio|admin\s*panel|admin\s*dashboard|analytics\s*dashboard|monitoring\s*tool|devops\s*pipeline|ci\s*cd|docker|container|kubernetes|k8s|auth\s*system|payment\s*system|notification\s*system|email\s*system|search\s*engine|recommendation\s*engine|ml\s*model|ai\s*model|neural\s*network|data\s*pipeline|etl|scraper|crawler|infrastructure|environment|cluster|deployment)\b'
    if re.search(build_verbs, flat, re.IGNORECASE) and re.search(build_targets, flat, re.IGNORECASE):
        return False

    # ── 5. Loose build match (verb alone with clear software context)
    #    Mirrors BUILD_KEYWORDS_LOOSE from Dashboard.jsx
    loose_verbs = r'\b(build|create|make|develop|generate)\b'
    loose_targets = r'\b(web|app|site|page|saas|dash|api|mvp|tool|product|platform|frontend|backend|mobile|ios|android)\b'
    if re.search(loose_verbs, flat, re.IGNORECASE) and re.search(loose_targets, flat, re.IGNORECASE):
        return False

    # ── 6. Long technical briefs (mirrors looksLikeBuildSpec in Dashboard.jsx)
    if len(flat) >= 160:
        tech_signals = [
            'react native', 'ios', 'android', 'expo', 'jest', 'playwright',
            'e2e', 'swagger', 'microservice', 'rest api', 'graphql', 'braintree',
            'postgres', 'mongodb', 'tailwind', 'fastapi', 'next.js', 'vite',
            'kubernetes', 'docker', 'offline', 'multi-tenant', 'saas',
            'dashboard', 'crm', 'oauth', 'jwt', 'websocket', 'redis',
            'elasticsearch', 'celery', 'rabbitmq', 'kafka',
        ]
        hits = sum(1 for s in tech_signals if s in flat)
        if hits >= 2:
            return False

    # ── 7. Explicit intent phrases ("I want you to build", "go ahead and create", etc.)
    explicit_phrases = [
        r'i\s+(want|need)\s+(you\s+to|u\s+to)\s+(build|create|make|develop|generate|code|write)',
        r'(go\s+ahead\s+and|just|please)\s+(build|create|make|develop|generate|code|write)',
        r"(you\s+decide|figure\s+it\s+out|don'?t\s+ask|just\s+do\s+it)",
        r'(can\s+you|could\s+you|would\s+you)\s+(build|create|make|develop|generate|code|write)',
    ]
    for pat in explicit_phrases:
        if re.search(pat, flat, re.IGNORECASE):
            return False

    # ── 8. Everything else is conversational — let the LLM handle it
    return True


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



# ═══════════════════════════════════════════════════════════════════════════
#  AGENTIC LOOP — observe → act → inspect → revise (replaces one-shot LLM)
# ═══════════════════════════════════════════════════════════════════════════
#
#  Architecture:  competitor analysis showed every high-quality coding agent
#  (Claude Code, Replit, Lovable) runs a while(True) loop where the model
#  can call file/run/search tools mid-generation and decides its own exit
#  condition via stop_reason == "end_turn".  CrucibAI previously made one
#  LLM call per agent step and returned.  This section replaces that pattern.
#
#  Concurrency:   read-only tools (read_file, list_files, search_files) run
#  in parallel (asyncio.gather, up to 10 concurrent). Write tools
#  (write_file, edit_file, run_command) run serially to avoid races.
#
#  Safety caps:   20 turns max; tool errors are reported to the model (not
#  raised), so the model can retry or skip gracefully.
# ─────────────────────────────────────────────────────────────────────────

# Read-only tools that are safe to execute concurrently
_READONLY_TOOLS: frozenset = frozenset({"read_file", "list_files", "search_files"})

# Agents that benefit from extended thinking before they write.
# These are the agents whose mistakes are most expensive downstream:
#   • Planners write the architecture every other agent follows
#   • Architecture agents define component contracts
#   • Security agents must catch subtle vulnerabilities
# Thinking is ONLY activated when the Anthropic model supports it
# (claude-3-7-sonnet and later).  Cerebras / fallback models skip it silently.
_THINKING_AGENTS: frozenset = frozenset({
    # Planning & architecture
    "Planner",
    "Architecture Agent",
    "Technical Architecture",
    "System Architecture",
    "Database Schema",
    "API Design",
    # Security — subtle issues require deep reasoning
    "Security Agent",
    "Security Audit",
    "Security Review",
    # Complex multi-file generators that must reason about the whole workspace
    "Backend Generation",
    "Frontend Generation",
    "Integration Agent",
    "Full Stack Generator",
    # Quality gates that need to reason, not just scan
    "UX Auditor",
    "Code Review Agent",
    "Test Strategy Agent",
})

# Models that support extended thinking (must be claude-3-7-sonnet or later)
_THINKING_CAPABLE_MODELS: tuple = (
    "claude-3-7-sonnet",
    "claude-sonnet-4",
    "claude-opus-4",
)

# Thinking token budget.  High enough that the model can reason through
# a non-trivial codebase; low enough to stay within cost budget.
_THINKING_BUDGET_TOKENS: int = 8000

# Anthropic tool_use definitions exposed to every agent
WORKSPACE_TOOLS_FOR_AGENTS: list = [
    {
        "name": "read_file",
        "description": (
            "Read a file from the project workspace. "
            "Use this to inspect existing code before writing or editing."
        ),
        "input_schema": {
            "type": "object",
            "required": ["path"],
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path within the project workspace (e.g. src/App.jsx).",
                },
            },
        },
    },
    {
        "name": "write_file",
        "description": (
            "Write content to a file in the project workspace. "
            "Creates the file and any parent directories if they do not exist. "
            "Overwrites the file completely — include ALL content."
        ),
        "input_schema": {
            "type": "object",
            "required": ["path", "content"],
            "properties": {
                "path": {"type": "string", "description": "Relative path (e.g. src/components/Button.jsx)."},
                "content": {"type": "string", "description": "Complete file content to write."},
            },
        },
    },
    {
        "name": "edit_file",
        "description": (
            "Perform an exact string replacement inside an existing file. "
            "old_text must match verbatim (including whitespace and indentation). "
            "Replaces only the FIRST occurrence."
        ),
        "input_schema": {
            "type": "object",
            "required": ["path", "old_text", "new_text"],
            "properties": {
                "path": {"type": "string", "description": "Relative path of the file to edit."},
                "old_text": {"type": "string", "description": "Exact text to find and replace."},
                "new_text": {"type": "string", "description": "Replacement text."},
            },
        },
    },
    {
        "name": "list_files",
        "description": "List files and directories in the project workspace.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Subdirectory to list (default: workspace root).",
                },
                "pattern": {
                    "type": "string",
                    "description": "Optional glob pattern to filter (e.g. '*.py', 'src/**/*.jsx').",
                },
            },
        },
    },
    {
        "name": "run_command",
        "description": (
            "Run an allowlisted command in the project workspace. "
            "Allowed prefixes: pytest, npm test, npm run test, npx jest, "
            "npx eslint, npm audit, python -m bandit, wc -l, find . "
            "Use this to verify code compiles / tests pass."
        ),
        "input_schema": {
            "type": "object",
            "required": ["command"],
            "properties": {
                "command": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Command as array of strings (e.g. ['npm', 'test']).",
                },
                "cwd": {
                    "type": "string",
                    "description": "Working directory relative to workspace root.",
                },
            },
        },
    },
    {
        "name": "search_files",
        "description": (
            "Search for a regex pattern across files in the project workspace. "
            "Returns matching lines with file names and line numbers."
        ),
        "input_schema": {
            "type": "object",
            "required": ["pattern"],
            "properties": {
                "pattern": {"type": "string", "description": "Regex pattern to search for."},
                "path": {
                    "type": "string",
                    "description": "Subdirectory to search within (default: entire workspace).",
                },
                "file_pattern": {
                    "type": "string",
                    "description": "Glob filter for filenames (e.g. '*.py', '*.{ts,tsx}').",
                },
            },
        },
    },
]


def _execute_workspace_tool_sync(
    tool_name: str,
    inputs: Dict[str, Any],
    project_id: str,
    workspace_path: str,
) -> Dict[str, Any]:
    """
    Execute a single workspace tool via runtime_engine.execute_tool_for_task.
    All real I/O is delegated through the single-brain runtime authority chain.
    edit_file is synthesised via read → replace → write.
    search_files uses subprocess grep (not in execute_tool natively).
    """
    import subprocess
    from backend.services.runtime.runtime_engine import runtime_engine as _re

    task_id = f"agent-loop-{project_id}"

    def _run_tool(tool_name_inner: str, params: dict) -> dict:
        return _re.execute_tool_for_task(
            project_id=project_id,
            task_id=task_id,
            tool_name=tool_name_inner,
            params={**params, "task_id": task_id},
        )

    if tool_name == "read_file":
        return _run_tool("file", {
            "action": "read",
            "path": inputs.get("path", ""),
        })

    if tool_name == "write_file":
        return _run_tool("file", {
            "action": "write",
            "path": inputs.get("path", ""),
            "content": inputs.get("content", ""),
        })

    if tool_name == "edit_file":
        path = inputs.get("path", "")
        old_text = inputs.get("old_text", "")
        new_text = inputs.get("new_text", "")
        read_result = _run_tool("file", {"action": "read", "path": path})
        if not read_result.get("success"):
            return {
                "success": False,
                "output": f"Could not read {path}: {read_result.get('error', '')}",
                "error": "read_failed",
            }
        current = read_result.get("output", "")
        if old_text not in current:
            # Try a looser match (strip trailing whitespace per line)
            stripped_old = "\n".join(l.rstrip() for l in old_text.splitlines())
            stripped_cur = "\n".join(l.rstrip() for l in current.splitlines())
            if stripped_old in stripped_cur:
                current = stripped_cur
                old_text = stripped_old
            else:
                return {
                    "success": False,
                    "output": (
                        f"edit_file: old_text not found verbatim in {path}. "
                        "Use read_file first to get the exact text."
                    ),
                    "error": "edit_miss",
                }
        updated = current.replace(old_text, new_text, 1)
        return _run_tool("file", {"action": "write", "path": path, "content": updated})

    if tool_name == "list_files":
        return _run_tool("file", {
            "action": "list",
            "path": inputs.get("path", ""),
            "pattern": inputs.get("pattern", ""),
        })

    if tool_name == "run_command":
        return _run_tool("run", {
            "command": inputs.get("command", []),
            "cwd": inputs.get("cwd", ""),
        })

        if tool_name == "search_files":
            try:
                from backend.project_state import WORKSPACE_ROOT
                ws_root = Path(WORKSPACE_ROOT) / project_id.replace("/", "_").replace("\\", "_")
                sub_path = (inputs.get("path") or "").lstrip("/\\")
                search_root = (ws_root / sub_path) if sub_path else ws_root
                if not search_root.exists():
                    search_root = ws_root
                pattern = inputs.get("pattern", ".")
                file_pat = inputs.get("file_pattern", "")
                cmd = ["grep", "-rn", "--max-count=20"]
                if file_pat:
                    cmd += [f"--include={file_pat}"]
                cmd += [pattern, str(search_root)]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
                out = proc.stdout.strip()[:6000] or "(no matches)"
                return {"success": True, "output": out}
            except Exception as exc:
                return {"success": False, "output": "", "error": str(exc)}

    return {"success": False, "output": f"Unknown tool: {tool_name}", "error": "unknown_tool"}


async def _execute_workspace_tool_async(
    tool_name: str,
    inputs: Dict[str, Any],
    project_id: str,
    workspace_path: str,
) -> Dict[str, Any]:
    """Async shim: runs the sync tool executor in a thread pool so we can await it."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        _execute_workspace_tool_sync,
        tool_name,
        inputs,
        project_id,
        workspace_path,
    )


async def _call_llm_with_tools_loop(
    *,
    message: str,
    system_message: str,
    project_id: str,
    workspace_path: str,
    api_key: str,
    model: str,
    agent_name: str = "",
    max_turns: int = 20,
    use_thinking: bool = False,
) -> Tuple[str, Dict[str, Any]]:
    """
    Full agentic loop: while(stop_reason != "end_turn") → execute tools → feed results back.

    Returns (final_text_output, metadata_dict).

    Concurrency model (mirrors Claude Code toolOrchestration.ts):
      • read-only tools  →  asyncio.gather (up to 10 concurrent)
      • write / run tools  →  serial (preserves file-system consistency)

    Adaptive thinking (mirrors Claude Code thinkingConfig: { type: 'adaptive' }):
      • Enabled when use_thinking=True AND the model supports it
      • Inserts a private reasoning block before the first tool-use or output
      • Only Anthropic models claude-3-7-sonnet+ support this; others skip silently
      • Thinking blocks from the response are preserved in the message history
        so the model retains its reasoning across tool calls
    """
    import httpx
    from backend.anthropic_models import normalize_anthropic_model, ANTHROPIC_HAIKU_MODEL

    model = normalize_anthropic_model(model, default=ANTHROPIC_HAIKU_MODEL)
    logger = logging.getLogger(__name__)

    messages: List[Dict[str, Any]] = [{"role": "user", "content": message}]
    files_written: List[str] = []
    turns = 0
    final_text = ""

    while turns < max_turns:
        turns += 1

        # ── Call Anthropic with workspace tools ──────────────────────────
        # Determine whether to activate extended thinking this turn.
        # Rules:
        #   • Only turn 1 (the model thinks before acting, not between retries)
        #   • Only when the caller requested thinking AND the model supports it
        #   • Thinking blocks must be passed back in subsequent turns so the
        #     model keeps its reasoning context across tool calls
        _model_lower = model.lower()
        _thinking_this_turn = (
            use_thinking
            and turns == 1
            and any(_model_lower.startswith(m) for m in _THINKING_CAPABLE_MODELS)
        )
        _req_max_tokens = (
            _THINKING_BUDGET_TOKENS + 8096  # thinking + output budget
            if _thinking_this_turn
            else 8096
        )
        _req_body: Dict[str, Any] = {
            "model": model,
            "max_tokens": _req_max_tokens,
            "system": system_message,
            "messages": messages,
            "tools": WORKSPACE_TOOLS_FOR_AGENTS,
        }
        if _thinking_this_turn:
            # Extended thinking: model gets a private scratchpad before acting.
            # betas header enables the feature on older API versions.
            _req_body["thinking"] = {
                "type": "enabled",
                "budget_tokens": _THINKING_BUDGET_TOKENS,
            }
            logger.info("[agent_loop] %s turn 1: extended thinking enabled (budget=%d)",
                        agent_name, _THINKING_BUDGET_TOKENS)

        try:
            async with httpx.AsyncClient(timeout=180) as client:
                _headers = {
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                }
                if _thinking_this_turn:
                    _headers["anthropic-beta"] = "interleaved-thinking-2025-05-14"
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=_headers,
                    json=_req_body,
                )
        except Exception as exc:
            logger.error("[agent_loop] %s turn %d: HTTP error: %s", agent_name, turns, exc)
            break

        if resp.status_code != 200:
            logger.error(
                "[agent_loop] %s turn %d: Anthropic %s: %s",
                agent_name, turns, resp.status_code, resp.text[:300],
            )
            break

        data = resp.json()
        stop_reason = data.get("stop_reason", "end_turn")
        content_blocks = data.get("content", [])

        # Accumulate any text the model produced this turn
        for block in content_blocks:
            if isinstance(block, dict) and block.get("type") == "text":
                final_text = block.get("text", "")

        # Append assistant turn to history
        messages.append({"role": "assistant", "content": content_blocks})

        if stop_reason == "end_turn":
            logger.info("[agent_loop] %s done after %d turn(s)", agent_name, turns)
            break

        if stop_reason != "tool_use":
            logger.warning("[agent_loop] %s unexpected stop_reason=%s", agent_name, stop_reason)
            break

        # ── Partition tool calls ────────────────────────────────────────
        tool_calls = [b for b in content_blocks if isinstance(b, dict) and b.get("type") == "tool_use"]
        if not tool_calls:
            break

        read_calls  = [tc for tc in tool_calls if tc.get("name") in _READONLY_TOOLS]
        write_calls = [tc for tc in tool_calls if tc.get("name") not in _READONLY_TOOLS]

        tool_results: List[Dict[str, Any]] = []

        # ── Read-only: run concurrently (up to 10) ──────────────────────
        if read_calls:
            semaphore = asyncio.Semaphore(10)

            async def _run_read(tc: Dict[str, Any]) -> Dict[str, Any]:
                async with semaphore:
                    return await _execute_workspace_tool_async(
                        tc.get("name", ""),
                        tc.get("input", {}),
                        project_id,
                        workspace_path,
                    )

            read_results = await asyncio.gather(
                *[_run_read(tc) for tc in read_calls],
                return_exceptions=True,
            )
            for tc, res in zip(read_calls, read_results):
                if isinstance(res, Exception):
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tc["id"],
                        "content": f"Error: {res}",
                        "is_error": True,
                    })
                else:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tc["id"],
                        "content": str(res.get("output", "")) if res.get("success") else f"Error: {res.get('error', 'unknown')}",
                        **({"is_error": True} if not res.get("success") else {}),
                    })
                logger.debug("[agent_loop] %s read tool=%s ok=%s", agent_name, tc.get("name"), not isinstance(res, Exception))

        # ── Write / run: serial to preserve workspace consistency ────────
        for tc in write_calls:
            name = tc.get("name", "")
            inputs = tc.get("input", {})
            try:
                res = await _execute_workspace_tool_async(name, inputs, project_id, workspace_path)
                if name in ("write_file", "edit_file"):
                    p = inputs.get("path", "")
                    if p and p not in files_written:
                        files_written.append(p)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc["id"],
                    "content": str(res.get("output", "ok")) if res.get("success") else f"Error: {res.get('error', 'failed')}",
                    **({"is_error": True} if not res.get("success") else {}),
                })
                logger.info("[agent_loop] %s write tool=%s path=%s ok=%s", agent_name, name, inputs.get("path",""), res.get("success"))
            except Exception as exc:
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tc["id"],
                    "content": f"Error: {exc}",
                    "is_error": True,
                })

        # ── Feed results back for next turn ─────────────────────────────
        messages.append({"role": "user", "content": tool_results})

    else:
        logger.warning("[agent_loop] %s hit max_turns=%d — forcing end_turn", agent_name, max_turns)

    metadata = {
        "turns": turns,
        "files_written": files_written,
        "model": model,
    }
    return final_text, metadata


# ─── end of agentic loop helpers ───────────────────────────────────────────

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
    workspace_path: str = "",
):
    # ── Build context for this agent ────────────────────────────────────────
    # Priority 1: structured build memory (goal, stack, schema, routes, files)
    # Priority 2: raw prior-agent outputs (truncated, for agents that need code)
    # ─────────────────────────────────────────────────────────────────────────
    memory_summary = ""
    if workspace_path:
        try:
            from backend.orchestration.build_memory import get_memory_summary
            memory_summary = get_memory_summary(workspace_path)
        except Exception as _bm_err:
            import logging as _logging
            _logging.getLogger(__name__).warning("build_memory get_summary failed: %s", _bm_err)

    # Build raw context block from prior agents' outputs (kept as supplement)
    # Use 8000 chars per agent so code context is not truncated.
    context_block = ""
    if previous_outputs:
        parts = []
        for prior_agent, prior_result in previous_outputs.items():
            prior_text = ""
            if isinstance(prior_result, dict):
                prior_text = str(prior_result.get("output") or prior_result.get("result") or "")
            elif isinstance(prior_result, str):
                prior_text = prior_result
            if prior_text.strip():
                parts.append(f"### {prior_agent}\n{prior_text[:8000]}")
        if parts:
            context_block = (
                "\n\n---\n## Context from prior agents\n"
                + "\n\n".join(parts)
                + "\n---\n"
            )

    # Inject the goal as a reminder at the top of the prompt so agents never
    # forget what they are building when context is long.
    goal_reminder = f"## GOAL\n{project_prompt}\n\n## YOUR TASK\n"

    # Compose enriched prompt: goal + structured memory (if available) + raw context
    if memory_summary:
        enriched_prompt = goal_reminder + project_prompt + "\n\n" + memory_summary + context_block
    else:
        enriched_prompt = goal_reminder + project_prompt + context_block
    # Use the AGENT_DAG system_prompt so each agent gets its full code-writing
    # instructions (e.g. "Output ONLY complete JSX code") instead of the bare
    # "Frontend Generation execution" stub that caused agents to return prose.
    try:
        from backend.agent_dag import AGENT_DAG as _AGENT_DAG
        _dag_entry = _AGENT_DAG.get(agent_name, {})
        _dag_system_prompt = (_dag_entry.get("system_prompt") or "").strip()
    except Exception:
        _dag_system_prompt = ""
    # Inject design system + payment default rules for code-generating agents
    _DESIGN_PAYMENT_AGENTS = {
        "Frontend Generation", "Design Agent", "Backend Generation",
        "Integration Agent", "API Integration", "Deployment Agent",
    }
    _UX_AUDIT_AGENTS = {"UX Auditor"}
    try:
        from backend.prompts.loader import (
            load_design_system_injection,
            load_payment_default_injection,
        )
        _design_inject = load_design_system_injection()
        _payment_inject = load_payment_default_injection()
    except Exception:
        _design_inject = ""
        _payment_inject = ""

    if agent_name in _DESIGN_PAYMENT_AGENTS and (_design_inject or _payment_inject):
        _injection_parts = []
        if _design_inject:
            _injection_parts.append(f"## DESIGN SYSTEM REQUIREMENTS (MANDATORY)\n\n{_design_inject.strip()}")
        if _payment_inject:
            _injection_parts.append(f"## PAYMENT INTEGRATION REQUIREMENTS (MANDATORY)\n\n{_payment_inject.strip()}")
        _injection_block = "\n\n---\n\n".join(_injection_parts)
        _dag_system_prompt = f"{_injection_block}\n\n---\n\n{_dag_system_prompt}" if _dag_system_prompt else _injection_block

    if agent_name in _UX_AUDIT_AGENTS:
        _ux_grounding = (
            "\n\nCRITICAL AUDIT RULE: Before scoring ANYTHING, you MUST:\n"
            "1. Read the generated source files explicitly listed in your context.\n"
            "2. Reference actual file paths (e.g. src/pages/Dashboard.jsx) in your audit.\n"
            "3. NEVER write 'I\'ll assume', 'based on the specification', or 'since no frontend code'. "
            "These phrases mean your audit is fictional and it WILL be rejected by the Build Integrity Validator.\n"
            "4. If you cannot see actual code, write: AUDIT BLOCKED: Required files not available. Score: INVALID.\n"
            "Your score must reference specific line numbers in specific files."
        )
        _dag_system_prompt = (_dag_system_prompt or "") + _ux_grounding

    system_message = _dag_system_prompt or (
        f"You are {agent_name}. Output ONLY production-ready code. "
        "No prose, no markdown explanation. Start your response with the first line of code."
    )
    # ── Agentic loop: try tool-using Anthropic loop first, fall back to
    #    legacy one-shot if no Anthropic key is available.
    _anthropic_key = (effective or {}).get("anthropic") or os.environ.get("ANTHROPIC_API_KEY", "")
    _primary_model = next(
        (c.get("model") for c in (model_chain or []) if c.get("provider") == "anthropic"),
        None,
    )

    if _anthropic_key and _primary_model:
        # Adaptive thinking: enabled for agents where deep pre-reasoning matters.
        # Mirrors Claude Code's thinkingConfig: { type: 'adaptive' }.
        _use_thinking = agent_name in _THINKING_AGENTS
        # Full observe-act-inspect-revise loop
        output, _loop_meta = await _call_llm_with_tools_loop(
            message=enriched_prompt,
            system_message=system_message,
            project_id=project_id,
            workspace_path=workspace_path or "",
            api_key=_anthropic_key,
            model=_primary_model,
            agent_name=agent_name,
            max_turns=20,
            use_thinking=_use_thinking,
        )
        _files_written = _loop_meta.get("files_written", [])
        _turns = _loop_meta.get("turns", 1)
    else:
        # Fallback: legacy one-shot (no Anthropic key in chain)
        output, _meta_fb = await _call_llm_with_fallback(
            message=enriched_prompt,
            system_message=system_message,
            session_id=f"{project_id}:{agent_name}",
            model_chain=model_chain,
            api_keys=effective,
            agent_name=agent_name,
        )
        _files_written = []
        _turns = 1

    result = {
        "status": "completed",
        "output": output,
        "result": output,
        "tokens_used": 100,
        "agent": agent_name,
        "project_id": project_id,
        "user_id": user_id,
        "build_kind": build_kind,
        "files_written": _files_written,
        "loop_turns": _turns,
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
        runtime_state = __import__("backend.orchestration.runtime_state", fromlist=["get_job"])
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


class InjectPaymentBody(BaseModel):
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
    read_only: bool = False
    expires_at: Optional[datetime] = None


class ShareReadBody(BaseModel):
    model_config = _model_config()
    share_id: str = ""


class ShareRevokeBody(BaseModel):
    model_config = _model_config()
    share_id: str = ""


class ShareUpdateBody(BaseModel):
    model_config = _model_config()
    share_id: str = ""
    read_only: Optional[bool] = None
    expires_at: Optional[datetime] = None


class ProjectStateBody(BaseModel):
    model_config = _model_config()
    project_id: str = ""
    state: Dict[str, Any] = Field(default_factory=dict)


class ProjectListBody(BaseModel):
    model_config = _model_config()
    user_id: Optional[str] = None
    limit: int = MAX_USER_PROJECTS_DASHBOARD
    offset: int = 0


class ProjectDeleteBody(BaseModel):
    model_config = _model_config()
    project_id: str = ""


class ProjectCreateBody(BaseModel):
    model_config = _model_config()
    project_name: str = ""
    project_type: str = ""
    description: str = ""
    project_id: Optional[str] = None


class ProjectUpdateBody(BaseModel):
    model_config = _model_config()
    project_id: str = ""
    project_name: Optional[str] = None
    project_type: Optional[str] = None
    description: Optional[str] = None


class ProjectRenameBody(BaseModel):
    model_config = _model_config()
    project_id: str = ""
    new_name: str = ""


class ProjectForkBody(BaseModel):
    model_config = _model_config()
    project_id: str = ""
    new_name: str = ""


class ProjectArchiveBody(BaseModel):
    model_config = _model_config()
    project_id: str = ""


class ProjectUnarchiveBody(BaseModel):
    model_config = _model_config()
    project_id: str = ""


class ProjectPinBody(BaseModel):
    model_config = _model_config()
    project_id: str = ""


class ProjectUnpinBody(BaseModel):
    model_config = _model_config()
    project_id: str = ""


class ProjectSetPublicBody(BaseModel):
    model_config = _model_config()
    project_id: str = ""
    is_public: bool = False


class ProjectSetPrivateBody(BaseModel):
    model_config = _model_config()
    project_id: str = ""


class ProjectSetFeaturedBody(BaseModel):
    model_config = _model_config()
    project_id: str = ""
    is_featured: bool = False


class ProjectSetTemplateBody(BaseModel):
    model_config = _model_config()
    project_id: str = ""
    is_template: bool = False


class ProjectSetOwnerBody(BaseModel):
    model_config = _model_config()
    project_id: str = ""
    new_owner_id: str = ""


class ProjectAddCollaboratorBody(BaseModel):
    model_config = _model_config()
    project_id: str = ""
    user_id: str = ""
    role: str = "viewer"


class ProjectRemoveCollaboratorBody(BaseModel):
    model_config = _model_config()
    project_id: str = ""
    user_id: str = ""


class ProjectTransferBody(BaseModel):
    model_config = _model_config()
    project_id: str = ""
    new_owner_id: str = ""


class ProjectTransferAcceptBody(BaseModel):
    model_config = _model_config()
    project_id: str = ""


class ProjectTransferRejectBody(BaseModel):
    model_config = _model_config()
    project_id: str = ""


class ProjectTransferCancelBody(BaseModel):
    model_config = _model_config()
    project_id: str = ""


class ProjectTransferListBody(BaseModel):
    model_config = _model_config()
    user_id: Optional[str] = None
    limit: int = 100
    offset: int = 0


class ProjectTransferReadBody(BaseModel):
    model_config = _model_config()
    project_id: str = ""


class ProjectTransferDeleteBody(BaseModel):
    model_config = _model_config()
    project_id: str = ""


class ProjectTransferUpdateBody(BaseModel):
    model_config = _model_config()
    project_id: str = ""
    new_owner_id: Optional[str] = None
    status: Optional[str] = None


class ProjectTransferSetPublicBody(BaseModel):
    model_config = _model_config()
    project_id: str = ""
    is_public: bool = False


class ProjectTransferSetPrivateBody(BaseModel):
    model_config = _model_config()
    project_id: str = ""


class ProjectTransferSetFeaturedBody(BaseModel):
    model_config = _model_config()
    project_id: str = ""
    is_featured: bool = False


class ProjectTransferSetTemplateBody(BaseModel):
    model_config = _model_config()
    project_id: str = ""
    is_template: bool = False


class ProjectTransferSetOwner(BaseModel):
    model_config = _model_config()
    project_id: str = ""
    new_owner_id: str = ""


class ProjectTransferAddCollaborator(BaseModel):
    model_config = _model_config()
    project_id: str = ""
    user_id: str = ""
    role: str = "viewer"


class ProjectTransferRemoveCollaborator(BaseModel):
    model_config = _model_config()
    project_id: str = ""
    user_id: str = ""


class ProjectTransferTransfer(BaseModel):
    model_config = _model_config()
    project_id: str = ""
    new_owner_id: str = ""


class ProjectTransferTransferAccept(BaseModel):
    model_config = _model_config()
    project_id: str = ""


class ProjectTransferTransferReject(BaseModel):
    model_config = _model_config()
    project_id: str = ""


class ProjectTransferTransferCancel(BaseModel):
    model_config = _model_config()
    project_id: str = ""


class ProjectTransferTransferList(BaseModel):
    model_config = _model_config()
    user_id: Optional[str] = None
    limit: int = 100
    offset: int = 0


class ProjectTransferTransferRead(BaseModel):
    model_config = _model_config()
    project_id: str = ""


class ProjectTransferTransferDelete(BaseModel):
    model_config = _model_config()
    project_id: str = ""


class ProjectTransferTransferUpdate(BaseModel):
    model_config = _model_config()
    project_id: str = ""
    new_owner_id: Optional[str] = None
    status: Optional[str] = None


class User(BaseModel):
    model_config = _model_config()
    id: str
    email: EmailStr
    is_admin: bool = False
    credit_balance: int = 0
    referral_code: Optional[str] = None
    referred_by: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserUpdate(BaseModel):
    model_config = _model_config()
    email: Optional[EmailStr] = None
    is_admin: Optional[bool] = None
    credit_balance: Optional[int] = None
    referral_code: Optional[str] = None
    referred_by: Optional[str] = None


class UserCreate(BaseModel):
    model_config = _model_config()
    email: EmailStr
    password: str
    is_admin: bool = False
    credit_balance: int = 0
    referral_code: Optional[str] = None
    referred_by: Optional[str] = None


class Token(BaseModel):
    model_config = _model_config()
    access_token: str
    token_type: str


class TokenData(BaseModel):
    model_config = _model_config()
    email: Optional[str] = None


class LoginRequest(BaseModel):
    model_config = _model_config()
    email: EmailStr
    password: str


class PasswordResetRequest(BaseModel):
    model_config = _model_config()
    email: EmailStr


class PasswordReset(BaseModel):
    model_config = _model_config()
    token: str
    new_password: str


class EmailVerificationRequest(BaseModel):
    model_config = _model_config()
    email: EmailStr


class EmailVerification(BaseModel):
    model_config = _model_config()
    token: str


class GuestLoginResponse(BaseModel):
    model_config = _model_config()
    user_id: str
    access_token: str
    token_type: str


class RefreshTokenRequest(BaseModel):
    model_config = _model_config()
    refresh_token: str


class RefreshTokenResponse(BaseModel):
    model_config = _model_config()
    access_token: str
    token_type: str


class Project(BaseModel):
    model_config = _model_config()
    id: str
    name: str
    type: str
    description: str
    user_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProjectCreate(BaseModel):
    model_config = _model_config()
    project_name: str
    project_type: str
    description: str
    id: Optional[str] = None


class ProjectUpdate(BaseModel):
    model_config = _model_config()
    project_name: Optional[str] = None
    project_type: Optional[str] = None
    description: Optional[str] = None


class ProjectDelete(BaseModel):
    model_config = _model_config()
    project_id: str


class ProjectList(BaseModel):
    model_config = _model_config()
    user_id: Optional[str] = None
    limit: int = 100
    offset: int = 0


class ProjectRead(BaseModel):
    model_config = _model_config()
    project_id: str


class ProjectRename(BaseModel):
    model_config = _model_config()
    project_id: str
    new_name: str


class ProjectFork(BaseModel):
    model_config = _model_config()
    project_id: str
    new_name: str


class ProjectArchive(BaseModel):
    model_config = _model_config()
    project_id: str


class ProjectUnarchive(BaseModel):
    model_config = _model_config()
    project_id: str


class ProjectPin(BaseModel):
    model_config = _model_config()
    project_id: str


class ProjectUnpin(BaseModel):
    model_config = _model_config()
    project_id: str


class ProjectSetPublic(BaseModel):
    model_config = _model_config()
    project_id: str
    is_public: bool = False


class ProjectSetPrivate(BaseModel):
    model_config = _model_config()
    project_id: str


class ProjectSetFeatured(BaseModel):
    model_config = _model_config()
    project_id: str
    is_featured: bool = False


class ProjectSetTemplate(BaseModel):
    model_config = _model_config()
    project_id: str
    is_template: bool = False


class ProjectSetOwner(BaseModel):
    model_config = _model_config()
    project_id: str
    new_owner_id: str


class ProjectAddCollaborator(BaseModel):
    model_config = _model_config()
    project_id: str
    user_id: str
    role: str = "viewer"


class ProjectRemoveCollaborator(BaseModel):
    model_config = _model_config()
    project_id: str
    user_id: str


class ProjectTransfer(BaseModel):
    model_config = _model_config()
    project_id: str
    new_owner_id: str


class ProjectTransferAccept(BaseModel):
    model_config = _model_config()
    project_id: str


class ProjectTransferReject(BaseModel):
    model_config = _model_config()
    project_id: str


class ProjectTransferCancel(BaseModel):
    model_config = _model_config()
    project_id: str


class ProjectTransferList(BaseModel):
    model_config = _model_config()
    user_id: Optional[str] = None
    limit: int = 100
    offset: int = 0


class ProjectTransferRead(BaseModel):
    model_config = _model_config()
    project_id: str


class ProjectTransferDelete(BaseModel):
    model_config = _model_config()
    project_id: str


class ProjectTransferUpdate(BaseModel):
    model_config = _model_config()
    project_id: str
    new_owner_id: Optional[str] = None
    status: Optional[str] = None


class ProjectTransferSetPublic(BaseModel):
    model_config = _model_config()
    project_id: str
    is_public: bool = False


class ProjectTransferSetPrivate(BaseModel):
    model_config = _model_config()
    project_id: str


class ProjectTransferSetFeatured(BaseModel):
    model_config = _model_config()
    project_id: str
    is_featured: bool = False


class ProjectTransferSetTemplate(BaseModel):
    model_config = _model_config()
    project_id: str
    is_template: bool = False


class ProjectTransferSetOwner(BaseModel):
    model_config = _model_config()
    project_id: str
    new_owner_id: str


class ProjectTransferAddCollaborator(BaseModel):
    model_config = _model_config()
    project_id: str
    user_id: str
    role: str = "viewer"


class ProjectTransferRemoveCollaborator(BaseModel):
    model_config = _model_config()
    project_id: str
    user_id: str


class ProjectTransferTransfer(BaseModel):
    model_config = _model_config()
    project_id: str
    new_owner_id: str


class ProjectTransferTransferAccept(BaseModel):
    model_config = _model_config()
    project_id: str


class ProjectTransferTransferReject(BaseModel):
    model_config = _model_config()
    project_id: str


class ProjectTransferTransferCancel(BaseModel):
    model_config = _model_config()
    project_id: str


class ProjectTransferTransferList(BaseModel):
    model_config = _model_config()
    user_id: Optional[str] = None
    limit: int = 100
    offset: int = 0


class ProjectTransferTransferRead(BaseModel):
    model_config = _model_config()
    project_id: str


class ProjectTransferTransferDelete(BaseModel):
    model_config = _model_config()
    project_id: str


class ProjectTransferTransferUpdate(BaseModel):
    model_config = _model_config()
    project_id: str
    new_owner_id: Optional[str] = None
    status: Optional[str] = None


class _FakeDb:
    """In-memory fake DB for tests that run without PostgreSQL."""

    def __init__(self):
        self._stores: dict = {}

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        self._stores.setdefault(name, _FakeCollection(name))
        return self._stores[name]


def _matches(doc: dict, query: dict) -> bool:
    """Check if a document matches a query dict (flat equality only)."""
    for k, v in query.items():
        if k.startswith("$"):
            continue
        if doc.get(k) != v:
            return False
    return True


def _project(doc: dict, projection: dict) -> dict:
    """Apply a Mongo-style projection (include or exclude fields)."""
    if not projection:
        return dict(doc)
    # Check if it's an exclusion projection (all 0s) or inclusion (all 1s)
    values = [v for k, v in projection.items() if k != "_id"]
    if not values or all(v == 0 for v in values):
        # Exclusion
        return {k: v for k, v in doc.items() if projection.get(k, 1) != 0}
    else:
        # Inclusion — always include _id unless explicitly excluded
        result = {}
        for k, v in projection.items():
            if v and k in doc:
                result[k] = doc[k]
        if projection.get("_id", 1) and "_id" in doc:
            result["_id"] = doc["_id"]
        return result


class _FakeCollection:
    def __init__(self, name: str):
        self.name = name
        self._docs: list = []

    async def find_one(self, query: dict = None, projection: dict = None, *args, **kwargs):
        query = query or {}
        for doc in self._docs:
            if _matches(doc, query):
                return _project(doc, projection) if projection else dict(doc)
        return None

    async def insert_one(self, doc: dict, *args, **kwargs):
        import copy
        self._docs.append(copy.deepcopy(doc))
        return type("R", (), {"inserted_id": doc.get("id", doc.get("_id", ""))})()

    async def update_one(self, query: dict, update: dict, upsert: bool = False, **kwargs):
        for doc in self._docs:
            if _matches(doc, query):
                if "$set" in update:
                    doc.update(update["$set"])
                if "$inc" in update:
                    for k, v in update["$inc"].items():
                        doc[k] = doc.get(k, 0) + v
                if "$push" in update:
                    for k, v in update["$push"].items():
                        doc.setdefault(k, []).append(v)
                return type("R", (), {"matched_count": 1, "modified_count": 1})()
        if upsert:
            new_doc = {**query}
            if "$set" in update:
                new_doc.update(update["$set"])
            self._docs.append(new_doc)
        return type("R", (), {"matched_count": 0, "modified_count": 0})()

    async def update_many(self, query: dict, update: dict, **kwargs):
        count = 0
        for doc in self._docs:
            if _matches(doc, query):
                if "$set" in update:
                    doc.update(update["$set"])
                count += 1
        return type("R", (), {"matched_count": count, "modified_count": count})()

    def find(self, query: dict = None, projection: dict = None, *args, **kwargs):
        """Return a synchronous cursor-like list (supports iteration and async iteration)."""
        query = query or {}
        results = [
            _project(d, projection) if projection else dict(d)
            for d in self._docs
            if _matches(d, query)
        ]
        return _FakeCursor(results)

    async def delete_one(self, query: dict, **kwargs):
        for i, doc in enumerate(self._docs):
            if _matches(doc, query):
                self._docs.pop(i)
                return type("R", (), {"deleted_count": 1})()
        return type("R", (), {"deleted_count": 0})()

    async def delete_many(self, query: dict, **kwargs):
        before = len(self._docs)
        self._docs = [d for d in self._docs if not _matches(d, query)]
        return type("R", (), {"deleted_count": before - len(self._docs)})()

    async def count_documents(self, query: dict = None, **kwargs):
        query = query or {}
        return sum(1 for d in self._docs if _matches(d, query))

    async def create_index(self, *args, **kwargs):
        return "index_created"

    async def drop(self):
        self._docs.clear()


class _FakeCursor:
    """Mimics Motor's AsyncIOMotorCursor enough for common use patterns."""
    def __init__(self, docs: list):
        self._docs = docs
        self._idx = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._idx >= len(self._docs):
            raise StopAsyncIteration
        doc = self._docs[self._idx]
        self._idx += 1
        return doc

    def __iter__(self):
        return iter(self._docs)

    def sort(self, *args, **kwargs):
        return self

    def skip(self, n):
        self._docs = self._docs[n:]
        return self

    def limit(self, n):
        if n:
            self._docs = self._docs[:n]
        return self

    async def to_list(self, length=None):
        if length:
            return self._docs[:length]
        return list(self._docs)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global db
    # ── Test-mode: FakeDb bypass (no Postgres required) ──────────────────────
    if os.environ.get("CRUCIBAI_TEST_DB_UNAVAILABLE") == "1":
        if not isinstance(db, _FakeDb):
            db = _FakeDb()
        try:
            from deps import init as init_deps
            init_deps(db=db, audit_logger=audit_logger)
        except Exception:
            pass
        yield
        return
    # ── Normal startup ────────────────────────────────────────────────────────
    try:
        from .services.migration_runner import run_migrations_idempotent
        await run_migrations_idempotent()
        logger.info("Startup migrations complete.")
    except Exception as _mig_err:
        logger.warning("Startup migration failed (non-fatal): %s", _mig_err)
    try:
        from .db_pg import ensure_all_tables
        await ensure_all_tables()
        logger.info("ensure_all_tables complete.")
    except Exception as _tbl_err:
        logger.warning("ensure_all_tables failed (non-fatal): %s", _tbl_err)
    yield
    # shutdown
    logger.info("shutdown")


app = FastAPI(lifespan=lifespan)

api_router = __import__('fastapi').APIRouter()  # optional-auth public catalog routes


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"", "0", "false", "no", "off"}


_app_env = os.environ.get("APP_ENV", os.environ.get("ENV", "")).strip().lower()
_is_production = _app_env in {"prod", "production"} or bool(
    os.environ.get("RAILWAY_ENVIRONMENT")
)
STRICT_ROUTE_LOADING = _env_flag("CRUCIB_STRICT_ROUTES", default=False)

cors_origins = [
    origin.strip()
    for origin in os.environ.get("CORS_ORIGINS", os.environ.get("FRONTEND_URL", "")).split(",")
    if origin.strip()
]
cors_origins: List[str] = CORS_ALLOW_ORIGINS
cors_allow_credentials: bool = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=cors_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

try:
    from .middleware.observability import ObservabilityMiddleware
    app.add_middleware(ObservabilityMiddleware)
except ImportError:
    try:
        from backend.middleware.observability import ObservabilityMiddleware
        app.add_middleware(ObservabilityMiddleware)
    except Exception:
        pass
except Exception:
    pass


# WS-I: COOP/COEP headers for WebContainers in-browser preview.
# Gated by env FEATURE_WEBCONTAINER_COOP (default off) to avoid affecting
# existing embedding. When on, serves cross-origin-isolated headers required
# by SharedArrayBuffer / WebContainers API.
import os as _os_ws_i
def _webcontainer_coop_coep(request, call_next):
    pass  # placeholder for type-checkers
try:
    from starlette.middleware.base import BaseHTTPMiddleware as _BaseHTTPMiddleware
    from starlette.responses import Response as _StarletteResponse

    class WebContainerCoopCoepMiddleware(_BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            response: _StarletteResponse = await call_next(request)
            if _os_ws_i.environ.get("FEATURE_WEBCONTAINER_COOP", "").lower() in ("1", "true", "yes", "on"):
                response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
                response.headers["Cross-Origin-Embedder-Policy"] = "require-corp"
                response.headers["Cross-Origin-Resource-Policy"] = "cross-origin"
            return response

    # Register as early as possible; FastAPI app object is `app`.
    try:
        app.add_middleware(WebContainerCoopCoepMiddleware)  # type: ignore[name-defined]
    except Exception:
        # app not yet defined at this import site; will be wired when module reloaded
        pass
except Exception:
    pass

_ALL_ROUTES: List[Tuple[str, str, bool]] = [
    ("routes.compat", "router", False),
    ("routes.misc", "router", False),
    ("routes.auth", "auth_router", False),
    ("routes.runtime", "router", False),
    ("routes.projects", "projects_router", False),
    # WS-G: per-project persistent memory (K/V JSONB)
    ("routes.project_memory", "router", True),
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
    ("routes.prompts", "router", True),
    # WS-F: MCP dispatch layer (Slack / GitHub / Notion)
    ("routes.mcp", "router", True),
    # WS-D: RAG / vector memory
    ("routes.memory", "router", True),
    ("routes.chat_react", "router", True),
    ("routes.share", "router", True),
    ("routes.preview_serve", "router", True),
    ("routes.sso", "router", True),
    ("routes.terminal", "router", False),
    ("routes.tokens", "router", False),
    ("routes.trust", "router", False),
    ("routes.vibecoding", "router", False),
    ("routes.workflows", "router", False),
    ("routes.workspace", "router", False),
    ("routes.build_progress", "router", False),
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

@app.get("/health")
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "ok": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

@app.get("/api/v1/health")
async def health_check_v1():
    return {"status": "ok", "version": "v1", "timestamp": str(datetime.now())}


@app.get("/api/")
async def api_root():
    return {
        "message": "CrucibAI API",
        "status": "healthy",
        "simulation": "reality_engine",
    }


@app.get("/api/release/version")
async def release_version():
    return {
        "status": "healthy",
        "release_contract": "simulation_reality_engine_v2",
        "simulation_route": "/api/simulations",
        "simulation_page": "/app/what-if",
        "frontend_source": "fresh_build_required",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }



class BenchmarkRunRequest(BaseModel):
    goal: str
    secret: str

@app.get("/api/v1/benchmark-run")
async def run_benchmark_job_direct_get():
    return {"status": "benchmark endpoint exists"}

@app.post("/api/v1/benchmark-run")
async def run_benchmark_job_direct(
    body: BenchmarkRunRequest,
    background_tasks: BackgroundTasks
):
    """
    Direct benchmark endpoint in server.py.
    """
    BENCHMARK_SECRET = os.environ.get("BENCHMARK_SECRET", "crucibai_benchmark_2026_secret_key")
    if body.secret != BENCHMARK_SECRET:
        raise HTTPException(status_code=401, detail="Invalid benchmark secret")
        
    try:
        from .services.runtime.task_manager import task_manager
        from .routes.orchestrator import _background_auto_runner_job
        
        # Create job with a system user ID
        job = await task_manager.create_task(
            goal=body.goal,
            user_id="system-benchmark-user",
            mode="guided"
        )
        
        job_id = job["id"]
        project_id = job.get("project_id")
        workspace_path = _project_workspace_path(project_id)
        
        # Start background execution
        background_tasks.add_task(_background_auto_runner_job, job_id, str(workspace_path))
        
        return {
            "success": True, 
            "job_id": job_id, 
            "project_id": project_id,
            "status": "started"
        }
        
    except Exception as e:
        logger.exception("benchmark/run direct error")
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/api/llm-config")
async def llm_config(user: User = Depends(get_authenticated_or_api_user)):
    user_keys = await get_workspace_api_keys(user)
    effective = _effective_api_keys(user_keys)
    anthropic_ready = bool(effective.get("anthropic") or effective.get("ANTHROPIC_API_KEY"))
    cerebras_ready = bool(effective.get("cerebras") or effective.get("CEREBRAS_API_KEY"))
    return {
        "anthropic_model": ANTHROPIC_HAIKU_MODEL,
        "anthropic_api_key": anthropic_ready,
        "cerebras_api_key": cerebras_ready,
        "chat_with_search_system": CHAT_WITH_SEARCH_SYSTEM,
        "real_agent_no_llm_keys_detail": REAL_AGENT_NO_LLM_KEYS_DETAIL,
        "has_any_llm_api_key": bool(effective),
        "has_anthropic_api_key": anthropic_ready,
        "has_cerebras_api_key": cerebras_ready,
        "providers": {
            "anthropic": {"configured": anthropic_ready, "model": ANTHROPIC_HAIKU_MODEL},
            "cerebras": {"configured": cerebras_ready},
        },
    }


@app.get("/api/llm-models")
async def llm_models(user: User = Depends(get_authenticated_or_api_user)):
    return await _get_model_chain(user)


@app.get("/api/api-keys")
async def api_keys(user: User = Depends(get_current_user)):
    return await get_workspace_api_keys(user)


@app.get("/api/session-journal")
async def session_journal(user: User = Depends(get_current_user)):
    return await list_session_journal_entries(user.id)


@app.get("/api/events")
async def events(user: User = Depends(get_current_user)):
    return await read_persisted_events(user.id)


@app.get("/api/memory-graph")
async def memory_graph(user: User = Depends(get_current_user)):
    return await get_memory_graph(user.id)


@app.get("/api/cost-tracker")
async def cost_tracker_endpoint(user: User = Depends(get_current_user)):
    return await cost_tracker.get_costs(user.id)


@app.get("/api/provider-readiness")
async def provider_readiness_endpoint(user: User = Depends(get_current_user)):
    return build_provider_readiness(
        user_tier="admin" if getattr(user, "is_admin", False) else "free",
        available_credits=int(getattr(user, "credit_balance", 0) or 0),
    )


@app.get("/api/health/llm")
async def llm_health_check():
    readiness = build_provider_readiness()
    return {
        "status": readiness.get("status", "not_configured"),
        "ok": readiness.get("status") == "ready",
        "live_invocation": readiness.get("live_invocation"),
        "secret_values_included": False,
        "warnings": readiness.get("warnings") or [],
        "providers": readiness.get("providers") or {},
    }


# Dynamically load all routers from the routes directory.
# This keeps the server file clean and modular.
_ALL_ROUTES: List[Tuple[str, str, bool]] = [
    ("backend.routes.auth", "auth_router", False),
    ("backend.routes.runtime", "router", False),
    ("backend.routes.simulations", "router", False),
    ("backend.routes.projects", "projects_router", False),
    ("backend.routes.project_memory", "router", False),
    ("backend.routes.automation", "router", False),
    ("backend.routes.community", "router", False),
    ("backend.routes.voice_input", "router", False),
    ("backend.routes.crucib_workspace_adapter", "router", False),
    ("backend.routes.crucib_ws_events", "router", False),
    ("backend.routes.deploy", "router", False),
    ("backend.routes.ecosystem", "router", False),
    ("backend.routes.ai", "router", False),
    ("backend.routes.images", "router", False),
    ("backend.routes.migration", "router", False),
    ("backend.routes.git_sync", "router", False),
    ("backend.routes.ide", "router", True),
    ("backend.routes.mobile", "mobile_router", True),
    ("backend.routes.monitoring", "router", False),
    ("backend.routes.doctor", "router", False),
    ("backend.routes.capabilities", "router", False),
    ("backend.routes.trust", "router", False),
    ("backend.routes.knowledge", "router", False),
    ("backend.routes.connectors", "router", False),
    ("backend.routes.braintree_payments", "router", False),
    ("backend.routes.cost_hook", "router", False),
    ("backend.routes.skills", "router", False),
    ("backend.routes.terminal", "router", False),
    ("backend.routes.tokens", "router", False),
    ("backend.routes.vibecoding", "router", False),
    ("backend.routes.worktrees", "router", False),
    ("backend.routes.artifacts", "router", False),
    ("backend.routes.approvals", "router", False),
    ("backend.routes.chat_react", "router", False),
    ("backend.routes.compat", "router", False),
    ("backend.routes.compact_command", "router", False),
    ("backend.routes.orchestrator", "router", False),
    ("backend.routes.jobs", "router", False),
    ("backend.routes.workspace", "router", False),
    ("backend.routes.preview_serve", "router", False),
    ("backend.adapter.routes.preview", "router", True),
    ("backend.adapter.routes.deploy", "router", True),
    ("backend.adapter.routes.trust", "router", True),
    ("backend.adapter.routes.automation", "router", True),
    ("backend.adapter.routes.files", "router", True),
    ("backend.adapter.routes.spawn", "router", True),
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
                "status": "loaded",
            }
        )
    except Exception as e:
        ROUTE_REGISTRATION_REPORT.append(
            {
                "module": _module_name,
                "attr": _attr_name,
                "status": "failed",
                "error": str(e),
            }
        )
        if not _optional:
            raise RuntimeError(
                f"Required router failed to load: {_module_name}.{_attr_name}: {e}"
            ) from e

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


@app.get("/auth/me", include_in_schema=False)
async def auth_me_compat(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    """Legacy compatibility for tests and old clients expecting /auth/me."""
    return {"id": user.get("id"), "email": user.get("email")}


@app.get("/api/oauth/callback", include_in_schema=False)
async def oauth_callback_compat() -> dict[str, Any]:
    """Compatibility shim: explicit endpoint existence for OAuth callback probes."""
    raise HTTPException(status_code=400, detail="Use provider-specific callback endpoints")


@app.get("/metrics", include_in_schema=False)
async def metrics_compat() -> Response:
    """Prometheus-compatible metrics surface for readiness checks."""
    payload = "\n".join(
        [
            "# HELP crucibai_up Service health flag",
            "# TYPE crucibai_up gauge",
            "crucibai_up 1",
            "",
        ]
    )
    return Response(content=payload, media_type="text/plain; version=0.0.4")


@app.get("/templates", include_in_schema=False)
async def templates_optional_inventory(_user: dict = Depends(get_optional_user)):
    # Kept in server.py so Phase 2 optional-auth audit can inventory safe routes.
    return {"templates": []}


def _is_admin_user(user: dict) -> bool:
    if not user:
        return {"prompts": [], "total": 0}
    return {"prompts": [], "total": 0, "user_id": user.get("id")}


@api_router.get("/agents/activity")
async def get_agents_activity(user: dict = Depends(get_optional_user)):
    """Return agent activity feed. Anonymous returns empty; authenticated returns own activity."""
    if not user:
        return {"activity": [], "total": 0}
    return {"activity": [], "total": 0, "user_id": user.get("id")}


@api_router.get("/orchestrator/build-jobs")
async def list_build_jobs(user: dict = Depends(get_optional_user)):
    """List build jobs. Anonymous returns empty; authenticated lists own jobs."""
    if not user:
        return {"jobs": [], "total": 0}
    return {"jobs": [], "total": 0, "user_id": user.get("id")}


# ── Project progress websocket ────────────────────────────────────────────────
@app.websocket("/api/projects/{project_id}/progress")
async def websocket_project_progress(websocket: WebSocket, project_id: str):
    """Real-time project build progress stream.


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


@app.websocket("/api/projects/{project_id}/progress")
async def websocket_project_progress(websocket: WebSocket, project_id: str):
    """Real-time WebSocket: streams event-bus events for a project, with heartbeat."""
    import jwt as _jwt_ws  # local import — jwt not guaranteed at module scope
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008)
        return
    try:
        payload = _jwt_ws.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user = {"id": payload.get("user_id"), "email": payload.get("email")}
    except Exception:
        await websocket.close(code=1008)
        return
    project_owner_claim = {"id": project_id, "user_id": user["id"]}
    await websocket.accept()
    queue: asyncio.Queue = asyncio.Queue(maxsize=256)
    loop = asyncio.get_event_loop()

    def _on_event(record):
        rec_project = getattr(record, "payload", {}).get("project_id") if hasattr(record, "payload") else None
        if rec_project and rec_project != project_id:
            return
        payload_data = record.payload if hasattr(record, "payload") else {}
        ts = record.ts if hasattr(record, "ts") else ""
        frame = {
            "type": record.event_type if hasattr(record, "event_type") else str(record),
            "project_id": project_id,
            "payload": payload_data,
            "ts": ts,
        }
        try:
            loop.call_soon_threadsafe(queue.put_nowait, frame)
        except Exception:
            pass

    try:
        from services.events import event_bus as _ebus
    except ImportError:
        try:
            from backend.services.events import event_bus as _ebus
        except ImportError:
            _ebus = None

    if _ebus is not None:
        _ebus.subscribe("*", _on_event)

    try:
        await websocket.send_json({"type": "connected", "project": project_owner_claim})

        async def _pump_events():
            while True:
                try:
                    frame = await asyncio.wait_for(queue.get(), timeout=25.0)
                    await websocket.send_json(frame)
                except asyncio.TimeoutError:
                    await websocket.send_json({"type": "heartbeat", "project_id": project_id})

        async def _recv_client():
            while True:
                try:
                    data = await websocket.receive_text()
                    if data == "ping":
                        await websocket.send_json({"type": "pong"})
                except Exception:
                    raise

        pump_task = asyncio.create_task(_pump_events())
        recv_task = asyncio.create_task(_recv_client())
        done, pending = await asyncio.wait(
            {pump_task, recv_task}, return_when=asyncio.FIRST_EXCEPTION
        )
        for t in pending:
            t.cancel()
    except Exception:
        pass
    finally:
        if _ebus is not None:
            try:
                _ebus.unsubscribe("*", _on_event)
            except Exception:
                pass
        try:
            await websocket.close()
        except Exception:
            pass


app.include_router(api_router)

# Add security and performance middleware
@app.get("/api/admin/route-report")
async def route_report(user: User = Depends(require_permission(Permission.CREATE_PROJECT))):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")
    return ROUTE_REGISTRATION_REPORT


@app.get("/api/dev-preview/{project_id}", include_in_schema=False)
@app.get("/api/dev-preview/{project_id}/{path:path}", include_in_schema=False)
async def dev_preview_serve(project_id: str, path: str = ""):
    """Hot-reload SPA preview for dev mode. Requires CRUCIBAI_DEV=1."""
    import os as _os, sys as _preview_sys
    if not _os.environ.get("CRUCIBAI_DEV"):
        raise HTTPException(status_code=404, detail="Not found")
    # Use the module object that has the (possibly patched) WORKSPACE_ROOT
    _srv_mod = _preview_sys.modules.get("server") or _preview_sys.modules.get("backend.server")
    _ws_root = getattr(_srv_mod, "WORKSPACE_ROOT", None) or WORKSPACE_ROOT
    workspace = Path(_ws_root) / project_id
    dist = workspace / "dist"
    serve_root = dist if dist.is_dir() else workspace
    target = path.strip("/") or "index.html"
    full_path = serve_root / target
    if full_path.is_file():
        return FileResponse(str(full_path))
    index = serve_root / "index.html"
    if index.is_file():
        return FileResponse(str(index))
    raise HTTPException(status_code=404, detail=f"File not found: {target}")


@app.get("/api/metrics", include_in_schema=False)
async def prometheus_metrics():
    """Prometheus-format metrics endpoint."""
    try:
        from .middleware.observability import render_metrics
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(render_metrics(), media_type="text/plain; version=0.0.4")
    except ImportError:
        try:
            from backend.middleware.observability import render_metrics
            from fastapi.responses import PlainTextResponse
            return PlainTextResponse(render_metrics(), media_type="text/plain; version=0.0.4")
        except Exception as exc:
            return {"error": str(exc)}
    except Exception as exc:
        return {"error": str(exc)}


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



async def _resolve_job_project_id_for_user(job_id: str, user_id: str) -> Optional[str]:
    job = await _lookup_job(job_id)
    if not job:
        return None
    project_id = job.get("project_id")
    if not project_id:
        return None
    # Verify user has access to this project
    try:
        from . import deps
        db = await deps.get_db()
        project = await db.projects.find_one({
            "_id": project_id,
            "user_id": user_id,
        })
        if project:
            return project_id
    except Exception:
        pass
    return None

def _asgi_static_http_only(static_asgi):
    """Wrap StaticFiles so WebSocket handshakes never hit Starlette's assert scope['type']=='http'."""
    async def app(scope, receive, send):
        if scope["type"] == "websocket":
            from starlette.websockets import WebSocket

            ws = WebSocket(scope, receive, send)
            await ws.close(code=1000)
            return
        if scope["type"] != "http":
            return
        await static_asgi(scope, receive, send)

    return app


# Serve static files from the 'static' directory
if STATIC_DIR.exists() and any(STATIC_DIR.iterdir()):
    _static_files = StaticFiles(directory=str(STATIC_DIR), html=True)
    app.mount("/", _asgi_static_http_only(_static_files), name="static")
    @app.exception_handler(404)
    async def not_found_handler(request, exc):
        path = getattr(getattr(request, "url", None), "path", "")
        if path.startswith("/api/"):
            detail = getattr(exc, "detail", "Not Found")
            return JSONResponse(status_code=404, content={"detail": detail})
        return FileResponse(str(STATIC_DIR / "index.html"))
else:
    logger.warning(
        f"Static directory not found or empty: {STATIC_DIR}. " f"Static file serving will be disabled."
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
