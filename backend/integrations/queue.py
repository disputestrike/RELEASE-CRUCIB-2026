"""
Job queue: Redis when REDIS_URL is set, else in-memory.
Workers and automation stay green; add REDIS_URL for multi-replica scale.
"""
import os
import asyncio
import logging
import uuid
import json
from typing import Any, Callable, Dict, List
from collections import deque

logger = logging.getLogger(__name__)

_memory_queue: List[Dict] = []
_redis_client = None


def get_queue() -> str:
    """Return 'redis' or 'memory'."""
    if os.environ.get("REDIS_URL", "").strip():
        return "redis"
    return "memory"


async def _redis_push(name: str, payload: dict) -> str:
    global _redis_client
    if _redis_client is None:
        try:
            import redis.asyncio as redis
            _redis_client = redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
        except ImportError:
            logger.warning("redis package not installed; falling back to memory queue")
            return _memory_push(name, payload)
    job_id = str(uuid.uuid4())
    await _redis_client.rpush("crucibai:queue", json.dumps({"id": job_id, "name": name, "payload": payload}))
    return job_id


def _memory_push(name: str, payload: dict) -> str:
    job_id = str(uuid.uuid4())
    _memory_queue.append({"id": job_id, "name": name, "payload": payload})
    return job_id


async def enqueue_job(name: str, payload: dict) -> str:
    """Enqueue a job (async). Returns job_id. Use from FastAPI/async code."""
    if get_queue() == "redis":
        return await _redis_push(name, payload)
    return _memory_push(name, payload)


def drain_memory_queue(handler: Callable[[str, dict], Any]) -> int:
    """Process all jobs in memory queue. Returns count processed. Call from worker loop."""
    n = 0
    while _memory_queue:
        job = _memory_queue.pop(0)
        try:
            handler(job["name"], job["payload"])
            n += 1
        except Exception as e:
            logger.exception("Job %s failed: %s", job.get("id"), e)
    return n
