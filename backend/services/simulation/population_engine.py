from __future__ import annotations

import hashlib
import random
from typing import Any, Dict, List

from .models import ScenarioClassification
from .repository import new_id, now_iso


DEPTH_POPULATION = {
    "fast": 250,
    "balanced": 1000,
    "deep": 5000,
    "maximum": 10000,
}


DOMAIN_COHORTS = {
    "sports": [
        ("model-driven analysts", -0.03, "probability and recent form"),
        ("optimistic fans", 0.11, "upside narrative and momentum"),
        ("skeptical bettors", -0.08, "market discipline and injury variance"),
        ("neutral viewers", 0.0, "broad public uncertainty"),
    ],
    "business": [
        ("price-sensitive customers", -0.12, "budget pressure"),
        ("high-intent buyers", 0.08, "clear value perception"),
        ("sales operators", 0.04, "pipeline mechanics"),
        ("skeptical executives", -0.05, "risk and retention exposure"),
    ],
    "engineering": [
        ("platform engineers", 0.04, "technical leverage"),
        ("security reviewers", -0.08, "control and compliance risk"),
        ("operators", -0.04, "deploy and incident burden"),
        ("product teams", 0.06, "speed and user value"),
    ],
    "finance": [
        ("risk-off investors", -0.09, "downside protection"),
        ("momentum traders", 0.08, "trend following"),
        ("macro analysts", -0.02, "rate and policy uncertainty"),
        ("long-term allocators", 0.03, "strategic horizon"),
    ],
    "politics": [
        ("policy insiders", -0.03, "institutional constraints"),
        ("affected citizens", -0.06, "direct impact and uncertainty"),
        ("market observers", 0.02, "adaptation incentives"),
        ("risk monitors", -0.08, "instability and second-order effects"),
    ],
    "biomedical": [
        ("clinical teams prioritizing safety & equipoise", 0.03, "toxicity-informed adoption"),
        ("patients navigating access & recurrence risk", -0.04, "real-world adherence"),
        ("payers scrutinizing comparative effectiveness", -0.05, "budget and coverage guardrails"),
        ("discovery scientists pursuing translational deltas", 0.05, "mechanistic upside"),
    ],
}


def _seed(prompt: str, run_id: str) -> int:
    digest = hashlib.sha256(f"{prompt}:{run_id}".encode("utf-8")).hexdigest()
    return int(digest[:12], 16)


def build_population_model(
    *,
    simulation_id: str,
    run_id: str,
    prompt: str,
    classification: ScenarioClassification,
    debate: Dict[str, Any],
    evidence_summary: Dict[str, Any],
    depth: str,
    requested_population_size: int | None = None,
) -> Dict[str, Any]:
    quality = evidence_summary.get("quality") or {}
    completeness = float(quality.get("data_completeness") or 0.25)
    average_belief = float(debate.get("average_belief") or 0.42)
    disagreement = 1.0 - float(debate.get("agreement") or 0.5)
    population_size = int(requested_population_size or DEPTH_POPULATION.get(depth, 1000))
    population_size = max(100, min(population_size, 10000))
    cohorts = DOMAIN_COHORTS.get(classification.domain) or [
        ("optimistic stakeholders", 0.08, "upside case"),
        ("skeptical stakeholders", -0.08, "downside risk"),
        ("neutral observers", 0.0, "insufficient evidence"),
        ("risk-sensitive actors", -0.05, "uncertainty and reversibility"),
    ]
    rng = random.Random(_seed(prompt, run_id))
    raw_weights: List[float] = []
    for _, bias, _ in cohorts:
        center = max(0.05, min(0.95, average_belief + bias + rng.uniform(-0.03, 0.03)))
        uncertainty_penalty = 0.08 if completeness < 0.45 and bias > 0 else 0
        raw_weights.append(max(0.05, center - uncertainty_penalty + disagreement * 0.04))
    total = sum(raw_weights) or 1
    now = now_iso()
    clusters: List[Dict[str, Any]] = []
    allocated = 0
    for idx, (label, bias, rationale) in enumerate(cohorts):
        share = raw_weights[idx] / total
        if idx == len(cohorts) - 1:
            size = max(0, population_size - allocated)
        else:
            size = int(round(population_size * share))
            allocated += size
        stance_score = max(0.01, min(0.99, average_belief + bias))
        clusters.append(
            {
                "id": new_id("pop"),
                "simulation_id": simulation_id,
                "run_id": run_id,
                "cluster_type": "population",
                "label": label,
                "size": size,
                "share": round(share, 3),
                "stance_score": round(stance_score, 3),
                "rationale": rationale,
                "expected_shift": "more cautious" if completeness < 0.45 else "evidence-responsive",
                "created_at": now,
            }
        )

    warnings = []
    if not quality.get("live_data_used"):
        warnings.append("Population response is modeled from available prompt evidence, not live external data.")
    if completeness < 0.45:
        warnings.append("Weak evidence reduces population simulation reliability.")

    return {
        "population_size": population_size,
        "method": "core_agents_plus_synthetic_population",
        "depth": depth,
        "clusters": clusters,
        "warnings": warnings,
        "summary": (
            f"Modeled {population_size:,} synthetic perspectives from core agent beliefs, "
            "evidence completeness, and domain-specific cohort bias."
        ),
    }
