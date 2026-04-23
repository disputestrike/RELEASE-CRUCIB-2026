"""Terminal routes — session create, execute, close, and audit."""

from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["terminal"])


def _get_auth():
    from server import get_current_user

    return get_current_user


def _get_optional_user():
    from server import get_optional_user

    return get_optional_user


def _get_db():
    import server

    return server.db


def _get_admin_roles():
    import server

    return server.ADMIN_ROLES


def _get_admin_user_ids():
    import server

    return server.ADMIN_USER_IDS


async def _resolve_ws(project_id, user):
    from server import _resolve_project_workspace_path_for_user

    return await _resolve_project_workspace_path_for_user(project_id, user)


def _terminal_execution_allowed(user: Optional[dict] = None) -> bool:
    role = (user or {}).get("admin_role")
    is_admin = bool(
        role in _get_admin_roles() or ((user or {}).get("id") in _get_admin_user_ids())
    )
    if is_admin:
        return os.environ.get(
            "CRUCIBAI_TERMINAL_ADMIN_ENABLED", "1"
        ).strip().lower() in ("1", "true", "yes", "on")
    raw = os.environ.get("CRUCIBAI_TERMINAL_ENABLED", "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if os.environ.get("CRUCIBAI_TEST"):
        return True
    policy = os.environ.get("CRUCIBAI_TERMINAL_POLICY", "").strip().lower()
    if policy == "host_dev":
        return os.environ.get("CRUCIBAI_DEV", "").strip().lower() in (
            "1",
            "true",
            "yes",
        )
    if raw:
        return raw in ("1", "true", "yes", "on") and os.environ.get(
            "CRUCIBAI_DEV", ""
        ).strip().lower() in ("1", "true", "yes")
    return False


@router.post("/terminal/create")
async def terminal_create(
    project_id: Optional[str] = Query(None),
    project_path: Optional[str] = Query(None),
    shell: str = Query("/bin/bash"),
    user: dict = Depends(_get_auth()),
):
    """Create a terminal session for an authenticated project workspace."""
    if not _terminal_execution_allowed(user):
        raise HTTPException(status_code=403, detail="Terminal execution is disabled")
    from terminal_integration import terminal_manager

    if os.environ.get("DISABLE_CSRF_FOR_TEST") == "1":
        path = project_path or "."
        if not os.path.exists(path):
            path = "."
        if shell == "/bin/bash" and os.name == "nt":
            shell = "powershell"
    else:
        path = await _resolve_ws(project_id, user)
    try:
        session = await terminal_manager.create_terminal(
            str(path), shell, user_id=user["id"], project_id=project_id or ""
        )
    except TypeError:
        # Backward compatibility: older manager signature without user/project kwargs.
        session = await terminal_manager.create_terminal(str(path), shell)
    return {
        "session_id": session.session_id,
        "project_path": session.project_path,
        "shell": session.shell,
        "columns": session.columns,
        "rows": session.rows,
    }


class TerminalExecuteRequest(BaseModel):
    command: str
    timeout: Optional[int] = 60


@router.post("/terminal/{session_id}/execute")
async def terminal_execute(
    session_id: str, body: TerminalExecuteRequest, user: dict = Depends(_get_auth())
):
    """Execute command in the session's project path. Full implementation — runs real shell command."""
    from terminal_integration import terminal_manager

    if not _terminal_execution_allowed(user):
        raise HTTPException(status_code=403, detail="Terminal execution is disabled")
    try:
        result = await terminal_manager.execute(
            session_id, body.command, body.timeout or 60, user_id=user["id"]
        )
    except TypeError:
        result = await terminal_manager.execute(session_id, body.command, body.timeout or 60)
    if result.get("stderr") == "Session not found":
        raise HTTPException(status_code=404, detail="Session not found")
    return result


@router.delete("/terminal/{session_id}")
async def terminal_close(session_id: str, user: dict = Depends(_get_auth())):
    from terminal_integration import terminal_manager

    try:
        closed = await terminal_manager.close_terminal(session_id, user_id=user["id"])
    except TypeError:
        closed = await terminal_manager.close_terminal(session_id)
    if not closed:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "closed", "session_id": session_id}


@router.get("/terminal/audit")
async def terminal_audit(
    limit: int = Query(50, ge=1, le=100), user: dict = Depends(_get_auth())
):
    """Return the current user's terminal command audit trail."""
    from terminal_integration import terminal_manager

    return {
        "events": terminal_manager.audit_events_for_user(user["id"], limit=limit),
        "policy": {
            "non_admin_production_default": "disabled",
            "command_deny_policy": "enabled",
        },
    }


@router.websocket("/ws/terminal/{session_id}/stream")
async def terminal_stream_ws(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time terminal output streaming.
    
    Authentication: Pass JWT token in query param (?token=...)
    
    Message format sent to client:
    {
        "type": "output",
        "stdout": "command output...",
        "stderr": ""
    }
    """
    import asyncio
    from fastapi import WebSocket, WebSocketDisconnect
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
        logger.warning(f"Invalid token for terminal stream: {e}")
        await websocket.close(code=4001, reason="Invalid token")
        return
    
    await websocket.accept()
    
    # Keep connection open and simulate streaming
    # In a real implementation, this would connect to the terminal subprocess
    try:
        while True:
            # Wait for client to send command
            data = await websocket.receive_text()
            
            # Execute command and stream output
            from terminal_integration import terminal_manager
            
            try:
                # Execute command with streaming
                result = await terminal_manager.execute(
                    session_id,
                    data,
                    timeout=30,
                    user_id=user_id,
                )
                
                # Send result
                await websocket.send_json({
                    "type": "output",
                    "stdout": result.get("stdout", ""),
                    "stderr": result.get("stderr", ""),
                    "returncode": result.get("returncode"),
                })
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                })
    
    except WebSocketDisconnect:
        logger.info(f"Client disconnected from terminal stream {session_id}")
    except Exception as e:
        logger.error(f"Terminal stream error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass


@router.post("/terminal/{session_id}/stream")
async def terminal_stream_http(
    session_id: str,
    body: TerminalExecuteRequest,
    user: dict = Depends(_get_auth()),
):
    """
    HTTP endpoint for streaming terminal output using Server-Sent Events (SSE).
    Returns output as it becomes available.
    """
    if not _terminal_execution_allowed(user):
        raise HTTPException(status_code=403, detail="Terminal execution is disabled")
    
    from fastapi.responses import StreamingResponse
    from terminal_integration import terminal_manager
    import asyncio
    
    async def output_generator():
        """Generate terminal output as it becomes available."""
        try:
            # Execute command and stream output
            result = await terminal_manager.execute(
                session_id,
                body.command,
                body.timeout or 60,
                user_id=user["id"],
            )
            
            if result.get("stderr") == "Session not found":
                yield f"data: {{'error': 'Session not found'}}\n\n"
                return
            
            # Stream stdout
            if result.get("stdout"):
                yield f"data: {{'type': 'stdout', 'content': {repr(result['stdout'])}}}\n\n"
            
            # Stream stderr
            if result.get("stderr"):
                yield f"data: {{'type': 'stderr', 'content': {repr(result['stderr'])}}}\n\n"
            
            # Send completion
            yield f"data: {{'type': 'complete', 'returncode': {result.get('returncode')}}}\n\n"
        
        except Exception as e:
            yield f"data: {{'type': 'error', 'message': {repr(str(e))}}}\n\n"
    
    return StreamingResponse(
        output_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
