from __future__ import annotations

import io
import zipfile
from datetime import datetime, timezone
from typing import Dict
from uuid import uuid4

from fastapi import HTTPException


async def build_project_deploy_zip_buffer_service(*, project_id: str, user_id: str, db, deploy_readme: str):
    project = await db.projects.find_one({"id": project_id, "user_id": user_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    deploy_files = project.get("deploy_files") or {}
    if not deploy_files:
        raise HTTPException(
            status_code=404,
            detail="No deploy snapshot for this project. Open in Workspace and use Deploy there, or re-run the build.",
        )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("README-DEPLOY.md", deploy_readme)
        for name, content in deploy_files.items():
            safe_name = (name or "").lstrip("/")
            if safe_name:
                zf.writestr(safe_name, content if isinstance(content, str) else str(content))
    buf.seek(0)
    return buf


async def get_project_deploy_files_json_service(*, project_id: str, user_id: str, db):
    project = await db.projects.find_one({"id": project_id, "user_id": user_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "files": project.get("deploy_files") or {},
        "status": project.get("status", "unknown"),
        "quality_score": project.get("quality_score"),
    }


async def get_project_logs_service(*, project_id: str, user_id: str, db):
    project = await db.projects.find_one({"id": project_id, "user_id": user_id}, {"id": 1})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    cursor = db.project_logs.find({"project_id": project_id}, {"_id": 0}).sort("created_at", 1)
    logs = await cursor.to_list(500)
    return {"logs": logs}


async def get_build_history_service(*, project_id: str, user_id: str, db):
    project = await db.projects.find_one({"id": project_id, "user_id": user_id}, {"build_history": 1})
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"build_history": project.get("build_history") or []}


async def create_export_service(*, project_id: str, export_format: str, user_id: str, db):
    project = await db.projects.find_one({"id": project_id, "user_id": user_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    export_id = str(uuid4())
    export_doc = {
        "id": export_id,
        "project_id": project_id,
        "user_id": user_id,
        "format": export_format or "pdf",
        "status": "completed",
        "download_url": f"/api/exports/{export_id}/download",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.exports.insert_one(export_doc)
    return {"export": {k: v for k, v in export_doc.items() if k != "_id"}}


async def get_exports_service(*, user_id: str, db, max_exports_list: int):
    cursor = db.exports.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1)
    exports = await cursor.to_list(max_exports_list)
    return {"exports": exports}
