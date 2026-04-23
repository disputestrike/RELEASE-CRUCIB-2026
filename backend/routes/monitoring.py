"""Monitoring and health check routes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List
from uuid import uuid4

from fastapi import APIRouter

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

_EVENTS: List[Dict[str, Any]] = []

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@router.post("/events/track")
async def track_event(payload: Dict[str, Any]):
    """Track a monitoring event."""
    event = {
        "event_id": str(uuid4()),
        "event_type": payload.get("event_type", "unknown"),
        "user_id": payload.get("user_id"),
        "success": bool(payload.get("success", True)),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }
    _EVENTS.insert(0, event)
    # Keep bounded memory footprint for in-process runs.
    if len(_EVENTS) > 1000:
        del _EVENTS[1000:]
    return {"status": "ok", "event_id": event["event_id"]}


@router.get("/events")
async def list_events(limit: int = 50):
    """List recently tracked monitoring events."""
    safe_limit = max(1, min(limit, 200))
    return {"events": _EVENTS[:safe_limit]}


@router.get("/metrics")
async def get_metrics():
    """Get system metrics"""
    return {"status": "ok", "metrics": {}}


@router.get("/status")
async def get_status():
    """Get system status"""
    return {"status": "ok"}
