"""
Metrics API — Phase 3: Closed-Loop Optimization.

Endpoints for deployed apps to ping performance data back to the platform and
for the optimization engine to read signals.

POST /api/apps/{app_id}/metrics         — deployed app sends a metric snapshot
GET  /api/apps/{app_id}/metrics/summary — current aggregated stats for an app
GET  /api/apps/{app_id}/metrics/signals — pending optimization signals
GET  /api/apps/metrics/apps             — list all tracked app IDs (admin)
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from ..services.performance_monitor import (
    record_metric,
    get_app_summary,
    analyze_and_signal,
    OptimizationSignal,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/apps", tags=["metrics"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class MetricPayload(BaseModel):
    """Schema for a metric ping from a deployed app."""
    app_id: str
    ts: Optional[float] = Field(default=None, description="Unix epoch; defaults to server time")
    load_ms: int = Field(default=0, ge=0, description="Page load time in ms")
    error_rate: float = Field(default=0.0, ge=0.0, le=1.0, description="Error fraction 0-1")
    active_users: int = Field(default=0, ge=0)
    requests: int = Field(default=0, ge=0, description="Request count in this period")
    endpoint_p95: Optional[float] = Field(default=None, ge=0.0, description="API p95 latency ms")
    custom: Dict[str, Any] = Field(default_factory=dict, description="Any extra key/values")


class MetricAckResponse(BaseModel):
    ok: bool
    app_id: str
    recorded_at: float


class MetricSummaryResponse(BaseModel):
    app_id: str
    summary: Dict[str, Any]


class SignalsResponse(BaseModel):
    app_id: str
    signal_count: int
    signals: List[Dict[str, Any]]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/{app_id}/metrics", response_model=MetricAckResponse, status_code=201)
async def post_metric(app_id: str, payload: MetricPayload, request: Request):
    """
    Accept a performance metric ping from a deployed app.

    Called automatically by the telemetry snippet injected into every deployed
    app's index.html.  The endpoint is unauthenticated intentionally — deployed
    apps run in user browsers and cannot safely hold credentials.  Rate-limiting
    is handled at the reverse-proxy layer (Railway / Cloudflare).
    """
    if payload.app_id and payload.app_id != app_id:
        app_id = payload.app_id

    data = payload.model_dump()
    data["app_id"] = app_id
    if not data.get("ts"):
        data["ts"] = time.time()

    await record_metric(data)

    logger.info(
        "[METRICS] app=%s load_ms=%d err=%.3f users=%d",
        app_id, payload.load_ms, payload.error_rate, payload.active_users,
    )

    return MetricAckResponse(ok=True, app_id=app_id, recorded_at=data["ts"])


@router.get("/{app_id}/metrics/summary", response_model=MetricSummaryResponse)
async def get_metrics_summary(app_id: str):
    """Return aggregated performance stats for a deployed app."""
    summary = await get_app_summary(app_id)
    if not summary:
        raise HTTPException(
            status_code=404,
            detail=f"No metrics recorded for app '{app_id}' yet.",
        )
    return MetricSummaryResponse(app_id=app_id, summary=summary)


@router.get("/{app_id}/metrics/signals", response_model=SignalsResponse)
async def get_optimization_signals(app_id: str):
    """
    Return current optimization signals for a deployed app.

    The optimization engine polls this endpoint; the frontend can also surface
    these signals as improvement suggestions to the user.
    """
    signals: List[OptimizationSignal] = await analyze_and_signal(app_id)
    return SignalsResponse(
        app_id=app_id,
        signal_count=len(signals),
        signals=[s.to_dict() for s in signals],
    )


@router.get("/metrics/apps")
async def list_tracked_apps():
    """
    List all app IDs that have sent at least one metric ping.
    Used by the optimization engine sweep and admin dashboards.
    """
    from ..services.performance_monitor import _store
    app_ids = await _store.get_all_app_ids()
    return {"app_ids": app_ids, "count": len(app_ids)}
