from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Set

AGENT_STATUS_PENDING = "pending"
AGENT_STATUS_RUNNING = "running"
AGENT_STATUS_COMPLETED = "completed"
AGENT_STATUS_FAILED = "failed"
AGENT_STATUS_FAILED_WITH_FALLBACK = "failed_with_fallback"
AGENT_STATUS_SKIPPED = "skipped"

TERMINAL_AGENT_STATES = {
    AGENT_STATUS_COMPLETED,
    AGENT_STATUS_FAILED,
    AGENT_STATUS_FAILED_WITH_FALLBACK,
    AGENT_STATUS_SKIPPED,
}

_ALLOWED_TRANSITIONS: Dict[str, Set[str]] = {
    AGENT_STATUS_PENDING: {AGENT_STATUS_RUNNING, AGENT_STATUS_SKIPPED, AGENT_STATUS_FAILED},
    AGENT_STATUS_RUNNING: {
        AGENT_STATUS_COMPLETED,
        AGENT_STATUS_FAILED,
        AGENT_STATUS_FAILED_WITH_FALLBACK,
        AGENT_STATUS_SKIPPED,
    },
    AGENT_STATUS_COMPLETED: set(),
    AGENT_STATUS_FAILED: {AGENT_STATUS_PENDING, AGENT_STATUS_RUNNING},
    AGENT_STATUS_FAILED_WITH_FALLBACK: set(),
    AGENT_STATUS_SKIPPED: set(),
}


@dataclass(frozen=True)
class AgentTransitionResult:
    current_status: str
    next_status: str
    allowed: bool
    reason: Optional[str] = None


def normalize_agent_status(status: Optional[str]) -> str:
    raw = (status or AGENT_STATUS_PENDING).strip().lower()
    aliases = {
        "queued": AGENT_STATUS_PENDING,
        "processing": AGENT_STATUS_RUNNING,
        "complete": AGENT_STATUS_COMPLETED,
        "done": AGENT_STATUS_COMPLETED,
        "ok": AGENT_STATUS_COMPLETED,
        "success": AGENT_STATUS_COMPLETED,
        "fallback": AGENT_STATUS_FAILED_WITH_FALLBACK,
    }
    return aliases.get(raw, raw)


def allowed_next_agent_statuses(status: Optional[str]) -> Iterable[str]:
    normalized = normalize_agent_status(status)
    return sorted(_ALLOWED_TRANSITIONS.get(normalized, set()))


def validate_agent_transition(current_status: Optional[str], next_status: Optional[str]) -> AgentTransitionResult:
    current = normalize_agent_status(current_status)
    nxt = normalize_agent_status(next_status)
    if current == nxt:
        return AgentTransitionResult(current_status=current, next_status=nxt, allowed=True, reason="no-op")
    allowed = nxt in _ALLOWED_TRANSITIONS.get(current, set())
    return AgentTransitionResult(
        current_status=current,
        next_status=nxt,
        allowed=allowed,
        reason=None if allowed else f"{current} -> {nxt} is not allowed",
    )


def assert_agent_transition(current_status: Optional[str], next_status: Optional[str]) -> None:
    result = validate_agent_transition(current_status, next_status)
    if not result.allowed:
        raise ValueError(result.reason or "invalid agent state transition")
