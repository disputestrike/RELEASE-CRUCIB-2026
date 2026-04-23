from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from fastapi import HTTPException
from fastapi.responses import FileResponse


def list_job_workspace_files_service(*, job_id: str, user: dict, offset: int, limit: int, resolve_project_for_job, project_workspace_path, list_all_rel_paths, paginated_payload):
    project_id = resolve_project_for_job(job_id, user)
    if hasattr(project_id, "__await__"):
        raise RuntimeError("resolve_project_for_job must already be awaited by caller")
    root = project_workspace_path(project_id).resolve()
    if not root.exists():
        return paginated_payload([], offset, limit)
    paths = list_all_rel_paths(root)
    return paginated_payload(paths, offset, limit)


def get_job_workspace_file_content_service(*, job_id: str, user: dict, path: str, resolve_project_for_job, project_workspace_path, workspace_file_disk_path):
    project_id = resolve_project_for_job(job_id, user)
    if hasattr(project_id, "__await__"):
        raise RuntimeError("resolve_project_for_job must already be awaited by caller")
    root = project_workspace_path(project_id).resolve()
    full = workspace_file_disk_path(root, path)
    try:
        content = full.read_text(encoding="utf-8", errors="replace")
    except Exception:
        raise HTTPException(status_code=400, detail="File not readable as text")
    rel = str(full.relative_to(root)).replace("\\", "/")
    return {"path": rel, "content": content}


def get_job_workspace_file_raw_service(*, job_id: str, user: dict, path: str, resolve_project_for_job, project_workspace_path, workspace_file_disk_path, guess_media_type):
    project_id = resolve_project_for_job(job_id, user)
    if hasattr(project_id, "__await__"):
        raise RuntimeError("resolve_project_for_job must already be awaited by caller")
    root = project_workspace_path(project_id).resolve()
    full = workspace_file_disk_path(root, path)
    if not full.exists() or not full.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    guessed = guess_media_type(full.name)
    media = guessed or "application/octet-stream"
    return FileResponse(path=str(full), media_type=media, filename=full.name)


def visual_edit_job_workspace_file_service(*, job_id: str, user: dict, body: Any, resolve_project_for_job, project_workspace_path):
    project_id = resolve_project_for_job(job_id, user)
    if hasattr(project_id, "__await__"):
        raise RuntimeError("resolve_project_for_job must already be awaited by caller")
    root = project_workspace_path(project_id).resolve()
    rel_path = (body.file_path or "").strip().replace("\\", "/").lstrip("/")
    if ".." in rel_path or not rel_path:
        raise HTTPException(status_code=400, detail="Invalid path")
    full = (root / rel_path).resolve()
    try:
        full.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=400, detail="Path outside workspace")
    if not full.exists() or not full.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    if not body.find_text:
        raise HTTPException(status_code=400, detail="find_text is required")
    before = full.read_text(encoding="utf-8", errors="replace")
    if body.find_text not in before:
        raise HTTPException(status_code=400, detail="find_text not found in target file")
    after = before.replace(body.find_text, body.replace_text, 1)
    snapshot_dir = root / ".crucibai" / "snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot_name = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{full.name}.bak"
    snapshot_path = snapshot_dir / snapshot_name
    snapshot_path.write_text(before, encoding="utf-8")
    full.write_text(after, encoding="utf-8")
    return {
        "status": "patched",
        "job_id": job_id,
        "project_id": project_id,
        "file_path": rel_path,
        "snapshot_path": str(snapshot_path.relative_to(root)).replace("\\", "/"),
        "changed": True,
        "find_text": body.find_text,
        "replace_text": body.replace_text,
    }
