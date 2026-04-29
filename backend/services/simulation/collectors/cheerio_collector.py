from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Set
from urllib.parse import urlparse

import httpx

from .provenance import fingerprint_text, utc_now_iso
from .types import NormalizedRow

DEFAULT_UA = (
    "Mozilla/5.0 (compatible; CrucibAI/1.0; +https://crucib.ai; evidence-retrieval)"
)
_SKIP_EXT = {".pdf", ".zip", ".png", ".jpg", ".jpeg", ".gif", ".mp4", ".mp3", ".wasm"}


def _extract_main_text(soup: Any, max_chars: int = 12000) -> str:
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()
    main = soup.find("article") or soup.find("main") or soup.find(role="main")
    if main:
        text = main.get_text("\n", strip=True)
    else:
        text = soup.get_text("\n", strip=True)
    lines = [ln for ln in (ln.strip() for ln in text.splitlines()) if ln]
    out = "\n".join(lines)
    return out[:max_chars]


async def deep_fetch_urls(
    seed_rows: List[NormalizedRow],
    *,
    max_pages: int = 6,
    min_body_chars_to_skip: int = 400,
) -> tuple[List[NormalizedRow], Dict[str, Any]]:
    """Static HTML ingestion (Cheerio-equivalent): GET page and extract visible text."""
    if os.getenv("REALITY_ENGINE_CHEERIO", "1").lower() not in {"1", "true", "yes", "on"}:
        return list(seed_rows), {
            "name": "cheerio",
            "attempted": False,
            "wired": True,
            "success": False,
            "failure_kind": "disabled",
            "failure_detail": "REALITY_ENGINE_CHEERIO is off.",
            "pages_fetched": 0,
            "rows_enriched": 0,
            "latency_ms": 0.0,
            "errors": [],
        }

    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:
        return list(seed_rows), {
            "name": "cheerio",
            "attempted": False,
            "wired": True,
            "success": False,
            "failure_kind": "missing_dependency",
            "failure_detail": f"beautifulsoup4 not importable: {exc}",
            "pages_fetched": 0,
            "rows_enriched": 0,
            "latency_ms": 0.0,
            "errors": [str(exc)],
        }

    started = time.perf_counter()
    errors: List[str] = []
    pages = 0
    enriched_count = 0
    seen: Set[str] = set()
    out: List[NormalizedRow] = []

    timeout = float(os.getenv("REALITY_ENGINE_CHEERIO_TIMEOUT", "14") or 14)
    headers = {"User-Agent": os.getenv("CRUCIB_HTTP_USER_AGENT", DEFAULT_UA)}

    async with httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=True) as client:
        for row in seed_rows:
            url = str(row.get("url") or "").strip()
            if not url:
                continue
            body_len = len((row.get("content") or row.get("snippet") or "").strip())
            if body_len >= min_body_chars_to_skip or pages >= max_pages:
                out.append(row)
                continue
            path = urlparse(url).path.lower()
            if any(path.endswith(ext) for ext in _SKIP_EXT):
                out.append(row)
                continue
            if url in seen:
                out.append(row)
                continue
            seen.add(url)
            try:
                resp = await client.get(url)
                if resp.status_code != 200:
                    errors.append(f"{url[:120]}: HTTP {resp.status_code}")
                    out.append(row)
                    continue
                ctype = (resp.headers.get("content-type") or "").lower()
                if "html" not in ctype and "text/plain" not in ctype:
                    errors.append(f"{url[:120]}: skip content-type {ctype or 'unknown'}")
                    out.append(row)
                    continue
                soup = BeautifulSoup(resp.text[:2_000_000], "html.parser")
                title_el = soup.find("title")
                title = (title_el.get_text(strip=True) if title_el else row.get("title")) or ""
                final_url = str(resp.url)
                redirect_count = len(resp.history or [])
                text = _extract_main_text(soup)
                if len(text) < 80:
                    errors.append(f"{url[:120]}: sparse extract ({len(text)} chars)")
                    out.append(row)
                    continue
                snippet = text[:1200]
                retrieved_at = utc_now_iso()
                out.append(
                    NormalizedRow(
                        title=str(title or row.get("title"))[:500],
                        url=url,
                        snippet=snippet,
                        content=text,
                        collector="cheerio_html",
                        score=float(row.get("score") or 0.45) + 0.05,
                        http_status=int(resp.status_code),
                        request_url=url,
                        final_url=final_url,
                        redirect_count=redirect_count,
                        content_sha256=fingerprint_text(text),
                        retrieved_at_iso=retrieved_at,
                    )
                )
                pages += 1
                enriched_count += 1
            except Exception as exc:
                errors.append(f"{url[:120]}: {exc}")
                out.append(row)

    if not out:
        out = list(seed_rows)

    debug = {
        "name": "cheerio",
        "attempted": True,
        "wired": True,
        "success": pages > 0,
        "failure_kind": None if pages > 0 else "no_successful_page_fetches",
        "failure_detail": "; ".join(errors[:6])[:1200] if errors else None,
        "pages_fetched": pages,
        "rows_enriched": enriched_count,
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "errors": errors[:20],
    }
    return out, debug
