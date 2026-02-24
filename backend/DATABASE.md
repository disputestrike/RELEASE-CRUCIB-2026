# Database (CrucibAI backend)

## Full migration to PostgreSQL

The app uses **PostgreSQL only** (no MongoDB in production).

- **DATABASE_URL** (required): PostgreSQL connection string (`postgresql://...`). Set in `.env`.
- **MySQL, TiDB, or any other database are NOT supported.** The code uses `asyncpg` (PostgreSQL-only).

## Schema

All tables use a `doc` JSONB column for the document; primary keys and indexes are defined in `backend/migrations/001_full_schema.sql`. Tables: users, projects, project_logs, agent_status, chat_history, workspace_env, token_ledger, token_usage, tasks, user_agents, agent_runs, referral_codes, referrals, api_keys, enterprise_inquiries, backup_codes, mfa_setup_temp, shares, blocked_requests, agent_memory, automation_tasks, audit_log, examples, monitoring_events.

## One-time migration from MongoDB

If you have existing data in MongoDB, run once:

```bash
MONGO_URL=mongodb://... DATABASE_URL=postgresql://... python -m scripts.migrate_mongo_to_postgres
```

Then run the app with **DATABASE_URL** only (no MONGO_URL).
