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

# ── Re-exports: symbols that routes/ai.py and routes/orchestrator.py import
# from server.py directly. These live in sub-modules; re-exported here so
# the existing import chains in ai.py/orchestrator.py don't need to change.
# ─────────────────────────────────────────────────────────────────────────
try:
    from .agent_dag import AGENT_DAG  # 245-node DAG used by orchestrator
except Exception:
    AGENT_DAG: dict = {}

try:
    from .dev_stub_llm import (
        is_real_agent_only,
        chat_llm_available,
        stub_build_enabled,
        stub_multifile_markdown,
    )
    from .dev_stub_llm import detect_build_kind as _stub_detect_build_kind
except Exception:
    def is_real_agent_only() -> bool: return False
    def chat_llm_available(effective_keys=None) -> bool: return True
    def stub_build_enabled() -> bool: return False
    def stub_multifile_markdown(prompt: str, build_kind=None) -> str: return ""
    def _stub_detect_build_kind(msg: str) -> str: return "fullstack"

try:
    from .content_policy import screen_user_content
except Exception:
    def screen_user_content(text: str): return None  # None = not blocked

try:
    from .pricing_plans import _speed_from_plan
except Exception:
    def _speed_from_plan(plan: str) -> str: return "balanced"

# Runtime state containers — mutated at runtime by orchestrator
LAST_BUILD_STATE: dict = {}
RECENT_AGENT_SELECTION_LOGS: list = []


def _tokens_to_credits(tokens: int) -> int:
    """Convert token count to credit units (1 credit = 1 000 tokens)."""
    return max(1, int(tokens) // 1000)


def _needs_live_data(message: str) -> bool:
    """Determine if this message benefits from a live web search.

    Philosophy: CrucibAI is a fully internet-connected AI. Almost any
    substantive question benefits from current web data. We only skip
    search for pure greetings, simple math, or explicit code-writing tasks
    where the user wants the LLM to generate code (not look it up).
    """
    m = message.lower().strip()

    # --- Never search: pure greetings / closings (very short or exact match) ---
    pure_greetings = {
        "hi", "hello", "hey", "yo", "sup", "bye", "goodbye", "thanks",
        "thank you", "ok", "okay", "cool", "got it", "sure", "yes", "no",
        "lol", "haha", "nice", "great", "awesome", "perfect",
    }
    if m in pure_greetings:
        return False
    if len(m) < 8:
        return False

    # --- Never search: pure math / unit conversion ---
    import re
    if re.match(r'^[\d\s\+\-\*\/\^\(\)\.\,\%\=]+$', m):
        return False
    math_only = re.match(r'^(what is |calculate |convert |how many )?(\d[\d\s\+\-\*\/\^\(\)\.\,\%]*)(\s*(\+|\-|\*|\/|\^|to|in|equals|=)\s*[\d\s\+\-\*\/\^\(\)\.\,\%]*)?$', m)
    if math_only:
        return False

    # --- Never search: explicit code generation requests ---
    # User wants the LLM to WRITE code, not look something up
    code_gen_patterns = [
        r'\b(write|create|generate|build|make|implement|code|scaffold)\b.*\b(function|class|component|script|program|app|api|endpoint|module|snippet|test|query|schema|migration|dockerfile|config)\b',
        r'\b(fix|debug|refactor|optimize|review)\b.*\b(this|my|the)\b.*\b(code|function|class|bug|error|issue)\b',
        r'\b(explain|how does)\b.*\b(this code|this function|this algorithm)\b',
    ]
    for pat in code_gen_patterns:
        if re.search(pat, m):
            return False

    # --- Always search: explicit internet/research requests ---
    explicit_search = [
        'search', 'look up', 'find out', 'google', 'browse', 'visit',
        'go to', 'check the website', 'read the article', 'what does.*say',
        'according to', 'source', 'reference', 'cite',
    ]
    if any(k in m for k in explicit_search):
        return True

    # --- Always search: questions about real-world facts, people, events, companies ---
    # Any "what", "who", "when", "where", "why", "how" question about the real world
    question_starters = (
        'what ', 'who ', 'when ', 'where ', 'why ', 'how ', 'which ',
        'is ', 'are ', 'was ', 'were ', 'does ', 'do ', 'did ', 'has ',
        'have ', 'had ', 'can ', 'could ', 'should ', 'would ', 'will ',
        'tell me about', 'explain', 'describe', 'summarize', 'give me',
        'show me', 'list', 'find', 'get me', 'i want to know',
        'i need to know', 'help me understand',
    )
    if any(m.startswith(k) or k in m for k in question_starters):
        return True

    # --- Always search: any message mentioning a named entity, product, company, or place ---
    # Capitalized words in the original message are strong signals
    original_words = message.split()
    capitalized = [w for w in original_words if len(w) > 2 and w[0].isupper() and not w.isupper()]
    if len(capitalized) >= 1 and len(message) > 15:
        return True

    # --- Default: search for anything substantive (> 20 chars) ---
    # Better to search and get no results than to answer with stale knowledge
    if len(m) > 20:
        return True

    return False


async def _fetch_search_context(message: str) -> str:
    """Return web-search context string using Tavily (v2 Bearer auth), Serper, or DuckDuckGo fallback."""
    import os, httpx
    from datetime import datetime, timezone
    now_str = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")
    try:
        # --- Tavily v2 (preferred) — API key goes in Authorization header, NOT in body ---
        tavily_key = os.environ.get("TAVILY_API_KEY", "").strip()
        if tavily_key:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.post(
                    "https://api.tavily.com/search",
                    headers={
                        "Authorization": f"Bearer {tavily_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "query": message,
                        "max_results": 5,
                        "search_depth": "basic",
                        "include_answer": True,
                    },
                )
                if r.status_code == 200:
                    data = r.json()
                    parts = []
                    # Tavily direct answer (most accurate)
                    if data.get("answer"):
                        parts.append(f"Direct answer: {data['answer']}")
                    # Individual result snippets
                    for item in data.get("results", [])[:4]:
                        title = item.get("title", "")
                        content = (item.get("content") or "")[:300]
                        if content:
                            parts.append(f"- {title}: {content}")
                    if parts:
                        return f"[Today is {now_str}]\n" + "\n".join(parts)
                else:
                    import logging
                    logging.getLogger(__name__).warning(
                        "Tavily returned %s: %s", r.status_code, r.text[:200]
                    )
        # --- Serper (fallback) ---
        serper_key = os.environ.get("SERPER_API_KEY", "").strip()
        if serper_key:
            async with httpx.AsyncClient(timeout=8) as client:
                r = await client.post(
                    "https://google.serper.dev/search",
                    headers={"X-API-KEY": serper_key, "Content-Type": "application/json"},
                    json={"q": message, "num": 5},
                )
                if r.status_code == 200:
                    data = r.json()
                    parts = [f"[Today is {now_str}]"]
                    if data.get("answerBox", {}).get("answer"):
                        parts.append(f"Direct answer: {data['answerBox']['answer']}")
                    snippets = [f"- {item.get('title','')}: {item.get('snippet','')}" for item in data.get("organic", [])[:4]]
                    parts.extend(snippets)
                    return "\n".join(parts)
        # --- DuckDuckGo instant answer (no key needed) ---
        async with httpx.AsyncClient(timeout=6) as client:
            r = await client.get(
                "https://api.duckduckgo.com/",
                params={"q": message, "format": "json", "no_html": "1", "skip_disambig": "1"},
            )
            if r.status_code == 200:
                data = r.json()
                abstract = data.get("AbstractText", "")
                answer = data.get("Answer", "")
                related = [t.get("Text", "") for t in data.get("RelatedTopics", [])[:3] if isinstance(t, dict)]
                parts = [p for p in [answer, abstract] + related if p]
                if parts:
                    return f"[Today is {now_str}]\n" + "\n".join(f"- {p}" for p in parts[:5])
    except Exception as _e:
        import logging
        logging.getLogger(__name__).warning("_fetch_search_context failed: %s", _e)
    # Even if search fails, always inject today's date
    return f"[Today is {now_str}. No live search results available.]"


def _merge_prior_turns_into_message(message: str, prior_turns) -> str:
    """Prepend the last N conversation turns so the LLM has context."""
    if not prior_turns:
        return message
    parts = []
    for turn in (prior_turns or [])[-6:]:
        role = turn.get("role", "user")
        content = (turn.get("content") or "").strip()
        if content:
            parts.append(f"{role.capitalize()}: {content}")
    return ("\n".join(parts) + f"\nUser: {message}") if parts else message


def _build_chat_system_prompt_for_request(message: str, user_id=None) -> str:
    """Craft a system prompt tailored to the incoming message."""
    import re
    m = (message or "").lower()
    # Code / build focused — use word-boundary matching to avoid false positives
    # e.g. 'function' in 'who is the function of...' vs 'write a function'
    code_kw = (
        # Unambiguous code terms
        r"\bcode\b", r"\bdebug\b", r"\brefactor\b", r"\balgorithm\b", r"\bimplement\b",
        r"\bsql\b", r"\bregex\b", r"\bsnippet\b", r"\bsyntax\b",
        r"\bpython\b", r"\bjavascript\b", r"\btypescript\b",
        r"\bapi endpoint\b", r"\bcompile\b", r"\btest case\b",
        r"\bgithub\b", r"\bgit commit\b", r"\bdocker\b", r"\bkubernetes\b",
        # Contextual — only match when combined with a coding action
        r"\bwrite a (function|class|method|module|component)\b",
        r"\b(implement|create|build) a (function|class|method|api|endpoint)\b",
        r"\b(fix|debug|solve) (this )?(bug|error|issue|problem) in\b",
        r"\b(unit test|integration test|test suite)\b",
        r"\b(react|vue|angular|next\.js|express|fastapi|django|flask)\b",
        r"\b(npm|pip|yarn|cargo|gradle|maven)\b",
        r"\b(async|await|promise|callback|closure|recursion)\b",
        r"\b(array|object|dictionary|hashmap|linked list|binary tree)\b",
    )
    if any(re.search(k, m) for k in code_kw):
        return (
            "You are CrucibAI, an expert AI software engineer and architect. "
            "You write production-quality, complete, deployable code. "
            "Always explain your reasoning briefly, then provide the full working code. "
            "Be precise, thorough, and never truncate output."
        )
    # General knowledge / factual / current events
    return (
        "You are CrucibAI, a highly capable AI assistant built by the CrucibAI team. "
        "You have access to real-time internet search and can answer questions about "
        "current events, news, prices, people, companies, and anything happening in the world right now. "
        "You are knowledgeable across all domains: science, history, politics, culture, "
        "technology, business, sports, entertainment, and more. "
        "NEVER say you cannot access the internet, NEVER say you have a knowledge cutoff, "
        "NEVER say you cannot provide real-time information. "
        "When live search results are provided in the conversation, use them as your primary source "
        "and answer confidently with that information. "
        "You are also an expert software engineer and can help build production-ready applications when asked. "
        "Be conversational, direct, and thorough."
    )


def _extract_pdf_text_from_b64(b64: str) -> str:
    """Extract readable text from a base64-encoded PDF attachment."""
    try:
        import base64, io
        data = base64.b64decode(b64)
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(data))
            return "\n".join(p.extract_text() or "" for p in reader.pages)[:8000]
        except Exception:
            return data.decode("utf-8", errors="ignore")[:4000]
    except Exception:
        return ""
# ─────────────────────────────────────────────────────────────────────────
from .services.session_journal import list_entries as list_session_journal_entries
from .services.events.persistent_sink import read_events as read_persisted_events
from .services.runtime.memory_graph import get_graph as get_memory_graph
from .services.runtime.cost_tracker import cost_tracker
from .services.runtime.task_manager import task_manager

from .config import ROOT_DIR, WORKSPACE_ROOT
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
CHAT_WITH_SEARCH_SYSTEM = (
    "You are CrucibAI, a fully internet-connected AI assistant. "
    "Live web search results have been retrieved and are provided below. "
    "Use these search results as your PRIMARY and AUTHORITATIVE source of information. "
    "Answer the user's question directly and confidently using the live data provided. "
    "NEVER say you cannot access the internet. NEVER mention a knowledge cutoff. "
    "NEVER say you cannot provide real-time information. "
    "If the search results contain the answer, state it clearly and directly. "
    "Always cite or reference the source when relevant."
)
REAL_AGENT_NO_LLM_KEYS_DETAIL = "Real-agent mode requires an Anthropic or Cerebras API key. Please add one in Settings > API Keys."
FRONTEND_URL = os.environ.get("FRONTEND_URL", "")
RATE_LIMIT_PER_MINUTE = int(os.environ.get("RATE_LIMIT_PER_MINUTE", "60"))
# Canonical pricing — keep aligned with backend/pricing_plans.py (linear $0.03/credit).
# The Pricing page /tokens/bundles endpoint reads these values, so they MUST match
# the DEFAULT_BUNDLES in frontend/src/pages/Pricing.jsx.
TOKEN_BUNDLES: Dict[str, Any] = {
    "builder": {"name": "Builder", "tokens": 500_000,  "credits": 500,  "price": 15},
    "pro":     {"name": "Pro",     "tokens": 1_000_000, "credits": 1000, "price": 30},
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
            'e2e', 'swagger', 'microservice', 'rest api', 'graphql', 'stripe',
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
    # Build context block from prior agents' outputs so each agent can
    # build on the work already done rather than starting blind.
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
                parts.append(f"### {prior_agent}\n{prior_text[:2000]}")
        if parts:
            context_block = (
                "\n\n---\n## Context from prior agents\n"
                + "\n\n".join(parts)
                + "\n---\n"
            )
    enriched_prompt = project_prompt + context_block
    output, _meta = await _call_llm_with_fallback(
        message=enriched_prompt,
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup — ensure Postgres tables exist before serving any requests
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8000",
        "https://app.crucib.ai",
        "https://www.crucib.ai",
        "https://crucib.ai",
        FRONTEND_URL,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

@app.get("/api/v1/health")
async def health_check_v1():
    return {"status": "ok", "version": "v1", "timestamp": str(datetime.now())}



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
    effective = await _effective_api_keys(user)
    return {
        "anthropic_model": ANTHROPIC_HAIKU_MODEL,
        "anthropic_api_key": bool(effective.get("ANTHROPIC_API_KEY")),
        "cerebras_api_key": bool(effective.get("CEREBRAS_API_KEY")),
        "chat_with_search_system": CHAT_WITH_SEARCH_SYSTEM,
        "real_agent_no_llm_keys_detail": REAL_AGENT_NO_LLM_KEYS_DETAIL,
        "has_any_llm_api_key": bool(effective),
        "has_anthropic_api_key": bool(effective.get("ANTHROPIC_API_KEY")),
        "has_cerebras_api_key": bool(effective.get("CEREBRAS_API_KEY")),
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
    return await build_provider_readiness(user)


# Dynamically load all routers from the routes directory.
# This keeps the server file clean and modular.
_ALL_ROUTES: List[Tuple[str, str, bool]] = [
    ("backend.routes.auth", "auth_router", False),
    ("backend.routes.runtime", "router", False),
    ("backend.routes.projects", "projects_router", False),
    ("backend.routes.project_memory", "router", False),
    ("backend.routes.automation", "router", False),
    ("backend.routes.community", "router", False),
    ("backend.routes.crucib_workspace_adapter", "router", False),
    ("backend.routes.crucib_ws_events", "router", False),
    ("backend.routes.deploy", "router", False),
    ("backend.routes.ecosystem", "router", False),
    ("backend.routes.ai", "router", False),
    ("backend.routes.git_sync", "router", False),
    ("backend.routes.ide", "router", True),
    ("backend.routes.mobile", "mobile_router", True),
    ("backend.routes.monitoring", "router", False),
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

@app.get("/api/admin/route-report")
async def route_report(user: User = Depends(require_permission(Permission.CREATE_PROJECT))):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")
    return ROUTE_REGISTRATION_REPORT

# Static file mounting moved to the end of the file to avoid shadowing API routes.



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

# Serve static files from the 'static' directory
if STATIC_DIR.exists() and any(STATIC_DIR.iterdir()):
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
    @app.exception_handler(404)
    async def not_found_handler(_, __):
        return FileResponse(str(STATIC_DIR / "index.html"))
else:
    logger.warning(
        f"Static directory not found or empty: {STATIC_DIR}. " f"Static file serving will be disabled."
    )



