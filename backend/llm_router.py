"""Compatibility facade for the single CrucibAI routing policy.

The routing rules live in backend.llm_client. This module keeps older imports
working while preventing a second model policy from drifting out of sync.
"""

from __future__ import annotations

import logging
import os
from enum import Enum
from typing import Any, Dict, List, Tuple

from .anthropic_models import ANTHROPIC_HAIKU_MODEL, ANTHROPIC_SONNET_MODEL
from .llm_client import (
    ALLOW_SONNET,
    CEREBRAS_MODEL,
    HAIKU_MODEL,
    SONNET_ALLOWED_TASKS,
    SONNET_MODEL,
    get_cerebras_key,
    get_route_labels,
)

logger = logging.getLogger(__name__)

LLAMA_API_KEY = os.environ.get("LLAMA_API_KEY", "").strip()
LLAMA_MODEL = "meta-llama/Llama-3-70b-chat-hf"
LLAMA_PROVIDER = "together"

CEREBRAS_API_KEY = os.environ.get("CEREBRAS_API_KEY", "").strip()
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
HAIKU_MODEL = HAIKU_MODEL or ANTHROPIC_HAIKU_MODEL
SONNET_MODEL = SONNET_MODEL or ANTHROPIC_SONNET_MODEL


class TaskComplexity(str, Enum):
    """Task complexity labels kept for legacy callers."""

    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    CRITICAL = "critical"


class TaskClassifier:
    """Small classifier used only to pick a policy task label."""

    COMPLEX_KEYWORDS = {
        "architecture",
        "authentication",
        "database",
        "debugging",
        "failure",
        "logic",
        "migration",
        "optimization",
        "performance",
        "reasoning",
        "recovery",
        "security",
        "validation",
        "verification",
    }

    SIMPLE_KEYWORDS = {
        "add line",
        "change text",
        "color",
        "comment",
        "edit",
        "fix typo",
        "format",
        "rename",
        "spacing",
        "style",
        "typo",
        "update",
    }

    CRITICAL_AGENTS = {
        "code review agent",
        "deployment agent",
        "schema validation agent",
        "security checker",
        "validation agent",
    }

    @staticmethod
    def classify(request: str, agent_name: str = "") -> TaskComplexity:
        request_lower = (request or "").lower()
        agent_lower = (agent_name or "").lower()

        if any(agent in agent_lower for agent in TaskClassifier.CRITICAL_AGENTS):
            return TaskComplexity.CRITICAL
        if any(keyword in request_lower for keyword in TaskClassifier.COMPLEX_KEYWORDS):
            return TaskComplexity.COMPLEX
        if any(keyword in request_lower for keyword in TaskClassifier.SIMPLE_KEYWORDS):
            return TaskComplexity.SIMPLE
        return TaskComplexity.MODERATE


def _policy_task_for_complexity(
    task_complexity: TaskComplexity,
    *,
    user_tier: str,
    speed_selector: str,
) -> str:
    if task_complexity == TaskComplexity.CRITICAL:
        premium = (
            ALLOW_SONNET
            and user_tier in {"pro", "scale", "teams"}
            and speed_selector == "max"
        )
        return "premium_final_proof" if premium else "standard_final_proof"
    if task_complexity == TaskComplexity.COMPLEX:
        # Complex build work still uses Cerebras volume unless a caller names a
        # proof/planning/security capability directly.
        return "code_generation"
    return "code_generation"


class LLMRouter:
    """Legacy class wrapper around backend.llm_client routing."""

    def __init__(self):
        self.llama_available = bool(LLAMA_API_KEY)
        self.cerebras_available = bool(CEREBRAS_API_KEY)
        self.haiku_available = bool(ANTHROPIC_API_KEY)
        self.sonnet_available = bool(ANTHROPIC_API_KEY and ALLOW_SONNET)

    def get_model_chain(
        self,
        task_complexity: TaskComplexity,
        user_tier: str = "free",
        speed_selector: str = "lite",
        available_credits: int = 0,
    ) -> List[Tuple[str, str, str]]:
        task_type = _policy_task_for_complexity(
            task_complexity,
            user_tier=user_tier,
            speed_selector=speed_selector,
        )
        chain: List[Tuple[str, str, str]] = []
        for label in get_route_labels(task_type):
            if label == "cerebras" and self.cerebras_available:
                chain.append(("cerebras", CEREBRAS_MODEL, "cerebras"))
            elif label == "haiku" and self.haiku_available:
                chain.append(("haiku", HAIKU_MODEL, "anthropic"))
            elif label == "sonnet" and self.sonnet_available and task_type in SONNET_ALLOWED_TASKS:
                chain.append(("sonnet", SONNET_MODEL, "anthropic"))

        if not chain:
            logger.error("No LLM models available")
        return chain

    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        info = {
            "cerebras": {
                "name": f"Cerebras {CEREBRAS_MODEL}",
                "cost_per_1m_tokens": 0.27,
                "speed": "very_fast",
                "quality": 8.5,
                "provider": "cerebras",
            },
            "haiku": {
                "name": "Claude Haiku",
                "cost_per_1m_tokens": 1.0,
                "speed": "medium",
                "quality": 9.0,
                "provider": "anthropic",
            },
            "sonnet": {
                "name": "Claude Sonnet",
                "cost_per_1m_tokens": 3.0,
                "speed": "medium",
                "quality": 9.8,
                "provider": "anthropic",
            },
        }
        return info.get(model_name, {})


router = LLMRouter()
classifier = TaskClassifier()
