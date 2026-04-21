"""
backend/routes/artifacts.py
──────────────────────────────
HTTP surface for the artifact system.

Spec: L – Artifact System
Branch: engineering/master-list-closeout

Endpoints:
  GET  /api/artifacts                  — list artifacts for current user
  POST /api/artifacts                  — create artifact from content
  GET  /api/artifacts/{id}             — get artifact metadata
  GET  /api/artifacts/{id}/download    — download artifact content
  GET  /api/artifacts/{id}/versions    — list versions
  POST /api/artifacts/{id}/screenshot  — attach screenshot to thread
  GET  /api/threads/{thread_id}/artifacts — list artifacts for a thread
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["artifacts"])


def _get_auth():
    from server import get_current_user
    return get_current_user


# ─────────────────────────────────────────────────────────────────────────────
# List / create
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/artifacts")
async def list_artifacts(
    thread_id: Optional[str] = None,
    artifact_type: Optional[str] = None,
    limit: int = 50,
    user: dict = Depends(_get_auth()),
):
    """List artifacts for the current user, optionally filtered by thread or type."""
    from db_pg import get_db
    db = await get_db()
    user_id = user.get("id") or user.get("sub", "anon")

    params: dict = {"user_id": user_id, "limit": limit}
    where_clauses = ["user_id = :user_id"]
    if thread_id:
        where_clauses.append("thread_id = :thread_id")
        params["thread_id"] = thread_id
    if artifact_type:
        where_clauses.append("artifact_type = :artifact_type")
        params["artifact_type"] = artifact_type

    where = " AND ".join(where_clauses)
    try:
        rows = await db.fetch_all(
            f"SELECT * FROM artifacts WHERE {where} ORDER BY created_at DESC LIMIT :limit",
            params,
        )
        return {"artifacts": [dict(r) for r in rows]}
    except Exception as exc:
        logger.warning("[artifacts] list failed: %s", exc)
        return {"artifacts": [], "error": str(exc)}


@router.post("/artifacts")
async def create_artifact(
    request: Request,
    user: dict = Depends(_get_auth()),
):
    """Create an artifact from provided content."""
    from db_pg import get_db
    from services.artifact_builder import artifact_builder

    db = await get_db()
    user_id = user.get("id") or user.get("sub", "anon")

    body = await request.json()
    artifact_type = body.get("artifact_type", "product_spec")
    title         = body.get("title", "Untitled Artifact")
    content       = body.get("content", "")
    thread_id     = body.get("thread_id")
    run_id        = body.get("run_id")
    render_pdf    = body.get("render_pdf", False)
    render_slides = body.get("render_slides", False)

    if not content:
        raise HTTPException(status_code=400, detail="content is required")

    record = await artifact_builder.build(
        artifact_type=artifact_type,
        title=title,
        content=content,
        user_id=user_id,
        thread_id=thread_id,
        run_id=run_id,
        metadata=body.get("metadata", {}),
        db=db,
        render_pdf=render_pdf,
        render_slides=render_slides,
    )
    return {"artifact": {
        "id":             record.id,
        "artifact_type":  record.artifact_type,
        "title":          record.title,
        "download_url":   record.download_url,
        "mime_type":      record.mime_type,
        "size_bytes":     record.size_bytes,
        "version":        record.version,
        "created_at":     record.created_at,
    }}


# ─────────────────────────────────────────────────────────────────────────────
# Single artifact
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/artifacts/{artifact_id}")
async def get_artifact(artifact_id: str, user: dict = Depends(_get_auth())):
    from db_pg import get_db
    db = await get_db()
    user_id = user.get("id") or user.get("sub", "anon")

    try:
        row = await db.fetch_one(
            "SELECT * FROM artifacts WHERE id = :id AND user_id = :user_id",
            {"id": artifact_id, "user_id": user_id},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    if not row:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return {"artifact": dict(row)}


@router.get("/artifacts/{artifact_id}/download")
async def download_artifact(artifact_id: str, user: dict = Depends(_get_auth())):
    from db_pg import get_db
    db = await get_db()
    user_id = user.get("id") or user.get("sub", "anon")

    try:
        row = await db.fetch_one(
            "SELECT * FROM artifacts WHERE id = :id AND user_id = :user_id",
            {"id": artifact_id, "user_id": user_id},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    if not row:
        raise HTTPException(status_code=404, detail="Artifact not found")

    artifact = dict(row)
    storage_path = artifact.get("storage_path")
    if storage_path and os.path.exists(storage_path):
        return FileResponse(
            path=storage_path,
            media_type=artifact.get("mime_type", "application/octet-stream"),
            filename=f"{artifact.get('title', artifact_id)}.{_ext(artifact.get('mime_type','txt'))}",
        )
    # Fallback: return metadata as JSON
    return JSONResponse({"artifact": artifact, "note": "file not on disk"})


def _ext(mime_type: str) -> str:
    return {
        "application/pdf": "pdf",
        "application/json": "json",
        "text/plain": "txt",
        "text/markdown": "md",
        "image/png": "png",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    }.get(mime_type, "bin")


@router.get("/artifacts/{artifact_id}/versions")
async def list_artifact_versions(artifact_id: str, user: dict = Depends(_get_auth())):
    from db_pg import get_db
    db = await get_db()
    user_id = user.get("id") or user.get("sub", "anon")

    # Verify ownership
    try:
        row = await db.fetch_one(
            "SELECT id FROM artifacts WHERE id = :id AND user_id = :user_id",
            {"id": artifact_id, "user_id": user_id},
        )
    except Exception:
        row = None
    if not row:
        raise HTTPException(status_code=404, detail="Artifact not found")

    try:
        rows = await db.fetch_all(
            "SELECT * FROM artifact_versions WHERE artifact_id = :artifact_id ORDER BY version DESC",
            {"artifact_id": artifact_id},
        )
        return {"versions": [dict(r) for r in rows]}
    except Exception as exc:
        return {"versions": [], "error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# Thread-scoped list
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/threads/{thread_id}/artifacts")
async def list_thread_artifacts(thread_id: str, user: dict = Depends(_get_auth())):
    from db_pg import get_db
    db = await get_db()
    user_id = user.get("id") or user.get("sub", "anon")

    try:
        rows = await db.fetch_all(
            "SELECT * FROM artifacts WHERE thread_id = :thread_id AND user_id = :user_id ORDER BY created_at DESC",
            {"thread_id": thread_id, "user_id": user_id},
        )
        return {"artifacts": [dict(r) for r in rows]}
    except Exception as exc:
        return {"artifacts": [], "error": str(exc)}


# ─────────────────────────────────────────────────────────────────────────────
# Thread checkpoint endpoints  (Spec A)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/threads/{thread_id}/checkpoint")
async def save_thread_checkpoint(
    thread_id: str,
    request: Request,
    user: dict = Depends(_get_auth()),
):
    """Save a checkpoint for the given thread."""
    from db_pg import get_db
    from services.agent_loop import agent_loop

    db = await get_db()
    user_id = user.get("id") or user.get("sub", "anon")
    body = await request.json()

    checkpoint_id = await agent_loop.save_checkpoint(
        thread_id=thread_id,
        run_id=body.get("run_id", ""),
        user_id=user_id,
        phase=body.get("phase", "unknown"),
        data=body.get("data", {}),
        db=db,
    )
    return {"checkpoint_id": checkpoint_id, "thread_id": thread_id}


@router.get("/threads/{thread_id}/checkpoint/latest")
async def get_latest_thread_checkpoint(
    thread_id: str,
    user: dict = Depends(_get_auth()),
):
    """Return latest checkpoint for a thread (non-mutating)."""
    from db_pg import get_db
    from services.agent_loop import agent_loop

    db = await get_db()
    cp = await agent_loop.load_checkpoint(thread_id=thread_id, db=db)
    if not cp:
        return {"thread_id": thread_id, "checkpoint": None}

    data = cp.get("checkpoint_data") or {}
    return {
        "thread_id": thread_id,
        "checkpoint": cp,
        "resume_state": {
            "run_id": data.get("run_id"),
            "phase": data.get("phase") or cp.get("phase"),
            "status": cp.get("status"),
            "created_at": cp.get("created_at"),
            "checkpoint_id": cp.get("id"),
        },
    }


@router.post("/threads/{thread_id}/resume")
async def resume_thread(
    thread_id: str,
    request: Request,
    user: dict = Depends(_get_auth()),
):
    """Resume agent loop from latest checkpoint for this thread."""
    from db_pg import get_db
    from services.agent_loop import agent_loop

    db = await get_db()
    user_id = user.get("id") or user.get("sub", "anon")

    cp = await agent_loop.load_checkpoint(thread_id=thread_id, db=db)
    if not cp:
        raise HTTPException(status_code=404, detail="No checkpoint found for this thread")

    cp_data = cp.get("checkpoint_data") or {}
    run_id = cp_data.get("run_id", thread_id)
    result = await agent_loop.resume(run_id)
    return {
        "thread_id": thread_id,
        "checkpoint": cp,
        "resume_state": {
            "run_id": run_id,
            "phase": cp_data.get("phase") or cp.get("phase"),
            "status": result.get("status", "resumed"),
            "checkpoint_id": cp.get("id"),
        },
        "result": result,
    }
