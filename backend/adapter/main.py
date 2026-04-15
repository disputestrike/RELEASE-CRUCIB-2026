"""
CrucibAI Backend Adapter
Wraps the existing 245-agent engine with:
- REST endpoints matching the frontend's backendContract.ts
- WebSocket /ws/events for real-time event streaming
- Spawn engine for parallel agent execution
- Event bridge translating internal events → frontend events
"""
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

app = FastAPI(
    title="CrucibAI Adapter",
    description="REST + WebSocket adapter layer for the 245-agent engine",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register all route modules ────────────────────────────────────────────────
from adapter.routes import build, files, preview, deploy, automation, spawn, trust

app.include_router(build.router)
app.include_router(files.router)
app.include_router(preview.router)
app.include_router(deploy.router)
app.include_router(automation.router)
app.include_router(spawn.router)
app.include_router(trust.router)


# ── WebSocket endpoint ────────────────────────────────────────────────────────
@app.websocket("/ws/events")
async def websocket_events(websocket: WebSocket, jobId: str = None):
    """
    Real-time event stream for a job.
    Frontend's eventBus connects here and receives normalized events.
    Also bridges our internal SSE events to WebSocket format.
    """
    if not jobId:
        await websocket.close(code=1008, reason="Missing jobId")
        return

    from adapter.websocket_manager import manager
    await manager.connect(websocket, jobId)

    # Also bridge existing SSE events to this WebSocket
    try:
        from orchestration.event_bus import subscribe, unsubscribe
        queue = await subscribe(jobId)

        import asyncio

        async def bridge_sse():
            """Forward internal SSE events to WebSocket clients."""
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30)
                    if event is None:
                        break
                    # Translate internal event → frontend format
                    from adapter.services.event_bridge import bridge_internal_event
                    bridge_internal_event(
                        jobId,
                        event.get("type") or event.get("event_type", ""),
                        event.get("payload", event),
                    )
                except asyncio.TimeoutError:
                    # Send keepalive ping
                    await manager.broadcast(jobId, {"type": "ping", "jobId": jobId})
                except Exception as e:
                    logger.debug("bridge_sse: %s", e)
                    break

        bridge_task = asyncio.create_task(bridge_sse())

        try:
            while True:
                data = await websocket.receive_text()
                # Handle subscribe/unsubscribe from client
                import json
                try:
                    msg = json.loads(data)
                    if msg.get("action") == "ping":
                        await websocket.send_json({"type": "pong"})
                except Exception:
                    pass
        except WebSocketDisconnect:
            pass
        finally:
            bridge_task.cancel()
            await unsubscribe(jobId, queue)

    except Exception as e:
        logger.warning("ws events error: %s", e)
        # Simple mode: just keep connection alive
        try:
            while True:
                data = await websocket.receive_text()
        except WebSocketDisconnect:
            pass
    finally:
        manager.disconnect(websocket, jobId)


@app.get("/health")
async def health():
    return {"status": "ok", "adapter": "v1", "agents": 245}


# ── Mount adapter onto main server.py app ────────────────────────────────────
def mount_on_main_app(main_app):
    """Mount the adapter router onto the existing FastAPI app."""
    from fastapi import APIRouter
    adapter_router = APIRouter()

    # Mount all routes
    for router in [build.router, files.router, preview.router, deploy.router,
                   automation.router, spawn.router, trust.router]:
        main_app.include_router(router)

    # Mount WebSocket
    @main_app.websocket("/ws/events")
    async def _ws(websocket: WebSocket, jobId: str = None):
        await websocket_events(websocket, jobId)

    logger.info("Adapter mounted on main app")
