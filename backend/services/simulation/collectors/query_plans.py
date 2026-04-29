from __future__ import annotations

import re
from typing import List

from ..models import ScenarioClassification


def _viral_stock_queries(prompt: str) -> List[str]:
    p = (prompt or "").strip()
    return [
        f"{p} unusual volume today stocks",
        "most active stocks today high volume",
        "top stock market movers today headlines",
        "stocks trending retail traders today",
        "pre-market stock movers today",
        "after hours stock movers biggest volume",
        "unusual options activity stocks today",
        "short squeeze stocks high volume today",
        "reddit wallstreetbets trending tickers discussion",
        "small cap stocks viral momentum catalyst",
        "stocks major news catalyst this week earnings",
      ]


def _options_week_queries(prompt: str) -> List[str]:
    p = (prompt or "").strip()
    return [
        f"{p} implied volatility options chain",
        "weekly options highest open interest earnings calendar",
        "SPY QQQ options flow unusual activity",
        f"{p} stock options implied volatility skew",
    ]


def build_retrieval_queries(
    prompt: str,
    classification: ScenarioClassification,
    evidence_depth: int,
    *,
    min_variants: int = 5,
    max_variants: int = 12,
) -> List[str]:
    """5–12 domain-aware query variants; multi-shot retrieval."""
    base = (prompt or "").strip()
    lower = base.lower()
    domain = classification.domain
    out: List[str] = []

    if domain == "finance":
        if any(
            w in lower
            for w in (
                "viral",
                "meme",
                "next big",
                "skyrocket",
                "momentum",
                "what stock",
                "which stock",
                "hot stock",
            )
        ):
            out.extend(_viral_stock_queries(base))
        if re.search(r"\boption", lower):
            out.extend(_options_week_queries(base))
        out.extend(
            [
                f"{base} latest stock market news today analyst",
                f"{base} SEC filing catalyst earnings date",
                f"{base} Bloomberg Reuters market movers",
                f"{base} macro Federal Reserve rates impact equities",
            ]
        )
    elif domain == "sports":
        out = [
            f"{base} standings injuries schedule odds today",
            f"{base} roster news injury report latest",
            f"{base} playoff bracket prediction analysts",
            f"{base} betting odds implied probability championship",
            f"{base} team performance metrics recent games",
        ]
    elif domain == "biomedical":
        out = [
            f"{base} PubMed clinical trial systematic review",
            f"{base} ClinicalTrials.gov enrollment status oncology",
            f"{base} FDA approval indication immunotherapy",
            f"{base} NCI guideline biomarker",
            f"{base} ASCO ESMO recent trial results",
        ]
    elif domain == "politics":
        out = [
            f"{base} official government statement policy",
            f"{base} sanctions legal analysis recent",
            f"{base} Federal Register regulation",
            f"{base} Reuters AP news geopolitics",
        ]
    elif domain == "business":
        out = [
            f"{base} pricing SaaS competitor benchmark churn",
            f"{base} customer sentiment review social",
            f"{base} market reaction earnings revenue",
        ]
    elif domain == "engineering":
        out = [
            f"{base} cloud migration case study reliability",
            f"{base} security compliance architecture benchmark",
        ]
    else:
        out = [f"{base} latest news analysis data", f"{base} current sources expert commentary"]

    seen: set[str] = set()
    uniq: List[str] = []
    for q in out:
        qn = " ".join(q.split())
        if qn.lower() in seen or not qn:
            continue
        seen.add(qn.lower())
        uniq.append(qn)

    cap = max(min_variants, min(max_variants, max(5, evidence_depth + 4)))
    return uniq[:cap]
