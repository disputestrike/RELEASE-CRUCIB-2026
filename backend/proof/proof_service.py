"""
proof_service.py — Proof persistence and retrieval.
Every verified action produces evidence stored here.
"""

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_pool = None


def set_pool(pool):
    global _pool
    _pool = pool


def _now() -> datetime:
    return datetime.now(timezone.utc)


def compute_bundle_integrity_sha256(flat_items: List[Dict[str, Any]]) -> str:
    """Stable SHA-256 over canonical JSON of proof rows (Fifty-point #23)."""
    canonical = json.dumps(flat_items, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _empty_bundle(job_id: str) -> Dict[str, Any]:
    from proof.build_contract import empty_contract

    return {
        "job_id": job_id,
        "quality_score": 0.0,
        "total_proof_items": 0,
        "verification_proof_items": 0,
        "category_counts": {
            "files": 0,
            "routes": 0,
            "database": 0,
            "verification": 0,
            "deploy": 0,
            "generic": 0,
        },
        "bundle": {
            "files": [],
            "routes": [],
            "database": [],
            "verification": [],
            "deploy": [],
            "generic": [],
        },
        "bundle_sha256": compute_bundle_integrity_sha256([]),
        "build_contract": empty_contract(job_id),
        "verification_class_counts": {},
        "class_coverage": {},
        "class_weighted_score": 0.0,
        "trust_score": 0.0,
        "penalties_applied": 0,
        "truth_status": {},
        "spec_guard": {},
        "spec_compliance_percent": 100.0,
        "production_readiness_score": 0.0,
        "production_readiness_cap_note": "",
        "production_readiness_factors": [],
        "scorecard": {},
        "verification_failed_count": 0,
        "step_exception_count": 0,
        "build_verified": False,
    }


async def store_proof(
    job_id: str, step_id: str, proof_type: str, title: str, payload: Dict[str, Any]
) -> str:
    if _pool is None:
        logger.error(
            "proof_service.store_proof: DB pool not set (call proof_service.set_pool); skipping persist"
        )
        return ""
    proof_id = str(uuid.uuid4())
    async with _pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO jobs (id)
            VALUES ($1)
            ON CONFLICT (id) DO NOTHING
            """,
            job_id,
        )
        await conn.execute(
            """
            INSERT INTO proof_items (id, job_id, step_id, proof_type, title,
                                     payload_json, created_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7)
        """,
            proof_id,
            job_id,
            step_id,
            proof_type,
            title,
            json.dumps(payload),
            _now(),
        )
    return proof_id


async def fetch_proof_items_raw(job_id: str) -> List[Dict[str, Any]]:
    """
    Flat proof rows for P5 proof_index (id, step_id, proof_type, title, payload dict, created_at).
    """
    if _pool is None:
        return []
    async with _pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, step_id, proof_type, title, payload_json, created_at
            FROM proof_items
            WHERE job_id = $1
            ORDER BY created_at
            """,
            job_id,
        )
    out: List[Dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        raw = d.pop("payload_json", None)
        try:
            d["payload"] = json.loads(raw) if raw else {}
        except Exception:
            d["payload"] = {}
        out.append(d)
    return out


FAILURE_QUALITY_CAP = 40.0  # aligns with steer/build contract when gates fail


def compute_build_verdict(
    *,
    quality_score_raw: float,
    verification_failed_count: int,
    step_exception_count: int,
    job_status: Optional[str],
) -> tuple[float, bool]:
    """
    Product truth for proof JSON: build_verified only when job completed cleanly
    and no stored verification_failure rows (§11 — narrative must match verifier).
    """
    st = (job_status or "").strip().lower()
    bad_proof = verification_failed_count + step_exception_count
    build_verified = bad_proof == 0 and st == "completed"
    q = float(quality_score_raw)
    if not build_verified:
        q = min(q, FAILURE_QUALITY_CAP)
    return round(q, 2), build_verified


async def get_proof(job_id: str) -> Dict[str, Any]:
    """Return proof bundle grouped by category for the proof panel UI."""
    if _pool is None:
        logger.warning(
            "proof_service.get_proof: DB pool not set; returning empty bundle"
        )
        return _empty_bundle(job_id)
    async with _pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM proof_items WHERE job_id=$1 ORDER BY created_at", job_id
        )
        job_quick = await conn.fetchrow(
            "SELECT * FROM jobs WHERE id=$1",
            job_id,
        )

    items = [dict(r) for r in rows]
    job_quick_dict = dict(job_quick) if job_quick else None
    job_status_str = (
        str((job_quick_dict or {}).get("status") or "").strip().lower()
        or None
    )
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
        "milestone": "verification",
        "verification_failed": "verification",
        "step_exception": "verification",
        "generic": "generic",
    }

    for item in items:
        category = type_map.get(item.get("proof_type", "generic"), "generic")
        payload = {}
        try:
            payload = json.loads(item.get("payload_json") or "{}")
        except Exception:
            pass
        bundle[category].append(
            {
                "id": item["id"],
                "type": item["proof_type"],
                "proof_type": item["proof_type"],
                "title": item["title"],
                "payload": payload,
                "created_at": str(item["created_at"]),
            }
        )

    # Quality score from real stored rows only (no UI fabrication)
    total_items = len(items)
    verified_items = sum(
        1
        for i in items
        if i.get("proof_type") in ("compile", "api", "test", "milestone")
    )
    if total_items == 0:
        quality_score_raw = 0.0
    else:
        quality_score_raw = float(
            min(100, round(70 + (verified_items / max(1, total_items)) * 30))
        )

    vf_cnt = sum(
        1 for i in items if i.get("proof_type") == "verification_failed"
    )
    sx_cnt = sum(1 for i in items if i.get("proof_type") == "step_exception")
    quality_score, build_verified = compute_build_verdict(
        quality_score_raw=quality_score_raw,
        verification_failed_count=vf_cnt,
        step_exception_count=sx_cnt,
        job_status=job_status_str,
    )

    category_counts = {k: len(v) for k, v in bundle.items()}

    flat: List[Dict[str, Any]] = []
    for lst in bundle.values():
        for row in lst:
            flat.append(row)

    try:
        from backend.orchestration.trust.trust_scoring import compute_trust_metrics

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

    spec_compliance = 100.0
    spec_guard_snapshot: Dict[str, Any] = {}
    try:
        from backend.orchestration.spec_guardian import (
            evaluate_goal_against_runner,
            merge_plan_risk_flags_into_report,
        )
        from backend.orchestration.truth_scores import (
            build_honest_scorecard,
            compute_production_readiness,
        )

        goal = str((job_quick_dict or {}).get("goal") or "")
        async with _pool.acquire() as conn:
            bp = await conn.fetchrow(
                "SELECT plan_json FROM build_plans WHERE job_id=$1 ORDER BY created_at DESC LIMIT 1",
                job_id,
            )
        risk_flags: List = []
        plan_bt = None
        if bp and bp.get("plan_json"):
            try:
                pj = json.loads(bp["plan_json"])
                risk_flags = pj.get("risk_flags") or []
                plan_bt = pj.get("crucib_build_target")
            except Exception:
                pass
        spec_guard_snapshot = merge_plan_risk_flags_into_report(
            risk_flags,
            evaluate_goal_against_runner(goal, build_target=plan_bt),
            build_target=plan_bt,
        )
        spec_compliance = float(
            spec_guard_snapshot.get("spec_compliance_percent") or 100.0
        )

        prod = compute_production_readiness(flat, bundle)
        scorecard = build_honest_scorecard(
            pipeline_quality_score=quality_score,
            trust_score=float(trust.get("trust_score") or 0.0),
            spec_compliance_percent=spec_compliance,
            production_readiness=prod,
        )
    except Exception:
        logger.exception("proof_service.get_proof: truthful scorecard failed")
        prod = {
            "production_readiness_score": 0.0,
            "production_readiness_cap_note": "",
            "production_readiness_factors": [],
        }
        scorecard = {
            "pipeline_quality_score": quality_score,
            "trust_evidence_score": float(trust.get("trust_score") or 0.0),
            "spec_compliance_percent": 100.0,
            "production_readiness_score": 0.0,
            "honest_summary": "Extended scores unavailable.",
        }

    bundle_sha256 = compute_bundle_integrity_sha256(flat)
    try:
        from proof.build_contract import build_contract

        async with _pool.acquire() as conn:
            step_rows = await conn.fetch(
                "SELECT * FROM job_steps WHERE job_id=$1 ORDER BY order_index, created_at",
                job_id,
            )
        jr = job_quick_dict if job_quick_dict else None
        contract = build_contract(
            job=dict(jr) if jr else {"id": job_id},
            steps=[dict(row) for row in step_rows],
            bundle=bundle,
            bundle_sha256=bundle_sha256,
            quality_score=quality_score,
            trust_score=float(trust.get("trust_score") or 0.0),
            production_readiness_score=float(
                prod.get("production_readiness_score") or 0.0
            ),
        )
    except Exception:
        logger.exception("proof_service.get_proof: build contract failed")
        from proof.build_contract import empty_contract

        contract = empty_contract(job_id)

    proof_index_doc: Optional[Dict[str, Any]] = None
    try:
        pid = (job_quick_dict or {}).get("project_id") if job_quick_dict else None
        if not pid and _pool is not None:
            async with _pool.acquire() as conn:
                jrow = await conn.fetchrow(
                    "SELECT project_id FROM jobs WHERE id = $1", job_id
                )
            pid = (jrow or {}).get("project_id")
        if pid:
            from pathlib import Path

            from project_state import WORKSPACE_ROOT

            safe = str(pid).replace("..", "").strip()
            idx_path = Path(WORKSPACE_ROOT) / safe / "META" / "proof_index.json"
            if idx_path.is_file():
                proof_index_doc = json.loads(idx_path.read_text(encoding="utf-8"))
    except Exception:
        logger.debug("get_proof: proof_index load skipped", exc_info=True)

    return {
        "job_id": job_id,
        "quality_score": quality_score,
        "total_proof_items": total_items,
        "verification_proof_items": verified_items,
        "verification_failed_count": vf_cnt,
        "step_exception_count": sx_cnt,
        "build_verified": build_verified,
        "category_counts": category_counts,
        "bundle": bundle,
        "bundle_sha256": bundle_sha256,
        "build_contract": contract,
        **trust,
        "spec_guard": spec_guard_snapshot,
        "spec_compliance_percent": spec_compliance,
        **prod,
        "scorecard": scorecard,
        "proof_index": proof_index_doc or {},
    }
