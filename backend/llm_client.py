"""
LLM Client — Unified interface for Cerebras/Claude API calls.
Handles authentication, prompt building, structured response parsing, retries.

Model routing policy (capability-based):
  CEREBRAS primary (70-80% of tokens) — mechanical execution volume:
    intent_parse, simple_chat, drafting, code_generate, component_generation,
    boilerplate_generation, landing_page_generate, file_summarization,
    log_error_summary, agent_swarm_worker, worker_agent, cheap_refutation,
    repair_patch_generation, expo_metadata, expo_repair_generation,
    scaffolding, backend_scaffold_generation, generated_file_expansion

  HAIKU primary (20-30% of tokens) — reasoning/validation authority:
    complex_chat, requirements_clarification, build_plan, architecture_plan,
    validation, build_integrity, repair_diagnosis, standard_final_proof,
    should_escalate, backend_scaffold_plan, db_auth_payment_plan,
    review, audit, security, verification, planning, architecture, reasoning

  SONNET: disabled by default, 0% of tokens.
    Requires ALLOW_SONNET=true env gate.
    Only: premium_final_proof, hard_failure_adjudication, security_review,
           fullstack_auth_payment_review, enterprise_deep_review

Key rule: worker agents ALWAYS use Cerebras. Never Anthropic. Never Sonnet.
Key rule: Anthropic failure must never stop agents — Cerebras keeps builds alive.
Key rule: Cerebras keys are round-robined (up to 5 keys) — no rate limiting.
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from backend.anthropic_models import ANTHROPIC_HAIKU_MODEL, ANTHROPIC_SONNET_MODEL, normalize_anthropic_model

# Lazy import avoids circular dependency — model_share_enforcer may import llm_router.
def _get_share_enforcer():
    try:
        from backend.model_share_enforcer import share_enforcer  # noqa
        return share_enforcer
    except Exception:
        return None

logger = logging.getLogger(__name__)

# ─── Capability routing tables ────────────────────────────────────────────────
# CEREBRAS handles all high-volume mechanical execution.
CEREBRAS_PRIMARY_TASKS = {
    # Chat / intent
    "intent_parse", "simple_chat", "chat",
    # Drafting and copy
    "drafting", "draft",
    # Code and scaffolding generation (Cerebras writes code, Haiku reviews plans)
    "code_generate", "code_generation", "component_generation",
    "boilerplate_generation", "scaffolding",
    "backend_scaffold_generation", "db_scaffold_generation",
    "landing_page_generate", "landing_page",
    "generated_file_expansion", "file_expansion",
    # Worker agents — Cerebras ONLY, never Anthropic
    "agent_swarm_worker", "worker_agent", "swarm_worker",
    # Summaries and cheap tasks
    "file_summarization", "file_summary", "log_error_summary", "log_summary",
    "cheap_refutation",
    # Repair execution (Cerebras patches, Haiku diagnoses)
    "repair_patch_generation", "repair_patch", "simple_repair",
    # Expo
    "expo_metadata", "expo_repair_generation", "expo_generation",
    # Styling/UI
    "styling", "color_palette", "typography", "animation", "brand",
    "responsive", "dark_mode", "seo", "i18n", "notification",
    "email_template", "documentation",
}

# HAIKU controls all reasoning, validation, and proof-gate decisions.
HAIKU_PRIMARY_TASKS = {
    # Chat requiring deep reasoning
    "complex_chat", "requirements_clarification",
    # Build and architecture decisions
    "build_plan", "planning", "architecture_plan", "architecture",
    # Validation and integrity
    "validation", "build_integrity", "build_integrity_validator",
    # Repair diagnosis (Haiku diagnoses, Cerebras patches)
    "repair_diagnosis",
    # Proof gates
    "standard_final_proof", "proof",
    # Escalation decisions
    "should_escalate",
    # Plan/review phases of scaffolding (generation stays on Cerebras)
    "backend_scaffold_plan", "db_auth_payment_plan",
    # Review, audit, security, verification — Haiku is gatekeeper
    "review", "audit", "security", "verification", "reasoning",
    # Build quality
    "frontend_generation",  # plan on Haiku; but see note below
    "backend_generation",   # plan on Haiku; generation on Cerebras
    "multi_tenant", "rag", "embedding",
}

# SONNET — locked. Requires ALLOW_SONNET=true env gate.
SONNET_GATED_TASKS = {
    "premium_final_proof",
    "hard_failure_adjudication",
    "security_review",
    "fullstack_auth_payment_review",
    "enterprise_deep_review",
}

# Worker-agent tasks — Cerebras ONLY, no Anthropic fallback permitted.
WORKER_AGENT_TASKS = {
    "agent_swarm_worker", "worker_agent", "swarm_worker",
}

# Back-compat import name kept for any code that imported this.
CEREBRAS_OK_TASKS = CEREBRAS_PRIMARY_TASKS


@dataclass
class LLMConfig:
    """LLM configuration from environment."""

    provider: str  # "anthropic" or "cerebras"
    api_key: str
    model: str
    max_tokens: int = 4000
    temperature: float = 0.7
    # True = never fall back to Anthropic (worker agents)
    cerebras_only: bool = False


def _allow_sonnet() -> bool:
    return os.environ.get("ALLOW_SONNET", "false").strip().lower() in {"1", "true", "yes"}


def get_llm_config(task_type: str = "") -> Optional["LLMConfig"]:
    """
    Load LLM config using capability-based routing.

    Decision authority:
      Cerebras  → mechanical execution (70-80% volume)
      Haiku     → reasoning/validation/proof gates (20-30%)
      Sonnet    → locked behind ALLOW_SONNET=true (0% default)

    Worker agents always use Cerebras. Anthropic failure never stops agents.
    """
    task_lower = task_type.lower().strip()

    claude_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    cerebras_key = os.environ.get("CEREBRAS_API_KEY", "").strip()
    cerebras_model = os.environ.get("CEREBRAS_MODEL", "llama-3.3-70b")

    # ── Sonnet gate (max 1% of tokens when explicitly enabled) ──────────────
    if task_lower in SONNET_GATED_TASKS:
        if _allow_sonnet() and claude_key:
            # Sonnet is open — but enforce share cap before committing
            model = normalize_anthropic_model(
                os.environ.get("ANTHROPIC_MODEL"),
                default=ANTHROPIC_SONNET_MODEL,
            )
            _enf = _get_share_enforcer()
            if _enf and not _enf.allow(provider="anthropic", model=model):
                # Share cap hit → downgrade to Haiku silently
                logger.warning(
                    "LLM routing: task=%s → Sonnet share cap hit; downgrading to Haiku", task_type
                )
            else:
                logger.debug("LLM routing: task=%s → sonnet/%s (premium gate open)", task_type, model)
                return LLMConfig(provider="anthropic", api_key=claude_key, model=model)
        # Sonnet locked or key absent → Haiku is the explicit fallback for premium tasks
        if claude_key:
            model = normalize_anthropic_model(
                os.environ.get("ANTHROPIC_MODEL"),
                default=ANTHROPIC_HAIKU_MODEL,
            )
            logger.info(
                "LLM routing: task=%s — Sonnet locked (ALLOW_SONNET=false); "
                "using Haiku/%s as premium fallback", task_type, model
            )
            return LLMConfig(provider="anthropic", api_key=claude_key, model=model)
        # Anthropic key absent → Cerebras reasoning as last resort
        if cerebras_key:
            logger.warning(
                "LLM routing: task=%s — Sonnet locked and no Anthropic key; "
                "using Cerebras/%s as last-resort fallback", task_type, cerebras_model
            )
            return LLMConfig(provider="cerebras", api_key=cerebras_key, model=cerebras_model)
        return None

    # ── Worker agents — Cerebras ONLY ────────────────────────────────────────
    if task_lower in WORKER_AGENT_TASKS:
        if cerebras_key:
            logger.debug("LLM routing: task=%s → cerebras/%s (worker-only)", task_type, cerebras_model)
            return LLMConfig(
                provider="cerebras", api_key=cerebras_key,
                model=cerebras_model, cerebras_only=True,
            )
        # No Cerebras key + worker agent = fatal config error, not silent Anthropic fallback
        logger.error(
            "task=%s requires Cerebras but CEREBRAS_API_KEY is not set. "
            "Worker agents must not use Anthropic.", task_type
        )
        return None

    # ── Haiku primary: reasoning/validation/proof-gate capabilities ───────────
    if task_lower in HAIKU_PRIMARY_TASKS:
        if claude_key:
            model = normalize_anthropic_model(
                os.environ.get("ANTHROPIC_MODEL"),
                default=ANTHROPIC_HAIKU_MODEL,
            )
            logger.debug("LLM routing: task=%s → haiku/%s (reasoning gate)", task_type, model)
            return LLMConfig(provider="anthropic", api_key=claude_key, model=model)
        # Anthropic unavailable → fall back to Cerebras (never blocks agents)
        if cerebras_key:
            logger.warning(
                "LLM routing: task=%s needs Haiku but Anthropic key absent; "
                "falling back to Cerebras/%s", task_type, cerebras_model
            )
            return LLMConfig(provider="cerebras", api_key=cerebras_key, model=cerebras_model)
        logger.error("No LLM keys available for task=%s", task_type)
        return None

    # ── Cerebras primary: all volume/mechanical tasks + unknown task types ────
    if cerebras_key:
        logger.debug("LLM routing: task=%s → cerebras/%s (volume engine)", task_type or "default", cerebras_model)
        return LLMConfig(provider="cerebras", api_key=cerebras_key, model=cerebras_model)

    # ── Final fallback: Haiku if Cerebras key missing ─────────────────────────
    if claude_key:
        model = normalize_anthropic_model(
            os.environ.get("ANTHROPIC_MODEL"),
            default=ANTHROPIC_HAIKU_MODEL,
        )
        logger.warning(
            "LLM routing: task=%s — no Cerebras key; falling back to haiku/%s",
            task_type or "default", model
        )
        return LLMConfig(provider="anthropic", api_key=claude_key, model=model)

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
            result_text = await call_claude(system_prompt, user_prompt, config)
        elif config.provider == "cerebras":
            result_text = await call_cerebras(system_prompt, user_prompt, config)
        else:
            logger.error("Unknown LLM provider: %s", config.provider)
            return None
        # Record usage for model-share enforcement
        if result_text:
            _enf = _get_share_enforcer()
            if _enf:
                _estimated_tokens = (len(system_prompt) + len(user_prompt) + len(result_text)) // 4
                _enf.record(provider=config.provider, model=config.model, tokens=_estimated_tokens)
        return result_text

    except Exception as e:
        logger.exception("LLM call failed: %s", e)
        # Auto-fallback: never let provider failure stop agents.
        cerebras_key = os.environ.get("CEREBRAS_API_KEY", "").strip()
        claude_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        cerebras_model = os.environ.get("CEREBRAS_MODEL", "llama-3.3-70b")
        if config.provider == "cerebras" and not getattr(config, "cerebras_only", False):
            # Cerebras failed → try Haiku
            if claude_key:
                logger.warning("Cerebras failed for task=%s, falling back to Haiku", task_type)
                fallback = LLMConfig(
                    provider="anthropic",
                    api_key=claude_key,
                    model=normalize_anthropic_model(None, default=ANTHROPIC_HAIKU_MODEL),
                    temperature=temperature,
                )
                return await call_claude(system_prompt, user_prompt, fallback)
        elif config.provider == "anthropic":
            # Anthropic failed → try Cerebras reasoning (keeps agents alive)
            if cerebras_key:
                logger.warning("Anthropic failed for task=%s, falling back to Cerebras", task_type)
                fallback = LLMConfig(
                    provider="cerebras",
                    api_key=cerebras_key,
                    model=cerebras_model,
                    temperature=temperature,
                )
                return await call_cerebras(system_prompt, user_prompt, fallback)
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
    """Call LLM to generate code — routes via capability-based get_llm_config."""
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
    """Call LLM to generate structured JSON output — routes via capability-based get_llm_config."""
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


# ─── call_llm_simple ─────────────────────────────────────────────────────────
async def call_llm_simple(prompt: str, *, task_type: str = "simple_chat") -> str:
    """
    Convenience wrapper: single user-turn call routed by task_type.

    Returns the response text (empty string on failure).
    Used by RepairEngine and other services that don't need full
    system/user separation.
    """
    result = await call_llm(
        system_prompt="You are a helpful assistant.",
        user_prompt=prompt,
        task_type=task_type,
        temperature=0.3,
    )
    return result or ""


# ─── Sonnet compressed proof packet ──────────────────────────────────────────

def build_sonnet_proof_packet(
    *,
    goal: str,
    plan_summary: str,
    file_manifest: List[str],
    validator_results: List[Dict[str, Any]],
    critical_excerpts: List[str],
    unresolved_risks: List[str],
    max_chars: int = 12_000,
) -> str:
    """
    Build a compressed proof packet for Sonnet consumption.

    Sonnet must NEVER receive raw chat history or swarm chatter.
    Instead it receives this compressed packet containing only the
    information it needs to adjudicate the final proof gate.

    The packet is kept under *max_chars* so Sonnet stays within
    SONNET_MAX_TOKENS_PER_RUN (default 15 000 tokens ≈ 60 000 chars).

    Returns a structured XML-like string the Sonnet system prompt
    can reference without ambiguity.
    """
    # Summarise validator results
    vr_lines: List[str] = []
    for vr in validator_results:
        status = "PASS" if vr.get("passed") else "FAIL"
        name   = vr.get("name") or vr.get("check") or "unknown"
        detail = vr.get("detail") or vr.get("message") or ""
        vr_lines.append(f"  [{status}] {name}: {detail[:200]}")

    # Trim collections to budget
    excerpts_block = "\n---\n".join(critical_excerpts)[:3000]
    risks_block    = "\n".join(f"  - {r}" for r in unresolved_risks[:20])
    files_block    = "\n".join(f"  {f}" for f in file_manifest[:100])

    packet = f"""<proof_packet>
<goal>{goal[:500]}</goal>

<plan_summary>
{plan_summary[:1500]}
</plan_summary>

<file_manifest>
{files_block}
</file_manifest>

<validator_results>
{chr(10).join(vr_lines)}
</validator_results>

<critical_excerpts>
{excerpts_block}
</critical_excerpts>

<unresolved_risks>
{risks_block}
</unresolved_risks>
</proof_packet>"""

    # Hard truncate if still over budget
    if len(packet) > max_chars:
        packet = packet[:max_chars] + "\n<!-- packet truncated to budget -->"

    logger.debug("build_sonnet_proof_packet: %d chars", len(packet))
    return packet
