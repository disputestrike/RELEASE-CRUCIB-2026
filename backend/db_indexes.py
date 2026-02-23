"""
MongoDB index creation for CrucibAI collections.
Called at app startup to keep queries fast at scale.
Failures are logged but do not crash the app (e.g. missing perms).
"""
import logging

logger = logging.getLogger(__name__)


async def ensure_indexes(db):
    """Create recommended indexes on all hot-path collections."""
    try:
        await db.users.create_index("id", unique=True)
        await db.users.create_index("email", unique=True)
        await db.users.create_index("created_at")
    except Exception as e:
        logger.warning("Index users: %s", e)

    try:
        await db.projects.create_index("user_id")
        await db.projects.create_index("id", unique=True)
        await db.projects.create_index("created_at")
        await db.projects.create_index("status")
    except Exception as e:
        logger.warning("Index projects: %s", e)

    try:
        await db.token_ledger.create_index("user_id")
        await db.token_ledger.create_index([("user_id", 1), ("created_at", -1)])
        await db.token_ledger.create_index("type")
    except Exception as e:
        logger.warning("Index token_ledger: %s", e)

    try:
        await db.agent_runs.create_index("agent_id")
        await db.agent_runs.create_index("triggered_at")
    except Exception as e:
        logger.warning("Index agent_runs: %s", e)

    try:
        await db.agent_status.create_index("project_id")
    except Exception as e:
        logger.warning("Index agent_status: %s", e)

    try:
        await db.workspace_env.create_index("user_id", unique=True)
    except Exception as e:
        logger.warning("Index workspace_env: %s", e)

    try:
        await db.project_logs.create_index("project_id")
        await db.project_logs.create_index([("project_id", 1), ("created_at", 1)])
    except Exception as e:
        logger.warning("Index project_logs: %s", e)

    logger.info("MongoDB indexes ensured (or skipped if already exist).")
