"""WS-B: SSE endpoint /api/chat/react streaming ReAct events."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Dict, Optional

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from services.react_loop import react_stream
from services.prompts import load_prompt
from services.tools import get_tools

router = APIRouter(prefix="/api/chat", tags=["chat-react"])


class ReactChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    thinking_budget: int = 8000
    max_steps: int = 6


async def _sse_iter(req: ReactChatRequest, request: Request) -> AsyncIterator[bytes]:
    system_prompt = load_prompt("honesty_bias.v1.md")
    tools = get_tools()
    async for event in react_stream(
        req.prompt,
        system_prompt=system_prompt,
        tools=tools,
        thinking_budget=req.thinking_budget,
        max_steps=req.max_steps,
    ):
        if await request.is_disconnected():
            return
        line = f"data: {json.dumps(event, default=str)}\n\n"
        yield line.encode("utf-8")


@router.post("/react")
async def chat_react(req: ReactChatRequest, request: Request) -> StreamingResponse:
    return StreamingResponse(
        _sse_iter(req, request),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/react/health")
async def chat_react_health() -> Dict[str, Any]:
    return {"ok": True, "endpoint": "/api/chat/react", "method": "POST", "sse": True}
