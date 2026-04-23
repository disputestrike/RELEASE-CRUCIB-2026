"""Per-task cost accumulation and limit enforcement.

Tracks token usage and credit spend per task_id.
Credit limits are checked before spawning sub-agents.
"""

from __future__ import annotations

import os
import threading
from typing import Dict, Optional

_DEFAULT_COST_LIMIT = float(os.environ.get("CRUCIB_TASK_COST_LIMIT", "50.0"))


class CostTracker:
    """Thread-safe cost accumulator with configurable per-task credit limits."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # {task_id: {"tokens": float, "credits": float}}
        self._ledger: Dict[str, Dict[str, float]] = {}

    def record(
        self,
        task_id: str,
        *,
        tokens: int = 0,
        credits: float = 0.0,
    ) -> Dict[str, float]:
        """Accumulate usage for a task. Returns the updated totals."""
        with self._lock:
            entry = self._ledger.setdefault(task_id, {"tokens": 0.0, "credits": 0.0})
            entry["tokens"] += tokens
            entry["credits"] += credits
            return dict(entry)

    def get(self, task_id: str) -> Dict[str, float]:
        """Return current usage totals for a task (never raises)."""
        with self._lock:
            return dict(self._ledger.get(task_id) or {"tokens": 0.0, "credits": 0.0})

    def check_limit(
        self,
        task_id: str,
        *,
        limit: Optional[float] = None,
    ) -> bool:
        """Return True if the task is within the credit limit.

        Uses ``limit`` when provided, otherwise falls back to the environment
        default (``CRUCIB_TASK_COST_LIMIT``).
        """
        cap = limit if limit is not None else _DEFAULT_COST_LIMIT
        usage = self.get(task_id)
        return float(usage.get("credits") or 0.0) < cap

    def reset(self, task_id: str) -> None:
        """Clear accumulated cost for a task."""
        with self._lock:
            self._ledger.pop(task_id, None)

    def all_tasks(self) -> Dict[str, Dict[str, float]]:
        """Return a snapshot of the full ledger."""
        with self._lock:
            return {k: dict(v) for k, v in self._ledger.items()}


cost_tracker = CostTracker()
