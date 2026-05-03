from __future__ import annotations

from typing import Any, Dict, List

from .models import ScenarioClassification


SOURCE_PRECEDENCE = [
    "official_api_fetcher",
    "authorized_enterprise_connector",
    "targeted_web_search",
    "controlled_browser_crawl",
    "user_upload",
    "generic_web_source",
]

OUTPUT_CONTRACT = [
    "one_line_verdict",
    "calibrated_probability_interval",
    "top_supporting_claims",
    "top_opposing_claims",
    "sensitivity_triggers",
    "next_best_action",
    "replay_handle",
]

TERMINAL_STATES = ["Yes", "No", "Unclear", "Insufficient Evidence"]


DOMAIN_POLICIES: Dict[str, Dict[str, Any]] = {
    "sports": {
        "required_evidence_classes": [
            "official schedule, standings, and seed path",
            "current roster and injury availability",
            "recent form and opponent strength",
            "market odds or implied probability",
            "historical tournament or championship analogs",
        ],
        "preferred_connectors": [
            "official league feed",
            "team reports",
            "licensed odds/injury provider",
            "targeted Tavily search",
            "controlled Playwright crawl",
        ],
        "minimum_coverage": 0.62,
        "official_required_for_strong_verdict": True,
        "verdict_style": "probability_interval",
    },
    "finance": {
        "required_evidence_classes": [
            "live market prices",
            "primary filings or financial statements",
            "macro indicators",
            "policy or rate signals",
            "analyst or market consensus",
        ],
        "preferred_connectors": ["SEC EDGAR", "FRED", "market data API", "targeted Tavily search"],
        "minimum_coverage": 0.68,
        "official_required_for_strong_verdict": True,
        "verdict_style": "risk_reward_interval",
    },
    "politics": {
        "required_evidence_classes": [
            "official policy or legal text",
            "current agency or government statements",
            "stakeholder positions",
            "legal constraints",
            "recent public signal",
        ],
        "preferred_connectors": ["Federal Register", "Regulations.gov", "agency API", "targeted Tavily search"],
        "minimum_coverage": 0.66,
        "official_required_for_strong_verdict": True,
        "verdict_style": "yes_no_unclear",
    },
    "engineering": {
        "required_evidence_classes": [
            "current architecture",
            "cost profile",
            "telemetry or performance baseline",
            "dependency graph",
            "security and compliance constraints",
            "rollback criteria",
        ],
        "preferred_connectors": ["GitHub", "Datadog", "CloudWatch", "Jira", "warehouse export"],
        "minimum_coverage": 0.58,
        "official_required_for_strong_verdict": False,
        "verdict_style": "go_no_go_with_prerequisites",
    },
    "business": {
        "required_evidence_classes": [
            "revenue and pricing baseline",
            "customer segments",
            "churn and retention data",
            "competitor pricing",
            "customer sentiment",
            "experiment or rollout plan",
        ],
        "preferred_connectors": ["PayPal", "Salesforce", "warehouse", "support export", "targeted Tavily search"],
        "minimum_coverage": 0.6,
        "official_required_for_strong_verdict": False,
        "verdict_style": "recommendation_with_expected_impact",
    },
    "product": {
        "required_evidence_classes": [
            "analytics events",
            "customer segments",
            "support feedback",
            "experiment history",
            "design or product requirements",
        ],
        "preferred_connectors": ["PostHog", "warehouse", "support export", "uploaded research", "targeted Tavily search"],
        "minimum_coverage": 0.58,
        "official_required_for_strong_verdict": False,
        "verdict_style": "reaction_segments",
    },
    "biomedical": {
        "required_evidence_classes": [
            "PeerMed/PubMed-class primary biomedical literature abstracts or full texts",
            "ClinicalTrials.gov or equivalent registry coverage for modality + indication",
            "FDA labeling or openFDA event signals when clinically relevant",
            "guideline excerpts (ASCO/NCCN/ESMO) referencing standard-of-care deltas",
            "survival/confidence intervals from RCTs vs RWE when juxtaposed",
        ],
        "preferred_connectors": [
            "PubMed / NIH / Europe PMC connectors",
            "ClinicalTrials.gov API",
            "openFDA (drugs/events)",
            "targeted Tavily biomedical search",
        ],
        "minimum_coverage": 0.68,
        "official_required_for_strong_verdict": True,
        "verdict_style": "uncertainty_first",
    },
    "general": {
        "required_evidence_classes": [
            "user assumptions",
            "current external facts",
            "historical analogs",
            "stakeholder impact",
            "risk indicators",
        ],
        "preferred_connectors": ["targeted Tavily search", "uploaded files", "controlled Playwright crawl"],
        "minimum_coverage": 0.52,
        "official_required_for_strong_verdict": False,
        "verdict_style": "uncertainty_first",
    },
}


def build_evidence_policy(classification: ScenarioClassification, prompt: str) -> Dict[str, Any]:
    domain_policy = DOMAIN_POLICIES.get(classification.domain) or DOMAIN_POLICIES["general"]
    is_current_or_high_stakes = classification.time_sensitivity in {"current", "future"} and classification.domain in {
        "sports",
        "finance",
        "politics",
        "biomedical",
    }
    required = list(domain_policy["required_evidence_classes"])
    for item in classification.required_evidence:
        if item not in required:
            required.append(item)

    return {
        "domain": classification.domain,
        "scenario_type": classification.scenario_type,
        "time_sensitivity": classification.time_sensitivity,
        "query": prompt.strip(),
        "required_evidence_classes": required,
        "preferred_connectors": list(domain_policy["preferred_connectors"]),
        "source_precedence": list(SOURCE_PRECEDENCE),
        "output_contract": list(OUTPUT_CONTRACT),
        "terminal_states": list(TERMINAL_STATES),
        "minimum_coverage": float(domain_policy["minimum_coverage"]),
        "official_required_for_strong_verdict": bool(domain_policy["official_required_for_strong_verdict"]),
        "verdict_style": domain_policy["verdict_style"],
        "high_stakes_or_current": is_current_or_high_stakes,
        "crawl_policy": {
            "respect_robots": True,
            "rate_limit_per_host": True,
            "block_heavy_assets": True,
            "requires_authorization_for_login_content": True,
            "legal_review_for_sensitive_sources": True,
        },
        "downgrade_rules": [
            "Insufficient Evidence if policy coverage is below the minimum threshold.",
            "Do not allow high agent agreement to create a strong verdict when evidence quality is weak.",
            "For current high-stakes scenarios, downgrade when no fresh external or official source is available.",
        ],
    }


def policy_missing_evidence(policy: Dict[str, Any], existing_missing: List[str]) -> List[str]:
    merged: List[str] = []
    for item in policy.get("required_evidence_classes") or []:
        if item not in merged:
            merged.append(item)
    for item in existing_missing or []:
        if item not in merged:
            merged.append(item)
    return merged
