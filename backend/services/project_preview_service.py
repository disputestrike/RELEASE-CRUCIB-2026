from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from fastapi import HTTPException
from fastapi.responses import FileResponse, Response


async def get_preview_token_service(*, project_id: str, user_id: str, user_can_access, create_preview_token, api_base_url: str) -> Dict[str, str]:
    if not await user_can_access(user_id, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    token = create_preview_token(project_id, user_id)
    base = api_base_url.rstrip("/") or "http://localhost:8000"
    return {"token": token, "url": f"{base}/api/projects/{project_id}/preview?preview_token={token}"}


async def serve_preview_service(
    *,
    project_id: str,
    path: str,
    preview_token: Optional[str],
    verify_preview_token,
    user_can_access,
    project_workspace_path,
) -> FileResponse | Response:
    if not preview_token:
        raise HTTPException(status_code=401, detail="preview_token required (get from /projects/{id}/preview-token)")
    try:
        pid, user_id = verify_preview_token(preview_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired preview token")
    if pid != project_id:
        raise HTTPException(status_code=403, detail="Token project mismatch")
    if not await user_can_access(user_id, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    root = project_workspace_path(project_id).resolve()
    if not root.exists():
        raise HTTPException(status_code=404, detail="No workspace yet")
    rel = (path or "").strip().lstrip("/").replace("\\", "/")
    if ".." in rel or rel.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid path")
    full = (root / rel).resolve()
    try:
        full.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=400, detail="Path outside workspace")
    if full.is_dir():
        full = full / "index.html"
    if not full.exists():
        if not rel:
            return Response(
                content='<!DOCTYPE html><html><head><meta charset="utf-8"><title>Building...</title></head><body style="display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;font-family:system-ui;background:#1A1A1A;color:#999999;">Building your app... Agents are writing files.</body></html>',
                media_type="text/html",
            )
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(full)


def _run_npm_audit(root: Path) -> Optional[Dict[str, Any]]:
    pkg = root / "package.json"
    if not pkg.exists():
        return None
    try:
        r = subprocess.run(
            ["npm", "audit", "--json"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "CI": "1"},
        )
        if r.stdout:
            data = json.loads(r.stdout)
            meta = data.get("metadata", {}) or {}
            counts = meta.get("vulnerabilities", {}) or {}
            return {
                "critical": counts.get("critical", 0) or 0,
                "high": counts.get("high", 0) or 0,
                "moderate": counts.get("moderate", 0) or 0,
                "low": counts.get("low", 0) or 0,
                "info": counts.get("info", 0) or 0,
                "ok": (counts.get("critical", 0) or 0) == 0 and (counts.get("high", 0) or 0) == 0,
            }
        return {"ok": True, "critical": 0, "high": 0}
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
        return {"error": str(e)[:200]}
    except Exception as e:
        return {"error": str(e)[:200]}


def _run_pip_audit(root: Path) -> Optional[Dict[str, Any]]:
    req = root / "requirements.txt"
    if not req.exists():
        return None
    try:
        r = subprocess.run(
            [sys.executable, "-m", "pip_audit", "-r", str(req), "--format", "json", "--require-hashes", "false"],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=90,
        )
        if r.stdout:
            data = json.loads(r.stdout)
            deps = data.get("dependencies", {}) or {}
            total = sum(len((d.get("vulns") or [])) for d in deps.values() if isinstance(d, dict))
            return {"critical": total, "high": 0, "ok": total == 0}
        return {"ok": True, "critical": 0, "high": 0}
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
        return {"error": str(e)[:200]}
    except Exception as e:
        return {"error": str(e)[:200]}


async def get_project_dependency_audit_service(*, project_id: str, user_id: str, db, project_workspace_path, npm_audit_runner: Callable[[Path], Optional[Dict[str, Any]]] = _run_npm_audit, pip_audit_runner: Callable[[Path], Optional[Dict[str, Any]]] = _run_pip_audit):
    project = await db.projects.find_one({"id": project_id, "user_id": user_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    root = project_workspace_path(project_id).resolve()
    if not root.exists():
        return {"npm": None, "pip": None, "message": "No workspace files yet"}
    npm = await asyncio.to_thread(npm_audit_runner, root)
    pip = await asyncio.to_thread(pip_audit_runner, root)
    return {"npm": npm, "pip": pip}
