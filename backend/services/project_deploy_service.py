from __future__ import annotations

import base64
import os
from datetime import datetime, timezone
from io import BytesIO
from typing import Any, Dict, Optional

from fastapi import HTTPException


async def get_project_deploy_files_service(db, project_id: str, user_id: str) -> tuple[Dict[str, str], str]:
    project = await db.projects.find_one({"id": project_id, "user_id": user_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    deploy_files = project.get("deploy_files") or {}
    if not deploy_files:
        raise HTTPException(
            status_code=404,
            detail="No deploy snapshot. Open in Workspace and use Deploy there, or re-run the build.",
        )
    name = (project.get("name") or "crucibai-app").replace(" ", "-")[:50]
    return deploy_files, name


async def one_click_deploy_vercel_service(
    *,
    db,
    audit_logger,
    project_id: str,
    user: dict,
    request,
    body,
    validate_deployment,
    httpx_module,
) -> dict:
    deploy_files, project_name = await get_project_deploy_files_service(db, project_id, user["id"])
    validation = validate_deployment("vercel", deploy_files, None)
    if not validation.valid and validation.errors:
        raise HTTPException(status_code=400, detail={
            "message": "Deploy validation failed",
            "errors": validation.errors,
            "warnings": validation.warnings,
        })
    u = await db.users.find_one({"id": user["id"]}, {"deploy_tokens": 1})
    vercel_token = (
        (body.token if body and getattr(body, 'token', None) else None)
        or (u.get("deploy_tokens") or {}).get("vercel")
        or os.environ.get("VERCEL_TOKEN")
    )
    if not vercel_token:
        raise HTTPException(status_code=402, detail="Add your Vercel token in Settings → Deploy integrations for one-click deploy, or set VERCEL_TOKEN on server.")
    files_payload = []
    for path, content in deploy_files.items():
        safe_path = (path or "").lstrip("/")
        if not safe_path:
            continue
        raw = content if isinstance(content, (bytes, bytearray)) else content.encode("utf-8")
        files_payload.append({
            "file": safe_path,
            "data": base64.b64encode(raw).decode("ascii"),
            "encoding": "base64",
        })
    if not files_payload:
        raise HTTPException(status_code=400, detail="No deploy files to upload")
    async with httpx_module.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            "https://api.vercel.com/v13/deployments",
            headers={
                "Authorization": f"Bearer {vercel_token}",
                "Content-Type": "application/json",
            },
            json={"name": project_name, "files": files_payload, "target": "production"},
        )
    if r.status_code >= 400:
        msg = r.text
        try:
            msg = r.json().get("error", {}).get("message", r.text)
        except Exception:
            pass
        raise HTTPException(status_code=502, detail=f"Vercel deploy failed: {msg}")
    data = r.json()
    raw_url = data.get("url") or ((data.get("alias", [""])[0]) if data.get("alias") else "")
    if not raw_url and data.get("id"):
        raw_url = f"{data.get('id', '')}.vercel.app"
    live_url = f"https://{raw_url}" if raw_url and not raw_url.startswith("http") else raw_url
    if live_url:
        await db.projects.update_one({"id": project_id, "user_id": user["id"]}, {"$set": {"live_url": live_url}})
        if audit_logger:
            await audit_logger.log(
                user["id"],
                "project_deployed",
                resource_type="project",
                resource_id=project_id,
                new_value={"live_url": live_url},
                ip_address=getattr(request.client, "host", None),
            )
    return {"url": live_url, "deployment_id": data.get("id"), "status": data.get("readyState") or data.get("status")}


async def one_click_deploy_netlify_service(
    *,
    db,
    audit_logger,
    project_id: str,
    user: dict,
    request,
    body,
    validate_deployment,
    build_project_deploy_zip,
    httpx_module,
) -> dict:
    deploy_files, _ = await get_project_deploy_files_service(db, project_id, user["id"])
    validation = validate_deployment("netlify", deploy_files, None)
    if not validation.valid and validation.errors:
        raise HTTPException(status_code=400, detail={
            "message": "Deploy validation failed",
            "errors": validation.errors,
            "warnings": validation.warnings,
        })
    buf: BytesIO = await build_project_deploy_zip(project_id, user["id"])
    zip_bytes = buf.getvalue()
    u = await db.users.find_one({"id": user["id"]}, {"deploy_tokens": 1})
    netlify_token = (
        (body.token if body and getattr(body, 'token', None) else None)
        or (u.get("deploy_tokens") or {}).get("netlify")
        or os.environ.get("NETLIFY_TOKEN")
    )
    if not netlify_token:
        raise HTTPException(status_code=402, detail="Add your Netlify token in Settings → Deploy integrations for one-click deploy, or set NETLIFY_TOKEN on server.")
    existing_project = await db.projects.find_one({"id": project_id, "user_id": user["id"]}, {"netlify_site_id": 1})
    netlify_site_id = (existing_project or {}).get("netlify_site_id")
    async with httpx_module.AsyncClient(timeout=90.0) as client:
        if netlify_site_id:
            r = await client.post(
                f"https://api.netlify.com/api/v1/sites/{netlify_site_id}/deploys",
                headers={"Authorization": f"Bearer {netlify_token}", "Content-Type": "application/zip"},
                content=zip_bytes,
            )
        else:
            r = await client.post(
                "https://api.netlify.com/api/v1/sites",
                headers={"Authorization": f"Bearer {netlify_token}", "Content-Type": "application/zip"},
                content=zip_bytes,
            )
    if r.status_code >= 400:
        msg = r.text
        try:
            msg = r.json().get("message", r.text)
        except Exception:
            pass
        raise HTTPException(status_code=502, detail=f"Netlify deploy failed: {msg}")
    data = r.json()
    site_id = data.get("id") if not netlify_site_id else (data.get("site_id") or netlify_site_id)
    url = data.get("ssl_url") or data.get("url") or ""
    if not url and data.get("default_subdomain"):
        url = f"https://{data['default_subdomain']}.netlify.app"
    if not url and data.get("name"):
        url = f"https://{data['name']}.netlify.app"
    updates: dict[str, Any] = {}
    if url:
        updates["live_url"] = url
    if site_id and site_id != netlify_site_id:
        updates["netlify_site_id"] = site_id
    if updates:
        await db.projects.update_one({"id": project_id, "user_id": user["id"]}, {"$set": updates})
    if url and audit_logger:
        await audit_logger.log(
            user["id"],
            "project_deployed",
            resource_type="project",
            resource_id=project_id,
            new_value={"live_url": url},
            ip_address=getattr(request.client, "host", None),
        )
    return {"url": url, "site_id": site_id}


async def patch_project_publish_settings_service(*, db, project_id: str, body, user: dict) -> dict:
    project = await db.projects.find_one({"id": project_id, "user_id": user["id"]})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    updates = {}
    if body.custom_domain is not None:
        d = (body.custom_domain or "").strip().lower()
        if d and len(d) > 253:
            raise HTTPException(status_code=400, detail="custom_domain too long")
        if d and any(c in d for c in (" ", "/", "\\", ":", "?", "#", "<", ">", "@")):
            raise HTTPException(status_code=400, detail="custom_domain has invalid characters")
        updates["custom_domain"] = d or None
    if body.railway_project_url is not None:
        u = (body.railway_project_url or "").strip()
        if u and len(u) > 500:
            raise HTTPException(status_code=400, detail="railway_project_url too long")
        updates["railway_project_url"] = u or None
    if not updates:
        return {"project": {k: v for k, v in project.items() if k != "_id"}}
    updates["publish_settings_updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.projects.update_one({"id": project_id, "user_id": user["id"]}, {"$set": updates})
    out = await db.projects.find_one({"id": project_id, "user_id": user["id"]}, {"_id": 0})
    return {"project": out}


async def deploy_railway_package_service(*, db, project_id: str, user: dict, validate_deployment) -> dict:
    deploy_files, project_name = await get_project_deploy_files_service(db, project_id, user["id"])
    validation = validate_deployment("railway", deploy_files, None)
    if not validation.valid and validation.errors:
        raise HTTPException(status_code=400, detail={
            "message": "Deploy validation failed for Railway package",
            "errors": validation.errors,
            "warnings": validation.warnings,
        })
    steps = [
        "Download Deploy ZIP from this modal (server build snapshot).",
        "Unzip into an empty folder.",
        "npm i -g @railway/cli && railway login",
        "railway init  (or railway link) in that folder.",
        "railway up — set DATABASE_URL, JWT_SECRET, and API keys in Railway Variables.",
        "Optional: connect GitHub repo to Railway for continuous deploy.",
    ]
    return {
        "ok": True,
        "platform": "railway",
        "project_name": project_name,
        "steps": steps,
        "dashboard_url": "https://railway.app/new",
        "zip_relative_path": f"/api/projects/{project_id}/deploy/zip",
    }
