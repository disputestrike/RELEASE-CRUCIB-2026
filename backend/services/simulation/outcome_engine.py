from __future__ import annotations

from typing import Any, Dict, List

from .models import ScenarioClassification
from .repository import new_id, now_iso


def _probability_label(value: float) -> str:
    pct = round(max(0.01, min(0.99, value)) * 100)
    return f"{pct}%"


def build_outcomes(
    *,
    simulation_id: str,
    run_id: str,
    prompt: str,
    classification: ScenarioClassification,
    debate: Dict[str, Any],
    evidence_summary: Dict[str, Any],
) -> List[Dict[str, Any]]:
    avg = float(debate.get("average_belief") or 0.42)
    missing = evidence_summary.get("missing_evidence") or []
    evidence_refs = [ev["id"] for ev in (evidence_summary.get("evidence") or [])[:3]]
    policy = (evidence_summary.get("quality") or {}).get("evidence_policy") or {}
    coverage = float((evidence_summary.get("quality") or {}).get("policy_coverage", 0.25) or 0.25)
    style = classification.output_style
    now = now_iso()

    if style == "forecast":
        base = max(0.03, min(0.85, avg))
        templates = [
            ("Base case", base, "Most likely path given current evidence and gaps."),
            ("Optimistic case", min(0.92, base + 0.16), "Key uncertain drivers break favorably."),
            ("Pessimistic case", max(0.02, base - 0.16), "Missing or adverse evidence moves against the scenario."),
            ("Surprise case", max(0.01, min(0.35, base * 0.55)), "A low-probability shock changes the expected path."),
        ]
        probability_key = "probability"
    else:
        base = max(0.1, min(0.9, avg))
        templates = [
            ("Base case", base, "Proceed only with measured guardrails and visible checkpoints."),
            ("Optimistic case", min(0.95, base + 0.18), "Upside is captured with low friction and limited backlash."),
            ("Pessimistic case", max(0.05, base - 0.2), "Execution risk or stakeholder resistance dominates."),
            ("Black swan case", max(0.01, min(0.2, base * 0.4)), "Unexpected external event invalidates the plan."),
        ]
        probability_key = "likelihood"

    outcomes: List[Dict[str, Any]] = []
    for label, likelihood, rationale in templates:
        interval_width = max(0.08, min(0.32, 0.28 - coverage * 0.12))
        lower_bound = max(0.01, likelihood - interval_width)
        upper_bound = min(0.99, likelihood + interval_width)
        watch_triggers = missing[:3] or ["A new high-reliability source contradicts the current claim graph."]
        outcomes.append(
            {
                "id": new_id("outcome"),
                "simulation_id": simulation_id,
                "run_id": run_id,
                "label": label,
                probability_key: round(likelihood, 3),
                "lower_bound": round(lower_bound, 3),
                "upper_bound": round(upper_bound, 3),
                "probability_interval": f"{_probability_label(lower_bound)}-{_probability_label(upper_bound)}",
                "display_likelihood": _probability_label(likelihood),
                "rationale": rationale,
                "key_drivers": classification.required_evidence[:4],
                "risks": missing[:4],
                "assumptions": classification.assumptions,
                "evidence_refs": evidence_refs,
                "what_would_change": watch_triggers,
                "watch_triggers": watch_triggers,
                "evidence_policy_style": policy.get("verdict_style"),
                "created_at": now,
            }
        )
    return outcomes


def build_recommendation(classification: ScenarioClassification, outcomes: List[Dict[str, Any]]) -> Dict[str, Any]:
    base = next((o for o in outcomes if o["label"] == "Base case"), outcomes[0] if outcomes else {})
    likelihood = base.get("probability", base.get("likelihood", 0.0))
    if classification.scenario_type == "forecast":
        return {
            "type": "forecast",
            "summary": f"Estimated base-case likelihood: {base.get('display_likelihood', 'unknown')}.",
            "recommendation": "Treat this as a forecast with high sensitivity to missing current evidence.",
            "forecast_probability": likelihood,
        }
    if classification.scenario_type == "technical_architecture":
        return {
            "type": "tradeoff_matrix",
            "summary": "Use a staged pilot, rollback path, and evidence gates before committing broadly.",
            "recommendation": "Pilot first; do not treat the tradeoff as proven until runtime evidence exists.",
            "recommendation_strength": likelihood,
        }
    return {
        "type": "decision",
        "summary": "Proceed only if the missing evidence is collected or risk is intentionally accepted.",
        "recommendation": "Use the base case as the default and validate the strongest uncertainty before action.",
        "recommendation_strength": likelihood,
    }
