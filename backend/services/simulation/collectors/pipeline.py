from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Tuple

from ..models import ScenarioClassification
from .cheerio_collector import deep_fetch_urls
from .connector_collector import collect_connector_fixtures
from .official_api import collect_official
from .playwright_collector import playwright_deep_fetch
from .query_plans import build_retrieval_queries
from .tavily_collector import collect_tavily
from .types import NormalizedRow


def _should_run_tavily(classification: ScenarioClassification, prompt: str, use_live_evidence: bool) -> bool:
    if not use_live_evidence:
        return False
    if classification.time_sensitivity in {"current", "future"}:
        return True
    if classification.domain in {"finance", "sports", "politics", "business", "product", "biomedical"}:
        return True
    pl = (prompt or "").lower()
    keys = ("crypto", "bitcoin", "weather", "breaking", "today", "live price", "premarket")
    return any(k in pl for k in keys)


def _rows_to_live_dicts(rows: List[NormalizedRow]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for r in rows:
        url = str(r.get("url") or "").strip()
        if not url:
            continue
        out.append(
            {
                "url": url,
                "title": r.get("title"),
                "snippet": r.get("snippet") or "",
                "content": r.get("content") or r.get("snippet") or "",
                "_collector": r.get("collector"),
                "score": r.get("score"),
            }
        )
        prov = {
            k: r.get(k)
            for k in (
                "http_status",
                "request_url",
                "final_url",
                "redirect_count",
                "content_sha256",
                "retrieved_at_iso",
            )
            if r.get(k) is not None
        }
        if prov:
            out[-1]["_provenance"] = prov
    return out


def _dedupe_rows(rows: List[NormalizedRow]) -> List[NormalizedRow]:
    by_url: Dict[str, NormalizedRow] = {}
    for r in rows:
        u = r.get("url")
        if not u:
            continue
        if u not in by_url or float(r.get("score") or 0) > float(by_url[u].get("score") or 0):
            by_url[u] = r
    return list(by_url.values())


def _compute_gate(
    *,
    classification: ScenarioClassification,
    use_live_evidence: bool,
    collector_summaries: List[Dict[str, Any]],
) -> Dict[str, Any]:
    if not use_live_evidence:
        return {"passed": True, "reason": "use_live_evidence=false — exploratory / offline posture."}
    if classification.time_sensitivity not in {"current", "future"}:
        return {"passed": True, "reason": "Non-current time sensitivity — soft retrieval gate."}

    families = set()
    for c in collector_summaries:
        name = c.get("name")
        if not c.get("attempted"):
            continue
        if name == "tavily":
            families.add("web_search_api")
        elif name == "cheerio":
            families.add("static_html")
        elif name == "playwright":
            families.add("headless_browser")
        elif name == "official_api":
            families.add("official_registry")
        elif name == "connector" and c.get("success"):
            families.add("first_party_connector")

    if len(families) >= 2:
        return {"passed": True, "reason": f"Multiple retrieval families executed: {sorted(families)}."}

    failed_diag = [
        c
        for c in collector_summaries
        if c.get("attempted")
        and not c.get("success")
        and (c.get("failure_detail") or c.get("failure_kind"))
    ]
    if failed_diag:
        return {
            "passed": True,
            "reason": "Collectors ran and surfaced explicit failure diagnostics (see retrieval_debug.collectors).",
        }

    return {
        "passed": False,
        "reason": "Current-data run: fewer than two retrieval families produced usable work — review API keys (TAVILY_API_KEY) and collector logs.",
        "minimum_families": 2,
        "families_observed": sorted(families),
    }


async def run_retrieval_pipeline(
    *,
    prompt: str,
    classification: ScenarioClassification,
    use_live_evidence: bool,
    evidence_depth: int,
    attachments: List[Dict[str, Any]] | None,
    run_id: str | None = None,
    user_id: str | None = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, Any]]:
    started = time.perf_counter()
    queries = build_retrieval_queries(prompt, classification, evidence_depth)
    swarm_meta: Dict[str, Any] = {"used": False}
    if run_id and use_live_evidence:
        from .swarm_queries import expand_queries_via_subagents

        queries, swarm_meta = await expand_queries_via_subagents(
            prompt,
            queries,
            run_id=run_id,
            user_id=user_id or "system",
        )
    collector_summaries: List[Dict[str, Any]] = []
    all_rows: List[NormalizedRow] = []

    run_tavily = _should_run_tavily(classification, prompt, use_live_evidence)
    if run_tavily:
        t_rows, t_debug = await collect_tavily(queries, max_results_per_query=6)
        collector_summaries.append(t_debug)
        all_rows.extend(t_rows)
    else:
        collector_summaries.append(
            {
                "name": "tavily",
                "attempted": False,
                "success": False,
                "failure_kind": "skipped",
                "failure_detail": "Tavily not routed for this run.",
                "rows_returned": 0,
                "rows_accepted": 0,
                "calls": [],
                "latency_ms": 0.0,
            }
        )

    if use_live_evidence:
        conn_rows, conn_debug = await collect_connector_fixtures()
        collector_summaries.append(conn_debug)
        all_rows.extend(conn_rows)

    o_rows, o_debug = await collect_official(classification=classification, prompt=prompt, evidence_depth=evidence_depth)
    collector_summaries.append(
        {
            "name": "official_api",
            "attempted": bool(o_debug.get("attempted")),
            "success": bool(o_debug.get("success")),
            "rows_returned": int(o_debug.get("rows_returned") or 0),
            "ledger": o_debug.get("ledger"),
            "latency_ms": float(o_debug.get("latency_ms") or 0.0),
        }
    )
    all_rows.extend(o_rows)

    all_rows = _dedupe_rows(all_rows)

    cheerio_seed = [
        r
        for r in all_rows
        if str(r.get("url", "")).startswith("http")
        and "clinicaltrials.gov" not in r["url"].lower()
        and "pubmed.ncbi.nlm.nih.gov" not in r["url"].lower()
        and "api.fda.gov" not in r["url"].lower()
    ][: max(4, min(10, evidence_depth + 4))]

    cheerio_eligible = bool(use_live_evidence and cheerio_seed)
    if cheerio_eligible:
        enriched, ch_debug = await deep_fetch_urls(cheerio_seed, max_pages=max(3, min(8, evidence_depth + 2)))
        collector_summaries.append(ch_debug)
        by_url = {r["url"]: r for r in all_rows if r.get("url")}
        for orig, maybe_new in zip(cheerio_seed, enriched):
            u = orig.get("url")
            if u and maybe_new.get("collector") == "cheerio_html":
                by_url[u] = maybe_new
        all_rows = list(by_url.values())
    else:
        skip_detail = "Live evidence disabled — static HTML fetch not run."
        if use_live_evidence and not cheerio_seed:
            skip_detail = (
                "No eligible HTTP seed URLs for static fetch (excluding clinicaltrials.gov / PubMed / openFDA). "
                "Tavily/connector/fixtures returned no generic web URLs, or only registry endpoints."
            )
        collector_summaries.append(
            {
                "name": "cheerio",
                "attempted": False,
                "wired": True,
                "success": False,
                "failure_kind": "skipped",
                "failure_detail": skip_detail,
                "pages_fetched": 0,
                "latency_ms": 0.0,
                "errors": [],
            }
        )

    playwright_on = os.getenv("REALITY_ENGINE_PLAYWRIGHT", "0").lower() in {"1", "true", "yes", "on"}
    if use_live_evidence and playwright_on:
        pw_rows, pw_debug = await playwright_deep_fetch(all_rows, max_pages=2)
        collector_summaries.append(pw_debug)
        by_url = {r["url"]: r for r in all_rows if r.get("url")}
        for r in pw_rows:
            if r.get("collector") == "playwright" and r.get("url"):
                by_url[r["url"]] = r
        all_rows = list(by_url.values())
    else:
        if not use_live_evidence:
            pw_detail = "Live evidence disabled — Playwright not invoked."
            pw_kind = "skipped"
        elif not playwright_on:
            pw_detail = "REALITY_ENGINE_PLAYWRIGHT default off — set to 1 after `playwright install chromium`."
            pw_kind = "disabled"
        else:
            pw_detail = "Playwright not invoked."
            pw_kind = "skipped"
        collector_summaries.append(
            {
                "name": "playwright",
                "attempted": False,
                "wired": True,
                "success": False,
                "failure_kind": pw_kind,
                "failure_detail": pw_detail,
                "pages_fetched": 0,
                "latency_ms": 0.0,
                "errors": [],
            }
        )

    gate = _compute_gate(classification=classification, use_live_evidence=use_live_evidence, collector_summaries=collector_summaries)
    accepted_urls = {r["url"] for r in all_rows if r.get("url")}
    returned_estimate = sum(int(c.get("rows_returned") or c.get("rows_accepted") or 0) for c in collector_summaries)

    tav = next((c for c in collector_summaries if c.get("name") == "tavily"), {})
    ch = next((c for c in collector_summaries if c.get("name") == "cheerio"), {})
    pw = next((c for c in collector_summaries if c.get("name") == "playwright"), {})
    oa = next((c for c in collector_summaries if c.get("name") == "official_api"), {})

    retrieval_debug = {
        "query_variants": queries,
        "collectors": collector_summaries,
        "summary": {
            "source_urls_distinct": len(accepted_urls),
            "rows_estimate_pre_dedupe_hint": returned_estimate,
            "total_pipeline_latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "tavily_max_concurrent": tav.get("max_concurrent_requests"),
            "tavily_parallel_fan_out": bool(tav.get("fan_out")),
        },
        "gate": gate,
        "swarm_query_expansion": swarm_meta,
        "uploaded_files": {"count": len(attachments or []), "note": "Parsed claims from uploads remain in evidence_engine."},
    }

    # Legacy-shaped ledger for trust / output_answer compatibility

    off_ledger = (oa.get("ledger") or {}) if isinstance(oa.get("ledger"), dict) else {}
    conn = next((c for c in collector_summaries if c.get("name") == "connector"), {})

    retrieval_ledger = {
        "tavily": {
            "attempted": bool(tav.get("attempted")),
            "success": bool(tav.get("success")),
            "failure_reason": (tav.get("failure_detail") or tav.get("failure_kind")),
            "failure_kind": tav.get("failure_kind"),
            "calls": tav.get("calls") or [],
        },
        "cheerio": {
            "attempted": bool(ch.get("attempted")),
            "success": bool(ch.get("success")),
            "wired": True,
            "failure_reason": ch.get("failure_detail"),
            "pages_fetched": ch.get("pages_fetched"),
        },
        "playwright": {
            "attempted": bool(pw.get("attempted")),
            "success": bool(pw.get("success")),
            "wired": True,
            "failure_reason": pw.get("failure_detail"),
            "pages_fetched": pw.get("pages_fetched"),
        },
        "uploaded_files": {"count": len(attachments or []), "ingested": bool(attachments)},
        "official_api": {
            "clinicaltrials_gov": off_ledger.get("clinicaltrials_gov", {}),
            "pubmed_eutils": off_ledger.get("pubmed_eutils", {}),
            "openfda": off_ledger.get("openfda", {}),
        },
        "connector": {
            "attempted": bool(conn.get("attempted")),
            "success": bool(conn.get("success")),
            "failure_reason": conn.get("failure_detail") or conn.get("failure_kind"),
            "rows_returned": conn.get("rows_returned"),
        },
    }

    live_dicts = _rows_to_live_dicts(_dedupe_rows(all_rows))
    return live_dicts, retrieval_debug, retrieval_ledger
