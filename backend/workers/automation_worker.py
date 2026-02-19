"""
Automation worker: polls user_agents (schedule) and automation_tasks (legacy), executes runs, updates next_run_at.
Run as: python -m backend.workers.automation_worker
Requires: MONGO_URL, DB_NAME; optional CRUCIBAI_API_URL, CRUCIBAI_INTERNAL_TOKEN for run_agent actions.
"""
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

# Add parent to path so backend imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from motor.motor_asyncio import AsyncIOMotorClient

from automation.constants import (
    CREDITS_PER_AGENT_RUN,
    INTERNAL_USER_ID,
    MAX_CONCURRENT_RUNS_PER_USER,
    MAX_RUNS_PER_HOUR_PER_USER,
)
from automation.executor import run_actions
from automation.schedule import next_run_at, is_one_time

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 60
COLLECTION_AGENTS = "user_agents"
COLLECTION_RUNS = "agent_runs"
COLLECTION_LEGACY_TASKS = "automation_tasks"


async def get_db():
    """Connect to MongoDB (same as server)."""
    mongo_url = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
    db_name = os.environ.get("DB_NAME", "crucibai")
    client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=5000)
    return client[db_name]


async def check_credits(db, user_id: str) -> bool:
    """True if user has at least CREDITS_PER_AGENT_RUN (or is internal)."""
    if user_id == INTERNAL_USER_ID:
        return True
    user = await db.users.find_one({"id": user_id}, {"credit_balance": 1, "token_balance": 1})
    if not user:
        return False
    cred = user.get("credit_balance")
    if cred is None:
        cred = int((user.get("token_balance") or 0) // 1000)
    return cred >= CREDITS_PER_AGENT_RUN


async def deduct_credits(db, user_id: str, amount: int = CREDITS_PER_AGENT_RUN) -> None:
    """Deduct credits for agent run (internal user skipped)."""
    if user_id == INTERNAL_USER_ID:
        return
    await db.users.update_one({"id": user_id}, {"$inc": {"credit_balance": -amount}})


async def concurrent_runs_count(db, user_id: str) -> int:
    """Count runs in status=running for this user."""
    return await db.agent_runs.count_documents({"user_id": user_id, "status": "running"})


async def runs_this_hour(db, user_id: str) -> int:
    """Count runs started in the last hour."""
    from datetime import timedelta
    since = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    return await db.agent_runs.count_documents({"user_id": user_id, "started_at": {"$gte": since}})


async def process_due_agents(db):
    """Find due schedule agents, create run, execute, update."""
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    cursor = db[COLLECTION_AGENTS].find({
        "enabled": True,
        "trigger_type": "schedule",
        "$or": [
            {"next_run_at": {"$lte": now_iso}},
            {"next_run_at": None, "run_at": {"$lte": now_iso}},
        ],
    })
    agents = await cursor.to_list(length=100)

    for agent in agents:
        agent_id = agent.get("id")
        user_id = agent.get("user_id") or ""
        if not agent_id or not user_id:
            continue

        if user_id != INTERNAL_USER_ID:
            if await concurrent_runs_count(db, user_id) >= MAX_CONCURRENT_RUNS_PER_USER:
                logger.warning("User %s over concurrent run limit, skipping agent %s", user_id, agent_id)
                continue
            if await runs_this_hour(db, user_id) >= MAX_RUNS_PER_HOUR_PER_USER:
                logger.warning("User %s over hourly run limit, skipping agent %s", user_id, agent_id)
                continue
            if not await check_credits(db, user_id):
                logger.warning("User %s insufficient credits, skipping agent %s", user_id, agent_id)
                run_id = str(__import__("uuid").uuid4())
                await db[COLLECTION_RUNS].insert_one({
                    "id": run_id, "agent_id": agent_id, "user_id": user_id,
                    "triggered_at": now_iso, "triggered_by": "schedule",
                    "status": "failed", "started_at": now_iso, "finished_at": now_iso,
                    "error_message": "Insufficient credits", "output_summary": {}, "log_lines": [],
                })
                continue

        run_id = str(__import__("uuid").uuid4())
        await db[COLLECTION_RUNS].insert_one({
            "id": run_id, "agent_id": agent_id, "user_id": user_id,
            "triggered_at": now_iso, "triggered_by": "schedule",
            "status": "running", "started_at": now_iso,
            "output_summary": {}, "log_lines": [],
        })
        await deduct_credits(db, user_id)

        try:
            steps_context = []
            status, output_summary, log_lines, _ = await run_actions(
                agent, user_id, run_id, steps_context, run_agent_callback=None,
            )
        except Exception as e:
            logger.exception("Executor failed for run %s", run_id)
            status = "failed"
            output_summary = {"error": str(e)}
            log_lines = [f"[ERROR] {e}"]

        finished = datetime.now(timezone.utc).isoformat()
        await db[COLLECTION_RUNS].update_one(
            {"id": run_id},
            {"$set": {
                "status": status,
                "finished_at": finished,
                "output_summary": output_summary,
                "log_lines": log_lines[-1000:],
            }},
        )

        trigger_config = agent.get("trigger_config") or {}
        if is_one_time(trigger_config):
            await db[COLLECTION_AGENTS].update_one({"id": agent_id}, {"$set": {"next_run_at": None, "enabled": False}})
        else:
            next_ = next_run_at(
                cron_expression=trigger_config.get("cron_expression"),
                run_at=trigger_config.get("run_at"),
                from_time=datetime.fromisoformat(finished.replace("Z", "+00:00")),
            )
            await db[COLLECTION_AGENTS].update_one(
                {"id": agent_id},
                {"$set": {"next_run_at": next_.isoformat() if next_ else None, "updated_at": finished}},
            )
        logger.info("Run %s finished with status=%s", run_id, status)


async def process_legacy_automation_tasks(db):
    """Process automation_tasks (legacy) with run_at <= now; create run and execute once."""
    now = datetime.now(timezone.utc).isoformat()
    cursor = db[COLLECTION_LEGACY_TASKS].find({"status": "scheduled", "run_at": {"$lte": now}})
    tasks = await cursor.to_list(length=50)
    for task in tasks:
        task_id = task.get("id")
        user_id = (task.get("user_id") or "").strip() or INTERNAL_USER_ID
        if not task_id:
            continue
        # Build a one-shot agent doc: single run_agent action with task prompt
        agent_doc = {
            "id": f"legacy-{task_id}",
            "user_id": user_id,
            "actions": [{"type": "run_agent", "config": {"agent_name": "Content Agent", "prompt": task.get("prompt", "")}}],
        }
        run_id = str(__import__("uuid").uuid4())
        await db[COLLECTION_RUNS].insert_one({
            "id": run_id, "agent_id": f"legacy-{task_id}", "user_id": user_id,
            "triggered_at": now, "triggered_by": "schedule",
            "status": "running", "started_at": now, "output_summary": {}, "log_lines": [],
        })
        if user_id != INTERNAL_USER_ID and await check_credits(db, user_id):
            await deduct_credits(db, user_id)
        try:
            status, output_summary, log_lines, _ = await run_actions(agent_doc, user_id, run_id, [], run_agent_callback=None)
        except Exception as e:
            status, output_summary, log_lines = "failed", {"error": str(e)}, [str(e)]
        finished = datetime.now(timezone.utc).isoformat()
        await db[COLLECTION_RUNS].update_one(
            {"id": run_id},
            {"$set": {"status": status, "finished_at": finished, "output_summary": output_summary, "log_lines": log_lines[-1000:]}},
        )
        await db[COLLECTION_LEGACY_TASKS].update_one({"id": task_id}, {"$set": {"status": "completed", "completed_at": finished}})
        logger.info("Legacy task %s run %s status=%s", task_id, run_id, status)


async def main_loop():
    db = await get_db()
    logger.info("Automation worker started; polling every %s s", POLL_INTERVAL_SECONDS)
    while True:
        try:
            await process_due_agents(db)
            await process_legacy_automation_tasks(db)
        except Exception as e:
            logger.exception("Poll cycle failed: %s", e)
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(main_loop())
