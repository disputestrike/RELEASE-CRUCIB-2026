"""
CrucibAI Production Job Queue
==============================
Redis-backed persistent queue with BullMQ-style semantics.
Falls back to PostgreSQL-persisted in-memory queue when Redis unavailable.
All job state survives container restarts.

Key design:
- Jobs stored in Redis hash (crucibai:job:{id}) with 48h TTL
- Active queue: crucibai:queue:active  (RPUSH / BLPOP)
- Processing set: crucibai:queue:processing  (SADD on pickup, SREM on done)
- Dead-letter: crucibai:queue:dlq
- Recovery: on startup, jobs in 'processing' that are stale get re-queued

Without Redis: jobs stored in PostgreSQL automation_tasks table.
Worker reads unfinished jobs from DB on every startup.
"""
import os
import asyncio
import logging
import uuid
import json
import time
from typing import Any, Callable, Dict, List, Optional, Awaitable
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
_QUEUE_KEY      = "crucibai:queue:active"
_PROCESSING_KEY = "crucibai:queue:processing"
_DLQ_KEY        = "crucibai:queue:dlq"
_JOB_PREFIX     = "crucibai:job:"
_JOB_TTL        = 172800  # 48 hours in seconds
_STALE_TIMEOUT  = 600     # jobs processing > 10min assumed crashed

# ── In-process fallback store (PostgreSQL-backed on startup) ──────────────────
_memory_queue: List[str] = []          # list of job_ids
_memory_jobs:  Dict[str, Dict] = {}    # job_id → full job dict
_redis_client  = None
_db_ref        = None  # set by init_queue_db()
_worker_task   = None


def init_queue_db(db):
    """Call on startup with the db reference so queue can use PostgreSQL fallback."""
    global _db_ref
    _db_ref = db


def _use_redis() -> bool:
    return bool(os.environ.get("REDIS_URL", "").strip())


async def _get_redis():
    global _redis_client
    if _redis_client is not None:
        try:
            await _redis_client.ping()
            return _redis_client
        except Exception:
            _redis_client = None

    if not _use_redis():
        return None

    try:
        import redis.asyncio as redis
        _redis_client = redis.from_url(
            os.environ["REDIS_URL"],
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=10,
            retry_on_timeout=True,
        )
        await _redis_client.ping()
        logger.info("✅ Redis queue connected")
        return _redis_client
    except Exception as e:
        logger.warning("Redis unavailable, using PostgreSQL fallback: %s", e)
        _redis_client = None
        return None


# ── Job CRUD ──────────────────────────────────────────────────────────────────

def _make_job(name: str, payload: dict, job_id: str = None) -> dict:
    return {
        "id":           job_id or str(uuid.uuid4()),
        "name":         name,
        "payload":      payload,
        "status":       "queued",
        "progress":     0,
        "message":      "",
        "attempts":     0,
        "max_attempts": 3,
        "result":       None,
        "error":        None,
        "created_at":   datetime.now(timezone.utc).isoformat(),
        "updated_at":   datetime.now(timezone.utc).isoformat(),
        "started_at":   None,
        "completed_at": None,
    }


async def _save_job_redis(r, job: dict):
    await r.set(f"{_JOB_PREFIX}{job['id']}", json.dumps(job), ex=_JOB_TTL)


async def _load_job_redis(r, job_id: str) -> Optional[dict]:
    raw = await r.get(f"{_JOB_PREFIX}{job_id}")
    return json.loads(raw) if raw else None


async def _save_job_pg(job: dict):
    """Persist job to PostgreSQL automation_tasks table."""
    if not _db_ref:
        return
    try:
        await _db_ref.automation_tasks.update_one(
            {"id": job["id"]},
            {"$set": {"id": job["id"], "doc": job}},
            upsert=True,
        )
    except Exception as e:
        logger.debug("PG job save failed: %s", e)


async def _load_job_pg(job_id: str) -> Optional[dict]:
    if not _db_ref:
        return _memory_jobs.get(job_id)
    try:
        row = await _db_ref.automation_tasks.find_one({"id": job_id})
        return row.get("doc") if row else _memory_jobs.get(job_id)
    except Exception:
        return _memory_jobs.get(job_id)


# ── Public API ────────────────────────────────────────────────────────────────

async def enqueue_job(name: str, payload: dict, job_id: str = None) -> str:
    """Enqueue a job. Returns job_id. Survives container restart via Redis or PostgreSQL."""
    job = _make_job(name, payload, job_id)
    jid = job["id"]

    r = await _get_redis()
    if r:
        try:
            async with r.pipeline(transaction=True) as pipe:
                await pipe.set(f"{_JOB_PREFIX}{jid}", json.dumps(job), ex=_JOB_TTL)
                await pipe.rpush(_QUEUE_KEY, jid)
                await pipe.execute()
            logger.info("Job enqueued (Redis): %s [%s]", jid[:8], name)
            return jid
        except Exception as e:
            logger.warning("Redis enqueue failed, using PG fallback: %s", e)

    # PostgreSQL + memory fallback
    _memory_jobs[jid] = job
    _memory_queue.append(jid)
    await _save_job_pg(job)
    logger.info("Job enqueued (PG/memory): %s [%s]", jid[:8], name)
    return jid


async def get_job_status(job_id: str) -> Optional[dict]:
    """Get current job state."""
    r = await _get_redis()
    if r:
        try:
            return await _load_job_redis(r, job_id)
        except Exception:
            pass
    return await _load_job_pg(job_id)


async def update_job_progress(job_id: str, progress: int, status: str = "running", message: str = ""):
    """Update job progress 0-100."""
    now = datetime.now(timezone.utc).isoformat()
    r = await _get_redis()
    if r:
        try:
            raw = await r.get(f"{_JOB_PREFIX}{job_id}")
            if raw:
                job = json.loads(raw)
                job.update({"status": status, "progress": progress,
                            "message": message, "updated_at": now})
                await r.set(f"{_JOB_PREFIX}{job_id}", json.dumps(job), ex=_JOB_TTL)
                return
        except Exception:
            pass
    # Memory fallback
    if job_id in _memory_jobs:
        _memory_jobs[job_id].update({"status": status, "progress": progress,
                                      "message": message, "updated_at": now})
        await _save_job_pg(_memory_jobs[job_id])


async def complete_job(job_id: str, result: Any = None):
    now = datetime.now(timezone.utc).isoformat()
    await _update_job(job_id, {"status": "complete", "progress": 100,
                                "result": result, "completed_at": now})


async def fail_job(job_id: str, error: str):
    now = datetime.now(timezone.utc).isoformat()
    job = await _update_job(job_id, {"status": "failed", "error": error, "failed_at": now})

    # Send to dead-letter queue
    r = await _get_redis()
    if r and job:
        try:
            await r.rpush(_DLQ_KEY, json.dumps(job))
        except Exception:
            pass


async def _update_job(job_id: str, fields: dict) -> Optional[dict]:
    fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    r = await _get_redis()
    if r:
        try:
            raw = await r.get(f"{_JOB_PREFIX}{job_id}")
            if raw:
                job = json.loads(raw)
                job.update(fields)
                await r.set(f"{_JOB_PREFIX}{job_id}", json.dumps(job), ex=_JOB_TTL)
                return job
        except Exception:
            pass
    if job_id in _memory_jobs:
        _memory_jobs[job_id].update(fields)
        await _save_job_pg(_memory_jobs[job_id])
        return _memory_jobs[job_id]
    return None


# ── Worker ────────────────────────────────────────────────────────────────────

async def _dequeue(r) -> Optional[dict]:
    """Pop next job from queue."""
    if r:
        try:
            # Non-blocking pop
            jid = await r.lpop(_QUEUE_KEY)
            if jid:
                # Mark as processing
                await r.sadd(_PROCESSING_KEY, jid)
                return await _load_job_redis(r, jid)
        except Exception as e:
            logger.debug("Redis dequeue error: %s", e)

    if _memory_queue:
        jid = _memory_queue.pop(0)
        return _memory_jobs.get(jid)
    return None


async def recover_incomplete_jobs():
    """
    On startup: find jobs that were 'running' or 'queued' and re-enqueue them.
    This ensures in-flight jobs survive container restarts.
    Called once on server startup.
    """
    recovered = 0

    # Redis recovery: check processing set for stale jobs
    r = await _get_redis()
    if r:
        try:
            stale_ids = await r.smembers(_PROCESSING_KEY)
            now_ts = time.time()
            for jid in stale_ids:
                raw = await r.get(f"{_JOB_PREFIX}{jid}")
                if not raw:
                    await r.srem(_PROCESSING_KEY, jid)
                    continue
                job = json.loads(raw)
                # If started more than _STALE_TIMEOUT seconds ago — re-queue
                started = job.get("started_at", "")
                if started:
                    try:
                        started_ts = datetime.fromisoformat(started).timestamp()
                        if (now_ts - started_ts) > _STALE_TIMEOUT:
                            job["status"] = "queued"
                            job["attempts"] = job.get("attempts", 0)
                            await r.set(f"{_JOB_PREFIX}{jid}", json.dumps(job), ex=_JOB_TTL)
                            await r.rpush(_QUEUE_KEY, jid)
                            await r.srem(_PROCESSING_KEY, jid)
                            recovered += 1
                            logger.info("Recovered stale job: %s [%s]", jid[:8], job.get("name"))
                    except Exception:
                        pass
        except Exception as e:
            logger.debug("Redis recovery error: %s", e)

    # PostgreSQL recovery: find queued/running jobs not in memory
    if _db_ref:
        try:
            cursor = _db_ref.automation_tasks.find({"doc.status": {"$in": ["queued", "running"]}})
            async for row in cursor:
                job = row.get("doc", {})
                jid = job.get("id")
                if not jid or jid in _memory_jobs:
                    continue
                # Re-queue only if not already in Redis
                if r:
                    existing = await _load_job_redis(r, jid)
                    if existing and existing.get("status") in ("complete", "failed"):
                        continue
                job["status"] = "queued"
                _memory_jobs[jid] = job
                _memory_queue.append(jid)
                recovered += 1
                logger.info("Recovered PG job: %s [%s]", jid[:8], job.get("name"))
        except Exception as e:
            logger.debug("PG recovery error: %s", e)

    if recovered:
        logger.info("✅ Job recovery: %d jobs re-queued on startup", recovered)
    return recovered


async def run_worker(handlers: Dict[str, Callable[..., Awaitable[None]]], poll_interval: float = 1.0):
    """
    Persistent worker loop.
    - Dequeues jobs, dispatches to handler by name
    - Auto-retries up to max_attempts (default 3)
    - Failed jobs → dead-letter queue
    - Survives individual job errors without stopping
    """
    logger.info("✅ Job worker started (backend=%s)", "Redis" if _use_redis() else "PostgreSQL/memory")

    while True:
        try:
            r = await _get_redis()
            job = await _dequeue(r)

            if job:
                jid = job["id"]
                name = job["name"]
                attempts = job.get("attempts", 0) + 1
                handler = handlers.get(name)

                if not handler:
                    logger.warning("No handler for job '%s'", name)
                    await fail_job(jid, f"No handler for '{name}'")
                    if r:
                        try: await r.srem(_PROCESSING_KEY, jid)
                        except Exception: pass
                    continue

                now = datetime.now(timezone.utc).isoformat()
                await _update_job(jid, {"status": "running", "attempts": attempts, "started_at": now})
                logger.info("Processing job %s [%s] attempt %d/%d",
                            jid[:8], name, attempts, job.get("max_attempts", 3))

                try:
                    await handler(jid, job["payload"])
                    await complete_job(jid)
                    if r:
                        try: await r.srem(_PROCESSING_KEY, jid)
                        except Exception: pass
                    logger.info("✅ Job complete: %s", jid[:8])

                except Exception as e:
                    logger.error("Job %s failed (attempt %d): %s", jid[:8], attempts, e)
                    if r:
                        try: await r.srem(_PROCESSING_KEY, jid)
                        except Exception: pass

                    if attempts < job.get("max_attempts", 3):
                        # Re-queue for retry with backoff
                        backoff = min(30 * attempts, 120)
                        await asyncio.sleep(backoff)
                        job["attempts"] = attempts
                        job["status"] = "queued"
                        if r:
                            try:
                                await r.rpush(_QUEUE_KEY, jid)
                            except Exception:
                                _memory_queue.append(jid)
                        else:
                            _memory_queue.append(jid)
                        logger.warning("Job %s re-queued (attempt %d, backoff %ds)",
                                       jid[:8], attempts, backoff)
                    else:
                        await fail_job(jid, str(e))
                        logger.error("Job %s permanently failed after %d attempts",
                                     jid[:8], attempts)
            else:
                await asyncio.sleep(poll_interval)

        except asyncio.CancelledError:
            logger.info("Worker stopped")
            break
        except Exception as e:
            logger.error("Worker loop error: %s", e)
            await asyncio.sleep(poll_interval)
