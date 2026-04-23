"""
build_progress.py — WebSocket endpoint for real-time build progress streaming
"""

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["build-progress"])


@router.websocket("/ws/projects/{project_id}/build")
async def build_progress_ws(websocket: WebSocket, project_id: str):
    """
    WebSocket endpoint for real-time build progress.
    
    Authentication: Pass JWT token in query param (?token=...)
    
    Message format sent to client:
    {
        "type": "build_event",
        "event_type": "agent_started|agent_completed|file_generated|...",
        "message": "Human-readable message",
        "timestamp": "2024-04-22T...",
        "data": {...}
    }
    """
    from db_pg import get_pg_pool
    from server import JWT_ALGORITHM, JWT_SECRET
    import jwt as pyjwt
    
    # Authenticate via token query param
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="No token provided")
        return
    
    try:
        payload = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
    except Exception as e:
        logger.warning(f"Invalid token: {e}")
        await websocket.close(code=4001, reason="Invalid token")
        return
    
    # Verify user owns the project
    try:
        from server import _user_can_access_project_workspace
        ok = await _user_can_access_project_workspace(user_id, project_id)
        if not ok:
            await websocket.close(code=4003, reason="Access denied")
            return
    except ImportError:
        # If helper not available, allow (fallback)
        pass
    
    await websocket.accept()
    
    # Get event bus and subscribe
    from services.runtime.build_events import get_build_event_bus
    
    bus = get_build_event_bus()
    
    async def send_event(event):
        """Send event to WebSocket client."""
        try:
            await websocket.send_json({
                "type": "build_event",
                **event.to_dict()
            })
        except Exception as e:
            logger.warning(f"Failed to send event: {e}")
    
    await bus.subscribe(project_id, send_event)
    
    # Send event history to client on connection
    try:
        history = await bus.get_history(project_id, limit=50)
        for event_dict in history:
            await websocket.send_json({
                "type": "build_event",
                **event_dict
            })
    except Exception as e:
        logger.warning(f"Failed to send history: {e}")
    
    # Keep connection open
    try:
        while True:
            # Wait for client to send anything (usually won't happen, but handles disconnect)
            data = await websocket.receive_text()
            # Optionally handle client messages (e.g., "ping" for keepalive)
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from build progress for {project_id}")
    finally:
        await bus.unsubscribe(project_id, send_event)


@router.get("/projects/{project_id}/build/history")
async def get_build_history(
    project_id: str,
    limit: int = 100,
    user: dict = None,  # Optional - no auth required for demo
):
    """Get historical build events for a project."""
    from services.runtime.build_events import get_build_event_bus
    
    bus = get_build_event_bus()
    history = await bus.get_history(project_id, limit=limit)
    
    return {
        "project_id": project_id,
        "events": history,
        "count": len(history),
    }
