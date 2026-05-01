"""Capability-based model router.

Work division:
  Cerebras (70-80% tokens): mechanical execution — code gen, scaffolding,
    worker agents, drafting, summaries, repair patching, boilerplate.
  Haiku (20-30% tokens): reasoning/validation authority — build plans,
    architecture, repair diagnosis, proof gates, build integrity.
  Sonnet (0% default, max 1%): locked behind ALLOW_SONNET=true.

Cerebras keys are round-robined (CEREBRAS_API_KEY + CEREBRAS_API_KEY_1..5)
to distribute load across up to 5 keys and avoid rate limits.
"""

import logging
import os
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from .anthropic_models import ANTHROPIC_HAIKU_MODEL, ANTHROPIC_SONNET_MODEL
from .services.providers import choose_chain, selection_meta

logger = logging.getLogger(__name__)

# LLM Configuration
LLAMA_API_KEY = os.environ.get("LLAMA_API_KEY", "").strip()
LLAMA_MODEL = "meta-llama/Llama-3-70b-chat-hf"
LLAMA_PROVIDER = "together"  # Using Together AI for hosted Llama

# Cerebras key pool — round-robin across up to 5 keys for 5x rate limit
import itertools as _itertools


def _load_cerebras_keys() -> list:
    """Load all CEREBRAS_API_KEY_1..5 and CEREBRAS_API_KEY, return non-empty list."""
    keys = []
    # Primary env var
    k = os.environ.get("CEREBRAS_API_KEY", "").strip()
    if k:
        keys.append(k)
    # Pool keys 1-5
    for i in range(1, 6):
        k = os.environ.get(f"CEREBRAS_API_KEY_{i}", "").strip()
        if k and k not in keys:
            keys.append(k)
    return keys


_CEREBRAS_KEYS = _load_cerebras_keys()
_cerebras_key_cycle = _itertools.cycle(_CEREBRAS_KEYS) if _CEREBRAS_KEYS else None


def get_cerebras_key() -> str:
    """Return next Cerebras key in round-robin rotation."""
    if not _cerebras_key_cycle:
        return ""
    return next(_cerebras_key_cycle)


# Backwards compat — single key reference (first key or empty)
CEREBRAS_API_KEY = _CEREBRAS_KEYS[0] if _CEREBRAS_KEYS else ""
# Cerebras model id (API changes retired llama-3.3-70b). Set CEREBRAS_MODEL on Railway.
CEREBRAS_MODEL = (os.environ.get("CEREBRAS_MODEL") or "llama-3.3-70b").strip()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
HAIKU_MODEL = ANTHROPIC_HAIKU_MODEL
SONNET_MODEL = ANTHROPIC_SONNET_MODEL
ALLOW_SONNET = os.environ.get("ALLOW_SONNET", "false").strip().lower() in {"1", "true", "yes"}
# Sonnet token share caps — enforced in model-share observability layer.
# Sonnet must not exceed 1% of total platform token share.
SONNET_MAX_PLATFORM_TOKEN_SHARE = float(os.environ.get("SONNET_MAX_PLATFORM_TOKEN_SHARE", "0.01"))
# Per-run token cap for Sonnet: receive compressed proof packet only (10k-25k tokens).
SONNET_MAX_TOKENS_PER_RUN = int(os.environ.get("SONNET_MAX_TOKENS_PER_RUN", "15000"))
# Haiku over-threshold warning (logs warning if Haiku exceeds 35% of job/user token share)
HAIKU_MAX_TOKEN_SHARE_WARN = float(os.environ.get("HAIKU_MAX_TOKEN_SHARE_WARN", "0.35"))
# Cerebras under-threshold alert (alert if Cerebras drops below 60% on normal workloads)
CEREBRAS_MIN_TOKEN_SHARE_ALERT = float(os.environ.get("CEREBRAS_MIN_TOKEN_SHARE_ALERT", "0.60"))


class TaskComplexity(str, Enum):
    """Task complexity classification"""

    SIMPLE = "simple"  # Quick formatting, simple transforms
    MODERATE = "moderate"  # Standard code generation
    COMPLEX = "complex"  # Architecture, logic, security
    CRITICAL = "critical"  # High-stakes decisions


class TaskClassifier:
    """
    Classifies incoming tasks by complexity.
    Used to route to appropriate LLM.
    """

    COMPLEX_KEYWORDS = {
        "architecture",
        "design",
        "security",
        "authentication",
        "database",
        "schema",
        "migration",
        "performance",
        "optimization",
        "refactor",
        "bug fix",
        "debugging",
        "error",
        "failure",
        "recovery",
        "algorithm",
        "logic",
        "reasoning",
        "decision",
    }

    SIMPLE_KEYWORDS = {
        "format",
        "rename",
        "reorder",
        "style",
        "color",
        "spacing",
        "typo",
        "fix typo",
        "change text",
        "update",
        "edit",
        "add line",
        "remove line",
        "comment",
        "uncomment",
    }

    @staticmethod
    def classify(request: str, agent_name: str = "") -> TaskComplexity:
        """
        Classify task complexity from request text.

        Returns:
            TaskComplexity enum (SIMPLE, MODERATE, COMPLEX, CRITICAL)
        """
        request_lower = request.lower()
        agent_lower = agent_name.lower()

        # Check for critical agents
        critical_agents = {
            "security checker",
            "deployment agent",
            "database agent",
            "backend generation",
            "auth setup agent",
        }
        if any(agent in agent_lower for agent in critical_agents):
            return TaskComplexity.CRITICAL

        # Check for complex keywords
        if any(keyword in request_lower for keyword in TaskClassifier.COMPLEX_KEYWORDS):
            return TaskComplexity.COMPLEX

        # Check for simple keywords
        if any(keyword in request_lower for keyword in TaskClassifier.SIMPLE_KEYWORDS):
            return TaskComplexity.SIMPLE

        # Default: moderate
        return TaskComplexity.MODERATE


class LLMRouter:
    """
    Intelligent LLM router that selects the best model based on:
    - Task complexity
    - User tier
    - Speed selector
    - Credit availability

    Routing policy:
      - Volume/default work: Cerebras first, Haiku fallback.
      - Reasoning/validation heavy work: Haiku first, Cerebras fallback.
      - Sonnet: disabled by default, premium-gated only.
    """

    def __init__(self):
        self.llama_available = bool(LLAMA_API_KEY)
        self.cerebras_available = bool(CEREBRAS_API_KEY)
        self.haiku_available = bool(ANTHROPIC_API_KEY)
        self.sonnet_available = bool(ANTHROPIC_API_KEY)

    def get_model_chain(
        self,
        task_complexity: TaskComplexity,
        user_tier: str = "free",
        speed_selector: str = "lite",
        available_credits: int = 0,
        capability: str = "",
    ) -> list:
        """
        Get the LLM model chain for a task.

        Capability-based routing — work division:
          Cerebras (70-80% tokens): mechanical execution — code gen, scaffolding,
            worker agents, drafting, summaries, repair patching, boilerplate.
          Haiku (20-30% tokens): reasoning/validation — build plans, architecture,
            repair diagnosis, proof gates, build integrity, should_escalate.
          Sonnet (0% default, max 1%): locked premium only when ALLOW_SONNET=true.

        Worker agents always route to Cerebras only — never Anthropic, never Sonnet.

        Args:
            task_complexity: SIMPLE, MODERATE, COMPLEX, CRITICAL
            user_tier: free, builder, pro, scale, teams
            speed_selector: lite, pro, max
            available_credits: User's available credits
            capability: optional task capability hint (e.g. "build_plan", "code_generate")

        Returns:
            List of (name, model, provider) tuples in fallback order.
        """
        # Import capability tables from llm_client for a single source of truth.
        try:
            from .llm_client import (
                CEREBRAS_PRIMARY_TASKS,
                HAIKU_PRIMARY_TASKS,
                SONNET_GATED_TASKS,
                WORKER_AGENT_TASKS,
            )
        except ImportError:
            CEREBRAS_PRIMARY_TASKS = set()
            HAIKU_PRIMARY_TASKS = set()
            SONNET_GATED_TASKS = set()
            WORKER_AGENT_TASKS = set()

        cap_lower = (capability or "").lower().strip()
        is_pro_plus = user_tier in ("pro", "scale", "teams")
        is_paid = user_tier in ("builder", "pro", "scale", "teams")

        # ── Worker agents: Cerebras ONLY ──────────────────────────────────────
        if cap_lower in WORKER_AGENT_TASKS:
            chain = ["cerebras"]

        # ── Sonnet gate (locked, premium-only) ────────────────────────────────
        elif (
            cap_lower in SONNET_GATED_TASKS
            and ALLOW_SONNET
            and is_pro_plus
            and speed_selector == "max"
        ):
            chain = ["sonnet", "haiku", "cerebras"]

        # ── Haiku primary: reasoning/validation capabilities ──────────────────
        elif cap_lower in HAIKU_PRIMARY_TASKS or task_complexity == TaskComplexity.CRITICAL:
            chain = ["haiku", "cerebras"]

        # ── Cerebras primary: all volume/mechanical/default tasks ─────────────
        else:
            chain = ["cerebras", "haiku"]

        # AVAILABILITY CHECK
        final_chain = []
        for model in chain:
            if model == "llama" and self.llama_available:
                final_chain.append(("llama", LLAMA_MODEL, LLAMA_PROVIDER))
            elif model == "cerebras" and self.cerebras_available:
                final_chain.append(("cerebras", CEREBRAS_MODEL, "cerebras"))
            elif model == "haiku" and self.haiku_available:
                final_chain.append(("haiku", HAIKU_MODEL, "anthropic"))
            elif model == "sonnet" and self.sonnet_available:
                final_chain.append(("sonnet", SONNET_MODEL, "anthropic"))

        if not final_chain:
            logger.error(
                "No LLM models available for capability=%s complexity=%s",
                capability, task_complexity
            )

        # Optional provider-registry ordering
        chain_with_registry = choose_chain(
            final_chain,
            need_tools=task_complexity in (TaskComplexity.COMPLEX, TaskComplexity.CRITICAL),
            need_vision=False,
        )
        meta = selection_meta()
        logger.debug(
            "Model chain: capability=%s complexity=%s chain=%s registry_mode=%s",
            capability, task_complexity,
            [c[0] for c in chain_with_registry],
            meta.get("mode"),
        )
        return chain_with_registry

    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get cost and performance info for a model."""
        info = {
            "llama": {
                "name": "Llama 3 70B",
                "cost_per_1m_tokens": 0.0,  # Free (open-source via Together)
                "speed": "medium",
                "quality": 8.5,
                "provider": "together",
            },
            "cerebras": {
                "name": f"Cerebras {CEREBRAS_MODEL}",
                "cost_per_1m_tokens": 0.27,
                "speed": "very_fast",
                "quality": 8.5,
                "provider": "cerebras",
            },
            "haiku": {
                "name": "Claude Haiku 4.5",
                "cost_per_1m_tokens": 1.0,
                "speed": "medium",
                "quality": 9.0,
                "provider": "anthropic",
            },
            "sonnet": {
                "name": "Claude Sonnet 4.6",
                "cost_per_1m_tokens": 3.0,
                "speed": "medium",
                "quality": 9.8,
                "provider": "anthropic",
            },
        }
        return info.get(model_name, {})


# Singleton instance
router = LLMRouter()
classifier = TaskClassifier()
