"""
Preview Manager — manages preview URL resolution for jobs.
Cascades: dev_server_url → preview_url → published_url → deploy_url → sandpack path
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def get_preview_url(job_id: str, pool=None) -> Optional[str]:
    """Get the best available preview URL for a job."""
    if not pool:
        try:
            from db_pg import get_pg_pool
            pool = await get_pg_pool()
        except Exception:
            return None
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT dev_server_url, preview_url, published_url, deploy_url
                   FROM jobs WHERE id = $1 LIMIT 1""",
                job_id
            )
            if not row:
                return None
            return (row["dev_server_url"] or row["preview_url"] or
                    row["published_url"] or row["deploy_url"] or None)
    except Exception as e:
        logger.debug("get_preview_url: %s", e)
        # Fallback to published path
        return f"/published/{job_id}/"


async def get_preview_status(job_id: str) -> dict:
    """Return preview availability status for a job."""
    url = await get_preview_url(job_id)
    return {
        "available": url is not None,
        "url": url,
        "sandpackFallback": url is None,
    }
