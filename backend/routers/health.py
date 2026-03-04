"""
Health and readiness router.
Exposes GET /api/health for load balancers and ops. All wired in app.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health():
    """Liveness/readiness: returns 200 when the app is up. Wired in app."""
    return {"status": "healthy", "service": "crucibai"}
