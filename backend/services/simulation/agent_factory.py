from __future__ import annotations

from typing import Any, Dict, List

from .models import ScenarioClassification
from .repository import new_id, now_iso


DOMAIN_AGENTS = {
    "sports": [
        ("Basketball Performance Analyst", "team performance, form, and efficiency", 0.42, "balanced"),
        ("Injury Risk Analyst", "player health and availability impact", 0.35, "skeptical"),
        ("Betting Market Analyst", "market odds and implied probability", 0.40, "data_first"),
        ("Playoff Path Analyst", "seeding, matchups, and opponent strength", 0.38, "skeptical"),
        ("Historical Trends Analyst", "historical title patterns and precedent", 0.37, "historical"),
        ("Optimistic Fan Sentiment Agent", "public momentum and upside narrative", 0.48, "optimistic"),
        ("Opponent Strength Analyst", "field strength and rival risk", 0.34, "skeptical"),
        ("Uncertainty Auditor", "unknowns, variance, and missing data", 0.30, "cautious"),
    ],
    "business": [
        ("Revenue Analyst", "revenue lift and pricing mechanics", 0.52, "financial"),
        ("Customer Churn Analyst", "retention and churn downside", 0.36, "skeptical"),
        ("Competitive Pricing Analyst", "market price positioning", 0.45, "market"),
        ("Sales Leader", "pipeline and close-rate effects", 0.48, "commercial"),
        ("Customer Success Agent", "customer trust and support burden", 0.38, "customer_first"),
        ("Brand Risk Agent", "perception and reputation", 0.40, "risk"),
        ("CFO Agent", "margin and cash impact", 0.50, "financial"),
        ("Skeptical User Advocate", "user pain and objections", 0.32, "skeptical"),
    ],
    "engineering": [
        ("Architecture Analyst", "system design and migration path", 0.46, "balanced"),
        ("Security Analyst", "security and compliance exposure", 0.36, "security_first"),
        ("Cost Analyst", "infra and operating cost", 0.50, "cost_sensitive"),
        ("Migration Risk Analyst", "cutover and rollback risk", 0.34, "skeptical"),
        ("Performance Analyst", "latency, scale, and reliability", 0.44, "performance"),
        ("Developer Experience Agent", "team velocity and maintainability", 0.48, "dx"),
        ("Operations Agent", "deploy, observability, and incident risk", 0.38, "ops"),
        ("Compliance Agent", "policy and audit constraints", 0.35, "compliance"),
    ],
    "finance": [
        ("Macro Analyst", "macro signals and rates", 0.42, "macro"),
        ("Market Structure Analyst", "liquidity and positioning", 0.40, "market"),
        ("Risk Analyst", "downside exposure", 0.34, "risk"),
        ("Historical Modeler", "historical analogs", 0.38, "historical"),
        ("Policy Analyst", "policy and regulatory drivers", 0.36, "policy"),
        ("Sentiment Analyst", "market narrative and confidence", 0.44, "sentiment"),
    ],
    "politics": [
        ("Policy Analyst", "policy mechanics and constraints", 0.40, "policy"),
        ("Geopolitical Risk Analyst", "state actor and conflict risk", 0.34, "risk"),
        ("Legal Analyst", "legal and regulatory exposure", 0.36, "legal"),
        ("Stakeholder Analyst", "stakeholder incentives", 0.42, "stakeholder"),
        ("Historical Precedent Analyst", "similar past decisions", 0.37, "historical"),
        ("Public Sentiment Analyst", "public response and legitimacy", 0.43, "sentiment"),
    ],
}

FALLBACK_AGENTS = [
    ("Scenario Analyst", "problem framing and interpretation", 0.45, "balanced"),
    ("Evidence Analyst", "available facts and missing data", 0.40, "data_first"),
    ("Risk Analyst", "downside and uncertainty", 0.35, "risk"),
    ("Optimist Agent", "upside case", 0.55, "optimistic"),
    ("Skeptic Agent", "failure modes", 0.32, "skeptical"),
    ("Decision Analyst", "final recommendation", 0.46, "decision"),
]


def build_agents(
    *,
    simulation_id: str,
    run_id: str,
    classification: ScenarioClassification,
    agent_count: int,
    evidence_summary: Dict[str, Any],
) -> List[Dict[str, Any]]:
    templates = DOMAIN_AGENTS.get(classification.domain) or FALLBACK_AGENTS
    n = max(3, min(int(agent_count or len(templates)), 24))
    selected = [templates[i % len(templates)] for i in range(n)]
    completeness = float((evidence_summary.get("quality") or {}).get("data_completeness") or 0.25)
    now = now_iso()
    agents = []
    for idx, (name, expertise, prior, persona) in enumerate(selected):
        confidence = max(0.25, min(0.78, 0.35 + completeness * 0.4))
        agents.append(
            {
                "id": new_id("agent"),
                "simulation_id": simulation_id,
                "run_id": run_id,
                "name": name,
                "role": name,
                "domain_expertise": expertise,
                "persona": persona,
                "prior_belief": round(prior, 2),
                "current_belief": round(prior, 2),
                "confidence": round(confidence, 2),
                "risk_tolerance": "low" if persona in {"skeptical", "risk", "security_first", "compliance"} else "medium",
                "objective": f"Evaluate the {classification.domain} {classification.scenario_type} from the lens of {expertise}.",
                "evidence_access": [source["id"] for source in evidence_summary.get("sources", [])],
                "memory": [],
                "status": "ready",
                "round_history": [],
                "created_at": now,
            }
        )
    return agents

