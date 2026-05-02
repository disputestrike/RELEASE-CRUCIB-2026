"""
Cerebras API Key Round-Robin Router
Distributes requests across all available API keys with per-key rate tracking
to prevent individual key exhaustion.

Keys are loaded from CEREBRAS_API_KEY, CEREBRAS_API_KEY_1 .. CEREBRAS_API_KEY_5 (deduped).
Secrets are NEVER logged, stored in reports, or committed to code.

Rate-aware rotation:
  - Each key tracks its call timestamps in a sliding 60-second window.
  - get_next_cerebras_key() skips keys at their RPM limit; falls back to LRU key
    if all are exhausted (backpressure is the caller's responsibility).
  - wait_for_key() blocks up to `timeout_s` until a key has capacity.
"""

import logging
import os
import threading
import time
from collections import deque
from typing import Optional

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

# RPM limit per key — override with CEREBRAS_RPM_LIMIT env var.
# Cerebras free tier is typically 30 req/min per key.
_RPM_LIMIT = int(os.environ.get("CEREBRAS_RPM_LIMIT", "30"))
_WINDOW_SECONDS = 60.0

# Round-robin state (protected by lock for thread safety)
_state_lock = threading.Lock()
_current_key_index: int = 0

# Per-key sliding-window call log: key → deque of call timestamps
_key_call_log: dict = {}


def _evict_old_calls(log: deque, now: float) -> None:
    """Remove timestamps outside the current window (in-place)."""
    while log and now - log[0] > _WINDOW_SECONDS:
        log.popleft()


def get_next_cerebras_key() -> str:
    """
    Return the next Cerebras API key in round-robin rotation, skipping any key
    that has reached its RPM limit.  Falls back to the least-recently-used key
    if all keys are currently at the limit (callers should back off in that case).
    """
    key, _ = get_next_cerebras_key_with_index()
    return key


def get_next_cerebras_key_with_index() -> tuple:
    """
    Return (key, slot_index) of the next available Cerebras key.

    Rate-aware: skips keys at their RPM limit.  If all keys are exhausted,
    logs a warning and returns the next key in sequence (caller must handle 429s).
    """
    global _current_key_index
    if not CEREBRAS_KEYS:
        raise Exception("No Cerebras API keys configured")

    now = time.time()

    with _state_lock:
        # Try each key in round-robin order, skipping rate-limited ones
        for attempt in range(len(CEREBRAS_KEYS)):
            idx = _current_key_index % len(CEREBRAS_KEYS)
            _current_key_index = (_current_key_index + 1) % len(CEREBRAS_KEYS)
            key = CEREBRAS_KEYS[idx]

            # Initialise log for this key slot
            if key not in _key_call_log:
                _key_call_log[key] = deque()

            log = _key_call_log[key]
            _evict_old_calls(log, now)

            if len(log) < _RPM_LIMIT:
                log.append(now)
                logger.debug(
                    "Cerebras key rotation: slot=%d, calls_in_window=%d/%d",
                    idx, len(log), _RPM_LIMIT,
                )
                return key, idx

        # All keys at limit — fall back to next key and warn
        logger.warning(
            "All %d Cerebras keys at RPM limit (%d/min) — returning next key; "
            "caller should handle 429 / back off.",
            len(CEREBRAS_KEYS), _RPM_LIMIT,
        )
        idx = _current_key_index % len(CEREBRAS_KEYS)
        _current_key_index = (_current_key_index + 1) % len(CEREBRAS_KEYS)
        return CEREBRAS_KEYS[idx], idx


def wait_for_key(timeout_s: float = 30.0) -> Optional[str]:
    """
    Block until a Cerebras key with remaining capacity is available,
    or until `timeout_s` elapses.

    Returns the key string, or None on timeout.
    Intended for callers that prefer blocking over immediate 429 handling.
    """
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        now = time.time()
        with _state_lock:
            for key in CEREBRAS_KEYS:
                if key not in _key_call_log:
                    _key_call_log[key] = deque()
                log = _key_call_log[key]
                _evict_old_calls(log, now)
                if len(log) < _RPM_LIMIT:
                    log.append(now)
                    return key
        time.sleep(1.0)

    logger.warning("wait_for_key: timed out after %.1fs — all keys at limit", timeout_s)
    return None


def get_cerebras_key_pool() -> list:
    """Return all available Cerebras keys (copy)."""
    return CEREBRAS_KEYS.copy()


def has_cerebras_keys() -> bool:
    """Return True if at least one Cerebras key is configured."""
    return len(CEREBRAS_KEYS) > 0


def get_available_key_count() -> int:
    """Return the number of configured Cerebras keys."""
    return len(CEREBRAS_KEYS)


def get_key_capacity_status() -> list:
    """
    Return per-slot capacity status for monitoring.
    Returns list of dicts: {slot, calls_in_window, remaining, at_limit}
    Key values are NEVER included.
    """
    now = time.time()
    status = []
    with _state_lock:
        for i, key in enumerate(CEREBRAS_KEYS):
            if key not in _key_call_log:
                _key_call_log[key] = deque()
            log = _key_call_log[key]
            _evict_old_calls(log, now)
            calls = len(log)
            status.append({
                "slot": i,
                "calls_in_window": calls,
                "remaining": max(0, _RPM_LIMIT - calls),
                "at_limit": calls >= _RPM_LIMIT,
            })
    return status


class PoolTracker:
    """Tracks per-run and session-level provider pool usage metrics.

    Secrets (key values) are NEVER stored; only slot indices are tracked.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._session_keys_exercised: set = set()
        self._session_failover_events: list = []
        self._session_total_calls: int = 0
        self._run_keys_exercised: set = set()
        self._run_failover_events: list = []
        self._run_calls: int = 0
        self._run_latencies: list = []

    def start_run(self) -> None:
        with self._lock:
            self._run_keys_exercised = set()
            self._run_failover_events = []
            self._run_calls = 0
            self._run_latencies = []

    def record_call(self, key_index: int, latency_ms: float) -> None:
        with self._lock:
            self._run_keys_exercised.add(key_index)
            self._run_calls += 1
            self._run_latencies.append(latency_ms)
            self._session_keys_exercised.add(key_index)
            self._session_total_calls += 1

    def record_failover(self, from_index: int, to_index: int, reason: str) -> None:
        event = {"from_slot": from_index, "to_slot": to_index, "reason": reason[:120]}
        with self._lock:
            self._run_failover_events.append(event)
            self._session_failover_events.append(event)

    def get_run_stats(self) -> dict:
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
            "rpm_limit_per_key": _RPM_LIMIT,
            "keys_exercised_count": exercised,
            "failover_triggered": failovers > 0,
            "failover_event_count": failovers,
            "llm_calls": calls,
            "avg_latency_ms": avg_lat,
            "execution_mode": "pooled" if pool_size > 1 else "single_key",
        }

    def get_session_stats(self) -> dict:
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
            "rpm_limit_per_key": _RPM_LIMIT,
            "keys_exercised_count": exercised,
            "failover_events": failovers,
            "total_calls": total,
            "execution_mode": mode,
            "benchmark_note": note,
        }


# Module-level singleton
pool_tracker = PoolTracker()
