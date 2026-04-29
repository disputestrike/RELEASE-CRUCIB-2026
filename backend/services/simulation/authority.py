"""URL authority tiers and regulated-domain down-ranking for high-stakes scenarios."""

from __future__ import annotations

from typing import Any, Dict, Tuple

# Domains where tier-3+ general web must not receive “strong primary” weight.
REGULATED_DOMAINS = frozenset({"biomedical", "finance", "politics"})


def authority_tier(url: str, title: str = "") -> int:
    """
    Lower tier = higher institutional trust for synthesis.
    1 = official / registry / primary scientific index
    2 = major wire / reputable trade
    3 = general web / encyclopedia
    4 = social / forum / self-publishing
    """
    u = f"{url} {title}".lower()
    if any(
        x in u
        for x in (
            ".gov/",
            "clinicaltrials.gov",
            "pubmed",
            "ncbi.nlm.nih.gov",
            "fda.gov",
            "sec.gov",
            "federalregister.gov",
            "regulations.gov",
            "europa.eu",
            "un.org",
            "imf.org",
            "worldbank.org",
        )
    ):
        return 1
    if any(x in u for x in ("nba.com", "nfl.com", "mlb.com", "nhl.com", "fifa.com", "who.int")):
        return 1
    if any(x in u for x in ("reuters.com", "apnews.com", "ap.org", "bloomberg.com", "ft.com")):
        return 2
    if any(x in u for x in ("espn.com", "sports.yahoo.com", "theathletic.com")):
        return 2
    if any(x in u for x in ("wikipedia.org", "britannica.com")):
        return 3
    if any(
        x in u
        for x in (
            "reddit.com",
            "twitter.",
            "x.com",
            "facebook.",
            "blogspot",
            "medium.com",
            "substack.",
            "tumblr.",
        )
    ):
        return 4
    return 3


def apply_authority_cap(
    *,
    url: str,
    title: str,
    scenario_domain: str,
    base_reliability: float,
) -> Tuple[float, Dict[str, Any]]:
    tier = authority_tier(url, title)
    tier_caps = {1: 1.0, 2: 0.9, 3: 0.72, 4: 0.5}
    cap = tier_caps.get(tier, 0.72)
    score = min(float(base_reliability), cap)
    meta: Dict[str, Any] = {
        "authority_tier": tier,
        "tier_ceiling": cap,
        "regulated_domain": scenario_domain in REGULATED_DOMAINS,
    }
    if scenario_domain in REGULATED_DOMAINS and tier >= 3:
        before = score
        score = min(score, 0.55 if tier == 3 else 0.45)
        if score < before - 1e-6:
            meta["regulated_downrank"] = True
    meta["final_reliability_cap"] = round(score, 3)
    return round(score, 3), meta
