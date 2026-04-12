"""
Health and readiness router.
Exposes GET /api/health for load balancers and ops. All wired in app.
"""

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health():
    """Liveness/readiness: returns 200 when the app is up. Wired in app."""
    return {
        "status": "healthy",
        "service": "crucibai",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
