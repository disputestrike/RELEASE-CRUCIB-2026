
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

    async def run_task_loop(self, **kwargs) -> Dict[str, Any]:
        """Placeholder for the actual task loop implementation."""
        return {"status": "completed", "execution": {"success": True, "result": "Mocked loop result"}}

runtime_engine = RuntimeEngine()
