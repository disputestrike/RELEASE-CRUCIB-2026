from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Set

RUN_STATUS_PENDING = "pending"
RUN_STATUS_PLANNING = "planning"
RUN_STATUS_RUNNING = "running"
RUN_STATUS_RETRYING = "retrying"
RUN_STATUS_COMPLETED = "completed"
RUN_STATUS_FAILED = "failed"
RUN_STATUS_CANCELLED = "cancelled"
RUN_STATUS_PAUSED = "paused"

TERMINAL_RUN_STATES = {RUN_STATUS_COMPLETED, RUN_STATUS_FAILED, RUN_STATUS_CANCELLED}

_ALLOWED_TRANSITIONS: Dict[str, Set[str]] = {
    RUN_STATUS_PENDING: {RUN_STATUS_PLANNING, RUN_STATUS_RUNNING, RUN_STATUS_CANCELLED},
    RUN_STATUS_PLANNING: {RUN_STATUS_RUNNING, RUN_STATUS_FAILED, RUN_STATUS_CANCELLED},
    RUN_STATUS_RUNNING: {RUN_STATUS_RETRYING, RUN_STATUS_COMPLETED, RUN_STATUS_FAILED, RUN_STATUS_CANCELLED, RUN_STATUS_PAUSED},
    RUN_STATUS_RETRYING: {RUN_STATUS_RUNNING, RUN_STATUS_FAILED, RUN_STATUS_CANCELLED},
    RUN_STATUS_PAUSED: {RUN_STATUS_RUNNING, RUN_STATUS_CANCELLED},
    RUN_STATUS_FAILED: {RUN_STATUS_RETRYING, RUN_STATUS_CANCELLED},
    RUN_STATUS_COMPLETED: set(),
    RUN_STATUS_CANCELLED: set(),
}


@dataclass(frozen=True)
class RunTransitionResult:
    current_status: str
    next_status: str
    allowed: bool
    reason: Optional[str] = None



def allowed_next_statuses(status: Optional[str]) -> Iterable[str]:
    status = normalize_run_status(status)
    return sorted(_ALLOWED_TRANSITIONS.get(status, set()))



def normalize_run_status(status: Optional[str]) -> str:
    raw = (status or RUN_STATUS_PENDING).strip().lower()
    aliases = {
        "queued": RUN_STATUS_PENDING,
        "created": RUN_STATUS_PENDING,
        "plan": RUN_STATUS_PLANNING,
        "in_progress": RUN_STATUS_RUNNING,
        "processing": RUN_STATUS_RUNNING,
        "retry": RUN_STATUS_RETRYING,
        "done": RUN_STATUS_COMPLETED,
        "error": RUN_STATUS_FAILED,
        "stopped": RUN_STATUS_CANCELLED,
    }
    return aliases.get(raw, raw)



def validate_run_transition(current_status: Optional[str], next_status: Optional[str]) -> RunTransitionResult:
    current = normalize_run_status(current_status)
    nxt = normalize_run_status(next_status)
    if current == nxt:
        return RunTransitionResult(current_status=current, next_status=nxt, allowed=True, reason="no-op")
    allowed = nxt in _ALLOWED_TRANSITIONS.get(current, set())
    return RunTransitionResult(
        current_status=current,
        next_status=nxt,
        allowed=allowed,
        reason=None if allowed else f"{current} -> {nxt} is not allowed",
    )



def assert_run_transition(current_status: Optional[str], next_status: Optional[str]) -> None:
    result = validate_run_transition(current_status, next_status)
    if not result.allowed:
        raise ValueError(result.reason or "invalid run state transition")
