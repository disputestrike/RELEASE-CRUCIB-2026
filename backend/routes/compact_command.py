"""CF27 — /api/runtime/compact endpoint.

Adapted from claude-code-source-code/src/commands/compact. Triggers
context compaction on the active session.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/runtime", tags=["runtime"])

_COMPACTIONS: Dict[str, Dict[str, Any]] = {}


def _estimate_tokens_from_messages(messages) -> int:
    """chars ÷ 3.5 heuristic ported from clawspring/compaction.py."""
    total = 0
    for m in (messages or []):
        c = m.get("content", "")
        if isinstance(c, str):
            total += len(c)
        elif isinstance(c, list):
            for block in c:
                if isinstance(block, dict):
                    for v in block.values():
                        if isinstance(v, str):
                            total += len(v)
    return int(total / 3.5)


class CompactRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    target_tokens: int = Field(default=4000, ge=500, le=200000)
    messages: list = Field(default_factory=list)


@router.post("/compact")
def compact(body: CompactRequest):
    before = _estimate_tokens_from_messages(body.messages)
    # Placeholder: real compactor runs in services/runtime/context_manager.py
    after_target = min(before, body.target_tokens)
    compaction_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "compaction_id": compaction_id, "session_id": body.session_id,
        "tokens_before": before, "tokens_after_target": after_target,
        "target_tokens": body.target_tokens,
        "ratio": round(after_target / before, 3) if before else 1.0,
        "created_at": now,
    }
    _COMPACTIONS[compaction_id] = record
    return record


@router.get("/compact/{compaction_id}")
def get_compaction(compaction_id: str):
    return _COMPACTIONS.get(compaction_id, {"error": "not found"})
