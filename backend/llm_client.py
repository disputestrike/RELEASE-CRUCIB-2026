"""
LLM Client — Unified interface for Claude/Cerebras API calls.
Handles authentication, prompt building, structured response parsing, retries.

Model routing policy:
  - PLANNING / ARCHITECTURE / REASONING → Anthropic (long context, strong reasoning)
  - CODE GENERATION (large) → Anthropic (avoids Cerebras 8K token limit)
  - CODE GENERATION (small/fast) → Cerebras (fast, cheap, good for <8K)
  - VERIFICATION / SECURITY REVIEW → Anthropic (most reliable reviewer)
  - FALLBACK → whichever key is available
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from backend.anthropic_models import ANTHROPIC_SONNET_MODEL, normalize_anthropic_model

logger = logging.getLogger(__name__)

# Task types that MUST use Anthropic (long context or reasoning-heavy)
ANTHROPIC_REQUIRED_TASKS = {
    "planning",
    "architecture",
    "reasoning",
    "verification",
    "security",
    "frontend_generation",
    "backend_generation",
    "multi_tenant",
    "rag",
    "embedding",
    "review",
    "audit",
}

# Task types that can use Cerebras (fast, small outputs)
CEREBRAS_OK_TASKS = {
    "styling",
    "color_palette",
    "typography",
    "animation",
    "brand",
    "responsive",
    "dark_mode",
    "seo",
    "i18n",
    "notification",
    "email_template",
    "documentation",
}


@dataclass
class LLMConfig:
    """LLM configuration from environment."""

    provider: str  # "anthropic" or "cerebras"
    api_key: str
    model: str
    max_tokens: int = 4000
    temperature: float = 0.7


def get_llm_config(task_type: str = "") -> Optional[LLMConfig]:
    """
    Load LLM config with smart model routing based on task type.

    Large/complex tasks → Anthropic (200K context, superior reasoning)
    Small/fast tasks → Cerebras (if available, avoids 8K limit issues)
    """
    task_lower = task_type.lower()

    claude_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    cerebras_key = os.environ.get("CEREBRAS_API_KEY", "").strip()

    # Determine if this task REQUIRES Anthropic
    needs_anthropic = any(t in task_lower for t in ANTHROPIC_REQUIRED_TASKS)
    cerebras_ok = any(t in task_lower for t in CEREBRAS_OK_TASKS)

    # Route: if task needs Anthropic and we have the key, use it
    if claude_key and (needs_anthropic or not cerebras_ok or not cerebras_key):
        model = normalize_anthropic_model(
            os.environ.get("ANTHROPIC_MODEL"),
            default=ANTHROPIC_SONNET_MODEL,
        )
        logger.debug(
            "LLM routing: task=%s → anthropic/%s", task_type or "default", model
        )
        return LLMConfig(provider="anthropic", api_key=claude_key, model=model)

    # Route: small/fast task can use Cerebras
    if cerebras_key and cerebras_ok:
        model = os.environ.get("CEREBRAS_MODEL", "llama3.1-8b")
        logger.debug("LLM routing: task=%s → cerebras/%s", task_type, model)
        return LLMConfig(provider="cerebras", api_key=cerebras_key, model=model)

    # Fallback: use whatever key we have
    if claude_key:
        model = normalize_anthropic_model(
            os.environ.get("ANTHROPIC_MODEL"),
            default=ANTHROPIC_SONNET_MODEL,
        )
        return LLMConfig(provider="anthropic", api_key=claude_key, model=model)

    if cerebras_key:
        model = os.environ.get("CEREBRAS_MODEL", "llama3.1-8b")
        return LLMConfig(provider="cerebras", api_key=cerebras_key, model=model)

    logger.warning("No LLM API keys configured (ANTHROPIC_API_KEY or CEREBRAS_API_KEY)")
    return None


async def call_claude(
    system_prompt: str,
    user_prompt: str,
    config: LLMConfig,
    max_retries: int = 3,
) -> Optional[str]:
    """Call Claude API with retry logic."""
    try:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=config.api_key)

        for attempt in range(max_retries):
            try:
                message = await client.messages.create(
                    model=config.model,
                    max_tokens=config.max_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                    temperature=config.temperature,
                )
                return message.content[0].text if message.content else None

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        "Claude API error (attempt %d): %s, retrying in %ds",
                        attempt + 1,
                        e,
                        wait_time,
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        "Claude API failed after %d attempts: %s", max_retries, e
                    )
                    raise

    except ImportError:
        logger.error("anthropic library not installed")
        return None


async def call_cerebras(
    system_prompt: str,
    user_prompt: str,
    config: LLMConfig,
    max_retries: int = 3,
) -> Optional[str]:
    """Call Cerebras API with retry logic and token limit guard."""
    try:
        import httpx

        # Guard: Cerebras has 8192 token limit — estimate and warn
        combined_len = len(system_prompt) + len(user_prompt)
        estimated_tokens = combined_len // 4  # rough estimate
        if estimated_tokens > 7500:
            logger.warning(
                "Cerebras prompt estimated at %d tokens (limit 8192). "
                "Consider routing to Anthropic for this task.",
                estimated_tokens,
            )

        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": config.model,
            "max_tokens": min(config.max_tokens, 4096),  # Cerebras safe max
            "temperature": config.temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        for attempt in range(max_retries):
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
                    elif response.status_code == 429:
                        if attempt < max_retries - 1:
                            wait_time = 2**attempt
                            logger.warning(
                                "Cerebras rate limited, retrying in %ds", wait_time
                            )
                            await asyncio.sleep(wait_time)
                        else:
                            raise Exception("Rate limited after retries")
                    else:
                        raise Exception(
                            f"Cerebras API error: {response.status_code} {response.text}"
                        )

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        "Cerebras error (attempt %d): %s, retrying in %ds",
                        attempt + 1,
                        e,
                        wait_time,
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        "Cerebras API failed after %d attempts: %s", max_retries, e
                    )
                    raise

    except ImportError:
        logger.error("httpx library not installed")
        return None


async def call_llm(
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.7,
    task_type: str = "",
) -> Optional[str]:
    """
    Call LLM with smart routing based on task type.

    task_type hints: "planning", "frontend_generation", "backend_generation",
                     "verification", "security", "styling", "brand", etc.
    """
    config = get_llm_config(task_type)
    if not config:
        logger.error("No LLM configured - returning None")
        return None

    logger.info(
        "LLM call: provider=%s model=%s task=%s",
        config.provider,
        config.model,
        task_type or "default",
    )

    try:
        config.temperature = temperature
        if config.provider == "anthropic":
            return await call_claude(system_prompt, user_prompt, config)
        elif config.provider == "cerebras":
            return await call_cerebras(system_prompt, user_prompt, config)
        else:
            logger.error("Unknown LLM provider: %s", config.provider)
            return None

    except Exception as e:
        logger.exception("LLM call failed: %s", e)
        # Auto-fallback: if Cerebras failed, try Anthropic
        if config.provider == "cerebras":
            claude_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
            if claude_key:
                logger.warning("Cerebras failed, falling back to Anthropic")
                fallback = LLMConfig(
                    provider="anthropic",
                    api_key=claude_key,
                    model=normalize_anthropic_model(
                        None, default=ANTHROPIC_SONNET_MODEL
                    ),
                    temperature=temperature,
                )
                return await call_claude(system_prompt, user_prompt, fallback)
        return None


async def parse_json_response(
    response: str, required_keys: List[str] = None
) -> Optional[Dict[str, Any]]:
    """Parse JSON response from LLM with validation."""
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
            json_str = response
        data = json.loads(json_str)
        if required_keys:
            missing = [k for k in required_keys if k not in data]
            if missing:
                logger.error("Missing required keys in response: %s", missing)
                return None
        return data
    except json.JSONDecodeError as e:
        logger.error("Failed to parse JSON response: %s", e)
        return None
    except Exception as e:
        logger.error("Error parsing response: %s", e)
        return None


async def call_llm_for_code(
    goal: str,
    context: str,
    language: str = "JavaScript",
    instructions: str = "",
    task_type: str = "frontend_generation",
) -> Optional[Dict[str, str]]:
    """Call LLM to generate code — always routed to Anthropic for quality."""
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

    return {
        "code": response,
        "language": language,
        "length": len(response),
    }


async def call_llm_for_structured_output(
    task: str,
    context: str,
    schema_description: str = "",
    task_type: str = "planning",
) -> Optional[Dict[str, Any]]:
    """Call LLM to generate structured JSON output — routed to Anthropic for reliability."""
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
