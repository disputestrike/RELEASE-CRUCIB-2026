"""Per-project persistent K/V memory — WS-G."""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Body, Depends, HTTPException

router = APIRouter(prefix="/api/projects", tags=["project-memory"])


def _get_auth():
    from ..server import get_current_user

    return get_current_user


async def _require_project_access(project_id: str, user: dict) -> None:
    """Best-effort ownership check; silent no-op if db not ready."""
    try:
        from .. import server

        if server.db is None:
            return
        proj = await server.db.projects.find_one({"id": project_id})
        if proj is None:
            raise HTTPException(status_code=404, detail="project not found")
        owner = proj.get("user_id") or proj.get("owner_id")
        if owner and owner != user.get("id"):
            raise HTTPException(status_code=403, detail="forbidden")
    except HTTPException:
        raise
    except Exception:
        # Don't block on ownership errors; better to serve than to crash.
        return


@router.get("/{project_id}/memory")
async def list_memory(project_id: str, user: dict = Depends(_get_auth())):
    from ..services.project_memory import get_project_memory

    await _require_project_access(project_id, user)
    mem = await get_project_memory()
    return {"project_id": project_id, "values": await mem.list(project_id)}


@router.get("/{project_id}/memory/{key}")
async def get_memory(project_id: str, key: str, user: dict = Depends(_get_auth())):
    from ..services.project_memory import get_project_memory

    await _require_project_access(project_id, user)
    mem = await get_project_memory()
    val = await mem.get(project_id, key)
    if val is None:
        raise HTTPException(status_code=404, detail=f"key '{key}' not set")
    return {"project_id": project_id, "key": key, "value": val}


@router.put("/{project_id}/memory/{key}")
async def set_memory(
    project_id: str,
    key: str,
    body: dict = Body(...),
    user: dict = Depends(_get_auth()),
):
    """PUT /api/projects/{project_id}/memory/{key} with body: { "value": <any-json> }."""
    if "value" not in body:
        raise HTTPException(status_code=400, detail="body must include 'value'")
    from ..services.project_memory import get_project_memory

    await _require_project_access(project_id, user)
    mem = await get_project_memory()
    await mem.set(project_id, key, body["value"])
    return {"status": "ok", "project_id": project_id, "key": key}


@router.delete("/{project_id}/memory/{key}")
async def delete_memory(project_id: str, key: str, user: dict = Depends(_get_auth())):
    from ..services.project_memory import get_project_memory

    await _require_project_access(project_id, user)
    mem = await get_project_memory()
    removed = await mem.delete(project_id, key)
    return {"status": "deleted" if removed else "not_found", "project_id": project_id, "key": key}
