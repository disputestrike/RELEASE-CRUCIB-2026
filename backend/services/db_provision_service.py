"""
Auto-provision a Railway Postgres database for a job that needs one.
Called by the orchestrator when it detects a DB requirement in the plan.
Uses Railway's public API to create a Postgres plugin in the same project.
Falls back to a shared dev DB if Railway token is not set.
"""
import logging
import os
import httpx

logger = logging.getLogger(__name__)

RAILWAY_TOKEN = os.environ.get("RAILWAY_TOKEN", "")
RAILWAY_API = "https://backboard.railway.app/graphql/v2"

PROVISION_GQL = """
mutation provisionDatabase($projectId: String!, $serviceId: String) {
  pluginCreate(
    input: {
      projectId: $projectId
      name: "postgresql"
      friendlyName: "crucibai-db"
    }
  ) {
    id
    name
    variables {
      DATABASE_URL
    }
  }
}
"""


async def provision_postgres_for_job(job_id: str, railway_project_id: str | None = None) -> dict:
    """
    Provision a Postgres DB for a job. Returns connection info dict.
    If Railway is not configured, returns a stub for local dev.
    """
    project_id = railway_project_id or os.environ.get("RAILWAY_PROJECT_ID", "")

    if not RAILWAY_TOKEN or not project_id:
        logger.warning("db_provision: Railway not configured — returning shared dev DB stub")
        shared_url = os.environ.get("DATABASE_URL", "postgresql://localhost/crucibai_dev")
        return {
            "provisioned": False,
            "database_url": shared_url,
            "source": "shared_dev",
            "job_id": job_id,
        }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                RAILWAY_API,
                headers={
                    "Authorization": f"Bearer {RAILWAY_TOKEN}",
                    "Content-Type": "application/json",
                },
                json={
                    "query": PROVISION_GQL,
                    "variables": {"projectId": project_id},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            plugin = data.get("data", {}).get("pluginCreate", {})
            db_url = (plugin.get("variables") or {}).get("DATABASE_URL", "")
            logger.info("db_provision: provisioned Postgres for job %s plugin_id=%s", job_id, plugin.get("id"))
            return {
                "provisioned": True,
                "database_url": db_url,
                "plugin_id": plugin.get("id"),
                "source": "railway",
                "job_id": job_id,
            }
    except Exception as e:
        logger.error("db_provision: failed for job %s: %s", job_id, e)
        fallback = os.environ.get("DATABASE_URL", "")
        return {
            "provisioned": False,
            "database_url": fallback,
            "source": "fallback",
            "error": str(e),
            "job_id": job_id,
        }


def job_needs_database(plan: dict) -> bool:
    """
    Inspect the plan steps to determine if a DB is required.
    Checks for database agent, Prisma, Drizzle, Supabase, or ORM keywords.
    """
    if not plan:
        return False
    DB_SIGNALS = {"database", "prisma", "drizzle", "supabase", "postgres", "mysql", "sqlite", "orm", "migration"}
    steps = plan.get("steps", []) or []
    for step in steps:
        key = (step.get("step_key") or "").lower()
        agent = (step.get("agent_name") or "").lower()
        desc = (step.get("description") or "").lower()
        combined = f"{key} {agent} {desc}"
        if any(sig in combined for sig in DB_SIGNALS):
            return True
    goal = (plan.get("goal") or "").lower()
    if any(sig in goal for sig in DB_SIGNALS):
        return True
    return False
