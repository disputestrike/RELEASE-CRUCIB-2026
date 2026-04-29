from __future__ import annotations

import os
import time
from typing import Any, Dict, List

from .provenance import fingerprint_text, utc_now_iso
from .types import NormalizedRow


async def playwright_deep_fetch(
    rows: List[NormalizedRow],
    *,
    max_pages: int = 2,
    min_chars: int = 350,
) -> tuple[List[NormalizedRow], Dict[str, Any]]:
    """Dynamic page render when static extraction is thin. Optional: requires Playwright browsers."""
    if os.getenv("REALITY_ENGINE_PLAYWRIGHT", "0").lower() not in {"1", "true", "yes", "on"}:
        return list(rows), {
            "name": "playwright",
            "attempted": False,
            "wired": True,
            "success": False,
            "failure_kind": "disabled",
            "failure_detail": "Set REALITY_ENGINE_PLAYWRIGHT=1 to enable headless extraction (and install browsers).",
            "pages_fetched": 0,
            "latency_ms": 0.0,
            "errors": [],
        }

    started = time.perf_counter()
    errors: List[str] = []
    pages = 0
    extracted: List[NormalizedRow] = []

    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:
        return list(rows), {
            "name": "playwright",
            "attempted": False,
            "wired": True,
            "success": False,
            "failure_kind": "import_error",
            "failure_detail": f"playwright package issue: {exc}",
            "pages_fetched": 0,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "errors": [str(exc)],
        }

    candidates = [
        r
        for r in rows
        if r.get("url")
        and len((r.get("content") or r.get("snippet") or "").strip()) < min_chars
        and str(r.get("url")).startswith("http")
    ][:max_pages]

    if not candidates:
        return list(rows), {
            "name": "playwright",
            "attempted": False,
            "wired": True,
            "success": False,
            "failure_kind": "no_candidate_urls",
            "failure_detail": "No short-body URLs needed Playwright for this run.",
            "pages_fetched": 0,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "errors": [],
        }

    url_set = {c["url"] for c in candidates}
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=os.getenv("CRUCIB_HTTP_USER_AGENT", "CrucibAI-Playwright/1.0")
            )
            page = await context.new_page()
            for cand in candidates:
                url = cand["url"]
                try:
                    response = await page.goto(url, wait_until="domcontentloaded", timeout=25_000)
                    text = await page.inner_text("body")
                    text = " ".join(text.split()).strip()
                    if len(text) < 80:
                        errors.append(f"{url[:100]}: thin body after render")
                        continue
                    title = await page.title()
                    final_url = page.url
                    http_status = int(response.status) if response is not None else None
                    retrieved_at = utc_now_iso()
                    extracted.append(
                        NormalizedRow(
                            title=str(title or cand.get("title"))[:500],
                            url=url,
                            snippet=text[:1200],
                            content=text[:14_000],
                            collector="playwright",
                            score=float(cand.get("score") or 0.4) + 0.08,
                            http_status=http_status,
                            request_url=url,
                            final_url=final_url,
                            redirect_count=None,
                            content_sha256=fingerprint_text(text),
                            retrieved_at_iso=retrieved_at,
                        )
                    )
                    pages += 1
                except Exception as exc:
                    errors.append(f"{url[:100]}: {exc}")
            await browser.close()
    except Exception as exc:
        errors.append(f"playwright_launch_or_browser: {exc}")

    merged: List[NormalizedRow] = []
    replaced = {r["url"] for r in extracted}
    for r in rows:
        if r["url"] in replaced:
            for n in extracted:
                if n["url"] == r["url"]:
                    merged.append(n)
                    break
        else:
            merged.append(r)

    debug = {
        "name": "playwright",
        "attempted": True,
        "wired": True,
        "success": pages > 0,
        "failure_kind": None if pages > 0 else (errors[0] if errors else "launch_or_no_pages"),
        "failure_detail": "; ".join(errors[:4])[:1200] if errors else None,
        "candidate_urls": list(url_set)[:max_pages],
        "pages_fetched": pages,
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "errors": errors[:12],
        "install_hint": "Run `playwright install chromium` in the deployment image if launch fails.",
    }
    return merged, debug
