"""
proof_service.py — Proof persistence and retrieval.
Every verified action produces evidence stored here.
"""
import uuid
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

_pool = None


def set_pool(pool):
    global _pool
    _pool = pool


def _now():
    return datetime.now(timezone.utc).isoformat()


async def store_proof(job_id: str, step_id: str,
                       proof_type: str, title: str,
                       payload: Dict[str, Any]) -> str:
    proof_id = str(uuid.uuid4())
    async with _pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO proof_items (id, job_id, step_id, proof_type, title,
                                     payload_json, created_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7)
        """, proof_id, job_id, step_id, proof_type, title,
            json.dumps(payload), _now())
    return proof_id


async def get_proof(job_id: str) -> Dict[str, Any]:
    """Return proof bundle grouped by category for the proof panel UI."""
    async with _pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM proof_items WHERE job_id=$1 ORDER BY created_at",
            job_id
        )

    items = [dict(r) for r in rows]
    bundle: Dict[str, List] = {
        "files": [],
        "routes": [],
        "database": [],
        "verification": [],
        "deploy": [],
        "generic": [],
    }

    type_map = {
        "file": "files",
        "compile": "verification",
        "db": "database",
        "route": "routes",
        "deploy": "deploy",
        "api": "verification",
        "test": "verification",
        "generic": "generic",
    }

    for item in items:
        category = type_map.get(item.get("proof_type", "generic"), "generic")
        payload = {}
        try:
            payload = json.loads(item.get("payload_json") or "{}")
        except Exception:
            pass
        bundle[category].append({
            "id": item["id"],
            "type": item["proof_type"],
            "title": item["title"],
            "payload": payload,
            "created_at": str(item["created_at"]),
        })

    # Compute quality score from verification items
    total_items = len(items)
    verified_items = sum(1 for i in items if i.get("proof_type") in ("compile", "api", "test"))
    quality_score = min(100, round(70 + (verified_items / max(1, total_items)) * 30))

    return {
        "job_id": job_id,
        "quality_score": quality_score,
        "total_proof_items": total_items,
        "bundle": bundle,
    }
