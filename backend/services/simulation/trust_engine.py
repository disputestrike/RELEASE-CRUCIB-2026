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
    missing_count = len(evidence_summary.get("missing_evidence") or [])
    agreement = float(debate.get("agreement") or 0.5)
    recency_sensitivity = 0.85 if classification.time_sensitivity == "current" else 0.45

    components = {
        "evidence_quality": round(min(1.0, 0.35 + completeness * 0.7), 2),
        "evidence_freshness": 0.78 if live_data else (0.45 if classification.time_sensitivity == "current" else 0.62),
        "source_reliability": round(min(0.9, 0.35 + source_count * 0.12), 2),
        "data_completeness": round(completeness, 2),
        "agent_agreement": round(agreement, 2),
        "simulation_stability": round(min(0.85, 0.45 + agreement * 0.35), 2),
        "uncertainty_level": round(max(0.1, min(1.0, 0.25 + missing_count * 0.08 + (0.15 if not live_data else 0))), 2),
        "domain_fit": 0.85 if classification.domain != "general" else 0.55,
        "recency_sensitivity": round(recency_sensitivity, 2),
    }
    positive = (
        components["evidence_quality"] * 0.18
        + components["evidence_freshness"] * 0.12
        + components["source_reliability"] * 0.12
        + components["data_completeness"] * 0.22
        + min(components["agent_agreement"], components["data_completeness"] + 0.18) * 0.08
        + components["simulation_stability"] * 0.1
        + components["domain_fit"] * 0.1
    )
    weak_evidence_penalty = 0.12 if completeness < 0.45 and agreement > 0.75 else 0
    penalty = (
        components["uncertainty_level"] * 0.15
        + (0.08 if components["recency_sensitivity"] > 0.7 and not live_data else 0)
        + weak_evidence_penalty
    )
    score = max(0.05, min(0.95, positive - penalty))
    warnings: List[str] = []
    if not live_data and classification.time_sensitivity == "current":
        warnings.append("Current or time-sensitive scenario; no verified live data source was used.")
    if missing_count:
        warnings.append("Important evidence is missing; treat forecast and recommendation as provisional.")
    if agreement < 0.65:
        warnings.append("Agent disagreement is material.")
    if completeness < 0.45 and agreement > 0.75:
        warnings.append("High agent agreement is not strong proof because evidence completeness is weak.")

    return {
        "id": new_id("trust"),
        "simulation_id": simulation_id,
        "run_id": run_id,
        "trust_score": _band(score),
        "score": round(score, 3),
        "components": components,
        "warnings": warnings,
        "confidence_types": {
            "evidence_confidence": _band((components["evidence_quality"] + components["source_reliability"]) / 2),
            "forecast_confidence": _band(score if classification.scenario_type == "forecast" else score * 0.85),
            "recommendation_confidence": _band(score if classification.scenario_type != "forecast" else score * 0.8),
            "agent_agreement_confidence": _band(agreement),
        },
        "created_at": now_iso(),
    }
