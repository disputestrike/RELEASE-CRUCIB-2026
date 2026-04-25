from __future__ import annotations

from typing import Any, Dict, List

from .models import ScenarioClassification
from .repository import new_id, now_iso


ROUND_PURPOSES = [
    "Initial interpretation and priors",
    "Evidence review",
    "Challenges and counterarguments",
    "Belief updates and clustering",
    "Final synthesis and outcome generation",
]


def _agent_argument(agent: Dict[str, Any], classification: ScenarioClassification, missing: List[str], round_number: int) -> str:
    role = agent.get("role", "Agent")
    if round_number == 1:
        return f"{role} frames this as a {classification.domain} {classification.scenario_type} and sets an initial belief of {agent.get('current_belief')}."
    if round_number == 2:
        return f"{role} finds available evidence limited and flags missing data: {', '.join(missing[:2])}."
    if round_number == 3:
        return f"{role} challenges overconfidence because the strongest external evidence is not yet verified."
    if round_number == 4:
        return f"{role} updates belief based on evidence completeness and disagreement across the agent arena."
    return f"{role} contributes to the final case distribution and identifies what would change the outcome."


def run_debate(
    *,
    simulation_id: str,
    run_id: str,
    classification: ScenarioClassification,
    agents: List[Dict[str, Any]],
    evidence_summary: Dict[str, Any],
    rounds: int,
) -> Dict[str, Any]:
    max_rounds = max(1, min(int(rounds or 5), 8))
    quality = evidence_summary.get("quality") or {}
    completeness = float(quality.get("data_completeness") or 0.25)
    missing = evidence_summary.get("missing_evidence") or []
    round_rows: List[Dict[str, Any]] = []
    messages: List[Dict[str, Any]] = []
    belief_updates: List[Dict[str, Any]] = []

    mutable_agents = [dict(a) for a in agents]
    for r in range(1, max_rounds + 1):
        round_id = new_id("round")
        purpose = ROUND_PURPOSES[min(r - 1, len(ROUND_PURPOSES) - 1)]
        now = now_iso()
        round_rows.append(
            {
                "id": round_id,
                "simulation_id": simulation_id,
                "run_id": run_id,
                "round_number": r,
                "purpose": purpose,
                "status": "completed",
                "created_at": now,
            }
        )
        for idx, agent in enumerate(mutable_agents):
            previous = float(agent.get("current_belief") or agent.get("prior_belief") or 0.4)
            direction = 1 if idx % 3 == 0 else (-1 if idx % 3 == 1 else 0)
            evidence_drag = (completeness - 0.5) * 0.08
            uncertainty_drag = -0.03 if missing and direction >= 0 else 0.01
            delta = (direction * 0.025) + evidence_drag + uncertainty_drag
            if r == 1:
                delta = 0.0
            new_belief = max(0.05, min(0.9, previous + delta))
            prev_conf = float(agent.get("confidence") or 0.4)
            new_conf = max(0.2, min(0.85, prev_conf + (0.03 if completeness > 0.5 else -0.01)))
            agent["current_belief"] = round(new_belief, 3)
            agent["confidence"] = round(new_conf, 3)
            agent["status"] = "complete"
            agent.setdefault("round_history", []).append({"round": r, "belief": agent["current_belief"]})

            msg_id = new_id("msg")
            messages.append(
                {
                    "id": msg_id,
                    "simulation_id": simulation_id,
                    "run_id": run_id,
                    "round_id": round_id,
                    "agent_id": agent["id"],
                    "round_number": r,
                    "message_type": "argument",
                    "content": _agent_argument(agent, classification, missing, r),
                    "claims": [classification.interpretation],
                    "evidence_cited": [ev["id"] for ev in (evidence_summary.get("evidence") or [])[:2]],
                    "created_at": now,
                }
            )
            if r > 1:
                belief_updates.append(
                    {
                        "id": new_id("belief"),
                        "simulation_id": simulation_id,
                        "run_id": run_id,
                        "round_id": round_id,
                        "agent_id": agent["id"],
                        "previous_belief": round(previous, 3),
                        "new_belief": agent["current_belief"],
                        "previous_confidence": round(prev_conf, 3),
                        "new_confidence": agent["confidence"],
                        "reason": "Belief adjusted from evidence completeness, missing evidence, and peer challenge.",
                        "evidence_refs": [ev["id"] for ev in (evidence_summary.get("evidence") or [])[:2]],
                        "created_at": now,
                    }
                )

    beliefs = [float(a.get("current_belief") or 0.0) for a in mutable_agents]
    avg = sum(beliefs) / max(1, len(beliefs))
    bullish = [a["id"] for a in mutable_agents if float(a.get("current_belief") or 0) >= avg + 0.04]
    bearish = [a["id"] for a in mutable_agents if float(a.get("current_belief") or 0) <= avg - 0.04]
    neutral = [a["id"] for a in mutable_agents if a["id"] not in bullish and a["id"] not in bearish]
    clusters = []
    for label, members in [("bullish", bullish), ("bearish", bearish), ("neutral", neutral)]:
        if members:
            clusters.append(
                {
                    "id": new_id("cluster"),
                    "simulation_id": simulation_id,
                    "run_id": run_id,
                    "label": label,
                    "agent_ids": members,
                    "size": len(members),
                    "centroid_belief": round(
                        sum(float(a.get("current_belief") or 0) for a in mutable_agents if a["id"] in members) / len(members),
                        3,
                    ),
                    "created_at": now_iso(),
                }
            )

    return {
        "agents": mutable_agents,
        "rounds": round_rows,
        "messages": messages,
        "belief_updates": belief_updates,
        "clusters": clusters,
        "agreement": round(1.0 - min(1.0, (max(beliefs or [0]) - min(beliefs or [0]))), 3),
        "average_belief": round(avg, 3),
    }
