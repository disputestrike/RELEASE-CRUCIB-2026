"""CF11 — Onboarding time-to-first-preview instrumentation.

Captures the single most important funnel metric for competitive positioning:
how fast can a brand-new user go from prompt to a clickable preview?

Target: < 60 seconds.  Bolt.new and Lovable advertise sub-minute.

Endpoints
---------
POST /api/onboard/start           — records goal + started_at, returns onboard_id
POST /api/onboard/first-preview   — records preview_ready_at, computes elapsed_seconds
GET  /api/onboard/{id}            — fetch a specific onboard event
GET  /api/onboard/metrics         — aggregate: p50 / p90 / sub_60s_rate over last 7d

Storage: onboard_events table (created lazily via CREATE TABLE IF NOT EXISTS
so the route is self-sufficient and does not require a new migration).
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/onboard", tags=["onboard"])


def _get_auth():
    try:
        from backend.server import get_current_user
        return get_current_user
    except Exception:
        from fastapi import Request

        async def noop(request: Request = None):  # type: ignore[override]
            return {"id": "anonymous"}

        return noop


async def _get_db():
    """Return a DB pool or None if Postgres is unreachable.

    We never raise — the route should degrade to an in-memory response so
    demos/CI without Postgres can still exercise the API.
    """
    try:
        from backend.db_pg import get_db  # type: ignore
        return await get_db()
    except Exception as exc:
        logger.warning("onboard _get_db fell back to None: %s", exc)
        return None


async def _ensure_table(db):
    """Create onboard_events table on-demand (idempotent)."""
    if db is None:
        return
    try:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS onboard_events (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                goal TEXT,
                started_at TIMESTAMPTZ NOT NULL,
                preview_ready_at TIMESTAMPTZ,
                elapsed_seconds DOUBLE PRECISION,
                metadata JSONB
            );
            CREATE INDEX IF NOT EXISTS ix_onboard_events_user_id ON onboard_events (user_id);
            CREATE INDEX IF NOT EXISTS ix_onboard_events_started_at ON onboard_events (started_at DESC);
            """
        )
    except Exception as exc:  # pragma: no cover — degraded mode
        logger.warning("onboard_events table ensure failed: %s", exc)


# ── Pydantic ──────────────────────────────────────────────────────────────────


class OnboardStartRequest(BaseModel):
    goal: str = Field(..., min_length=1, max_length=2000)
    metadata: Optional[dict] = None


class OnboardPreviewRequest(BaseModel):
    onboard_id: str


class OnboardEventOut(BaseModel):
    id: str
    user_id: Optional[str]
    goal: Optional[str]
    started_at: datetime
    preview_ready_at: Optional[datetime]
    elapsed_seconds: Optional[float]
    under_target: Optional[bool]  # True iff elapsed < 60s

    @classmethod
    def from_row(cls, row) -> "OnboardEventOut":
        elapsed = row.get("elapsed_seconds") if isinstance(row, dict) else getattr(row, "elapsed_seconds", None)
        return cls(
            id=row["id"],
            user_id=row.get("user_id"),
            goal=row.get("goal"),
            started_at=row["started_at"],
            preview_ready_at=row.get("preview_ready_at"),
            elapsed_seconds=elapsed,
            under_target=(elapsed is not None and elapsed < 60.0),
        )


# ── Routes ────────────────────────────────────────────────────────────────────


@router.post("/start")
async def onboard_start(
    body: OnboardStartRequest,
    user: dict = Depends(_get_auth()),
):
    db = await _get_db()
    await _ensure_table(db)
    onboard_id = f"onb_{uuid.uuid4().hex[:12]}"
    started_at = datetime.now(timezone.utc)

    if db is not None:
        try:
            await db.execute(
                "INSERT INTO onboard_events (id, user_id, goal, started_at, metadata) "
                "VALUES ($1, $2, $3, $4, $5)",
                onboard_id,
                user.get("id"),
                body.goal,
                started_at,
                body.metadata or {},
            )
        except Exception as exc:
            logger.warning("onboard start insert failed: %s", exc)

    return {
        "id": onboard_id,
        "started_at": started_at.isoformat(),
        "target_seconds": 60.0,
        "goal": body.goal,
    }


@router.post("/first-preview")
async def onboard_first_preview(
    body: OnboardPreviewRequest,
    user: dict = Depends(_get_auth()),
):
    db = await _get_db()
    await _ensure_table(db)
    preview_ready_at = datetime.now(timezone.utc)

    if db is None:
        return {
            "id": body.onboard_id,
            "preview_ready_at": preview_ready_at.isoformat(),
            "elapsed_seconds": None,
            "under_target": None,
            "degraded": True,
        }

    row = None
    try:
        row = await db.fetchrow(
            "SELECT started_at FROM onboard_events WHERE id=$1",
            body.onboard_id,
        )
    except Exception as exc:
        logger.warning("onboard preview fetchrow failed: %s", exc)

    if row is None:
        raise HTTPException(status_code=404, detail=f"onboard_id not found: {body.onboard_id}")

    started_at = row["started_at"]
    elapsed = (preview_ready_at - started_at).total_seconds()
    under = elapsed < 60.0

    try:
        await db.execute(
            "UPDATE onboard_events "
            "SET preview_ready_at=$1, elapsed_seconds=$2 "
            "WHERE id=$3",
            preview_ready_at,
            elapsed,
            body.onboard_id,
        )
    except Exception as exc:
        logger.warning("onboard preview update failed: %s", exc)

    return {
        "id": body.onboard_id,
        "preview_ready_at": preview_ready_at.isoformat(),
        "elapsed_seconds": elapsed,
        "under_target": under,
        "target_seconds": 60.0,
    }


@router.get("/metrics")
async def onboard_metrics(user: dict = Depends(_get_auth())):
    """Aggregate funnel metrics over the last 7 days."""
    db = await _get_db()
    await _ensure_table(db)
    since = datetime.now(timezone.utc) - timedelta(days=7)

    if db is None:
        return {"count": 0, "sub_60s_rate": 0.0, "p50": None, "p90": None, "degraded": True}

    try:
        rows = await db.fetch(
            "SELECT elapsed_seconds FROM onboard_events "
            "WHERE started_at >= $1 AND elapsed_seconds IS NOT NULL",
            since,
        )
    except Exception as exc:
        logger.warning("onboard metrics fetch failed: %s", exc)
        return {"count": 0, "sub_60s_rate": 0.0, "p50": None, "p90": None, "degraded": True}

    times = sorted(float(r["elapsed_seconds"]) for r in rows)
    n = len(times)
    if n == 0:
        return {"count": 0, "sub_60s_rate": 0.0, "p50": None, "p90": None}

    def _pct(p: float) -> float:
        idx = min(n - 1, int(p * n))
        return times[idx]

    sub_60 = sum(1 for t in times if t < 60.0) / n
    return {
        "count": n,
        "sub_60s_rate": sub_60,
        "p50": _pct(0.5),
        "p90": _pct(0.9),
        "target_seconds": 60.0,
    }


@router.get("/{onboard_id}")
async def onboard_get(onboard_id: str, user: dict = Depends(_get_auth())):
    db = await _get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="database unavailable")
    try:
        row = await db.fetchrow("SELECT * FROM onboard_events WHERE id=$1", onboard_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"query failed: {exc}")
    if row is None:
        raise HTTPException(status_code=404, detail="onboard event not found")

    return OnboardEventOut.from_row(dict(row)).model_dump()
