"""MCP dispatch routes — /api/mcp/servers and /api/mcp/call."""
from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException

from backend.services.mcp_client import bootstrap_registry, registry

# Initialize adapters at import time (idempotent if called again).
_bootstrapped = False


def _ensure_bootstrapped():
    global _bootstrapped
    if not _bootstrapped:
        try:
            bootstrap_registry()
            _bootstrapped = True
        except Exception as e:  # Don't bring down the whole router on adapter import error
            import logging
            logging.getLogger(__name__).warning("MCP bootstrap failed: %s", e)


router = APIRouter(prefix="/api/mcp", tags=["mcp"])


@router.get("/servers")
async def list_servers():
    _ensure_bootstrapped()
    return {"servers": registry.list_servers()}


@router.post("/call")
async def call_tool(body: dict = Body(...)):
    _ensure_bootstrapped()
    tool_id = body.get("tool_id")
    args = body.get("args") or {}
    if not tool_id:
        raise HTTPException(status_code=400, detail="tool_id is required")
    try:
        result = await registry.dispatch(tool_id, args)
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    return {"tool_id": tool_id, "result": result}
