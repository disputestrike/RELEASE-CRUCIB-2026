"""CF27 — Cost tracker API.

Adapted from claude-code-source-code/src/costHook.ts + cost-tracker.ts.
Tracks per-run token + USD spend. Self-sufficient: in-memory registry;
the durable backend lives in services/events/event_store.py.
"""
from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cost", tags=["cost"])

# Indicative public pricing (USD per 1M tokens). Update via POST /api/cost/pricing.
PRICING: Dict[str, Dict[str, float]] = {
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-opus-4-6": {"input": 15.00, "output": 75.00},
    "claude-haiku-4-5": {"input": 0.80, "output": 4.00},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
}

_RUNS: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"turns": [], "total_usd": 0.0})


class TurnCost(BaseModel):
    run_id: str
    model: str
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cached_tokens: int = Field(default=0, ge=0)


class TurnCostResponse(BaseModel):
    run_id: str
    turn_id: str
    usd: float
    total_run_usd: float
    recorded_at: str


def _compute_usd(model: str, tin: int, tout: int) -> float:
    p = PRICING.get(model)
    if not p:
        return 0.0
    return (tin / 1_000_000) * p["input"] + (tout / 1_000_000) * p["output"]


@router.post("/turn", response_model=TurnCostResponse)
def record_turn(body: TurnCost) -> TurnCostResponse:
    usd = _compute_usd(body.model, body.input_tokens, body.output_tokens)
    turn_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()
    run = _RUNS[body.run_id]
    run["turns"].append({
        "turn_id": turn_id,
        "model": body.model,
        "input_tokens": body.input_tokens,
        "output_tokens": body.output_tokens,
        "cached_tokens": body.cached_tokens,
        "usd": usd,
        "recorded_at": now,
    })
    run["total_usd"] += usd
    return TurnCostResponse(
        run_id=body.run_id, turn_id=turn_id, usd=round(usd, 6),
        total_run_usd=round(run["total_usd"], 6), recorded_at=now,
    )


@router.get("/run/{run_id}")
def get_run(run_id: str):
    r = _RUNS.get(run_id)
    if not r:
        raise HTTPException(status_code=404, detail="run not found")
    return {
        "run_id": run_id,
        "turns": r["turns"],
        "total_usd": round(r["total_usd"], 6),
        "turn_count": len(r["turns"]),
    }


@router.get("/totals")
def totals():
    total = sum(r["total_usd"] for r in _RUNS.values())
    return {"run_count": len(_RUNS), "total_usd": round(total, 6)}


@router.get("/pricing")
def pricing():
    return {"pricing_per_million_tokens": PRICING}
