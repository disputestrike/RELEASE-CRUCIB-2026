from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .authority import REGULATED_DOMAINS, apply_authority_cap
from .collectors import run_retrieval_pipeline
from .models import ScenarioClassification
from .repository import new_id, now_iso
from .domain_policy import build_evidence_policy, policy_missing_evidence


class RetrievalGateError(Exception):
    """Raised when strict live-retrieval coverage is required but the gate failed."""

    def __init__(self, retrieval_debug: Dict[str, Any]):
        self.retrieval_debug = retrieval_debug
        super().__init__("live_retrieval_gate_failed")


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
        "live option chain, IV, OI, and spread for named underlyings",
        "earnings and catalyst calendar for those names",
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
    user_id: str | None = None,
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

    live_results, retrieval_debug, retrieval_ledger = await run_retrieval_pipeline(
        prompt=prompt,
        classification=classification,
        use_live_evidence=use_live_evidence,
        evidence_depth=evidence_depth,
        attachments=attachments,
        run_id=run_id,
        user_id=user_id,
    )
    search_queries = retrieval_debug.get("query_variants") or []

    seen_urls = set()
    for idx, result in enumerate(live_results[: max(0, evidence_depth * 3)]):
        url = str(result.get("url") or "").strip()
        title = str(result.get("title") or url or f"Live source {idx + 1}").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        reliability, reliability_score, source_precedence = _source_reliability(url, title)
        reliability_score, auth_meta = apply_authority_cap(
            url=url,
            title=title,
            scenario_domain=classification.domain,
            base_reliability=reliability_score,
        )
        lo = url.lower()
        col = str(result.get("_collector") or "")
        if col.startswith("connector:"):
            src_type = "connector_feed"
        elif "clinicaltrials.gov" in lo:
            src_type = "trial_registry"
        elif "pubmed" in lo or "/pubmed/" in lo or "ncbi.nlm.nih.gov/pubmed" in lo:
            src_type = "pubmed_catalog"
        elif "api.fda.gov" in lo or "openfda" in (result.get("snippet") or "").lower():
            src_type = "regulatory_openfda"
        else:
            src_type = "web"
        prov = dict(result.get("_provenance") or {})
        if result.get("retrieved_at_iso"):
            prov.setdefault("retrieved_at_iso", result.get("retrieved_at_iso"))
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
                    "query_variants": len(search_queries),
                    "collector": result.get("_collector"),
                    "retrieved_at": now,
                    "authority": auth_meta,
                    "provenance": prov,
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
        if source.get("type")
        in {"web", "trial_registry", "pubmed_catalog", "regulatory_openfda", "connector_feed"}
    ]
    source_by_url = {
        source.get("url"): source
        for source in sources
        if source.get("type")
        in {"web", "trial_registry", "pubmed_catalog", "regulatory_openfda", "connector_feed"}
    }
    for result in live_results[: max(0, evidence_depth * 3)]:
        url = str(result.get("url") or "").strip()
        source = source_by_url.get(url)
        if not source:
            continue
        content = str(result.get("content") or result.get("snippet") or "").strip()
        if not content:
            continue
        _, _rs, _ = _source_reliability(url, str(result.get("title") or ""))
        adj_score = float(source.get("reliability_score") or _rs or 0.62)
        lo = url.lower()
        col = str(result.get("_collector") or "").lower()
        if col.startswith("connector:"):
            ev_et = "connector_feed_extract"
        elif "clinicaltrials.gov" in lo:
            ev_et = "trial_registry_extract"
        elif "pubmed" in lo:
            ev_et = "pubmed_catalog_extract"
        elif "api.fda.gov" in lo:
            ev_et = "openfda_label_extract"
        elif "cheerio_html" in col:
            ev_et = "cheerio_html_extract"
        elif "playwright" in col:
            ev_et = "playwright_html_extract"
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
                "reliability_score": adj_score,
                "freshness_score": 0.82,
                "confidence": min(0.88, adj_score + 0.03),
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
    gate = retrieval_debug.get("gate") or {}
    if not use_live_evidence:
        unsupported_claims.append(
            "Live evidence was disabled (use_live_evidence=false); web/API collectors were skipped where applicable—Output Answer may be exploratory."
        )
    elif not gate.get("passed"):
        unsupported_claims.append(
            f"Retrieval gate did not meet minimum multi-collector coverage for a current-data run: {gate.get('reason', 'see retrieval_debug.collectors for per-collector errors.')}"
        )

    if use_live_evidence:
        tv = retrieval_ledger.get("tavily") or {}
        if tv.get("attempted") and not tv.get("success") and not live_data_used:
            unsupported_claims.append(
                f"Tavily did not yield ingestible rows: {tv.get('failure_reason') or tv.get('failure_kind') or 'see retrieval_debug.collectors[0].calls'}"
            )

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
            "openfda_label_extract",
            "cheerio_html_extract",
            "playwright_html_extract",
            "connector_feed_extract",
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

    downranked_sources = sum(
        1
        for s in sources
        if (s.get("metadata") or {}).get("authority", {}).get("regulated_downrank")
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
            "connector_snapshots": sum(1 for s in sources if s.get("type") == "connector_feed"),
            "authority_summary": {
                "regulated_domain": classification.domain in REGULATED_DOMAINS,
                "sources_downranked": downranked_sources,
            },
            "retrieval_ledger": retrieval_ledger,
            "retrieval_debug": retrieval_debug,
        },
        "retrieval_ledger": retrieval_ledger,
        "retrieval_debug": retrieval_debug,
    }
