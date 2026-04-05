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


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def store_proof(job_id: str, step_id: str,
                       proof_type: str, title: str,
                       payload: Dict[str, Any]) -> str:
    if _pool is None:
        logger.error(
            "proof_service.store_proof: DB pool not set (call proof_service.set_pool); skipping persist"
        )
        return ""
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
    if _pool is None:
        logger.warning("proof_service.get_proof: DB pool not set; returning empty bundle")
        return {
            "job_id": job_id,
            "quality_score": 0.0,
            "total_proof_items": 0,
            "verification_proof_items": 0,
            "category_counts": {
                "files": 0, "routes": 0, "database": 0,
                "verification": 0, "deploy": 0, "generic": 0,
            },
            "bundle": {
                "files": [], "routes": [], "database": [],
                "verification": [], "deploy": [], "generic": [],
            },
            "verification_class_counts": {},
            "class_coverage": {},
            "class_weighted_score": 0.0,
            "trust_score": 0.0,
            "penalties_applied": 0,
            "truth_status": {},
        }
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
            "proof_type": item["proof_type"],
            "title": item["title"],
            "payload": payload,
            "created_at": str(item["created_at"]),
        })

    # Quality score from real stored rows only (no UI fabrication)
    total_items = len(items)
    verified_items = sum(1 for i in items if i.get("proof_type") in ("compile", "api", "test"))
    if total_items == 0:
        quality_score = 0.0
    else:
        quality_score = float(min(100, round(70 + (verified_items / max(1, total_items)) * 30)))

    category_counts = {k: len(v) for k, v in bundle.items()}

    flat: List[Dict[str, Any]] = []
    for lst in bundle.values():
        for row in lst:
            flat.append(row)

    try:
        from orchestration.trust.trust_scoring import compute_trust_metrics

        has_screenshot = any(
            (row.get("payload") or {}).get("kind") == "preview_screenshot"
            for row in flat
        )
        has_live_deploy = False
        for row in bundle.get("deploy") or []:
            pl = row.get("payload") or {}
            st = pl.get("status")
            if pl.get("url") and st is not None:
                try:
                    if 200 <= int(st) < 400:
                        has_live_deploy = True
                        break
                except (TypeError, ValueError):
                    pass

        trust = compute_trust_metrics(
            flat,
            has_screenshot_proof=has_screenshot,
            has_live_deploy_url=has_live_deploy,
        )
    except Exception:
        logger.exception("proof_service.get_proof: trust metrics failed")
        trust = {
            "verification_class_counts": {},
            "class_coverage": {},
            "class_weighted_score": 0.0,
            "trust_score": 0.0,
            "penalties_applied": 0,
            "truth_status": {},
        }

    return {
        "job_id": job_id,
        "quality_score": quality_score,
        "total_proof_items": total_items,
        "verification_proof_items": verified_items,
        "category_counts": category_counts,
        "bundle": bundle,
        **trust,
    }
