"""
CrucibAI Agents & Automation: user-defined agents that run on schedule or webhook.
Executor, worker, and models for agent_runs and user_agents.
"""
from .models import (
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    TriggerConfig,
    ActionConfig,
    RunResponse,
)
from .constants import (
    CREDITS_PER_AGENT_RUN,
    MAX_CONCURRENT_RUNS_PER_USER,
    MAX_RUNS_PER_HOUR_PER_USER,
    AGENT_RUN_TIMEOUT_SECONDS,
    WEBHOOK_IDEMPOTENCY_SECONDS,
    WEBHOOK_RATE_LIMIT_PER_MINUTE,
)

__all__ = [
    "AgentCreate",
    "AgentUpdate",
    "AgentResponse",
    "TriggerConfig",
    "ActionConfig",
    "RunResponse",
    "CREDITS_PER_AGENT_RUN",
    "MAX_CONCURRENT_RUNS_PER_USER",
    "MAX_RUNS_PER_HOUR_PER_USER",
    "AGENT_RUN_TIMEOUT_SECONDS",
    "WEBHOOK_IDEMPOTENCY_SECONDS",
    "WEBHOOK_RATE_LIMIT_PER_MINUTE",
]
