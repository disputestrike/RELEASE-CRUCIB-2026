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

    return {
        "executive_summary": recommendation.get("summary"),
        "scenario_interpretation": classification.model_dump(),
        "evidence_summary": {
            "sources_used": len(evidence_summary.get("sources") or []),
            "facts_extracted": len(evidence_summary.get("evidence") or []),
            "missing_evidence": evidence_summary.get("missing_evidence") or [],
            "unsupported_claims": evidence_summary.get("unsupported_claims") or [],
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
        },
    }
