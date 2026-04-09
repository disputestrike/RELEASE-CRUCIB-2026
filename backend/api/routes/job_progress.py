"""Real-time WebSocket for job progress - WIRED TO EXECUTOR"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import json, logging
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections = {}
    
    async def connect(self, job_id: str, websocket: WebSocket):
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = []
        self.active_connections[job_id].append(websocket)
        logger.info(f"✓ Client → job {job_id}")
    
    def disconnect(self, job_id: str, websocket: WebSocket):
        if job_id in self.active_connections:
            self.active_connections[job_id].remove(websocket)
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]
    
    async def broadcast(self, job_id: str, message: dict):
        if job_id not in self.active_connections:
            return
        msg_json = json.dumps({**message, 'ts': datetime.utcnow().isoformat()})
        dead = []
        for ws in self.active_connections[job_id]:
            try:
                await ws.send_text(msg_json)
            except:
                dead.append(ws)
        for ws in dead:
            self.disconnect(job_id, ws)

manager = ConnectionManager()

@router.websocket("/api/job/{job_id}/progress")
async def websocket_job_progress(websocket: WebSocket, job_id: str):
    await manager.connect(job_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(job_id, websocket)

async def broadcast_event(job_id: str, event_type: str, **data):
    """EXECUTOR CALLS THIS after each agent runs"""
    event = {'type': event_type, **data}
    await manager.broadcast(job_id, event)
