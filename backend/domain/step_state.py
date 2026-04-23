from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Set

STEP_STATUS_PENDING = "pending"
STEP_STATUS_RUNNING = "running"
STEP_STATUS_VERIFYING = "verifying"
STEP_STATUS_RETRYING = "retrying"
STEP_STATUS_FAILED = "failed"
STEP_STATUS_COMPLETED = "completed"
STEP_STATUS_BLOCKED = "blocked"
STEP_STATUS_SKIPPED = "skipped"

TERMINAL_STEP_STATES = {
    STEP_STATUS_COMPLETED,
    STEP_STATUS_FAILED,
    STEP_STATUS_SKIPPED,
}

_ALLOWED_TRANSITIONS: Dict[str, Set[str]] = {
    STEP_STATUS_PENDING: {
        STEP_STATUS_RUNNING,
        STEP_STATUS_BLOCKED,
        STEP_STATUS_SKIPPED,
        STEP_STATUS_FAILED,
    },
    STEP_STATUS_RUNNING: {
        STEP_STATUS_VERIFYING,
        STEP_STATUS_RETRYING,
        STEP_STATUS_COMPLETED,
        STEP_STATUS_FAILED,
        STEP_STATUS_BLOCKED,
        STEP_STATUS_SKIPPED,
    },
    STEP_STATUS_VERIFYING: {
        STEP_STATUS_COMPLETED,
        STEP_STATUS_FAILED,
        STEP_STATUS_RETRYING,
        STEP_STATUS_BLOCKED,
    },
    STEP_STATUS_RETRYING: {
        STEP_STATUS_PENDING,
        STEP_STATUS_RUNNING,
        STEP_STATUS_FAILED,
        STEP_STATUS_BLOCKED,
    },
    STEP_STATUS_FAILED: {
        STEP_STATUS_PENDING,
        STEP_STATUS_RETRYING,
        STEP_STATUS_BLOCKED,
    },
    STEP_STATUS_BLOCKED: {
        STEP_STATUS_PENDING,
        STEP_STATUS_RETRYING,
        STEP_STATUS_SKIPPED,
    },
    STEP_STATUS_COMPLETED: set(),
    STEP_STATUS_SKIPPED: set(),
}


@dataclass(frozen=True)
class StepTransitionResult:
    current_status: str
    next_status: str
    allowed: bool
    reason: Optional[str] = None



def normalize_step_status(status: Optional[str]) -> str:
    raw = (status or STEP_STATUS_PENDING).strip().lower()
    aliases = {
        "queued": STEP_STATUS_PENDING,
        "planned": STEP_STATUS_PENDING,
        "processing": STEP_STATUS_RUNNING,
        "in_progress": STEP_STATUS_RUNNING,
        "verify": STEP_STATUS_VERIFYING,
        "retry": STEP_STATUS_RETRYING,
        "complete": STEP_STATUS_COMPLETED,
        "done": STEP_STATUS_COMPLETED,
        "ok": STEP_STATUS_COMPLETED,
        "success": STEP_STATUS_COMPLETED,
        "error": STEP_STATUS_FAILED,
    }
    return aliases.get(raw, raw)



def allowed_next_step_statuses(status: Optional[str]) -> Iterable[str]:
    normalized = normalize_step_status(status)
    return sorted(_ALLOWED_TRANSITIONS.get(normalized, set()))



def validate_step_transition(current_status: Optional[str], next_status: Optional[str]) -> StepTransitionResult:
    current = normalize_step_status(current_status)
    nxt = normalize_step_status(next_status)
    if current == nxt:
        return StepTransitionResult(current_status=current, next_status=nxt, allowed=True, reason="no-op")
    allowed = nxt in _ALLOWED_TRANSITIONS.get(current, set())
    return StepTransitionResult(
        current_status=current,
        next_status=nxt,
        allowed=allowed,
        reason=None if allowed else f"{current} -> {nxt} is not allowed",
    )



def assert_step_transition(current_status: Optional[str], next_status: Optional[str]) -> None:
    result = validate_step_transition(current_status, next_status)
    if not result.allowed:
        raise ValueError(result.reason or "invalid step state transition")
