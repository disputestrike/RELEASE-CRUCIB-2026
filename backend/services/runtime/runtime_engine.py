
"""
🔥 RuntimeEngine: THE ONLY EXECUTION SYSTEM

This is the unified execution layer that controls ALL execution paths.

MANDATE:
  - brain_layer decides
  - llm_router selects models
  - tool_executor only executes when called
  - agents do NOT run independently
  - NO system can execute outside this engine

EXECUTION LOOP:
  while not task.done:
    decision = brain_layer.decide(context)
    skill = skill_registry.resolve(decision)
    require_runtime_authority(ExecutionPhase.CHECK_PERMISSION)
    permission_engine.check(skill)
    provider = provider_registry.select(skill)
    result = execute_tool(skill)
    
    memory_graph.update(result)
    context_manager.update(result)
    if decision.spawn:
      spawn_subagent()
    if task.cancelled:
      break

This is THE execution control layer. Nothing else can execute.
"""

from __future__ import annotations

import asyncio
import uuid
import time
import logging
import os
import json
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import traceback

from pathlib import Path

from backend.project_state import WORKSPACE_ROOT
from backend.services.runtime.execution_context import runtime_execution_scope
from backend.services.runtime.context_manager import runtime_context_manager
from backend.services.runtime.spawn_engine import spawn_engine
from backend.services.skills.skill_registry import resolve_skill, list_skills, get_skill
from backend.services.runtime.memory_graph import add_node as memory_add_node
from backend.services.runtime.memory_graph import add_edge as memory_add_edge
from backend.services.runtime.virtual_fs import task_workspace
from backend.services.runtime.cost_tracker import cost_tracker
from backend.services.policy.permission_engine import evaluate_tool_call
from backend.services.runtime.execution_authority import require_runtime_authority, runtime_authority_snapshot
from backend.services.conversation_manager import ConversationSession
from backend.services.runtime.task_manager import task_manager
from backend.services.events import event_bus
from backend.llm_router import classifier, router as llm_router
from backend.services.brain_layer import BrainLayer
from backend.tool_executor import execute_tool

try:
    from backend.services.memory_store import memory_store, MemoryScope  # CF3
except Exception:  # pragma: no cover
    memory_store = None  # type: ignore
    MemoryScope = None  # type: ignore
try:
    from backend.services.capability_inspector import capability_inspector  # CF1
except Exception:  # pragma: no cover
    capability_inspector = None  # type: ignore

logger = logging.getLogger(__name__)


class ExecutionPhase(Enum):
    """Phases of execution."""
    INSPECT = "inspect"
    DECIDE = "decide"
    RESOLVE_SKILL = "resolve_skill"
    CHECK_PERMISSION = "check_permission"
    SELECT_PROVIDER = "select_provider"
    EXECUTE = "execute"
    UPDATE_MEMORY = "update_memory"
    UPDATE_CONTEXT = "update_context"
    SPAWN_SUBAGENT = "spawn_subagent"
    CANCELLED = "cancelled"


class ExecutionState(Enum):
    """State of an execution."""
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExecutionContext:
    """Context available to all systems during execution."""
    task_id: str
    user_id: str
    conversation_id: Optional[str] = None
    parent_task_id: Optional[str] = None
    depth: int = 0
    
    # Accumulated state
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    executed_steps: List[Dict[str, Any]] = field(default_factory=list)
    memory: Dict[str, Any] = field(default_factory=dict)
    cost_used: float = 0.0

    # Identifiers used by sub-systems
    project_id: Optional[str] = None

    # Cost enforcement
    cost_limit: float = 50.0

    # Derived
    cancelled: bool = False
    pause_requested: bool = False
    
    def add_step(self, result: Dict[str, Any]) -> None:
        """Record an executed step."""
        self.executed_steps.append(result)
    
    def add_to_history(self, role: str, content: str) -> None:
        """Add to conversation history."""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat()
        })


class RuntimeEngine:
    """
    THE ONLY execution system.
    
    Everything else works THROUGH this engine.
    """
    
    def __init__(self) -> None:
        self._brain_factory = BrainLayer
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.lock = asyncio.Lock()

    def execute_tool_for_task(
        self,
        *,
        project_id: str,
        task_id: str,
        tool_name: str,
        params: Optional[Dict[str, Any]] = None,
        skill_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Synchronous compatibility wrapper for runtime-owned tool execution.

        Tests and legacy policy paths call this directly to prove tools cannot
        run outside runtime authority. The actual execution still goes through
        `backend.tool_executor.execute_tool` inside `runtime_execution_scope`.
        """
        safe_params = dict(params or {})
        if skill_hint and not safe_params.get("skill"):
            safe_params["skill"] = f"/{skill_hint.strip('/')}"
        safe_params.setdefault("task_id", task_id)
        with runtime_execution_scope(
            project_id=project_id,
            task_id=task_id,
            skill_hint=skill_hint,
        ):
            return execute_tool(project_id=project_id, tool_name=tool_name, params=safe_params)

    async def execute_with_control(
        self,
        task_id: str,
        user_id: str,
        request: str,
        conversation_id: Optional[str] = None,
        parent_task_id: Optional[str] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], Any]] = None,
        mode: Optional[str] = None,
        allowed_phases: Optional[List[str]] = None,
        project_id_override: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Main execution entry point with FULL control.
        """
        session_id = (conversation_id or f"runtime-{task_id}").strip()
        project_id = (project_id_override or f"runtime-{user_id}").strip()
        
        runtime_authority_snapshot.set_current_snapshot(project_id)
        session = ConversationSession(session_id=session_id, user_id=user_id)

        task = task_manager.create_task(
            project_id=project_id,
            description=request,
            metadata={
                "source": "runtime.execute_with_control",
                "requested_task_id": task_id,
                "parent_task_id": parent_task_id,
                "session_id": session_id,
            }
        )
        effective_task_id = task["task_id"]

        event_bus.emit(
            "task_start",
            {
                "task_id": effective_task_id,
                "requested_task_id": task_id,
                "user_id": user_id,
                "request": request,
            },
        )

        try:
            brain_result = await self.run_task_loop(
                session=session,
                project_id=project_id,
                task_id=effective_task_id,
                user_message=request,
                progress_callback=progress_callback,
                mode=mode,
                allowed_phases=allowed_phases,
            )

            status = brain_result.get("status")
            if status == "execution_cancelled":
                task_manager.kill_task(project_id, effective_task_id, reason="cancelled_by_runtime")
            elif status == "execution_failed":
                task_manager.fail_task(
                    project_id,
                    effective_task_id,
                    error=str((brain_result.get("execution") or {}).get("error") or "execution_failed"),
                )
            else:
                task_manager.complete_task(
                    project_id,
                    effective_task_id,
                    metadata={
                        "intent": brain_result.get("intent"),
                        "selected_agents": brain_result.get("selected_agents", []),
                    },
                )

            current_task = task_manager.get_task(project_id, effective_task_id)
            
            if memory_store is not None and brain_result.get("status") not in ("execution_failed", "execution_cancelled"):
                try:
                    from backend.db_pg import get_db as _get_db_for_wb
                    _db_wb = await _get_db_for_wb()
                    wb_content = json.dumps(brain_result.get("execution", {}).get("result", {}))
                    if wb_content and len(wb_content) < 100_000:
                        await memory_store.write_memory(
                            user_id=user_id,
                            scope=MemoryScope.PROJECT,
                            key=f"project_result_{project_id}",
                            value=wb_content,
                        )
                except Exception as exc:
                    logger.warning("Failed to write memory for task %s: %s", effective_task_id, exc)

            event_bus.emit(
                "task_end",
                {
                    "task_id": effective_task_id,
                    "requested_task_id": task_id,
                    "state": (current_task or {}).get("status"),
                },
            )
            return brain_result.get("execution") or {"success": True, "output": "Task completed."}

        except Exception as exc:
            logger.exception("RuntimeEngine.execute_with_control failed for task %s: %s", effective_task_id, exc)
            task_manager.fail_task(project_id, effective_task_id, error=str(exc))
            raise

    async def run_task_loop(
        self,
        *,
        session: Any,
        project_id: str,
        task_id: str,
        user_message: str,
        progress_callback: Optional[Callable[[Dict[str, Any]], Any]] = None,
        mode: Optional[str] = None,
        allowed_phases: Optional[List[str]] = None,
        planner: Any = None,
        **_kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Real task execution loop.

        Replaces the one-line mock. Flow:
          1. BrainLayer.decide()  — intent classification + agent selection
          2. Emit plan event
          3. Per-agent execution via execute_request (uses workspace tools)
          4. Memory / context update after each agent
          5. Return structured result consumed by execute_with_control

        The I/O contract is unchanged — callers still receive
        {"status": ..., "execution": {...}, "intent": ..., "selected_agents": [...]}.
        """
        brain = planner or self._brain_factory()
        ctx = ExecutionContext(
            task_id=task_id,
            user_id=getattr(session, "user_id", "system"),
            conversation_id=getattr(session, "session_id", None),
            project_id=project_id,
        )

        # ── Step 1: Planning ─────────────────────────────────────────────
        try:
            plan = brain.decide(session, user_message)
        except Exception as exc:
            logger.exception("[run_task_loop] brain.decide failed: %s", exc)
            return {
                "status": "execution_failed",
                "execution": {"success": False, "error": str(exc)},
                "intent": "unknown",
                "selected_agents": [],
            }

        intent = plan.get("intent", "general")
        selected_agents: List[str] = plan.get("selected_agents") or []
        agent_configs: List[Dict[str, Any]] = plan.get("selected_agent_configs") or []

        event_bus.emit("task_plan", {
            "task_id": task_id,
            "project_id": project_id,
            "intent": intent,
            "selected_agents": selected_agents,
            "mode": mode,
        })
        if progress_callback:
            try:
                await asyncio.coroutine(progress_callback)(
                    {"phase": "planned", "intent": intent, "agents": selected_agents}
                ) if asyncio.iscoroutinefunction(progress_callback) else progress_callback(
                    {"phase": "planned", "intent": intent, "agents": selected_agents}
                )
            except Exception:
                pass

        # ── Step 2: Handle clarification requests ────────────────────────
        if plan.get("status") == "clarification_required":
            return {
                "status": "clarification_required",
                "execution": {
                    "success": True,
                    "result": {"assistant_response": plan.get("assistant_response", "")},
                },
                "intent": intent,
                "selected_agents": [],
            }

        # ── Step 3: Execute selected agents ─────────────────────────────
        agent_results: Dict[str, Any] = {}
        phases = allowed_phases or ["inspect", "classify", "plan", "execute", "test", "artifact"]

        for agent_name in selected_agents:
            # Respect phase gating if allowed_phases was provided
            agent_cfg = next((c for c in agent_configs if c.get("agent") == agent_name), {})

            event_bus.emit("agent_start", {
                "task_id": task_id,
                "project_id": project_id,
                "agent": agent_name,
            })
            if progress_callback:
                try:
                    _cb_payload = {"phase": "executing", "agent": agent_name}
                    if asyncio.iscoroutinefunction(progress_callback):
                        await progress_callback(_cb_payload)
                    else:
                        progress_callback(_cb_payload)
                except Exception:
                    pass

            try:
                exec_meta = {
                    "project_id": project_id,
                    "task_id": task_id,
                    "agent_name": agent_name,
                    **agent_cfg.get("params", {}),
                }
                result = await brain.execute_request(
                    session=session,
                    user_message=user_message,
                    progress_callback=progress_callback,
                    execution_meta=exec_meta,
                )
                agent_results[agent_name] = result

            except Exception as exc:
                logger.error("[run_task_loop] agent %s failed: %s", agent_name, exc)
                agent_results[agent_name] = {
                    "status": "failed",
                    "error": str(exc),
                }

            # Update context and memory after each agent
            ctx.add_step({"agent": agent_name, "result": agent_results[agent_name]})
            try:
                memory_add_node(project_id, agent_name, data={"status": "completed", "task_id": task_id})
            except Exception:
                pass

            event_bus.emit("agent_complete", {
                "task_id": task_id,
                "project_id": project_id,
                "agent": agent_name,
                "status": agent_results[agent_name].get("status", "unknown"),
            })

            # Stop early if a critical failure occurred and mode is not REPAIR
            if agent_results[agent_name].get("status") == "failed" and mode not in ("repair", "phased"):
                logger.warning("[run_task_loop] halting at failed agent %s", agent_name)
                break

        # ── Step 4: Aggregate results ────────────────────────────────────
        any_failed = any(
            v.get("status") == "failed" for v in agent_results.values()
        )
        final_status = "execution_failed" if any_failed and not agent_results else "execution_completed"

        # Collect last text output for callers that need a string summary
        summary_parts = []
        for name, res in agent_results.items():
            if isinstance(res, dict):
                text = (
                    res.get("output")
                    or (res.get("execution") or {}).get("result")
                    or res.get("error")
                    or ""
                )
                if text:
                    summary_parts.append(f"[{name}] {str(text)[:500]}")

        return {
            "status": final_status,
            "intent": intent,
            "selected_agents": selected_agents,
            "execution": {
                "success": not any_failed,
                "result": "\n".join(summary_parts) or "Task completed.",
                "agent_results": agent_results,
                "steps": len(ctx.executed_steps),
            },
        }

runtime_engine = RuntimeEngine()
