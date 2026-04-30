"""
Monitoring routes — event tracking and metrics.

POST /monitoring/events/track  – persist a monitoring event to PostgreSQL.
GET  /monitoring/events         – list recent monitoring events.
GET  /monitoring/health         – liveness / readiness probe.
GET  /monitoring/metrics        – Prometheus metrics (when prometheus_client is installed).
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

# ── Optional Prometheus support ───────────────────────────────────────────────

try:
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    _prometheus_available = True
except ImportError:
    _prometheus_available = False

# ═══════════════════════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════════════════════


class TrackEventRequest(BaseModel):
    event_type: str
    user_id: str
    duration: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    success: bool = True
    error_message: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/health")
async def health():
    """Liveness probe: always 200 while the process is up."""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/metrics")
async def metrics():
    """Expose Prometheus metrics when prometheus_client is installed."""
    if not _prometheus_available:
        return PlainTextResponse(
            "# prometheus_client not installed\n", media_type="text/plain"
        )
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.post("/events/track")
async def track_event(body: TrackEventRequest):
    """Persist a monitoring event to PostgreSQL (monitoring_events table)."""
    event_id = str(uuid.uuid4())
    try:
        from ....db_pg import get_pool
        pool = await get_pool()
        if pool:
            async with pool.acquire() as conn:
                await conn.execute(
                    """INSERT INTO monitoring_events
                           (event_id, event_type, user_id, duration, metadata, success, error_message)
                       VALUES ($1, $2, $3, $4, $5, $6, $7)""",
                    event_id,
                    body.event_type,
                    body.user_id,
                    body.duration,
                    json.dumps(body.metadata or {}),
                    body.success,
                    body.error_message,
                )
    except Exception as exc:
        logger.warning("track_event: DB insert failed — %s", exc)
    return {"status": "ok", "event_id": event_id}


@router.get("/events")
async def list_events(
    limit: int = Query(50, ge=1, le=200),
    event_type: Optional[str] = None,
    user_id: Optional[str] = None,
):
    """List recent monitoring events from PostgreSQL, with optional filters."""
    try:
        from ....db_pg import get_pool
        pool = await get_pool()
        if not pool:
            return {
                "events": [],
                "message": "PostgreSQL not configured (DATABASE_URL missing)",
            }

        # Build a parameterised WHERE clause
        conditions: List[str] = []
        params: List[Any] = []
        if event_type:
            params.append(event_type)
            conditions.append(f"event_type = ${len(params)}")
        if user_id:
            params.append(user_id)
            conditions.append(f"user_id = ${len(params)}")

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        params.append(limit)
        sql = (
            f"SELECT event_id, event_type, user_id, timestamp, duration, "
            f"metadata, success, error_message "
            f"FROM monitoring_events {where} "
            f"ORDER BY timestamp DESC LIMIT ${len(params)}"
        )

        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)

        events = [
            {
                "event_id": r["event_id"],
                "event_type": r["event_type"],
                "user_id": r["user_id"],
                "timestamp": r["timestamp"].isoformat() if r["timestamp"] else None,
                "duration": r["duration"],
                "metadata": r["metadata"],
                "success": r["success"],
                "error_message": r["error_message"],
            }
            for r in rows
        ]
        return {"events": events, "count": len(events)}
    except Exception as exc:
        logger.warning("list_events: query failed — %s", exc)
        return {"events": [], "error": str(exc)}
