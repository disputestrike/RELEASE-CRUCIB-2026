"""Runtime context manager for step-by-step state persistence.

Phase 2 objective:
- Keep execution context coherent across phases
- Persist resumable context snapshots to task sandbox
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from .cost_tracker import cost_tracker
from .virtual_fs import task_workspace


class RuntimeContextManager:
    """Updates and persists execution context after each step."""

    def update_from_step(
        self,
        *,
        context: Any,
        task_id: str,
        step_id: str,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        project_id = (getattr(context, "project_id", None) or f"runtime-{getattr(context, 'user_id', 'system')}")

        context.memory["last_result"] = result.get("output")
        context.memory["last_step_id"] = step_id
        context.memory["last_skill"] = (result.get("metadata") or {}).get("skill")
        context.memory["last_provider"] = (result.get("metadata") or {}).get("provider")

        totals = cost_tracker.get(task_id)
        context.cost_used = float(totals.get("credits") or 0.0)

        snapshot = {
            "task_id": task_id,
            "project_id": project_id,
            "step_id": step_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "cost_used": context.cost_used,
            "depth": getattr(context, "depth", 0),
            "cancelled": bool(getattr(context, "cancelled", False)),
            "pause_requested": bool(getattr(context, "pause_requested", False)),
            "memory": dict(context.memory or {}),
            "last_skill": context.memory.get("last_skill"),
            "last_provider": context.memory.get("last_provider"),
            "last_memory_node": context.memory.get("last_memory_node"),
            "executed_steps": len(getattr(context, "executed_steps", []) or []),
        }

        vfs = task_workspace(project_id, task_id, subdir="context")
        vfs.write_text("latest.json", json.dumps(snapshot, indent=2))
        return snapshot

    def load_latest(self, *, project_id: str, task_id: str) -> Optional[Dict[str, Any]]:
        vfs = task_workspace(project_id, task_id, subdir="context")
        if not vfs.exists("latest.json"):
            return None
        try:
            return json.loads(vfs.read_text("latest.json"))
        except Exception:
            return None


runtime_context_manager = RuntimeContextManager()
