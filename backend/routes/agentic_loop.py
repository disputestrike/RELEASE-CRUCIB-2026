"""
backend/routes/agentic_loop.py
───────────────────────────────
REST + SSE endpoints for the agentic tool-using loop (observe-act-inspect-review).

Endpoints
─────────
POST /api/agent/loop
    Body: { goal, max_steps?, thinking_budget?, system_prompt?, run_id? }
    Returns: StreamingResponse (text/event-stream) of structured loop events.

POST /api/agent/loop/run
    Body: same as above
    Returns: JSON envelope with all collected events (non-streaming).

GET  /api/agent/loop/health
    Returns: {"ok": true, "endpoint": "/api/agent/loop"}
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..services.agentic_tool_loop import agentic_tool_stream
from ..services.tools import get_tools

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["agentic-loop"])


# ─────────────────────────────────────────────────────────────────────────────
# Request schema
# ─────────────────────────────────────────────────────────────────────────────

class AgenticLoopRequest(BaseModel):
    goal: str = Field(..., min_length=1, max_length=8000, description="Natural-language goal for the agent.")
    max_steps: int = Field(default=8, ge=1, le=32, description="Maximum observe-act-inspect-review iterations.")
    thinking_budget: int = Field(default=8000, ge=100, le=128000, description="Token budget hint.")
    system_prompt: Optional[str] = Field(default=None, max_length=4000, description="Optional system prompt.")
    run_id: Optional[str] = Field(default=None, description="Optional run identifier for tracing.")


# ─────────────────────────────────────────────────────────────────────────────
# SSE streaming helper
# ─────────────────────────────────────────────────────────────────────────────

async def _sse_iter(req: AgenticLoopRequest, request: Request) -> AsyncIterator[bytes]:
    """Yield SSE-formatted bytes for each loop event."""
    run_id = req.run_id or uuid.uuid4().hex[:12]
    tools = get_tools()
    try:
        async for event in agentic_tool_stream(
            req.goal,
            tools=tools,
            system_prompt=req.system_prompt,
            max_steps=req.max_steps,
            thinking_budget=req.thinking_budget,
            run_id=run_id,
        ):
            if await request.is_disconnected():
                return
            line = f"data: {json.dumps(event, default=str)}\n\n"
            yield line.encode("utf-8")
    except Exception as exc:
        logger.exception("agentic_loop SSE error: %s", exc)
        error_event = {"type": "error", "message": str(exc), "run_id": run_id}
        yield f"data: {json.dumps(error_event)}\n\n".encode("utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/loop")
async def agentic_loop_stream(req: AgenticLoopRequest, request: Request) -> StreamingResponse:
    """Stream the agentic loop as Server-Sent Events."""
    return StreamingResponse(
        _sse_iter(req, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/loop/run")
async def agentic_loop_run(req: AgenticLoopRequest) -> Dict[str, Any]:
    """Run the agentic loop to completion and return all events as JSON."""
    run_id = req.run_id or uuid.uuid4().hex[:12]
    tools = get_tools()
    events: List[Dict[str, Any]] = []
    try:
        async for event in agentic_tool_stream(
            req.goal,
            tools=tools,
            system_prompt=req.system_prompt,
            max_steps=req.max_steps,
            thinking_budget=req.thinking_budget,
            run_id=run_id,
        ):
            events.append(event)
    except Exception as exc:
        logger.exception("agentic_loop_run error: %s", exc)
        events.append({"type": "error", "message": str(exc), "run_id": run_id})

    final = next((e for e in reversed(events) if e.get("type") == "final"), None)
    return {
        "run_id": run_id,
        "events": events,
        "final": final,
        "iterations": final.get("iterations") if final else len(events),
    }


@router.get("/loop/health")
async def agentic_loop_health() -> Dict[str, Any]:
    """Health check for the agentic loop endpoint."""
    return {"ok": True, "endpoint": "/api/agent/loop"}
