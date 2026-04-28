from __future__ import annotations

import os
from typing import Any

from fastapi import HTTPException


_PRODUCTION_VALUES = {"prod", "production", "railway"}


def is_production_runtime() -> bool:
    """Return true when production paths must not fall back to local files."""
    for key in ("RAILWAY_ENVIRONMENT", "CRUCIBAI_ENV", "ENVIRONMENT", "APP_ENV", "NODE_ENV"):
        if str(os.environ.get(key) or "").strip().lower() in _PRODUCTION_VALUES:
            return True
    return False


def require_canonical_db(pool: Any, *, action: str) -> Any:
    """Require PostgreSQL-backed canonical state in production.

    Local tests and developer runs can still exercise the file-backed compatibility
    runtime, but production must fail loudly instead of creating jobs that only
    exist on disk and drift away from the preview/proof contracts.
    """
    if pool is not None:
        return pool
    if is_production_runtime():
        raise HTTPException(
            status_code=503,
            detail={
                "error": "canonical_state_unavailable",
                "failure_reason": "database_unavailable",
                "message": f"{action} requires PostgreSQL canonical runtime state.",
                "recovery": "Check DATABASE_URL, migrations, and backend DB connectivity before retrying.",
            },
        )
    return None
