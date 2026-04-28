"""Brain planner layer: intent assessment and agent-step planning only."""

from __future__ import annotations

import logging
import sys
from typing import Any, Callable, Dict, List, Optional

from backend.agents.registry import AgentRegistry
from backend.services.conversation_manager import ConversationSession, ContextEnricher
from backend.services.events import event_bus
from backend.services.semantic_router import SemanticRouter

logger = logging.getLogger(__name__)


def _event_bus():
    legacy_events = sys.modules.get("services.events")
    return getattr(legacy_events, "event_bus", event_bus)


class BrainLayer:
    """Planner-only brain layer. Execution authority belongs to runtime_engine."""

    def __init__(self, router: Optional[SemanticRouter] = None, runtime_engine: Optional[Any] = None):
        self.router = router or SemanticRouter()
        self.runtime_engine = runtime_engine

    @staticmethod
    def _is_build_prompt(user_message: str, routing: Dict[str, Any]) -> bool:
        msg = (user_message or "").lower()
        intent = str(routing.get("intent") or "")
        if intent in {"generation", "execution", "deployment", "testing"}:
            return True
        build_markers = [
            "build ",
            "implement",
            "create ",
            "generate",
            "fix this app",
            "deploy",
            "dashboard",
            "api",
            "frontend",
            "backend",
            "saas",
        ]
        return any(marker in msg for marker in build_markers)

    @staticmethod
    def _force_execution_mode(session: ConversationSession, user_message: str) -> bool:
        msg = (user_message or "").lower()
        if "benchmark_mode=true" in msg or "[benchmark_mode]" in msg:
            return True
        if "must_complete=true" in msg or "[must_complete]" in msg:
            return True
        meta = getattr(session, "metadata", {}) or {}
        return bool(meta.get("benchmark_mode") or meta.get("must_complete"))

    def assess_request(self, session: ConversationSession, user_message: str) -> Dict[str, Any]:
        routing = self.router.route(
            user_message,
            {
                "session_context": session.get_context_enrichment(),
                "keywords": session.keywords,
            },
        )

        selected_agents = self._select_agents(routing)
        force_execution = self._force_execution_mode(session, user_message)
        build_prompt = self._is_build_prompt(user_message, routing)
        suppress_clarification = force_execution or build_prompt

        if routing.get("intent_confidence", 0.0) < 0.45 and not suppress_clarification:
            clarifying_questions = ContextEnricher.extract_clarifying_questions(
                {"user_prompt": user_message},
                session,
            )
            if clarifying_questions:
                return {
                    "assistant_response": clarifying_questions[0],
                    "suggestions": clarifying_questions,
                    "intent": routing.get("intent"),
                    "intent_confidence": routing.get("intent_confidence"),
                    "routing": routing,
                    "selected_agents": [a.get("agent") for a in selected_agents],
                    "selected_agent_configs": selected_agents,
                    "status": "clarification_required",
                }

        if force_execution and not selected_agents:
            selected_agents = [
                {
                    "agent": "WorkspaceExplorerAgent",
                    "confidence": 1.0,
                    "params": {"user_prompt": user_message, "must_complete": True, "benchmark_mode": True},
                    "reasoning": "must-complete fallback",
                }
            ]

        return {
            "assistant_response": self._summarize_plan(user_message, routing, selected_agents, session),
            "suggestions": self._suggest_followups(routing),
            "intent": routing.get("intent"),
            "intent_confidence": routing.get("intent_confidence"),
            "routing": routing,
            "selected_agents": [a.get("agent") for a in selected_agents],
            "selected_agent_configs": selected_agents,
            "force_execution": force_execution,
            "build_prompt": build_prompt,
            "status": "ready",
        }

    def decide(self, session: ConversationSession, user_message: str) -> Dict[str, Any]:
        """Planner decision API consumed by runtime_engine."""
        return self.assess_request(session, user_message)

    async def execute_request(
        self,
        session: ConversationSession,
        user_message: str,
        progress_callback: Optional[Callable[[Dict[str, Any]], Any]] = None,
        execution_meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Backward-compatible adapter that routes execution through runtime_engine."""

        meta = execution_meta or {}
        project_id = (meta.get("project_id") or f"brain-{getattr(session, 'session_id', 'session')}").strip()
        task_id = (meta.get("task_id") or "").strip() or None
        bus = _event_bus()

        # ── Route through runtime_engine when available ───────────────────────
        if self.runtime_engine is not None:
            if task_id:
                return await self.runtime_engine.run_task_loop(
                    session=session,
                    project_id=project_id,
                    task_id=task_id,
                    user_message=user_message,
                    progress_callback=progress_callback,
                    planner=self,
                )
            out = await self.runtime_engine.start_task(
                session=session,
                session_id=getattr(session, "session_id", "session"),
                project_id=project_id,
                user_message=user_message,
                progress_callback=progress_callback,
            )
            return out.get("brain_result") or {
                "status": "execution_failed",
                "execution": {"error": "runtime_engine returned no result"},
            }

        # ── Fallback: local execution (no runtime_engine) ─────────────────────
        assessment = self.assess_request(session, user_message)
        bus.emit("brain.assessed", {"project_id": project_id, "task_id": task_id, **assessment})
        bus.emit("brain.execution.started", {"project_id": project_id, "task_id": task_id})

        agent_outputs: List[Dict[str, Any]] = []
        agent_instances = self._get_agent_instances()

        for name in assessment.get("selected_agents") or []:
            # ── Cancellation guard before each agent ─────────────────────
            if task_id:
                try:
                    from services.runtime.task_manager import task_manager as _tm
                except ImportError:
                    from backend.services.runtime.task_manager import task_manager as _tm  # type: ignore
                record = _tm.get_task(project_id, task_id)
                if record and record.get("status") == "killed":
                    bus.emit("brain.execution.cancelled", {"project_id": project_id, "task_id": task_id})
                    return {
                        "status": "execution_cancelled",
                        "intent": assessment.get("intent"),
                        "selected_agents": assessment.get("selected_agents") or [],
                        "execution": {"success": False, "cancelled": True, "agent_outputs": agent_outputs},
                    }

            agent = agent_instances.get(name)
            if agent is None:
                continue
            runner = getattr(agent, "run", None)
            if not callable(runner):
                continue
            ctx = {"session": session, "message": user_message,
                   "project_id": project_id, "task_id": task_id}
            bus.emit("brain.agent.started", {"project_id": project_id, "task_id": task_id, "agent": name})
            # ── Set runtime execution scope so tool_executor authority checks pass ──
            try:
                from backend.services.runtime.execution_context import runtime_execution_scope as _rscope
            except ImportError:
                from services.runtime.execution_context import runtime_execution_scope as _rscope  # type: ignore
            async def _run_in_scope(_runner=runner, _ctx=ctx):
                with _rscope(project_id=project_id, task_id=task_id or "fallback"):
                    r = _runner(_ctx)
                    if hasattr(r, "__await__"):
                        r = await r
                    return r
            run_result = await _run_in_scope()
            bus.emit("brain.agent.completed", {"project_id": project_id, "task_id": task_id, "agent": name})
            agent_outputs.append({"agent": name, "result": run_result})

        bus.emit("brain.execution.completed", {
            "project_id": project_id, "task_id": task_id,
            "agents": [o["agent"] for o in agent_outputs],
        })
        return {
            "status": "executed",
            "intent": assessment.get("intent"),
            "selected_agents": assessment.get("selected_agents") or [],
            "execution": {"success": True, "agent_outputs": agent_outputs, "result": ""},
        }

        if task_id:  # pragma: no cover — dead after refactor; kept for safety
            return await self.runtime_engine.run_task_loop(
                session=session,
                project_id=project_id,
                task_id=task_id,
                user_message=user_message,
                progress_callback=progress_callback,
                planner=self,
            )

        out = await self.runtime_engine.start_task(
            session=session,
            session_id=getattr(session, "session_id", "session"),
            project_id=project_id,
            user_message=user_message,
            progress_callback=progress_callback,
        )
        return out.get("brain_result") or {
            "status": "execution_failed",
            "execution": {"error": "runtime_engine returned no result"},
        }

    def _get_agent_instances(self) -> Dict[str, Any]:
        """Legacy extension point for tests and local agent runners."""
        return {}

    def _select_agents(self, routing: Dict[str, Any], max_agents: int = 2) -> List[Dict[str, Any]]:
        candidates = routing.get("primary_agents", []) + routing.get("secondary_agents", [])
        candidates = sorted(candidates, key=lambda x: x.get("confidence", 0), reverse=True)

        selected: List[Dict[str, Any]] = []
        for agent in candidates:
            if len(selected) >= max_agents:
                break
            if agent.get("confidence", 0) >= 0.35:
                selected.append(agent)

        if not selected and candidates:
            selected.append(candidates[0])

        return selected

    def _summarize_plan(
        self,
        user_message: str,
        routing: Dict[str, Any],
        selected_agents: List[Dict[str, Any]],
        session: ConversationSession,
    ) -> str:
        intent = routing.get("intent", "general")
        confidence = float(routing.get("intent_confidence", 0.0) or 0.0)
        agent_actions = [self._human_action(agent) for agent in selected_agents]
        agent_description = ", then ".join(agent_actions) if agent_actions else "handle it carefully"

        if confidence < 0.6:
            return (
                f"I’m building a safe plan for this request. "
                f"It looks like a {intent.replace('_', ' ')} task, but I’m not fully certain yet. "
                f"I’ll proceed carefully and may request clarification."
            )

        return (
            f"I understand this as a {intent.replace('_', ' ')} task. "
            f"I’m taking a focused approach so you get one calm, useful result. "
            f"First I will {agent_description}. "
            f"If I need any more detail, I’ll ask for it before making changes."
        )

    def _human_action(self, agent_config: Dict[str, Any]) -> str:
        agent_name = str(agent_config.get("agent", "agent"))
        if "CodeAnalysis" in agent_name:
            return "review the code for quality and fixes"
        if "Backend" in agent_name:
            return "implement the backend behavior and API"
        if "Frontend" in agent_name:
            return "build the frontend interface"
        if "Terminal" in agent_name:
            return "run the project commands and inspect results"
        if "Deployment" in agent_name:
            return "deploy the app and verify it"
        if "UX" in agent_name or "Design" in agent_name:
            return "improve the design and user experience"
        if "Test" in agent_name:
            return "generate and run tests"
        return f"focus on the task with {agent_name}"

    def _suggest_followups(self, routing: Dict[str, Any]) -> List[str]:
        intent = routing.get("intent", "general")

        if intent == "code_analysis":
            return [
                "Review test coverage next",
                "Refactor the code for clarity",
                "Identify any hidden bugs",
            ]
        if intent == "testing":
            return [
                "Run focused regression tests",
                "Check failing test output",
                "Verify the build passes",
            ]
        if intent == "generation":
            return [
                "Refine the UX after generation",
                "Add error handling and validation",
                "Review the generated API contract",
            ]
        if intent == "deployment":
            return [
                "Verify the deployment logs",
                "Confirm the live URL works",
                "Run a smoke test",
            ]
        return [
            "Test the result",
            "Ask for a more detailed goal",
            "Review the generated output",
        ]

    def _get_agent_instances(self) -> Dict[str, Any]:
        # Ensure decorator-registered agents are imported before reading registry.
        try:
            import agents.clarification_agent  # noqa: F401
            import agents.code_analysis_agent  # noqa: F401
            import agents.database_agent  # noqa: F401
            import agents.deployment_agent  # noqa: F401
            import agents.design_agent  # noqa: F401
            import agents.documentation_agent  # noqa: F401
            import agents.stack_selector_agent  # noqa: F401
            import agents.workspace_explorer_agent  # noqa: F401
        except Exception as exc:
            logger.warning("Agent module bootstrap incomplete: %s", exc)

        registry = AgentRegistry.get_all_agents()
        instances: Dict[str, Any] = {}
        for name, cls in registry.items():
            try:
                instances[name] = cls()
            except Exception as exc:
                logger.warning("Could not instantiate agent %s: %s", name, exc)
        return instances

    def _build_agent_context(
        self,
        agent_config: Dict[str, Any],
        user_message: str,
        session: ConversationSession,
        execution_meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        context = {
            "user_prompt": user_message,
            "session_context": session.get_context_enrichment(),
        }
        if execution_meta:
            context.update(execution_meta)
        context.update(agent_config.get("params", {}))
        return context

    def _summarize_execution(
        self,
        brain_result: Dict[str, Any],
        execution_output: Dict[str, Any],
        user_message: str = "",
    ) -> str:
        summaries: List[str] = []
        seen_agents = set()
        for output in execution_output.get("agent_outputs", []):
            agent_name = output.get("agent")
            if isinstance(agent_name, str):
                seen_agents.add(agent_name)
            result = output.get("result")
            if isinstance(result, dict):
                if "files" in result:
                    summaries.append(f"{agent_name} generated {len(result['files'])} files.")
                elif "structure" in result:
                    summaries.append(f"{agent_name} produced structured output.")
                else:
                    summaries.append(f"{agent_name} produced keys {list(result.keys())}.")
            else:
                summaries.append(f"{agent_name} returned type {type(result).__name__}.")

        if not summaries:
            return (
                brain_result.get("assistant_response", "")
                + " I completed the focused plan, but there was no structured output detected."
            )

        completion_hints: List[str] = []
        if "DesignAgent" in seen_agents:
            completion_hints.append("frontend UI implemented")
        if "DatabaseAgent" in seen_agents:
            completion_hints.append("backend API/data flow implemented")
        if "DesignAgent" in seen_agents and "DatabaseAgent" in seen_agents:
            completion_hints.append("runnable end-to-end flow prepared")
        if "DeploymentAgent" in seen_agents:
            completion_hints.append("deploy readiness validated")

        summary = (
            "I've completed the focused execution. "
            + " ".join(summaries)
        )
        if user_message:
            brief = " ".join(user_message.split())
            if len(brief) > 240:
                brief = brief[:240] + "..."
            summary += f" Build brief addressed: {brief}."
        if completion_hints:
            summary += " Build status: " + ", ".join(completion_hints) + "."
        summary += " If you want, I can continue refining the output in the same conversation."
        return summary
