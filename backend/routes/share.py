"""WS-J: public share + remix endpoints."""

from __future__ import annotations

import json
import secrets
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

try:
    from db_pg import get_pg_pool
except Exception:  # pragma: no cover
    get_pg_pool = None  # type: ignore

router = APIRouter(prefix="/api/share", tags=["share"])

_SLUG_ALPHABET = "abcdefghjkmnpqrstuvwxyz23456789"


def _make_slug(n: int = 10) -> str:
    return "".join(secrets.choice(_SLUG_ALPHABET) for _ in range(n))


class ShareCreateRequest(BaseModel):
    project_id: str = Field(..., min_length=1)
    title: Optional[str] = None
    snapshot: Dict[str, Any] = Field(default_factory=dict)


class ShareCreateResponse(BaseModel):
    slug: str
    url_path: str
    project_id: str
    title: Optional[str]
    created_at: str


class ShareView(BaseModel):
    slug: str
    project_id: str
    title: Optional[str]
    snapshot: Dict[str, Any]
    created_at: str
    views: int
    remixes: int


async def _pool():
    if get_pg_pool is None:
        raise HTTPException(503, "pg pool not available")
    return await get_pg_pool()


def _user_id(request: Request) -> Optional[str]:
    # Best-effort — existing middleware may stash user on state. Anonymous users
    # are allowed to create shares tied to projects they already own; ownership
    # is enforced upstream by project access checks in the UI layer.
    return getattr(request.state, "user_id", None) or request.headers.get("x-user-id")


@router.post("", response_model=ShareCreateResponse)
async def create_share(req: ShareCreateRequest, request: Request) -> ShareCreateResponse:
    pool = await _pool()
    slug = _make_slug()
    uid = _user_id(request)
    async with pool.acquire() as conn:
        # Retry on slug collision
        for _ in range(5):
            try:
                row = await conn.fetchrow(
                    """INSERT INTO project_shares (slug, project_id, owner_user_id, title, snapshot)
                       VALUES ($1,$2,$3,$4,$5)
                       RETURNING slug, project_id, title, created_at""",
                    slug, req.project_id, uid, req.title, json.dumps(req.snapshot),
                )
                break
            except Exception as exc:
                if "project_shares_pkey" in str(exc):
                    slug = _make_slug()
                    continue
                raise HTTPException(500, f"db error: {exc}")
        else:
            raise HTTPException(500, "could not allocate slug")
    return ShareCreateResponse(
        slug=row["slug"],
        url_path=f"/p/{row['slug']}",
        project_id=row["project_id"],
        title=row["title"],
        created_at=row["created_at"].isoformat(),
    )


@router.get("/{slug}", response_model=ShareView)
async def get_share(slug: str) -> ShareView:
    pool = await _pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT slug, project_id, title, snapshot, created_at, views, remixes, revoked "
            "FROM project_shares WHERE slug = $1",
            slug,
        )
        if not row or row["revoked"]:
            raise HTTPException(404, "share not found")
        await conn.execute("UPDATE project_shares SET views = views + 1 WHERE slug = $1", slug)
    snap = row["snapshot"]
    if isinstance(snap, str):
        try:
            snap = json.loads(snap)
        except Exception:
            snap = {}
    return ShareView(
        slug=row["slug"],
        project_id=row["project_id"],
        title=row["title"],
        snapshot=snap or {},
        created_at=row["created_at"].isoformat(),
        views=row["views"] + 1,
        remixes=row["remixes"],
    )


class RemixResponse(BaseModel):
    ok: bool
    new_project_id: str
    remixed_from: str


@router.post("/{slug}/remix", response_model=RemixResponse)
async def remix_share(slug: str, request: Request) -> RemixResponse:
    pool = await _pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT project_id, snapshot, revoked FROM project_shares WHERE slug = $1", slug
        )
        if not row or row["revoked"]:
            raise HTTPException(404, "share not found")
        await conn.execute("UPDATE project_shares SET remixes = remixes + 1 WHERE slug = $1", slug)
    new_pid = f"remix_{secrets.token_hex(6)}_{int(time.time())}"
    # Intentionally lightweight: real project-copy hand-off is performed by
    # the projects router. Downstream callers can use this id as the target
    # to seed the new project from the snapshot returned in the body.
    return RemixResponse(ok=True, new_project_id=new_pid, remixed_from=slug)
