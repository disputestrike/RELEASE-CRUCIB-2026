from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple

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


def _source_reliability(url: str, title: str) -> Tuple[str, float]:
    lowered = f"{url} {title}".lower()
    if any(domain in lowered for domain in [".gov", "nba.com", "fifa.com", "espn.", "reuters.", "apnews.", "sec.gov"]):
        return "high", 0.85
    if any(domain in lowered for domain in ["wikipedia", "blog", "reddit", "forum"]):
        return "medium", 0.55
    return "medium_high", 0.7


def _queries(prompt: str, classification: ScenarioClassification, evidence_depth: int) -> List[str]:
    base = prompt.strip()
    if classification.domain == "sports":
        candidates = [
            f"{base} current odds injuries standings recent form",
            f"{base} roster injuries opponent strength forecast",
            f"{base} championship odds analyst prediction",
        ]
    elif classification.domain == "business":
        candidates = [
            f"{base} pricing churn customer sentiment competitor pricing",
            f"{base} market data customer reaction benchmark",
        ]
    elif classification.domain == "engineering":
        candidates = [
            f"{base} migration risk cost security reliability benchmark",
            f"{base} architecture tradeoffs incident rollback",
        ]
    elif classification.domain == "finance":
        candidates = [
            f"{base} latest market data analyst consensus macro indicators",
            f"{base} current price policy signal forecast",
        ]
    elif classification.domain == "politics":
        candidates = [
            f"{base} latest policy official statements legal constraints",
            f"{base} current news stakeholder reaction impact analysis",
        ]
    else:
        candidates = [f"{base} current evidence data analysis", f"{base} recent sources"]
    return candidates[: max(1, min(evidence_depth, len(candidates)))]


async def _tavily_search(query: str, max_results: int) -> List[Dict[str, Any]]:
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return []
    try:
        import httpx

        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": query,
                    "max_results": max(1, min(max_results, 8)),
                    "include_answer": False,
                    "include_raw_content": False,
                },
            )
        if response.status_code != 200:
            return []
        data = response.json()
        return data.get("results") or []
    except Exception:
        return []


async def build_evidence(
    *,
    simulation_id: str,
    run_id: str,
    prompt: str,
    classification: ScenarioClassification,
    assumptions: List[str],
    attachments: List[Dict[str, Any]],
    use_live_evidence: bool = True,
    evidence_depth: int = 4,
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

    live_results: List[Dict[str, Any]] = []
    search_queries = _queries(prompt, classification, evidence_depth)
    if use_live_evidence and classification.time_sensitivity in {"current", "future"}:
        for query in search_queries:
            live_results.extend(await _tavily_search(query, max_results=3))

    seen_urls = set()
    for idx, result in enumerate(live_results[: max(0, evidence_depth * 3)]):
        url = str(result.get("url") or "").strip()
        title = str(result.get("title") or url or f"Live source {idx + 1}").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        reliability, reliability_score = _source_reliability(url, title)
        sources.append(
            {
                "id": new_id("src"),
                "simulation_id": simulation_id,
                "run_id": run_id,
                "type": "web",
                "title": title[:240],
                "status": "available",
                "reliability": reliability,
                "freshness": "retrieved_now",
                "url": url,
                "metadata": {
                    "score": result.get("score"),
                    "query_count": len(search_queries),
                    "retrieved_at": now,
                },
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

    live_source_ids = [source["id"] for source in sources if source.get("type") == "web"]
    source_by_url = {source.get("url"): source for source in sources if source.get("type") == "web"}
    for result in live_results[: max(0, evidence_depth * 3)]:
        url = str(result.get("url") or "").strip()
        source = source_by_url.get(url)
        if not source:
            continue
        content = str(result.get("content") or result.get("snippet") or "").strip()
        if not content:
            continue
        _, reliability_score = _source_reliability(url, str(result.get("title") or ""))
        facts.append(
            {
                "id": new_id("fact"),
                "simulation_id": simulation_id,
                "run_id": run_id,
                "source_id": source["id"],
                "claim": content[:700],
                "evidence_type": "live_web_extract",
                "reliability_score": reliability_score,
                "freshness_score": 0.82,
                "confidence": min(0.88, reliability_score + 0.03),
                "url": url,
                "created_at": now,
            }
        )

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
    live_data_used = bool(live_source_ids)
    if classification.time_sensitivity == "current" and not live_data_used:
        unsupported_claims.append("No verified live source was used in this V1 run unless uploaded evidence was provided.")

    data_completeness = min(
        0.9,
        0.25
        + (len(attachments or []) * 0.1)
        + (len(assumptions or []) * 0.05)
        + (len(live_source_ids) * 0.07)
        + (len(facts) * 0.015),
    )
    if classification.domain == "general":
        data_completeness = min(data_completeness, 0.55)

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
            "live_data_used": live_data_used,
            "search_queries": search_queries if use_live_evidence else [],
            "live_source_count": len(live_source_ids),
        },
    }
