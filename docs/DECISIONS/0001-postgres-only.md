# ADR 0001: PostgreSQL Only

## Status

Accepted

## Context

CrucibAI previously carried MongoDB-era documentation and CI configuration, while the current backend code and deployment guide are PostgreSQL-first. Keeping both paths visible creates setup confusion and increases the chance that CI or production uses a database path that does not match the real app.

## Decision

Use PostgreSQL as the only system of record for CrucibAI.

Use supporting systems only for specific roles:

- `pgvector` for semantic memory and retrieval.
- Redis for queueing, rate limits, locks, and cache where needed.
- Object storage for large generated artifacts when database storage is no longer appropriate.

Do not add MongoDB back to the primary application path.

## Consequences

- Primary docs and CI must use `DATABASE_URL`, not `MONGO_URL` or `DB_NAME`.
- Tests must provision PostgreSQL when they need a database.
- Any remaining MongoDB wording should be treated as legacy drift unless a historical note explicitly labels it that way.
