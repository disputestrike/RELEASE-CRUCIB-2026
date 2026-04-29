from __future__ import annotations

import os
import urllib.parse
from typing import Any, Dict, List, Tuple

from .models import ScenarioClassification
from .repository import new_id, now_iso
from .domain_policy import build_evidence_policy, policy_missing_evidence


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
    "biomedical": [
        "peer-reviewed modality-level outcome data for indication subtype",
        "registered trial statuses (ClinicalTrials.gov / CTR parity)",
        "regulatory approvals or boxed warnings pertinent to modality",
        "biomarker assay traceability linking bench to surrogate endpoint",
        "population heterogeneity stratification survival curves",
    ],
}


def _source_reliability(url: str, title: str) -> Tuple[str, float, str]:
    lowered = f"{url} {title}".lower()
    if any(domain in lowered for domain in ["pubmed.ncbi.nlm.nih.gov", "pubmed/"]):
        return "indexed_peer_lit", 0.88, "targeted_pubmed_esearch"
    if any(domain in lowered for domain in [".gov", "sec.gov", "federalregister.gov", "clinicaltrials.gov", "fda.gov", "cdc.gov", "who.int"]):
        return "official_primary", 1.0, "official_api_or_primary_web"
    if any(domain in lowered for domain in ["nba.com", "fifa.com", "mlb.com", "nfl.com"]):
        return "official_league", 0.92, "official_api_or_primary_web"
    if any(domain in lowered for domain in ["sportradar", "fred.stlouisfed.org", "reuters.", "apnews.", "espn."]):
        return "trusted_structured_or_press", 0.78, "trusted_commercial_or_nonprofit"
    if any(domain in lowered for domain in ["wikipedia", "blog", "reddit", "forum"]):
        return "community_or_secondary", 0.38, "weak_secondary"
    return "secondary_web", 0.62, "targeted_web_search"


def _fit_to_policy(text: str, policy: Dict[str, Any]) -> float:
    lowered = text.lower()
    hits = 0
    for item in policy.get("required_evidence_classes") or []:
        tokens = [token for token in str(item).lower().replace("/", " ").split() if len(token) > 4]
        if any(token in lowered for token in tokens):
            hits += 1
    return round(min(1.0, 0.25 + hits * 0.18), 3)


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
    elif classification.domain == "biomedical":
        candidates = [
            f"{base} clinical trial oncology immunotherapy biomarker RCT PubMed NIH",
            f"{base} FDA approval indication toxicology surrogate endpoint CAR-T cellular therapy Genomics CT.gov",
            f"{base} guideline ASCO ESMO NCCN modality heterogeneity recurrence",
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


async def _clinicaltrials_gov_snapshots(prompt: str, max_results: int) -> List[Dict[str, Any]]:
    """Public ClinicalTrials.gov v2 snapshots — dynamic trial metadata without API secrets."""
    if os.getenv("REALITY_ENGINE_CTGOV", "1").lower() not in {"1", "true", "yes", "on"}:
        return []
    term = urllib.parse.quote((prompt or "").strip()[:220] or "oncology")
    try:
        import httpx

        url = f"https://clinicaltrials.gov/api/v2/studies?query.term={term}&pageSize={max(1, min(10, max_results))}&format=json"
        async with httpx.AsyncClient(timeout=18.0) as client:
            response = await client.get(url)
        if response.status_code != 200:
            return []
        data = response.json()
        out: List[Dict[str, Any]] = []
        for st in (data.get("studies") or [])[:max_results]:
            ps = (st or {}).get("protocolSection") or {}
            im = ps.get("identificationModule") or {}
            title = im.get("briefTitle") or im.get("officialTitle") or "clinical trial snapshot"
            nct = str((st.get("nctId") or im.get("nctId") or st.get("id") or "")).strip()
            pid = urllib.parse.quote(nct.replace(" ", ""))
            canonical = f"https://clinicaltrials.gov/study/{pid}" if nct else "https://clinicaltrials.gov"
            out.append(
                {
                    "title": title[:400],
                    "url": canonical,
                    "snippet": (
                        "Registry-derived trial metadata (ClinicalTrials.gov v2)—check inclusion criteria and primary outcome before extrapolating."
                    ),
                    "_nct": nct,
                }
            )
            if len(out) >= max_results:
                break
        return out
    except Exception:
        return []


async def _pubmed_eutils_snapshots(prompt: str, max_results: int) -> List[Dict[str, Any]]:
    """NCBI E-utilities (PubMed) — no API key required; abide by NIH usage guidelines."""
    if os.getenv("REALITY_ENGINE_PUBMED", "1").lower() not in {"1", "true", "yes", "on"}:
        return []
    term_raw = (prompt or "").strip()[:400] or "oncology randomized controlled trial"
    term = urllib.parse.quote(term_raw)
    retmax = max(1, min(12, int(max_results)))
    tool_email = (
        urllib.parse.quote((os.getenv("CRUCIB_NCBI_EMAIL") or "dev@crucib.ai").strip())
    )
    try:
        import httpx

        base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
        async with httpx.AsyncClient(timeout=22.0) as client:
            esearch_url = (
                f"{base}esearch.fcgi?db=pubmed&retmax={retmax}&retmode=json&tool=CrucibAI&email={tool_email}&term={term}"
            )
            er = await client.get(esearch_url)
            if er.status_code != 200:
                return []
            idlist = (er.json().get("esearchresult") or {}).get("idlist") or []
            idlist = [str(x).strip() for x in idlist if x]
            if not idlist:
                return []
            idstr = ",".join(idlist[:retmax])
            summary_url = f"{base}esummary.fcgi?db=pubmed&id={idstr}&retmode=json&tool=CrucibAI&email={tool_email}"
            sr = await client.get(summary_url)
            if sr.status_code != 200:
                return []
            summ_data = sr.json().get("result") or {}
        out: List[Dict[str, Any]] = []
        for uid in (summ_data.get("uids") or idlist[:retmax]):
            rec = summ_data.get(str(uid))
            if not isinstance(rec, dict):
                continue
            title = (rec.get("title") or "").strip() or "PubMed citation"
            url = f"https://pubmed.ncbi.nlm.nih.gov/{uid}/"
            journal = str(rec.get("source") or "").strip()
            jp = journal[:120]
            snippet = (
                f"PubMed catalog hit ( PMID:{uid}"
                + (f" · {jp}" if jp else "")
                + " ) — review abstract for indication/method specificity before citing clinical effect."
            )
            out.append(
                {
                    "title": title[:400],
                    "url": url,
                    "snippet": snippet,
                    "pmid": uid,
                }
            )
            if len(out) >= max_results:
                break
        return out
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
    evidence_policy: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    now = now_iso()
    policy = evidence_policy or build_evidence_policy(classification, prompt)
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
            "source_precedence": "user_upload",
            "reliability_score": 0.55,
            "freshness_score": 1.0,
            "traceability_score": 1.0,
            "fit_score": _fit_to_policy(prompt, policy),
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
                "source_precedence": "user_upload",
                "reliability_score": 0.6,
                "freshness_score": 0.55,
                "traceability_score": 0.75 if attachment.get("url") else 0.55,
                "fit_score": _fit_to_policy(str(attachment), policy),
                "metadata": attachment,
                "created_at": now,
            }
        )

    live_results: List[Dict[str, Any]] = []
    search_queries = _queries(prompt, classification, evidence_depth)
    if use_live_evidence and classification.time_sensitivity in {"current", "future"}:
        for query in search_queries:
            live_results.extend(await _tavily_search(query, max_results=3))

    if classification.domain == "biomedical":
        ct_rows = await _clinicaltrials_gov_snapshots(
            prompt, max_results=max(2, min(evidence_depth + 1, 8))
        )
        for row in ct_rows:
            live_results.append(
                {
                    "url": row.get("url"),
                    "title": row.get("title"),
                    "content": row.get("snippet") or "",
                    "snippet": row.get("snippet") or "",
                }
            )
        pm_rows = await _pubmed_eutils_snapshots(prompt, max_results=max(3, min(evidence_depth + 2, 10)))
        for row in pm_rows:
            live_results.append(
                {
                    "url": row.get("url"),
                    "title": row.get("title"),
                    "content": row.get("snippet") or "",
                    "snippet": row.get("snippet") or "",
                }
            )

    seen_urls = set()
    for idx, result in enumerate(live_results[: max(0, evidence_depth * 3)]):
        url = str(result.get("url") or "").strip()
        title = str(result.get("title") or url or f"Live source {idx + 1}").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        reliability, reliability_score, source_precedence = _source_reliability(url, title)
        lo = url.lower()
        if "clinicaltrials.gov" in lo:
            src_type = "trial_registry"
        elif "pubmed" in lo or "/pubmed/" in lo or "ncbi.nlm.nih.gov/pubmed" in lo:
            src_type = "pubmed_catalog"
        else:
            src_type = "web"
        sources.append(
            {
                "id": new_id("src"),
                "simulation_id": simulation_id,
                "run_id": run_id,
                "type": src_type,
                "title": title[:240],
                "status": "available",
                "reliability": reliability,
                "freshness": "retrieved_now",
                "url": url,
                "source_precedence": source_precedence,
                "reliability_score": reliability_score,
                "freshness_score": 0.85,
                "traceability_score": 0.9,
                "fit_score": _fit_to_policy(f"{title} {result.get('content') or result.get('snippet') or ''}", policy),
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
            "traceability_score": 1.0,
            "fit_score": _fit_to_policy(prompt, policy),
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
            "traceability_score": 1.0,
            "fit_score": _fit_to_policy(classification.interpretation, policy),
            "created_at": now,
        },
    ]

    live_source_ids = [
        source["id"]
        for source in sources
        if source.get("type") in {"web", "trial_registry", "pubmed_catalog"}
    ]
    source_by_url = {
        source.get("url"): source
        for source in sources
        if source.get("type") in {"web", "trial_registry", "pubmed_catalog"}
    }
    for result in live_results[: max(0, evidence_depth * 3)]:
        url = str(result.get("url") or "").strip()
        source = source_by_url.get(url)
        if not source:
            continue
        content = str(result.get("content") or result.get("snippet") or "").strip()
        if not content:
            continue
        _, reliability_score, _ = _source_reliability(url, str(result.get("title") or ""))
        lo = url.lower()
        if "clinicaltrials.gov" in lo:
            ev_et = "trial_registry_extract"
        elif "pubmed" in lo:
            ev_et = "pubmed_catalog_extract"
        else:
            ev_et = "live_web_extract"
        facts.append(
            {
                "id": new_id("fact"),
                "simulation_id": simulation_id,
                "run_id": run_id,
                "source_id": source["id"],
                "claim": content[:700],
                "evidence_type": ev_et,
                "reliability_score": reliability_score,
                "freshness_score": 0.82,
                "confidence": min(0.88, reliability_score + 0.03),
                "url": url,
                "traceability_score": 0.9,
                "fit_score": _fit_to_policy(content, policy),
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
                "traceability_score": 0.7,
                "fit_score": _fit_to_policy(assumption, policy),
                "created_at": now,
            }
        )

    missing = policy_missing_evidence(
        policy,
        DOMAIN_MISSING.get(classification.domain, ["verified current data", "external corroborating sources"]),
    )
    unsupported_claims = []
    live_data_used = bool(live_source_ids)
    if classification.time_sensitivity == "current" and not live_data_used:
        unsupported_claims.append("No verified live source was used in this V1 run unless uploaded evidence was provided.")
    if policy.get("official_required_for_strong_verdict") and not live_data_used:
        unsupported_claims.append("The evidence policy requires fresh primary or trusted external sources before a strong verdict.")

    policy_hits = set()
    for fact in facts:
        text = str(fact.get("claim") or "").lower()
        for idx, item in enumerate(policy.get("required_evidence_classes") or []):
            tokens = [token for token in str(item).lower().replace("/", " ").split() if len(token) > 4]
            if any(token in text for token in tokens):
                policy_hits.add(idx)
    policy_total = max(1, len(policy.get("required_evidence_classes") or []))
    policy_coverage = min(1.0, len(policy_hits) / policy_total + (0.1 if live_data_used else 0))
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
    data_completeness = round(max(data_completeness, min(0.9, policy_coverage * 0.75 + data_completeness * 0.25)), 2)

    claims: List[Dict[str, Any]] = []
    for idx, fact in enumerate(facts):
        supports_or_refutes = "supports" if fact.get("evidence_type") in {
            "prompt_fact",
            "live_web_extract",
            "trial_registry_extract",
            "pubmed_catalog_extract",
            "user_assumption",
        } else "context"
        if fact.get("evidence_type") == "scenario_interpretation":
            supports_or_refutes = "context"
        claims.append(
            {
                "id": new_id("clm"),
                "simulation_id": simulation_id,
                "run_id": run_id,
                "claim_text": fact.get("claim"),
                "evidence_id": fact.get("id"),
                "source_id": fact.get("source_id"),
                "supports_or_refutes": supports_or_refutes,
                "reliability_score": fact.get("reliability_score"),
                "freshness_score": fact.get("freshness_score"),
                "traceability_score": fact.get("traceability_score"),
                "fit_score": fact.get("fit_score"),
                "entities": [],
                "time_scope": classification.time_sensitivity,
                "claim_features": {"rank": idx + 1, "evidence_type": fact.get("evidence_type")},
                "created_at": now,
            }
        )
    for item in missing[:5]:
        claims.append(
            {
                "id": new_id("clm"),
                "simulation_id": simulation_id,
                "run_id": run_id,
                "claim_text": item,
                "evidence_id": None,
                "source_id": None,
                "supports_or_refutes": "refutes",
                "reliability_score": 0.0,
                "freshness_score": 0.0,
                "traceability_score": 0.0,
                "fit_score": 1.0,
                "entities": [],
                "time_scope": classification.time_sensitivity,
                "claim_features": {"missing_evidence": True},
                "created_at": now,
            }
        )

    return {
        "sources": sources,
        "evidence": facts,
        "claims": claims,
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
            "policy_coverage": round(policy_coverage, 3),
            "evidence_policy": policy,
            "traceability": round(
                sum(float(item.get("traceability_score") or 0) for item in facts) / max(1, len(facts)),
                3,
            ),
            "fit_to_query": round(
                sum(float(item.get("fit_score") or 0) for item in facts) / max(1, len(facts)),
                3,
            ),
            "registry_snapshots": sum(1 for s in sources if s.get("type") == "trial_registry"),
            "pubmed_snapshots": sum(1 for s in sources if s.get("type") == "pubmed_catalog"),
        },
    }
