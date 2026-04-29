from __future__ import annotations

from typing import Any, Dict, List

from .models import ScenarioClassification


def build_report(
    *,
    prompt: str,
    classification: ScenarioClassification,
    evidence_summary: Dict[str, Any],
    agents: List[Dict[str, Any]],
    debate: Dict[str, Any],
    outcomes: List[Dict[str, Any]],
    recommendation: Dict[str, Any],
    trust: Dict[str, Any],
    simulation_id: str,
    run_id: str,
    population_model: Dict[str, Any] | None = None,
    final_verdict: Dict[str, Any] | None = None,
    output_answer: Dict[str, Any] | None = None,
    routed_intent: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    disagreements = []
    for cluster in debate.get("clusters") or []:
        disagreements.append(
            {
                "cluster": cluster.get("label"),
                "size": cluster.get("size"),
                "centroid_belief": cluster.get("centroid_belief"),
            }
        )

    verdict = final_verdict or {}
    executive = verdict.get("verdict")
    if executive:
        executive = (
            f"{executive}: {recommendation.get('summary')} "
            f"Interval {round(float(verdict.get('lower_bound', 0)) * 100)}-"
            f"{round(float(verdict.get('upper_bound', 0)) * 100)}%."
        )
    else:
        executive = recommendation.get("summary")

    return {
        "executive_summary": executive,
        "final_verdict": verdict,
        "scenario_interpretation": classification.model_dump(),
        "evidence_summary": {
            "sources_used": len(evidence_summary.get("sources") or []),
            "facts_extracted": len(evidence_summary.get("evidence") or []),
            "claims_created": len(evidence_summary.get("claims") or []),
            "missing_evidence": evidence_summary.get("missing_evidence") or [],
            "unsupported_claims": evidence_summary.get("unsupported_claims") or [],
            "evidence_policy": (evidence_summary.get("quality") or {}).get("evidence_policy") or {},
            "claim_graph_preview": (evidence_summary.get("claims") or [])[:8],
        },
        "agent_consensus_disagreement": {
            "agent_count": len(agents),
            "agreement": debate.get("agreement"),
            "major_disagreements": disagreements,
        },
        "population_model": population_model or {},
        "belief_shifts": (debate.get("belief_updates") or [])[:20],
        "outcomes": outcomes,
        "recommendation": recommendation,
        "trust_score": trust,
        "strongest_evidence_for": verdict.get("strongest_evidence_for") or [],
        "strongest_evidence_against": verdict.get("strongest_evidence_against") or [],
        "what_would_change_the_outcome": sorted(
            {
                item
                for outcome in outcomes
                for item in (outcome.get("what_would_change") or [])
            }
        )[:8],
        "next_data_to_collect": evidence_summary.get("missing_evidence") or [],
        "replay_metadata": {
            "simulation_id": simulation_id,
            "run_id": run_id,
            "input_prompt": prompt,
            "engine": "Reality Engine V1",
            "live_data_used": bool((evidence_summary.get("quality") or {}).get("live_data_used")),
            "replay_scope": "core-agent transcript plus aggregated population cohorts",
        },
        "output_answer": output_answer or {},
        "routed_intent": routed_intent or {},
    }
