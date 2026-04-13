"""
CrucibAI LLM Router: Intelligent Routing System
================================================
Routes requests to Cerebras, Haiku, or Sonnet based on:
- Task complexity (simple vs complex)
- User tier (free, builder, pro, scale, teams)
- Speed selector (lite, pro, max)
- Credit availability

Free tier:    Cerebras (default llama3.1-8b; override CEREBRAS_MODEL)
Paid lite:    Cerebras (same)
Paid pro/max: Claude Haiku (paid quality)
Critical/complex (paid pro+): Claude Sonnet (highest quality)
"""

import logging
import os
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from anthropic_models import ANTHROPIC_HAIKU_MODEL, ANTHROPIC_SONNET_MODEL

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
CEREBRAS_MODEL = (os.environ.get("CEREBRAS_MODEL") or "llama3.1-8b").strip()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
HAIKU_MODEL = ANTHROPIC_HAIKU_MODEL
SONNET_MODEL = ANTHROPIC_SONNET_MODEL


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

    Routing tiers:
      Free        → Cerebras llama-3.3-70b (fast, high-quality 70B model)
      Builder     → lite: Cerebras; pro: Haiku
      Pro/Scale   → lite: Cerebras; pro: Haiku; max: Sonnet
      Teams       → lite: Cerebras; pro: Haiku; max: Sonnet
      Critical    → always Sonnet for paid, Cerebras for free
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
    ) -> list:
        """
        Get the LLM model chain for a task.

        Args:
            task_complexity: SIMPLE, MODERATE, COMPLEX, CRITICAL
            user_tier: free, builder, pro, scale, teams
            speed_selector: lite, pro, max
            available_credits: User's available credits

        Returns:
            List of models to try in order: [primary, fallback1, fallback2]
        """

        chain = []
        is_paid = user_tier in ("builder", "pro", "scale", "teams")
        is_pro_plus = user_tier in ("pro", "scale", "teams")

        # TIER-BASED ROUTING
        if user_tier == "free":
            # Free tier: Cerebras llama-3.3-70b (free, 70B quality) → Haiku fallback
            chain = ["cerebras", "haiku"]

        elif user_tier == "builder":
            if speed_selector == "lite":
                chain = ["cerebras", "haiku"]
            else:  # pro
                chain = ["haiku", "cerebras"]

        elif is_pro_plus:
            if speed_selector == "lite":
                chain = ["cerebras", "haiku"]
            elif speed_selector == "pro":
                chain = ["haiku", "cerebras"]
            else:  # max — use Sonnet for best quality
                chain = ["sonnet", "haiku", "cerebras"]

        # COMPLEXITY-BASED OVERRIDE for paid users
        if task_complexity == TaskComplexity.CRITICAL and is_paid:
            # Critical tasks on paid plans: use Sonnet if on pro+, Haiku otherwise
            if is_pro_plus and "sonnet" not in chain:
                chain.insert(0, "sonnet")
            elif "haiku" not in chain:
                chain.insert(0, "haiku")

        elif task_complexity == TaskComplexity.SIMPLE:
            # Simple tasks: always prefer Cerebras (fast, cheap)
            if chain and chain[0] != "cerebras":
                if "cerebras" in chain:
                    chain.remove("cerebras")
                chain.insert(0, "cerebras")

        # CREDIT-BASED OVERRIDE
        if available_credits < 10:
            # Low credits: deprioritize Sonnet and Haiku
            for model in ("sonnet", "haiku"):
                if model in chain:
                    chain.remove(model)
                    chain.append(model)

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

        # Fallback: if no models available, return empty (will error)
        if not final_chain:
            logger.error("No LLM models available")

        return final_chain

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
