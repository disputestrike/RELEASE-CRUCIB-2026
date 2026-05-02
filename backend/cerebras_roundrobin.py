"""
Cerebras API Key Round-Robin Router
Distributes requests across all available API keys to prevent rate limiting.
Keys are loaded from CEREBRAS_API_KEY, CEREBRAS_API_KEY_1 .. CEREBRAS_API_KEY_5 (deduped).
Secrets are NEVER logged, stored in reports, or committed to code.
"""

import logging
import os
import threading

logger = logging.getLogger(__name__)


def _load_cerebras_keys() -> list:
    """Load all available Cerebras keys from environment variables (deduped, no blanks)."""
    seen: set = set()
    keys: list = []
    candidates = [os.environ.get("CEREBRAS_API_KEY", "").strip()]
    for i in range(1, 6):
        candidates.append(os.environ.get(f"CEREBRAS_API_KEY_{i}", "").strip())
    for k in candidates:
        if k and k not in seen:
            seen.add(k)
            keys.append(k)
    return keys


CEREBRAS_KEYS: list = _load_cerebras_keys()

# Round-robin state (protected by lock for thread safety)
_state_lock = threading.Lock()
_current_key_index: int = 0


def get_next_cerebras_key() -> str:
    """Return the next Cerebras API key in round-robin rotation."""
    key, _ = get_next_cerebras_key_with_index()
    return key


def get_next_cerebras_key_with_index() -> tuple:
    """Return (key, slot_index) of the next Cerebras key in round-robin rotation."""
    global _current_key_index
    if not CEREBRAS_KEYS:
        raise Exception("No Cerebras API keys configured, falling back to env var")
    with _state_lock:
        idx = _current_key_index
        _current_key_index = (_current_key_index + 1) % len(CEREBRAS_KEYS)
    logger.debug("Cerebras key rotation: slot %d → %d", idx, _current_key_index)
    return CEREBRAS_KEYS[idx], idx


def get_cerebras_key_pool() -> list:
    """Return all available Cerebras keys (copy)."""
    return CEREBRAS_KEYS.copy()


def has_cerebras_keys() -> bool:
    """Return True if at least one Cerebras key is configured."""
    return len(CEREBRAS_KEYS) > 0


def get_available_key_count() -> int:
    """Return the number of configured Cerebras keys."""
    return len(CEREBRAS_KEYS)


class PoolTracker:
    """Tracks per-run and session-level provider pool usage metrics.

    Secrets (key values) are NEVER stored; only slot indices are tracked.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # Session-level accumulators
        self._session_keys_exercised: set = set()
        self._session_failover_events: list = []
        self._session_total_calls: int = 0
        # Per-run state (reset between benchmark runs)
        self._run_keys_exercised: set = set()
        self._run_failover_events: list = []
        self._run_calls: int = 0
        self._run_latencies: list = []

    def start_run(self) -> None:
        """Reset per-run counters at the start of each benchmark run."""
        with self._lock:
            self._run_keys_exercised = set()
            self._run_failover_events = []
            self._run_calls = 0
            self._run_latencies = []

    def record_call(self, key_index: int, latency_ms: float) -> None:
        """Record a successful LLM call (slot index and latency, not the key value)."""
        with self._lock:
            self._run_keys_exercised.add(key_index)
            self._run_calls += 1
            self._run_latencies.append(latency_ms)
            self._session_keys_exercised.add(key_index)
            self._session_total_calls += 1

    def record_failover(self, from_index: int, to_index: int, reason: str) -> None:
        """Record a key failover event (slot indices only, not key values)."""
        event = {
            "from_slot": from_index,
            "to_slot": to_index,
            "reason": reason[:120],
        }
        with self._lock:
            self._run_failover_events.append(event)
            self._session_failover_events.append(event)

    def get_run_stats(self) -> dict:
        """Return provider metadata for the current benchmark run."""
        with self._lock:
            pool_size = len(CEREBRAS_KEYS)
            exercised = len(self._run_keys_exercised)
            failovers = len(self._run_failover_events)
            latencies = list(self._run_latencies)
            calls = self._run_calls
        avg_lat = round(sum(latencies) / max(1, len(latencies)), 1)
        return {
            "provider": "cerebras",
            "pool_size": pool_size,
            "keys_exercised_count": exercised,
            "failover_triggered": failovers > 0,
            "failover_event_count": failovers,
            "llm_calls": calls,
            "avg_latency_ms": avg_lat,
            "execution_mode": "pooled" if pool_size > 1 else "single_key",
        }

    def get_session_stats(self) -> dict:
        """Return aggregate provider stats across all runs in this session."""
        with self._lock:
            pool_size = len(CEREBRAS_KEYS)
            exercised = len(self._session_keys_exercised)
            failovers = len(self._session_failover_events)
            total = self._session_total_calls
        mode = "pooled" if pool_size > 1 else "single_key"
        note = (
            f"Results produced using real pooled Cerebras provider execution "
            f"({pool_size} keys configured, {exercised} exercised, {failovers} failover events)."
            if pool_size > 1
            else "Results produced using single-key Cerebras provider execution."
        )
        return {
            "provider": "cerebras",
            "pool_size": pool_size,
            "keys_exercised_count": exercised,
            "failover_events": failovers,
            "total_calls": total,
            "execution_mode": mode,
            "benchmark_note": note,
        }


# Module-level singleton — imported by llm_cerebras and the benchmark scorecard
pool_tracker = PoolTracker()
