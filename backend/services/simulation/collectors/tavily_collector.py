from __future__ import annotations

import asyncio
import os
import time
from typing import Any, Dict, List, Tuple

import httpx

from .provenance import fingerprint_text, utc_now_iso
from .types import NormalizedRow, normalize_tavily_item


async def collect_tavily(
    queries: List[str],
    *,
    max_results_per_query: int = 6,
    topic: str | None = None,
    days: int | None = None,
) -> tuple[List[NormalizedRow], Dict[str, Any]]:
    """
    Multi-shot Tavily search with per-call diagnostics.
    Returns (normalized_rows, debug_dict).
    """
    api_key = os.getenv("TAVILY_API_KEY")
    started = time.perf_counter()
    calls: List[Dict[str, Any]] = []
    rows: List[NormalizedRow] = []
    if not api_key:
        return [], {
            "name": "tavily",
            "attempted": True,
            "success": False,
            "failure_kind": "missing_api_key",
            "failure_detail": "TAVILY_API_KEY is not set in the environment.",
            "rows_returned": 0,
            "rows_accepted": 0,
            "rows_rejected": 0,
            "reject_reasons": [],
            "calls": [],
            "latency_ms": 0.0,
        }

    use_raw = os.getenv("REALITY_ENGINE_TAVILY_RAW", "0").lower() in {"1", "true", "yes", "on"}
    timeout = float(os.getenv("REALITY_ENGINE_TAVILY_TIMEOUT", "18") or 18)
    max_conc = max(1, min(12, int(os.getenv("REALITY_ENGINE_TAVILY_MAX_CONCURRENT", "4") or 4)))

    reject_reasons: List[str] = []

    async def _single_search(
        client: httpx.AsyncClient, query: str, sem: asyncio.Semaphore
    ) -> Tuple[List[NormalizedRow], Dict[str, Any]]:
        call: Dict[str, Any] = {"query": query, "status_code": None, "failure_kind": None, "failure_detail": None, "result_count": 0}
        chunk: List[NormalizedRow] = []
        t0 = time.perf_counter()
        async with sem:
            try:
                payload: Dict[str, Any] = {
                    "api_key": api_key,
                    "query": query,
                    "max_results": max(1, min(max_results_per_query, 10)),
                    "include_answer": False,
                    "include_raw_content": use_raw,
                }
                if topic:
                    payload["topic"] = topic
                if days is not None and days > 0:
                    payload["days"] = int(days)

                response = await client.post("https://api.tavily.com/search", json=payload)
                call["status_code"] = response.status_code
                call["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)

                if response.status_code == 401:
                    call["failure_kind"] = "invalid_api_key"
                    call["failure_detail"] = "HTTP 401 from Tavily — key rejected."
                    return chunk, call
                if response.status_code == 429:
                    call["failure_kind"] = "quota_exceeded"
                    call["failure_detail"] = "HTTP 429 — rate limit or quota exceeded."
                    return chunk, call
                if response.status_code != 200:
                    body_prev = (response.text or "")[:500]
                    call["failure_kind"] = "http_error"
                    call["failure_detail"] = f"HTTP {response.status_code}: {body_prev}"
                    return chunk, call

                try:
                    data = response.json()
                except Exception as exc:
                    call["failure_kind"] = "parse_error"
                    call["failure_detail"] = f"JSON parse failed: {exc}"
                    return chunk, call

                raw_results = data.get("results") or []
                call["result_count"] = len(raw_results)
                if not raw_results:
                    call["failure_kind"] = "empty_results"
                    call["failure_detail"] = str(data.get("detail") or "API returned zero results for this query variant.")
                    return chunk, call

                call["failure_kind"] = None
                for item in raw_results:
                    norm = normalize_tavily_item(item if isinstance(item, dict) else {})
                    if norm:
                        chunk.append(norm)
                    else:
                        reject_reasons.append("normalize_drop_missing_url")
                return chunk, call
            except httpx.TimeoutException:
                call["failure_kind"] = "network_timeout"
                call["failure_detail"] = "Request timed out."
                call["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
                return chunk, call
            except Exception as exc:
                call["failure_kind"] = "network_error"
                call["failure_detail"] = str(exc)[:500]
                call["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
                return chunk, call

    sem = asyncio.Semaphore(max_conc)
    async with httpx.AsyncClient(timeout=timeout) as client:
        parts = await asyncio.gather(*[_single_search(client, q, sem) for q in queries])
    for chunk, call in parts:
        rows.extend(chunk)
        calls.append(call)

    # Deduplicate URLs keeping highest score
    by_url: Dict[str, NormalizedRow] = {}
    for r in rows:
        u = r["url"]
        if u not in by_url or r.get("score", 0) > by_url[u].get("score", 0):
            by_url[u] = r
    deduped = list(by_url.values())
    retrieved_at = utc_now_iso()
    for r in deduped:
        r["retrieved_at_iso"] = retrieved_at
        body = (r.get("content") or r.get("snippet") or "").strip()
        r["content_sha256"] = fingerprint_text(f"{r.get('url') or ''}\n{body}")
    rejected = max(0, len(rows) - len(deduped))
    if rejected:
        reject_reasons.extend(["dedupe_url"] * rejected)

    overall_success = len(deduped) > 0
    failure_kind = None
    failure_detail = None  # type: str | None
    if not overall_success:
        if not calls:
            failure_kind = "no_queries"
            failure_detail = "No Tavily calls executed."
        else:
            kinds = [c.get("failure_kind") for c in calls if c.get("failure_kind")]
            failure_kind = kinds[-1] if kinds else "all_queries_failed"
            failure_detail = " | ".join(
                f"{c.get('query', '')[:80]}: {(c.get('failure_detail') or c.get('failure_kind') or '')}"
                for c in calls
                if c.get("failure_kind")
            )[:1800]

    debug = {
        "name": "tavily",
        "attempted": True,
        "success": overall_success,
        "failure_kind": failure_kind,
        "failure_detail": failure_detail,
        "rows_returned": len(rows),
        "rows_accepted": len(deduped),
        "rows_rejected": len(reject_reasons),
        "reject_reasons": reject_reasons[:40],
        "calls": calls,
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "max_concurrent_requests": max_conc,
        "fan_out": len(queries) > 1,
        "quota_auth_note": "Check TAVILY_API_KEY and account quota on https://tavily.com if 401/429.",
    }
    return deduped, debug
