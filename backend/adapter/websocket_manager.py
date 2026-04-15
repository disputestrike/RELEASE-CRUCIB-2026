"""
WebSocket Manager — manages per-job WebSocket connections.
Broadcasts events to all connected frontend clients for a job.
"""
import asyncio
import logging
from typing import Dict, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, job_id: str):
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = set()
        self.active_connections[job_id].add(websocket)
        logger.info("WS connected for job %s (total: %d)", job_id,
                    len(self.active_connections[job_id]))

    def disconnect(self, websocket: WebSocket, job_id: str):
        if job_id in self.active_connections:
            self.active_connections[job_id].discard(websocket)
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]

    async def broadcast(self, job_id: str, event: dict):
        if job_id not in self.active_connections:
            return
        dead = set()
        for ws in list(self.active_connections[job_id]):
            try:
                await ws.send_json(event)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self.active_connections[job_id].discard(ws)

    def connection_count(self, job_id: str) -> int:
        return len(self.active_connections.get(job_id, set()))


manager = WebSocketManager()
