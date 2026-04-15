from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, Optional

from fastapi import HTTPException
from fastapi.responses import FileResponse, Response

BRANDING_HTML = """<!DOCTYPE html><html><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"></head><body style=\"margin:0;padding:0;font-family:system-ui,sans-serif;font-size:12px;display:flex;align-items:center;justify-content:center;min-height:28px;background:transparent;color:#808080;\"><a href=\"https://crucibai.com\" target=\"_blank\" rel=\"noopener noreferrer\" style=\"color:#808080;text-decoration:none;\">Built with CrucibAI</a></body></html>"""

_PUBLISHED_HTML_REWRITE_PATTERN = re.compile(
    r'(?P<attr>\b(?:src|href|content)=["\'])(?P<path>/(?!/)[^"\']+)(?P<quote>["\'])',
    flags=re.IGNORECASE,
)


def branding_response() -> Response:
    return Response(content=BRANDING_HTML, media_type="text/html")


def _should_prefix_published_asset(path: str) -> bool:
    if not path.startswith("/"):
        return False
    if path.startswith(("/api/", "/published/", "//")):
        return False
    return path.startswith(
        (
            "/assets/",
            "/static/",
            "/favicon",
            "/manifest",
            "/logo",
            "/robots",
            "/vite.svg",
            "/icons/",
            "/apple-touch",
            "/android-chrome",
            "/mstile",
        )
    )


def rewrite_published_html(html: str, job_id: str) -> str:
    publish_prefix = f"/published/{job_id}/"

    def _repl(match: re.Match[str]) -> str:
        original_path = match.group("path")
        if not _should_prefix_published_asset(original_path):
            return match.group(0)
        rewritten = publish_prefix.rstrip("/") + original_path
        return f"{match.group('attr')}{rewritten}{match.group('quote')}"

    rewritten = _PUBLISHED_HTML_REWRITE_PATTERN.sub(_repl, html)
    if "<head>" in rewritten and "<base " not in rewritten:
        rewritten = rewritten.replace("<head>", f'<head><base href="{publish_prefix}">', 1)
    return rewritten


def job_dist_root(
    project_id: Optional[str],
    project_workspace_path: Callable[[str], Path],
    workspace_root: Path,
) -> Optional[Path]:
    if not project_id:
        return None
    root = (project_workspace_path(project_id).resolve() / "dist").resolve()
    try:
        root.relative_to(workspace_root.resolve())
    except ValueError:
        return None
    return root


def job_public_preview_url(
    job: Dict[str, Any],
    project_workspace_path: Callable[[str], Path],
    workspace_root: Path,
    published_app_url: Callable[[str], str],
) -> Optional[str]:
    project_id = job.get("project_id")
    job_id = str(job.get("id") or "").strip()
    if not project_id or not job_id:
        return None
    dist_root = job_dist_root(project_id, project_workspace_path, workspace_root)
    if not dist_root or not dist_root.exists():
        return None
    return published_app_url(job_id)


def enrich_job_public_urls(
    job: Dict[str, Any],
    project_workspace_path: Callable[[str], Path],
    workspace_root: Path,
    published_app_url: Callable[[str], str],
) -> Dict[str, Any]:
    enriched = dict(job or {})
    preview_url = enriched.get("preview_url") or job_public_preview_url(
        enriched, project_workspace_path, workspace_root, published_app_url
    )
    if preview_url:
        enriched["preview_url"] = preview_url
        enriched.setdefault("published_url", preview_url)
        enriched.setdefault("deploy_url", preview_url)
    return enriched


async def serve_published_app_response(
    job_id: str,
    path: str,
    get_job: Callable[[str], Awaitable[Optional[Dict[str, Any]]]],
    safe_publish_id: Callable[[str], str],
    project_workspace_path: Callable[[str], Path],
    workspace_root: Path,
):
    if safe_publish_id(job_id) != job_id:
        raise HTTPException(status_code=400, detail="Invalid published app id")
    try:
        job = await get_job(job_id)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Published app lookup unavailable: {exc}")

    if not job or job.get("status") in {"failed", "blocked", "cancelled", "canceled", "error"}:
        raise HTTPException(status_code=404, detail="Published app not found")
    project_id = job.get("project_id")
    if not project_id:
        raise HTTPException(status_code=404, detail="Published app has no workspace")

    root = job_dist_root(project_id, project_workspace_path, workspace_root)
    if root is None:
        raise HTTPException(status_code=400, detail="Published app path outside workspace")
    if not root.exists():
        raise HTTPException(status_code=404, detail="Published app build artifact missing")

    clean = (path or "").strip().replace("\\", "/").lstrip("/")
    if ".." in clean or clean.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid published app path")
    requested_rel = Path(clean) if clean else Path("index.html")
    full = (root / clean).resolve() if clean else (root / "index.html").resolve()
    try:
        full.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=400, detail="Published app path outside dist")
    if full.is_dir():
        full = full / "index.html"
    if not full.exists():
        if clean and requested_rel.suffix:
            raise HTTPException(status_code=404, detail="Published app file not found")
        full = root / "index.html"
    if full.suffix.lower() == ".html":
        html = full.read_text(encoding="utf-8", errors="replace")
        return Response(content=rewrite_published_html(html, job_id), media_type="text/html")
    return FileResponse(full)
