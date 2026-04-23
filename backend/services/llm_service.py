"""LLM service helpers extracted from server.py.

Provides authentication dependency, task classification, model chain selection,
and direct LLM call helpers (Anthropic, Cerebras, Llama) with fallback logic.
"""

import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from dotenv import load_dotenv
from fastapi import Depends, HTTPException

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env", override=True)

from ..anthropic_models import ANTHROPIC_HAIKU_MODEL, normalize_anthropic_model
from ..deps import get_optional_user
from ..dev_stub_llm import REAL_AGENT_NO_LLM_KEYS_DETAIL, chat_llm_available
from ..dev_stub_llm import detect_build_kind as _stub_detect_build_kind
from ..dev_stub_llm import is_real_agent_only
from ..dev_stub_llm import plan_and_suggestions as _stub_plan_and_suggestions
from ..dev_stub_llm import stub_build_enabled, stub_file_dict, stub_multifile_markdown
from ..llm_router import CEREBRAS_MODEL
from ..llm_router import TaskComplexity, classifier
from ..llm_router import get_cerebras_key as _get_cerebras_key
from ..llm_router import router as llm_router
from .events import event_bus
from .skills import detect_skill

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Runtime API key references (resolved at call time so .env changes work)
# ---------------------------------------------------------------------------

ANTHROPIC_API_KEY: Optional[str] = os.environ.get("ANTHROPIC_API_KEY")

# ---------------------------------------------------------------------------
# Model configuration (mirrors server.py definitions)
# ---------------------------------------------------------------------------

MODEL_CONFIG: Dict[str, Dict[str, str]] = {
    "code": {"provider": "anthropic", "model": ANTHROPIC_HAIKU_MODEL},
    "analysis": {"provider": "anthropic", "model": ANTHROPIC_HAIKU_MODEL},
    "general": {"provider": "anthropic", "model": ANTHROPIC_HAIKU_MODEL},
    "creative": {"provider": "anthropic", "model": ANTHROPIC_HAIKU_MODEL},
    "fast": {"provider": "anthropic", "model": ANTHROPIC_HAIKU_MODEL},
}

MODEL_FALLBACK_CHAINS: List[Dict[str, str]] = [
    {"provider": "anthropic", "model": ANTHROPIC_HAIKU_MODEL},
]

MODEL_CHAINS: Dict[str, Any] = {
    "auto": None,  # resolved dynamically via MODEL_CONFIG + MODEL_FALLBACK_CHAINS
    "haiku": [{"provider": "anthropic", "model": ANTHROPIC_HAIKU_MODEL}],
}

# Vision-capable model chain
VISION_MODEL_CHAIN: List[Dict[str, str]] = [
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
) -> List[Dict[str, str]]:
    """Return a list of {provider, model} dicts to try in order.

    Cerebras (default llama3.1-8b, env CEREBRAS_MODEL) for fast/simple tasks; Haiku for complex/build tasks.
    ``force_complex=True`` always selects Haiku (for iterative builds).
    """
    cerebras_key = (effective_keys or {}).get("cerebras") or os.environ.get(
        "CEREBRAS_API_KEY"
    )
    anthropic_key = (effective_keys or {}).get("anthropic") or os.environ.get(
        "ANTHROPIC_API_KEY"
    )

    if model_key == "auto":
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
                chain = [
                    {"provider": "cerebras", "model": CEREBRAS_MODEL},
                    {"provider": "anthropic", "model": ANTHROPIC_HAIKU_MODEL},
                ]
            elif anthropic_key:
                chain = [
                    {"provider": "anthropic", "model": ANTHROPIC_HAIKU_MODEL},
                    {"provider": "cerebras", "model": CEREBRAS_MODEL},
                ]
            elif cerebras_key:
                chain = [{"provider": "cerebras", "model": CEREBRAS_MODEL}]
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
) -> tuple:
    """Intelligent LLM router with Cerebras primary and Haiku fallback.

    Routes based on task complexity, user tier, speed selector, and available credits.
    Returns ``(response_text, model_used)`` tuple.
    """
    if require_runtime_scope:
        from services.runtime.execution_authority import require_runtime_authority

        require_runtime_authority("llm_service", detail="model execution")

    task_complexity = classifier.classify(message, agent_name)

    model_chain = llm_router.get_model_chain(
        task_complexity=task_complexity,
        user_tier=user_tier,
        speed_selector=speed_selector,
        available_credits=available_credits,
    )
    try:
        event_bus.emit(
            "provider.chain.selected",
            {
                "task_complexity": str(task_complexity),
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

        try:
            logger.info(f"Trying {provider}/{model_name} for task: {task_complexity}")
            try:
                event_bus.emit(
                    "provider.call.started",
                    {
                        "provider": provider,
                        "model_name": model_name,
                        "model_id": model_id,
                        "task_complexity": str(task_complexity),
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
                        "task_complexity": str(task_complexity),
                        "agent_name": agent_name,
                        "session_id": session_id,
                    },
                )
            except Exception:
                logger.debug("provider.call.started event emission failed")

            if provider == "together" and llm_router.llama_available:
                response = await _call_llama_direct(
                    message,
                    system_message,
                    model=model_id,
                    api_key=llm_router.llama_available
                    and os.environ.get("LLAMA_API_KEY"),
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
                return (response, f"llama/{model_id}")

            elif provider == "cerebras" and llm_router.cerebras_available:
                response = await _call_cerebras_direct(
                    message,
                    system_message,
                    model=model_id,
                    api_key=_get_cerebras_key() or os.environ.get("CEREBRAS_API_KEY"),
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
                return (response, f"cerebras/{model_id}")

            elif provider == "anthropic" and llm_router.haiku_available:
                response = await _call_anthropic_direct(
                    message,
                    system_message,
                    model=model_id,
                    api_key=os.environ.get("ANTHROPIC_API_KEY"),
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
                return (response, f"haiku/{model_id}")

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
    "_call_llm_with_fallback",
    # Constants
    "SKILL_TRIGGERS",
    "MODEL_CONFIG",
    "MODEL_FALLBACK_CHAINS",
    "MODEL_CHAINS",
    "VISION_MODEL_CHAIN",
]
