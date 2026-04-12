"""Load plan-side fields (e.g. build target) for executor steps."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from .build_targets import DEFAULT_BUILD_TARGET, normalize_build_target

logger = logging.getLogger(__name__)


async def fetch_build_target_for_job(job_id: str) -> str:
    """Latest draft plan_json for job → crucib_build_target."""
    if not job_id:
        return DEFAULT_BUILD_TARGET
    try:
        from db_pg import get_pg_pool

        pool = await get_pg_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT plan_json FROM build_plans
                WHERE job_id = $1
                ORDER BY created_at DESC
                LIMIT 1
                """,
                job_id,
            )
        if not row or row.get("plan_json") is None:
            return DEFAULT_BUILD_TARGET
        raw = row["plan_json"]
        plan: Dict[str, Any] = json.loads(raw) if isinstance(raw, str) else dict(raw)
        return normalize_build_target(plan.get("crucib_build_target"))
    except Exception as e:
        logger.debug("fetch_build_target_for_job: %s", e)
        return DEFAULT_BUILD_TARGET
