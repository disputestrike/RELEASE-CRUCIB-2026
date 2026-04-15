"""
Spawn Engine — runs multiple agents IN PARALLEL using asyncio.gather.
This is the speed layer. 8 branches run simultaneously, consensus aggregated.

Strategies:
  diverse_priors       — architect/engineer/reviewer/optimizer
  role_based           — frontend/backend/database/security  
  adversarial          — proponent/critic/neutral/synthesizer
  optimistic_pessimistic — optimist/pessimist/realist/pragmatist
"""
import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

ROLE_MAPS = {
    "diverse_priors":         ["architect", "engineer", "reviewer", "optimizer"],
    "role_based":             ["frontend", "backend", "database", "security"],
    "adversarial":            ["proponent", "critic", "neutral", "synthesizer"],
    "optimistic_pessimistic": ["optimist", "pessimist", "realist", "pragmatist"],
}

# Map role → best CrucibAI agent name from AGENT_DAG
ROLE_TO_AGENT = {
    "architect":   "Architecture Decision Records Agent",
    "engineer":    "Backend Generation",
    "reviewer":    "Code Review Agent",
    "optimizer":   "Performance Profiler",
    "frontend":    "Frontend Generation",
    "backend":     "Backend Generation",
    "database":    "Database Agent",
    "security":    "Security Checker",
    "proponent":   "Requirements Clarifier",
    "critic":      "AgentShield",
    "neutral":     "Code Review Agent",
    "synthesizer": "Build Orchestrator Agent",
    "optimist":    "Performance Vibe Agent",
    "pessimist":   "Security Checker",
    "realist":     "Code Review Agent",
    "pragmatist":  "Build Validator Agent",
}


async def _run_single_branch(agent_name: str, task: str, context: dict,
                              subagent_id: str, job_id: str) -> dict:
    """Run one branch agent. Returns result dict."""
    from adapter.services.event_bridge import on_subagent_started, on_subagent_complete, on_subagent_failed

    on_subagent_started(job_id, subagent_id, agent_name, task)

    try:
        # Use our existing agent execution
        from routes.projects import _run_single_agent_with_context
        from orchestration.planner import generate_plan

        previous_outputs = context.get("previous_outputs", {})
        effective = context.get("effective_keys", {
            "anthropic": None, "cerebras": None, "openai": None
        })
        model_chain = context.get("model_chain", ["cerebras"])

        result = await _run_single_agent_with_context(
            project_id=context.get("project_id", job_id),
            user_id=context.get("user_id", "system"),
            agent_name=agent_name,
            project_prompt=task,
            previous_outputs=previous_outputs,
            effective=effective,
            model_chain=model_chain,
            build_kind=context.get("build_kind"),
        )

        on_subagent_complete(job_id, subagent_id, {
            "output": (result.get("output") or "")[:500],
            "status": result.get("status", "completed"),
        })
        return {"id": subagent_id, "status": "complete", "result": result, "agent": agent_name}

    except Exception as e:
        logger.warning("spawn branch %s failed: %s", agent_name, e)
        on_subagent_failed(job_id, subagent_id, str(e))
        return {"id": subagent_id, "status": "failed", "result": {"error": str(e)}, "agent": agent_name}


class SpawnEngine:
    def __init__(self, job_id: str):
        self.job_id = job_id

    async def spawn(self, task: str, config: dict, context: dict) -> dict:
        """
        Run multiple agents in parallel (asyncio.gather).
        Returns aggregated consensus result.
        """
        mode = config.get("mode", "variant")
        branches = min(int(config.get("branches", 8)), 16)  # cap at 16
        strategy = config.get("strategy", "diverse_priors")
        aggregation = config.get("aggregation", "consensus")

        role_list = ROLE_MAPS.get(strategy, ROLE_MAPS["diverse_priors"])

        # Assign subagent IDs and roles
        subagent_ids = [str(uuid.uuid4()) for _ in range(branches)]
        agents = [
            ROLE_TO_AGENT.get(role_list[i % len(role_list)], "Code Review Agent")
            for i in range(branches)
        ]

        logger.info("spawn: %d branches, strategy=%s, task=%s", branches, strategy, task[:60])

        # Run ALL in parallel — this is the speed advantage
        tasks = [
            _run_single_branch(agents[i], task, context, subagent_ids[i], self.job_id)
            for i in range(branches)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Normalize results
        processed = []
        for r in results:
            if isinstance(r, Exception):
                processed.append({"id": str(uuid.uuid4()), "status": "failed",
                                   "result": {"error": str(r)}})
            else:
                processed.append(r)

        # Aggregate
        consensus = self._aggregate(processed, aggregation)
        success_count = sum(1 for r in processed if r["status"] == "complete")
        confidence = success_count / len(processed) if processed else 0.0

        from adapter.services.event_bridge import on_milestone_reached
        on_milestone_reached(self.job_id, f"Spawn complete — {success_count}/{branches} branches succeeded",
                             f"Confidence: {confidence:.0%}")

        return {
            "consensus": consensus,
            "confidence": confidence,
            "branches": branches,
            "successCount": success_count,
            "disagreements": self._find_disagreements(processed),
            "recommendedAction": "Proceed" if confidence >= 0.5 else "Review",
            "subagentResults": processed,
        }

    async def inject_scenario(self, scenario: str, population_size: int = 32) -> dict:
        """
        Inject a scenario for population-level simulation.
        Runs agents against scenario to assess impact.
        """
        from adapter.services.event_bridge import on_milestone_reached
        on_milestone_reached(self.job_id, f"Scenario: {scenario}", f"Population: {population_size}")

        # Run security + performance agents against the scenario
        scenario_agents = ["AgentShield", "Performance Profiler", "Code Review Agent"]
        tasks = [
            _run_single_branch(agent, f"Analyze scenario: {scenario}", {}, 
                               str(uuid.uuid4()), self.job_id)
            for agent in scenario_agents
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        impacts = []
        risks = []
        for r in results:
            if not isinstance(r, Exception) and r.get("status") == "complete":
                output = r.get("result", {}).get("output", "")
                if "security" in output.lower() or "vulnerability" in output.lower():
                    risks.append("security_concern")
                if "performance" in output.lower() or "slow" in output.lower():
                    impacts.append("performance_impact")

        return {
            "scenario": scenario,
            "populationSize": population_size,
            "impacts": impacts or ["minimal_impact"],
            "risks": risks or ["low"],
            "recommendation": "Safe to proceed" if not risks else "Review security implications",
        }

    def _aggregate(self, results: list, method: str) -> dict:
        """Aggregate branch results into consensus."""
        successful = [r for r in results if r.get("status") == "complete"]
        if not successful:
            return {"error": "All branches failed", "output": ""}

        if method == "consensus":
            # Use result from first successful branch
            best = successful[0]
            return {
                "output": best.get("result", {}).get("output", ""),
                "agent": best.get("agent", ""),
                "branchId": best.get("id", ""),
            }
        elif method == "longest":
            # Use longest output (most complete)
            best = max(successful, key=lambda r: len(r.get("result", {}).get("output", "")))
            return {
                "output": best.get("result", {}).get("output", ""),
                "agent": best.get("agent", ""),
            }
        elif method == "vote":
            # Return all outputs for voting
            return {
                "outputs": [r.get("result", {}).get("output", "") for r in successful],
                "count": len(successful),
            }
        return self._aggregate(results, "consensus")

    def _find_disagreements(self, results: list) -> list:
        """Find branches that produced significantly different outputs."""
        successful = [r for r in results if r.get("status") == "complete"]
        if len(successful) < 2:
            return []
        outputs = [r.get("result", {}).get("output", "") for r in successful]
        # Simple length-based disagreement detection
        avg_len = sum(len(o) for o in outputs) / len(outputs)
        return [
            {"branchId": r.get("id"), "reason": "output_length_divergence"}
            for r, o in zip(successful, outputs)
            if abs(len(o) - avg_len) > avg_len * 0.5
        ]
