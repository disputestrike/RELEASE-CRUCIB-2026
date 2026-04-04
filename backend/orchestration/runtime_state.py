"""
runtime_state.py — Job and step state machine for CrucibAI Auto-Runner.
All state is persisted to PostgreSQL. All mutations go through helpers here.
"""
import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

# ── State enums ──────────────────────────────────────────────────────────────

JOB_STATES = [
    "planned", "approved", "queued", "running",
    "blocked", "failed", "completed", "cancelled"
]

STEP_STATES = [
    "pending", "running", "verifying", "retrying",
    "failed", "completed", "blocked", "skipped"
]

TERMINAL_JOB_STATES = {"completed", "failed", "cancelled"}
TERMINAL_STEP_STATES = {"completed", "failed", "skipped"}

# ── DB helpers (uses asyncpg pool injected at startup) ───────────────────────

_pool = None


def set_pool(pool):
    global _pool
    _pool = pool


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Job helpers ──────────────────────────────────────────────────────────────

async def create_job(project_id: str, mode: str = "guided", goal: str = "",
                     user_id: Optional[str] = None) -> Dict[str, Any]:
    job_id = str(uuid.uuid4())
    now = _now()
    async with _pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO jobs (id, project_id, status, mode, goal, current_phase,
                              created_at, updated_at, retry_count, quality_score, user_id)
            VALUES ($1,$2,'planned',$3,$4,'planning',$5,$5,0,0,$6)
        """, job_id, project_id, mode, goal, now, user_id)
    return await get_job(job_id)


async def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    async with _pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM jobs WHERE id=$1", job_id)
    return dict(row) if row else None


async def update_job_state(job_id: str, status: str,
                           extra: Optional[Dict] = None) -> None:
    updates = {"status": status, "updated_at": _now()}
    if extra:
        updates.update(extra)
    if status == "running" and "started_at" not in updates:
        updates["started_at"] = _now()
    if status in TERMINAL_JOB_STATES and "completed_at" not in updates:
        updates["completed_at"] = _now()
    set_clause = ", ".join(f"{k}=${i+2}" for i, k in enumerate(updates))
    vals = list(updates.values())
    async with _pool.acquire() as conn:
        await conn.execute(
            f"UPDATE jobs SET {set_clause} WHERE id=$1",
            job_id, *vals
        )


async def list_jobs(project_id: str) -> List[Dict[str, Any]]:
    async with _pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM jobs WHERE project_id=$1 ORDER BY created_at DESC LIMIT 50",
            project_id
        )
    return [dict(r) for r in rows]


# ── Step helpers ─────────────────────────────────────────────────────────────

async def create_step(job_id: str, step_key: str, agent_name: str,
                      phase: str, depends_on: Optional[List[str]] = None,
                      order_index: int = 0) -> Dict[str, Any]:
    step_id = str(uuid.uuid4())
    now = _now()
    deps = json.dumps(depends_on or [])
    async with _pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO job_steps (id, job_id, step_key, agent_name, phase,
                status, depends_on_json, created_at, retry_count, order_index)
            VALUES ($1,$2,$3,$4,$5,'pending',$6,$7,0,$8)
        """, step_id, job_id, step_key, agent_name, phase, deps, now, order_index)
    return await get_step(step_id)


async def get_step(step_id: str) -> Optional[Dict[str, Any]]:
    async with _pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM job_steps WHERE id=$1", step_id)
    return dict(row) if row else None


async def get_steps(job_id: str) -> List[Dict[str, Any]]:
    async with _pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM job_steps WHERE job_id=$1 ORDER BY order_index, created_at",
            job_id
        )
    return [dict(r) for r in rows]


async def update_step_state(step_id: str, status: str,
                            extra: Optional[Dict] = None) -> None:
    updates = {"status": status, "updated_at": _now()}
    if extra:
        updates.update(extra)
    if status == "running":
        updates.setdefault("started_at", _now())
    if status in TERMINAL_STEP_STATES:
        updates.setdefault("completed_at", _now())
    set_clause = ", ".join(f"{k}=${i+2}" for i, k in enumerate(updates))
    vals = list(updates.values())
    async with _pool.acquire() as conn:
        await conn.execute(
            f"UPDATE job_steps SET {set_clause} WHERE id=$1",
            step_id, *vals
        )


# ── Event helpers ─────────────────────────────────────────────────────────────

async def append_job_event(job_id: str, event_type: str,
                           payload: Optional[Dict] = None,
                           step_id: Optional[str] = None) -> str:
    event_id = str(uuid.uuid4())
    async with _pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO job_events (id, job_id, step_id, event_type, payload_json, created_at)
            VALUES ($1,$2,$3,$4,$5,$6)
        """, event_id, job_id, step_id, event_type,
            json.dumps(payload or {}), _now())
    return event_id


async def get_job_events(job_id: str, since_id: Optional[str] = None,
                         limit: int = 200) -> List[Dict[str, Any]]:
    async with _pool.acquire() as conn:
        if since_id:
            rows = await conn.fetch("""
                SELECT * FROM job_events
                WHERE job_id=$1 AND created_at > (
                    SELECT created_at FROM job_events WHERE id=$2
                )
                ORDER BY created_at LIMIT $3
            """, job_id, since_id, limit)
        else:
            rows = await conn.fetch(
                "SELECT * FROM job_events WHERE job_id=$1 ORDER BY created_at LIMIT $2",
                job_id, limit
            )
    return [dict(r) for r in rows]


# ── Checkpoint helpers ────────────────────────────────────────────────────────

async def save_checkpoint(job_id: str, checkpoint_key: str,
                          snapshot: Dict[str, Any]) -> None:
    cp_id = str(uuid.uuid4())
    async with _pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO job_checkpoints (id, job_id, checkpoint_key, snapshot_json, created_at)
            VALUES ($1,$2,$3,$4,$5)
            ON CONFLICT (job_id, checkpoint_key)
            DO UPDATE SET snapshot_json=$4, created_at=$5
        """, cp_id, job_id, checkpoint_key, json.dumps(snapshot), _now())


async def load_checkpoint(job_id: str,
                          checkpoint_key: str) -> Optional[Dict[str, Any]]:
    async with _pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT snapshot_json FROM job_checkpoints
            WHERE job_id=$1 AND checkpoint_key=$2
            ORDER BY created_at DESC LIMIT 1
        """, job_id, checkpoint_key)
    return json.loads(row["snapshot_json"]) if row else None


async def get_all_checkpoints(job_id: str) -> List[Dict[str, Any]]:
    async with _pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM job_checkpoints WHERE job_id=$1 ORDER BY created_at",
            job_id
        )
    return [dict(r) for r in rows]
