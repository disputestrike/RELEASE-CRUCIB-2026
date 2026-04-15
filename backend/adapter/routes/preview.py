"""Preview routes."""
from fastapi import APIRouter, Depends
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

@router.get("/api/builds/{job_id}/preview")
async def get_preview(job_id: str, user: dict = Depends(_get_auth())):
    from adapter.services.preview_manager import get_preview_url
    url = await get_preview_url(job_id)
    return {
        "url": url or f"/published/{job_id}/",
        "available": url is not None,
        "jobId": job_id,
    }
