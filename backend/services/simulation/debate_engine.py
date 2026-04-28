from __future__ import annotations

from typing import Any, Dict, List, Optional

from .models import ScenarioClassification
from .repository import new_id, now_iso


# One label per round when runs use up to 8 rounds (DEPTH_CONFIG / balanced override).
ROUND_PURPOSES = [
    "Initial interpretation and priors",
    "Evidence review",
    "Challenges and counterarguments",
    "Belief updates and clustering",
    "Stress-testing assumptions under uncertainty",
    "Cross-examination: contested gaps and peer arguments",
    "Scenario forks and second-order effects",
    "Final reconciliation before outcome synthesis",
]


def _normalize_gap(missing: List[Any], fallback: str, idx: int) -> str:
    if not missing:
        return fallback
    raw = missing[idx % len(missing)]
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        return str(raw.get("claim_text") or raw.get("detail") or raw.get("text") or raw.get("issue") or fallback)
    return str(raw)


def _agent_argument(
    agent: Dict[str, Any],
    classification: ScenarioClassification,
    evidence_summary: Dict[str, Any],
    round_number: int,
    *,
    peer_role: Optional[str],
    agent_index: int,
) -> str:
    role = agent.get("role", "Agent")
    peer = (peer_role or "another analyst").strip()
    missing = evidence_summary.get("missing_evidence") or []
    facts = evidence_summary.get("evidence") or []
    fact = (facts[(round_number + len(role) + agent_index) % len(facts)] if facts else {}).get("claim") or ""
    expertise = agent.get("domain_expertise") or "the scenario"
    lm = len(missing)
    gap = _normalize_gap(missing, "additional corroborating evidence", round_number + agent_index * 3)
    gap_alt = _normalize_gap(missing, "verification gaps", round_number + agent_index + 5)

    if round_number == 1:
        return f"{role} frames the question through {expertise} and starts from a {classification.scenario_type.replace('_', ' ')} prior of {agent.get('current_belief')}."
    if round_number == 2:
        if fact:
            return f"{role} weighs available evidence: {fact[:180]}"
        preview = gap if isinstance(gap, str) else str(gap)
        return f"{role} finds available evidence limited and flags missing data: {preview[:200]}."
    if round_number == 3:
        target_gap = gap if lm else "unverified external data"
        return f"{role} presses {peer} on '{target_gap[:200]}', warning that superficial agreement across agents is not independent proof."
    if round_number == 4:
        return f"{role} updates belief after comparing its prior against evidence completeness and {peer}'s objections."

    scenario = classification.scenario_type.replace("_", " ")
    snippet = fact[:160] if fact else ""
    if round_number == 5:
        return (
            f'{role} cross-examines {peer}: they argue {snippet or gap[:200]} anchors the outlook, '
            f"but the decisive swing factor is resolving '{gap_alt[:200]}' under your {scenario} framing."
        )
    if round_number == 6:
        return (
            f"{role} replies to {peer}: even if prior-round evidence largely holds, unexplored '{gap[:200]}' would flip "
            f"whose narrative dominates the simulated population split."
        )
    if round_number == 7:
        return (
            f"{role} proposes a contingency branch: should '{gap_alt[:200]}' materialize, "
            f"they revise exposure relative to {peer}'s stance and re-rank downside drivers."
        )
    return (
        f"{role} summarizes remaining disagreement with {peer} and asserts that tightening '{gap[:200]}' "
        f"would weigh most heavily in shifting the synthesized outcome distribution—not repeating the earlier round verbatim."
    )


def _belief_reason(
    agent: Dict[str, Any],
    classification: ScenarioClassification,
    missing: List[Any],
    completeness: float,
    direction: int,
) -> str:
    role = agent.get("role", "Agent")
    if completeness < 0.45:
        gap = _normalize_gap(missing, "missing corroborating evidence", len(role) + abs(direction))
        return f"{role} moved cautiously because {gap[:220]} remains unresolved."
    if direction > 0:
        return f"{role} increased belief because evidence aligned with its {classification.domain} objective."
    if direction < 0:
        return f"{role} reduced belief after counterarguments exposed downside in its area of expertise."
    return f"{role} held belief steady because evidence and counterarguments remained balanced."


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
        purpose = ROUND_PURPOSES[r - 1] if r <= len(ROUND_PURPOSES) else ROUND_PURPOSES[-1]
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
        n_agents = len(mutable_agents)
        for idx, agent in enumerate(mutable_agents):
            peer_role = mutable_agents[(idx + 1) % n_agents].get("role") if n_agents else None
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
            content = _agent_argument(
                agent,
                classification,
                evidence_summary,
                r,
                peer_role=str(peer_role).strip() if peer_role else None,
                agent_index=idx,
            )
            messages.append(
                {
                    "id": msg_id,
                    "simulation_id": simulation_id,
                    "run_id": run_id,
                    "round_id": round_id,
                    "agent_id": agent["id"],
                    "round_number": r,
                    "message_type": "argument",
                    "content": content,
                    "claims": [classification.interpretation],
                    "evidence_cited": [ev["id"] for ev in (evidence_summary.get("evidence") or [])[:2]],
                    "created_at": now,
                }
            )
            agent["latest_argument"] = content
            agent["latest_round"] = r
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
                        "reason": _belief_reason(agent, classification, missing, completeness, direction),
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
