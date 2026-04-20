"""Runtime spawn engine.

Phase 2 objective:
- Isolate spawn orchestration from runtime loop control flow
- Keep spawn decisions deterministic and centrally managed
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class SpawnEngine:
    """Coordinates sub-agent spawning from execution decisions."""

    async def maybe_spawn(
        self,
        *,
        runtime_engine: Any,
        task_id: str,
        context: Any,
        decision: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        if not bool((decision or {}).get("spawn")):
            return None

        target_agent = str((decision or {}).get("spawn_agent") or "").strip()
        if not target_agent:
            return None

        project_id = (getattr(context, "project_id", None) or f"runtime-{getattr(context, 'user_id', 'system')}")
        spawn_context = {
            "skill": (decision or {}).get("skill") or (decision or {}).get("action") or "default",
            **(((decision or {}).get("spawn_context") or {})),
        }

        max_depth = int((decision or {}).get("max_depth") or 3)
        max_cost = (decision or {}).get("max_cost")

        return await runtime_engine.spawn_agent(
            project_id=project_id,
            task_id=task_id,
            parent_message=str((decision or {}).get("spawn_message") or "spawn"),
            agent_name=target_agent,
            context=spawn_context,
            depth=getattr(context, "depth", 0) + 1,
            max_depth=max_depth,
            max_cost=max_cost,
        )


spawn_engine = SpawnEngine()
