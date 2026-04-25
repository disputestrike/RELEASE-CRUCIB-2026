from __future__ import annotations

from typing import Any, Dict, List

from .models import ScenarioClassification
from .repository import new_id, now_iso


DOMAIN_MISSING = {
    "sports": [
        "verified current roster and injury report",
        "current standings and seed path",
        "current betting odds or implied probability",
        "recent opponent strength metrics",
    ],
    "business": [
        "actual customer counts by segment",
        "current churn and retention metrics",
        "competitor pricing benchmark",
        "recent customer sentiment",
    ],
    "engineering": [
        "current cost profile",
        "dependency graph",
        "performance baseline",
        "security and compliance constraints",
    ],
    "finance": [
        "latest market prices",
        "recent macro indicators",
        "current policy signals",
    ],
    "politics": [
        "latest official policy text",
        "recent stakeholder statements",
        "current legal constraints",
    ],
}


def build_evidence(
    *,
    simulation_id: str,
    run_id: str,
    prompt: str,
    classification: ScenarioClassification,
    assumptions: List[str],
    attachments: List[Dict[str, Any]],
) -> Dict[str, Any]:
    now = now_iso()
    sources: List[Dict[str, Any]] = [
        {
            "id": new_id("src"),
            "simulation_id": simulation_id,
            "run_id": run_id,
            "type": "user_prompt",
            "title": "User prompt",
            "status": "available",
            "reliability": "medium",
            "freshness": "current_input",
            "url": None,
            "created_at": now,
        }
    ]

    for idx, attachment in enumerate(attachments or []):
        sources.append(
            {
                "id": new_id("src"),
                "simulation_id": simulation_id,
                "run_id": run_id,
                "type": "uploaded_file",
                "title": str(attachment.get("name") or f"Attachment {idx + 1}"),
                "status": "available",
                "reliability": "user_supplied",
                "freshness": "unknown",
                "url": attachment.get("url"),
                "metadata": attachment,
                "created_at": now,
            }
        )

    facts = [
        {
            "id": new_id("fact"),
            "simulation_id": simulation_id,
            "run_id": run_id,
            "source_id": sources[0]["id"],
            "claim": f"User asked: {prompt.strip()}",
            "evidence_type": "prompt_fact",
            "reliability_score": 0.7,
            "freshness_score": 1.0,
            "confidence": 0.7,
            "created_at": now,
        },
        {
            "id": new_id("fact"),
            "simulation_id": simulation_id,
            "run_id": run_id,
            "source_id": sources[0]["id"],
            "claim": classification.interpretation,
            "evidence_type": "scenario_interpretation",
            "reliability_score": 0.65,
            "freshness_score": 1.0,
            "confidence": 0.65,
            "created_at": now,
        },
    ]

    for assumption in assumptions or []:
        facts.append(
            {
                "id": new_id("fact"),
                "simulation_id": simulation_id,
                "run_id": run_id,
                "source_id": sources[0]["id"],
                "claim": assumption,
                "evidence_type": "user_assumption",
                "reliability_score": 0.55,
                "freshness_score": 1.0,
                "confidence": 0.55,
                "created_at": now,
            }
        )

    missing = DOMAIN_MISSING.get(classification.domain, ["verified current data", "external corroborating sources"])
    unsupported_claims = []
    if classification.time_sensitivity == "current":
        unsupported_claims.append("No verified live source was used in this V1 run unless uploaded evidence was provided.")

    data_completeness = min(0.65, 0.25 + (len(attachments or []) * 0.1) + (len(assumptions or []) * 0.05))
    if classification.domain == "general":
        data_completeness = min(data_completeness, 0.4)

    return {
        "sources": sources,
        "evidence": facts,
        "missing_evidence": missing,
        "unsupported_claims": unsupported_claims,
        "assumptions": [
            {
                "id": new_id("asm"),
                "simulation_id": simulation_id,
                "run_id": run_id,
                "assumption": item,
                "source": "user_or_classifier",
                "created_at": now,
            }
            for item in [*(assumptions or []), *classification.assumptions]
        ],
        "quality": {
            "data_completeness": round(data_completeness, 2),
            "source_count": len(sources),
            "fact_count": len(facts),
            "live_data_used": False,
        },
    }

