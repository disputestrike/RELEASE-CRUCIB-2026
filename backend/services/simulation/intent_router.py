from __future__ import annotations

import re
from typing import Any, Dict, List

from .models import ScenarioClassification


def route_intent(classification: ScenarioClassification, prompt: str) -> Dict[str, Any]:
    """High-level user intent for answer shaping (complements scenario_type)."""
    lower = (prompt or "").strip().lower()
    dom = classification.domain
    st = classification.scenario_type

    primary = "risk_analysis"
    secondary: List[str] = []

    if dom == "finance" and any(
        w in lower
        for w in (
            "option",
            "options",
            "call ",
            "put ",
            "spread",
            "strangle",
            "straddle",
            "iron condor",
            "iv ",
            "implied vol",
            "open interest",
            "gamma ",
            "theta ",
        )
    ):
        primary = "market_scan"
        secondary.append("derivatives_screening")
    elif dom == "finance" and any(w in lower for w in ("screen", "scan", "watchlist", "ticker")):
        primary = "market_scan"
    elif dom == "biomedical" and (
        any(w in lower for w in ("cancer", "oncology", "tumor", "car-t", "immunotherapy"))
        or st == "research_discovery"
    ):
        primary = "scientific_roadmap"
        secondary.append("drug_discovery")
    elif st == "forecast":
        primary = "forecast"
    elif st == "decision":
        primary = "decision"
    elif st == "research_discovery":
        primary = "research"
    elif st == "market_reaction":
        primary = "social_reaction_simulation"
    elif st == "technical_architecture":
        primary = "technical_plan"
    elif re.search(r"\bis there a cure\b|\bcure for\b", lower) and dom == "biomedical":
        primary = "discovery"
    elif any(w in lower for w in ("roadmap", "plan for", "how do we build", "architecture")):
        primary = "technical_plan"

    labels = [primary, *secondary, st, dom]
    return {
        "primary_intent": primary,
        "secondary_intents": secondary,
        "labels": list(dict.fromkeys(labels)),
    }
