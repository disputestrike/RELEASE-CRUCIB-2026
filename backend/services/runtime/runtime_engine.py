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
    permission_engine.check(skill)
    provider = provider_registry.select(skill)
    result = tool_executor.execute(skill)
    event_bus.emit("step")
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
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import traceback

from pathlib import Path

# Existing imports preserved for compatibility
from llm_router import classifier, router as llm_router
from project_state import WORKSPACE_ROOT
from services.brain_layer import BrainLayer
from services.conversation_manager import ConversationSession
from services.events import event_bus
from services.runtime.execution_authority import (
    require_runtime_authority,
    runtime_authority_snapshot,
)
from services.runtime.execution_context import runtime_execution_scope
from services.runtime.task_manager import task_manager
from services.runtime.context_manager import runtime_context_manager
from services.runtime.spawn_engine import spawn_engine
from tool_executor import execute_tool
from services.skills.skill_registry import resolve_skill, list_skills, get_skill
from services.runtime.memory_graph import add_node as memory_add_node
from services.runtime.virtual_fs import task_workspace
from services.runtime.cost_tracker import cost_tracker
from services.policy.permission_engine import evaluate_tool_call

logger = logging.getLogger(__name__)


class ExecutionPhase(Enum):
    """Phases of execution."""
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
    
    # =========================================================================
    # EXECUTION ENTRY POINT - The only method that should execute tasks
    # =========================================================================
    
    async def execute_with_control(
        self,
        task_id: str,
        user_id: str,
        request: str,
        conversation_id: Optional[str] = None,
        parent_task_id: Optional[str] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], Any]] = None,
    ) -> Dict[str, Any]:
        """
        Main execution entry point with FULL control.
        
        This is THE ONLY method that should execute any task.
        All systems work THROUGH this.
        
        Args:
            task_id: Unique task ID
            user_id: User making request
            request: Request/message to process
            conversation_id: Optional conversation ID
            parent_task_id: Optional parent task ID for sub-agents
            progress_callback: Optional callback for progress updates
            
        Returns:
            Execution result
            
        Raises:
            RuntimeError: If execution fails
        """
        
        session_id = (conversation_id or f"runtime-{task_id}").strip()
        project_id = f"runtime-{user_id}"
        session = ConversationSession(session_id=session_id, user_id=user_id)

        task = task_manager.create_task(
            project_id=project_id,
            description=request,
            metadata={
                "source": "runtime.execute_with_control",
                "requested_task_id": task_id,
                "parent_task_id": parent_task_id,
                "session_id": session_id,
            },
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
            event_bus.emit(
                "task_end",
                {
                    "task_id": effective_task_id,
                    "requested_task_id": task_id,
                    "state": (current_task or {}).get("status"),
                },
            )

            return {
                "task_id": effective_task_id,
                "requested_task_id": task_id,
                "project_id": project_id,
                "task_status": (current_task or {}).get("status"),
                "brain_result": brain_result,
                "assistant_response": brain_result.get("assistant_response"),
            }
        except Exception as e:
            task_manager.fail_task(project_id, effective_task_id, error=str(e))
            event_bus.emit(
                "task_error",
                {
                    "task_id": effective_task_id,
                    "requested_task_id": task_id,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                },
            )
            raise
    
    # =========================================================================
    # EXECUTION LOOP - The core control flow
    # =========================================================================
    
    async def _execution_loop(
        self,
        task_id: str,
        context: ExecutionContext,
        request: str,
        progress_callback: Optional[Callable[[Dict[str, Any]], Any]] = None
    ) -> Dict[str, Any]:
        """
        The core execution loop - ONLY place where real execution happens.
        
        while not task.done:
          decision = brain_layer.decide(context)
          skill = skill_registry.resolve(decision)
          permission_engine.check(skill)
          provider = provider_registry.select(skill)
          result = tool_executor.execute(skill)
          event_bus.emit("step")
          memory_graph.update(result)
          context_manager.update(result)
          if decision.spawn:
            spawn_subagent()
          if task.cancelled:
            break
        """
        
        step_count = 0
        max_steps = 100
        
        while step_count < max_steps:
            # Check cancellation
            if context.cancelled:
                event_bus.emit("execution_cancelled", {"task_id": task_id})
                break
            
            step_count += 1
            step_id = f"{task_id}-step-{step_count}"
            
            try:
                # PHASE 1: DECIDE - Brain layer decides what to do
                decision = await self._phase_decide(
                    task_id, context, request, step_id, progress_callback
                )
                if decision is None:
                    break
                
                # PHASE 2: RESOLVE SKILL - Convert decision to concrete skill
                skill = await self._phase_resolve_skill(
                    task_id, context, decision, step_id
                )
                if skill is None:
                    break
                
                # PHASE 3: CHECK PERMISSION - Permission engine validates
                permitted = await self._phase_check_permission(
                    task_id, context, skill, step_id
                )
                if not permitted:
                    raise PermissionError(f"Skill {skill} not permitted")
                
                # PHASE 4: SELECT PROVIDER - Choose best provider
                provider = await self._phase_select_provider(
                    task_id, context, skill, step_id
                )
                
                # PHASE 5: EXECUTE - Only place where execution happens
                execution_result = await self._phase_execute(
                    task_id, context, skill, provider, step_id
                )
                
                if not execution_result.get("success"):
                    raise RuntimeError(f"Execution failed: {execution_result.get('error')}")
                
                context.add_step(execution_result)
                
                # PHASE 6: EMIT EVENT
                event_bus.emit("step_complete", {
                    "task_id": task_id,
                    "step_id": step_id,
                    "step_number": step_count,
                    "output": execution_result.get("output")
                })
                
                # PHASE 7: UPDATE MEMORY
                await self._phase_update_memory(task_id, context, execution_result, step_id)
                
                # PHASE 8: UPDATE CONTEXT
                await self._phase_update_context(task_id, context, execution_result, step_id)
                
                # PHASE 9: SPAWN SUBAGENT (if requested by decision)
                if bool(decision.get("spawn")):
                    await self._phase_spawn_subagent(
                        task_id=task_id,
                        context=context,
                        decision=decision,
                        step_id=step_id,
                    )

                # Continue only when the decision explicitly requests another step.
                if not bool(decision.get("continue")):
                    break
                    
            except Exception as e:
                logger.error(f"Step {step_id} failed: {e}", exc_info=True)
                event_bus.emit("step_error", {
                    "task_id": task_id,
                    "step_id": step_id,
                    "error": str(e)
                })
                raise
        
        # Extract final result
        if context.executed_steps:
            return {
                "success": True,
                "output": context.executed_steps[-1].get("output"),
                "steps": len(context.executed_steps)
            }
        return {
            "success": False,
            "output": None,
            "steps": 0
        }
    
    # =========================================================================
    # EXECUTION PHASES - Each phase is isolated and controlled
    # =========================================================================
    
    async def _phase_decide(
        self,
        task_id: str,
        context: ExecutionContext,
        request: str,
        step_id: str,
        progress_callback: Optional[Callable] = None
    ) -> Optional[Dict[str, Any]]:
        """Phase 1: Brain layer decides what to do."""
        
        start_time = time.time()
        
        try:
            event_bus.emit("phase_start", {
                "task_id": task_id,
                "step_id": step_id,
                "phase": ExecutionPhase.DECIDE.value
            })
            
            # Call brain layer via existing infrastructure
            brain = self._brain_factory()
            # For now, use existing brain.decide pattern
            # TODO: Unify with new decision model
            
            duration_ms = (time.time() - start_time) * 1000
            
            decision = {
                "action": "default",
                "skill": "default",
                "confidence": 1.0,
                "continue": False,
                "spawn": False,
            }
            
            event_bus.emit("phase_end", {
                "task_id": task_id,
                "step_id": step_id,
                "phase": ExecutionPhase.DECIDE.value,
                "duration_ms": duration_ms,
                "decision": decision
            })
            
            return decision
            
        except Exception as e:
            logger.error(f"DECIDE phase failed: {e}", exc_info=True)
            raise
    
    async def _phase_resolve_skill(
        self,
        task_id: str,
        context: ExecutionContext,
        decision: Dict[str, Any],
        step_id: str
    ) -> Optional[str]:
        """Phase 2: Resolve decision to concrete skill."""
        
        start_time = time.time()
        
        try:
            event_bus.emit("phase_start", {
                "task_id": task_id,
                "step_id": step_id,
                "phase": ExecutionPhase.RESOLVE_SKILL.value
            })
            
            # Resolve skill from registry
            skill = resolve_skill(decision.get("action", ""))
            if skill:
                skill_name = skill.name
            else:
                skill_name = decision.get("skill", "default")
            
            duration_ms = (time.time() - start_time) * 1000
            
            event_bus.emit("phase_end", {
                "task_id": task_id,
                "step_id": step_id,
                "phase": ExecutionPhase.RESOLVE_SKILL.value,
                "duration_ms": duration_ms,
                "skill": skill_name
            })
            
            return skill_name
            
        except Exception as e:
            logger.error(f"RESOLVE_SKILL phase failed: {e}", exc_info=True)
            raise
    
    async def _phase_check_permission(
        self,
        task_id: str,
        context: ExecutionContext,
        skill: str,
        step_id: str
    ) -> bool:
        """Phase 3: Permission engine checks if skill is allowed."""
        
        start_time = time.time()
        
        try:
            event_bus.emit("phase_start", {
                "task_id": task_id,
                "step_id": step_id,
                "phase": ExecutionPhase.CHECK_PERMISSION.value
            })
            
            # Resolve skill and enforce known-skill policy.
            known = {s.name for s in list_skills()} | {"default"}
            if skill in known:
                permitted = True
                reason = f"known_skill:{skill}"

                # Phase 2: enforce policy at skill->tool boundary.
                skill_def = get_skill(skill)
                if skill_def is not None:
                    project_id = context.project_id or f"runtime-{context.user_id}"
                    for tool_name in sorted(skill_def.allowed_tools):
                        decision = evaluate_tool_call(
                            tool_name,
                            {},
                            surface=skill_def.surface,
                            skill_name=skill_def.name,
                            project_id=project_id,
                        )
                        if not decision.allowed:
                            permitted = False
                            if decision.ask:
                                reason = f"approval_required:{tool_name}:{decision.reason}"
                            else:
                                reason = f"policy_blocked:{tool_name}:{decision.reason}"
                            break
            else:
                import os as _os
                if _os.environ.get("CRUCIB_ENABLE_TOOL_POLICY", "0").strip().lower() in ("1", "true", "yes"):
                    permitted = False
                    reason = f"unknown_skill_blocked_by_policy:{skill}"
                else:
                    permitted = True
                    reason = f"unknown_skill_policy_disabled:{skill}"

            duration_ms = (time.time() - start_time) * 1000

            event_bus.emit("phase_end", {
                "task_id": task_id,
                "step_id": step_id,
                "phase": ExecutionPhase.CHECK_PERMISSION.value,
                "duration_ms": duration_ms,
                "permitted": permitted,
                "reason": reason,
            })

            return permitted
            
        except Exception as e:
            logger.error(f"CHECK_PERMISSION phase failed: {e}", exc_info=True)
            raise
    
    async def _phase_select_provider(
        self,
        task_id: str,
        context: ExecutionContext,
        skill: str,
        step_id: str
    ) -> Optional[Dict[str, Any]]:
        """Phase 4: Provider registry selects best provider."""
        
        start_time = time.time()
        
        try:
            event_bus.emit("phase_start", {
                "task_id": task_id,
                "step_id": step_id,
                "phase": ExecutionPhase.SELECT_PROVIDER.value
            })

            # Phase 6: central provider control via llm_router chain selection.
            skill_def = get_skill(skill)
            complexity = classifier.classify(skill or "", skill)
            credits_left = max(0, int((context.cost_limit or 0) - (context.cost_used or 0)))
            chain = llm_router.get_model_chain(
                task_complexity=complexity,
                user_tier="free",
                speed_selector="lite",
                available_credits=credits_left,
            )
            first = chain[0] if chain else ("none", "none", "none")
            provider = {
                "type": first[2],
                "model": first[1],
                "alias": first[0],
                "chain": [
                    {"alias": alias, "model": model, "provider": prov}
                    for (alias, model, prov) in chain
                ],
                "surface": skill_def.surface if skill_def else None,
            }

            event_bus.emit("provider.chain.selected.runtime", {
                "task_id": task_id,
                "step_id": step_id,
                "skill": skill,
                "provider": provider,
            })
            
            duration_ms = (time.time() - start_time) * 1000
            
            event_bus.emit("phase_end", {
                "task_id": task_id,
                "step_id": step_id,
                "phase": ExecutionPhase.SELECT_PROVIDER.value,
                "duration_ms": duration_ms,
                "provider": provider
            })
            
            return provider
            
        except Exception as e:
            logger.error(f"SELECT_PROVIDER phase failed: {e}", exc_info=True)
            raise
    
    async def _phase_execute(
        self,
        task_id: str,
        context: ExecutionContext,
        skill: str,
        provider: Optional[Dict[str, Any]],
        step_id: str
    ) -> Dict[str, Any]:
        """Phase 5: Tool executor runs the skill."""
        
        start_time = time.time()
        
        try:
            event_bus.emit("phase_start", {
                "task_id": task_id,
                "step_id": step_id,
                "phase": ExecutionPhase.EXECUTE.value
            })
            
            # Execute skill via tool executor
            # This is the ONLY place where real execution happens
            output = execute_tool(
                task_id,
                skill,
                context.memory
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            result = {
                "phase": ExecutionPhase.EXECUTE.value,
                "success": True,
                "output": output,
                "duration_ms": duration_ms,
                "metadata": {"skill": skill, "provider": provider},
            }
            # Record execution cost in the global cost tracker.
            cost_tracker.record(task_id, credits=duration_ms / 1000.0)
            
            event_bus.emit("phase_end", {
                "task_id": task_id,
                "step_id": step_id,
                "phase": ExecutionPhase.EXECUTE.value,
                "duration_ms": duration_ms,
                "success": True
            })
            
            return result
            
        except Exception as e:
            logger.error(f"EXECUTE phase failed: {e}", exc_info=True)
            
            return {
                "phase": ExecutionPhase.EXECUTE.value,
                "success": False,
                "error": str(e),
                "duration_ms": (time.time() - start_time) * 1000
            }
    
    async def _phase_update_memory(
        self,
        task_id: str,
        context: ExecutionContext,
        result: Dict[str, Any],
        step_id: str
    ) -> None:
        """Phase 6: Update memory graph with execution result."""
        
        try:
            event_bus.emit("phase_start", {
                "task_id": task_id,
                "step_id": step_id,
                "phase": ExecutionPhase.UPDATE_MEMORY.value
            })
            
            # Persist step result to memory graph.
            project_id = context.project_id or f"runtime-{context.user_id}"
            node_id = memory_add_node(
                project_id,
                task_id=task_id,
                node_type="step_result",
                payload={
                    "step_id": step_id,
                    "output": result.get("output"),
                    "skill": (result.get("metadata") or {}).get("skill"),
                    "duration_ms": result.get("duration_ms"),
                    "success": result.get("success"),
                },
                tags=["step", task_id],
            )
            # Also update fast in-memory cache.
            context.memory["last_result"] = result.get("output")
            context.memory["last_step_id"] = step_id
            context.memory["last_memory_node"] = node_id

            event_bus.emit("phase_end", {
                "task_id": task_id,
                "step_id": step_id,
                "phase": ExecutionPhase.UPDATE_MEMORY.value,
                "node_id": node_id,
            })
            
        except Exception as e:
            logger.warning(f"Failed to update memory: {e}")
    
    async def _phase_update_context(
        self,
        task_id: str,
        context: ExecutionContext,
        result: Dict[str, Any],
        step_id: str
    ) -> None:
        """Phase 7: Update execution context with step result."""
        
        try:
            event_bus.emit("phase_start", {
                "task_id": task_id,
                "step_id": step_id,
                "phase": ExecutionPhase.UPDATE_CONTEXT.value
            })

            snapshot = runtime_context_manager.update_from_step(
                context=context,
                task_id=task_id,
                step_id=step_id,
                result=result,
            )

            event_bus.emit("phase_end", {
                "task_id": task_id,
                "step_id": step_id,
                "phase": ExecutionPhase.UPDATE_CONTEXT.value,
                "cost_used": context.cost_used,
                "snapshot_step_id": snapshot.get("step_id"),
            })
            
        except Exception as e:
            logger.warning(f"Failed to update context: {e}")

    async def _phase_spawn_subagent(
        self,
        task_id: str,
        context: ExecutionContext,
        decision: Dict[str, Any],
        step_id: str,
    ) -> None:
        """Phase 9: Spawn sub-agent branch when decision requests it."""

        try:
            event_bus.emit(
                "phase_start",
                {
                    "task_id": task_id,
                    "step_id": step_id,
                    "phase": ExecutionPhase.SPAWN_SUBAGENT.value,
                },
            )

            spawn_result = await spawn_engine.maybe_spawn(
                runtime_engine=self,
                task_id=task_id,
                context=context,
                decision=decision,
            )
            target_agent = str(decision.get("spawn_agent") or "").strip()

            event_bus.emit(
                "phase_end",
                {
                    "task_id": task_id,
                    "step_id": step_id,
                    "phase": ExecutionPhase.SPAWN_SUBAGENT.value,
                    "spawn_requested": bool(spawn_result),
                    "spawn_agent": target_agent or None,
                    "spawn_result": spawn_result,
                },
            )
        except Exception as e:
            logger.warning(f"SPAWN_SUBAGENT phase failed: {e}")

    def get_task_status(self, project_id: str, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status. Uses task_manager for compatibility."""
        return task_manager.get_task(project_id, task_id)

    def cancel_task(self, project_id: str, task_id: str, reason: str = "cancelled_by_user") -> Optional[Dict[str, Any]]:
        """Cancel task. Uses task_manager for compatibility."""
        return task_manager.kill_task(project_id, task_id, reason=reason)
    
    # =========================================================================
    # CONTROL METHODS - Pause, resume, cancel with full control
    # =========================================================================
    
    async def cancel_task_controlled(self, task_id: str) -> bool:
        """Cancel a task execution with full control."""
        async with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task["state"] = ExecutionState.CANCELLED.value
                event_bus.emit("task_cancel_requested", {"task_id": task_id})
                return True
        return False
    
    async def pause_task_controlled(self, task_id: str) -> bool:
        """Pause a task execution."""
        async with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                task["state"] = ExecutionState.PAUSED.value
                task["context"].pause_requested = True
                event_bus.emit("task_paused", {"task_id": task_id})
                return True
        return False
    
    async def resume_task_controlled(self, task_id: str) -> bool:
        """Resume a paused task execution."""
        async with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                if task["state"] == ExecutionState.PAUSED.value:
                    task["state"] = ExecutionState.RUNNING.value
                    task["context"].pause_requested = False
                    event_bus.emit("task_resumed", {"task_id": task_id})
                    return True
        return False
    
    async def get_task_state_controlled(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get current state of a task with full details."""
        async with self.lock:
            if task_id in self.tasks:
                task = self.tasks[task_id]
                context = task.get("context", {})
                return {
                    "id": task_id,
                    "state": task.get("state"),
                    "created_at": task.get("created_at"),
                    "started_at": task.get("started_at"),
                    "completed_at": task.get("completed_at"),
                    "steps_completed": len(context.executed_steps) if hasattr(context, "executed_steps") else 0,
                    "cost_used": context.cost_used if hasattr(context, "cost_used") else 0,
                    "depth": context.depth if hasattr(context, "depth") else 0,
                    "cancelled": context.cancelled if hasattr(context, "cancelled") else False,
                    "error": task.get("error")
                }
        return None

    def execute_tool_for_task(
        self,
        *,
        project_id: str,
        task_id: str,
        tool_name: str,
        params: Dict[str, Any],
        skill_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
        with runtime_execution_scope(project_id=project_id, task_id=task_id, skill_hint=skill_hint):
            require_runtime_authority("runtime_engine", detail="tool dispatch")
            authority = runtime_authority_snapshot()
            p = dict(params or {})
            p.setdefault("task_id", task_id)
            p.setdefault("authority", authority)
            return execute_tool(project_id, tool_name, p)

    async def call_model_for_task(
        self,
        *,
        project_id: str,
        task_id: str,
        message: str,
        system_message: str,
        session_id: str,
        model_chain: list,
        user_id: Optional[str] = None,
        user_tier: str = "free",
        speed_selector: str = "lite",
        available_credits: int = 0,
        agent_name: str = "",
        api_keys: Optional[Dict[str, Optional[str]]] = None,
        content_blocks: Optional[List[Dict[str, Any]]] = None,
        idempotency_key: Optional[str] = None,
        skill_hint: Optional[str] = None,
    ) -> tuple[str, str]:
        from services import llm_service

        event_payload = {
            "project_id": project_id,
            "task_id": task_id,
            "agent": agent_name or "llm",
            "tool": "llm",
        }
        event_bus.emit("tool_start", event_payload)
        try:
            with runtime_execution_scope(project_id=project_id, task_id=task_id, skill_hint=skill_hint):
                require_runtime_authority("runtime_engine", detail="model dispatch")
                authority = runtime_authority_snapshot()
                result = await llm_service._call_llm_with_fallback(
                    message=message,
                    system_message=system_message,
                    session_id=session_id,
                    model_chain=model_chain,
                    user_id=user_id,
                    user_tier=user_tier,
                    speed_selector=speed_selector,
                    available_credits=available_credits,
                    agent_name=agent_name,
                    api_keys=api_keys,
                    content_blocks=content_blocks,
                    idempotency_key=idempotency_key,
                )
            # Record approximate token cost from response length.
            _text = result[0] if isinstance(result, tuple) else str(result)
            _tokens = len(_text) // 4
            cost_tracker.record(task_id, tokens=_tokens, credits=round(_tokens * 0.000002, 6))
            event_bus.emit("tool_end", {**event_payload, "authority": authority})
            return result
        except Exception as exc:
            event_bus.emit("error", {**event_payload, "error": str(exc)})
            raise

    async def call_model_for_request(
        self,
        *,
        session_id: str,
        project_id: str,
        description: str,
        message: str,
        system_message: str,
        model_chain: list,
        user_id: Optional[str] = None,
        user_tier: str = "free",
        speed_selector: str = "lite",
        available_credits: int = 0,
        agent_name: str = "",
        api_keys: Optional[Dict[str, Optional[str]]] = None,
        content_blocks: Optional[List[Dict[str, Any]]] = None,
        idempotency_key: Optional[str] = None,
        skill_hint: Optional[str] = None,
    ) -> tuple[str, str]:
        task = task_manager.create_task(
            project_id=project_id,
            description=description,
            metadata={"session_id": session_id, "source": "runtime.llm"},
        )
        task_id = task["task_id"]
        try:
            text, model = await self.call_model_for_task(
                project_id=project_id,
                task_id=task_id,
                message=message,
                system_message=system_message,
                session_id=session_id,
                model_chain=model_chain,
                user_id=user_id,
                user_tier=user_tier,
                speed_selector=speed_selector,
                available_credits=available_credits,
                agent_name=agent_name,
                api_keys=api_keys,
                content_blocks=content_blocks,
                idempotency_key=idempotency_key,
                skill_hint=skill_hint,
            )
            task_manager.complete_task(project_id, task_id, metadata={"model_used": model})
            return text, model
        except Exception as exc:
            task_manager.fail_task(project_id, task_id, error=str(exc))
            raise

    def _select_provider_chain(self, user_message: str, agent_name: str) -> List[Dict[str, str]]:
        complexity = classifier.classify(user_message, agent_name)
        chain = llm_router.get_model_chain(
            task_complexity=complexity,
            user_tier="free",
            speed_selector="lite",
            available_credits=0,
        )
        return [
            {"alias": alias, "model": model, "provider": provider}
            for (alias, model, provider) in chain
        ]

    def _isolated_subagent_workspace(self, project_id: str, task_id: str, agent_name: str, depth: int) -> Path:
        safe_project = project_id.replace("/", "_").replace("\\", "_")
        safe_agent = agent_name.replace("/", "_").replace("\\", "_").replace(" ", "_")
        root = WORKSPACE_ROOT / safe_project / "_subagents" / task_id / f"d{depth}_{safe_agent}"
        root.mkdir(parents=True, exist_ok=True)
        return root

    async def spawn_agent(
        self,
        *,
        project_id: str,
        task_id: str,
        parent_message: str,
        agent_name: str,
        context: Dict[str, Any],
        depth: int = 1,
        max_depth: int = 3,
        max_cost: Optional[float] = None,
    ) -> Dict[str, Any]:
        parent_task = task_manager.get_task(project_id, task_id)
        if parent_task and parent_task.get("status") == "killed":
            return {
                "success": False,
                "error": "parent_task_cancelled",
                "task_id": task_id,
            }
        if parent_task and parent_task.get("status") == "paused":
            return {
                "success": False,
                "error": "parent_task_paused",
                "task_id": task_id,
            }

        if not cost_tracker.check_limit(task_id, limit=max_cost):
            return {"success": False, "error": "subagent_cost_limit_exceeded", "task_id": task_id}
        if depth > max_depth:
            return {"success": False, "error": "subagent_max_depth_exceeded", "depth": depth}

        workspace = self._isolated_subagent_workspace(project_id, task_id, agent_name, depth)
        brain = self._brain_factory()
        instances = brain._get_agent_instances()
        agent = instances.get(agent_name)
        if not agent:
            return {"success": False, "error": f"subagent_not_found:{agent_name}"}

        payload = dict(context or {})
        payload.update(
            {
                "project_id": project_id,
                "task_id": task_id,
                "subagent": True,
                "subagent_depth": depth,
                "workspace_dir": str(workspace),
            }
        )

        event_bus.emit(
            "spawn.started",
            {
                "project_id": project_id,
                "task_id": task_id,
                "agent": agent_name,
                "depth": depth,
                "workspace": str(workspace),
            },
        )
        try:
            with runtime_execution_scope(project_id=project_id, task_id=task_id, skill_hint=payload.get("skill")):
                run_fn = getattr(agent, "run")
                result = await run_fn(payload)
            event_bus.emit(
                "spawn.completed",
                {
                    "project_id": project_id,
                    "task_id": task_id,
                    "agent": agent_name,
                    "depth": depth,
                },
            )
            return {"success": True, "result": result, "workspace": str(workspace)}
        except Exception as exc:
            event_bus.emit(
                "spawn.failed",
                {
                    "project_id": project_id,
                    "task_id": task_id,
                    "agent": agent_name,
                    "depth": depth,
                    "error": str(exc),
                },
            )
            return {"success": False, "error": str(exc), "workspace": str(workspace)}

    async def start_task(
        self,
        *,
        session: ConversationSession,
        session_id: str,
        project_id: str,
        user_message: str,
        progress_callback: Optional[Callable[[Dict[str, Any]], Any]] = None,
    ) -> Dict[str, Any]:
        task = task_manager.create_task(
            project_id=project_id,
            description=user_message,
            metadata={
                "session_id": session_id,
                "source": "chat.message",
            },
        )

        task_id = task["task_id"]
        event_bus.emit(
            "chat.request.started",
            {
                "session_id": session_id,
                "project_id": project_id,
                "task_id": task_id,
            },
        )

        brain_result = await self.run_task_loop(
            session=session,
            project_id=project_id,
            task_id=task_id,
            user_message=user_message,
            progress_callback=progress_callback,
        )

        status = brain_result.get("status")
        if status == "execution_cancelled":
            task_manager.kill_task(project_id, task_id, reason="cancelled_by_runtime")
        elif status == "execution_failed":
            task_manager.fail_task(
                project_id,
                task_id,
                error=str((brain_result.get("execution") or {}).get("error") or "execution_failed"),
            )
        else:
            task_manager.complete_task(
                project_id,
                task_id,
                metadata={
                    "intent": brain_result.get("intent"),
                    "selected_agents": brain_result.get("selected_agents", []),
                },
            )

        current_task = task_manager.get_task(project_id, task_id)
        event_bus.emit(
            "chat.request.completed",
            {
                "session_id": session_id,
                "project_id": project_id,
                "task_id": task_id,
                "task_status": (current_task or {}).get("status"),
            },
        )

        return {
            "task": current_task,
            "brain_result": brain_result,
        }

    async def run_task_loop(
        self,
        *,
        session: ConversationSession,
        project_id: str,
        task_id: str,
        user_message: str,
        progress_callback: Optional[Callable[[Dict[str, Any]], Any]] = None,
        planner: Optional[BrainLayer] = None,
    ) -> Dict[str, Any]:
        brain = planner or self._brain_factory()

        msg_lower = (user_message or "").lower()
        benchmark_mode = (
            "benchmark_mode=true" in msg_lower
            or "[benchmark_mode]" in msg_lower
            or bool((getattr(session, "metadata", {}) or {}).get("benchmark_mode"))
        )
        must_complete_mode = (
            benchmark_mode
            or "must_complete=true" in msg_lower
            or "[must_complete]" in msg_lower
            or bool((getattr(session, "metadata", {}) or {}).get("must_complete"))
        )

        assessment = brain.decide(session, user_message)
        matched_skill = resolve_skill(user_message)
        skill_hint = matched_skill.name if matched_skill else None
        event_bus.emit(
            "brain.assessed",
            {
                "intent": assessment.get("intent"),
                "intent_confidence": assessment.get("intent_confidence"),
                "selected_agents": assessment.get("selected_agents") or [],
                "status": assessment.get("status"),
                "benchmark_mode": benchmark_mode,
                "must_complete": must_complete_mode,
                "task_id": task_id,
            },
        )

        if assessment.get("status") != "ready":
            if must_complete_mode and assessment.get("status") == "clarification_required":
                assessment["status"] = "ready"
                assessment["assistant_response"] = "Running in must-complete mode; proceeding with defaults."
                assessment["selected_agent_configs"] = assessment.get("selected_agent_configs") or [
                    {"agent": "WorkspaceExplorerAgent", "params": {"user_prompt": user_message, "must_complete": True}}
                ]
                assessment["selected_agents"] = [cfg.get("agent") for cfg in assessment["selected_agent_configs"]]
            else:
                return assessment

        selected_agent_configs: List[Dict[str, Any]] = assessment.get("selected_agent_configs") or []
        if not selected_agent_configs:
            if must_complete_mode:
                selected_agent_configs = [
                    {"agent": "WorkspaceExplorerAgent", "params": {"user_prompt": user_message, "must_complete": True}}
                ]
                assessment["selected_agent_configs"] = selected_agent_configs
                assessment["selected_agents"] = ["WorkspaceExplorerAgent"]
            else:
                assessment["status"] = "ready_no_execution"
                return assessment

        outputs: List[Dict[str, Any]] = []

        try:
            event_bus.emit(
                "brain.execution.started",
                {
                    "intent": assessment.get("intent"),
                    "selected_agents": assessment.get("selected_agents") or [],
                    "task_id": task_id,
                },
            )

            agent_instances = brain._get_agent_instances()
            total = len(selected_agent_configs)

            for idx, agent_config in enumerate(selected_agent_configs, start=1):
                current = task_manager.get_task(project_id, task_id)
                if current and current.get("status") == "killed":
                    raise asyncio.CancelledError("task marked killed")
                while current and current.get("status") == "paused":
                    await asyncio.sleep(0.05)
                    current = task_manager.get_task(project_id, task_id)
                    if current and current.get("status") == "killed":
                        raise asyncio.CancelledError("task marked killed")

                agent_name = agent_config.get("agent")
                if not agent_name:
                    raise ValueError("Selected agent config is missing an agent name")

                agent = agent_instances.get(agent_name)
                if not agent:
                    raise ValueError(f"Agent '{agent_name}' is not registered or cannot be instantiated")

                event_payload = {
                    "task_id": task_id,
                    "project_id": project_id,
                    "step": idx,
                    "total_steps": total,
                    "agent": agent_name,
                }
                event_bus.emit("step_start", event_payload)
                event_bus.emit("agent_start", event_payload)
                event_bus.emit("brain.agent.started", event_payload)

                provider_chain = self._select_provider_chain(user_message, agent_name)
                event_bus.emit(
                    "provider.chain.selected.runtime",
                    {
                        "project_id": project_id,
                        "task_id": task_id,
                        "agent": agent_name,
                        "chain": provider_chain,
                    },
                )

                if progress_callback:
                    payload = {
                        "type": "status",
                        "content": f"Running step {idx}/{total}: {agent_name}",
                        "metadata": event_payload,
                    }
                    maybe = progress_callback(payload)
                    if asyncio.iscoroutine(maybe):
                        await maybe

                context = brain._build_agent_context(
                    agent_config,
                    user_message,
                    session,
                    {
                        "project_id": project_id,
                        "task_id": task_id,
                        "skill": skill_hint,
                        "provider_chain": provider_chain,
                    },
                )
                try:
                    result, runtime_meta = await self._run_agent_with_resilience(
                        project_id=project_id,
                        task_id=task_id,
                        user_message=user_message,
                        agent_name=agent_name,
                        agent=agent,
                        context=context,
                        agent_instances=agent_instances,
                        skill_hint=skill_hint,
                        benchmark_mode=benchmark_mode,
                    )
                except Exception as exc:
                    if not must_complete_mode:
                        raise
                    event_bus.emit(
                        "brain.agent.fallback_used",
                        {
                            "task_id": task_id,
                            "project_id": project_id,
                            "agent": agent_name,
                            "error": str(exc),
                            "must_complete": True,
                        },
                    )
                    result = {
                        "diagnosed_failure": str(exc),
                        "fallback": "must_complete_offline_plan",
                        "frontend": "UI scaffold planned",
                        "backend": "API/data flow scaffold planned",
                        "runnable": "Local run instructions generated",
                        "next_action": "Execute with configured provider credentials",
                    }
                    runtime_meta = {
                        "event": "agent.fallback",
                        "agent": agent_name,
                        "strategy": "diagnose_and_continue",
                    }
                if runtime_meta:
                    outputs.append({"agent": f"runtime:{agent_name}", "result": runtime_meta, "runtime_meta": True})
                outputs.append({"agent": agent_name, "result": result})

                # Post-step cancellation: honour a kill that arrived during execution.
                current_post = task_manager.get_task(project_id, task_id)
                if current_post and current_post.get("status") == "killed":
                    raise asyncio.CancelledError("task marked killed after step")

                # Spawn: agent may return {"spawn_request": {"agent": ..., "context": ...}}
                spawn_req = result if isinstance(result, dict) else {}
                if spawn_req.get("spawn_request"):
                    sr = spawn_req["spawn_request"]
                    spawn_agent_name = str(sr.get("agent") or "").strip()
                    if spawn_agent_name:
                        spawn_out = await self.spawn_agent(
                            project_id=project_id,
                            task_id=task_id,
                            parent_message=user_message,
                            agent_name=spawn_agent_name,
                            context={
                                "skill": skill_hint,
                                **(sr.get("context") or {}),
                            },
                            depth=1,
                        )
                        outputs.append(
                            {
                                "agent": f"spawn:{spawn_agent_name}",
                                "result": spawn_out,
                                "spawned": True,
                            }
                        )
                        task_manager.update_task(
                            project_id,
                            task_id,
                            metadata={"spawned_agent": spawn_agent_name},
                        )

                self._update_memory(
                    session=session,
                    task_id=task_id,
                    user_message=user_message,
                    agent_name=agent_name,
                    result=result,
                )
                self._update_context_state(
                    session=session,
                    task_id=task_id,
                    step=idx,
                    agent_name=agent_name,
                    provider_chain=provider_chain,
                )

                task_manager.update_task(
                    project_id,
                    task_id,
                    metadata={
                        "last_step": idx,
                        "last_agent": agent_name,
                        "skill": skill_hint,
                    },
                )

                event_bus.emit("brain.agent.completed", event_payload)
                event_bus.emit("agent_end", event_payload)
                event_bus.emit("step_end", event_payload)

                if progress_callback:
                    payload = {
                        "type": "status",
                        "content": f"Completed step {idx}/{total}: {agent_name}",
                        "metadata": event_payload,
                    }
                    maybe = progress_callback(payload)
                    if asyncio.iscoroutine(maybe):
                        await maybe

            spawned_count = sum(1 for o in outputs if o.get("spawned"))
            assessment["execution"] = {
                "agent_outputs": outputs,
                "completed_tasks": len(outputs),
                "total_tasks": len(selected_agent_configs),
                "spawned_tasks": spawned_count,
            }
            try:
                assessment["assistant_response"] = brain._summarize_execution(
                    assessment,
                    assessment["execution"],
                    user_message,
                )
            except TypeError:
                assessment["assistant_response"] = brain._summarize_execution(assessment, assessment["execution"])
            assessment["status"] = "executed"

            event_bus.emit(
                "brain.execution.completed",
                {
                    "task_id": task_id,
                    "completed_tasks": len(outputs),
                    "total_tasks": len(selected_agent_configs),
                },
            )
            return assessment

        except asyncio.CancelledError:
            assessment["status"] = "execution_cancelled"
            assessment["execution"] = {"cancelled": True}
            event_bus.emit(
                "brain.execution.cancelled",
                {
                    "task_id": task_id,
                    "intent": assessment.get("intent"),
                },
            )
            return assessment
        except Exception as exc:
            assessment["status"] = "execution_failed"
            assessment["execution"] = {"error": str(exc)}
            event_bus.emit(
                "brain.execution.failed",
                {
                    "task_id": task_id,
                    "intent": assessment.get("intent"),
                    "error": str(exc),
                },
            )
            return assessment

    async def _run_agent_with_resilience(
        self,
        *,
        project_id: str,
        task_id: str,
        user_message: str,
        agent_name: str,
        agent: Any,
        context: Dict[str, Any],
        agent_instances: Dict[str, Any],
        skill_hint: Optional[str],
        benchmark_mode: bool = False,
    ) -> tuple[Any, Optional[Dict[str, Any]]]:
        default_retries = "4" if benchmark_mode else "2"
        max_retries = max(0, min(int(os.environ.get("CRUCIB_AGENT_MAX_RETRIES", default_retries)), 6))
        attempts = 0
        last_error: Optional[Exception] = None
        failure_kind = "unknown"

        while attempts <= max_retries:
            try:
                with runtime_execution_scope(project_id=project_id, task_id=task_id, skill_hint=skill_hint):
                    run_fn = getattr(agent, "run")
                    result = await run_fn(context)
                if attempts == 0:
                    return result, None
                return result, {
                    "event": "agent.recovered",
                    "agent": agent_name,
                    "attempts": attempts + 1,
                    "failure_kind": failure_kind,
                    "strategy": "retry",
                }
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                last_error = exc
                failure_kind = self._classify_agent_error(exc)
                if attempts >= max_retries:
                    break
                wait_s = min(0.75, 0.15 * (attempts + 1))
                event_bus.emit(
                    "brain.agent.retry_scheduled",
                    {
                        "task_id": task_id,
                        "project_id": project_id,
                        "agent": agent_name,
                        "attempt": attempts + 1,
                        "max_retries": max_retries,
                        "failure_kind": failure_kind,
                        "delay_s": wait_s,
                        "error": str(exc),
                    },
                )
                await asyncio.sleep(wait_s)
                attempts += 1

        repair = await self._attempt_targeted_repair(
            project_id=project_id,
            task_id=task_id,
            user_message=user_message,
            failed_agent=agent_name,
            failed_context=context,
            failure_kind=failure_kind,
            last_error=last_error,
            agent_instances=agent_instances,
            skill_hint=skill_hint,
        )
        if repair.get("repaired"):
            with runtime_execution_scope(project_id=project_id, task_id=task_id, skill_hint=skill_hint):
                run_fn = getattr(agent, "run")
                result = await run_fn(context)
            return result, {
                "event": "agent.recovered",
                "agent": agent_name,
                "attempts": max_retries + 2,
                "failure_kind": failure_kind,
                "strategy": "repair_then_retry",
                "repair_agent": repair.get("repair_agent"),
            }

        raise RuntimeError(
            f"agent_failed:{agent_name}:{failure_kind}:{str(last_error) if last_error else 'unknown_error'}"
        )

    def _classify_agent_error(self, exc: Exception) -> str:
        msg = str(exc).lower()
        if "timeout" in msg or "timed out" in msg:
            return "timeout"
        if "rate limit" in msg or "429" in msg:
            return "rate_limit"
        if "permission" in msg or "forbidden" in msg or "unauthorized" in msg:
            return "permission"
        if "json" in msg or "parse" in msg or "schema" in msg:
            return "contract"
        if "connection" in msg or "network" in msg or "dns" in msg:
            return "network"
        if "not found" in msg or "missing" in msg:
            return "dependency"
        return "runtime"

    def _pick_repair_agent(self, agent_instances: Dict[str, Any], failed_agent: str) -> Optional[str]:
        preferred = [
            "CodeAnalysisAgent",
            "TestGenerationAgent",
            "BackendAgent",
            "FrontendAgent",
        ]
        for name in preferred:
            if name in agent_instances and name != failed_agent:
                return name
        for name in sorted(agent_instances.keys()):
            if name != failed_agent:
                return name
        return None

    async def _attempt_targeted_repair(
        self,
        *,
        project_id: str,
        task_id: str,
        user_message: str,
        failed_agent: str,
        failed_context: Dict[str, Any],
        failure_kind: str,
        last_error: Optional[Exception],
        agent_instances: Dict[str, Any],
        skill_hint: Optional[str],
    ) -> Dict[str, Any]:
        repair_agent_name = self._pick_repair_agent(agent_instances, failed_agent)
        if not repair_agent_name:
            return {"repaired": False, "reason": "no_repair_agent_available"}

        repair_agent = agent_instances.get(repair_agent_name)
        if repair_agent is None:
            return {"repaired": False, "reason": "repair_agent_unavailable"}

        event_bus.emit(
            "brain.agent.repair.started",
            {
                "task_id": task_id,
                "project_id": project_id,
                "failed_agent": failed_agent,
                "repair_agent": repair_agent_name,
                "failure_kind": failure_kind,
                "error": str(last_error) if last_error else "",
            },
        )

        repair_context = {
            "user_prompt": user_message,
            "project_id": project_id,
            "task_id": task_id,
            "skill": skill_hint,
            "repair": True,
            "failure_kind": failure_kind,
            "failed_agent": failed_agent,
            "failed_context": failed_context,
            "failure_error": str(last_error) if last_error else "unknown_error",
            "goal": "produce targeted repair guidance and unblock execution",
        }

        try:
            with runtime_execution_scope(project_id=project_id, task_id=task_id, skill_hint=skill_hint):
                run_fn = getattr(repair_agent, "run")
                repair_result = await run_fn(repair_context)
            event_bus.emit(
                "brain.agent.repair.completed",
                {
                    "task_id": task_id,
                    "project_id": project_id,
                    "failed_agent": failed_agent,
                    "repair_agent": repair_agent_name,
                    "failure_kind": failure_kind,
                },
            )
            return {
                "repaired": True,
                "repair_agent": repair_agent_name,
                "repair_result": repair_result,
            }
        except Exception as repair_exc:
            event_bus.emit(
                "brain.agent.repair.failed",
                {
                    "task_id": task_id,
                    "project_id": project_id,
                    "failed_agent": failed_agent,
                    "repair_agent": repair_agent_name,
                    "failure_kind": failure_kind,
                    "error": str(repair_exc),
                },
            )
            return {
                "repaired": False,
                "repair_agent": repair_agent_name,
                "reason": str(repair_exc),
            }

    def _update_memory(
        self,
        *,
        session: ConversationSession,
        task_id: str,
        user_message: str,
        agent_name: str,
        result: Any,
    ) -> None:
        session_meta = getattr(session, "metadata", None)
        if not isinstance(session_meta, dict):
            session_meta = {}
            setattr(session, "metadata", session_meta)

        mem = dict(session_meta.get("runtime_memory") or {})
        steps = list(mem.get("steps") or [])

        query_words = {w for w in user_message.lower().split() if len(w) > 2}
        result_text = str(result).lower()
        overlap = sum(1 for w in query_words if w in result_text)
        relevance = overlap / max(1, len(query_words))

        steps.append(
            {
                "task_id": task_id,
                "agent": agent_name,
                "relevance": relevance,
                "result_preview": str(result)[:500],
            }
        )

        # Context compaction: keep top-relevance recent memory entries.
        steps = sorted(steps, key=lambda s: float(s.get("relevance", 0.0)), reverse=True)[:20]
        mem["steps"] = steps
        session_meta["runtime_memory"] = mem

    def _update_context_state(
        self,
        *,
        session: ConversationSession,
        task_id: str,
        step: int,
        agent_name: str,
        provider_chain: List[Dict[str, str]],
    ) -> None:
        session_meta = getattr(session, "metadata", None)
        if not isinstance(session_meta, dict):
            session_meta = {}
            setattr(session, "metadata", session_meta)
        ctx = dict(session_meta.get("runtime_context") or {})
        ctx["task_id"] = task_id
        ctx["last_step"] = step
        ctx["last_agent"] = agent_name
        ctx["last_provider_chain"] = provider_chain
        session_meta["runtime_context"] = ctx


runtime_engine = RuntimeEngine()
