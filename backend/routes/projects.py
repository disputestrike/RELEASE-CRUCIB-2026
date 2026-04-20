"""
projects.py — Core project CRUD + build orchestration via RuntimeEngine.

Restored from d406214^ with agent_dag / legacy dependencies removed.
Build execution is delegated entirely to runtime_engine.execute_with_control().
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import os
import shutil
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from deps import (
    JWT_ALGORITHM,
    JWT_SECRET,
    get_audit_logger,
    get_current_user,
    get_db,
    get_optional_user,
    require_permission,
)
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, StreamingResponse
from project_state import WORKSPACE_ROOT, load_state
from pydantic import BaseModel, Field, model_validator

try:
    from utils.rbac import Permission, has_permission
except ImportError:
    has_permission = lambda u, p: True  # noqa: E731

    class Permission:  # type: ignore[no-redef]
        CREATE_PROJECT = "create_project"
        VIEW_PROJECT = "view_project"
        DELETE_PROJECT = "delete_project"
        EDIT_PROJECT = "edit_project"


try:
    from pricing_plans import CREDITS_PER_TOKEN
except ImportError:
    CREDITS_PER_TOKEN = 1000

try:
    from content_policy import screen_user_content
except ImportError:
    screen_user_content = None  # type: ignore[assignment]

try:
    from agents.legal_compliance import check_request as legal_check_request
except ImportError:
    legal_check_request = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

projects_router = APIRouter(prefix="/api", tags=["projects"])

FREE_TIER_MAX_PROJECTS = 3
MAX_PROJECT_DESCRIPTION_LENGTH = 5000
MAX_PROJECT_REQUIREMENTS_JSON_LENGTH = 50_000
MAX_PROMPT_LENGTH = 20_000

# In-memory SSE event store (per-process; persisted events live in DB)
_build_events: Dict[str, List[Dict[str, Any]]] = {}
_BUILD_EVENTS_MAX = 500


async def _call_llm_with_fallback(*_args, **_kwargs):
    # Compatibility shim for legacy tests that monkeypatch this symbol.
    return ("plan-ready", 1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _project_workspace_path(project_id: str) -> Path:
    base = Path(WORKSPACE_ROOT) / "projects" / project_id
    return base


def _safe_import_path(path: str) -> str:
    p = (path or "").strip().replace("\\", "/").lstrip("/")
    if ".." in p or p.startswith("/"):
        return ""
    return p[:500]


def _user_credits(user: dict) -> int:
    return int(user.get("credit_balance", 0) or 0)


def _tokens_to_credits(tokens: int) -> int:
    return max(1, tokens // CREDITS_PER_TOKEN)


async def _ensure_credit_balance(user_id: str) -> None:
    """No-op placeholder; real credit enforcement lives in tokens.py."""
    pass


async def _run_build_background(project_id: str, user_id: str, prompt: str) -> None:
    """Background task: delegates to RuntimeEngine which is the ONLY executor."""
    try:
        from services.runtime.runtime_engine import runtime_engine

        db = get_db()
        await db.projects.update_one(
            {"id": project_id}, {"$set": {"status": "running"}}
        )
        result = await runtime_engine.execute_with_control(
            task_id=project_id,
            user_id=user_id,
            request=prompt,
            conversation_id=f"project-{project_id}",
        )
        status = "completed" if result.get("success") else "failed"
        await db.projects.update_one(
            {"id": project_id},
            {
                "$set": {
                    "status": status,
                    "completed_at": datetime.now(timezone.utc).isoformat(),
                    "runtime_result": result,
                }
            },
        )
    except Exception as exc:
        logger.exception("Build failed for project %s: %s", project_id, exc)
        try:
            db = get_db()
            await db.projects.update_one(
                {"id": project_id},
                {
                    "$set": {
                        "status": "failed",
                        "error": str(exc),
                        "completed_at": datetime.now(timezone.utc).isoformat(),
                    }
                },
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    description: str = Field("", max_length=MAX_PROJECT_DESCRIPTION_LENGTH)
    project_type: str = Field(..., max_length=100)
    requirements: Dict[str, Any] = Field(default_factory=dict)
    estimated_tokens: Optional[int] = None
    quick_build: Optional[bool] = False

    @model_validator(mode="after")
    def check_requirements_size(self):
        try:
            if len(json.dumps(self.requirements or {})) > MAX_PROJECT_REQUIREMENTS_JSON_LENGTH:
                raise ValueError("requirements too large")
        except TypeError:
            pass
        return self


class ProjectImportBody(BaseModel):
    name: Optional[str] = None
    source: str
    files: Optional[List[Dict[str, Any]]] = None
    zip_base64: Optional[str] = None
    git_url: Optional[str] = None


class BuildPlanRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=MAX_PROMPT_LENGTH)
    swarm: Optional[bool] = False
    build_kind: Optional[str] = None


class ProjectPublishSettingsBody(BaseModel):
    custom_domain: Optional[str] = None
    railway_project_url: Optional[str] = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@projects_router.post("/projects")
async def create_project(
    data: ProjectCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    audit_logger = get_audit_logger()

    if Permission is not None and not has_permission(user, Permission.CREATE_PROJECT):
        raise HTTPException(status_code=403, detail="Insufficient permission to create projects")

    plan = user.get("plan", "free")
    if plan == "free":
        count = await db.projects.count_documents({"user_id": user["id"]})
        if count >= FREE_TIER_MAX_PROJECTS:
            raise HTTPException(
                status_code=403,
                detail="You've saved 3 projects. Upgrade to Builder to save unlimited projects.",
                headers={"X-Upgrade-Required": "builder"},
            )

    project_type_lower = (data.project_type or "").strip().lower()
    default_tokens = 80_000 if project_type_lower == "landing" else 675_000
    estimated_tokens = data.estimated_tokens or default_tokens
    estimated_credits = _tokens_to_credits(estimated_tokens)

    await _ensure_credit_balance(user["id"])
    cred = _user_credits(user)
    if cred < estimated_credits:
        raise HTTPException(
            status_code=402,
            detail=f"Insufficient credits. Need {estimated_credits}, have {cred}.",
        )

    # Content policy screen
    prompt = (data.requirements or {}).get("prompt") or data.description or ""
    if isinstance(prompt, dict):
        prompt = prompt.get("prompt") or str(prompt)

    if legal_check_request and prompt:
        compliance = legal_check_request(prompt)
        if not compliance.get("allowed"):
            await db.blocked_requests.insert_one(
                {
                    "user_id": user["id"],
                    "prompt": prompt[:2000],
                    "reason": compliance.get("reason"),
                    "category": compliance.get("category"),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "status": "blocked",
                }
            )
            raise HTTPException(
                status_code=400,
                detail=compliance.get("reason") or "Request violates Acceptable Use Policy.",
            )

    project_id = str(uuid.uuid4())
    project = {
        "id": project_id,
        "user_id": user["id"],
        "name": data.name,
        "description": data.description,
        "project_type": data.project_type,
        "requirements": data.requirements,
        "status": "queued",
        "tokens_allocated": estimated_tokens,
        "tokens_used": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "live_url": None,
        "quick_build": data.quick_build or False,
    }
    await db.projects.insert_one(project)

    if audit_logger:
        await audit_logger.log(
            user["id"],
            "project_created",
            resource_type="project",
            resource_id=project_id,
            new_value={"name": data.name},
            ip_address=getattr(request.client, "host", None),
        )

    await db.users.update_one({"id": user["id"]}, {"$inc": {"credit_balance": -estimated_credits}})

    background_tasks.add_task(_run_build_background, project_id, user["id"], prompt)

    return {"project": {k: v for k, v in project.items() if k != "_id"}}


@projects_router.get("/projects")
async def get_projects(
    limit: int = Query(100, ge=1, le=500),
    user: dict = Depends(get_current_user),
):
    db = get_db()
    cursor = db.projects.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1)
    projects = await cursor.to_list(limit)
    return {"projects": projects}


@projects_router.post("/projects/import")
async def import_project(
    data: ProjectImportBody,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    project_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    name = (data.name or "Imported project").strip() or "Imported project"
    project = {
        "id": project_id,
        "user_id": user["id"],
        "name": name,
        "description": "Imported from paste, ZIP, or Git.",
        "project_type": "fullstack",
        "requirements": {"prompt": "", "imported": True},
        "status": "imported",
        "tokens_allocated": 0,
        "tokens_used": 0,
        "created_at": now,
        "completed_at": now,
        "live_url": None,
    }
    await db.projects.insert_one(project)
    root = _project_workspace_path(project_id).resolve()
    root.mkdir(parents=True, exist_ok=True)
    written = 0

    if data.source == "paste" and data.files:
        for item in data.files[:200]:
            path = _safe_import_path(item.get("path") or "")
            if not path:
                continue
            content = item.get("code") or item.get("content") or ""
            if len(content) > 2 * 1024 * 1024:
                continue
            full = (root / path).resolve()
            try:
                full.relative_to(root)
            except ValueError:
                continue
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content[:2 * 1024 * 1024], encoding="utf-8", errors="replace")
            written += 1
    elif data.source == "zip" and data.zip_base64:
        try:
            raw = base64.b64decode(data.zip_base64, validate=True)
            if len(raw) > 10 * 1024 * 1024:
                raise HTTPException(status_code=413, detail="ZIP too large (max 10 MB)")
            with zipfile.ZipFile(io.BytesIO(raw), "r") as zf:
                for info in zf.infolist()[:500]:
                    if info.is_dir():
                        continue
                    path = _safe_import_path(info.filename)
                    if not path or "node_modules" in path or "__pycache__" in path:
                        continue
                    full = (root / path).resolve()
                    try:
                        full.relative_to(root)
                    except ValueError:
                        continue
                    full.parent.mkdir(parents=True, exist_ok=True)
                    full.write_bytes(zf.read(info.filename))
                    written += 1
        except zipfile.BadZipFile:
            raise HTTPException(status_code=400, detail="Invalid ZIP file")

    return {"project_id": project_id, "name": name, "files_written": written}


@projects_router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"project": project}


@projects_router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.project_logs.delete_many({"project_id": project_id})
    await db.agent_status.delete_many({"project_id": project_id})
    await db.shares.delete_many({"project_id": project_id})
    await db.projects.delete_one({"id": project_id, "user_id": user["id"]})
    if project_id in _build_events:
        del _build_events[project_id]
    try:
        workspace_path = _project_workspace_path(project_id)
        if workspace_path.exists():
            shutil.rmtree(workspace_path, ignore_errors=True)
    except Exception as exc:
        logger.warning("Could not remove workspace dir %s: %s", project_id, exc)
    return Response(status_code=204)


@projects_router.get("/projects/{project_id}/state")
async def get_project_state(
    project_id: str,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    state = load_state(project_id)
    return {"state": state, "project": project}


@projects_router.get("/projects/{project_id}/events")
async def get_project_events(
    project_id: str,
    since: int = Query(0, ge=0),
    user: dict = Depends(get_current_user),
):
    db = get_db()
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    events = _build_events.get(project_id, [])
    return {"events": events[since:], "total": len(events)}


@projects_router.get("/projects/{project_id}/logs")
async def get_project_logs(
    project_id: str,
    limit: int = Query(200, ge=1, le=1000),
    user: dict = Depends(get_current_user),
):
    db = get_db()
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    cursor = db.project_logs.find({"project_id": project_id}, {"_id": 0}).sort("ts", -1)
    logs = await cursor.to_list(limit)
    return {"logs": list(reversed(logs))}


@projects_router.post("/projects/{project_id}/duplicate")
async def duplicate_project(
    project_id: str,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    new_id = str(uuid.uuid4())
    new_project = {
        **{k: v for k, v in project.items() if k != "_id"},
        "id": new_id,
        "name": f"{project.get('name', 'Project')} (copy)",
        "status": "imported",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "live_url": None,
    }
    await db.projects.insert_one(new_project)
    # Copy workspace files if they exist
    src = _project_workspace_path(project_id)
    dst = _project_workspace_path(new_id)
    if src.exists():
        try:
            shutil.copytree(src, dst)
        except Exception as exc:
            logger.warning("Could not copy workspace for duplicate: %s", exc)
    return {"project": {k: v for k, v in new_project.items() if k != "_id"}}


@projects_router.get("/build/phases")
async def get_build_phases(user: dict = Depends(get_optional_user)):
    """Return generic build phase info for the UI."""
    return {
        "phases": [
            {"id": "plan", "name": "plan", "label": "Plan", "order": 1},
            {"id": "scaffold", "name": "scaffold", "label": "Scaffold", "order": 2},
            {"id": "build", "name": "build", "label": "Build", "order": 3},
            {"id": "test", "name": "test", "label": "Test", "order": 4},
            {"id": "deploy", "name": "deploy", "label": "Deploy", "order": 5},
        ]
    }


@projects_router.post("/build/plan")
async def build_plan(
    data: BuildPlanRequest,
    user: dict = Depends(get_current_user),
):
    """Return a build plan (skeleton) for a prompt."""
    return {
        "plan": {
            "prompt": data.prompt,
            "project_type": "fullstack",
            "phases": ["plan", "scaffold", "build", "test"],
            "estimated_tokens": 675_000,
        }
    }


@projects_router.get("/settings/capabilities")
async def get_capabilities(user: dict = Depends(get_optional_user)):
    """Return platform capability flags used by the frontend."""
    return {
        "llm": True,
        "agents": True,
        "deploy": True,
        "preview": True,
        "git": True,
        "terminal": True,
    }
