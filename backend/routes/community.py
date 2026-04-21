"""Public community/template trust routes.

This router is intentionally static for launch: templates and case studies are
curated by the CrucibAI team until moderation workflows are staffed and audited.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_PG_READY = False
_PG_TABLE_CHECKED = False

try:
    import asyncpg  # type: ignore  # noqa: F401
    _PG_READY = True
except Exception:  # pragma: no cover - optional dep
    _PG_READY = False


async def _get_pg_pool():
    """Return asyncpg pool or None if DB unavailable."""
    try:
        from db import get_pg_pool  # type: ignore
        return await get_pg_pool()
    except Exception:
        return None


async def _ensure_publish_table():
    """Create community_publications table on first use (idempotent)."""
    global _PG_TABLE_CHECKED
    if _PG_TABLE_CHECKED:
        return
    pool = await _get_pg_pool()
    if pool is None:
        return
    try:
        async with pool.acquire() as con:
            await con.execute(
                """
                CREATE TABLE IF NOT EXISTS community_publications (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    project_id TEXT,
                    title TEXT NOT NULL,
                    description TEXT,
                    tags TEXT[] DEFAULT ARRAY[]::TEXT[],
                    prompt TEXT,
                    preview_url TEXT,
                    proof_score DOUBLE PRECISION DEFAULT 0,
                    moderation_status TEXT DEFAULT 'pending',
                    moderation_reasons JSONB DEFAULT '[]'::JSONB,
                    created_at TIMESTAMPTZ NOT NULL,
                    approved_at TIMESTAMPTZ
                )
                """
            )
        _PG_TABLE_CHECKED = True
    except Exception as exc:
        logger.warning("community_publications ensure failed: %s", exc)


def _get_auth_user(request: Request) -> Optional[str]:
    """Best-effort user_id extraction; returns anonymous-publish string on failure."""
    try:
        user = getattr(request.state, "user", None)
        if user and isinstance(user, dict):
            return user.get("id") or user.get("user_id")
    except Exception:
        pass
    return None


class PublishRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=120)
    description: Optional[str] = Field(None, max_length=500)
    prompt: Optional[str] = Field(None, max_length=2000)
    tags: List[str] = Field(default_factory=list, max_items=10)
    project_id: Optional[str] = None
    preview_url: Optional[str] = None
    proof_score: float = Field(default=0.0, ge=0.0, le=100.0)

COMMUNITY_TEMPLATES = [
    {
        "id": "dashboard",
        "name": "Dashboard",
        "description": "Sidebar, metrics cards, proof-ready preview, and publish path.",
        "prompt": "Create a dashboard with a sidebar, stat cards, and a chart area. React and Tailwind.",
        "tags": ["saas", "analytics"],
        "difficulty": "starter",
        "proof_score": 100,
        "moderation_status": "approved",
        "remix_endpoint": "/api/community/templates/dashboard/remix-plan",
    },
    {
        "id": "saas-shell",
        "name": "SaaS shell",
        "description": "Auth shell, settings area, pricing surface, and deploy-ready structure.",
        "prompt": "Create a SaaS app shell with top nav, user menu, and settings page. React and Tailwind.",
        "tags": ["saas", "auth"],
        "difficulty": "intermediate",
        "proof_score": 100,
        "moderation_status": "approved",
        "remix_endpoint": "/api/community/templates/saas-shell/remix-plan",
    },
    {
        "id": "crm",
        "name": "CRM dashboard",
        "description": "Contacts, pipeline board, activity feed, and clean data states.",
        "prompt": "Create a CRM dashboard with contacts list, deals pipeline, and activity feed. React and Tailwind.",
        "tags": ["crm", "business"],
        "difficulty": "intermediate",
        "proof_score": 100,
        "moderation_status": "approved",
        "remix_endpoint": "/api/community/templates/crm/remix-plan",
    },
    {
        "id": "workflow-agent",
        "name": "Workflow agent",
        "description": "Automation starter that calls the same build AI inside a workflow.",
        "prompt": "Create an automation dashboard that runs an agent step, reviews output, and sends a summary.",
        "tags": ["automation", "agents"],
        "difficulty": "advanced",
        "proof_score": 100,
        "moderation_status": "approved",
        "remix_endpoint": "/api/community/templates/workflow-agent/remix-plan",
    },
]


CASE_STUDIES = [
    {
        "id": "live-golden-path",
        "title": "Live golden path proof",
        "summary": "Railway production run completed prompt, plan, build, preview, proof, publish, and public URL.",
        "proof": "proof/live_production_golden_path/PASS_FAIL.md",
        "status": "verified",
    },
    {
        "id": "repeatability-v1",
        "title": "50-prompt repeatability benchmark",
        "summary": "Deterministic benchmark suite covers 50 app categories with a 90% release threshold.",
        "proof": "proof/benchmarks/repeatability_v1/PASS_FAIL.md",
        "status": "verified",
    },
    {
        "id": "full-systems-gate",
        "title": "Full systems release gate",
        "summary": "Backend, frontend, Railway, public trust preflight, and live golden path run as required gates.",
        "proof": "proof/full_systems/PASS_FAIL.md",
        "status": "verified",
    },
]


def create_community_router() -> APIRouter:
    router = APIRouter(prefix="/api/community", tags=["community"])

    @router.get("/templates")
    async def community_templates():
        return {
            "status": "ready",
            "moderation": "curated_pre_publish",
            "templates": COMMUNITY_TEMPLATES,
        }

    @router.get("/templates/{template_id}/remix-plan")
    async def community_template_remix_plan(template_id: str):
        template = next(
            (item for item in COMMUNITY_TEMPLATES if item["id"] == template_id), None
        )
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        return {
            "template_id": template_id,
            "name": template["name"],
            "prompt": f"Remix template '{template['name']}': {template['prompt']}",
            "tags": template["tags"],
            "difficulty": template["difficulty"],
            "proof_score": template["proof_score"],
            "moderation_status": template["moderation_status"],
            "route": "/app/workspace",
        }

    @router.get("/case-studies")
    async def community_case_studies():
        return {"status": "ready", "case_studies": CASE_STUDIES}

    @router.get("/moderation-policy")
    async def community_moderation_policy():
        return {
            "status": "ready",
            "policy": "Curated templates only for launch; public submissions require moderation before listing.",
            "checks": [
                "owner permission",
                "secret scan",
                "security proof",
                "preview proof",
                "copyright and abuse review",
            ],
        }

    @router.post("/publish")
    async def community_publish(body: PublishRequest, request: Request):
        """CF13 — Accept a publish submission into the moderation queue.

        Validates title + required proof_score, runs lightweight automated
        checks (secret scan, score threshold), then persists to
        ``community_publications`` with moderation_status='pending'.
        Returns a publication_id the client can poll.
        """
        await _ensure_publish_table()
        user_id = _get_auth_user(request) or "anonymous"

        # lightweight automated moderation (fast, deterministic, no LLM)
        reasons: List[str] = []
        lowered = f"{body.title}\n{body.description or ''}\n{body.prompt or ''}".lower()
        secret_markers = (
            "sk-", "ghp_", "aws_secret", "private_key", "begin rsa",
            "ssh-rsa aaaa", "aws_access_key_id",
        )
        for marker in secret_markers:
            if marker in lowered:
                reasons.append(f"secret_marker_detected:{marker}")
        if body.proof_score < 80.0:
            reasons.append("proof_score_below_publish_threshold")
        if len(body.tags) > 10:
            reasons.append("too_many_tags")

        publication_id = uuid.uuid4().hex[:16]
        now = datetime.now(timezone.utc)
        moderation_status = "pending" if not reasons else "rejected"

        pool = await _get_pg_pool()
        persisted = False
        if pool is not None:
            try:
                async with pool.acquire() as con:
                    await con.execute(
                        """
                        INSERT INTO community_publications
                            (id, user_id, project_id, title, description, tags,
                             prompt, preview_url, proof_score, moderation_status,
                             moderation_reasons, created_at)
                        VALUES
                            ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11::jsonb,$12)
                        """,
                        publication_id, user_id, body.project_id, body.title,
                        body.description, body.tags, body.prompt, body.preview_url,
                        float(body.proof_score), moderation_status,
                        __import__("json").dumps(reasons), now,
                    )
                persisted = True
            except Exception as exc:
                logger.warning("publish persist failed: %s", exc)

        return {
            "status": "accepted" if moderation_status == "pending" else "rejected",
            "publication_id": publication_id,
            "moderation_status": moderation_status,
            "moderation_reasons": reasons,
            "persisted": persisted,
            "title": body.title,
            "tags": body.tags,
            "proof_score": body.proof_score,
            "created_at": now.isoformat(),
            "message": (
                "Submission queued for moderation"
                if moderation_status == "pending"
                else "Submission failed automated checks; address reasons and resubmit"
            ),
        }

    @router.get("/publications")
    async def community_publications(limit: int = 25):
        """CF13 — Latest publish submissions (approved + pending), newest first."""
        await _ensure_publish_table()
        pool = await _get_pg_pool()
        rows = []
        if pool is not None:
            try:
                async with pool.acquire() as con:
                    recs = await con.fetch(
                        """
                        SELECT id, title, description, tags, proof_score,
                               moderation_status, created_at
                        FROM community_publications
                        WHERE moderation_status IN ('pending','approved')
                        ORDER BY created_at DESC
                        LIMIT $1
                        """,
                        max(1, min(100, int(limit))),
                    )
                    for r in recs:
                        rows.append({
                            "id": r["id"],
                            "title": r["title"],
                            "description": r["description"],
                            "tags": list(r["tags"] or []),
                            "proof_score": float(r["proof_score"] or 0),
                            "moderation_status": r["moderation_status"],
                            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                        })
            except Exception as exc:
                logger.warning("publications list failed: %s", exc)
        return {"status": "ready", "publications": rows, "count": len(rows)}

    return router


router = create_community_router()
