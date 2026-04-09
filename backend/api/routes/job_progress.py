"""Job progress transport for live orchestration UI."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from orchestration.controller_brain import build_live_job_progress
from orchestration.runtime_state import get_job, get_job_events, get_steps

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: Dict[str, list[WebSocket]] = {}

    async def connect(self, job_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.setdefault(job_id, []).append(websocket)
        logger.info("job-progress websocket connected: %s", job_id)

    def disconnect(self, job_id: str, websocket: WebSocket) -> None:
        if job_id not in self.active_connections:
            return
        conns = self.active_connections[job_id]
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self.active_connections.pop(job_id, None)

    async def broadcast(self, job_id: str, message: dict) -> None:
        if job_id not in self.active_connections:
            return
        payload = json.dumps({**message, "ts": datetime.now(timezone.utc).isoformat()})
        dead: list[WebSocket] = []
        for ws in list(self.active_connections[job_id]):
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(job_id, ws)


manager = ConnectionManager()


def _event_level(event: Dict[str, Any]) -> str:
    payload = event.get("payload") or {}
    if payload.get("error") or payload.get("failure_reason"):
        return "error"
    if str(event.get("event_type") or event.get("type") or "").endswith("completed"):
        return "success"
    return "info"


def _event_message(event: Dict[str, Any]) -> str:
    payload = event.get("payload") or {}
    if payload.get("message"):
        return str(payload["message"])
    if payload.get("error"):
        return str(payload["error"])
    if payload.get("failure_reason"):
        return str(payload["failure_reason"])
    step_key = payload.get("step_key")
    agent_name = payload.get("agent_name") or payload.get("agent")
    event_type = str(event.get("event_type") or event.get("type") or "event").replace("_", " ")
    if agent_name and step_key:
        return f"{agent_name} ({step_key}) {event_type}"
    if agent_name:
        return f"{agent_name} {event_type}"
    if step_key:
        return f"{step_key} {event_type}"
    return event_type


async def _load_job_progress_payload(job_id: str) -> Dict[str, Any]:
    job = await get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    steps = await get_steps(job_id)
    events = await get_job_events(job_id, limit=250)
    controller = build_live_job_progress(job=job, steps=steps, events=events)
    controller["logs"] = [
        {
            "timestamp": event.get("created_at"),
            "type": event.get("event_type"),
            "agent": (event.get("payload") or {}).get("agent_name")
            or (event.get("payload") or {}).get("agent")
            or (event.get("payload") or {}).get("step_key")
            or "system",
            "message": _event_message(event),
            "level": _event_level(event),
        }
        for event in events[-50:]
    ]
    return controller


@router.get("/api/job/{job_id}/progress")
async def get_job_progress(job_id: str):
    """Bootstrap state for the orchestration Kanban UI."""
    return await _load_job_progress_payload(job_id)


@router.websocket("/api/job/{job_id}/progress")
async def websocket_job_progress(websocket: WebSocket, job_id: str):
    await manager.connect(job_id, websocket)
    try:
        bootstrap = await _load_job_progress_payload(job_id)
        await websocket.send_text(json.dumps({"type": "bootstrap", "payload": bootstrap}))
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except HTTPException:
        await websocket.close(code=1008)
    except WebSocketDisconnect:
        manager.disconnect(job_id, websocket)
    except Exception:
        manager.disconnect(job_id, websocket)
        try:
            await websocket.close(code=1011)
        except Exception:
            pass


async def broadcast_event(job_id: str, event_type: str, **data):
    """Broadcast executor or project progress events to live job viewers."""
    event = {"type": event_type, **data}
    try:
        event["snapshot"] = await _load_job_progress_payload(job_id)
    except HTTPException:
        logger.debug("job-progress snapshot unavailable for %s", job_id)
    except Exception:
        logger.debug("job-progress snapshot refresh failed for %s", job_id, exc_info=True)
    await manager.broadcast(job_id, event)
    logger.debug("job-progress [%s] -> %s", event_type, job_id)
