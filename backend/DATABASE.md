# CrucibAI database — PostgreSQL

## Overview

CrucibAI uses **PostgreSQL only** for application data. The `db_pg.py` module exposes a small **document-style API** on JSONB (e.g. `find_one`, `update_one`) so route handlers stay concise.

## Architecture

### `db_pg.py`

```python
db = await get_db()
user = await db.users.find_one({"id": user_id})
await db.users.update_one({"id": user_id}, {"$set": {"name": "Alice"}})
```

### Storage

- **Tables**: one per entity (`users`, `projects`, `chat_history`, …)
- **Rows**: `id` + `doc` (JSONB)
- **Operators**: `$set`, `$inc`, `$gte`, `$lte`, `$in`, `$nin`, `$push`, `$pull`, …

## Setup

Set `DATABASE_URL` in `.env`:

```bash
DATABASE_URL=postgresql://user:password@localhost:5432/crucibai
```

Railway: attach Postgres and set `DATABASE_URL` in service variables.

On startup the app runs migrations and ensures tables exist.

## Local dev

- **Required for auth / guest / builds:** valid `DATABASE_URL` and reachable Postgres.
- Optional: `CRUCIBAI_DEV=1` for relaxed limits while developing.
