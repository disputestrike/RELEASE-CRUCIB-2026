# Postgres-Only Migration

Last updated: 2026-04-08

## Decision

CrucibAI uses PostgreSQL as the only primary database.

MongoDB is not part of the target architecture. Any remaining MongoDB references in older docs, historical reports, scripts, comments, or test labels are drift unless a maintainer explicitly re-approves them.

## Target Stack

- PostgreSQL: system of record for users, projects, jobs, tasks, events, proof, billing state, and app metadata.
- PostgreSQL JSONB: compatibility layer for document-shaped records while the codebase is being cleaned up.
- pgvector: planned vector memory/search extension when semantic retrieval is hardened.
- Redis: queue/cache acceleration, not primary durable state.
- Object storage: planned home for generated file artifacts, deploy bundles, logs, and proof bundles that should not live inside database rows forever.

## Migration Rules

- New database work must use `DATABASE_URL`; do not add `MONGO_URL` or `DB_NAME` requirements.
- CI and Railway docs must provision Postgres and Redis, not MongoDB.
- Any compatibility wrapper named like a document collection must still persist to Postgres.
- Generated app schemas should be explicit SQL migrations when possible.
- Tenant and ownership checks must be enforced in application queries and backed by Postgres-level controls where practical.

## Cleanup Backlog

- Audit secondary markdown files for MongoDB setup instructions and either update or mark them historical.
- Add a pgvector ADR before introducing vector memory as a required dependency.
- Move large generated artifacts out of Postgres rows into object storage with database metadata pointers.
- Add migration smoke tests that run on clean Postgres and upgraded Postgres.

## Acceptance

This migration is complete when a fresh developer or Railway environment can boot from `DATABASE_URL` and `REDIS_URL` alone, tests no longer require MongoDB configuration, and primary setup docs no longer instruct users to configure MongoDB.
