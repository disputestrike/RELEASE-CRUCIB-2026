"""Optional LLM subagent swarm to diversify search query variants (env-gated)."""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Tuple


def _parse_query_lines(text: str) -> List[str]:
    out: List[str] = []
    for raw in (text or "").replace("\r", "\n").split("\n"):
        line = raw.strip()
        line = re.sub(r"^\d+[\).\s]+", "", line)
        line = line.lstrip("-*•").strip()
        if 6 <= len(line) <= 220 and not line.lower().startswith("json"):
            out.append(line[:220])
    return out


async def expand_queries_via_subagents(
    prompt: str,
    base_queries: List[str],
    *,
    run_id: str,
    user_id: str,
) -> Tuple[List[str], Dict[str, Any]]:
    enabled = os.getenv("CRUCIB_RETRIEVAL_SWARM_QUERIES", "0").lower() in {"1", "true", "yes", "on"}
    if not enabled:
        return list(base_queries), {"used": False, "reason": "CRUCIB_RETRIEVAL_SWARM_QUERIES off"}

    branches = max(2, min(8, int(os.getenv("CRUCIB_RETRIEVAL_SWARM_BRANCHES", "3") or 3)))
    try:
        from ......services.runtime.subagent_orchestrator import SubagentOrchestrator    except ImportError:
        try:
            from services.runtime.subagent_orchestrator import SubagentOrchestrator
        except ImportError:
            return list(base_queries), {"used": False, "reason": "SubagentOrchestrator import failed"}

    job_id = f"retrieval-{run_id}"[:96]
    orch = SubagentOrchestrator(job_id=job_id, user_id=user_id or "system")
    task = (
        "Generate 5–10 short web search query strings to gather evidence for the question below. "
        "Rules: one query per line; no numbering; no JSON; no commentary; 6–120 characters per line.\n\n"
        f"Question:\n{prompt[:2000]}"
    )
    try:
        out = await orch.run(task=task, config={"branches": branches}, context={"retrieval_query_expansion": True})
    except Exception as exc:
        return list(base_queries), {"used": False, "reason": f"swarm_run_error:{exc}"[:500]}

    extra: List[str] = []
    for row in out.get("subagentResults") or []:
        rec = str(((row.get("result") or {}).get("recommendation")) or "")
        extra.extend(_parse_query_lines(rec))
    for fragment in ((out.get("consensus") or {}).get("reasons") or [])[:6]:
        extra.extend(_parse_query_lines(str(fragment)))

    merged: List[str] = []
    seen: set[str] = set()
    for q in list(base_queries) + extra:
        k = q.strip().lower()
        if k and k not in seen:
            seen.add(k)
            merged.append(q.strip())
    cap = max(12, min(24, len(base_queries) + 12))
    merged = merged[:cap]
    return merged, {
        "used": True,
        "requested_branches": branches,
        "actual_branches": out.get("actualBranches"),
        "queries_added": max(0, len(merged) - len(base_queries)),
        "job_id": job_id,
    }
