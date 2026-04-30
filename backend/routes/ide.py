"""IDE routes — debugger, profiler, and linter."""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["ide"])


def _get_auth():
    from ....server import get_current_user
    return get_current_user


def _get_optional_user():
    from ....server import get_optional_user
    return get_optional_user


def _get_db():
    import server

    return server.db


async def _resolve_ws(project_id, user):
    from ....server import _resolve_project_workspace_path_for_user
    return await _resolve_project_workspace_path_for_user(project_id, user)


class IDEBreakpointRequest(BaseModel):
    file_path: str
    line: int
    column: int = 0
    condition: Optional[str] = None


@router.post("/ide/debug/start")
async def ide_debug_start(
    project_id: str = Query(...), user: dict = Depends(_get_auth())
):
    """Start a debug session. Wired to DebuggerManager in ide_features.py."""
    from ide_features import debugger_manager

    await _resolve_ws(project_id, user)
    session_id = str(uuid.uuid4())
    session = await debugger_manager.start_debug_session(
        session_id, project_id, user_id=user["id"]
    )
    return {
        "session_id": session.session_id,
        "project_id": session.project_id,
        "status": session.status,
    }


@router.post("/ide/debug/{session_id}/breakpoint")
async def ide_debug_set_breakpoint(
    session_id: str, body: IDEBreakpointRequest, user: dict = Depends(_get_auth())
):
    """Set a breakpoint in a debug session."""
    from ide_features import BreakPoint, debugger_manager

    bp = BreakPoint(
        file_path=body.file_path,
        line=body.line,
        column=body.column,
        condition=body.condition,
    )
    try:
        result = await debugger_manager.set_breakpoint(
            session_id, bp, user_id=user["id"]
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "id": result.id,
        "file_path": result.file_path,
        "line": result.line,
        "column": result.column,
        "condition": result.condition,
        "enabled": result.enabled,
    }


@router.delete("/ide/debug/{session_id}/breakpoint/{breakpoint_id}")
async def ide_debug_remove_breakpoint(
    session_id: str, breakpoint_id: str, user: dict = Depends(_get_auth())
):
    """Remove a breakpoint."""
    from ide_features import debugger_manager

    try:
        await debugger_manager.remove_breakpoint(
            session_id, breakpoint_id, user_id=user["id"]
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "removed"}


@router.post("/ide/profiler/start")
async def ide_profiler_start(
    project_id: str = Query(...), user: dict = Depends(_get_auth())
):
    """Start profiler session. Wired to ProfilerManager in ide_features.py."""
    from ide_features import profiler_manager

    await _resolve_ws(project_id, user)
    session_id = str(uuid.uuid4())
    out = await profiler_manager.start_profiler(
        session_id, project_id, user_id=user["id"]
    )
    return out


@router.post("/ide/profiler/stop")
async def ide_profiler_stop(
    session_id: str = Query(...), user: dict = Depends(_get_auth())
):
    """Stop profiler session."""
    from ide_features import profiler_manager

    try:
        out = await profiler_manager.stop_profiler(session_id, user_id=user["id"])
    except ValueError:
        raise HTTPException(status_code=404, detail="Session not found")
    return out


@router.post("/ide/lint")
async def ide_lint(
    project_id: str = Query(...),
    file_path: Optional[str] = None,
    code: Optional[str] = None,
    user: dict = Depends(_get_auth()),
):
    """Run linter (pyflakes for Python, node --check for JS/TS). Wired to LinterManager."""
    from ide_features import linter_manager

    await _resolve_ws(project_id, user)
    issues = await linter_manager.run_lint(project_id, file_path or "", code)
    return {
        "issues": [
            {
                "file_path": i.file_path,
                "line": i.line,
                "column": i.column,
                "message": i.message,
                "severity": i.severity,
            }
            for i in issues
        ]
    }
