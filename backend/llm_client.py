"""Unified LLM client for CrucibAI.

Routing policy from the approved Claude Code fusion notes:
- Cerebras is the volume execution engine for generation and repair patches.
- Haiku is the reasoning and validation quality gate.
- Sonnet is disabled unless ALLOW_SONNET=true and the task is explicitly
  one of the premium/deep proof capabilities.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

from backend.anthropic_models import (
    ANTHROPIC_HAIKU_MODEL,
    ANTHROPIC_SONNET_MODEL,
    normalize_anthropic_model,
)

logger = logging.getLogger(__name__)

CEREBRAS_MODEL = (os.environ.get("CEREBRAS_MODEL") or "llama3.1-8b").strip()
HAIKU_MODEL = ANTHROPIC_HAIKU_MODEL
SONNET_MODEL = ANTHROPIC_SONNET_MODEL


CEREBRAS_FIRST_TASKS = {
    "agent_swarm_worker",
    "animation",
    "backend_generation",
    "brand",
    "code",
    "code_generate",
    "code_generation",
    "component_generation",
    "dark_mode",
    "documentation",
    "draft",
    "email_template",
    "feature_generation",
    "frontend_generation",
    "i18n",
    "notification",
    "patch_generation",
    "repair_patch",
    "repair_patch_generation",
    "responsive",
    "scaffold",
    "seo",
    "styling",
    "typography",
    "worker",
}

HAIKU_FIRST_TASKS = {
    "architecture",
    "audit",
    "build_integrity_validator",
    "build_plan",
    "complex_chat_or_requirements_clarification",
    "hard_failure_triage",
    "planning",
    "proof",
    "reasoning",
    "repair_diagnosis",
    "review",
    "security",
    "security_review",
    "standard_final_proof",
    "validation",
    "verification",
}

SONNET_ALLOWED_TASKS = {
    "enterprise_deep_review",
    "fullstack_auth_payment_review",
    "hard_failure_adjudication",
    "premium_final_proof",
    "security_review",
}

# Back-compat names used by older tests/importers. This set intentionally no
# longer includes generation tasks.
ANTHROPIC_REQUIRED_TASKS = HAIKU_FIRST_TASKS
CEREBRAS_OK_TASKS = CEREBRAS_FIRST_TASKS

ALLOW_SONNET = os.environ.get("ALLOW_SONNET", "false").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
SONNET_MAX_PLATFORM_TOKEN_SHARE = float(
    os.environ.get("SONNET_MAX_PLATFORM_TOKEN_SHARE", "0.01") or "0.01"
)
SONNET_MAX_TOKENS_PER_RUN = int(
    os.environ.get("SONNET_MAX_TOKENS_PER_RUN", "12000") or "12000"
)


@dataclass
class LLMConfig:
    """Concrete provider configuration for one model attempt."""

    provider: str
    api_key: str
    model: str
    max_tokens: int = 4000
    temperature: float = 0.7


def _primary_llm_is_cerebras() -> bool:
    value = (
        os.environ.get("PRIMARY_LLM_PROVIDER", "")
        or os.environ.get("CRUCIB_PRIMARY_LLM", "")
    ).strip().lower()
    return value in {"cerebras", "cerebra", "cb"}


def _task_matches(task_type: str, names: Sequence[str]) -> bool:
    task_lower = (task_type or "").strip().lower()
    if not task_lower:
        return False
    return any(name in task_lower for name in names)


def _sonnet_allowed_for_task(task_type: str) -> bool:
    return ALLOW_SONNET and _task_matches(task_type, SONNET_ALLOWED_TASKS)


def _get_cerebras_key() -> str:
    try:
        from backend.cerebras_roundrobin import get_next_cerebras_key

        return get_next_cerebras_key()
    except Exception as exc:
        key = os.environ.get("CEREBRAS_API_KEY", "").strip()
        if not key:
            logger.debug("No Cerebras key available from pool or env: %s", exc)
        return key


def get_cerebras_key() -> str:
    """Public compatibility wrapper for the single Cerebras key source."""

    return _get_cerebras_key()


def _get_anthropic_key() -> str:
    return os.environ.get("ANTHROPIC_API_KEY", "").strip()


def _cerebras_config(temperature: float = 0.7) -> Optional[LLMConfig]:
    key = _get_cerebras_key()
    if not key:
        return None
    return LLMConfig(
        provider="cerebras",
        api_key=key,
        model=(os.environ.get("CEREBRAS_MODEL") or "llama3.1-8b").strip(),
        max_tokens=4096,
        temperature=temperature,
    )


def _haiku_config(temperature: float = 0.7) -> Optional[LLMConfig]:
    key = _get_anthropic_key()
    if not key:
        return None
    model = normalize_anthropic_model(
        os.environ.get("ANTHROPIC_HAIKU_MODEL") or os.environ.get("ANTHROPIC_MODEL"),
        default=ANTHROPIC_HAIKU_MODEL,
    )
    if "sonnet" in model.lower():
        model = ANTHROPIC_HAIKU_MODEL
    return LLMConfig(
        provider="anthropic",
        api_key=key,
        model=model,
        max_tokens=4096,
        temperature=temperature,
    )


def _sonnet_config(temperature: float = 0.7) -> Optional[LLMConfig]:
    key = _get_anthropic_key()
    if not key:
        return None
    model = normalize_anthropic_model(
        os.environ.get("ANTHROPIC_SONNET_MODEL") or os.environ.get("ANTHROPIC_MODEL"),
        default=ANTHROPIC_SONNET_MODEL,
    )
    if "sonnet" not in model.lower():
        model = ANTHROPIC_SONNET_MODEL
    return LLMConfig(
        provider="anthropic",
        api_key=key,
        model=model,
        max_tokens=min(SONNET_MAX_TOKENS_PER_RUN, 8192),
        temperature=temperature,
    )


def get_route_labels(task_type: str) -> List[str]:
    if _sonnet_allowed_for_task(task_type):
        return ["sonnet", "haiku", "cerebras"]

    if _task_matches(task_type, HAIKU_FIRST_TASKS):
        return ["haiku", "cerebras"]

    if _primary_llm_is_cerebras() or _task_matches(task_type, CEREBRAS_FIRST_TASKS):
        return ["cerebras", "haiku"]

    return ["cerebras", "haiku"]


def get_model_chain_entries(task_type: str) -> List[Dict[str, str]]:
    """Return provider/model entries without owning another routing policy."""

    entries: List[Dict[str, str]] = []
    for label in get_route_labels(task_type):
        if label == "sonnet":
            entries.append({"provider": "anthropic", "model": SONNET_MODEL})
        elif label == "haiku":
            entries.append({"provider": "anthropic", "model": HAIKU_MODEL})
        elif label == "cerebras":
            entries.append({"provider": "cerebras", "model": CEREBRAS_MODEL})
    return entries


def get_llm_chain(task_type: str = "", temperature: float = 0.7) -> List[LLMConfig]:
    """Return provider attempts in approved order for this capability."""

    configs: List[LLMConfig] = []
    seen: set[tuple[str, str]] = set()
    for label in get_route_labels(task_type):
        config: Optional[LLMConfig]
        if label == "sonnet":
            config = _sonnet_config(temperature)
        elif label == "haiku":
            config = _haiku_config(temperature)
        else:
            config = _cerebras_config(temperature)
        if not config:
            continue
        key = (config.provider, config.model)
        if key in seen:
            continue
        seen.add(key)
        configs.append(config)
    return configs


def get_llm_config(task_type: str = "") -> Optional[LLMConfig]:
    """Back-compat helper returning the first configured model for a task."""

    chain = get_llm_chain(task_type)
    if chain:
        return chain[0]
    logger.warning("No LLM API keys configured for task=%s", task_type or "default")
    return None


async def call_claude(
    system_prompt: str,
    user_prompt: str,
    config: LLMConfig,
    max_retries: int = 3,
) -> Optional[str]:
    """Call Anthropic with retry logic."""

    try:
        import anthropic
    except ImportError:
        logger.error("anthropic library not installed")
        return None

    client = anthropic.AsyncAnthropic(api_key=config.api_key)
    for attempt in range(max_retries):
        try:
            message = await client.messages.create(
                model=normalize_anthropic_model(config.model, default=ANTHROPIC_HAIKU_MODEL),
                max_tokens=config.max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                temperature=config.temperature,
            )
            return message.content[0].text if message.content else None
        except Exception as exc:
            if attempt >= max_retries - 1:
                logger.error("Anthropic API failed after %d attempts: %s", max_retries, exc)
                raise
            wait_time = 2**attempt
            logger.warning(
                "Anthropic API error attempt=%d wait=%ds error=%s",
                attempt + 1,
                wait_time,
                exc,
            )
            await asyncio.sleep(wait_time)
    return None


async def call_cerebras(
    system_prompt: str,
    user_prompt: str,
    config: LLMConfig,
    max_retries: int = 3,
) -> Optional[str]:
    """Call Cerebras with retry logic and round-robin failover on rate limits."""

    try:
        import httpx
    except ImportError:
        logger.error("httpx library not installed")
        return None

    combined_len = len(system_prompt or "") + len(user_prompt or "")
    estimated_tokens = combined_len // 4
    if estimated_tokens > 7500:
        logger.warning(
            "Cerebras prompt estimated at %d tokens; generation may need a smaller proof packet.",
            estimated_tokens,
        )

    payload = {
        "model": config.model,
        "max_tokens": min(config.max_tokens, 4096),
        "temperature": config.temperature,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    api_key = config.api_key
    for attempt in range(max_retries):
        if attempt > 0:
            api_key = _get_cerebras_key() or api_key
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.cerebras.ai/v1/chat/completions",
                    json=payload,
                    headers=headers,
                    timeout=60.0,
                )
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            if response.status_code == 429 and attempt < max_retries - 1:
                logger.warning("Cerebras rate limited; rotating key and retrying")
                await asyncio.sleep(2**attempt)
                continue
            raise RuntimeError(f"Cerebras API error: {response.status_code} {response.text}")
        except Exception as exc:
            if attempt >= max_retries - 1:
                logger.error("Cerebras API failed after %d attempts: %s", max_retries, exc)
                raise
            wait_time = 2**attempt
            logger.warning(
                "Cerebras error attempt=%d wait=%ds error=%s",
                attempt + 1,
                wait_time,
                exc,
            )
            await asyncio.sleep(wait_time)
    return None


async def call_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    task_type: str = "",
) -> Optional[str]:
    """Call the first available model in the approved fallback chain."""

    chain = get_llm_chain(task_type, temperature=temperature)
    if not chain:
        logger.error("No LLM configured for task=%s", task_type or "default")
        return None

    last_error: Optional[Exception] = None
    for config in chain:
        logger.info(
            "LLM call: provider=%s model=%s task=%s",
            config.provider,
            config.model,
            task_type or "default",
        )
        try:
            if config.provider == "anthropic":
                return await call_claude(system_prompt, user_prompt, config)
            if config.provider == "cerebras":
                return await call_cerebras(system_prompt, user_prompt, config)
            logger.error("Unknown LLM provider: %s", config.provider)
        except Exception as exc:
            last_error = exc
            logger.warning(
                "LLM attempt failed provider=%s model=%s task=%s error=%s",
                config.provider,
                config.model,
                task_type or "default",
                exc,
            )
    if last_error:
        logger.error("All LLM attempts failed for task=%s: %s", task_type or "default", last_error)
    return None


async def call_llm_simple(
    prompt: str,
    task_type: str = "code_generation",
    system_prompt: str = "You are CrucibAI's backend build assistant.",
    temperature: float = 0.3,
) -> Optional[str]:
    """Small compatibility wrapper used by repair/build services."""

    return await call_llm(
        system_prompt=system_prompt,
        user_prompt=prompt,
        temperature=temperature,
        task_type=task_type,
    )


async def parse_json_response(
    response: str, required_keys: List[str] = None
) -> Optional[Dict[str, Any]]:
    """Parse JSON response from an LLM with optional required-key validation."""

    if not response:
        return None
    try:
        if "```json" in response:
            start = response.index("```json") + 7
            end = response.index("```", start)
            json_str = response[start:end].strip()
        elif "```" in response:
            start = response.index("```") + 3
            end = response.index("```", start)
            json_str = response[start:end].strip()
        else:
            json_str = response.strip()
        data = json.loads(json_str)
        if required_keys:
            missing = [key for key in required_keys if key not in data]
            if missing:
                logger.error("Missing required keys in response: %s", missing)
                return None
        return data
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse JSON response: %s", exc)
        return None
    except Exception as exc:
        logger.error("Error parsing response: %s", exc)
        return None


def _truncate(value: Any, limit: int) -> Any:
    if isinstance(value, str):
        return value[:limit]
    if isinstance(value, list):
        return [_truncate(item, limit) for item in value[:20]]
    if isinstance(value, dict):
        return {str(k)[:80]: _truncate(v, limit) for k, v in list(value.items())[:40]}
    return value


def build_sonnet_proof_packet(
    *,
    goal: str = "",
    plan: Optional[Dict[str, Any]] = None,
    verification: Optional[Dict[str, Any]] = None,
    files_changed: Optional[List[str]] = None,
    risks: Optional[List[str]] = None,
    max_chars: int = 16000,
) -> str:
    """Build the compressed packet Sonnet is allowed to inspect."""

    packet = {
        "goal": _truncate(goal, 2000),
        "plan": _truncate(plan or {}, 1200),
        "verification": _truncate(verification or {}, 2000),
        "files_changed": (files_changed or [])[:80],
        "risks": (risks or [])[:40],
        "sonnet_scope": sorted(SONNET_ALLOWED_TASKS),
    }
    text = json.dumps(packet, ensure_ascii=True, separators=(",", ":"))
    return text[:max_chars]


async def call_llm_for_code(
    goal: str,
    context: str,
    language: str = "JavaScript",
    instructions: str = "",
    task_type: str = "frontend_generation",
) -> Optional[Dict[str, str]]:
    """Generate code through the approved task route, usually Cerebras first."""

    system_prompt = f"""You are an expert {language} developer. Generate production-ready {language} code.

Code must:
- Be complete and runnable
- Include all necessary imports
- Have proper error handling
- Follow {language} best practices
- Be properly formatted and indented

CRITICAL: Respond with ONLY valid {language} code. No markdown. No explanation.
Your response must start with the first line of code (import/function/const/def).
Never start with a word, sentence, or any explanation."""

    user_prompt = f"""Goal: {goal}

Context: {context}

{instructions}

Generate the complete {language} code now."""

    response = await call_llm(
        system_prompt, user_prompt, temperature=0.7, task_type=task_type
    )
    if not response:
        return None
    return {"code": response, "language": language, "length": len(response)}


async def call_llm_for_structured_output(
    task: str,
    context: str,
    schema_description: str = "",
    task_type: str = "planning",
) -> Optional[Dict[str, Any]]:
    """Generate structured JSON, using Haiku first for planning/validation tasks."""

    system_prompt = f"""You are a helpful assistant that generates structured data.

Always respond with ONLY valid JSON, no markdown, no explanation.

{schema_description}"""

    user_prompt = f"""Task: {task}

Context: {context}

Generate the JSON now."""

    response = await call_llm(
        system_prompt, user_prompt, temperature=0.3, task_type=task_type
    )
    if not response:
        return None
    return await parse_json_response(response)
