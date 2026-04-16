"""Semantic routing for planner intent assessment and agent selection."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


class IntentClassifier:
    """Classify user intent from natural language hints."""

    INTENT_PATTERNS = {
        "code_analysis": {
            "keywords": [
                "analyze",
                "review",
                "code quality",
                "inspect",
                "structure",
                "refactor",
                "complexity",
            ],
            "agents": ["CodeAnalysisAgent"],
            "confidence_boost": ["code", "function", "class", "method"],
        },
        "testing": {
            "keywords": ["test", "debug", "failing", "error", "broken", "unit test", "pytest", "coverage"],
            "agents": ["TerminalAgent"],
            "confidence_boost": ["pytest", "failing", "test_", "unittest"],
        },
        "execution": {
            "keywords": ["run", "execute", "build", "compile", "deploy", "start", "launch"],
            "agents": ["TerminalAgent"],
            "confidence_boost": ["npm", "python", "make", "docker"],
        },
        "generation": {
            "keywords": ["generate", "create", "write", "implement", "build"],
            "agents": ["BackendAgent", "FrontendAgent"],
            "confidence_boost": ["function", "component", "class", "api"],
        },
        "exploration": {
            "keywords": ["find", "search", "locate", "where", "look for", "navigate", "structure", "project"],
            "agents": ["WorkspaceExplorerAgent"],
            "confidence_boost": ["find", "search", "grep", "directory", "file"],
        },
        "explanation": {
            "keywords": ["explain", "what", "how", "why", "understand", "clarify", "document"],
            "agents": ["CodeAnalysisAgent", "DocumentationAgent"],
            "confidence_boost": ["how", "what", "why", "explain"],
        },
        "deployment": {
            "keywords": ["deploy", "release", "production", "staging", "docker", "kubernetes", "aws"],
            "agents": ["DeploymentAgent"],
            "confidence_boost": ["deploy", "docker", "k8s", "production"],
        },
        "version_control": {
            "keywords": ["git", "commit", "push", "pull", "branch", "merge", "github"],
            "agents": ["TerminalAgent"],
            "confidence_boost": ["git", "commit", "github"],
        },
    }

    @staticmethod
    def classify(text: str) -> Tuple[str, float]:
        text_lower = text.lower()
        best_intent = "general"
        best_confidence = 0.0

        for intent, patterns in IntentClassifier.INTENT_PATTERNS.items():
            confidence = 0.0
            keyword_matches = sum(1 for kw in patterns["keywords"] if kw in text_lower)
            if keyword_matches > 0:
                confidence = keyword_matches / len(patterns["keywords"])
            for boost_kw in patterns.get("confidence_boost", []):
                if boost_kw in text_lower:
                    confidence += 0.2
            if confidence > best_confidence:
                best_confidence = confidence
                best_intent = intent

        return best_intent, min(1.0, best_confidence)


class SemanticRouter:
    """Routes requests to the best agent set for the current intent."""

    def __init__(self, agent_registry: Optional[Dict[str, Any]] = None):
        self.agent_registry = agent_registry or {}
        self.routing_history: List[Dict[str, Any]] = []
        self.learned_patterns: Dict[str, List[str]] = {}

    def route(self, user_request: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        context = context or {}
        intent, intent_confidence = IntentClassifier.classify(user_request)
        intent_patterns = IntentClassifier.INTENT_PATTERNS.get(intent, {})
        recommended_agents = intent_patterns.get("agents", [])

        primary_agents = []
        secondary_agents = []
        for agent_name in recommended_agents:
            agent_config = self._score_agent(agent_name, user_request, context)
            if agent_config["confidence"] >= 0.7:
                primary_agents.append(agent_config)
            else:
                secondary_agents.append(agent_config)

        if not primary_agents:
            learned = self._find_learned_patterns(user_request)
            if learned:
                primary_agents.append(learned)
            else:
                primary_agents.append(
                    {
                        "agent": "PlannerAgent",
                        "confidence": 0.5,
                        "params": {"user_prompt": user_request},
                        "reasoning": "Generic fallback - no specific intent detected",
                    }
                )

        result = {
            "primary_agents": primary_agents,
            "secondary_agents": secondary_agents,
            "intent": intent,
            "intent_confidence": intent_confidence,
            "reasoning": self._generate_reasoning(intent, primary_agents, intent_confidence),
        }
        self._record_routing(user_request, result)
        return result

    def route_sequence(self, user_request: str, max_agents: int = 3) -> List[Dict[str, Any]]:
        routing = self.route(user_request)
        agents = routing["primary_agents"] + routing["secondary_agents"]
        agents.sort(key=lambda item: item["confidence"], reverse=True)
        return agents[:max_agents]

    def _score_agent(self, agent_name: str, user_request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        score = 0.5
        request_lower = user_request.lower()

        if agent_name == "CodeAnalysisAgent":
            if any(kw in request_lower for kw in ["analyze", "review", "code", "complexity", "quality"]):
                score += 0.3
            if "code_content" in context or "file_path" in context:
                score += 0.2
        elif agent_name == "WorkspaceExplorerAgent":
            if any(kw in request_lower for kw in ["find", "search", "locate", "explore", "structure"]):
                score += 0.3
            if "search" in request_lower:
                score += 0.2
        elif agent_name == "TerminalAgent":
            if any(kw in request_lower for kw in ["run", "test", "build", "execute", "git"]):
                score += 0.3
            if "pytest" in request_lower or "test" in request_lower:
                score += 0.2
        elif agent_name == "BackendAgent":
            if any(kw in request_lower for kw in ["backend", "api", "server", "database"]):
                score += 0.3
        elif agent_name == "FrontendAgent":
            if any(kw in request_lower for kw in ["frontend", "ui", "component", "react"]):
                score += 0.3

        params = self._extract_params(agent_name, user_request, context)
        return {
            "agent": agent_name,
            "confidence": min(1.0, score),
            "params": params,
            "reasoning": "Agent selected based on request keywords and context",
        }

    def _extract_params(self, agent_name: str, user_request: str, context: Dict[str, Any]) -> Dict[str, Any]:
        params = {"user_prompt": user_request}
        if "code_content" in context:
            params["code_content"] = context["code_content"]
        if "file_path" in context:
            params["file_path"] = context["file_path"]

        lowered = user_request.lower()
        if agent_name == "CodeAnalysisAgent":
            if "analyze all" in lowered:
                params["analysis_type"] = "all"
            elif "structure" in lowered:
                params["analysis_type"] = "structure"
            elif "issues" in lowered:
                params["analysis_type"] = "issues"
        elif agent_name == "WorkspaceExplorerAgent":
            if "search" in lowered:
                params["action"] = "search"
                if "for" in user_request:
                    params["query"] = user_request.split("for")[-1].strip()
            elif "find" in lowered:
                params["action"] = "locate_pattern"
            elif "structure" in lowered:
                params["action"] = "project_map"
        elif agent_name == "TerminalAgent":
            if "test" in lowered:
                params["action"] = "run_test"
            elif "build" in lowered:
                params["action"] = "build"
            elif "git" in lowered:
                params["action"] = "git_command"

        return params

    def _find_learned_patterns(self, user_request: str) -> Optional[Dict[str, Any]]:
        request_lower = user_request.lower()
        for pattern, agents in self.learned_patterns.items():
            if pattern in request_lower and agents:
                return {
                    "agent": agents[0],
                    "confidence": 0.65,
                    "params": {"user_prompt": user_request},
                    "reasoning": "Selected based on learned patterns",
                }
        return None

    def _generate_reasoning(self, intent: str, agents: List[Dict[str, Any]], confidence: float) -> str:
        agent_names = ", ".join(agent["agent"] for agent in agents[:2])
        if confidence >= 0.8:
            certainty = "highly confident"
        elif confidence >= 0.6:
            certainty = "moderately confident"
        else:
            certainty = "uncertain"
        return (
            f"I'm {certainty} your intent is '{intent}' (confidence: {confidence:.0%}). "
            f"Routing to {agent_names} based on request analysis."
        )

    def _record_routing(self, user_request: str, result: Dict[str, Any]) -> None:
        self.routing_history.append(
            {
                "request": user_request,
                "intent": result["intent"],
                "agents": [agent["agent"] for agent in result["primary_agents"]],
                "timestamp": str(__import__("datetime").datetime.now()),
            }
        )
        if len(self.routing_history) > 1000:
            self.routing_history = self.routing_history[-1000:]

    def export_routing_stats(self) -> Dict[str, Any]:
        intent_counts: Dict[str, int] = {}
        agent_counts: Dict[str, int] = {}
        for record in self.routing_history:
            intent = record["intent"]
            intent_counts[intent] = intent_counts.get(intent, 0) + 1
            for agent in record["agents"]:
                agent_counts[agent] = agent_counts.get(agent, 0) + 1
        return {
            "total_routings": len(self.routing_history),
            "intents": intent_counts,
            "agents_used": agent_counts,
        }