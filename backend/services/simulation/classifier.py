from __future__ import annotations

import re
from typing import List

from .models import ScenarioClassification


SPORTS_TERMS = {
    "nba",
    "lakers",
    "basketball",
    "finals",
    "playoff",
    "championship",
    "world cup",
    "football",
    "soccer",
    "arsenal",
    "brazil",
    "match",
}
# Strong biomedical / clinical science signals — checked before generic bucket.
BIOMEDICAL_TERMS = {
    "cancer",
    "oncology",
    "oncologist",
    "tumor",
    "tumour",
    "chemotherapy",
    "radiotherapy",
    "immunotherapy",
    "car-t",
    "cart cell",
    "clinical trial",
    "phase ii",
    "phase iii",
    "placebo-controlled",
    "fda",
    "ema approval",
    "pubmed",
    "clinicaltrials.gov",
    "nih",
    "nccn",
    "pathology",
    "biopsy",
    "chemo",
    "leukemia",
    "melanoma",
    "metastasis",
    "radiation oncology",
    "radiation therapy",
    "pharmacovigilance",
    "pharma",
    "drug discovery",
    "gene therapy",
    "cell therapy",
    "mrna vaccine",
    "genomics",
    "genomic",
    "proteomics",
    "immune checkpoint",
    "pd-1",
    "her2",
    "biomarker",
    "oncogene",
    "in vitro",
    "in vivo",
    "epidemiology",
    "mortality rate",
    "survival curve",
}
BUSINESS_TERMS = {"price", "pricing", "customers", "churn", "revenue", "startup", "sales", "market"}
FINANCE_TERMS = {
    "stock",
    "inflation",
    "tariff",
    "trade",
    "oil",
    "crypto",
    "interest rate",
    "recession",
    "equity",
    "share price",
    "nasdaq",
    "nyse",
    "earnings",
    "valuation",
}
POLITICS_TERMS = {"election", "ban", "policy", "sanction", "government", "war", "military", "defense"}
ENGINEERING_TERMS = {"aws", "api", "database", "migrate", "stack", "backend", "frontend", "cloud", "security"}
PRODUCT_TERMS = {"feature", "redesign", "launch", "ux", "users", "conversion", "retention"}


def _contains_any(text: str, terms: set[str]) -> bool:
    return any(term in text for term in terms)


def _required_evidence(domain: str, scenario_type: str) -> List[str]:
    if domain == "biomedical":
        return [
            "peer-reviewed primary literature consensus (PubMed-class sources)",
            "current trial enrollment and eligibility (trial registry parity)",
            "regulatory approvals and indications (FDA/openFDA parity where applicable)",
            "biomarker and subtype specificity",
            "safety profiles and adverse-event signals",
            "real-world comparative effectiveness signals where available",
        ]
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
            "timestamps and liquidity for traded instruments when applicable",
            "primary filings when single-name equities are involved",
            "macro indicators",
            "policy or rate signals",
            "analyst or market consensus where appropriate",
            "scheduled catalyst calendar (earnings, FDA, splits, macro prints)",
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
    elif _contains_any(lower, BIOMEDICAL_TERMS):
        domain = "biomedical"
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
        r"\bwill\b",
        r"\bwin\b",
        r"\bhappen\b",
        r"\bforecast\b",
        r"\bprobability\b",
        r"\blikely\b",
        r"\bwhat happens if\b",
    ]
    decision_patterns = [r"\bshould\b", r"\bdo we\b", r"\bshould we\b", r"\braise\b", r"\bcut\b", r"\bmigrate\b"]
    market_patterns = [r"\bcustomers hate\b", r"\bmarket reaction\b", r"\busers react\b", r"\bresponse\b"]
    research_patterns = [
        r"\bhow (do|can) we\b",
        r"\bwhat would it take\b",
        r"\bwhat is the way\b",
        r"\bis there a cure\b",
        r"\bcure\b",
        r"\bhow to cure\b",
        r"\bresearch roadmap\b",
        r"\bhypothesis\b",
        r"\bmechanism of action\b",
    ]
    short_horizon_markers = ("next week", "this week", "tomorrow", "today", "next day", "pre-market")

    scenario_type = "risk_analysis"
    output_style = "decision_memo"

    name_like_finance = any(x in lower for x in ("stock", "stocks", "ticker", "equity", "share price"))

    # Finance: short-window trading / tape questions — emphasize live-evidence posture, never fake ticks.
    if domain == "finance" and (
        name_like_finance or "market" in lower or "portfolio" in lower
    ):
        if any(m in lower for m in short_horizon_markers) or bool(re.search(r"\bnext\s+\d+\s+days\b", lower)):
            scenario_type = "short_horizon_forecast"
            output_style = "forecast"
        elif any(re.search(p, lower) for p in forecast_patterns):
            scenario_type = "forecast"
            output_style = "forecast"
        elif any(re.search(p, lower) for p in decision_patterns):
            scenario_type = "decision"
            output_style = "decision_memo"
        else:
            scenario_type = "forecast"
            output_style = "forecast"

    elif domain == "biomedical" and (
        any(re.search(p, lower) for p in research_patterns) or ("?" in text and any(w in lower for w in ("cure", "treat", "why", "how")))
    ):
        scenario_type = "research_discovery"
        output_style = "research_roadmap"
    elif any(re.search(p, lower) for p in market_patterns):
        scenario_type = "market_reaction"
        output_style = "response_segments"
    elif domain == "sports" or any(re.search(p, lower) for p in forecast_patterns):
        scenario_type = "forecast"
        output_style = "forecast"
    elif any(re.search(p, lower) for p in decision_patterns):
        scenario_type = "decision"
        output_style = "decision_memo"
    elif domain == "engineering":
        scenario_type = "technical_architecture"
        output_style = "tradeoff_matrix"
    elif domain == "finance":
        scenario_type = "forecast"
        output_style = "forecast"
    else:
        scenario_type = "risk_analysis"
        output_style = "decision_memo"

    time_sensitivity = "current" if domain in {"sports", "finance", "politics", "biomedical"} else "future"
    if any(term in lower for term in ["historical", "last year", "previously"]):
        time_sensitivity = "historical"
    if any(term in lower for term in ["evergreen", "principle", "strategy"]) and domain not in {"sports"}:
        time_sensitivity = "evergreen"

    interpretation = (
        f"This appears to be a {domain.replace('_', ' ')} {scenario_type.replace('_', ' ')}. "
        "The Reality Engine routes specialist personas, adapts outputs to the detected intent (not always a rigid probability quartet), "
        "and binds claims to harvested evidence tiers."
    )
    if domain == "biomedical" and scenario_type == "research_discovery":
        interpretation = (
            "This is treated as an open biomedical / scientific-discovery question—not a faux single-number prognosis. "
            "We deploy oncology-focused specialist agents, demand peer-reviewed-class evidence channels, "
            "and prioritize roadmaps over fake precision when literature or trial coverage is incomplete."
        )
    elif domain == "finance" and scenario_type == "short_horizon_forecast":
        interpretation = (
            "Short-window market-motion question: the scan must cite live or near-live market evidence when connectors succeed; "
            "otherwise verdicts stay evidence-gated and you get an explicit acquisition plan—not invented tick paths."
        )
    elif domain == "sports" and "lakers" in lower and "nba" in lower:
        interpretation = (
            "This appears to be a sports championship forecast. Title likelihood is synthesized from standings-relevant cues, injuries, playoff path, "
            "matched odds/analyst strands when adapters return them—not from generic stubs."
        )

    assumptions = []
    if len(text.split()) <= 4:
        assumptions.append(
            "The prompt is terse, so inferred intent relies on lexical routing; tighten wording for sharper specialist selection."
        )
    if scenario_type == "research_discovery":
        assumptions.append(
            "No universal clinical cure thesis is assumed—outputs emphasize subtype-specific modalities and staged evidence ladders."
        )
    if scenario_type == "short_horizon_forecast":
        assumptions.append("Short-horizon price motion requires authoritative market timestamps; absence yields Insufficient Evidence on directional picks.")

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
