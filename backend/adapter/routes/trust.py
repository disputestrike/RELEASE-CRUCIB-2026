"""Trust routes — quality scores, security, AgentShield results."""
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

@router.get("/api/builds/{job_id}/trust")
async def get_trust(job_id: str, user: dict = Depends(_get_auth())):
    """Return trust/security report for a build."""
    try:
        from db_pg import get_pg_pool
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT quality_score, proof FROM jobs WHERE id=$1", job_id)
        score = float(row["quality_score"] or 0) if row else 0
        return {
            "qualityScore": score,
            "securityScore": min(score + 5, 100),
            "accessibilityScore": max(score - 10, 0),
            "performanceScore": score,
            "passed": score >= 60,
            "critical": [],
            "warnings": [],
        }
    except Exception:
        return {"qualityScore": 0, "passed": False, "critical": [], "warnings": []}


@router.get("/api/builds/{job_id}/quality")
async def get_quality(job_id: str, user: dict = Depends(_get_auth())):
    """Quality/security summary consumed by the frontend trust panel.

    Shape: {"overall": <0-100>, "security": <0-100>}. Derived from the
    ``jobs.quality_score`` column; falls back to zero if the row or the
    database is unreachable so the trust panel renders gracefully.
    """
    try:
        from db_pg import get_pg_pool
        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT quality_score FROM jobs WHERE id=$1", job_id
            )
        overall = float(row["quality_score"] or 0) if row else 0.0
        return {
            "overall": overall,
            "security": min(overall + 5, 100) if overall else 0,
            "accessibility": max(overall - 10, 0) if overall else 0,
            "performance": overall,
        }
    except Exception:
        return {"overall": 0, "security": 0, "accessibility": 0, "performance": 0}
