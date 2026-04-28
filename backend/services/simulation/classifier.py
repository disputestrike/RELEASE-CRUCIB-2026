from __future__ import annotations

import re
from typing import List

from .models import ScenarioClassification


SPORTS_TERMS = {
    "nba", "lakers", "basketball", "finals", "playoff", "championship",
    "world cup", "football", "soccer", "arsenal", "brazil", "match",
}
BUSINESS_TERMS = {"price", "pricing", "customers", "churn", "revenue", "startup", "sales", "market"}
FINANCE_TERMS = {"stock", "inflation", "tariff", "trade", "oil", "crypto", "interest rate", "recession"}
POLITICS_TERMS = {"election", "ban", "policy", "sanction", "government", "war", "military", "defense"}
ENGINEERING_TERMS = {"aws", "api", "database", "migrate", "stack", "backend", "frontend", "cloud", "security"}
PRODUCT_TERMS = {"feature", "redesign", "launch", "ux", "users", "conversion", "retention"}


def _contains_any(text: str, terms: set[str]) -> bool:
    return any(term in text for term in terms)


def _required_evidence(domain: str, scenario_type: str) -> List[str]:
    if domain == "sports":
        return [
            "team record and standings",
            "recent performance",
            "player injuries and availability",
            "playoff path or opponent strength",
            "market odds or analyst consensus",
            "historical championship patterns",
        ]
    if domain == "business":
        return [
            "current revenue and pricing",
            "customer segments",
            "churn or retention data",
            "competitor pricing",
            "sales pipeline impact",
            "customer sentiment",
        ]
    if domain == "engineering":
        return [
            "current architecture",
            "cost profile",
            "security constraints",
            "migration complexity",
            "dependency graph",
            "performance bottlenecks",
        ]
    if domain == "finance":
        return [
            "current market data",
            "historical trend data",
            "macro indicators",
            "policy or rate signals",
            "analyst consensus",
        ]
    if domain == "politics":
        return [
            "current policy state",
            "stakeholder positions",
            "historical precedent",
            "legal or regulatory constraints",
            "recent news signals",
        ]
    return ["user assumptions", "current facts", "historical analogs", "stakeholder impact", "risk indicators"]


def classify_scenario(prompt: str) -> ScenarioClassification:
    text = (prompt or "").strip()
    lower = text.lower()

    if _contains_any(lower, SPORTS_TERMS):
        domain = "sports"
    elif _contains_any(lower, ENGINEERING_TERMS):
        domain = "engineering"
    elif _contains_any(lower, BUSINESS_TERMS):
        domain = "business"
    elif _contains_any(lower, FINANCE_TERMS):
        domain = "finance"
    elif _contains_any(lower, POLITICS_TERMS):
        domain = "politics"
    elif _contains_any(lower, PRODUCT_TERMS):
        domain = "product"
    else:
        domain = "general"

    forecast_patterns = [
        r"\bwill\b", r"\bwin\b", r"\bhappen\b", r"\bforecast\b", r"\bprobability\b",
        r"\blikely\b", r"\bwhat happens if\b",
    ]
    decision_patterns = [r"\bshould\b", r"\bdo we\b", r"\bshould we\b", r"\braise\b", r"\bcut\b", r"\bmigrate\b"]
    market_patterns = [r"\bcustomers hate\b", r"\bmarket reaction\b", r"\busers react\b", r"\bresponse\b"]

    if any(re.search(p, lower) for p in market_patterns):
        scenario_type = "market_reaction"
    elif domain == "sports" or any(re.search(p, lower) for p in forecast_patterns):
        scenario_type = "forecast"
    elif any(re.search(p, lower) for p in decision_patterns):
        scenario_type = "decision"
    elif domain == "engineering":
        scenario_type = "technical_architecture"
    else:
        scenario_type = "risk_analysis"

    time_sensitivity = "current" if domain in {"sports", "finance", "politics"} else "future"
    if any(term in lower for term in ["historical", "last year", "previously"]):
        time_sensitivity = "historical"
    if any(term in lower for term in ["evergreen", "principle", "strategy"]):
        time_sensitivity = "evergreen"

    if scenario_type == "forecast":
        output_style = "forecast"
    elif scenario_type == "technical_architecture":
        output_style = "tradeoff_matrix"
    elif scenario_type == "market_reaction":
        output_style = "response_segments"
    else:
        output_style = "decision_memo"

    interpretation = (
        f"This appears to be a {domain} {scenario_type.replace('_', ' ')}. "
        f"The Reality Engine will analyze the scenario using evidence, assumptions, "
        f"specialized agents, belief updates, and multi-case outcomes."
    )
    if domain == "sports" and "lakers" in lower and "nba" in lower:
        interpretation = (
            "This appears to be a sports championship forecast. I will estimate the Lakers' "
            "NBA title likelihood using team performance, injuries, playoff path, opponent "
            "strength, market odds, and analyst signals when available."
        )

    assumptions = []
    if len(text.split()) <= 4:
        assumptions.append("The prompt is terse, so the system infers the most likely intent and exposes missing evidence.")

    return ScenarioClassification(
        domain=domain,
        scenario_type=scenario_type,
        time_sensitivity=time_sensitivity,
        required_evidence=_required_evidence(domain, scenario_type),
        output_style=output_style,
        interpretation=interpretation,
        ambiguity="medium" if assumptions else "low",
        assumptions=assumptions,
    )
