from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict


class NormalizedRow(TypedDict, total=False):
    """Unified row consumed by evidence_engine source ingestion."""

    title: str
    url: str
    snippet: str
    content: str
    published_at: Optional[str]
    collector: str
    score: float
    raw_excerpt: Optional[str]
    # Provenance (optional; populated by HTTP / browser collectors where available)
    http_status: Optional[int]
    request_url: Optional[str]
    final_url: Optional[str]
    redirect_count: Optional[int]
    content_sha256: Optional[str]
    retrieved_at_iso: Optional[str]


def normalize_tavily_item(item: Dict[str, Any], collector: str = "tavily") -> Optional[NormalizedRow]:
    url = str(item.get("url") or "").strip()
    if not url:
        return None
    title = str(item.get("title") or url or "Web result").strip()
    body = (item.get("content") or item.get("snippet") or item.get("raw_content") or "").strip()
    return NormalizedRow(
        title=title[:500],
        url=url,
        snippet=body[:1200] if body else title[:400],
        content=body[:8000] if body else title[:400],
        published_at=None,
        collector=collector,
        score=float(item.get("score") or 0.5),
    )


def merge_content(row: NormalizedRow, extra_text: str, collector: str) -> NormalizedRow:
    extra = (extra_text or "").strip()
    if not extra:
        return row
    prev = (row.get("content") or row.get("snippet") or "").strip()
    if extra in prev:
        return row
    merged = f"{prev}\n\n[{collector} excerpt]\n{extra}".strip()
    return NormalizedRow(
        **{**row, "content": merged[:12000], "snippet": merged[:1200], "collector": collector}
    )
