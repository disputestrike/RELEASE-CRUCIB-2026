"""LLM service helpers extracted from server.py.

Provides authentication dependency, task classification, model chain selection,
and direct LLM call helpers (Anthropic, Cerebras, Llama) with fallback logic.
"""

import asyncio
import json
import logging
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
from dotenv import load_dotenv
from fastapi import Depends, HTTPException

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env", override=True)

try:
    from ..anthropic_models import ANTHROPIC_HAIKU_MODEL, normalize_anthropic_model
    from ..deps import get_optional_user
    from ..dev_stub_llm import REAL_AGENT_NO_LLM_KEYS_DETAIL, chat_llm_available
    from ..dev_stub_llm import detect_build_kind as _stub_detect_build_kind
    from ..dev_stub_llm import is_real_agent_only
    from ..dev_stub_llm import plan_and_suggestions as _stub_plan_and_suggestions
    from ..dev_stub_llm import stub_build_enabled, stub_file_dict, stub_multifile_markdown
    from ..llm_client import CEREBRAS_MODEL, get_cerebras_key as _get_cerebras_key
    from ..llm_client import get_model_chain_entries
    from ..llm_router import classifier
    from ..llm_router import router as llm_router
    from .events import event_bus
    from .skills import detect_skill
except ImportError:  # compatibility for legacy tests importing `services.*`
    from backend.anthropic_models import ANTHROPIC_HAIKU_MODEL, normalize_anthropic_model
    from backend.deps import get_optional_user
    from backend.dev_stub_llm import REAL_AGENT_NO_LLM_KEYS_DETAIL, chat_llm_available
    from backend.dev_stub_llm import detect_build_kind as _stub_detect_build_kind
    from backend.dev_stub_llm import is_real_agent_only
    from backend.dev_stub_llm import plan_and_suggestions as _stub_plan_and_suggestions
    from backend.dev_stub_llm import stub_build_enabled, stub_file_dict, stub_multifile_markdown
    from backend.llm_client import CEREBRAS_MODEL, get_cerebras_key as _get_cerebras_key
    from backend.llm_client import get_model_chain_entries
    from backend.llm_router import classifier
    from backend.llm_router import router as llm_router
    from backend.services.events import event_bus
    from backend.services.skills import detect_skill

logger = logging.getLogger(__name__)
ALLOW_SONNET = os.environ.get("ALLOW_SONNET", "false").strip().lower() in {"1", "true", "yes"}
ALLOW_SONNET_OVER_1_PERCENT = os.environ.get("ALLOW_SONNET_OVER_1_PERCENT", "false").strip().lower() in {"1", "true", "yes"}
_USAGE_WINDOW_TOTAL_TOKENS = 0
_USAGE_WINDOW_BY_PROVIDER = defaultdict(int)
_USAGE_WINDOW_BY_MODEL = defaultdict(int)
_USAGE_WINDOW_BY_CAPABILITY = defaultdict(int)


def _estimate_tokens(text: str) -> int:
    return max(1, int(len(text or "") / 4))


def _record_provider_usage(provider: str, model_id: str, capability: str, prompt: str, output: str) -> None:
    global _USAGE_WINDOW_TOTAL_TOKENS
    used = _estimate_tokens(prompt) + _estimate_tokens(output)
    _USAGE_WINDOW_TOTAL_TOKENS += used
    _USAGE_WINDOW_BY_PROVIDER[provider] += used
    _USAGE_WINDOW_BY_MODEL[f"{provider}/{model_id}"] += used
    _USAGE_WINDOW_BY_CAPABILITY[capability] += used
    if _USAGE_WINDOW_TOTAL_TOKENS <= 0:
        return
    haiku = _USAGE_WINDOW_BY_MODEL.get(f"anthropic/{ANTHROPIC_HAIKU_MODEL}", 0)
    sonnet = sum(v for k, v in _USAGE_WINDOW_BY_MODEL.items() if "/claude-sonnet" in k)
    haiku_share = (haiku / _USAGE_WINDOW_TOTAL_TOKENS) * 100.0
    sonnet_share = (sonnet / _USAGE_WINDOW_TOTAL_TOKENS) * 100.0
    logger.info(
        "provider.usage.window total_tokens=%s by_provider=%s by_capability=%s",
        _USAGE_WINDOW_TOTAL_TOKENS,
        dict(_USAGE_WINDOW_BY_PROVIDER),
        dict(_USAGE_WINDOW_BY_CAPABILITY),
    )
    if haiku_share > 35.0:
        logger.warning("provider.policy.haiku_share_high share=%.2f threshold=35.0", haiku_share)
    if sonnet_share > 1.0 and not ALLOW_SONNET_OVER_1_PERCENT:
        logger.error("provider.policy.sonnet_share_block share=%.2f threshold=1.0", sonnet_share)

# ---------------------------------------------------------------------------
# Runtime API key references (resolved at call time so .env changes work)
# ---------------------------------------------------------------------------

ANTHROPIC_API_KEY: Optional[str] = os.environ.get("ANTHROPIC_API_KEY")

# ---------------------------------------------------------------------------
# Model configuration (mirrors server.py definitions)
# ---------------------------------------------------------------------------

MODEL_CONFIG: Dict[str, Dict[str, str]] = {
    "code": {"provider": "cerebras", "model": CEREBRAS_MODEL},
    "analysis": {"provider": "cerebras", "model": CEREBRAS_MODEL},
    "general": {"provider": "cerebras", "model": CEREBRAS_MODEL},
    "creative": {"provider": "cerebras", "model": CEREBRAS_MODEL},
    "fast": {"provider": "cerebras", "model": CEREBRAS_MODEL},
}

MODEL_FALLBACK_CHAINS: List[Dict[str, str]] = [
    {"provider": "cerebras", "model": CEREBRAS_MODEL},
    {"provider": "anthropic", "model": ANTHROPIC_HAIKU_MODEL},
]

MODEL_CHAINS: Dict[str, Any] = {
    "auto": None,  # resolved dynamically via MODEL_CONFIG + MODEL_FALLBACK_CHAINS
    "haiku": [
        {"provider": "cerebras", "model": CEREBRAS_MODEL},
        {"provider": "anthropic", "model": ANTHROPIC_HAIKU_MODEL},
    ],
}

# Vision-capable model chain
VISION_MODEL_CHAIN: List[Dict[str, str]] = [
    {"provider": "cerebras", "model": CEREBRAS_MODEL},
    {"provider": "anthropic", "model": ANTHROPIC_HAIKU_MODEL},
]

# ---------------------------------------------------------------------------
# Skill auto-detection
# ---------------------------------------------------------------------------

SKILL_TRIGGERS: Dict[str, List[str]] = {
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
        "paypal billing",
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
        "paypal checkout",
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


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


async def get_authenticated_or_api_user(
    user: Optional[dict] = Depends(get_optional_user),
) -> dict:
    """Require either a signed-in user or a valid public API key for LLM/action routes."""
    if not user:
        raise HTTPException(
            status_code=401, detail="Authentication or API key required"
        )
    return user


# ---------------------------------------------------------------------------
# Skill auto-detection
# ---------------------------------------------------------------------------


async def _auto_detect_skill(prompt: str, user_id: str) -> Optional[str]:
    """Auto-detect the best skill for a prompt. Transparent to the user."""
    if os.environ.get("CRUCIB_ENABLE_SKILLS", "0").strip().lower() in (
        "1",
        "true",
        "yes",
    ):
        try:
            detected = detect_skill(prompt)
            if detected:
                return detected.name
        except Exception as e:
            logger.debug("skills registry detection failed; fallback to trigger map: %s", e)

    p = prompt.lower()
    for skill_name, triggers in SKILL_TRIGGERS.items():
        if any(t in p for t in triggers):
            return skill_name
    return None


# ---------------------------------------------------------------------------
# Task complexity / type classification
# ---------------------------------------------------------------------------


def _is_product_support_query(prompt: str) -> Optional[str]:
    """Detect if the user is asking for product support and return a canned response."""
    p = prompt.lower().strip()
    support_keywords = [
        "how do i", "how to", "help with", "support", "password reset",
        "billing", "subscription", "account", "refund", "contact", "issue"
    ]
    if any(kw in p for kw in support_keywords) and len(p) < 100:
        return "For product support, billing inquiries, or technical assistance, please visit our Help Center at https://help.manus.im or contact our support team directly."
    return None


def _classify_task_complexity(prompt: str) -> str:
    """Returns 'fast' (Cerebras) or 'complex' (Haiku)."""
    p = prompt.lower().strip()
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
        len(p) > 150,
    ]
    fast_signals = [
        len(p) < 80,
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
    return "complex"


def detect_task_type(message: str) -> str:
    """Auto-detect the best model based on message content."""
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


# ---------------------------------------------------------------------------
# Provider / key helpers
# ---------------------------------------------------------------------------


def _provider_has_key(
    provider: str, effective_keys: Optional[Dict[str, str]] = None
) -> bool:
    """True if we have an API key for this provider."""
    if provider == "anthropic":
        if effective_keys:
            return bool(effective_keys.get("anthropic"))
        return bool(os.environ.get("ANTHROPIC_API_KEY"))
    if provider == "cerebras":
        # Check effective_keys first (workspace-level keys), then env
        if effective_keys:
            return bool(effective_keys.get("cerebras") or os.environ.get("CEREBRAS_API_KEY"))
        return bool(os.environ.get("CEREBRAS_API_KEY"))
    return False


def _filter_chain_by_keys(
    chain: list, effective_keys: Optional[Dict[str, str]] = None
) -> list:
    """Keep only providers we have keys for."""
    return [
        c for c in chain if _provider_has_key(c.get("provider", ""), effective_keys)
    ]


def _policy_task_type(
    model_key: str,
    message: str,
    force_complex: bool = False,
    agent_name: str = "",
) -> str:
    key = (model_key or "auto").strip().lower()
    if key in {
        "build_plan",
        "planning",
        "architecture",
        "repair_diagnosis",
        "standard_final_proof",
        "premium_final_proof",
        "security_review",
        "validation",
        "verification",
        "proof",
    }:
        return key
    if key == "haiku":
        return "standard_final_proof"
    if key == "analysis":
        return "planning"
    if key in {"code", "general", "creative", "fast"}:
        return "code_generation"

    agent_lower = (agent_name or "").lower()
    if any(token in agent_lower for token in ("security", "validation", "review", "proof")):
        return "standard_final_proof"
    if any(token in agent_lower for token in ("planner", "requirements", "stack selector")):
        return "build_plan"
    if force_complex:
        return "planning"

    complexity = classifier.classify(message or "", agent_name or "")
    if str(getattr(complexity, "value", complexity)).lower() == "critical":
        return "standard_final_proof"
    return "code_generation"


def _get_model_chain(
    model_key: str,
    message: str,
    effective_keys: Optional[Dict[str, str]] = None,
    force_complex: bool = False,
) -> List[Dict[str, str]]:
    """Return provider/model attempts from the single llm_client policy."""

    task_type = _policy_task_type(model_key, message, force_complex)
    chain = get_model_chain_entries(task_type)
    return _filter_chain_by_keys(chain, effective_keys) or [
        c
        for c in (MODEL_FALLBACK_CHAINS or [])
        if _provider_has_key(c.get("provider", ""), effective_keys)
    ]


# ---------------------------------------------------------------------------
# API key resolution
# ---------------------------------------------------------------------------


async def get_workspace_api_keys(user: Optional[dict]) -> Dict[str, Optional[str]]:
    """Load Anthropic/Cerebras from server environment. Cerebras uses round-robin rotation."""
    return {
        "anthropic": os.environ.get("ANTHROPIC_API_KEY") or None,
        "cerebras": _get_cerebras_key() or os.environ.get("CEREBRAS_API_KEY") or None,
    }


def _effective_api_keys(
    user_keys: Dict[str, Optional[str]],
) -> Dict[str, Optional[str]]:
    """Use server-side API keys. Cerebras uses round-robin rotation across key pool."""
    return {
        "anthropic": os.environ.get("ANTHROPIC_API_KEY") or None,
        "cerebras": _get_cerebras_key() or os.environ.get("CEREBRAS_API_KEY") or None,
    }


# ---------------------------------------------------------------------------
# Direct LLM callers
# ---------------------------------------------------------------------------


async def _call_anthropic_multimodal(
    content_blocks: List[Dict[str, Any]],
    system: str,
    model: str = ANTHROPIC_HAIKU_MODEL,
    api_key: Optional[str] = None,
) -> str:
    """Call Anthropic with multimodal user content (text + image). Uses vision-capable model."""
    key = (api_key or "").strip() or os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise ValueError("ANTHROPIC_API_KEY not set")
    model = normalize_anthropic_model(model, default=ANTHROPIC_HAIKU_MODEL)
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=key)
    anthropic_content: List[Dict[str, Any]] = []
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
    """Return True if any content block is an image_url type."""
    if not content_blocks:
        return False
    return any(b.get("type") == "image_url" for b in content_blocks)


async def _call_llama_direct(
    message: str,
    system_message: str,
    model: str = "meta-llama/Llama-2-70b-chat-hf",
    api_key: Optional[str] = None,
) -> str:
    """Call Llama 70B via Together AI."""
    if not api_key:
        raise ValueError("LLAMA_API_KEY not set")
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


async def _call_cerebras_direct(
    message: str,
    system_message: str,
    model: str = "llama3.1-8b",
    api_key: Optional[str] = None,
) -> str:
    """Call Cerebras Llama via Cerebras AI API with key-rotation on rate limits."""
    if not api_key:
        raise ValueError("CEREBRAS_API_KEY not set")
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
            next_key = _get_cerebras_key()
            if next_key and next_key != api_key:
                logger.warning("Cerebras key rate limited — rotating to next key")
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
            logger.warning("Cerebras rate limited — falling back to next model")
            raise Exception("RATE_LIMITED: Cerebras API rate limit exceeded")
        if response.status_code != 200:
            logger.warning(f"Cerebras API error: {response.text}")
            raise Exception(f"Cerebras API returned {response.status_code}")
        data = response.json()
        output = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return output.strip()


async def _call_anthropic_direct(
    message: str,
    system_message: str,
    model: str = ANTHROPIC_HAIKU_MODEL,
    api_key: Optional[str] = None,
) -> str:
    """Call Anthropic Claude via HTTP. Uses api_key or ANTHROPIC_API_KEY env var."""
    key = (api_key or "").strip() or os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise ValueError("ANTHROPIC_API_KEY not set")
    model = normalize_anthropic_model(model, default=ANTHROPIC_HAIKU_MODEL)
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": key,
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
            logger.warning("Anthropic API error %s: %s", response.status_code, err_body)
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


async def _call_anthropic_messages_with_tools(
    *,
    api_key: str,
    model: str,
    system_message: str,
    messages: List[Dict[str, Any]],
    tools: List[Dict[str, Any]],
    max_tokens: int = 8192,
    thinking: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Single Claude Messages API turn with tools (HTTP).

    Returns normalized dict for ``runtime_engine.run_agent_loop``::

        ``stop_reason``: ``end_turn`` | ``tool_use`` | ``max_tokens`` | ...
        ``content``: list of ``{"type":"text"|"tool_use"|"thinking"|...}`` blocks
        ``usage``: optional usage payload from API

    When ``thinking`` is set (extended thinking), ``max_tokens`` is raised so
    ``budget_tokens`` can stay below the output cap per API rules.

    Raises on HTTP/API errors so callers can fall back.
    """
    key = (api_key or "").strip()
    if not key:
        raise ValueError("ANTHROPIC_API_KEY not set")
    model = normalize_anthropic_model(model, default=ANTHROPIC_HAIKU_MODEL)

    effective_max = max_tokens
    if thinking and (thinking.get("type") == "enabled"):
        try:
            budget = int(thinking.get("budget_tokens") or 0)
        except (TypeError, ValueError):
            budget = 0
        # API: budget_tokens must be < max_tokens; leave headroom for visible output + tools.
        effective_max = max(effective_max, budget + 8192, 16384)

    payload: Dict[str, Any] = {
        "model": model,
        "max_tokens": effective_max,
        "system": system_message,
        "messages": messages,
        "tools": tools,
    }
    if thinking:
        payload["thinking"] = thinking

    headers = {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
    }
    # Optional interleaved-thinking beta (some models); harmless when ignored.
    beta = (os.environ.get("CRUCIBAI_ANTHROPIC_BETA_HEADERS") or "").strip()
    if beta:
        headers["anthropic-beta"] = beta

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=180,
        )
    if response.status_code != 200:
        err_body = response.text[:800]
        logger.warning(
            "Anthropic tools API error %s: %s", response.status_code, err_body
        )
        try:
            err_json = response.json()
            err_msg = (err_json.get("error") or {}).get("message", err_body)
        except Exception:
            err_msg = err_body
        raise Exception(f"Anthropic API returned {response.status_code}: {err_msg[:400]}")

    data = response.json()
    raw_blocks = data.get("content") or []
    normalized: List[Dict[str, Any]] = []
    for block in raw_blocks:
        btype = block.get("type")
        if btype == "text":
            normalized.append({"type": "text", "text": block.get("text") or ""})
        elif btype == "tool_use":
            normalized.append(
                {
                    "type": "tool_use",
                    "id": block.get("id"),
                    "name": block.get("name") or "",
                    "input": block.get("input") if isinstance(block.get("input"), dict) else {},
                }
            )
        elif btype in ("thinking", "redacted_thinking"):
            # Extended thinking blocks must round-trip on follow-up turns with tools.
            normalized.append(dict(block))
        else:
            normalized.append(block)

    stop_reason = data.get("stop_reason") or "end_turn"
    out: Dict[str, Any] = {
        "stop_reason": stop_reason,
        "content": normalized,
    }
    usage = data.get("usage")
    if isinstance(usage, dict):
        out["usage"] = usage
    return out


def _resolve_cerebras_api_key_for_call(
    api_keys: Optional[Dict[str, Optional[str]]],
) -> str:
    eff = (api_keys or {}).get("cerebras")
    if isinstance(eff, str) and eff.strip():
        return eff.strip()
    return (_get_cerebras_key() or os.environ.get("CEREBRAS_API_KEY") or "").strip()


def _resolve_anthropic_api_key_for_call(
    api_keys: Optional[Dict[str, Optional[str]]],
) -> str:
    eff = (api_keys or {}).get("anthropic")
    if isinstance(eff, str) and eff.strip():
        return eff.strip()
    return (os.environ.get("ANTHROPIC_API_KEY") or "").strip()


def _normalize_explicit_model_chain(
    model_chain: Optional[list],
    api_keys: Optional[Dict[str, Optional[str]]],
) -> Optional[List[Tuple[str, str, str]]]:
    """Convert explicit ``[{"provider","model"}, ...]`` chains to router tuples.

    Swarm and ``_get_model_chain`` pass ordered provider dicts (often Cerebras
    first). When this returns ``None``, callers should resolve through
    ``backend.llm_client.get_model_chain_entries``.

    Tuple chains ``(label, model_id, provider)`` are passed through unchanged.
    """
    if not model_chain:
        return None
    first = model_chain[0]
    if isinstance(first, dict):
        out: List[Tuple[str, str, str]] = []
        for entry in model_chain:
            if not isinstance(entry, dict):
                continue
            raw_prov = (entry.get("provider") or "").strip().lower()
            model_id = (entry.get("model") or "").strip()
            if not model_id:
                continue
            provider = raw_prov
            if provider in ("llama", "togetherai", "together_ai"):
                provider = "together"
            if provider == "together":
                if not (os.environ.get("LLAMA_API_KEY") or "").strip():
                    continue
                label = "llama"
            elif provider == "cerebras":
                if not _resolve_cerebras_api_key_for_call(api_keys):
                    continue
                label = "cerebras"
            elif provider == "anthropic":
                if not _resolve_anthropic_api_key_for_call(api_keys):
                    continue
                if "sonnet" in model_id.lower() and not ALLOW_SONNET:
                    continue
                label = "sonnet" if "sonnet" in model_id.lower() else "haiku"
            else:
                continue
            out.append((label, model_id, provider))
        return out or None
    if isinstance(first, (list, tuple)) and len(first) >= 3:
        tuples_out: List[Tuple[str, str, str]] = []
        for x in model_chain:
            if isinstance(x, (list, tuple)) and len(x) >= 3:
                tuples_out.append((str(x[0]), str(x[1]), str(x[2])))
        return tuples_out or None
    return None


async def _call_llm_with_fallback(
    message: str,
    system_message: str,
    session_id: str,
    model_chain: list,
    user_id: Optional[str] = None,
    user_tier: str = "free",
    speed_selector: str = "lite",
    available_credits: int = 0,
    agent_name: str = "",
    api_keys: Optional[Dict[str, Optional[str]]] = None,
    content_blocks: Optional[List[Dict[str, Any]]] = None,
    idempotency_key: Optional[str] = None,
    require_runtime_scope: bool = False,
    intent_schema: Optional[Dict[str, Any]] = None,
) -> tuple:
    """Intelligent LLM router with Cerebras primary and Haiku fallback.

    Routes based on task complexity, user tier, speed selector, and available credits.
    Returns ``(response_text, model_used)`` tuple.
    """
    if require_runtime_scope:
        from backend.services.runtime.execution_authority import require_runtime_authority

        require_runtime_authority("llm_service", detail="model execution")

    task_label = "explicit"

    explicit = _normalize_explicit_model_chain(model_chain, api_keys)
    if explicit is not None:
        model_chain = explicit
    else:
        task_label = _policy_task_type(
            "auto",
            message,
            force_complex=speed_selector == "max",
            agent_name=agent_name,
        )
        model_chain = _normalize_explicit_model_chain(
            get_model_chain_entries(task_label),
            api_keys,
        ) or []
        if not model_chain:
            # Compatibility path for tests/legacy callers that monkeypatch the
            # router object. The router module is now a facade over llm_client.
            model_chain = llm_router.get_model_chain(
                task_complexity=classifier.classify(message, agent_name),
                user_tier=user_tier,
                speed_selector=speed_selector,
                available_credits=available_credits,
            )
    try:
        event_bus.emit(
            "provider.chain.selected",
            {
                "task_complexity": task_label,
                "chain": [
                    {
                        "name": name,
                        "model": model_id,
                        "provider": provider,
                    }
                    for (name, model_id, provider) in model_chain
                ],
                "agent_name": agent_name,
                "session_id": session_id,
            },
        )
    except Exception:
        logger.debug("provider.chain.selected event emission failed")

    if not model_chain:
        raise ValueError(
            "No LLM models available. Configure LLAMA_API_KEY, CEREBRAS_API_KEY, or ANTHROPIC_API_KEY."
        )

    last_error = None

    for model_info in model_chain:
        model_name, model_id, provider = model_info
        if provider == "anthropic" and "sonnet" in model_id.lower():
            if not ALLOW_SONNET:
                continue
            if _USAGE_WINDOW_TOTAL_TOKENS > 0 and not ALLOW_SONNET_OVER_1_PERCENT:
                sonnet_used = sum(v for k, v in _USAGE_WINDOW_BY_MODEL.items() if "/claude-sonnet" in k)
                if (sonnet_used / _USAGE_WINDOW_TOTAL_TOKENS) * 100.0 > 1.0:
                    logger.error("provider.policy.sonnet_blocked_over_share model=%s", model_id)
                    continue

        try:
            logger.info(
                "provider.fallback.attempt session_id=%s agent=%s task=%s provider=%s model_id=%s label=%s",
                session_id,
                agent_name,
                task_label,
                provider,
                model_id,
                model_name,
            )
            try:
                event_bus.emit(
                    "provider.call.started",
                    {
                        "provider": provider,
                        "model_name": model_name,
                        "model_id": model_id,
                        "task_complexity": task_label,
                        "agent_name": agent_name,
                        "session_id": session_id,
                    },
                )
                event_bus.emit(
                    "model_call",
                    {
                        "provider": provider,
                        "model_name": model_name,
                        "model_id": model_id,
                        "task_complexity": task_label,
                        "agent_name": agent_name,
                        "session_id": session_id,
                    },
                )
            except Exception:
                logger.debug("provider.call.started event emission failed")

            if provider == "together" and os.environ.get("LLAMA_API_KEY"):
                response = await _call_llama_direct(
                    message,
                    system_message,
                    model=model_id,
                    api_key=os.environ.get("LLAMA_API_KEY"),
                )
                try:
                    event_bus.emit(
                        "provider.call.succeeded",
                        {
                            "provider": provider,
                            "model_name": model_name,
                            "model_id": model_id,
                            "session_id": session_id,
                        },
                    )
                except Exception:
                    logger.debug("provider.call.succeeded event emission failed")
                logger.info(
                    "provider.fallback.succeeded session_id=%s provider=%s model_id=%s",
                    session_id,
                    provider,
                    model_id,
                )
                _record_provider_usage(provider, model_id, task_label, message, response)
                return (response, f"llama/{model_id}")

            elif provider == "cerebras":
                cerebras_key = _resolve_cerebras_api_key_for_call(api_keys)
                response = await _call_cerebras_direct(
                    message,
                    system_message,
                    model=model_id,
                    api_key=cerebras_key or None,
                )
                try:
                    event_bus.emit(
                        "provider.call.succeeded",
                        {
                            "provider": provider,
                            "model_name": model_name,
                            "model_id": model_id,
                            "session_id": session_id,
                        },
                    )
                except Exception:
                    logger.debug("provider.call.succeeded event emission failed")
                logger.info(
                    "provider.fallback.succeeded session_id=%s provider=%s model_id=%s",
                    session_id,
                    provider,
                    model_id,
                )
                _record_provider_usage(provider, model_id, task_label, message, response)
                return (response, f"cerebras/{model_id}")

            elif provider == "anthropic":
                anthropic_key = _resolve_anthropic_api_key_for_call(api_keys)
                response = await _call_anthropic_direct(
                    message,
                    system_message,
                    model=model_id,
                    api_key=anthropic_key or None,
                )
                try:
                    event_bus.emit(
                        "provider.call.succeeded",
                        {
                            "provider": provider,
                            "model_name": model_name,
                            "model_id": model_id,
                            "session_id": session_id,
                        },
                    )
                except Exception:
                    logger.debug("provider.call.succeeded event emission failed")
                logger.info(
                    "provider.fallback.succeeded session_id=%s provider=%s model_id=%s",
                    session_id,
                    provider,
                    model_id,
                )
                _record_provider_usage(provider, model_id, task_label, message, response)
                return (response, f"{model_name}/{model_id}")

        except Exception as e:
            last_error = e
            err_str = str(e)
            try:
                event_bus.emit(
                    "provider.call.failed",
                    {
                        "provider": provider,
                        "model_name": model_name,
                        "model_id": model_id,
                        "error": err_str,
                        "session_id": session_id,
                    },
                )
            except Exception:
                logger.debug("provider.call.failed event emission failed")
            low = err_str.lower()
            transient = (
                "RATE_LIMITED" in err_str
                or "rate limit" in low
                or "429" in err_str
                or "credit" in low
                or "billing" in low
                or "balance" in low
                or "402" in err_str
                or "401" in err_str
                or "403" in err_str
                or "overloaded" in low
                or "capacity" in low
            )
            if transient:
                logger.warning(
                    "provider.fallback.failed_transient session_id=%s provider=%s model=%s "
                    "trying_next_in_chain err=%s",
                    session_id,
                    provider,
                    model_id,
                    err_str[:400],
                )
            else:
                logger.warning(
                    "provider.fallback.failed session_id=%s provider=%s model=%s trying_next err=%s",
                    session_id,
                    provider,
                    model_id,
                    err_str[:400],
                )
            continue

    error_msg = f"All LLM models failed. Last error: {last_error}"
    logger.error(error_msg)
    raise last_error or Exception(error_msg)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    "get_authenticated_or_api_user",
    "_auto_detect_skill",
    "_is_product_support_query",
    "_classify_task_complexity",
    "detect_task_type",
    "_provider_has_key",
    "_filter_chain_by_keys",
    "_get_model_chain",
    "get_workspace_api_keys",
    "_effective_api_keys",
    "_call_anthropic_multimodal",
    "_content_blocks_have_image",
    "_call_llama_direct",
    "_call_cerebras_direct",
    "_call_anthropic_direct",
    "_call_anthropic_messages_with_tools",
    "_call_llm_with_fallback",
    # Constants
    "SKILL_TRIGGERS",
    "MODEL_CONFIG",
    "MODEL_FALLBACK_CHAINS",
    "MODEL_CHAINS",
    "VISION_MODEL_CHAIN",
]
