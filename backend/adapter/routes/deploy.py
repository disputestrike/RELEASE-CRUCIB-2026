"""Deploy routes — Railway + Vercel + Netlify."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
logger = logging.getLogger(__name__)
router = APIRouter()

def _get_auth():
    try:
        from server import get_current_user
        return get_current_user
    except Exception:
        from fastapi import Request
        async def noop(request: Request = None):
            return {"id": "anonymous"}
        return noop

class DeployRequest(BaseModel):
    target: str = "railway"

@router.post("/api/builds/{job_id}/deploy")
async def deploy_build(job_id: str, req: DeployRequest, user: dict = Depends(_get_auth())):
    try:
        from db_pg import get_pg_pool
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("SELECT project_id FROM jobs WHERE id=$1", job_id)
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")
        project_id = row["project_id"]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Delegate to existing Railway deploy
    try:
        import httpx, os
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"http://localhost:{os.getenv('PORT','8000')}/api/projects/{project_id}/deploy/railway",
                json={"job_id": job_id},
                timeout=60,
            )
            data = resp.json()
        url = data.get("deploy_url") or data.get("url") or ""
        from adapter.services.event_bridge import on_deploy_live
        if url:
            on_deploy_live(job_id, url, url)
        return {"status": "success" if url else "pending", "url": url,
                "previewUrl": url, "deployedAt": ""}
    except Exception as e:
        logger.warning("deploy error: %s", e)
        return {"status": "pending", "url": "", "previewUrl": "", "deployedAt": ""}
