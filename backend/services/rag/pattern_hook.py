"""Pattern capture/retrieval hooks — keep the RAG store out of agent code.

On every successful job completion, call record_success(project_id, summary).
Before launching a new job, call retrieve_priors(project_id, query) to get
the top-K prior patterns for context injection.
"""
from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, Optional

from .store import get_store

logger = logging.getLogger(__name__)

_PATTERNS_COLLECTION = "project_patterns"


def _make_id(project_id: str, summary: str) -> str:
    h = hashlib.sha1(f"{project_id}::{summary}".encode("utf-8")).hexdigest()[:16]
    return f"{project_id}:{h}"


async def record_success(project_id: str, job_summary: str,
                          extra: Optional[dict] = None) -> dict:
    """Upsert a successful job's summary as a pattern against the project."""
    if not project_id or not job_summary:
        return {"ok": False, "reason": "project_id and job_summary required"}
    store = get_store()
    doc = {
        "id": _make_id(project_id, job_summary),
        "text": job_summary,
        "metadata": {
            "project_id": project_id,
            "kind": "pattern",
            "ts": time.time(),
            **(extra or {}),
        },
    }
    return await store.upsert(_PATTERNS_COLLECTION, [doc])


async def retrieve_priors(project_id: str, query: str, k: int = 5) -> list[dict]:
    """Return top-K similar prior patterns for this project."""
    if not project_id or not query:
        return []
    store = get_store()
    try:
        hits = await store.query(
            _PATTERNS_COLLECTION,
            query=query,
            k=k,
            where={"project_id": project_id},
        )
    except Exception as e:
        logger.warning("RAG retrieve_priors failed: %s", e)
        return []
    if hits:
        logger.info("RAG: retrieved %d priors for project %s", len(hits), project_id)
    return hits
