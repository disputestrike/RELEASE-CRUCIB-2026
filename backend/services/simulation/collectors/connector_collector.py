"""First-party connector feed ingestion (fixtures now; Slack/GitHub/Jira wiring later)."""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .provenance import fingerprint_text, utc_now_iso
from .types import NormalizedRow


async def collect_connector_fixtures() -> Tuple[List[NormalizedRow], Dict[str, Any]]:
    started = time.perf_counter()
    path = (os.getenv("CRUCIB_CONNECTOR_FIXTURE_PATH") or "").strip()
    inline = (os.getenv("CRUCIB_CONNECTOR_FIXTURE_JSON") or "").strip()

    if not path and not inline:
        return [], {
            "name": "connector",
            "attempted": False,
            "wired": True,
            "success": False,
            "failure_kind": "no_fixture",
            "failure_detail": "Set CRUCIB_CONNECTOR_FIXTURE_JSON or CRUCIB_CONNECTOR_FIXTURE_PATH for connector rows.",
            "rows_returned": 0,
            "latency_ms": 0.0,
            "supported": ["slack", "github", "jira", "stripe", "posthog", "snowflake", "bigquery"],
        }

    items: List[Dict[str, Any]] = []
    try:
        if inline:
            parsed = json.loads(inline)
            items = parsed if isinstance(parsed, list) else []
        else:

            def _load() -> Any:
                return json.loads(Path(path).read_text(encoding="utf-8"))

            payload = await asyncio.to_thread(_load)
            items = payload if isinstance(payload, list) else []
    except Exception as exc:
        return [], {
            "name": "connector",
            "attempted": True,
            "wired": True,
            "success": False,
            "failure_kind": "parse_error",
            "failure_detail": str(exc)[:500],
            "rows_returned": 0,
            "latency_ms": round((time.perf_counter() - started) * 1000, 2),
            "supported": ["slack", "github", "jira", "stripe"],
        }

    rows: List[NormalizedRow] = []
    now = utc_now_iso()
    for raw in items[:40]:
        if not isinstance(raw, dict):
            continue
        url = str(raw.get("url") or raw.get("permalink") or "").strip()
        if not url or not url.startswith("http"):
            continue
        title = str(raw.get("title") or raw.get("subject") or url)[:500]
        body = str(raw.get("snippet") or raw.get("body") or raw.get("text") or "")[:8000]
        connector = str(raw.get("connector") or raw.get("source") or "connector")
        row = NormalizedRow(
            title=title,
            url=url,
            snippet=body[:1200] if body else title[:400],
            content=body if body else title,
            collector=f"connector:{connector}",
            score=float(raw.get("score") or 0.72),
            http_status=int(raw.get("http_status") or 200),
            request_url=url,
            final_url=url,
            redirect_count=0,
            content_sha256=fingerprint_text(f"{url}\n{body}"),
            retrieved_at_iso=str(raw.get("retrieved_at_iso") or now),
        )
        rows.append(row)

    return rows, {
        "name": "connector",
        "attempted": True,
        "wired": True,
        "success": len(rows) > 0,
        "failure_kind": None if rows else "empty_fixture",
        "failure_detail": None if rows else "Fixture contained no valid http URLs.",
        "rows_returned": len(rows),
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "supported_future": ["slack", "github", "jira", "stripe", "posthog", "linear"],
    }
