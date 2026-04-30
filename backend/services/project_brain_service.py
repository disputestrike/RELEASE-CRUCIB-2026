"""
Project Brain Service — persistent cross-session memory for each project/user.

Stores:
  - Product goal and vision
  - Chosen stack and architecture decisions
  - Accepted UI patterns
  - Known bugs and their fixes
  - Deployment choices and environment
  - Security decisions
  - User preferences (style, tone, complexity)
  - Completed milestones
  - Open tasks

This is the "one continuous project brain" that makes CrucibAI
feel like it remembers everything across sessions.
"""
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS project_brain (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    project_id TEXT,
    goal TEXT,
    stack TEXT,
    architecture TEXT,
    ui_patterns JSONB DEFAULT '[]',
    known_fixes JSONB DEFAULT '[]',
    deployment_config JSONB DEFAULT '{}',
    security_decisions JSONB DEFAULT '[]',
    completed_milestones JSONB DEFAULT '[]',
    open_tasks JSONB DEFAULT '[]',
    user_preferences JSONB DEFAULT '{}',
    summary TEXT,
    build_count INTEGER DEFAULT 0,
    last_quality_score FLOAT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, project_id)
)
"""


async def _ensure_table(pool) -> bool:
    try:
        async with pool.acquire() as conn:
            await conn.execute(_CREATE_TABLE)
        return True
    except Exception as e:
        logger.warning("project_brain: table creation failed: %s", e)
        return False


async def load_project_brain(
    user_id: str,
    project_id: Optional[str] = None,
    pool=None,
) -> Optional[Dict]:
    """Load the project brain for a user/project. Returns None if not found."""
    if not pool:
        try:
            from ....db_pg import get_pg_pool            pool = await get_pg_pool()
        except Exception:
            return None

    await _ensure_table(pool)

    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """SELECT * FROM project_brain
                   WHERE user_id = $1 AND (project_id = $2 OR ($2 IS NULL AND project_id IS NULL))
                   ORDER BY updated_at DESC LIMIT 1""",
                user_id, project_id
            )
            if not row:
                return None

            brain = dict(row)
            # Parse JSONB fields
            for field in ['ui_patterns', 'known_fixes', 'deployment_config',
                          'security_decisions', 'completed_milestones', 'open_tasks', 'user_preferences']:
                if isinstance(brain.get(field), str):
                    try:
                        brain[field] = json.loads(brain[field])
                    except Exception:
                        pass

            return brain
    except Exception as e:
        logger.warning("project_brain: load failed: %s", e)
        return None


async def update_project_brain(
    user_id: str,
    project_id: Optional[str] = None,
    job_id: str = "",
    goal: str = "",
    stack: str = "",
    quality_score: float = 0,
    architecture: str = "",
    pool=None,
) -> bool:
    """Update the project brain after a completed build."""
    if not user_id:
        return False

    if not pool:
        try:
            from ....db_pg import get_pg_pool            pool = await get_pg_pool()
        except Exception:
            return False

    await _ensure_table(pool)

    try:
        brain_id = str(uuid.uuid4())
        # Build a natural language summary
        summary_parts = []
        if goal:
            summary_parts.append(f"Project goal: {goal[:200]}")
        if stack:
            summary_parts.append(f"Stack: {stack}")
        if quality_score:
            summary_parts.append(f"Last build quality: {quality_score:.0%}")
        summary = " | ".join(summary_parts)

        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO project_brain
                    (id, user_id, project_id, goal, stack, architecture, summary,
                     build_count, last_quality_score, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, 1, $8, NOW())
                ON CONFLICT (user_id, project_id) DO UPDATE SET
                    goal = COALESCE(NULLIF($4, ''), project_brain.goal),
                    stack = COALESCE(NULLIF($5, ''), project_brain.stack),
                    architecture = COALESCE(NULLIF($6, ''), project_brain.architecture),
                    summary = CASE WHEN $7 != '' THEN $7 ELSE project_brain.summary END,
                    build_count = project_brain.build_count + 1,
                    last_quality_score = CASE WHEN $8 > 0 THEN $8 ELSE project_brain.last_quality_score END,
                    updated_at = NOW()
            """,
                brain_id, user_id, project_id, goal, stack, architecture,
                summary, float(quality_score)
            )
        return True
    except Exception as e:
        logger.warning("project_brain: update failed: %s", e)
        return False


async def add_known_fix(
    user_id: str,
    error_pattern: str,
    fix: str,
    project_id: Optional[str] = None,
    pool=None,
) -> bool:
    """Add a known bug fix to the project brain."""
    if not pool:
        try:
            from ....db_pg import get_pg_pool            pool = await get_pg_pool()
        except Exception:
            return False

    await _ensure_table(pool)

    try:
        async with pool.acquire() as conn:
            existing = await conn.fetchval(
                """SELECT known_fixes FROM project_brain
                   WHERE user_id = $1 AND (project_id = $2 OR project_id IS NULL)
                   LIMIT 1""",
                user_id, project_id
            )
            fixes = json.loads(existing) if existing else []
            fixes.append({
                "error": error_pattern[:200],
                "fix": fix[:500],
                "added_at": datetime.now(timezone.utc).isoformat()
            })
            fixes = fixes[-50:]  # Keep last 50 fixes

            await conn.execute("""
                UPDATE project_brain SET known_fixes = $1, updated_at = NOW()
                WHERE user_id = $2 AND (project_id = $3 OR project_id IS NULL)
            """, json.dumps(fixes), user_id, project_id)
        return True
    except Exception as e:
        logger.warning("project_brain: add_known_fix failed: %s", e)
        return False


async def get_brain_summary(user_id: str, project_id: Optional[str] = None, pool=None) -> str:
    """Get a formatted summary of the project brain for injection into prompts."""
    brain = await load_project_brain(user_id, project_id, pool)
    if not brain:
        return ""

    parts = ["PROJECT BRAIN (what we know about this project):"]
    if brain.get("goal"):
        parts.append(f"Goal: {brain['goal'][:200]}")
    if brain.get("stack"):
        parts.append(f"Stack: {brain['stack']}")
    if brain.get("architecture"):
        parts.append(f"Architecture: {brain['architecture'][:200]}")

    fixes = brain.get("known_fixes", [])
    if fixes:
        parts.append(f"Known fixes ({len(fixes)}):")
        for fix in fixes[-5:]:
            parts.append(f"  - Error: {fix.get('error', '')[:80]} → Fix: {fix.get('fix', '')[:80]}")

    milestones = brain.get("completed_milestones", [])
    if milestones:
        parts.append(f"Completed: {', '.join(str(m) for m in milestones[-5:])}")

    if brain.get("build_count", 0) > 0:
        parts.append(f"Build count: {brain['build_count']} | Last quality: {brain.get('last_quality_score', 0):.0%}")

    return "\n".join(parts)
