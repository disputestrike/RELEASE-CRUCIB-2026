"""Brain planner layer: intent assessment and agent-step planning only."""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from agents.registry import AgentRegistry
from services.conversation_manager import ConversationSession, ContextEnricher
from services.events import event_bus
from services.semantic_router import SemanticRouter

logger = logging.getLogger(__name__)


class BrainLayer:
    """Planner-only brain layer. Execution authority belongs to runtime_engine."""

    def __init__(self, router: Optional[SemanticRouter] = None):
        self.router = router or SemanticRouter()

    def assess_request(self, session: ConversationSession, user_message: str) -> Dict[str, Any]:
        routing = self.router.route(
            user_message,
            {
                "session_context": session.get_context_enrichment(),
                "keywords": session.keywords,
            },
        )

        selected_agents = self._select_agents(routing)

        if routing.get("intent_confidence", 0.0) < 0.45:
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

        return {
            "assistant_response": self._summarize_plan(user_message, routing, selected_agents, session),
            "suggestions": self._suggest_followups(routing),
            "intent": routing.get("intent"),
            "intent_confidence": routing.get("intent_confidence"),
            "routing": routing,
            "selected_agents": [a.get("agent") for a in selected_agents],
            "selected_agent_configs": selected_agents,
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
        from services.runtime.runtime_engine import runtime_engine

        meta = execution_meta or {}
        project_id = (meta.get("project_id") or f"brain-{getattr(session, 'session_id', 'session')}").strip()
        task_id = (meta.get("task_id") or "").strip() or None

        if task_id:
            return await runtime_engine.run_task_loop(
                session=session,
                project_id=project_id,
                task_id=task_id,
                user_message=user_message,
                progress_callback=progress_callback,
                planner=self,
            )

        out = await runtime_engine.start_task(
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
    ) -> str:
        summaries: List[str] = []
        for output in execution_output.get("agent_outputs", []):
            agent_name = output.get("agent")
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

        return (
            "I’ve completed the focused execution. "
            + " ".join(summaries)
            + " If you want, I can continue refining the output in the same conversation."
        )
