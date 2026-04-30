"""Wave 5 — Marketplace route.

Surfaces community_publications as a public marketplace with kind filtering,
single listing detail, install metadata, and featured listings.

Endpoints
---------
GET  /api/marketplace/listings          — all approved listings with proof_score >= 80
GET  /api/marketplace/listings/{id}     — single listing detail
POST /api/marketplace/listings/{id}/install — install metadata (no exec)
GET  /api/marketplace/featured          — top 6 by install_count
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Request

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])

_TABLE_CHECKED = False


async def _get_pool():
    try:
        from ....db_pg import get_db  # type: ignore        return await get_db()
    except Exception:
        return None


async def _ensure_install_count(pool):
    """Add install_count column to community_publications if missing (idempotent)."""
    global _TABLE_CHECKED
    if _TABLE_CHECKED:
        return
    if pool is None:
        return
    try:
        await pool.execute(
            "ALTER TABLE community_publications ADD COLUMN IF NOT EXISTS install_count bigint DEFAULT 0"
        )
        _TABLE_CHECKED = True
    except Exception as exc:
        logger.warning("marketplace ensure install_count failed: %s", exc)


def _row_to_dict(r: dict) -> dict:
    return {
        "id": r["id"],
        "title": r["title"],
        "description": r.get("description"),
        "tags": list(r.get("tags") or []),
        "proof_score": float(r.get("proof_score") or 0),
        "kind": _infer_kind(r),
        "install_count": int(r.get("install_count") or 0),
        "published_at": r["published_at"].isoformat() if r.get("published_at") else None,
        "preview_url": r.get("preview_url"),
        "user_id": r.get("user_id"),
    }


def _infer_kind(r: dict) -> str:
    """Infer listing kind from tags or default to 'template'."""
    tags = [t.lower() for t in (r.get("tags") or [])]
    for kind in ("plugin", "skill", "mcp"):
        if kind in tags:
            return kind
    return "template"


@router.get("/listings")
async def list_marketplace(kind: Optional[str] = None):
    """GET /api/marketplace/listings — approved listings with proof_score >= 80."""
    pool = await _get_pool()
    if pool is None:
        return {"listings": [], "degraded": True}

    await _ensure_install_count(pool)

    try:
        rows = await pool.fetch(
            """
            SELECT id, user_id, title, description, tags, proof_score,
                   approved_at AS published_at, preview_url,
                   COALESCE(install_count, 0) AS install_count
            FROM community_publications
            WHERE proof_score >= 80
              AND moderation_status = 'approved'
            ORDER BY approved_at DESC NULLS LAST
            LIMIT 100
            """
        )
        listings = [_row_to_dict(dict(r)) for r in rows]
        if kind:
            listings = [l for l in listings if l["kind"] == kind]
        return {"listings": listings, "count": len(listings)}
    except Exception as exc:
        logger.warning("marketplace listings failed: %s", exc)
        return {"listings": [], "degraded": True}


@router.get("/listings/{listing_id}")
async def get_listing(listing_id: str):
    """GET /api/marketplace/listings/{id} — single listing detail."""
    pool = await _get_pool()
    if pool is None:
        raise HTTPException(status_code=503, detail="Database unavailable")

    await _ensure_install_count(pool)

    try:
        row = await pool.fetchrow(
            """
            SELECT id, user_id, title, description, tags, proof_score,
                   approved_at AS published_at, preview_url, prompt,
                   COALESCE(install_count, 0) AS install_count
            FROM community_publications
            WHERE id = $1 AND moderation_status = 'approved'
            """,
            listing_id,
        )
    except Exception as exc:
        logger.warning("marketplace get_listing failed: %s", exc)
        raise HTTPException(status_code=503, detail="Database error")

    if row is None:
        raise HTTPException(status_code=404, detail="Listing not found")

    data = _row_to_dict(dict(row))
    data["prompt"] = row.get("prompt")
    return data


@router.post("/listings/{listing_id}/install")
async def install_listing(listing_id: str):
    """POST /api/marketplace/listings/{id}/install — returns install metadata, no exec."""
    pool = await _get_pool()

    listing_kind = "template"
    listing_title = listing_id

    if pool is not None:
        try:
            await _ensure_install_count(pool)
            row = await pool.fetchrow(
                "SELECT id, title, tags FROM community_publications WHERE id = $1 AND moderation_status = 'approved'",
                listing_id,
            )
            if row is None:
                raise HTTPException(status_code=404, detail="Listing not found")
            listing_title = row["title"]
            listing_kind = _infer_kind(dict(row))
            # increment install_count
            await pool.execute(
                "UPDATE community_publications SET install_count = COALESCE(install_count,0) + 1 WHERE id = $1",
                listing_id,
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("marketplace install failed: %s", exc)

    kind_to_cmd = {
        "plugin": f"crucibai plugin install {listing_id}",
        "skill": f"crucibai skill add {listing_id}",
        "mcp": f"crucibai mcp enable {listing_id}",
        "template": f"crucibai template clone {listing_id}",
    }
    return {
        "listing_id": listing_id,
        "title": listing_title,
        "type": listing_kind,
        "install_cmd": kind_to_cmd.get(listing_kind, f"crucibai install {listing_id}"),
        "docs_url": f"https://docs.crucibai.com/marketplace/{listing_id}",
    }


@router.get("/featured")
async def featured_listings():
    """GET /api/marketplace/featured — top 6 by install_count."""
    pool = await _get_pool()
    if pool is None:
        return {"listings": [], "degraded": True}

    await _ensure_install_count(pool)

    try:
        rows = await pool.fetch(
            """
            SELECT id, user_id, title, description, tags, proof_score,
                   approved_at AS published_at, preview_url,
                   COALESCE(install_count, 0) AS install_count
            FROM community_publications
            WHERE moderation_status = 'approved'
            ORDER BY install_count DESC NULLS LAST
            LIMIT 6
            """
        )
        return {"listings": [_row_to_dict(dict(r)) for r in rows]}
    except Exception as exc:
        logger.warning("marketplace featured failed: %s", exc)
        return {"listings": [], "degraded": True}
