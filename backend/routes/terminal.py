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
    is_admin = bool(role in _get_admin_roles() or ((user or {}).get("id") in _get_admin_user_ids()))
    if is_admin:
        return os.environ.get("CRUCIBAI_TERMINAL_ADMIN_ENABLED", "1").strip().lower() in ("1", "true", "yes", "on")
    raw = os.environ.get("CRUCIBAI_TERMINAL_ENABLED", "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    if os.environ.get("CRUCIBAI_TEST"):
        return True
    policy = os.environ.get("CRUCIBAI_TERMINAL_POLICY", "").strip().lower()
    if policy == "host_dev":
        return os.environ.get("CRUCIBAI_DEV", "").strip().lower() in ("1", "true", "yes")
    if raw:
        return raw in ("1", "true", "yes", "on") and os.environ.get("CRUCIBAI_DEV", "").strip().lower() in ("1", "true", "yes")
    return False


@router.post("/terminal/create")
async def terminal_create(project_id: Optional[str] = Query(None), shell: str = Query("/bin/bash"), user: dict = Depends(_get_auth())):
    """Create a terminal session for an authenticated project workspace."""
    if not _terminal_execution_allowed(user):
        raise HTTPException(status_code=403, detail="Terminal execution is disabled")
    from terminal_integration import terminal_manager
    path = await _resolve_ws(project_id, user)
    session = await terminal_manager.create_terminal(str(path), shell, user_id=user["id"], project_id=project_id or "")
    return {"session_id": session.session_id, "project_path": session.project_path, "shell": session.shell, "columns": session.columns, "rows": session.rows}


class TerminalExecuteRequest(BaseModel):
    command: str
    timeout: Optional[int] = 60


@router.post("/terminal/{session_id}/execute")
async def terminal_execute(session_id: str, body: TerminalExecuteRequest, user: dict = Depends(_get_auth())):
    """Execute command in the session's project path. Full implementation — runs real shell command."""
    from terminal_integration import terminal_manager
    if not _terminal_execution_allowed(user):
        raise HTTPException(status_code=403, detail="Terminal execution is disabled")
    result = await terminal_manager.execute(session_id, body.command, body.timeout or 60, user_id=user["id"])
    if result.get("stderr") == "Session not found":
        raise HTTPException(status_code=404, detail="Session not found")
    return result


@router.delete("/terminal/{session_id}")
async def terminal_close(session_id: str, user: dict = Depends(_get_auth())):
    from terminal_integration import terminal_manager
    closed = await terminal_manager.close_terminal(session_id, user_id=user["id"])
    if not closed:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "closed", "session_id": session_id}


@router.get("/terminal/audit")
async def terminal_audit(limit: int = Query(50, ge=1, le=100), user: dict = Depends(_get_auth())):
    """Return the current user's terminal command audit trail."""
    from terminal_integration import terminal_manager
    return {
        "events": terminal_manager.audit_events_for_user(user["id"], limit=limit),
        "policy": {
            "non_admin_production_default": "disabled",
            "command_deny_policy": "enabled",
        },
    }
