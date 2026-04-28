"""
backend/routes/agentic_loop.py
───────────────────────────────
REST + SSE endpoints for the agentic tool-using loop (observe-act-inspect-review).

Endpoints
─────────
POST /api/agent/loop
    Body: { goal, max_steps?, thinking_budget?, system_prompt?, tools? }
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
    from backend.services.agentic_tool_loop import agentic_tool_stream
    from backend.services.tools import get_tools

    run_id = req.run_id or str(uuid.uuid4())
    tools = get_tools()

    async for event in agentic_tool_stream(
        req.goal,
        tools=tools,
        system_prompt=req.system_prompt,
        max_steps=req.max_steps,
        thinking_budget=req.thinking_budget,
        run_id=run_id,
    ):
        if await request.is_disconnected():
            logger.info("[agentic_loop] client disconnected run_id=%s", run_id)
            return
        line = f"data: {json.dumps(event, default=str)}\n\n"
        yield line.encode("utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/loop")
async def agentic_loop_stream(req: AgenticLoopRequest, request: Request) -> StreamingResponse:
    """Stream the observe-act-inspect-review loop as Server-Sent Events."""
    return StreamingResponse(
        _sse_iter(req, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Run-Id": req.run_id or "",
        },
    )


@router.post("/loop/run")
async def agentic_loop_run(req: AgenticLoopRequest) -> Dict[str, Any]:
    """Run the loop to completion and return all events as a JSON list."""
    from backend.services.agentic_tool_loop import agentic_tool_stream
    from backend.services.tools import get_tools

    run_id = req.run_id or str(uuid.uuid4())
    tools = get_tools()
    events: List[Dict[str, Any]] = []

    async for event in agentic_tool_stream(
        req.goal,
        tools=tools,
        system_prompt=req.system_prompt,
        max_steps=req.max_steps,
        thinking_budget=req.thinking_budget,
        run_id=run_id,
    ):
        events.append(event)

    final = next((e for e in reversed(events) if e.get("type") == "final"), None)
    errors = [e for e in events if e.get("type") == "error"]

    return {
        "run_id": run_id,
        "goal": req.goal,
        "status": "completed" if not errors else "completed_with_errors",
        "iterations": (final or {}).get("iterations", len(events)),
        "elapsed_ms": (final or {}).get("elapsed_ms"),
        "final_content": (final or {}).get("content", ""),
        "events": events,
        "error_count": len(errors),
    }


@router.get("/loop/health")
async def agentic_loop_health() -> Dict[str, Any]:
    """Health check for the agentic loop endpoint."""
    return {
        "ok": True,
        "endpoint": "/api/agent/loop",
        "streaming_endpoint": "/api/agent/loop (POST, SSE)",
        "batch_endpoint": "/api/agent/loop/run (POST, JSON)",
        "phases": ["observe", "act", "inspect", "review"],
    }
