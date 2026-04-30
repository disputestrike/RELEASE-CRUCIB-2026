"""Idempotent sequential SQL migration runner.

Improvements over the original ``db_pg.run_migrations()``:

* Maintains a ``schema_migrations`` table that records which files have
  already been applied — files are **not** re-executed on every startup.
* Migration 010 creates the tracking table itself, so the very first run
  bootstraps the tracker automatically.
* Falls back gracefully when the tracker table doesn't exist yet (applies
  all files, then creates the table).
* The original ``run_migrations()`` is preserved for compatibility; this
  module adds ``run_migrations_idempotent()`` which server.py calls on startup.

Usage (server.py startup)::

    from ....services.migration_runner import run_migrations_idempotent    await run_migrations_idempotent()
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"


def _strip_leading_sql_comments(stmt: str) -> str:
    lines = []
    for line in stmt.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def _split_sql_statements(content: str) -> list[str]:
    """Split SQL into statements without breaking quoted strings or DO $$ blocks."""
    statements: list[str] = []
    current: list[str] = []
    i = 0
    in_single_quote = False
    in_double_quote = False
    in_line_comment = False
    in_block_comment = False
    dollar_tag: str | None = None
    length = len(content)

    while i < length:
        char = content[i]
        next_char = content[i + 1] if i + 1 < length else ""

        if in_line_comment:
            current.append(char)
            if char == "\n":
                in_line_comment = False
            i += 1
            continue

        if in_block_comment:
            current.append(char)
            if char == "*" and next_char == "/":
                current.append(next_char)
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue

        if dollar_tag is not None:
            if content.startswith(dollar_tag, i):
                current.append(dollar_tag)
                i += len(dollar_tag)
                dollar_tag = None
            else:
                current.append(char)
                i += 1
            continue

        if in_single_quote:
            current.append(char)
            if char == "'" and next_char == "'":
                current.append(next_char)
                i += 2
                continue
            if char == "'":
                in_single_quote = False
            i += 1
            continue

        if in_double_quote:
            current.append(char)
            if char == '"':
                in_double_quote = False
            i += 1
            continue

        if char == "-" and next_char == "-":
            current.extend((char, next_char))
            in_line_comment = True
            i += 2
            continue

        if char == "/" and next_char == "*":
            current.extend((char, next_char))
            in_block_comment = True
            i += 2
            continue

        if char == "'":
            current.append(char)
            in_single_quote = True
            i += 1
            continue

        if char == '"':
            current.append(char)
            in_double_quote = True
            i += 1
            continue

        if char == "$":
            tag_end = content.find("$", i + 1)
            if tag_end != -1:
                candidate = content[i : tag_end + 1]
                if all(c == "_" or c.isalnum() or c == "$" for c in candidate):
                    current.append(candidate)
                    dollar_tag = candidate
                    i = tag_end + 1
                    continue

        if char == ";":
            statement = _strip_leading_sql_comments("".join(current))
            if statement:
                statements.append(statement)
            current = []
            i += 1
            continue

        current.append(char)
        i += 1

    trailing = _strip_leading_sql_comments("".join(current))
    if trailing:
        statements.append(trailing)
    return statements


async def _get_pool():
    """Import and return the asyncpg connection pool from db_pg."""
    from ....db_pg import get_pg_pool  # type: ignore[import]
    return await get_pg_pool()


async def _applied_migrations(pool) -> set[str]:
    """Return the set of already-applied migration filenames."""
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT filename FROM schema_migrations")
            return {row["filename"] for row in rows}
    except Exception:
        # Table doesn't exist yet — treat as empty set (first run)
        return set()


async def _record_migration(pool, filename: str) -> None:
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO schema_migrations (filename) VALUES ($1) ON CONFLICT DO NOTHING",
                filename,
            )
    except Exception as exc:
        logger.debug("Could not record migration %s: %s", filename, exc)


async def _execute_file(pool, path: Path) -> tuple[int, int]:
    """Execute all statements in *path*.  Returns ``(ok, skipped)``."""
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("Migration %s: could not read file: %s", path.name, exc)
        return 0, 0

    statements = _split_sql_statements(content)
    ok = fail = 0
    for stmt in statements:
        if not stmt:
            continue
        try:
            async with pool.acquire() as conn:
                await conn.execute(stmt)
            ok += 1
        except Exception as exc:
            logger.debug("Migration %s stmt skipped: %s", path.name, str(exc)[:120])
            fail += 1
    return ok, fail


async def run_migrations_idempotent() -> None:
    """Apply all pending migrations exactly once.

    Files that have already been recorded in ``schema_migrations`` are
    skipped.  New files (sorted by name) are executed and then recorded.
    """
    if not os.environ.get("DATABASE_URL"):
        logger.debug("DATABASE_URL not set — skipping migrations")
        return

    try:
        pool = await _get_pool()
    except Exception as exc:
        logger.warning("Migration runner: could not get DB pool: %s", exc)
        return

    all_files = sorted(
        f for f in _MIGRATIONS_DIR.iterdir() if f.is_file() and f.suffix == ".sql"
    )

    applied = await _applied_migrations(pool)
    pending = [f for f in all_files if f.name not in applied]

    if not pending:
        logger.info("Migrations: all %d files already applied", len(all_files))
        return

    logger.info(
        "Migrations: %d total, %d already applied, %d pending",
        len(all_files),
        len(applied),
        len(pending),
    )

    for migration_file in pending:
        ok, fail = await _execute_file(pool, migration_file)
        logger.info("Migration %s: %d ok, %d skipped", migration_file.name, ok, fail)
        await _record_migration(pool, migration_file.name)

    logger.info("Migrations: %d pending files applied", len(pending))
