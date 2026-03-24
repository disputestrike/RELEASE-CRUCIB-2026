"""
CrucibAI Job Queue
==================
Redis when REDIS_URL is set, in-memory fallback otherwise.
Supports: enqueue, dequeue, job status, progress updates, dead-letter.

Usage:
    from integrations.queue import enqueue_job, get_job_status, update_job_progress

    job_id = await enqueue_job("iterative_build", {"prompt": "...", "user_id": "..."})
    status = await get_job_status(job_id)
"""
import os
import asyncio
import logging
import uuid
import json
import time
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# ── In-memory stores (used when Redis not configured) ─────────────────────────
_memory_queue: List[Dict] = []
_memory_jobs: Dict[str, Dict] = {}  # job_id → job state
_redis_client = None
_REDIS_QUEUE_KEY = "crucibai:queue"
_REDIS_JOB_KEY = "crucibai:job:"
_REDIS_DLQ_KEY = "crucibai:dlq"


def _use_redis() -> bool:
    return bool(os.environ.get("REDIS_URL", "").strip())


async def _get_redis():
    global _redis_client
    if _redis_client is None:
        try:
            import redis.asyncio as redis
            _redis_client = redis.from_url(
                os.environ["REDIS_URL"],
                decode_responses=True,
                socket_connect_timeout=5,
            )
            await _redis_client.ping()
            logger.info("Redis queue connected: %s", os.environ["REDIS_URL"][:30])
        except Exception as e:
            logger.warning("Redis unavailable, using memory queue: %s", e)
            _redis_client = None
    return _redis_client


# ── Job lifecycle ─────────────────────────────────────────────────────────────

async def enqueue_job(name: str, payload: dict, priority: int = 0) -> str:
    """Enqueue a job. Returns job_id."""
    job_id = str(uuid.uuid4())
    job = {
        "id": job_id,
        "name": name,
        "payload": payload,
        "status": "queued",
        "priority": priority,
        "progress": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "attempts": 0,
        "max_attempts": 3,
        "result": None,
        "error": None,
    }

    if _use_redis():
        r = await _get_redis()
        if r:
            try:
                await r.set(f"{_REDIS_JOB_KEY}{job_id}", json.dumps(job), ex=86400)  # 24h TTL
                await r.rpush(_REDIS_QUEUE_KEY, job_id)
                logger.info("Job enqueued (Redis): %s [%s]", job_id[:8], name)
                return job_id
            except Exception as e:
                logger.warning("Redis enqueue failed, falling back to memory: %s", e)

    # Memory fallback
    _memory_jobs[job_id] = job
    _memory_queue.append(job_id)
    logger.info("Job enqueued (memory): %s [%s]", job_id[:8], name)
    return job_id


async def get_job_status(job_id: str) -> Optional[Dict]:
    """Get current job state. Returns None if not found."""
    if _use_redis():
        r = await _get_redis()
        if r:
            try:
                raw = await r.get(f"{_REDIS_JOB_KEY}{job_id}")
                if raw:
                    return json.loads(raw)
            except Exception:
                pass
    return _memory_jobs.get(job_id)


async def update_job_progress(job_id: str, progress: int, status: str = "running", message: str = ""):
    """Update job progress (0-100). Called from within worker."""
    update = {
        "status": status,
        "progress": progress,
        "message": message,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    if _use_redis():
        r = await _get_redis()
        if r:
            try:
                raw = await r.get(f"{_REDIS_JOB_KEY}{job_id}")
                if raw:
                    job = json.loads(raw)
                    job.update(update)
                    await r.set(f"{_REDIS_JOB_KEY}{job_id}", json.dumps(job), ex=86400)
                    return
            except Exception:
                pass

    if job_id in _memory_jobs:
        _memory_jobs[job_id].update(update)


async def complete_job(job_id: str, result: Any = None):
    """Mark job as complete."""
    await _set_job_field(job_id, {"status": "complete", "progress": 100, "result": result,
                                   "completed_at": datetime.now(timezone.utc).isoformat()})


async def fail_job(job_id: str, error: str, send_to_dlq: bool = True):
    """Mark job as failed. Optionally send to dead-letter queue."""
    await _set_job_field(job_id, {"status": "failed", "error": error,
                                   "failed_at": datetime.now(timezone.utc).isoformat()})
    if send_to_dlq and _use_redis():
        r = await _get_redis()
        if r:
            try:
                raw = await r.get(f"{_REDIS_JOB_KEY}{job_id}")
                if raw:
                    await r.rpush(_REDIS_DLQ_KEY, raw)
            except Exception:
                pass


async def _set_job_field(job_id: str, fields: dict):
    fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    if _use_redis():
        r = await _get_redis()
        if r:
            try:
                raw = await r.get(f"{_REDIS_JOB_KEY}{job_id}")
                if raw:
                    job = json.loads(raw)
                    job.update(fields)
                    await r.set(f"{_REDIS_JOB_KEY}{job_id}", json.dumps(job), ex=86400)
                    return
            except Exception:
                pass
    if job_id in _memory_jobs:
        _memory_jobs[job_id].update(fields)


# ── Worker (processes one job at a time from queue) ──────────────────────────

async def dequeue_job() -> Optional[Dict]:
    """Dequeue next job. Returns job dict or None."""
    if _use_redis():
        r = await _get_redis()
        if r:
            try:
                job_id = await r.lpop(_REDIS_QUEUE_KEY)
                if job_id:
                    raw = await r.get(f"{_REDIS_JOB_KEY}{job_id}")
                    if raw:
                        return json.loads(raw)
            except Exception:
                pass

    if _memory_queue:
        job_id = _memory_queue.pop(0)
        return _memory_jobs.get(job_id)
    return None


async def run_worker(handlers: Dict[str, Callable], poll_interval: float = 1.0):
    """
    Run continuous worker loop. handlers = {job_name: async_handler_fn}.
    Each handler receives (job_id, payload) and should call update_job_progress().
    Run as: asyncio.create_task(run_worker({"iterative_build": build_handler}))
    """
    logger.info("Job worker started (queue=%s)", "redis" if _use_redis() else "memory")
    while True:
        try:
            job = await dequeue_job()
            if job:
                job_id = job["id"]
                name = job["name"]
                handler = handlers.get(name)
                if not handler:
                    logger.warning("No handler for job: %s", name)
                    await fail_job(job_id, f"No handler registered for '{name}'")
                    continue

                await _set_job_field(job_id, {"status": "running", "attempts": job.get("attempts", 0) + 1})
                try:
                    logger.info("Processing job %s [%s]", job_id[:8], name)
                    await handler(job_id, job["payload"])
                    await complete_job(job_id)
                    logger.info("Job complete: %s", job_id[:8])
                except Exception as e:
                    attempts = job.get("attempts", 0) + 1
                    max_attempts = job.get("max_attempts", 3)
                    if attempts < max_attempts:
                        # Re-queue for retry
                        job["attempts"] = attempts
                        job["status"] = "queued"
                        if _use_redis():
                            r = await _get_redis()
                            if r:
                                await r.rpush(_REDIS_QUEUE_KEY, job_id)
                        else:
                            _memory_queue.append(job_id)
                        logger.warning("Job %s failed (attempt %d/%d), re-queued: %s",
                                       job_id[:8], attempts, max_attempts, e)
                    else:
                        await fail_job(job_id, str(e), send_to_dlq=True)
                        logger.error("Job %s failed permanently after %d attempts: %s",
                                     job_id[:8], max_attempts, e)
            else:
                await asyncio.sleep(poll_interval)
        except asyncio.CancelledError:
            logger.info("Worker cancelled")
            break
        except Exception as e:
            logger.error("Worker loop error: %s", e)
            await asyncio.sleep(poll_interval)
