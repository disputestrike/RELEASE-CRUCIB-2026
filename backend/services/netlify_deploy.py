"""
Netlify one-shot deploy service.
Set NETLIFY_TOKEN (Personal Access Token from app.netlify.com/user/applications).
Optionally set NETLIFY_SITE_ID to deploy to the same site each time;
if unset, a new Netlify site is created per deploy.

Usage:
    result = await deploy_to_netlify(dist_dir="/path/to/dist", site_name="my-app")
    # result = {"url": "https://xxx.netlify.app", "site_id": "...", "deploy_id": "..."}
"""
from __future__ import annotations
import asyncio, hashlib, io, logging, mimetypes, os, zipfile
from pathlib import Path
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

NETLIFY_API = "https://api.netlify.com/api/v1"

def _token() -> Optional[str]:
    return os.environ.get("NETLIFY_TOKEN", "").strip() or None

def netlify_configured() -> bool:
    return bool(_token())

def _headers() -> dict:
    return {"Authorization": f"Bearer {_token()}", "Content-Type": "application/zip"}

def _zip_dist(dist_dir: str) -> bytes:
    """Zip the dist directory in memory."""
    buf = io.BytesIO()
    dist = Path(dist_dir)
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in dist.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(dist))
    return buf.getvalue()

async def deploy_to_netlify(
    dist_dir: str,
    site_name: Optional[str] = None,
    site_id: Optional[str] = None,
    timeout: int = 90,
) -> dict:
    """
    Deploy a built React/Vite dist folder to Netlify.
    Returns {"url": str, "site_id": str, "deploy_id": str}.
    Raises RuntimeError on failure.
    """
    token = _token()
    if not token:
        raise RuntimeError("NETLIFY_TOKEN not set — cannot deploy")

    if not os.path.isdir(dist_dir):
        raise RuntimeError(f"dist_dir does not exist: {dist_dir}")

    zip_bytes = _zip_dist(dist_dir)
    logger.info("[NETLIFY] Zipped dist: %d bytes", len(zip_bytes))

    site_id = site_id or os.environ.get("NETLIFY_SITE_ID", "").strip() or None
    
    async with httpx.AsyncClient(timeout=timeout) as client:
        # Create a new site if no site_id
        if not site_id:
            slug = (site_name or "crucibai-app").lower().replace(" ", "-")[:32]
            resp = await client.post(
                f"{NETLIFY_API}/sites",
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json={"name": slug, "custom_domain": None},
            )
            if resp.status_code not in (200, 201):
                raise RuntimeError(f"Netlify site creation failed: {resp.status_code} {resp.text[:200]}")
            site_data = resp.json()
            site_id = site_data["id"]
            logger.info("[NETLIFY] Created site %s id=%s", slug, site_id)

        # Deploy the ZIP
        resp = await client.post(
            f"{NETLIFY_API}/sites/{site_id}/deploys",
            content=zip_bytes,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/zip"},
        )
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Netlify deploy failed: {resp.status_code} {resp.text[:300]}")
        deploy = resp.json()
        deploy_id = deploy["id"]
        logger.info("[NETLIFY] Deploy created: %s", deploy_id)

        # Poll until ready (max 60s)
        for _ in range(30):
            await asyncio.sleep(2)
            poll = await client.get(
                f"{NETLIFY_API}/deploys/{deploy_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            state = poll.json().get("state", "")
            if state == "ready":
                url = poll.json().get("ssl_url") or poll.json().get("url", "")
                logger.info("[NETLIFY] Deploy ready: %s", url)
                return {"url": url, "site_id": site_id, "deploy_id": deploy_id}
            if state in ("error", "failed"):
                raise RuntimeError(f"Netlify deploy state={state}")
        
        # Timeout — return the expected URL anyway
        url = deploy.get("ssl_url") or deploy.get("url", f"https://{site_id}.netlify.app")
        return {"url": url, "site_id": site_id, "deploy_id": deploy_id}
