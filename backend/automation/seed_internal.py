"""
Seed 5 internal (dogfooding) agents: Daily digest, Deployment check, Lead sync, Content refresh, Error report.
Call from server startup when SEED_INTERNAL_AGENTS=1 or run as script.
"""
import os
import logging
from datetime import datetime, timezone

from .constants import INTERNAL_USER_ID
from .schedule import next_run_at

logger = logging.getLogger(__name__)


async def seed_internal_agents(db) -> int:
    """Insert 5 internal agents if not already present. Returns count inserted."""
    existing = await db.user_agents.count_documents({"user_id": INTERNAL_USER_ID})
    if existing >= 5:
        return 0
    now = datetime.now(timezone.utc).isoformat()
    # next_run_at for cron: 9am daily, every 6h, daily, daily, daily
    agents = [
        {
            "id": "internal-daily-digest",
            "user_id": INTERNAL_USER_ID,
            "name": "Daily digest",
            "description": "Internal: generate daily summary (Content Agent).",
            "trigger_type": "schedule",
            "trigger_config": {"type": "schedule", "cron_expression": "0 9 * * *", "next_run_at": None},
            "actions": [{"type": "run_agent", "config": {"agent_name": "Content Agent", "prompt": "Summarize key product updates for today in 3 bullets."}}],
            "enabled": True,
            "created_at": now,
            "updated_at": now,
            "next_run_at": None,
        },
        {
            "id": "internal-deployment-check",
            "user_id": INTERNAL_USER_ID,
            "name": "Deployment health check",
            "description": "Internal: HTTP check every 6h.",
            "trigger_type": "schedule",
            "trigger_config": {"type": "schedule", "cron_expression": "0 */6 * * *", "next_run_at": None},
            "actions": [{"type": "http", "config": {"method": "GET", "url": os.environ.get("CRUCIBAI_HEALTH_URL", "https://api.github.com/zen")}}],
            "enabled": True,
            "created_at": now,
            "updated_at": now,
            "next_run_at": None,
        },
        {
            "id": "internal-lead-sync",
            "user_id": INTERNAL_USER_ID,
            "name": "Lead sync",
            "description": "Internal: webhook-triggered lead sync.",
            "trigger_type": "webhook",
            "trigger_config": {"type": "webhook", "webhook_secret": os.environ.get("INTERNAL_WEBHOOK_SECRET", "internal-lead-sync-secret")},
            "actions": [{"type": "http", "config": {"method": "POST", "url": os.environ.get("LEAD_SYNC_WEBHOOK", "https://httpbin.org/post"), "body": {"source": "crucibai"}}}],
            "enabled": True,
            "created_at": now,
            "updated_at": now,
            "next_run_at": None,
        },
        {
            "id": "internal-content-refresh",
            "user_id": INTERNAL_USER_ID,
            "name": "Content refresh",
            "description": "Internal: daily content refresh (Content Agent).",
            "trigger_type": "schedule",
            "trigger_config": {"type": "schedule", "cron_expression": "0 8 * * *", "next_run_at": None},
            "actions": [{"type": "run_agent", "config": {"agent_name": "Content Agent", "prompt": "Suggest one short blog idea for the product."}}],
            "enabled": True,
            "created_at": now,
            "updated_at": now,
            "next_run_at": None,
        },
        {
            "id": "internal-error-report",
            "user_id": INTERNAL_USER_ID,
            "name": "Error report",
            "description": "Internal: daily error aggregate.",
            "trigger_type": "schedule",
            "trigger_config": {"type": "schedule", "cron_expression": "0 7 * * *", "next_run_at": None},
            "actions": [{"type": "http", "config": {"method": "GET", "url": os.environ.get("CRUCIBAI_API_URL", "http://localhost:8000").rstrip("/") + "/api/health"}}],
            "enabled": True,
            "created_at": now,
            "updated_at": now,
            "next_run_at": None,
        },
    ]
    for a in agents:
        next_ = next_run_at(cron_expression=a["trigger_config"].get("cron_expression"), run_at=a["trigger_config"].get("run_at"))
        if next_:
            a["next_run_at"] = next_.isoformat()
            a["trigger_config"]["next_run_at"] = next_.isoformat()
        await db.user_agents.update_one({"id": a["id"]}, {"$setOnInsert": a}, upsert=True)
    inserted = await db.user_agents.count_documents({"user_id": INTERNAL_USER_ID}) - existing
    logger.info("Seed internal agents: %s existing, %s new", existing, inserted)
    return inserted
