"""
backend/services/agent_loop.py
──────────────────────────────
Canonical façade for the CrucibAI agent loop.

Spec: E – Central Agent Loop
Branch: engineering/master-list-closeout

Design principle: This file is a THIN FAÇADE over RuntimeEngine.
No execution logic lives here — RuntimeEngine is the single executor.
This file adds:
  • The canonical path backend/services/agent_loop.py that the spec requires.
  • ExecutionMode enum (8 modes from spec D).
  • AgentLoop.run(mode, goal) public surface.
  • Checkpoint / resume / cancel helpers (spec A / E).
"""

from __future__ import annotations

import logging
import uuid
from enum import Enum
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# D. Execution Modes
# ─────────────────────────────────────────────────────────────────────────────

class ExecutionMode(str, Enum):
    """Eight execution modes.  Each maps to a constrained RuntimeEngine phase set."""

    ANALYZE_ONLY    = "analyze_only"
    """Read-only inspection.  No code writes, no tool side-effects."""

    PLAN_FIRST      = "plan_first"
    """Produce a detailed plan + file map, await approval before execution."""

    SHORT_PASS      = "short_pass"
    """One-shot quick fix: skip migration, skip phasing, skip sub-agents."""

    ONE_PASS        = "one_pass"
    """Single execution loop, no phasing.  Low-risk builds only."""

    PHASED          = "phased"
    """Multi-phase with checkpoint between phases.  Use for high-risk work."""

    MIGRATION       = "migration"
    """Codebase migration / transformation flow.  Produces file map + report."""

    BUILD           = "build"
    """Standard feature build: inspect → plan → execute → test → preview."""

    REPAIR          = "repair"
    """Targeted fix: reproduce → identify root cause → patch → retest."""


# Phases enabled per mode.  RuntimeEngine will skip phases not in this set.
MODE_PHASE_MAP: Dict[ExecutionMode, list[str]] = {
    ExecutionMode.ANALYZE_ONLY: ["inspect", "classify"],
    ExecutionMode.PLAN_FIRST:   ["inspect", "classify", "plan"],
    ExecutionMode.SHORT_PASS:   ["inspect", "execute", "test"],
    ExecutionMode.ONE_PASS:     ["inspect", "classify", "plan", "execute", "test"],
    ExecutionMode.PHASED:       ["inspect", "classify", "plan", "execute", "test", "preview", "repair", "artifact"],
    ExecutionMode.MIGRATION:    ["inspect", "classify", "plan", "migrate", "test", "artifact"],
    ExecutionMode.BUILD:        ["inspect", "classify", "plan", "execute", "test", "preview", "artifact"],
    ExecutionMode.REPAIR:       ["inspect", "reproduce", "execute", "test", "artifact"],
}


def _build_goal_request(goal: str, engine_context: Dict[str, Any]) -> str:
    """Attach execution-mode context to the natural-language goal.

    RuntimeEngine currently accepts a request string as the single planning
    payload, so we embed structured hints in a stable marker block.
    """
    import json

    hints = {
        "mode": engine_context.get("mode"),
        "phases": engine_context.get("phases"),
        "dry_run": engine_context.get("dry_run"),
        "thread_id": engine_context.get("thread_id"),
        "project_id": engine_context.get("project_id"),
    }
    return f"{goal}\n\n[RUNTIME_HINTS]{json.dumps(hints, ensure_ascii=True)}[/RUNTIME_HINTS]"


# ─────────────────────────────────────────────────────────────────────────────
# AgentLoop façade
# ─────────────────────────────────────────────────────────────────────────────

class AgentLoop:
    """Public surface for launching, pausing, resuming and cancelling agent runs.

    All real work is delegated to RuntimeEngine.  This class owns:
      - mode selection logic
      - thread/checkpoint bookkeeping
      - the public async ``run()`` coroutine
    """

    def __init__(self) -> None:
        # Lazy import to avoid circular deps at module load time.
        self._engine: Any = None

    def _get_engine(self):
        if self._engine is None:
            from ....services.runtime.runtime_engine import RuntimeEngine            self._engine = RuntimeEngine()
        return self._engine

    # ── Primary entry point ──────────────────────────────────────────────────

    async def run(
        self,
        *,
        mode: ExecutionMode | str,
        goal: str,
        thread_id: Optional[str] = None,
        user_id: str = "system",
        project_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        on_event: Optional[Callable[[str, Any], None]] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Run the agent loop.

        Args:
            mode:       ExecutionMode (or string value).
            goal:       Natural-language goal / user request.
            thread_id:  Existing thread to continue, or None to start fresh.
            user_id:    Caller identity.
            project_id: Associated project (optional).
            context:    Extra context forwarded to RuntimeEngine.
            on_event:   Optional callback(event_type, payload) for streaming.
            dry_run:    If True, plan only — no destructive tool calls.

        Returns:
            dict with keys: run_id, thread_id, mode, status, result, steps, artifacts
        """
        if isinstance(mode, str):
            try:
                mode = ExecutionMode(mode)
            except ValueError:
                logger.warning("Unknown execution mode '%s', defaulting to BUILD", mode)
                mode = ExecutionMode.BUILD

        run_id = str(uuid.uuid4())
        thread_id = thread_id or str(uuid.uuid4())

        logger.info("[AgentLoop] run_id=%s mode=%s thread=%s dry_run=%s", run_id, mode.value, thread_id, dry_run)

        phases = MODE_PHASE_MAP[mode]

        engine_context = {
            "run_id": run_id,
            "thread_id": thread_id,
            "user_id": user_id,
            "project_id": project_id,
            "goal": goal,
            "mode": mode.value,
            "phases": phases,
            "dry_run": dry_run,
            **(context or {}),
        }

        try:
            request = _build_goal_request(goal, engine_context)
            result = await self._get_engine().execute_with_control(
                task_id=run_id,
                user_id=user_id,
                request=request,
                conversation_id=thread_id,
                progress_callback=(
                    (lambda payload: on_event("progress", payload)) if on_event else None
                ),
                mode=mode.value,  # CF2
                allowed_phases=phases,  # CF2
            )
            return {
                "run_id": run_id,
                "thread_id": thread_id,
                "mode": mode.value,
                "status": "completed",
                "result": result,
                "engine_context": engine_context,
            }
        except Exception as exc:
            logger.exception("[AgentLoop] run %s failed: %s", run_id, exc)
            return {
                "run_id": run_id,
                "thread_id": thread_id,
                "mode": mode.value,
                "status": "failed",
                "error": str(exc),
            }

    # ── Control surface ──────────────────────────────────────────────────────

    async def cancel(self, run_id: str) -> bool:
        """Cancel a running loop by run_id."""
        try:
            engine = self._get_engine()
            if hasattr(engine, "cancel"):
                await engine.cancel(run_id)
                return True
            if hasattr(engine, "cancel_task_controlled"):
                return bool(await engine.cancel_task_controlled(run_id))
            return False
        except Exception as exc:
            logger.warning("[AgentLoop] cancel %s failed: %s", run_id, exc)
            return False

    async def pause(self, run_id: str) -> bool:
        """Pause a running loop (checkpoint will be written)."""
        try:
            engine = self._get_engine()
            if hasattr(engine, "pause"):
                await engine.pause(run_id)
                return True
            if hasattr(engine, "pause_task_controlled"):
                return bool(await engine.pause_task_controlled(run_id))
            return False
        except Exception as exc:
            logger.warning("[AgentLoop] pause %s failed: %s", run_id, exc)
            return False

    async def resume(self, run_id: str, *, on_event: Optional[Callable] = None) -> Dict[str, Any]:
        """Resume a paused or checkpointed loop."""
        try:
            engine = self._get_engine()
            if hasattr(engine, "resume"):
                return await engine.resume(run_id, on_event=on_event)
            if hasattr(engine, "resume_task_controlled"):
                resumed = bool(await engine.resume_task_controlled(run_id))
                return {"run_id": run_id, "status": "resumed" if resumed else "not_found"}
            return {"run_id": run_id, "status": "resumed"}
        except Exception as exc:
            logger.warning("[AgentLoop] resume %s failed: %s", run_id, exc)
            return {"run_id": run_id, "status": "failed", "error": str(exc)}

    # ── Checkpoint helpers ────────────────────────────────────────────────────

    async def save_checkpoint(
        self,
        *,
        thread_id: str,
        run_id: str,
        user_id: str,
        phase: str,
        data: Dict[str, Any],
        db: Any,
    ) -> str:
        """Persist a checkpoint to the thread_checkpoints table."""
        import json
        checkpoint_id = str(uuid.uuid4())
        now = __import__("datetime").datetime.utcnow().isoformat()
        doc = {
            "id": checkpoint_id,
            "thread_id": thread_id,
            "user_id": user_id,
            "checkpoint_data": json.dumps({"run_id": run_id, "phase": phase, **data}),
            "phase": phase,
            "status": "saved",
            "created_at": now,
        }
        await db.execute(
            """INSERT INTO thread_checkpoints (id, thread_id, user_id, checkpoint_data, phase, status, created_at)
               VALUES (:id, :thread_id, :user_id, :checkpoint_data::jsonb, :phase, :status, :created_at)
               ON CONFLICT (id) DO NOTHING""",
            doc,
        )
        return checkpoint_id

    async def load_checkpoint(self, *, thread_id: str, db: Any) -> Optional[Dict[str, Any]]:
        """Load the latest checkpoint for a thread."""
        row = await db.fetch_one(
            """SELECT * FROM thread_checkpoints WHERE thread_id = :thread_id
               ORDER BY created_at DESC LIMIT 1""",
            {"thread_id": thread_id},
        )
        if row is None:
            return None
        import json
        cp = dict(row)
        if isinstance(cp.get("checkpoint_data"), str):
            cp["checkpoint_data"] = json.loads(cp["checkpoint_data"])
        return cp


# Module-level singleton
agent_loop = AgentLoop()
