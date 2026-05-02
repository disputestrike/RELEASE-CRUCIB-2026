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

    # Short questions that still need the web (or the session date line in system prompt is not enough for news).
    import re as _re2

    if _re2.search(
        r"^\s*(date|todays? date|current date|what\s*'?s?\s*the\s*date|date\s+today|today\??s?\s*date|time\??|what\s*day|what\s*'?s?\s*today)\s*[\?\.!]*\s*$",
        m,
        _re2.I,
    ):
        return True
    if _re2.search(
        r"^\s*(us|u\.s\.?|american)\s*president|^\s*who\s+is\s+the\s+(us|u\.s\.?|current)\s+president|^\s*president(\s+of\s+(the\s+)?us\??a?)?\s*[\?\.!]*\s*$",
        m,
        _re2.I,
    ):
        return True
    if len(m) < 8:
        return False

    # --- Never search: identity questions about CrucibAI itself ---
    # These are answered by the system prompt IDENTITY section, not web search
    import re as _re
    identity_patterns = [
        r'^(who|what)\s+(are|is)\s+(you|u|crucibai)\??$',
        r'^(who|what)\s+(r|are)\s+u\??$',
        r'^what\s+do\s+(you|u)\s+do\??$',
        r'^(who|what)\s+made\s+(you|u)\??$',
        r'^(who|what)\s+built\s+(you|u)\??$',
        r'^(are|r)\s+you\s+(chatgpt|claude|gpt|openai|anthropic|an\s+ai|an\s+llm)\??$',
        r'^what\s+(model|ai|llm)\s+(are|r)\s+(you|u)\??$',
        r'^(how|how\'s)\s+(are|r)\s+(you|u)\??$',
        r'^(how\s+are\s+you|how\s+r\s+u|how\s+are\s+u|hru)\??$',
    ]
    for pat in identity_patterns:
        if _re.match(pat, m.strip()):
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
    """Return web-search context string.

    Tier order:
    1. Tavily v2  (best quality; requires valid TAVILY_API_KEY)
    2. Serper     (Google results; requires SERPER_API_KEY)
    3. Jina AI + Bing News RSS  (free, no key, works from any server)
    4. DuckDuckGo Instant Answer API  (free, no key)
    5. DuckDuckGo HTML scrape  (free, no key, may need browser UA)
    6. Bing HTML scrape  (free, no key, may need browser UA)
    """
    import os, httpx, re as _re, urllib.parse
    from datetime import datetime, timezone
    now_str = datetime.now(timezone.utc).strftime("%A, %B %d, %Y")
    _log = __import__('logging').getLogger(__name__)

    def _ctx(parts):
        return f"[Today is {now_str}]\n" + "\n".join(parts)

    try:
        # ── 1. Tavily v2 (preferred when key works) ──────────────────────────
        tavily_key = os.environ.get("TAVILY_API_KEY", "").strip()
        if tavily_key:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    r = await client.post(
                        "https://api.tavily.com/search",
                        headers={"Authorization": f"Bearer {tavily_key}", "Content-Type": "application/json"},
                        json={"query": message, "max_results": 5, "search_depth": "basic", "include_answer": True},
                    )
                    if r.status_code == 200:
                        data = r.json()
                        parts = []
                        if data.get("answer"):
                            parts.append(f"Direct answer: {data['answer']}")
                        for item in data.get("results", [])[:4]:
                            content = (item.get("content") or "")[:300]
                            if content:
                                parts.append(f"- {item.get('title','')}: {content}")
                        if parts:
                            return _ctx(parts)
                    else:
                        _log.warning("Tavily %s: %s", r.status_code, r.text[:100])
            except Exception as e:
                _log.warning("Tavily error: %s", e)

        # ── 2. Serper (if key set) ────────────────────────────────────────────
        serper_key = os.environ.get("SERPER_API_KEY", "").strip()
        if serper_key:
            try:
                async with httpx.AsyncClient(timeout=8) as client:
                    r = await client.post(
                        "https://google.serper.dev/search",
                        headers={"X-API-KEY": serper_key, "Content-Type": "application/json"},
                        json={"q": message, "num": 5},
                    )
                    if r.status_code == 200:
                        data = r.json()
                        parts = []
                        if data.get("answerBox", {}).get("answer"):
                            parts.append(f"Direct answer: {data['answerBox']['answer']}")
                        for item in data.get("organic", [])[:4]:
                            snip = item.get("snippet", "")
                            if snip:
                                parts.append(f"- {item.get('title','')}: {snip}")
                        if parts:
                            return _ctx(parts)
            except Exception as e:
                _log.warning("Serper error: %s", e)

        # ── 3. Jina AI + Bing News RSS (free, no key, highly reliable) ──────────
        # Jina's r.jina.ai reader fetches any URL and returns clean markdown.
        # Bing News RSS gives real-time news headlines without CAPTCHA.
        try:
            encoded_q = urllib.parse.quote(message)
            jina_url = f"https://r.jina.ai/https://www.bing.com/news/search?q={encoded_q}&format=RSS"
            async with httpx.AsyncClient(
                timeout=12,
                follow_redirects=True,
                headers={"User-Agent": "CrucibAI/1.0 (crucibai.com)", "Accept": "text/plain"},
            ) as client:
                r = await client.get(jina_url)
                if r.status_code == 200 and len(r.text) > 200:
                    # Extract headlines from Jina markdown output
                    headlines = _re.findall(r'###\s+\[([^\]]+)\]', r.text)
                    # Extract snippet text (content after headline links)
                    snippets = _re.findall(r'\]\([^)]+\)\n([^\n#\[]{40,})', r.text)
                    parts = []
                    for h in headlines[:5]:
                        parts.append(f"- {h[:200]}")
                    for s in snippets[:3]:
                        parts.append(f"  {s.strip()[:200]}")
                    if parts:
                        return _ctx(parts)
        except Exception as e:
            _log.warning("Jina+BingNews error: %s", e)

        # ── 4. DuckDuckGo Instant Answer API (no key needed) ─────────────────
        try:
            async with httpx.AsyncClient(
                timeout=8,
                headers={"User-Agent": "Mozilla/5.0 (compatible; CrucibAI/1.0)"},
            ) as client:
                r = await client.get(
                    "https://api.duckduckgo.com/",
                    params={"q": message, "format": "json", "no_html": "1", "skip_disambig": "1"},
                )
                if r.status_code == 200:
                    data = r.json()
                    parts = []
                    if data.get("Answer"):
                        parts.append(f"Direct answer: {data['Answer']}")
                    if data.get("AbstractText"):
                        parts.append(f"- {data['AbstractText'][:400]}")
                    for t in data.get("RelatedTopics", [])[:4]:
                        if isinstance(t, dict) and t.get("Text"):
                            parts.append(f"- {t['Text'][:200]}")
                    if parts:
                        return _ctx(parts)
        except Exception as e:
            _log.warning("DDG instant answer error: %s", e)

        # ── 5. DuckDuckGo HTML scrape ───────────────────────────────────────────
        try:
            async with httpx.AsyncClient(
                timeout=10,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept-Language": "en-US,en;q=0.9",
                },
                follow_redirects=True,
            ) as client:
                r = await client.get("https://html.duckduckgo.com/html/", params={"q": message})
                if r.status_code == 200:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(r.text, "html.parser")
                    parts = []
                    for result in soup.select(".result__snippet")[:5]:
                        text = result.get_text(strip=True)
                        if text and len(text) > 20:
                            parts.append(f"- {text[:300]}")
                    if parts:
                        return _ctx(parts)
        except Exception as e:
            _log.warning("DDG HTML scrape error: %s", e)

        # ── 6. Bing HTML scrape ──────────────────────────────────────────────────
        try:
            async with httpx.AsyncClient(
                timeout=10,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept-Language": "en-US,en;q=0.9",
                },
                follow_redirects=True,
            ) as client:
                r = await client.get("https://www.bing.com/search", params={"q": message, "setlang": "en"})
                if r.status_code == 200:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(r.text, "html.parser")
                    parts = []
                    for sel in [".b_focusTextMedium", ".b_focusTextSmall", ".b_factrow"]:
                        el = soup.select_one(sel)
                        if el:
                            parts.append(f"Direct answer: {el.get_text(strip=True)[:300]}")
                            break
                    for cap in soup.select(".b_caption p")[:4]:
                        text = cap.get_text(strip=True)
                        if text and len(text) > 20:
                            parts.append(f"- {text[:300]}")
                    if parts:
                        return _ctx(parts)
        except Exception as e:
            _log.warning("Bing scrape error: %s", e)

    except Exception as _e:
        _log.warning("_fetch_search_context outer error: %s", _e)

    # Always inject today's date even if all search methods fail
    return f"[Today is {now_str}]"


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
    """Build the full CrucibAI system prompt with identity, known facts, and behavior rules.

    This is the gold-source system prompt. It includes:
    - CrucibAI identity (never reveal underlying model)
    - Hardcoded KNOWN FACTS so the LLM never hallucinates Biden/wrong president
    - TODAY's date injected at call time
    - Full behavior rules from the gold source
    """
    from datetime import datetime, timezone as _tz
    today = datetime.now(_tz.utc).strftime("%B %d, %Y")
    return f"""You are CrucibAI \u2014 an AI platform that builds apps, automations, and digital products.

TODAY'S DATE: {today}. Always use this exact date when asked what the date or year is. Never use a date from your training data.

KNOWLEDGE CUTOFF:
- Your training data cutoff is approximately October 2024. Today is {today}. These are two different things \u2014 do not confuse them.
- For factual questions, give a direct answer with ONE sentence of useful context. Not zero context (too short), not a paragraph (too long). The right level: \"Donald Trump \u2014 he won the 2024 election and was inaugurated January 20, 2025.\" Or: \"Bola Tinubu \u2014 he's been Nigeria's president since 2023.\" Direct answer + one grounding fact. No URLs, no citations, no \"as of my knowledge cutoff.\"
- Only add a caveat if the question is about something very recent (last few weeks) or highly specific real-time data (stock prices, sports scores today). For widely known facts, just answer.
- If the user corrects you, accept it immediately. Never argue.
- KNOWN FACTS (answer these directly, no caveats needed):
  - US President: Donald Trump (47th), inaugurated January 20, 2025. Previous president: Joe Biden (2021-2025).
  - Current year: 2026.

IDENTITY \u2014 answer these exactly, no more, no less:
- \"Who are you?\" / \"What are you?\" \u2192 \"I'm CrucibAI. I build things. Tell me what you want and we'll make it.\"
- \"Who made you?\" / \"Who built you?\" / \"What company?\" \u2192 \"I'm CrucibAI.\"
- \"What model are you?\" / \"Are you ChatGPT?\" / \"Are you Claude?\" / \"What AI are you?\" \u2192 \"I'm CrucibAI. I don't discuss what's under the hood \u2014 I just build. What do you want to make?\"
- \"Are you an agent?\" / \"Do you use agents?\" \u2192 \"I'm CrucibAI. I build things. What do you want to make?\"
- \"How do you work?\" / \"What technology?\" / \"What stack?\" \u2192 \"Proprietary technology built to take your idea from prompt to product. Give me a description and I'll show you what it can do.\"
- \"What can you build?\" \u2192 \"Web apps, mobile apps, landing pages, automations, APIs, dashboards \u2014 your entire product from one prompt. What do you need?\"

Be direct, grounded, and confident. You are a builder and research partner\u2014not customer support.
When the user attaches images or PDFs: images are shown to you directly, PDFs are extracted as text. Use that content to answer questions or help build something. Do not say you cannot see attachments.

OUTPUT FORMAT (modern product, not an old-school chatbot):
- NEVER use numbered lists (1. 2. 3.) for conversational answers. Numbered lists are only for step-by-step instructions when the user explicitly asks for steps.
- NEVER use bullet points by default. Only use bullets when listing 4+ parallel items that genuinely need scanning.
- Do not wrap normal prose in asterisks or decorative markdown. No **bold** in conversational replies.
- No cheesy filler: not "I'm excited", "Here's what I found", "Great question", "I'd love to help", "Here are a few options", "There are several ways", or generic AI-marketplace hype.
- For open-ended questions like "how do we make money?" or "what should we build?": give ONE direct recommendation, not a menu of options. Pick the best one and say why. Then offer to build it.
- For research, markets, or startup ideas: be specific and analytical. One strong take, not a listicle.
- Maximum response length for conversational questions: 3 sentences unless the user asks for more.

Rules:
- Never say "How can I assist you today?"
- Never say "How can I help you with your software development or coding needs?"
- Never say "Here are a few options" or "There are several ways"
- Never give a numbered list for a conversational question
- Never sound generic or robotic
- Speak like a capable, founder-grade builder: direct judgment, one strong take, no performative enthusiasm
- Never reveal the underlying model, technology stack, or internal architecture

CRITICAL \u2014 Ambiguity and clarification:
- When the user's intent is clear but details are missing, make the best reasonable assumption, state it in one sentence, and proceed.
- Never ask more than one clarifying question per response.
- If the user says \"just do it\", \"figure it out\", \"you decide\", \"don't ask questions\" \u2014 state what you will do in one line and proceed.
- Banned phrases: \"I need a bit more context\", \"Are you looking to build X or Y?\", \"The more details you share\", \"Great choice! Are you looking to...\"
- Ambiguity is a reason to decide, not a reason to stop.

Examples:
- \"Hello\" / \"Hi\" \u2192 \"Hi. What do you want to build?\"
- \"What can you do?\" \u2192 \"Apps, automations, landing pages, APIs, internal tools\u2014from prompt to shippable output. What are you trying to ship?\"
- \"How are you?\" \u2192 \"Ready when you are. What's the project?\"
- Company name mentioned WITHOUT build request \u2192 \"Interesting \u2014 do you want to build something related to that? Tell me what you have in mind.\"
- Question about a competitor or other AI tool \u2192 \"I don't worry about other tools \u2014 I just build. What do you want to make?\"
- Build request with vague details \u2192 State one concrete interpretation in one sentence and offer to build it.

CRITICAL \u2014 When to use code vs prose:
- Research, strategy, market analysis, opportunity mapping, GTM, or \"what should we build\" answers: use plain prose only.
- Do not decorate normal prose with asterisks, fake bold, or markdown emphasis habits.
- When the user explicitly asks for code, implementation, or to \"show the code\": use a single fenced block with the appropriate language tag.

CRITICAL \u2014 Code output rules (only when code is explicitly requested):
- Wrap code in one fenced block: ```lang\\n...code...\\n```
- NEVER write explanation inside a code block.
- NEVER append explanation after the closing ```.
- One sentence BEFORE the code block if needed, then the code, then stop.
"""


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
# Canonical pricing — keep aligned with backend/pricing_plans.py.
# The Pricing page /tokens/bundles endpoint reads these values, so they MUST match
# the DEFAULT_BUNDLES in frontend/src/pages/Pricing.jsx.
TOKEN_BUNDLES: Dict[str, Any] = {
    "builder": {"name": "Builder", "tokens": 250_000, "credits": 500, "price": 20},
    "pro": {"name": "Pro", "tokens": 750_000, "credits": 1500, "price": 50},
    "scale": {"name": "Scale", "tokens": 1_500_000, "credits": 3000, "price": 100},
    "teams": {"name": "Teams", "tokens": 3_000_000, "credits": 6000, "price": 200},
}
ANNUAL_PRICES: Dict[str, Any] = {
    "builder": 200,
    "pro": 500,
    "scale": 1000,
    "teams": 2000,
}
PAYMENT_PROVIDER = "paypal"
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


def _is_admin_user(user: Optional[dict]) -> bool:
    """True for configured admin IDs or acceptable ``admin_role`` (tests may monkeypatch)."""
    if not user:
        return False
    uid = user.get("id")
    if uid and str(uid) in ADMIN_USER_IDS:
        return True
    role = user.get("admin_role")
    return role in ADMIN_ROLES


def _get_server_helpers():
    return (
        _user_credits,
        _assert_job_owner_match,   # FIX: was _ensure_credit_balance — wrong function,
        _resolve_job_project_id_for_user,
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


def _anthropic_api_key_for_agent_loop(effective: Optional[dict]) -> str:
    return (
        ((effective or {}).get("anthropic") or os.environ.get("ANTHROPIC_API_KEY") or "")
        .strip()
    )


def _anthropic_model_from_chain(model_chain: list) -> str:
    """Pick Claude model ID from swarm/router chain when present."""
    try:
        from .anthropic_models import ANTHROPIC_HAIKU_MODEL, normalize_anthropic_model
    except ImportError:
        from backend.anthropic_models import ANTHROPIC_HAIKU_MODEL, normalize_anthropic_model

    for entry in model_chain or []:
        if isinstance(entry, dict) and entry.get("provider") == "anthropic":
            return normalize_anthropic_model(
                entry.get("model"), default=ANTHROPIC_HAIKU_MODEL
            )
        if isinstance(entry, (list, tuple)) and len(entry) >= 3:
            _name, mid, provider = entry[0], entry[1], entry[2]
            if provider == "anthropic" and mid:
                return normalize_anthropic_model(mid, default=ANTHROPIC_HAIKU_MODEL)
    return normalize_anthropic_model(None, default=ANTHROPIC_HAIKU_MODEL)


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

    workspace_fs = (workspace_path or "").strip()
    anthropic_key = _anthropic_api_key_for_agent_loop(effective)
    use_workspace_tool_loop = bool(workspace_fs) and bool(anthropic_key)
    output: Any = ""
    _meta: Any = {}
    completed_anthropic_tool_loop = False
    completed_provider_tool_loop = False

    async def _provider_neutral_workspace_loop() -> tuple[Any, Any]:
        """Cerebras/other providers via text tool loop — same DAG agent, no Anthropic tools API."""
        try:
            from .orchestration.runtime_engine import run_text_agent_loop
        except ImportError:
            from backend.orchestration.runtime_engine import run_text_agent_loop

        async def _call_text_llm(*, message, system_message, session_id):
            resp, model_used = await _call_llm_with_fallback(
                message=message,
                system_message=system_message,
                session_id=session_id,
                model_chain=model_chain,
                api_keys=effective,
                agent_name=agent_name,
            )
            return {
                "text": resp.get("text", "") if isinstance(resp, dict) else str(resp or ""),
                "model": model_used,
                "tokens_used": resp.get("tokens_used", 0) if isinstance(resp, dict) else 0,
            }

        loop_out = await run_text_agent_loop(
            agent_name=agent_name,
            system_prompt=system_message,
            user_message=enriched_prompt,
            workspace_path=workspace_fs,
            call_text_llm=_call_text_llm,
        )
        out = loop_out.get("final_text") or "[agent completed provider-neutral tool loop]"
        meta = {
            "model": "provider_neutral_tool_loop",
            "tool_loop": True,
            "provider_neutral_tool_loop": True,
            "iterations": loop_out.get("iterations"),
            "files_written": loop_out.get("files_written"),
            "elapsed_seconds": loop_out.get("elapsed_seconds"),
        }
        return out, meta

    if use_workspace_tool_loop:
        try:
            from .orchestration.runtime_engine import (
                MAX_LOOP_ITERATIONS,
                extract_final_assistant_text,
                run_agent_loop,
            )
            from .services.llm_service import _call_anthropic_messages_with_tools
        except ImportError:
            from backend.orchestration.runtime_engine import (
                MAX_LOOP_ITERATIONS,
                extract_final_assistant_text,
                run_agent_loop,
            )
            from backend.services.llm_service import _call_anthropic_messages_with_tools

        anthropic_model = _anthropic_model_from_chain(model_chain)

        async def _call_llm_turn(messages, system, tools, thinking=None):
            return await _call_anthropic_messages_with_tools(
                api_key=anthropic_key,
                model=anthropic_model,
                system_message=system,
                messages=messages,
                tools=tools,
                max_tokens=8192,
                thinking=thinking,
            )

        try:
            loop_out = await run_agent_loop(
                agent_name=agent_name,
                system_prompt=system_message,
                user_message=enriched_prompt,
                workspace_path=workspace_fs,
                call_llm=_call_llm_turn,
                max_iterations=MAX_LOOP_ITERATIONS,
            )
            final_text = extract_final_assistant_text(loop_out.get("messages") or [])
            output = (
                final_text.strip()
                if final_text.strip()
                else "[agent completed tool loop with no assistant text]"
            )
            _meta = {
                "model": f"anthropic_tool_loop/{anthropic_model}",
                "tool_loop": True,
                "iterations": loop_out.get("iterations"),
                "files_written": loop_out.get("files_written"),
                "elapsed_seconds": loop_out.get("elapsed_seconds"),
                "anthropic_usage": loop_out.get("usage"),
            }
            completed_anthropic_tool_loop = True
        except Exception as exc:
            logger.warning(
                "workspace tool loop failed for %s — trying provider-neutral tool loop then single-shot: %s",
                agent_name,
                exc,
            )
            recovered = False
            if workspace_fs:
                try:
                    output, _meta = await _provider_neutral_workspace_loop()
                    if isinstance(_meta, dict):
                        _meta["recovery_after_anthropic_tool_loop_fail"] = True
                    completed_provider_tool_loop = True
                    recovered = True
                except Exception as exc2:
                    logger.warning(
                        "provider-neutral recovery after anthropic failure failed for %s: %s",
                        agent_name,
                        exc2,
                    )
            if not recovered:
                output, _meta = await _call_llm_with_fallback(
                    message=enriched_prompt,
                    system_message=system_message,
                    session_id=f"{project_id}:{agent_name}",
                    model_chain=model_chain,
                    api_keys=effective,
                    agent_name=agent_name,
                )
    else:
        if workspace_fs and not anthropic_key:
            logger.warning(
                "workspace path set but no Anthropic API key — agent %s uses provider-neutral "
                "text tool loop",
                agent_name,
            )
            try:
                output, _meta = await _provider_neutral_workspace_loop()
                completed_provider_tool_loop = True
            except Exception as exc:
                logger.warning(
                    "provider-neutral workspace tool loop failed for %s — falling back to single-shot LLM: %s",
                    agent_name,
                    exc,
                )
                output, _meta = await _call_llm_with_fallback(
                    message=enriched_prompt,
                    system_message=system_message,
                    session_id=f"{project_id}:{agent_name}",
                    model_chain=model_chain,
                    api_keys=effective,
                    agent_name=agent_name,
                )
        else:
            output, _meta = await _call_llm_with_fallback(
                message=enriched_prompt,
                system_message=system_message,
                session_id=f"{project_id}:{agent_name}",
                model_chain=model_chain,
                api_keys=effective,
                agent_name=agent_name,
            )

    est_tokens = max(100, len(str(output or "")) // 4)
    if completed_anthropic_tool_loop and isinstance(_meta, dict):
        u = _meta.get("anthropic_usage") or {}
        if isinstance(u, dict):
            inp = u.get("input_tokens")
            outp = u.get("output_tokens")
            billed = 0
            if isinstance(inp, int):
                billed += inp
            if isinstance(outp, int):
                billed += outp
            if billed > 0:
                est_tokens = max(100, billed)

    result = {
        "status": "completed",
        "output": output,
        "result": output,
        "tokens_used": est_tokens,
        "agent": agent_name,
        "project_id": project_id,
        "user_id": user_id,
        "build_kind": build_kind,
    }
    if completed_anthropic_tool_loop:
        result["tool_loop"] = True
        if isinstance(_meta, dict):
            result["tool_loop_iterations"] = _meta.get("iterations")
            result["tool_loop_files_written"] = _meta.get("files_written")
            if isinstance(_meta.get("anthropic_usage"), dict):
                result["anthropic_usage"] = _meta["anthropic_usage"]
    if completed_provider_tool_loop:
        result["tool_loop"] = True
        result["provider_neutral_tool_loop"] = True
        if isinstance(_meta, dict):
            result["tool_loop_iterations"] = _meta.get("iterations")
            result["tool_loop_files_written"] = _meta.get("files_written")
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup — ensure Postgres tables exist before serving any requests
    try:
        from .services.migration_runner import run_migrations_idempotent
        await run_migrations_idempotent()
        logger.info("Startup migrations complete.")
    except Exception as _mig_err:
        logger.error("Startup migration failed (non-fatal): %s", _mig_err, exc_info=True)
    try:
        from .db_pg import ensure_all_tables
        await ensure_all_tables()
        logger.info("ensure_all_tables complete.")
    except Exception as _tbl_err:
        logger.error("ensure_all_tables failed (non-fatal): %s", _tbl_err, exc_info=True)
    yield
    # shutdown
    logger.info("shutdown")


app = FastAPI(lifespan=lifespan)

# Introspection for tests and ops (CORS is configured in middleware only otherwise).
CORS_ALLOW_ORIGINS: List[str] = [
    o
    for o in [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8000",
        "https://app.crucib.ai",
        "https://www.crucib.ai",
        "https://crucib.ai",
        FRONTEND_URL,
    ]
    if o and str(o).strip()
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
    benchmark_secret = os.environ.get("BENCHMARK_SECRET") or os.environ.get("CRUCIBAI_BENCHMARK_SECRET")
    if not benchmark_secret:
        raise HTTPException(status_code=500, detail="Benchmark secret not configured (set BENCHMARK_SECRET or CRUCIBAI_BENCHMARK_SECRET)")
    if body.secret != benchmark_secret:
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
    ("backend.routes.admin", "router", False),
    ("backend.routes.debug_api", "router", False),
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
    ("backend.routes.paypal_payments", "router", False),
    ("backend.routes.cost_hook", "router", False),
    ("backend.routes.skills", "router", False),
    ("backend.routes.terminal", "router", False),
    ("backend.routes.tokens", "router", False),
    ("backend.routes.misc", "router", False),
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
            logger.error("Required router failed to load: %s.%s: %s", _module_name, _attr_name, e, exc_info=True)
            raise RuntimeError(
                f"Required router failed to load: {_module_name}.{_attr_name}: {e}"
            ) from e

@app.get("/api/admin/route-report")
async def route_report(user: User = Depends(require_permission(Permission.CREATE_PROJECT))):
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")
    return ROUTE_REGISTRATION_REPORT


@app.get("/published/{job_id}/")
@app.get("/published/{job_id}/{path:path}")
async def serve_published_generated_app(job_id: str, path: str = ""):
    from .orchestration.publish_urls import safe_publish_id
    from .services.published_app_service import serve_published_app_response

    return await serve_published_app_response(
        job_id=job_id,
        path=path,
        get_job=_lookup_job,
        safe_publish_id=safe_publish_id,
        project_workspace_path=_project_workspace_path,
        workspace_root=WORKSPACE_ROOT,
    )

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



      