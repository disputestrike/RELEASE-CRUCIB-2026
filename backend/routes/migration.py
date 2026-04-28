"""
/api/migrations/* — codebase migration endpoints (CF5).

Persists migration_runs, migration_file_maps, source_to_target_mappings rows
(via db_pg) and delegates to services.migration_engine for planning and
execution.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/migrations", tags=["migrations"])


def _get_auth():
    try:
        from ..server import get_current_user
        return get_current_user
    except ImportError:
        try:
            from server import get_current_user  # type: ignore
            return get_current_user
        except ImportError:
            async def _noop_auth():
                return {}
            return _noop_auth


def _plan_to_dict(plan: Any) -> Dict[str, Any]:
    try:
        return asdict(plan)
    except Exception:
        return {
            "migration_id": getattr(plan, "migration_id", None),
            "strategy": getattr(plan, "strategy", None),
            "source_root": getattr(plan, "source_root", None),
            "target_root": getattr(plan, "target_root", None),
            "summary": getattr(plan, "summary", None),
            "file_actions": [asdict(fa) for fa in getattr(plan, "file_actions", [])],
            "new_files": getattr(plan, "new_files", []),
            "behavior_checklist": getattr(plan, "behavior_checklist", []),
            "test_commands": getattr(plan, "test_commands", []),
        }


async def _persist_run(db: Any, *, run: Dict[str, Any]) -> None:
    """Insert a migration_runs row if the table exists."""
    if db is None:
        return
    try:
        await db.execute(
            """
            INSERT INTO migration_runs
                (id, user_id, thread_id, strategy, source_path, target_path,
                 status, plan, summary, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, $9::jsonb, NOW())
            ON CONFLICT (id) DO UPDATE SET
                status = EXCLUDED.status,
                summary = EXCLUDED.summary
            """,
            run["id"],
            run.get("user_id"),
            run.get("thread_id"),
            run.get("strategy"),
            run.get("source_root"),
            run.get("target_root"),
            run.get("status", "planned"),
            json.dumps(run.get("plan") or {}),
            json.dumps(run.get("result") or {}),
        )
    except Exception as exc:
        logger.warning("migration_runs persist failed (non-fatal): %s", exc)


async def _persist_file_map(db: Any, *, migration_id: str, file_actions: List[Dict[str, Any]]) -> None:
    if db is None or not file_actions:
        return
    try:
        for fa in file_actions:
            _fm_id = f"{migration_id}:{fa.get('source_path')}"
            await db.execute(
                """
                INSERT INTO migration_file_maps
                    (id, migration_id, source_path, target_path, action, notes, created_at)
                VALUES ($1, $2, $3, $4, $5, $6, NOW())
                ON CONFLICT (id) DO NOTHING
                """,
                _fm_id,
                migration_id,
                fa.get("source_path"),
                fa.get("target_path"),
                fa.get("action"),
                fa.get("notes"),
            )
    except Exception as exc:
        logger.warning("migration_file_maps persist failed (non-fatal): %s", exc)


@router.post("/plan")
async def plan_migration(
    request: Request,
    user: dict = Depends(_get_auth()),
) -> Dict[str, Any]:
    """Produce a migration plan (no side effects)."""
    from ..services.migration_engine import migration_engine

    body = await request.json()
    source_root = body.get("source_root")
    target_root = body.get("target_root")
    if not source_root or not target_root:
        raise HTTPException(status_code=400, detail="source_root and target_root are required")

    strategy = body.get("strategy", "merge_many_to_fewer")
    thread_id = body.get("thread_id")
    user_id = user.get("id") or user.get("sub", "anon")

    try:
        plan = migration_engine.plan(
            source_root=source_root,
            target_root=target_root,
            strategy=strategy,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"migration plan failed: {exc}")

    plan_dict = _plan_to_dict(plan)

    db = None
    try:
        from ..db_pg import get_db
        db = await get_db()
    except Exception:
        db = None

    await _persist_run(
        db,
        run={
            "id": plan_dict.get("migration_id"),
            "user_id": user_id,
            "thread_id": thread_id,
            "strategy": strategy,
            "source_root": source_root,
            "target_root": target_root,
            "status": "planned",
            "plan": plan_dict,
        },
    )
    await _persist_file_map(
        db,
        migration_id=plan_dict.get("migration_id"),
        file_actions=plan_dict.get("file_actions") or [],
    )

    return {"plan": plan_dict, "status": "planned"}


@router.post("/execute")
async def execute_migration(
    request: Request,
    user: dict = Depends(_get_auth()),
) -> Dict[str, Any]:
    """Execute a previously produced plan (or a freshly produced one).

    Body must contain EITHER `migration_id` pointing to a stored plan (not yet
    implemented — requires full plan round-trip) OR the full plan payload
    under `plan` to run without round-trip.  `dry_run=true` by default.
    """
    from ..services.migration_engine import (
        MigrationPlan,
        FileAction,
        migration_engine,
    )

    body = await request.json()
    plan_payload = body.get("plan")
    dry_run = bool(body.get("dry_run", True))
    user_id = user.get("id") or user.get("sub", "anon")

    if not plan_payload:
        raise HTTPException(
            status_code=400,
            detail="plan payload is required (produce one via /api/migrations/plan first)",
        )

    try:
        plan = MigrationPlan(
            migration_id=plan_payload["migration_id"],
            strategy=plan_payload["strategy"],
            source_root=plan_payload["source_root"],
            target_root=plan_payload["target_root"],
            file_actions=[FileAction(**fa) for fa in plan_payload.get("file_actions", [])],
            new_files=plan_payload.get("new_files", []),
            behavior_checklist=plan_payload.get("behavior_checklist", []),
            test_commands=plan_payload.get("test_commands", []),
            summary=plan_payload.get("summary", ""),
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"invalid plan payload: {exc}")

    try:
        result = migration_engine.execute_plan(plan, dry_run=dry_run)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"migration execute failed: {exc}")

    result_dict = asdict(result) if hasattr(result, "__dataclass_fields__") else dict(result)

    db = None
    try:
        from ..db_pg import get_db
        db = await get_db()
    except Exception:
        db = None

    await _persist_run(
        db,
        run={
            "id": plan.migration_id,
            "user_id": user_id,
            "strategy": plan.strategy,
            "source_root": plan.source_root,
            "target_root": plan.target_root,
            "status": result_dict.get("status", "completed"),
            "plan": _plan_to_dict(plan),
            "result": result_dict,
        },
    )

    return {"result": result_dict, "migration_id": plan.migration_id}


@router.get("/{migration_id}")
async def get_migration(
    migration_id: str,
    user: dict = Depends(_get_auth()),
) -> Dict[str, Any]:
    """Return a migration run row."""
    try:
        from ..db_pg import get_db
        db = await get_db()
    except Exception:
        db = None

    if db is None:
        raise HTTPException(status_code=503, detail="database unavailable")

    try:
        row = await db.fetchrow(
            "SELECT id, status, strategy, source_path, target_path, plan, summary, created_at "
            "FROM migration_runs WHERE id = $1",
            migration_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"fetch migration failed: {exc}")
    if not row:
        raise HTTPException(status_code=404, detail="migration not found")
    return dict(row)


@router.get("/{migration_id}/file-map")
async def get_migration_file_map(
    migration_id: str,
    user: dict = Depends(_get_auth()),
) -> Dict[str, Any]:
    """Return the source→target file map for a migration run."""
    try:
        from ..db_pg import get_db
        db = await get_db()
    except Exception:
        db = None

    if db is None:
        raise HTTPException(status_code=503, detail="database unavailable")

    try:
        rows = await db.fetch(
            "SELECT source_path, target_path, action, notes FROM migration_file_maps "
            "WHERE migration_id = $1 ORDER BY source_path",
            migration_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"fetch file-map failed: {exc}")

    return {"migration_id": migration_id, "file_map": [dict(r) for r in rows]}
