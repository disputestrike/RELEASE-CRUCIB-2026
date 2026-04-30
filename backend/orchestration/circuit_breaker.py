"""
Circuit Breaker - Detects retry loops and escalates to human.

Prevents infinite repair loops on the same error.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from enum import Enum


class CircuitState(Enum):
    """States of the circuit breaker."""
    CLOSED = "closed"      # Normal operation, retries allowed
    OPEN = "open"          # Too many failures, blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class FailureRecord:
    """Record of a single failure."""
    timestamp: datetime
    contract_item_id: str
    error_type: str
    error_hash: str  # Normalized error signature
    repair_agent: str


@dataclass
class CircuitBreakerState:
    """Current state of the circuit breaker for a contract item."""
    contract_item_id: str
    state: CircuitState
    failures: List[FailureRecord] = field(default_factory=list)
    last_failure_time: Optional[datetime] = None
    open_time: Optional[datetime] = None
    consecutive_successes: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "contract_item_id": self.contract_item_id,
            "state": self.state.value,
            "failure_count": len(self.failures),
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "open_time": self.open_time.isoformat() if self.open_time else None,
            "consecutive_successes": self.consecutive_successes
        }


class CircuitBreaker:
    """
    Circuit breaker for repair operations.
    
    Detects when the same contract item fails repeatedly
    and escalates to human intervention.
    
    Rules:
    - 3 same failures in 5 minutes → OPEN circuit
    - After 10 minutes in OPEN → HALF_OPEN (allow 1 test)
    - If test succeeds → CLOSED
    - If test fails → OPEN again, escalate to human
    """
    
    def __init__(
        self,
        max_failures: int = 3,
        reset_timeout_seconds: int = 600,  # 10 minutes
        half_open_max_tests: int = 1
    ):
        self.max_failures = max_failures
        self.reset_timeout = timedelta(seconds=reset_timeout_seconds)
        self.half_open_max_tests = half_open_max_tests
        
        # State per contract item
        self._states: Dict[str, CircuitBreakerState] = {}
    
    def record_failure(
        self,
        contract_item_id: str,
        error_type: str,
        error_message: str,
        repair_agent: str
    ) -> CircuitBreakerState:
        """
        Record a failure for a contract item.
        
        Returns the current state after recording.
        """
        # Get or create state
        state = self._get_or_create_state(contract_item_id)
        
        # Create normalized error hash
        error_hash = self._normalize_error(error_type, error_message)
        
        # Record the failure
        record = FailureRecord(
            timestamp=datetime.utcnow(),
            contract_item_id=contract_item_id,
            error_type=error_type,
            error_hash=error_hash,
            repair_agent=repair_agent
        )
        state.failures.append(record)
        state.last_failure_time = record.timestamp
        state.consecutive_successes = 0  # Reset success count
        
        # Check if circuit should open
        recent_failures = self._count_recent_failures(state, window_minutes=5)
        same_error_failures = self._count_same_error_failures(state, error_hash)
        
        if state.state == CircuitState.CLOSED:
            if same_error_failures >= self.max_failures:
                # Same error 3 times - OPEN the circuit
                state.state = CircuitState.OPEN
                state.open_time = datetime.utcnow()
        
        elif state.state == CircuitState.HALF_OPEN:
            # Failure in half-open → back to OPEN
            state.state = CircuitState.OPEN
            state.open_time = datetime.utcnow()
        
        return state
    
    def record_success(self, contract_item_id: str) -> CircuitBreakerState:
        """
        Record a success for a contract item.
        
        Returns the current state after recording.
        """
        state = self._get_or_create_state(contract_item_id)
        state.consecutive_successes += 1
        
        if state.state == CircuitState.HALF_OPEN:
            if state.consecutive_successes >= self.half_open_max_tests:
                # Success in half-open → CLOSED
                state.state = CircuitState.CLOSED
                state.failures = []  # Clear history
                state.open_time = None
        
        elif state.state == CircuitState.CLOSED:
            # Normal success, clear old failures
            self._clear_old_failures(state, window_minutes=10)
        
        return state
    
    def can_execute(self, contract_item_id: str) -> bool:
        """
        Check if execution is allowed for this contract item.
        
        Returns True if allowed, False if circuit is OPEN.
        """
        state = self._get_or_create_state(contract_item_id)
        
        if state.state == CircuitState.CLOSED:
            return True
        
        elif state.state == CircuitState.OPEN:
            # Check if reset timeout has passed
            if state.open_time:
                elapsed = datetime.utcnow() - state.open_time
                if elapsed >= self.reset_timeout:
                    # Transition to HALF_OPEN
                    state.state = CircuitState.HALF_OPEN
                    state.consecutive_successes = 0
                    return True
            return False
        
        elif state.state == CircuitState.HALF_OPEN:
            # Allow limited tests in half-open
            return True
        
        return True
    
    def should_escalate_to_human(self, contract_item_id: str) -> bool:
        """
        Check if we should escalate this to human intervention.
        
        Returns True if:
        - Circuit is OPEN and has been for a while
        - Multiple different repair agents have failed
        """
        state = self._get_or_create_state(contract_item_id)
        
        if state.state != CircuitState.OPEN:
            return False
        
        # Check if multiple agents have been tried
        tried_agents = set(f.repair_agent for f in state.failures)
        if len(tried_agents) >= 3:
            # 3+ different agents failed - escalate
            return True
        
        # Check if circuit has been open too long
        if state.open_time:
            elapsed = datetime.utcnow() - state.open_time
            if elapsed >= self.reset_timeout * 2:  # 2x timeout
                # Stuck too long - escalate
                return True
        
        return False
    
    def get_state(self, contract_item_id: str) -> CircuitBreakerState:
        """Get current state for a contract item."""
        return self._get_or_create_state(contract_item_id)
    
    def _get_or_create_state(self, contract_item_id: str) -> CircuitBreakerState:
        """Get existing state or create new."""
        if contract_item_id not in self._states:
            self._states[contract_item_id] = CircuitBreakerState(
                contract_item_id=contract_item_id,
                state=CircuitState.CLOSED
            )
        return self._states[contract_item_id]
    
    def _normalize_error(self, error_type: str, error_message: str) -> str:
        """
        Create a normalized hash of the error.
        
        This groups similar errors together.
        """
        # Remove file-specific details (paths, line numbers)
        normalized = error_message
        normalized = self._remove_paths(normalized)
        normalized = self._remove_line_numbers(normalized)
        normalized = normalized.lower().strip()
        
        # Simple hash: first 50 chars of normalized message
        return f"{error_type}:{normalized[:50]}"
    
    def _remove_paths(self, message: str) -> str:
        """Remove file paths from error message."""
        # Pattern: /path/to/file.tsx or C:\path\to\file.tsx
        import re
        return re.sub(r'([A-Za-z]:)?[/\\][\w/\\.-]+\.[\w]+', '<PATH>', message)
    
    def _remove_line_numbers(self, message: str) -> str:
        """Remove line numbers from error message."""
        import re
        return re.sub(r'\(\d+,?\d*\)', '(L,C)', message)
    
    def _count_recent_failures(self, state: CircuitBreakerState, window_minutes: int) -> int:
        """Count failures within time window."""
        cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
        return sum(1 for f in state.failures if f.timestamp > cutoff)
    
    def _count_same_error_failures(self, state: CircuitBreakerState, error_hash: str) -> int:
        """Count failures with same error signature."""
        cutoff = datetime.utcnow() - timedelta(minutes=5)
        return sum(
            1 for f in state.failures
            if f.error_hash == error_hash and f.timestamp > cutoff
        )
    
    def _clear_old_failures(self, state: CircuitBreakerState, window_minutes: int):
        """Clear failures older than window."""
        cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
        state.failures = [f for f in state.failures if f.timestamp > cutoff]


class CircuitBreakerMonitor:
    """
    Monitors all circuit breakers and reports status.
    
    Used for visibility into system health.
    """
    
    def __init__(self, circuit_breaker: CircuitBreaker):
        self.cb = circuit_breaker
    
    def get_all_open_circuits(self) -> List[CircuitBreakerState]:
        """Get all currently open circuits."""
        return [
            state for state in self.cb._states.values()
            if state.state == CircuitState.OPEN
        ]
    
    def get_escalation_candidates(self) -> List[CircuitBreakerState]:
        """Get circuits that should escalate to human."""
        return [
            state for state in self.cb._states.values()
            if self.cb.should_escalate_to_human(state.contract_item_id)
        ]
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get overall health report."""
        states = list(self.cb._states.values())
        
        total = len(states)
        closed = sum(1 for s in states if s.state == CircuitState.CLOSED)
        open_count = sum(1 for s in states if s.state == CircuitState.OPEN)
        half_open = sum(1 for s in states if s.state == CircuitState.HALF_OPEN)
        
        return {
            "total_circuits": total,
            "closed": closed,
            "open": open_count,
            "half_open": half_open,
            "healthy": open_count == 0,
            "escalation_required": len(self.get_escalation_candidates())
        }
