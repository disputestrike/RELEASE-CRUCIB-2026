from __future__ import annotations

from typing import Any, Dict, List

from .models import ScenarioClassification


def _likelihood(outcome: Dict[str, Any]) -> float:
    return float(outcome.get("probability", outcome.get("likelihood", 0.0)) or 0.0)


def _confidence_interval(probability: float, trust_score: float, evidence_coverage: float) -> Dict[str, float]:
    uncertainty = max(0.08, min(0.38, 0.34 - (trust_score * 0.16) + ((1 - evidence_coverage) * 0.16)))
    lower = max(0.01, probability - uncertainty)
    upper = min(0.99, probability + uncertainty)
    return {"lower_bound": round(lower, 3), "upper_bound": round(upper, 3), "uncertainty_width": round(upper - lower, 3)}


def _terminal_verdict(
    *,
    probability: float,
    lower_bound: float,
    upper_bound: float,
    evidence_coverage: float,
    minimum_coverage: float,
    trust_score: float,
    official_gate_failed: bool,
) -> str:
    if evidence_coverage < minimum_coverage or official_gate_failed or trust_score < 0.22:
        return "Insufficient Evidence"
    if probability >= 0.65 and lower_bound > 0.5:
        return "Yes"
    if probability <= 0.35 and upper_bound < 0.5:
        return "No"
    return "Unclear"


def _next_best_action(verdict: str, classification: ScenarioClassification, missing: List[str]) -> str:
    def _gap_preview(raw: Any) -> str:
        if isinstance(raw, dict):
            return str(raw.get("claim_text") or raw.get("detail") or raw)[:220]
        return str(raw)[:220]

    if verdict == "Insufficient Evidence":
        needed = missing[0] if missing else "the highest-quality missing source"
        if classification.domain == "biomedical":
            return (
                f"Bench this until PubMed/registry/FDA-tier connectors substantiate competing modalities; "
                f"first gap to close: {_gap_preview(needed)}."
            )
        if classification.scenario_type == "short_horizon_forecast":
            return (
                "Acquire authoritative tape timestamps plus earnings/catalyst calendars before directional trade language; "
                f"nearest missing layer: {_gap_preview(needed)}."
            )
        return f"Collect or connect {needed} before treating this as decision-grade."

    if classification.scenario_type == "research_discovery":
        return (
            "Queue structured literature + trial-registry pulls (Europe PMC/AACT parity) "
            "and map subtype-specific equipoise—not headline cure percentages—to the next assays."
        )
    if classification.scenario_type == "short_horizon_forecast":
        return (
            "Continuously ingest live quotations, imbalances, filings, EPS dates, consensus deltas—rerun once connectors satisfy timestamp parity."
        )
    if classification.scenario_type == "forecast":
        return "Track the watch triggers and rerun when fresh evidence changes."
    if classification.domain == "engineering":
        return "Run a staged pilot with telemetry, rollback criteria, and explicit go/no-go gates."
    if classification.domain in {"business", "product"}:
        return "Run a controlled experiment or segmented rollout before full commitment."
    return "Use the verdict as a provisional decision memo and monitor the strongest counterfactuals."


def build_final_verdict(
    *,
    classification: ScenarioClassification,
    evidence_summary: Dict[str, Any],
    outcomes: List[Dict[str, Any]],
    trust: Dict[str, Any],
) -> Dict[str, Any]:
    quality = evidence_summary.get("quality") or {}
    policy = quality.get("evidence_policy") or {}
    base = next((item for item in outcomes if item.get("label") == "Base case"), outcomes[0] if outcomes else {})
    probability = max(0.01, min(0.99, _likelihood(base)))
    evidence_coverage = float(quality.get("policy_coverage", quality.get("data_completeness", 0.0)) or 0.0)
    minimum_coverage = float(policy.get("minimum_coverage", 0.52) or 0.52)
    trust_score = float(trust.get("score") or 0.0)
    live_data_used = bool(quality.get("live_data_used"))
    official_required = bool(policy.get("official_required_for_strong_verdict"))
    official_gate_failed = bool(
        official_required
        and classification.time_sensitivity in {"current", "future"}
        and not live_data_used
    )
    interval = _confidence_interval(probability, trust_score, evidence_coverage)
    verdict = _terminal_verdict(
        probability=probability,
        lower_bound=interval["lower_bound"],
        upper_bound=interval["upper_bound"],
        evidence_coverage=evidence_coverage,
        minimum_coverage=minimum_coverage,
        trust_score=trust_score,
        official_gate_failed=official_gate_failed,
    )
    missing = evidence_summary.get("missing_evidence") or []
    claims = evidence_summary.get("claims") or []
    supporting = [claim for claim in claims if claim.get("supports_or_refutes") == "supports"][:3]
    opposing = [claim for claim in claims if claim.get("supports_or_refutes") == "refutes"][:3]
    if not supporting:
        supporting = claims[:2]
    if not opposing:
        opposing = [{"claim_text": item, "reason": "missing evidence"} for item in missing[:2]]

    watch_triggers = []
    for outcome in outcomes:
        for item in outcome.get("what_would_change") or []:
            if item not in watch_triggers:
                watch_triggers.append(item)

    return {
        "verdict": verdict,
        "probability": round(probability, 3),
        **interval,
        "confidence_label": trust.get("trust_score") or "Low",
        "decision_boundary": 0.5,
        "evidence_coverage": round(evidence_coverage, 3),
        "minimum_coverage": round(minimum_coverage, 3),
        "official_gate_failed": official_gate_failed,
        "why": (base.get("rationale") or "The base case reflects the current claim graph, debate, and trust score."),
        "strongest_evidence_for": supporting,
        "strongest_evidence_against": opposing,
        "counterfactual_triggers": watch_triggers[:6],
        "next_best_action": _next_best_action(verdict, classification, missing),
        "contract": "Every run resolves to Yes, No, Unclear, or Insufficient Evidence with a probability interval and audit trail.",
    }
