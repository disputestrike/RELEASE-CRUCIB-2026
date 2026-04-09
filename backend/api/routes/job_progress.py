# backend/api/routes/job_progress.py
"""
Real-time WebSocket endpoint for job orchestration progress.
Broadcasts agent start/complete/error events to frontend.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from typing import Dict, List, Set
import json
import logging
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter()

# Connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, job_id: str, websocket: WebSocket):
        await websocket.accept()
        if job_id not in self.active_connections:
            self.active_connections[job_id] = []
        self.active_connections[job_id].append(websocket)
        logger.info(f"Client connected to job {job_id}")
    
    def disconnect(self, job_id: str, websocket: WebSocket):
        if job_id in self.active_connections:
            self.active_connections[job_id].remove(websocket)
            if not self.active_connections[job_id]:
                del self.active_connections[job_id]
            logger.info(f"Client disconnected from job {job_id}")
    
    async def broadcast(self, job_id: str, message: dict):
        """Broadcast event to all clients watching this job."""
        if job_id not in self.active_connections:
            return
        
        message_json = json.dumps({
            **message,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        disconnected = []
        for websocket in self.active_connections[job_id]:
            try:
                await websocket.send_text(message_json)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.append(websocket)
        
        for ws in disconnected:
            self.disconnect(job_id, ws)

manager = ConnectionManager()

@router.websocket("/api/job/{job_id}/progress")
async def websocket_job_progress(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time job progress.
    
    Events sent:
    - phase_update: Phase progress changed
    - agent_start: Agent task started
    - agent_progress: Agent is running (progress update)
    - agent_complete: Agent task finished
    - agent_error: Agent task failed
    - build_complete: Entire build done
    """
    await manager.connect(job_id, websocket)
    
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            # Client can send ping/pong or other messages
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(job_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error for job {job_id}: {e}")
        manager.disconnect(job_id, websocket)

async def broadcast_event(job_id: str, event_type: str, **data):
    """
    Broadcast event to all clients watching a job.
    Called from executor.py after each agent runs.
    """
    event = {
        'type': event_type,
        **data
    }
    await manager.broadcast(job_id, event)

@router.get("/api/job/{job_id}/progress")
async def get_job_progress(job_id: str):
    """
    GET endpoint to retrieve current progress state.
    Useful for page reload - get current state without WebSocket.
    """
    try:
        from database import get_job_by_id
        job = await get_job_by_id(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {
            "job_id": job_id,
            "status": job.status,
            "total_progress": job.progress_percent,
            "is_running": job.status == "running",
            "phases": await build_phase_data(job),
            "created_at": job.created_at,
            "updated_at": job.updated_at
        }
    except Exception as e:
        logger.error(f"Error getting job progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def build_phase_data(job):
    """Build phase data for frontend display."""
    phases = []
    
    # Get all agents grouped by phase
    from database import get_agents_by_job
    agents = await get_agents_by_job(job.id)
    
    phase_map = {}
    for agent in agents:
        phase = agent.phase or "unknown"
        if phase not in phase_map:
            phase_map[phase] = []
        phase_map[phase].append(agent)
    
    # Build phase structure
    phase_order = [
        "requirements",
        "stack_selection", 
        "frontend_generation",
        "backend_generation",
        "database",
        "integration",
        "testing",
        "deployment"
    ]
    
    for phase_name in phase_order:
        if phase_name not in phase_map:
            continue
        
        phase_agents = phase_map[phase_name]
        completed = sum(1 for a in phase_agents if a.status == "complete")
        total = len(phase_agents)
        
        phases.append({
            "id": phase_name,
            "name": phase_name.replace("_", " ").title(),
            "status": "complete" if completed == total else "running" if completed > 0 else "queued",
            "progress": int(completed / total * 100) if total > 0 else 0,
            "agents": [
                {
                    "id": agent.id,
                    "name": agent.name,
                    "status": agent.status,
                    "error": agent.error if agent.status == "error" else None,
                    "output": agent.output[:200] if agent.output else None
                }
                for agent in phase_agents
            ],
            "completed": completed,
            "total": total
        })
    
    return phases
