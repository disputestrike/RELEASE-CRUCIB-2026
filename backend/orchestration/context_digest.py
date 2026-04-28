"""
Compact context for long runs: last N error-like signals from job events (§3.1 signal vs noise).

Callers can inject the returned strings into repair prompts or steering — not a full
Context Manager Service, but a single honest extraction point.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List


def last_error_traces(
    events: List[Dict[str, Any]],
    *,
    limit: int = 3,
    max_chars: int = 1200,
) -> List[str]:
    """Return up to ``limit`` recent error summaries from job event payloads (newest first)."""
    out: List[str] = []
    for ev in reversed(events or []):
        if len(out) >= limit:
            break
        t = str(ev.get("event_type") or ev.get("type") or "").lower()
        pl_raw = ev.get("payload")
        if isinstance(pl_raw, dict) and pl_raw:
            pl = dict(pl_raw)
        elif isinstance(ev.get("data"), dict):
            pl = dict(ev["data"])  # type: ignore[arg-type]
        elif isinstance(ev.get("payload_json"), str):
            try:
                lj = json.loads(ev["payload_json"])  # runtime_state.append_job_event store
                pl = lj if isinstance(lj, dict) else {}
            except Exception:
                pl = {}
        elif isinstance(pl_raw, str):
            try:
                pl = json.loads(pl_raw)
            except Exception:
                pl = {}
        else:
            pl = {}
        if not isinstance(pl, dict):
            pl = {}
        if "error" in t or "fail" in t or "exception" in t or pl.get("error"):
            msg = pl.get("error") or pl.get("message") or pl.get("detail") or str(pl)[:400]
            s = str(msg).strip()
            if s:
                out.append(s[:max_chars])
        elif pl.get("issues") and any(
            x in t for x in ("preview", "verify", "gate", "fail", "job")
        ):
            iss = pl.get("issues")
            if isinstance(iss, list) and iss:
                out.append(str(iss[0])[:max_chars])
    return out
