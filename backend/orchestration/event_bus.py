"""
event_bus.py — In-process pub/sub for job events.
Consumers (SSE/WebSocket handlers) subscribe to a job's stream.
Events are also persisted to DB via runtime_state.
"""
import asyncio
import logging
from typing import Dict, List, Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)

# ── In-memory subscriber registry ────────────────────────────────────────────
# job_id → list of asyncio.Queue
_subscribers: Dict[str, List[asyncio.Queue]] = defaultdict(list)
_lock = asyncio.Lock()


async def subscribe(job_id: str) -> asyncio.Queue:
    """Return a queue that receives event dicts for this job."""
    q: asyncio.Queue = asyncio.Queue(maxsize=500)
    async with _lock:
        _subscribers[job_id].append(q)
    return q


async def unsubscribe(job_id: str, queue: asyncio.Queue) -> None:
    async with _lock:
        subs = _subscribers.get(job_id, [])
        if queue in subs:
            subs.remove(queue)
        if not subs:
            _subscribers.pop(job_id, None)


async def publish(job_id: str, event_type: str,
                  payload: Optional[Dict[str, Any]] = None,
                  step_id: Optional[str] = None) -> None:
    """Publish event to all in-memory subscribers and mirror to WebSocket progress."""
    event = {
        "job_id": job_id,
        "step_id": step_id,
        "type": event_type,
        "payload": payload or {},
    }
    async with _lock:
        subs = list(_subscribers.get(job_id, []))
    for q in subs:
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("event_bus: subscriber queue full for job %s", job_id)
    try:
        from api.routes.job_progress import broadcast_event as websocket_broadcast_event

        await websocket_broadcast_event(job_id, event_type, step_id=step_id, payload=payload or {})
    except Exception:
        logger.debug("event_bus: websocket mirror unavailable for job %s", job_id)


def publish_sync(job_id: str, event_type: str,
                 payload: Optional[Dict[str, Any]] = None,
                 step_id: Optional[str] = None) -> None:
    """Sync wrapper — schedules publish on the running event loop."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(publish(job_id, event_type, payload, step_id))
    except RuntimeError:
        pass  # no loop running yet
