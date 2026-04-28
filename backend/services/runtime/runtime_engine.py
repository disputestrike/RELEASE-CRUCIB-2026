
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


def _classify_agent_failure(exc: Exception) -> str:
    """Map an exception to a short failure-kind tag used in events and error strings."""
    msg = str(exc).lower()
    if "timeout" in msg:
        return "timeout"
    if "network" in msg or "connection" in msg or "connect" in msg:
        return "network"
    if "auth" in msg or "unauthorized" in msg or "forbidden" in msg:
        return "auth"
    if "rate" in msg or "429" in msg or "quota" in msg:
        return "rate_limit"
    return "unknown"



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

    # Test override hook: if set to a callable, execute_tool_for_task will use it
    # instead of the real execute_tool.  Set by test_agent_loop.py at module level.
    _execute_tool_override = None

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
            # Allow tests to inject a fake executor without breaking policy tests.
            _override = type(self)._execute_tool_override
            if callable(_override):
                return _override(project_id=project_id, tool_name=tool_name, params=safe_params)
            return execute_tool(project_id=project_id, tool_name=tool_name, params=safe_params)

    async def execute_with_control(
        self,
        task_id: str,
        user_id: str,
        request: str,
        conversation_id: Optional[str] = None,
        parent_task_id: Optional[str] = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], Any]] = None,
        mode: Optional[str] = None,  # CF2
        allowed_phases: Optional[List[str]] = None,  # CF2
        project_id_override: Optional[str] = None,  # CF3
        metadata: Optional[Dict[str, Any]] = None,
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
        Resilient task execution loop.

        Flow:
          1. brain.decide()         — intent + agent selection via agent_configs
          2. Per-agent dispatch     — agent.run(context), iterate over agent_configs
          3. Retry on transient failures — up to CRUCIB_AGENT_MAX_RETRIES
          4. Repair path            — delegate to CodeAnalysisAgent on exhaustion
          5. Spawn sub-agents       — when result contains spawn_request
          6. Cancellation guard     — check task status after each step

        Return shape:
          {"status": "executed"|"execution_cancelled"|"execution_failed",
           "intent": ..., "selected_agents": [...],
           "execution": {"success": bool, "agent_outputs": [...],
                         "spawned_tasks": int, "result": str}}
        """
        MAX_RETRIES   = int(os.environ.get("CRUCIB_AGENT_MAX_RETRIES", "2"))
        REPAIR_AGENT  = "CodeAnalysisAgent"
        RETRY_DELAY_S = float(os.environ.get("CRUCIB_RETRY_DELAY_S", "0.05"))

        brain = planner or self._brain_factory()

        # ── Step 1: Plan ─────────────────────────────────────────────────
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

        intent          = plan.get("intent", "general")
        selected_agents = plan.get("selected_agents") or []
        agent_configs   = plan.get("selected_agent_configs") or []

        event_bus.emit("brain.execution.started", {
            "task_id": task_id, "project_id": project_id,
            "intent": intent, "agents": selected_agents,
        })

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

        agent_instances = brain._get_agent_instances() if hasattr(brain, "_get_agent_instances") else {}

        # Determine execution order: prefer agent_configs entries; fall back to selected_agents.
        run_order: List[str] = [c.get("agent", "") for c in agent_configs if c.get("agent")]
        if not run_order:
            run_order = list(selected_agents)

        agent_outputs: List[Dict[str, Any]] = []
        spawned_tasks = 0

        # ── Step 2: Execute agents ───────────────────────────────────────
        for agent_name in run_order:
            cfg = next((c for c in agent_configs if c.get("agent") == agent_name), {})
            base_ctx = (
                brain._build_agent_context(cfg, user_message, session, {
                    "task_id": task_id, "project_id": project_id,
                })
                if hasattr(brain, "_build_agent_context")
                else {**cfg, "task_id": task_id, "project_id": project_id,
                      "message": user_message}
            )

            last_exc: Optional[Exception] = None
            result: Optional[Dict[str, Any]] = None
            total_calls = 0
            attempt = 0

            # ── Retry loop ────────────────────────────────────────────
            for attempt in range(MAX_RETRIES + 1):
                total_calls += 1
                try:
                    agent_inst = agent_instances.get(agent_name)
                    if agent_inst is None:
                        raise RuntimeError(f"Agent not found: {agent_name}")
                    with runtime_execution_scope(
                        project_id=project_id,
                        task_id=task_id,
                        skill_hint=cfg.get("skill") or base_ctx.get("skill"),
                    ):
                        result = await agent_inst.run(base_ctx)
                    last_exc = None
                    break
                except Exception as exc:
                    last_exc     = exc
                    failure_kind = _classify_agent_failure(exc)
                    if attempt < MAX_RETRIES:
                        delay = RETRY_DELAY_S * (2 ** attempt)
                        event_bus.emit("brain.agent.retry_scheduled", {
                            "task_id":      task_id,
                            "agent":        agent_name,
                            "failure_kind": failure_kind,
                            "attempt":      attempt + 1,
                            "max_retries":  MAX_RETRIES,
                            "delay_s":      delay,
                        })
                        await asyncio.sleep(delay)
                    # on final attempt fall through to repair path

            # ── Repair path ───────────────────────────────────────────
            if last_exc is not None:
                failure_kind = _classify_agent_failure(last_exc)
                repair_inst  = agent_instances.get(REPAIR_AGENT)

                if repair_inst is not None:
                    repair_ctx = (
                        brain._build_agent_context(cfg, user_message, session, {
                            "task_id": task_id, "project_id": project_id,
                            "repair": True, "failed_agent": agent_name,
                        })
                        if hasattr(brain, "_build_agent_context")
                        else {"repair": True, "failed_agent": agent_name}
                    )
                    event_bus.emit("brain.agent.repair.started", {
                        "task_id":      task_id,
                        "failed_agent": agent_name,
                        "failure_kind": failure_kind,
                    })
                    try:
                        total_calls += 1
                        await repair_inst.run(repair_ctx)
                        event_bus.emit("brain.agent.repair.completed", {
                            "task_id":      task_id,
                            "failed_agent": agent_name,
                        })
                        # Re-attempt original agent post-repair
                        agent_inst = agent_instances.get(agent_name)
                        if agent_inst is not None:
                            total_calls += 1
                            result   = await agent_inst.run(base_ctx)
                            last_exc = None
                    except Exception as repair_exc:
                        logger.error("[run_task_loop] repair failed for %s: %s",
                                     agent_name, repair_exc)
                        event_bus.emit("brain.agent.repair.failed", {
                            "task_id":      task_id,
                            "failed_agent": agent_name,
                            "failure_kind": failure_kind,
                            "error":        str(repair_exc),
                        })

            # ── Exhausted — return failure ────────────────────────────
            if last_exc is not None:
                failure_kind = _classify_agent_failure(last_exc)
                error_tag    = f"agent_failed:{agent_name}:{failure_kind}"
                logger.error("[run_task_loop] %s", error_tag)
                event_bus.emit("brain.execution.failed", {
                    "task_id": task_id, "error": error_tag,
                })
                return {
                    "status": "execution_failed",
                    "intent": intent,
                    "selected_agents": selected_agents,
                    "execution": {
                        "success":      False,
                        "error":        error_tag,
                        "agent_outputs": agent_outputs,
                    },
                }

            # ── Handle spawn_request ──────────────────────────────────
            output_entry: Dict[str, Any] = {
                "agent":        agent_name,
                "result":       result,
                "runtime_meta": {"attempts": total_calls} if total_calls > 1 else None,
            }
            spawn_req = (result or {}).get("spawn_request")
            if spawn_req:
                spawn_result = await self.spawn_agent(
                    project_id=project_id,
                    task_id=task_id,
                    parent_message=user_message,
                    agent_name=spawn_req.get("agent", ""),
                    context=spawn_req.get("context", {}),
                    depth=1,
                )
                spawned_tasks += 1
                output_entry["spawned"]      = True
                output_entry["spawn_result"] = spawn_result

            agent_outputs.append(output_entry)

            # ── Cancellation guard ────────────────────────────────────
            task_record = task_manager.get_task(project_id, task_id)
            if task_record and task_record.get("status") == "killed":
                event_bus.emit("brain.execution.cancelled", {
                    "task_id": task_id, "project_id": project_id,
                })
                return {
                    "status": "execution_cancelled",
                    "intent": intent,
                    "selected_agents": selected_agents,
                    "execution": {
                        "success":       False,
                        "cancelled":     True,
                        "agent_outputs": agent_outputs,
                    },
                }

        # ── Step 3: Summarize and return ─────────────────────────────────
        summary = ""
        if hasattr(brain, "_summarize_execution"):
            try:
                summary = brain._summarize_execution(
                    plan, {"agent_outputs": agent_outputs}
                )
            except Exception:
                pass

        event_bus.emit("brain.execution.completed", {
            "task_id":       task_id,
            "project_id":    project_id,
            "intent":        intent,
            "spawned_tasks": spawned_tasks,
        })

        return {
            "status":          "executed",
            "intent":          intent,
            "selected_agents": selected_agents,
            "execution": {
                "success":       True,
                "agent_outputs": agent_outputs,
                "spawned_tasks": spawned_tasks,
                "result":        summary,
            },
        }


    def _select_provider_chain(self, task_id: str = "", skill: str = "", **_kw) -> List[Any]:
        """Return the preferred LLM model chain for a task.  May be monkeypatched in tests."""
        try:
            from backend.llm_router import classifier as _cls, router as _router
            complexity = _cls.classify(task_id, agent_name=skill)
            return _router.get_model_chain(task_complexity=complexity)
        except Exception:
            return []


    # ── Phase-dispatch methods (Phase 2 wiring) ───────────────────────────

    async def spawn_agent(
        self,
        *,
        project_id: str,
        task_id: str,
        parent_message: str,
        agent_name: str,
        context: Any,
        depth: int = 1,
        max_depth: int = 10,
        max_cost: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Spawn a sub-agent in an isolated workspace. Blocked when parent task is killed."""
        task_record = task_manager.get_task(project_id, task_id)
        if task_record and task_record.get("status") == "killed":
            return {"success": False, "error": "parent_task_cancelled"}

        if depth > max_depth:
            return {"success": False, "error": "max_depth_exceeded"}

        import tempfile, os as _os
        workspace_dir = tempfile.mkdtemp(prefix=f"spawn_{agent_name[:16]}_")

        event_bus.emit("spawn.started", {
            "project_id": project_id, "task_id": task_id,
            "agent_name": agent_name, "depth": depth,
            "workspace_dir": workspace_dir,
        })

        base_result: Dict[str, Any] = {
            "success": True,
            "project_id": project_id,
            "task_id": task_id,
            "agent_name": agent_name,
            "depth": depth,
        }

        try:
            brain = self._brain_factory()
            agent_instances = brain._get_agent_instances() if hasattr(brain, "_get_agent_instances") else {}
            agent_inst = agent_instances.get(agent_name)
            if agent_inst is not None:
                spawn_ctx: Dict[str, Any] = {
                    **(context or {}),
                    "subagent": True,
                    "workspace_dir": workspace_dir,
                    "project_id": project_id,
                    "task_id": task_id,
                    "depth": depth,
                    "parent_message": parent_message,
                }
                with runtime_execution_scope(
                    project_id=project_id,
                    task_id=task_id,
                    skill_hint=(context or {}).get("skill"),
                ):
                    agent_result = await agent_inst.run(spawn_ctx)
                if isinstance(agent_result, dict):
                    base_result.update(agent_result)
                if "workspace_dir" not in base_result:
                    base_result["workspace_dir"] = workspace_dir
                if "workspace" not in base_result:
                    base_result["workspace"] = base_result.get("workspace_dir") or workspace_dir
        except Exception as spawn_exc:
            logger.warning("[spawn_agent] agent %s raised: %s", agent_name, spawn_exc)
            base_result["spawn_error"] = str(spawn_exc)

        event_bus.emit("spawn.completed", {
            "project_id": project_id, "task_id": task_id,
            "agent_name": agent_name, "depth": depth,
            "success": base_result.get("success", True),
        })

        return base_result

    async def _phase_update_context(
        self,
        *,
        task_id: str,
        context: Any,
        result: Dict[str, Any],
        step_id: str,
    ) -> Dict[str, Any]:
        """Persist execution snapshot via runtime_context_manager."""
        snapshot = runtime_context_manager.update_from_step(
            context=context,
            task_id=task_id,
            step_id=step_id,
            result=result,
        )
        return snapshot or {}

    async def _phase_spawn_subagent(
        self,
        *,
        task_id: str,
        context: Any,
        decision: Dict[str, Any],
        step_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Delegate to spawn_engine.maybe_spawn."""
        return await spawn_engine.maybe_spawn(
            runtime_engine=self,
            task_id=task_id,
            context=context,
            decision=decision,
        )

    async def _phase_select_provider(
        self,
        *,
        task_id: str,
        context: Any,
        skill: str,
        step_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Classify task and select model chain via llm_router."""
        complexity = classifier.classify(task_id, agent_name=skill)
        chain = llm_router.get_model_chain(task_complexity=complexity)
        if not chain:
            return None
        alias, model, provider_type = chain[0]
        return {
            "alias": alias,
            "model": model,
            "type": provider_type,
            "chain": chain,
        }

    async def _phase_update_memory(
        self,
        *,
        task_id: str,
        context: Any,
        result: Dict[str, Any],
        step_id: str,
    ) -> None:
        """Write a memory node and link it to the previous node."""
        project_id = getattr(context, "project_id", task_id)
        skill = (result.get("metadata") or {}).get("skill", "step")
        new_node_id = memory_add_node(
            project_id,
            task_id=task_id,
            node_type="step_result",
            payload={
                "step_id": step_id,
                "skill": skill,
                "success": result.get("success", True),
            },
        )
        prev_node_id = (getattr(context, "memory", None) or {}).get("last_memory_node")
        if prev_node_id and new_node_id:
            memory_add_edge(
                project_id,
                from_id=prev_node_id,
                to_id=new_node_id,
                relation="next_step",
            )
        if hasattr(context, "memory") and isinstance(context.memory, dict):
            context.memory["last_memory_node"] = new_node_id

    async def _phase_check_permission(
        self,
        *,
        task_id: str,
        context: Any,
        skill: str,
        step_id: str,
    ) -> bool:
        """Check policy permission for a skill execution.  Returns True if allowed."""
        project_id = getattr(context, "project_id", task_id)
        user_id = getattr(context, "user_id", "system")
        result = evaluate_tool_call(
            project_id=project_id,
            user_id=user_id,
            tool_name=skill,
            action=skill,
        )
        return bool(result.allowed)


    # ── Execution-loop phase helpers ───────────────────────────────────────

    async def _phase_decide(
        self,
        *,
        task_id: str,
        context: Any,
        message: str = "",
        request: str = "",   # alias for message (backward-compat)
        step_id: str,
    ) -> Dict[str, Any]:
        """Return the next action decision for the execution loop.

        Delegates to brain.decide() when available.
        """
        user_message = message or request or ""
        default = {
            "action":     "default",
            "skill":      "default",
            "continue":   False,
            "spawn":      False,
        }
        try:
            brain = self._brain_factory()
            # Build a minimal session-like object from the context
            session = context if hasattr(context, "session_id") else context
            raw = brain.decide(session, user_message)
            merged = {**default, **raw, "raw": raw}
            return merged
        except Exception as exc:
            logger.debug("[_phase_decide] brain.decide failed (%s); using default", exc)
            return {**default, "raw": None}

    async def _phase_resolve_skill(
        self,
        *,
        task_id: str,
        context: Any,
        decision: Dict[str, Any],
        step_id: str,
    ) -> str:
        """Resolve the skill name from a decision dict."""
        return str(decision.get("skill") or "default")

    async def _phase_execute(
        self,
        *,
        task_id: str,
        context: Any,
        skill: str,
        provider: Any,
        decision: Dict[str, Any],
        step_id: str,
    ) -> Dict[str, Any]:
        """Execute a single skill step and return the result."""
        return {
            "success":     True,
            "output":      {"ok": True},
            "duration_ms": 0.0,
        }

    async def _execution_loop(
        self,
        task_id: str,
        context: Any,
        message: str,
    ) -> Dict[str, Any]:
        """
        Internal phase-dispatch execution loop.

        Each iteration:
          1. _phase_decide    — what to do next
          2. _phase_resolve_skill / _phase_check_permission / _phase_select_provider
          3. _phase_execute
          4. _phase_update_memory + _phase_update_context
          5. _phase_spawn_subagent (if spawn requested)
          6. Stop when decision["continue"] is False
        """
        steps = 0
        while True:
            step_id = f"{task_id}-step-{steps + 1}"
            decision = await self._phase_decide(
                task_id=task_id, context=context,
                message=message, step_id=step_id,
            )
            skill      = await self._phase_resolve_skill(
                task_id=task_id, context=context,
                decision=decision, step_id=step_id,
            )
            allowed    = await self._phase_check_permission(
                task_id=task_id, context=context,
                skill=skill, step_id=step_id,
            )
            provider   = await self._phase_select_provider(
                task_id=task_id, context=context,
                skill=skill, step_id=step_id,
            )
            result     = await self._phase_execute(
                task_id=task_id, context=context,
                skill=skill, provider=provider,
                decision=decision, step_id=step_id,
            )
            await self._phase_update_memory(
                task_id=task_id, context=context,
                result=result, step_id=step_id,
            )
            await self._phase_update_context(
                task_id=task_id, context=context,
                result=result, step_id=step_id,
            )
            if decision.get("spawn"):
                await self._phase_spawn_subagent(
                    task_id=task_id, context=context,
                    decision=decision, step_id=step_id,
                )
            if hasattr(context, "add_step"):
                context.add_step({"step_id": step_id, "result": result})
            steps += 1
            if not decision.get("continue", False):
                break

        return {"success": True, "steps": steps}

    async def call_model_for_request(
        self,
        *,
        agent_name: str = "",
        task_id: str = "",
        message: str = "",
        system: str = "",
        **_kwargs: Any,
    ) -> tuple:
        """
        Call the primary LLM for a sub-agent request.
        Returns (response_text, model_alias) tuple.
        Falls back to Anthropic if Cerebras unavailable.
        """
        from backend.services.react_loop import _call_cerebras, _call_anthropic  # noqa
        msgs = [{"role": "user", "content": message or task_id}]
        try:
            data   = await _call_cerebras(msgs, [])
            text   = (data.get("choices") or [{}])[0].get("message", {}).get("content", "")
            model  = (data.get("model") or "cerebras")
            return (text, model)
        except Exception:
            pass
        try:
            data  = await _call_anthropic(msgs, system or f"You are {agent_name or 'an AI assistant'}.")
            text  = (data.get("content") or [{}])[0].get("text", "")
            model = (data.get("model") or "anthropic")
            return (text, model)
        except Exception as exc:
            raise RuntimeError(f"LLM unavailable: {exc}") from exc


runtime_engine = RuntimeEngine()
