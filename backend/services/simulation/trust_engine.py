from __future__ import annotations

from typing import Any, Dict, List

from .models import ScenarioClassification
from .repository import new_id, now_iso


def _band(score: float) -> str:
    if score >= 0.74:
        return "High"
    if score >= 0.48:
        return "Medium"
    return "Low"


def build_trust_score(
    *,
    simulation_id: str,
    run_id: str,
    classification: ScenarioClassification,
    evidence_summary: Dict[str, Any],
    debate: Dict[str, Any],
) -> Dict[str, Any]:
    quality = evidence_summary.get("quality") or {}
    completeness = float(quality.get("data_completeness") or 0.25)
    live_data = bool(quality.get("live_data_used"))
    source_count = int(quality.get("source_count") or 0)
    live_source_count = int(quality.get("live_source_count") or 0)
    missing_count = len(evidence_summary.get("missing_evidence") or [])
    agreement = float(debate.get("agreement") or 0.5)
    recency_sensitivity = 0.85 if classification.time_sensitivity == "current" else 0.45
    facts = evidence_summary.get("evidence") or []
    sources = evidence_summary.get("sources") or []
    traceability = float(quality.get("traceability") or 0.45)
    policy_coverage = float(quality.get("policy_coverage", completeness) or completeness)
    reliability_scores = [float(source.get("reliability_score") or 0.45) for source in sources]
    source_quality = sum(reliability_scores) / max(1, len(reliability_scores))
    source_types = {str(source.get("type") or "unknown") for source in sources}
    source_diversity = min(1.0, (len(source_types) + live_source_count) / 5)
    calibration_score = 0.5
    unsupported_consensus_penalty = 0.0
    if completeness < 0.45 and agreement > 0.75:
        unsupported_consensus_penalty = 0.45
    elif not live_data and agreement > 0.8:
        unsupported_consensus_penalty = 0.25

    components = {
        "source_quality": round(min(1.0, max(source_quality, 0.25 + completeness * 0.45)), 2),
        "evidence_freshness": 0.78 if live_data else (0.45 if classification.time_sensitivity == "current" else 0.62),
        "evidence_coverage": round(policy_coverage, 2),
        "traceability": round(traceability, 2),
        "source_diversity": round(source_diversity, 2),
        "calibration_score": calibration_score,
        "unsupported_consensus_penalty": round(unsupported_consensus_penalty, 2),
        "source_reliability": round(min(0.9, 0.35 + source_count * 0.12), 2),
        "data_completeness": round(completeness, 2),
        "agent_agreement": round(agreement, 2),
        "simulation_stability": round(min(0.85, 0.45 + agreement * 0.35), 2),
        "uncertainty_level": round(max(0.1, min(1.0, 0.25 + missing_count * 0.08 + (0.15 if not live_data else 0))), 2),
        "domain_fit": 0.85 if classification.domain != "general" else 0.55,
        "recency_sensitivity": round(recency_sensitivity, 2),
    }
    score = (
        components["source_quality"] * 0.25
        + components["evidence_freshness"] * 0.15
        + components["evidence_coverage"] * 0.15
        + components["traceability"] * 0.15
        + components["source_diversity"] * 0.10
        + components["calibration_score"] * 0.10
        + (1 - components["unsupported_consensus_penalty"]) * 0.10
    )
    weak_evidence_penalty = 0.12 if completeness < 0.45 and agreement > 0.75 else 0
    penalty = (
        components["uncertainty_level"] * 0.15
        + (0.08 if components["recency_sensitivity"] > 0.7 and not live_data else 0)
        + weak_evidence_penalty
    )
    score = max(0.05, min(0.95, score - penalty))
    warnings: List[str] = []
    if not live_data and classification.time_sensitivity == "current":
        warnings.append("Current or time-sensitive scenario; no verified live data source was used.")
    if missing_count:
        warnings.append("Important evidence is missing; treat forecast and recommendation as provisional.")
    if agreement < 0.65:
        warnings.append("Agent disagreement is material.")
    if completeness < 0.45 and agreement > 0.75:
        warnings.append("High agent agreement is not strong proof because evidence completeness is weak.")
    if unsupported_consensus_penalty:
        warnings.append("Unsupported-consensus penalty applied: agreement was discounted because the claim graph is weak.")
    if not facts:
        warnings.append("No extracted evidence facts are available.")

    return {
        "id": new_id("trust"),
        "simulation_id": simulation_id,
        "run_id": run_id,
        "trust_score": _band(score),
        "score": round(score, 3),
        "components": components,
        "formula": "0.25Q + 0.15F + 0.15C + 0.15T + 0.10D + 0.10K + 0.10(1-P)",
        "warnings": warnings,
        "confidence_types": {
            "evidence_confidence": _band((components["source_quality"] + components["source_reliability"]) / 2),
            "forecast_confidence": _band(score if classification.scenario_type == "forecast" else score * 0.85),
            "recommendation_confidence": _band(score if classification.scenario_type != "forecast" else score * 0.8),
            "agent_agreement_confidence": _band(agreement),
        },
        "created_at": now_iso(),
    }
