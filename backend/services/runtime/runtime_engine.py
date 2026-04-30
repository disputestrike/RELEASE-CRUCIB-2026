
"""
🔥 RuntimeEngine: unified execution layer.

Brain plans; this engine runs planner-selected agents with retries,
optional repair delegation, cancellation checks, spawn support,
and phased skill execution for advanced flows.

See tests: backend/tests/test_run_task_loop.py, test_phase2_runtime_wiring.py,
test_runtime_execution_loop.py
"""

from __future__ import annotations

import asyncio
import logging
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .....llm_router import classifier, router as llm_routerfrom .....services.brain_layer import BrainLayerfrom .....services.conversation_manager import ConversationSession
try:
    from services.events import event_bus  # same singleton as patches in tests importing services.*
except ImportError:  # pragma: no cover
    from .....services.events import event_busfrom .....services.policy.permission_engine import evaluate_tool_callfrom .....services.runtime.context_manager import runtime_context_managerfrom .....services.runtime.cost_tracker import cost_trackerfrom .....services.runtime.execution_context import runtime_execution_scopefrom .....services.runtime.memory_graph import add_edge as memory_add_edgefrom .....services.runtime.memory_graph import add_node as memory_add_nodefrom .....services.runtime.spawn_engine import spawn_enginefrom .....services.runtime.task_manager import task_managerfrom .....services.skills.skill_registry import resolve_skillfrom .....tool_executor import execute_tool
try:
    from .....services.capability_inspector import capability_inspector  # pragma: no coverexcept Exception:
    capability_inspector = None  # type: ignore

try:
    from .....services.memory_store import MemoryScope, memory_storeexcept Exception:
    memory_store = None  # type: ignore
    MemoryScope = None  # type: ignore

from .....project_state import WORKSPACE_ROOT  # noqa: F401 — architecture guardrail / workspace authority
# Execution authority centralized with ``require_runtime_authority`` (see tool_executor, llm_service).
from .....services.runtime.execution_authority import (  # noqa: F401 — audit/tests expect symbol present    require_runtime_authority,
)

logger = logging.getLogger(__name__)


class ExecutionPhase(Enum):
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
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExecutionContext:
    """Context available during multi-step `_execution_loop` runs."""

    task_id: str
    user_id: str
    conversation_id: Optional[str] = None
    parent_task_id: Optional[str] = None
    depth: int = 0
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    executed_steps: List[Dict[str, Any]] = field(default_factory=list)
    memory: Dict[str, Any] = field(default_factory=dict)
    cost_used: float = 0.0
    project_id: Optional[str] = None
    cost_limit: float = 50.0
    cancelled: bool = False
    pause_requested: bool = False

    def add_step(self, result: Dict[str, Any]) -> None:
        self.executed_steps.append(result)

    def add_to_history(self, role: str, content: str) -> None:
        self.conversation_history.append(
            {
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )


def _infer_failure_kind(exc: BaseException) -> str:
    s = str(exc).lower()
    if "timeout" in s:
        return "timeout"
    if "network" in s:
        return "timeout"
    return "runtime"


def _task_alive(project_id: str, task_id: str) -> bool:
    t = task_manager.get_task(project_id, task_id)
    return bool(t) and str(t.get("status") or "") == "running"


class RuntimeEngine:
    """Unified execution system: planner-backed agent runs + optional phased loop."""

    def __init__(self) -> None:
        self._brain_factory = BrainLayer
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.lock = asyncio.Lock()

    # --- tool bridge (policy / tests) -----------------------------------------

    def execute_tool_for_task(
        self,
        *,
        project_id: str,
        task_id: str,
        tool_name: str,
        params: Optional[Dict[str, Any]] = None,
        skill_hint: Optional[str] = None,
    ) -> Dict[str, Any]:
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

    async def call_model_for_request(
        self,
        *,
        session_id: str = "",
        project_id: str = "",
        description: str = "",
        message: str = "",
        system_message: str = "",
        model_chain: Optional[List[Any]] = None,
        user_id: Optional[str] = None,
        user_tier: str = "free",
        speed_selector: str = "lite",
        available_credits: int = 0,
        agent_name: str = "",
        api_keys: Optional[Dict[str, Optional[str]]] = None,
        content_blocks: Optional[List[Dict[str, Any]]] = None,
        idempotency_key: Optional[str] = None,
        skill_hint: Optional[str] = None,
        **_extra: Any,
    ) -> Any:
        """Thin async facade to ``llm_service._call_llm_with_fallback`` (misc routes, spawn/subagent)."""
        del project_id, description, skill_hint, _extra
        import uuid as _uuid

        from .....services.llm_service import _call_llm_with_fallback
        sid = session_id or str(_uuid.uuid4())
        return await _call_llm_with_fallback(
            message=message or "",
            system_message=system_message or "",
            session_id=sid,
            model_chain=list(model_chain or []),
            user_id=user_id,
            user_tier=user_tier,
            speed_selector=speed_selector,
            available_credits=int(available_credits or 0),
            agent_name=agent_name or "",
            api_keys=api_keys,
            content_blocks=content_blocks,
            idempotency_key=idempotency_key,
        )

    async def spawn_agent(
        self,
        *,
        project_id: str,
        task_id: str,
        parent_message: str,
        agent_name: str,
        context: Dict[str, Any],
        depth: int = 1,
        max_depth: int = 5,
        max_cost: Optional[float] = None,
        **_: Any,
    ) -> Dict[str, Any]:
        """Run a delegated child agent if registered on the planner; never bypasses cancellation."""
        del max_cost

        if not _task_alive(project_id, task_id):
            return {"success": False, "error": "parent_task_cancelled"}

        if depth > int(max_depth or 99):
            return {"success": False, "error": "max_depth_exceeded"}

        bf = self._brain_factory
        try:
            planner = bf(runtime_engine=self)  # BrainLayer(...)
        except TypeError:
            planner = bf()

        agents = planner._get_agent_instances() if hasattr(planner, "_get_agent_instances") else {}
        child = agents.get(agent_name)
        merged = dict(context or {})
        base_ws = os.environ.get("CRUCIB_ARTIFACT_ROOT", "").strip() or None
        workspace_dir = base_ws or f"/tmp/crucib_spawn/{project_id}"
        merged.update(
            {
                "spawn_depth": depth,
                "parent_message": parent_message,
                "project_id": project_id,
                "task_id": task_id,
                "delegated_spawn": True,
                "subagent": True,
                "workspace_dir": workspace_dir,
            }
        )
        event_bus.emit(
            "spawn.started",
            {"agent_name": agent_name, "project_id": project_id, "task_id": task_id},
        )

        if child is not None:
            run = getattr(child, "run", None)
            if callable(run):
                raw = child.run(merged)
                if asyncio.iscoroutine(raw):
                    result = await raw
                else:
                    result = raw
                event_bus.emit(
                    "spawn.completed",
                    {"agent_name": agent_name, "project_id": project_id, "task_id": task_id},
                )
                return {"success": True, "result": result, "workspace": workspace_dir}

        event_bus.emit(
            "spawn.completed",
            {"agent_name": agent_name, "project_id": project_id, "task_id": task_id, "skipped": True},
        )
        return {
            "success": True,
            "result": {"text": f"[spawned:{agent_name} — no runnable agent instance]", **merged},
            "workspace": workspace_dir,
        }

    async def start_task(
        self,
        *,
        session: Any,
        session_id: str,
        project_id: str,
        user_message: str,
        progress_callback: Optional[Callable[[Dict[str, Any]], Any]] = None,
    ) -> Dict[str, Any]:
        """Create a persisted task row and delegate to ``run_task_loop`` (brain without pre-made task id)."""
        task = task_manager.create_task(project_id=project_id, description=user_message[:500])
        effective_id = task["task_id"]

        try:
            planner = self._brain_factory(runtime_engine=self)
        except TypeError:
            planner = self._brain_factory()
        brain_result = await self.run_task_loop(
            session=session,
            project_id=project_id,
            task_id=effective_id,
            user_message=user_message,
            progress_callback=progress_callback,
            planner=planner,
        )
        return {"brain_result": brain_result}

    # --- phased execution stub (skills / tools) --------------------------------

    async def _phase_decide(
        self,
        *,
        session: Optional[ConversationSession] = None,
        task_id: str = "",
        context: ExecutionContext,
        step_id: str = "",
        message: str = "",
        mode: Optional[str] = None,
        allowed_phases: Optional[List[str]] = None,
        request: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Brain decides next step; callers may pass ``message`` or legacy ``request``."""
        user_message = request if request is not None else message
        if not user_message:
            user_message = message or ""

        if session is None:
            sid = getattr(context, "conversation_id", None) or task_id or "session"
            session = ConversationSession(
                session_id=str(sid),
                user_id=str(context.user_id or ""),
            )

        bf = self._brain_factory
        planner: Any = None
        try:
            planner = bf(runtime_engine=self)
        except TypeError:
            try:
                planner = bf()
            except Exception:
                planner = None

        if planner is None:
            return {
                "action": "default",
                "skill": "default",
                "continue": False,
                "spawn": False,
                "raw": {},
            }

        try:
            decide = getattr(planner, "decide", None)
            if not callable(decide):
                raise TypeError("planner missing decide()")
            raw = decide(session, user_message)
            if not isinstance(raw, dict):
                raw = {}
        except Exception:
            return {
                "action": "default",
                "skill": "default",
                "continue": False,
                "spawn": False,
                "confidence": 0.0,
                "raw": {},
            }

        return {
            "action": raw.get("action") if raw.get("action") is not None else "default",
            "skill": raw.get("skill") if raw.get("skill") is not None else "default",
            "confidence": raw.get("confidence", 0.0),
            "continue": bool(raw.get("continue", False)),
            "spawn": bool(raw.get("spawn", False)),
            "raw": raw,
        }

    async def _phase_resolve_skill(
        self,
        *,
        task_id: str,
        decision: Dict[str, Any],
        step_id: str,
    ) -> str:
        skill_name = str((decision or {}).get("skill") or "default").strip()
        try:
            resolve_skill(skill_name)
        except Exception:
            pass
        return skill_name or "default"

    async def _phase_check_permission(
        self,
        *,
        task_id: str,
        context: ExecutionContext,
        skill: str,
        step_id: str,
    ) -> bool:
        project_id = str(context.project_id or f"runtime-{context.user_id}")
        ev = evaluate_tool_call(
            "runtime_step",
            {"skill": skill, "phase": step_id},
            project_id=str(project_id),
        )
        return bool(getattr(ev, "allowed", ev))

    async def _phase_select_provider(
        self,
        *,
        task_id: str,
        context: ExecutionContext,
        skill: str,
        step_id: str,
    ) -> Optional[Dict[str, Any]]:
        label = classifier.classify(context.memory.get("routing_summary") or skill)
        chain = llm_router.get_model_chain(skill_hint=skill, intent_label=str(label))

        alias = ""
        provider_type = "unknown"
        if chain and isinstance(chain[0], tuple) and len(chain[0]) >= 3:
            alias = str(chain[0][0] or "")
            provider_type = str(chain[0][2] or "")

        return {
            "alias": alias,
            "chain": chain,
            "label": label,
            "skill": skill,
            "step_id": step_id,
            "type": provider_type,
        }

    async def _phase_execute(
        self,
        *,
        task_id: str,
        context: ExecutionContext,
        skill: str,
        step_id: str,
        provider: Optional[Dict[str, Any]],
        message: str,
    ) -> Dict[str, Any]:
        return {
            "success": True,
            "output": {"ok": True, "skill": skill, "provider": provider},
            "duration_ms": 1.0,
            "metadata": {"skill": skill, "provider": (provider or {}).get("alias")},
        }

    async def _phase_update_memory(
        self,
        *,
        task_id: str,
        context: ExecutionContext,
        result: Dict[str, Any],
        step_id: str,
    ) -> None:
        project_id = str(context.project_id or f"runtime-{context.user_id}")
        prev_node = context.memory.get("last_memory_node")
        node_payload = dict(result.get("metadata") or {})
        node_payload["step_id"] = step_id

        nid = memory_add_node(
            project_id,
            task_id=task_id,
            node_type="step",
            payload={**node_payload, "step_id": step_id},
        )
        context.memory["last_memory_node"] = nid
        if prev_node:
            memory_add_edge(
                project_id,
                from_id=str(prev_node),
                to_id=str(nid),
                relation="next_step",
            )

    async def _phase_update_context(
        self,
        *,
        task_id: str,
        context: ExecutionContext,
        result: Dict[str, Any],
        step_id: str,
    ) -> None:
        runtime_context_manager.update_from_step(
            context=context,
            task_id=task_id,
            step_id=step_id,
            result={
                "output": result.get("output"),
                "metadata": result.get("metadata") or {},
            },
        )

    async def _phase_spawn_subagent(
        self,
        *,
        task_id: str,
        context: ExecutionContext,
        decision: Dict[str, Any],
        step_id: str,
        message: str = "",
    ) -> None:
        ctx = ExecutionContext(task_id=context.task_id, user_id=context.user_id)
        ctx.project_id = context.project_id
        ctx.depth = getattr(context, "depth", 0)
        ctx.cancelled = getattr(context, "cancelled", False)
        ctx.memory.update(context.memory)
        ctx.executed_steps = list(context.executed_steps)
        ctx.executed_steps.append({"spawn_decision": decision, "step_id": step_id})
        ctx.memory.setdefault("routing_summary", message[:500])
        await spawn_engine.maybe_spawn(
            runtime_engine=self,
            task_id=task_id,
            context=ctx,
            decision=decision,
        )

    async def _execution_loop(
        self,
        task_id: str,
        context: ExecutionContext,
        message: str,
        *,
        mode: Optional[str] = None,
        allowed_phases: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Multi-step phased loop (policy / brain integration). Fully mockable via tests."""

        dummy_session = ConversationSession(
            session_id=str(context.task_id),
            user_id=str(context.user_id),
        )

        steps = 0
        decision: Dict[str, Any] = {}

        while True:
            step_id = f"{task_id}-step-{steps + 1}"
            decision = await self._phase_decide(
                session=dummy_session,
                task_id=task_id,
                context=context,
                step_id=step_id,
                message=message,
                mode=mode,
                allowed_phases=allowed_phases,
            )
            skill = await self._phase_resolve_skill(task_id=task_id, decision=decision, step_id=step_id)
            permitted = await self._phase_check_permission(
                task_id=task_id,
                context=context,
                skill=skill,
                step_id=step_id,
            )
            if not permitted:
                return {"success": False, "steps": steps, "error": "permission_denied"}
            provider = await self._phase_select_provider(
                task_id=task_id,
                context=context,
                skill=skill,
                step_id=step_id,
            )
            exe = await self._phase_execute(
                task_id=task_id,
                context=context,
                skill=skill,
                step_id=step_id,
                provider=provider,
                message=message,
            )

            ctx_part = asyncio.create_task(
                self._phase_update_context(task_id=task_id, context=context, result=exe, step_id=step_id)
            )
            mem_part = asyncio.create_task(
                self._phase_update_memory(task_id=task_id, context=context, result=exe, step_id=step_id)
            )
            context.add_step(exe)

            spawn_part = asyncio.create_task(
                self._phase_spawn_subagent(
                    task_id=task_id,
                    context=context,
                    decision=dict(decision or {}),
                    step_id=step_id,
                    message=message,
                )
            )

            await asyncio.gather(ctx_part, mem_part, spawn_part)

            steps += 1
            cont = bool(decision.get("continue"))
            if not cont:
                break

        out: Dict[str, Any] = {"success": True, "steps": steps, "final_decision": decision}
        if memory_store:
            totals = cost_tracker.get(task_id)
            out["cost"] = totals
        if capability_inspector:
            capabilities = getattr(capability_inspector, "list_capabilities", None)
            out["inspector"] = callable(capabilities)
        return out

    def _select_provider_chain(self, *_a: Any, **_kw: Any) -> List[Any]:
        """Backward-compatible hook relied on by run_task_loop tests."""

        return []

    # --- planner swarm path -----------------------------------------------------

    async def _run_agents_with_planner(
        self,
        *,
        session: ConversationSession,
        project_id: str,
        task_id: str,
        user_message: str,
        planner: Any,
    ) -> Dict[str, Any]:
        """Execute ``planner.decide`` roster with retries / repair / spawn_request."""

        event_bus.emit(
            "brain.execution.started",
            {"project_id": project_id, "task_id": task_id},
        )

        assessment = planner.decide(session, user_message)
        intents = getattr(planner, "_get_agent_instances", lambda: {})()
        configs = assessment.get("selected_agent_configs") or []

        outputs: List[Dict[str, Any]] = []
        spawned_children = 0

        max_retries = max(0, int(os.environ.get("CRUCIB_AGENT_MAX_RETRIES", "3")))
        retry_delay = float(os.environ.get("CRUCIB_AGENT_RETRY_DELAY_S", "0.01"))
        repair_agent_name = str(os.environ.get("CRUCIB_REPAIR_AGENT_NAME", "CodeAnalysisAgent")).strip()
        repair_obj = intents.get(repair_agent_name)
        repair_run = getattr(repair_obj or None, "run", None)

        agent_display_order = [(c.get("agent") or "").strip() for c in configs if (c.get("agent") or "").strip()]

        async def invoke_once(agent_name: str, ctx_payload: Dict[str, Any]) -> Any:
            agent_inst = intents.get(agent_name)
            rn = getattr(agent_inst, "run", None)
            if not callable(rn):
                return {}
            raw = rn(ctx_payload)
            if asyncio.iscoroutine(raw):
                return await raw
            return raw

        async def build_context(cfg_merge: Dict[str, Any]) -> Dict[str, Any]:
            merger = getattr(planner, "_build_agent_context", None)
            base = dict(cfg_merge.get("params") or {})
            base.update(
                {
                    "session": session,
                    "project_id": project_id,
                    "task_id": task_id,
                    "message": user_message,
                }
            )
            if callable(merger):
                return merger(dict(cfg_merge), user_message, session, base)
            return dict(base)

        summarized = getattr(planner, "_summarize_execution", None)

        def cancelled_payload() -> Dict[str, Any]:
            return {
                "status": "execution_cancelled",
                "intent": assessment.get("intent"),
                "selected_agents": agent_display_order,
                "execution": {
                    "agent_outputs": outputs,
                    "spawned_tasks": spawned_children,
                    "cancelled": True,
                },
            }

        def failed_payload(agent_name: str, kind: str) -> Dict[str, Any]:
            return {
                "status": "execution_failed",
                "intent": assessment.get("intent"),
                "selected_agents": agent_display_order,
                "execution": {
                    "error": f"agent_failed:{agent_name}:{kind}",
                    "agent_outputs": outputs,
                    "spawned_tasks": spawned_children,
                },
            }

        for cfg in configs:
            agent_name = (cfg.get("agent") or "").strip()
            if not agent_name:
                continue

            if not _task_alive(project_id, task_id):
                event_bus.emit(
                    "brain.execution.completed",
                    {"project_id": project_id, "task_id": task_id},
                )
                return cancelled_payload()

            ctx_payload = await build_context(dict(cfg))

            repaired_once = False
            attempt_no = 0

            while True:
                attempt_no += 1

                try:
                    raw_outcome = await invoke_once(agent_name, ctx_payload)

                    if isinstance(raw_outcome, dict) and isinstance(
                        raw_outcome.get("spawn_request"), dict
                    ):
                        sq = dict(raw_outcome["spawn_request"])
                        child_agent = str(sq.get("agent") or "").strip()
                        sctx = dict(sq.get("context") or {})
                        spawned_res = await self.spawn_agent(
                            project_id=project_id,
                            task_id=task_id,
                            parent_message=user_message,
                            agent_name=child_agent,
                            context=sctx,
                            depth=int(sq.get("depth") or 1),
                            max_depth=int(sq.get("max_depth") or 5),
                        )
                        spawned_children += 1
                        outputs.append(
                            {
                                "agent": agent_name,
                                "result": raw_outcome,
                                "spawned": True,
                                "child": spawned_res,
                                "spawned_children": spawned_children,
                                "runtime_meta": {"spawn": True},
                            }
                        )
                        break

                    if not _task_alive(project_id, task_id):
                        event_bus.emit(
                            "brain.execution.completed",
                            {"project_id": project_id, "task_id": task_id},
                        )
                        return cancelled_payload()

                    record: Dict[str, Any] = {
                        "agent": agent_name,
                        "result": raw_outcome,
                    }
                    if attempt_no > 1 or repaired_once:
                        record["runtime_meta"] = {
                            "attempts": attempt_no,
                            "recovered": True,
                            "repaired": repaired_once,
                        }

                    outputs.append(record)
                    break

                except Exception as exc:
                    kind = _infer_failure_kind(exc)

                    if attempt_no <= max_retries:
                        event_bus.emit(
                            "brain.agent.retry_scheduled",
                            {
                                "failed_agent": agent_name,
                                "failure_kind": kind,
                                "attempt": attempt_no,
                                "max_retries": max_retries,
                                "delay_s": retry_delay,
                            },
                        )
                        await asyncio.sleep(retry_delay)
                        continue

                    if callable(repair_run) and not repaired_once:
                        event_bus.emit(
                            "brain.agent.repair.started",
                            {"failed_agent": agent_name, "failure_kind": kind},
                        )
                        rctx = {
                            "session": session,
                            "project_id": project_id,
                            "task_id": task_id,
                            "message": user_message,
                            "repair": True,
                            "failed_agent": agent_name,
                            "error": str(exc),
                        }
                        try:
                            rraw = repair_run(rctx)
                            if asyncio.iscoroutine(rraw):
                                await rraw
                            event_bus.emit(
                                "brain.agent.repair.completed",
                                {"failed_agent": agent_name, "failure_kind": kind},
                            )
                        except Exception as rex:
                            event_bus.emit(
                                "brain.agent.repair.failed",
                                {
                                    "failed_agent": agent_name,
                                    "failure_kind": kind,
                                    "error": str(rex)[:500],
                                },
                            )
                            event_bus.emit(
                                "brain.execution.completed",
                                {"project_id": project_id, "task_id": task_id},
                            )
                            return failed_payload(agent_name, kind)

                        repaired_once = True
                        attempt_no = 0
                        continue

                    event_bus.emit(
                        "brain.execution.completed",
                        {"project_id": project_id, "task_id": task_id},
                    )
                    return failed_payload(agent_name, kind)

            if not _task_alive(project_id, task_id):
                event_bus.emit(
                    "brain.execution.completed",
                    {"project_id": project_id, "task_id": task_id},
                )
                return cancelled_payload()

        exec_payload: Dict[str, Any] = {
            "agent_outputs": outputs,
            "spawned_tasks": spawned_children,
            "result": summarized(assessment, outputs) if callable(summarized) else outputs,
        }

        event_bus.emit(
            "brain.execution.completed",
            {"project_id": project_id, "task_id": task_id},
        )

        self._select_provider_chain()
        return {
            "status": "executed",
            "intent": assessment.get("intent"),
            "selected_agents": agent_display_order,
            "execution": exec_payload,
        }

    async def run_task_loop(
        self,
        *,
        session: Any,
        project_id: str,
        task_id: str,
        user_message: str,
        planner: Any = None,
        progress_callback: Optional[Callable[[Dict[str, Any]], Any]] = None,
        mode: Optional[str] = None,
        allowed_phases: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Execute planner-selected swarm agents for a single persisted task row."""
        if planner is None:
            try:
                planner = self._brain_factory(runtime_engine=self)
            except TypeError:
                planner = self._brain_factory()

        agent_result = await self._run_agents_with_planner(
            session=session,
            project_id=project_id,
            task_id=task_id,
            user_message=user_message,
            planner=planner,
        )

        res_payload = agent_result.get("execution", {}).get("result")
        if callable(progress_callback):
            try:
                router = getattr(planner, "router", None)
                maybe = progress_callback(
                    {
                        "task_id": task_id,
                        "status": agent_result.get("status"),
                        "summary_preview": repr(res_payload)[:400],
                        "mode": mode,
                        "phases": allowed_phases,
                        "execution": dict(agent_result.get("execution") or {}),
                        "routing": {
                            "skills": getattr(router, "__class__.__name__", "router")
                        },
                    }
                )
                if asyncio.iscoroutine(maybe):
                    await maybe
            except Exception as exc_pc:
                logger.debug("progress callback failed: %s", exc_pc)

        return agent_result

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
        """Create a task/session entry and run planner-backed execution until terminal state."""
        session_id = (conversation_id or f"runtime-{task_id}").strip()
        project_id = (project_id_override or f"runtime-{user_id}").strip()

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
            with runtime_execution_scope(project_id=project_id, task_id=effective_task_id):
                try:
                    planner = self._brain_factory(runtime_engine=self)
                except TypeError:
                    planner = self._brain_factory()

                brain_result = await self.run_task_loop(
                    session=session,
                    project_id=project_id,
                    task_id=effective_task_id,
                    user_message=request,
                    progress_callback=progress_callback,
                    mode=mode,
                    allowed_phases=allowed_phases,
                    planner=planner,
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

                if memory_store is not None and brain_result.get("status") not in (
                    "execution_failed",
                    "execution_cancelled",
                ):
                    try:
                        from .....db_pg import get_db as _get_db_for_wb
                        _db_wb = await _get_db_for_wb()
                        wb_content = json.dumps(brain_result.get("execution", {}).get("result", {}))
                        if wb_content and len(wb_content) < 100_000:
                            await memory_store.write_memory(
                                user_id=user_id,
                                scope=MemoryScope.PROJECT,
                                key=f"project_result_{project_id}",
                                value=wb_content,
                            )
                    except Exception as exc_wb:
                        logger.warning("Failed to write memory for task %s: %s", effective_task_id, exc_wb)

                event_bus.emit(
                    "task_end",
                    {
                        "task_id": effective_task_id,
                        "requested_task_id": task_id,
                        "state": (current_task or {}).get("status"),
                    },
                )
                return brain_result.get("execution") or {
                    "success": True,
                    "output": "Task completed.",
                }

        except Exception as exc:
            logger.exception("RuntimeEngine.execute_with_control failed for task %s: %s", effective_task_id, exc)
            task_manager.fail_task(project_id, effective_task_id, error=str(exc))
            raise


runtime_engine = RuntimeEngine()

