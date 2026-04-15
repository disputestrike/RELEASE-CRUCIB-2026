"""
Skill Memory Service — CrucibAI learns from every build.

After each completed build, the Skill Extractor agent extracts patterns.
These skills are stored and loaded into future builds to make the AI smarter.

This is the key feature from "Everything Claude Code" — now running on
CrucibAI's 244-agent DAG instead of a CLI tool.
"""
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


async def save_skills_from_build(
    job_id: str,
    user_id: str,
    skill_extractor_output: str,
    pool=None,
) -> List[Dict]:
    """
    Parse Skill Extractor agent output and persist skills to database.
    Called automatically after every completed build.
    """
    if not skill_extractor_output or not pool:
        return []

    try:
        # Parse JSON output from Skill Extractor agent
        data = json.loads(skill_extractor_output.strip())
        skills = data.get("skills", [])
        build_summary = data.get("build_summary", {})
    except (json.JSONDecodeError, AttributeError):
        logger.warning("skill_memory: could not parse Skill Extractor output for job %s", job_id)
        return []

    if not skills:
        return []

    saved = []
    try:
        async with pool.acquire() as conn:
            # Ensure table exists
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS crucibai_skills (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    trigger_condition TEXT,
                    pattern TEXT NOT NULL,
                    confidence FLOAT DEFAULT 0.5,
                    use_count INTEGER DEFAULT 0,
                    created_at TIMESTAMPTZ DEFAULT NOW(),
                    updated_at TIMESTAMPTZ DEFAULT NOW()
                )
            """)

            for skill in skills:
                import uuid
                skill_id = str(uuid.uuid4())
                await conn.execute("""
                    INSERT INTO crucibai_skills
                    (id, user_id, job_id, name, category, trigger_condition, pattern, confidence, created_at)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW())
                    ON CONFLICT DO NOTHING
                """,
                    skill_id,
                    user_id,
                    job_id,
                    skill.get("name", "unnamed skill"),
                    skill.get("category", "general"),
                    skill.get("trigger", ""),
                    skill.get("pattern", ""),
                    float(skill.get("confidence", 0.5)),
                )
                saved.append(skill)

        logger.info("skill_memory: saved %d skills from job %s", len(saved), job_id)
    except Exception as e:
        logger.warning("skill_memory: failed to save skills: %s", e)

    return saved


async def load_relevant_skills(
    goal: str,
    user_id: str,
    pool=None,
    limit: int = 10,
) -> str:
    """
    Load the most relevant skills for a new build goal.
    Injected into the planner prompt to make future builds smarter.
    """
    if not pool:
        return ""

    try:
        async with pool.acquire() as conn:
            # Check table exists
            exists = await conn.fetchval(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'crucibai_skills')"
            )
            if not exists:
                return ""

            # Get top skills by use_count and confidence for this user
            # Simple relevance: match goal keywords against trigger_condition
            rows = await conn.fetch("""
                SELECT name, category, trigger_condition, pattern, confidence, use_count
                FROM crucibai_skills
                WHERE user_id = $1
                ORDER BY (confidence * 0.6 + LEAST(use_count, 10) * 0.04) DESC
                LIMIT $2
            """, user_id, limit * 2)

            if not rows:
                return ""

            # Filter by keyword relevance
            goal_words = set(goal.lower().split())
            scored = []
            for row in rows:
                trigger = (row["trigger_condition"] or "").lower()
                trigger_words = set(trigger.split())
                overlap = len(goal_words & trigger_words)
                scored.append((overlap, dict(row)))

            scored.sort(key=lambda x: -x[0])
            top = [s[1] for s in scored[:limit]]

            if not top:
                return ""

            # Format as context for planner
            lines = ["LEARNED SKILLS FROM PREVIOUS BUILDS (apply where relevant):"]
            for skill in top:
                lines.append(f"\n[{skill['category'].upper()}] {skill['name']}")
                if skill.get("trigger_condition"):
                    lines.append(f"  When: {skill['trigger_condition']}")
                lines.append(f"  Pattern: {skill['pattern'][:300]}")
                lines.append(f"  Confidence: {skill['confidence']:.0%}")

            return "\n".join(lines)

    except Exception as e:
        logger.warning("skill_memory: failed to load skills: %s", e)
        return ""


async def get_user_skills(user_id: str, pool=None) -> List[Dict]:
    """Get all skills for a user — for the skills library UI."""
    if not pool:
        return []
    try:
        async with pool.acquire() as conn:
            exists = await conn.fetchval(
                "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'crucibai_skills')"
            )
            if not exists:
                return []
            rows = await conn.fetch("""
                SELECT id, name, category, trigger_condition, pattern, confidence, use_count, created_at
                FROM crucibai_skills WHERE user_id = $1
                ORDER BY updated_at DESC LIMIT 100
            """, user_id)
            return [dict(r) for r in rows]
    except Exception as e:
        logger.warning("skill_memory: get_user_skills failed: %s", e)
        return []
