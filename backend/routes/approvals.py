"""
backend/routes/approvals.py
──────────────────────────────
Safety / governance approval endpoints.

Spec: O – Safety + Governance
Branch: engineering/master-list-closeout

Endpoints:
  GET  /api/approvals                  — list pending approvals for user
  POST /api/approvals/{id}/approve     — approve an action
  POST /api/approvals/{id}/deny        — deny an action
  GET  /api/approvals/{id}             — get approval details
  POST /api/agent-runs/{run_id}/cancel — cancel a running agent loop
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["approvals"])


def _get_auth():
    from server import get_current_user
    return get_current_user


# ─────────────────────────────────────────────────────────────────────────────
# Approvals
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/approvals")
async def list_approvals(
    status: Optional[str] = "pending",
    thread_id: Optional[str] = None,
    user: dict = Depends(_get_auth()),
):
    """List approvals for the current user."""
    from db_pg import get_db
    db = await get_db()
    user_id = user.get("id") or user.get("sub", "anon")

    params: dict = {"user_id": user_id}
    where = "user_id = :user_id"
    if status:
        where += " AND decision = :decision"
        params["decision"] = status
    if thread_id:
        where += " AND thread_id = :thread_id"
        params["thread_id"] = thread_id

    try:
        rows = await db.fetch_all(
            f"SELECT * FROM approvals WHERE {where} ORDER BY created_at DESC LIMIT 100",
            params,
        )
        return {"approvals": [dict(r) for r in rows]}
    except Exception as exc:
        logger.warning("[approvals] list failed: %s", exc)
        return {"approvals": [], "error": str(exc)}


@router.get("/approvals/{approval_id}")
async def get_approval(approval_id: str, user: dict = Depends(_get_auth())):
    from db_pg import get_db
    db = await get_db()
    user_id = user.get("id") or user.get("sub", "anon")

    try:
        row = await db.fetch_one(
            "SELECT * FROM approvals WHERE id = :id AND user_id = :user_id",
            {"id": approval_id, "user_id": user_id},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    if not row:
        raise HTTPException(status_code=404, detail="Approval not found")
    return {"approval": dict(row)}


@router.post("/approvals/{approval_id}/approve")
async def approve_action(approval_id: str, user: dict = Depends(_get_auth())):
    """Approve a pending action."""
    return await _decide(approval_id, "approved", user)


@router.post("/approvals/{approval_id}/deny")
async def deny_action(approval_id: str, user: dict = Depends(_get_auth())):
    """Deny a pending action."""
    return await _decide(approval_id, "denied", user)


async def _decide(approval_id: str, decision: str, user: dict) -> dict:
    from db_pg import get_db
    db = await get_db()
    user_id = user.get("id") or user.get("sub", "anon")
    now = datetime.now(timezone.utc).isoformat()

    try:
        await db.execute(
            """UPDATE approvals SET decision = :decision, decided_at = :decided_at
               WHERE id = :id AND user_id = :user_id""",
            {"decision": decision, "decided_at": now, "id": approval_id, "user_id": user_id},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    # Emit audit log entry
    try:
        import json
        await db.execute(
            """INSERT INTO audit_log (id, user_id, action, details, created_at)
               VALUES (:id, :user_id, :action, :details::jsonb, :created_at)""",
            {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "action": f"approval_{decision}",
                "details": json.dumps({"approval_id": approval_id}),
                "created_at": now,
            },
        )
    except Exception:
        pass

    return {"approval_id": approval_id, "decision": decision, "decided_at": now}


# ─────────────────────────────────────────────────────────────────────────────
# Agent run cancellation  (Spec O – cancellation support)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/agent-runs/{run_id}/cancel")
async def cancel_agent_run(run_id: str, user: dict = Depends(_get_auth())):
    """Cancel a running agent loop by run_id."""
    from services.agent_loop import agent_loop
    success = await agent_loop.cancel(run_id)
    return {"run_id": run_id, "cancelled": success}


@router.post("/agent-runs/{run_id}/pause")
async def pause_agent_run(run_id: str, user: dict = Depends(_get_auth())):
    """Pause a running agent loop."""
    from services.agent_loop import agent_loop
    success = await agent_loop.pause(run_id)
    return {"run_id": run_id, "paused": success}


# ─────────────────────────────────────────────────────────────────────────────
# Automation runs history  (Spec I)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/automations/{automation_id}/runs")
async def list_automation_runs(
    automation_id: str,
    limit: int = 50,
    user: dict = Depends(_get_auth()),
):
    """List run history for an automation."""
    from db_pg import get_db
    db = await get_db()

    try:
        rows = await db.fetch_all(
            """SELECT * FROM automation_runs WHERE automation_id = :automation_id
               ORDER BY created_at DESC LIMIT :limit""",
            {"automation_id": automation_id, "limit": limit},
        )
        return {"runs": [dict(r) for r in rows]}
    except Exception as exc:
        return {"runs": [], "error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# Capability audit  (Spec B / P)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/capability-audit")
async def capability_audit(user: dict = Depends(_get_auth())):
    """Run capability inspection and return the A-Q audit table."""
    from db_pg import get_db
    from services.capability_inspector import capability_inspector

    db = await get_db()
    user_id = user.get("id") or user.get("sub", "anon")
    rows = await capability_inspector.run_and_log(db=db, user_id=user_id)
    return {"audit": rows}


# ─────────────────────────────────────────────────────────────────────────────
# Agent loop launch  (Spec E)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/agent-loop/run")
async def launch_agent_loop(
    request: Request,
    user: dict = Depends(_get_auth()),
):
    """Launch the agent loop with a specified mode and goal."""
    from services.agent_loop import agent_loop, ExecutionMode

    body = await request.json()
    goal      = body.get("goal", "")
    mode      = body.get("mode", ExecutionMode.BUILD.value)
    thread_id = body.get("thread_id")
    dry_run   = bool(body.get("dry_run", False))
    user_id   = user.get("id") or user.get("sub", "anon")

    if not goal:
        raise HTTPException(status_code=400, detail="goal is required")

    result = await agent_loop.run(
        mode=mode,
        goal=goal,
        thread_id=thread_id,
        user_id=user_id,
        dry_run=dry_run,
    )
    return result
