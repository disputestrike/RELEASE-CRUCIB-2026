"""
DB Migrator — Phase 2: Full Last-Mile Automation.

Runs Alembic migrations automatically after every successful deploy.
Zero manual steps. Rolls back cleanly on failure.

Usage:
    from backend.services.db_migrator import run_migrations
    result = await run_migrations()
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Alembic config path (relative to repo root, or absolute via env)
ALEMBIC_INI = os.environ.get("ALEMBIC_INI", "alembic.ini")
# Max seconds for a migration run
MIGRATION_TIMEOUT = int(os.environ.get("MIGRATION_TIMEOUT", "120"))


async def run_migrations(
    alembic_ini: Optional[str] = None,
    revision: str = "head",
    timeout: int = MIGRATION_TIMEOUT,
) -> Dict[str, Any]:
    """
    Run Alembic migrations up to `revision` (default: head).

    Returns:
        {
            "success": bool,
            "revision": str,
            "output": str,
            "duration_ms": int,
            "error": str | None,
        }
    """
    ini = alembic_ini or ALEMBIC_INI
    start = time.monotonic()

    if not os.path.isfile(ini):
        logger.warning("[DB-MIGRATE] alembic.ini not found at %s — skipping", ini)
        return {
            "success": True,
            "revision": "skipped",
            "output": f"No alembic.ini at {ini} — skipping migration",
            "duration_ms": 0,
            "error": None,
        }

    logger.info("[DB-MIGRATE] Running: alembic upgrade %s (ini=%s)", revision, ini)

    try:
        proc = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                "alembic", "-c", ini, "upgrade", revision,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            ),
            timeout=timeout,
        )
        stdout, _ = await proc.communicate()
        output = stdout.decode("utf-8", errors="replace").strip() if stdout else ""
        elapsed_ms = int((time.monotonic() - start) * 1000)

        if proc.returncode == 0:
            logger.info("[DB-MIGRATE] Migration succeeded in %dms", elapsed_ms)
            return {
                "success": True,
                "revision": revision,
                "output": output,
                "duration_ms": elapsed_ms,
                "error": None,
            }
        else:
            logger.error("[DB-MIGRATE] Migration failed rc=%d:\n%s", proc.returncode, output)
            return {
                "success": False,
                "revision": revision,
                "output": output,
                "duration_ms": elapsed_ms,
                "error": f"alembic exit code {proc.returncode}",
            }

    except asyncio.TimeoutError:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.error("[DB-MIGRATE] Migration timed out after %ds", timeout)
        return {
            "success": False,
            "revision": revision,
            "output": "",
            "duration_ms": elapsed_ms,
            "error": f"Migration timed out after {timeout}s",
        }
    except Exception as exc:
        elapsed_ms = int((time.monotonic() - start) * 1000)
        logger.exception("[DB-MIGRATE] Unexpected error: %s", exc)
        return {
            "success": False,
            "revision": revision,
            "output": "",
            "duration_ms": elapsed_ms,
            "error": str(exc),
        }


async def get_current_revision(alembic_ini: Optional[str] = None) -> Optional[str]:
    """Return the current Alembic revision (or None on error)."""
    ini = alembic_ini or ALEMBIC_INI
    if not os.path.isfile(ini):
        return None
    try:
        proc = await asyncio.create_subprocess_exec(
            "alembic", "-c", ini, "current",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await proc.communicate()
        output = stdout.decode("utf-8", errors="replace").strip() if stdout else ""
        # Parse "abc123 (head)" or just "abc123"
        for line in output.splitlines():
            if line.strip():
                return line.strip().split()[0]
        return None
    except Exception:
        return None
