"""
Brain Layer: unified request interpretation, plan-first routing, and calm response assembly.
This layer chooses a focused execution path, limits agent usage, and returns human-style outputs.
"""

import asyncio
import inspect
import logging
from typing import Any, Callable, Dict, List, Optional

import agents
from agents.registry import AgentRegistry
from services.conversation_manager import ConversationSession, ContextEnricher
from services.semantic_router import SemanticRouter

logger = logging.getLogger(__name__)


class BrainLayer:
    """Top-level brain layer that abstracts swarm behavior into a single operator."""

    def __init__(self, router: Optional[SemanticRouter] = None):
        self.router = router or SemanticRouter()

    def assess_request(self, session: ConversationSession, user_message: str) -> Dict[str, Any]:
        """Interpret user intent and return a calm plan-first response."""
        routing = self.router.route(
            user_message,
            {
                "session_context": session.get_context_enrichment(),
                "keywords": session.keywords,
            },
        )

        selected_agents = self._select_agents(routing)

        if routing["intent_confidence"] < 0.45:
            clarifying_questions = ContextEnricher.extract_clarifying_questions(
                {"user_prompt": user_message}, session
            )
            if clarifying_questions:
                return {
                    "assistant_response": clarifying_questions[0],
                    "suggestions": clarifying_questions,
                    "intent": routing["intent"],
                    "intent_confidence": routing["intent_confidence"],
                    "routing": routing,
                    "selected_agents": [a["agent"] for a in selected_agents],
                "selected_agent_configs": selected_agents,
            "suggestions": self._suggest_followups(routing),
            "intent": routing["intent"],
            "intent_confidence": routing["intent_confidence"],
            "routing": routing,
            "selected_agents": [a["agent"] for a in selected_agents],
            "selected_agent_configs": selected_agents,
            "status": "ready",
        }

    def _select_agents(self, routing: Dict[str, Any], max_agents: int = 2) -> List[Dict[str, Any]]:
        agents = routing.get("primary_agents", []) + routing.get("secondary_agents", [])
        agents = sorted(agents, key=lambda x: x.get("confidence", 0), reverse=True)

        selected: List[Dict[str, Any]] = []
        for agent in agents:
            if len(selected) >= max_agents:
                break
            if agent.get("confidence", 0) >= 0.35:
                selected.append(agent)

        if not selected and agents:
            selected.append(agents[0])

        return selected

    def _summarize_plan(
        self,
        user_message: str,
        routing: Dict[str, Any],
        selected_agents: List[Dict[str, Any]],
        session: ConversationSession,
    ) -> str:
        intent = routing.get("intent", "general")
        confidence = routing.get("intent_confidence", 0.0)
        agent_actions = [self._human_action(agent) for agent in selected_agents]
        agent_description = ", then ".join(agent_actions) if agent_actions else "handle it carefully"

        summary = (
            f"I understand this as a {intent.replace('_', ' ')} task. "
            f"I’m taking a focused approach so you get one calm, useful result. "
            f"First I will {agent_description}. "
            f"If I need any more detail, I’ll ask for it before making changes."
        )

        if confidence < 0.6:
            summary = (
                f"I’m building a safe plan for this request. "
                f"It looks like a {intent.replace('_', ' ')} task, but I’m not fully certain yet. "
                f"I’ll proceed carefully and may request clarification."
            )

        return summary

    def _human_action(self, agent_config: Dict[str, Any]) -> str:
        agent_name = agent_config.get("agent", "agent")
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
        suggestions = []

        if intent == "code_analysis":
            suggestions = [
                "Review test coverage next",
                "Refactor the code for clarity",
                "Identify any hidden bugs",
            ]
        elif intent == "testing":
            suggestions = [
                "Run focused regression tests",
                "Check failing test output",
                "Verify the build passes",
            ]
        elif intent == "generation":
            suggestions = [
                "Refine the UX after generation",
                "Add error handling and validation",
                "Review the generated API contract",
            ]
        elif intent == "deployment":
            suggestions = [
                "Verify the deployment logs",
                "Confirm the live URL works",
                "Run a smoke test",
            ]
        else:
            suggestions = [
                "Test the result",
                "Ask for a more detailed goal",
                "Review the generated output",
            ]

        return suggestions[:3]

    async def execute_request(
        self,
        session: ConversationSession,
        user_message: str,
        progress_callback: Optional[Callable[[Dict[str, Any]], Any]] = None,
    ) -> Dict[str, Any]:
        """Assess the request and execute the selected plan if ready."""
        brain_result = self.assess_request(session, user_message)

        if brain_result.get("status") != "ready":
            return brain_result

        if not brain_result.get("selected_agent_configs"):
            brain_result["assistant_response"] = (
                brain_result["assistant_response"]
                + " I have a focused plan, but no execution path was selected."
            )
            brain_result["status"] = "ready_no_execution"
            return brain_result

        try:
            execution_output = await self._run_selected_agents(
                session,
                user_message,
                brain_result["selected_agent_configs"],
                progress_callback=progress_callback,
            )
            brain_result["execution"] = execution_output
            brain_result["assistant_response"] = self._summarize_execution(
                brain_result, execution_output
            )
            brain_result["status"] = "executed"
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            brain_result["assistant_response"] = (
                brain_result["assistant_response"]
                + " I encountered an issue while executing the plan. The plan is preserved and we can continue from here."
            )
            brain_result["status"] = "execution_failed"
            brain_result["execution"] = {"error": str(e)}

        return brain_result

    def _get_agent_instances(self) -> Dict[str, Any]:
        """Build a registry of available agent instances."""
        try:
            import agents as agents_pkg  # Ensure the package imports agent definitions

            _ = agents_pkg.__all__
        except Exception:
            pass

        registry = AgentRegistry.get_all_agents()
        instances: Dict[str, Any] = {}
        for name, cls in registry.items():
            try:
                instances[name] = cls()
            except Exception as e:
                logger.warning(f"Could not instantiate agent {name}: {e}")
        return instances

    def _build_agent_context(
        self,
        agent_config: Dict[str, Any],
        user_message: str,
        session: ConversationSession,
    ) -> Dict[str, Any]:
        context = {
            "user_prompt": user_message,
            "session_context": session.get_context_enrichment(),
        }
        context.update(agent_config.get("params", {}))
        return context

    async def _dispatch_progress(
        self,
        callback: Callable[[Dict[str, Any]], Any],
        payload: Dict[str, Any],
    ) -> None:
        if not callback:
            return
        result = callback(payload)
        if inspect.isawaitable(result):
            await result

    async def _run_selected_agents(
        self,
        session: ConversationSession,
        user_message: str,
        selected_agent_configs: List[Dict[str, Any]],
        progress_callback: Optional[Callable[[Dict[str, Any]], Any]] = None,
    ) -> Dict[str, Any]:
        agent_instances = self._get_agent_instances()
        outputs: List[Dict[str, Any]] = []
        total = len(selected_agent_configs)

        for index, agent_config in enumerate(selected_agent_configs, start=1):
            agent_name = agent_config.get("agent")
            if not agent_name:
                raise ValueError("Selected agent config is missing an agent name")

            agent = agent_instances.get(agent_name)
            if not agent:
                raise ValueError(f"Agent '{agent_name}' is not registered or cannot be instantiated")

            await self._dispatch_progress(
                progress_callback,
                {
                    "type": "status",
                    "content": f"Starting {agent_name} ({index}/{total})...",
                    "metadata": {
                        "agent": agent_name,
                        "step": index,
                        "total_steps": total,
                    },
                },
            )

            context = self._build_agent_context(agent_config, user_message, session)
            result = await agent.run(context)
            outputs.append({"agent": agent_name, "result": result})

            await self._dispatch_progress(
                progress_callback,
                {
                    "type": "status",
                    "content": f"{agent_name} completed successfully.",
                    "metadata": {
                        "agent": agent_name,
                        "step": index,
                        "total_steps": total,
                    },
                },
            )

        return {
            "agent_outputs": outputs,
            "completed_tasks": len(outputs),
            "total_tasks": total,
        }

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
                    summaries.append(
                        f"{agent_name} generated {len(result['files'])} files."
                    )
                elif "structure" in result:
                    summaries.append(
                        f"{agent_name} produced a structured result with keys {list(result.keys())}."
                    )
                else:
                    summaries.append(f"{agent_name} produced a result with keys {list(result.keys())}.")
            else:
                summaries.append(f"{agent_name} returned a result of type {type(result).__name__}.")

        if not summaries:
            return (
                brain_result["assistant_response"]
                + " I completed the focused plan, but there was no structured output detected."
            )

        return (
            "I’ve completed the focused execution. "
            + " ".join(summaries)
            + " If you want, I can continue refining the output in the same conversation."
        )
