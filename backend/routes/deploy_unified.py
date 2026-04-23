"""CF12 — Unified /api/deploy dispatcher.

Single endpoint that routes to the appropriate per-target service.  Replaces
the pattern of clients having to know which target-specific endpoint to call
(e.g. /deploy/railway vs /deploy/vercel).

Supported targets:

    - railway    -> routes/projects.py (existing Railway flow)
    - vercel     -> services/project_deploy_service.one_click_deploy_vercel_service
    - netlify    -> services/project_deploy_service.one_click_deploy_netlify_service
    - docker     -> emit Dockerfile + build instructions (via existing files)
    - k8s        -> emit k8s manifests from existing deploy_files + templates
    - terraform  -> emit terraform module scaffolding

Docker/K8s/Terraform are emitter-only (they produce a downloadable archive;
they don't provision remote infra directly — that's Phase 3).
"""
from __future__ import annotations

import io
import logging
import zipfile
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/deploy", tags=["deploy"])

SUPPORTED_TARGETS = {"railway", "vercel", "netlify", "docker", "k8s", "terraform"}


def _get_auth():
    try:
        from server import get_current_user
        return get_current_user
    except Exception:
        from fastapi import Request

        async def noop(request: Request = None):  # type: ignore[override]
            return {"id": "anonymous"}

        return noop


class DeployRequest(BaseModel):
    target: str = Field(..., description="One of: railway, vercel, netlify, docker, k8s, terraform")
    project_id: str
    env_vars: Optional[Dict[str, str]] = None
    region: Optional[str] = None


# ── Dockerfile / k8s / terraform emitters (pure templates) ───────────────────


def _dockerfile_for(files: Dict[str, str]) -> str:
    has_package = any("package.json" in p for p in files)
    has_requirements = any("requirements.txt" in p for p in files)
    if has_package:
        return (
            "# CrucibAI-emitted Dockerfile (node)\n"
            "FROM node:20-alpine AS build\n"
            "WORKDIR /app\n"
            "COPY package*.json ./\n"
            "RUN npm ci --omit=dev\n"
            "COPY . .\n"
            "RUN npm run build || true\n"
            "EXPOSE 3000\n"
            'CMD ["npm", "start"]\n'
        )
    if has_requirements:
        return (
            "# CrucibAI-emitted Dockerfile (python)\n"
            "FROM python:3.11-slim\n"
            "WORKDIR /app\n"
            "COPY requirements.txt ./\n"
            "RUN pip install --no-cache-dir -r requirements.txt\n"
            "COPY . .\n"
            "EXPOSE 8000\n"
            'CMD ["python", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]\n'
        )
    return (
        "# CrucibAI-emitted Dockerfile (fallback)\n"
        "FROM nginx:alpine\n"
        "COPY . /usr/share/nginx/html\n"
        "EXPOSE 80\n"
    )


def _k8s_manifest(project_name: str) -> str:
    safe = project_name.lower().replace(" ", "-").replace("_", "-")
    return (
        "# CrucibAI-emitted k8s manifest\n"
        "apiVersion: apps/v1\n"
        "kind: Deployment\n"
        f"metadata: {{name: {safe}}}\n"
        "spec:\n"
        "  replicas: 2\n"
        f"  selector: {{matchLabels: {{app: {safe}}}}}\n"
        "  template:\n"
        f"    metadata: {{labels: {{app: {safe}}}}}\n"
        "    spec:\n"
        "      containers:\n"
        f"        - name: {safe}\n"
        f"          image: {safe}:latest\n"
        "          ports: [{containerPort: 3000}]\n"
        "---\n"
        "apiVersion: v1\n"
        "kind: Service\n"
        f"metadata: {{name: {safe}}}\n"
        "spec:\n"
        "  type: LoadBalancer\n"
        f"  selector: {{app: {safe}}}\n"
        "  ports: [{port: 80, targetPort: 3000}]\n"
    )


def _terraform_module(project_name: str) -> str:
    safe = project_name.lower().replace(" ", "-").replace("_", "-")
    return (
        "# CrucibAI-emitted terraform module\n"
        'terraform {\n'
        '  required_providers {\n'
        '    docker = { source = "kreuzwerker/docker", version = "~> 3.0" }\n'
        '  }\n'
        '}\n'
        'resource "docker_image" "app" {\n'
        f'  name = "{safe}:latest"\n'
        '  build { context = path.module }\n'
        '}\n'
        'resource "docker_container" "app" {\n'
        f'  name  = "{safe}"\n'
        '  image = docker_image.app.image_id\n'
        '  ports { internal = 3000, external = 3000 }\n'
        '}\n'
    )


def _zip_bytes(entries: Dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in entries.items():
            zf.writestr(path, content)
    return buf.getvalue()


async def _load_deploy_files(db, project_id: str, user_id: str) -> tuple[Dict[str, str], str]:
    try:
        from services.project_deploy_service import get_project_deploy_files_service
        return await get_project_deploy_files_service(db, project_id, user_id)
    except HTTPException:
        raise
    except Exception:
        # Fallback when db/ORM isn't available — return a minimal stub so
        # emitters still produce valid output in degraded envs.
        return ({"README.md": f"# {project_id}\n"}, project_id[:40] or "crucibai-app")


# ── Routes ────────────────────────────────────────────────────────────────────


@router.post("")
async def unified_deploy(
    body: DeployRequest,
    request: Request,
    user: dict = Depends(_get_auth()),
):
    target = body.target.lower()
    if target not in SUPPORTED_TARGETS:
        raise HTTPException(
            status_code=400,
            detail={"error": "unsupported_target", "supported": sorted(SUPPORTED_TARGETS)},
        )

    # For live-deploy targets (railway/vercel/netlify), delegate to existing services.
    if target in {"railway", "vercel", "netlify"}:
        try:
            import httpx  # noqa: F401
            from deps import get_db  # type: ignore
            db = await get_db()
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"db unavailable: {exc}")

        if target == "vercel":
            try:
                from services.project_deploy_service import one_click_deploy_vercel_service
                from validate_deployment import validate_deployment  # type: ignore
                import httpx
            except Exception as exc:
                raise HTTPException(status_code=503, detail=f"vercel path unavailable: {exc}")
            return await one_click_deploy_vercel_service(
                db=db,
                audit_logger=None,
                project_id=body.project_id,
                user=user,
                request=request,
                body=body,
                validate_deployment=validate_deployment,
                httpx_module=httpx,
            )
        if target == "netlify":
            try:
                from services.project_deploy_service import one_click_deploy_netlify_service
                from validate_deployment import validate_deployment  # type: ignore
                import httpx
            except Exception as exc:
                raise HTTPException(status_code=503, detail=f"netlify path unavailable: {exc}")
            return await one_click_deploy_netlify_service(
                db=db,
                audit_logger=None,
                project_id=body.project_id,
                user=user,
                request=request,
                body=body,
                validate_deployment=validate_deployment,
                httpx_module=httpx,
            )
        # Railway: delegate to existing /api/projects/{pid}/deploy/railway
        try:
            from services.project_deploy_service import deploy_railway_package_service
            from validate_deployment import validate_deployment  # type: ignore
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"railway path unavailable: {exc}")
        return await deploy_railway_package_service(
            db=db,
            project_id=body.project_id,
            user=user,
            validate_deployment=validate_deployment,
        )

    # Emitter targets: docker/k8s/terraform — produce downloadable artifact bundle.
    try:
        from deps import get_db  # type: ignore
        db = await get_db()
    except Exception:
        db = None

    try:
        files, name = await _load_deploy_files(db, body.project_id, user.get("id", "anon"))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"load files failed: {exc}")

    bundle: Dict[str, str] = dict(files)
    if target == "docker":
        bundle["Dockerfile"] = _dockerfile_for(files)
        bundle[".dockerignore"] = "node_modules\n__pycache__\n.env\n"
    elif target == "k8s":
        bundle["Dockerfile"] = _dockerfile_for(files)
        bundle["k8s/manifest.yaml"] = _k8s_manifest(name)
    elif target == "terraform":
        bundle["Dockerfile"] = _dockerfile_for(files)
        bundle["terraform/main.tf"] = _terraform_module(name)

    archive = _zip_bytes(bundle)

    import base64

    return {
        "status": "emitted",
        "target": target,
        "project_id": body.project_id,
        "project_name": name,
        "files_count": len(bundle),
        "archive_base64": base64.b64encode(archive).decode("ascii"),
        "archive_size_bytes": len(archive),
    }


@router.get("/targets")
async def list_targets():
    """Discovery endpoint — frontend uses this to populate TopActions."""
    return {
        "supported": sorted(SUPPORTED_TARGETS),
        "live_deploy": ["railway", "vercel", "netlify"],
        "emit_only": ["docker", "k8s", "terraform"],
    }
