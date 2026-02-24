#!/usr/bin/env python3
"""
One-time migration: copy data from MongoDB to PostgreSQL.
Run with: MONGO_URL=... DATABASE_URL=... python -m scripts.migrate_mongo_to_postgres
Collections: users, projects, project_logs, agent_status, chat_history, workspace_env,
  token_ledger, token_usage, tasks, user_agents, agent_runs, referral_codes, referrals,
  api_keys, enterprise_inquiries, backup_codes, mfa_setup_temp, shares, blocked_requests,
  agent_memory, automation_tasks, audit_log, examples.
"""
import asyncio
import json
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _serialize(d):
    """Convert MongoDB doc to JSON-serializable for Postgres doc."""
    out = {}
    for k, v in d.items():
        if k == "_id":
            continue
        if hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        elif isinstance(v, dict):
            out[k] = _serialize(v)
        elif isinstance(v, list):
            out[k] = [_serialize(x) if isinstance(x, dict) else x for x in v]
        else:
            out[k] = v
    return out


async def main():
    mongo_url = os.environ.get("MONGO_URL", "").strip()
    db_name = os.environ.get("DB_NAME", "crucibai")
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not mongo_url:
        print("Set MONGO_URL to source MongoDB.", file=sys.stderr)
        sys.exit(1)
    if not database_url:
        print("Set DATABASE_URL to target PostgreSQL.", file=sys.stderr)
        sys.exit(1)

    from motor.motor_asyncio import AsyncIOMotorClient
    from db_postgres import get_db

    client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=10000)
    mongo_db = client[db_name]
    pg_db = await get_db()

    collections = [
        "users", "projects", "project_logs", "agent_status", "chat_history", "workspace_env",
        "token_ledger", "token_usage", "tasks", "user_agents", "agent_runs", "referral_codes",
        "referrals", "api_keys", "enterprise_inquiries", "backup_codes", "mfa_setup_temp",
        "shares", "blocked_requests", "agent_memory", "automation_tasks", "audit_log", "examples",
    ]
    for coll_name in collections:
        try:
            cursor = mongo_db[coll_name].find({})
            count = 0
            async for doc in cursor:
                d = _serialize(doc)
                if not d:
                    continue
                try:
                    if coll_name == "agent_status":
                        await pg_db.agent_status.insert_one(d)
                    elif coll_name == "backup_codes":
                        await pg_db.backup_codes.insert_one(d)
                    elif coll_name == "audit_log":
                        await pg_db.audit_log.insert_one(d)
                    else:
                        await getattr(pg_db, coll_name).insert_one(d)
                    count += 1
                except Exception as e:
                    print(f"  skip doc {coll_name}: {e}", file=sys.stderr)
            print(f"{coll_name}: {count} docs")
        except Exception as e:
            print(f"{coll_name}: error {e}", file=sys.stderr)
    from db_postgres import close_pool
    await close_pool()
    client.close()
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
