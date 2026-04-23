"""
/api/images/* — image generation endpoints (CF4).

Wraps services.image_generation.ImageGenerationService so WorkspaceV3 (and any
external caller) can generate an image and get back a uniform artifact record.
"""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request

router = APIRouter(prefix="/api/images", tags=["images"])


def _get_auth():
    from ..server import get_current_user
    return get_current_user


def _result_to_dict(r: Any) -> Dict[str, Any]:
    if hasattr(r, "to_dict"):
        return r.to_dict()  # type: ignore[no-any-return]
    if hasattr(r, "__dict__") and not isinstance(r, dict):
        try:
            return asdict(r)
        except TypeError:
            return dict(r.__dict__)
    if isinstance(r, dict):
        return r
    return {"value": repr(r)}


@router.post("/generate")
async def generate_image(
    request: Request,
    user: dict = Depends(_get_auth()),
) -> Dict[str, Any]:
    """Generate an image from a text prompt. Returns the ImageResult record."""
    from ..services.image_generation import image_generation

    body = await request.json()
    prompt = (body.get("prompt") or "").strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="prompt is required")

    context_type = body.get("context_type", "ui_concept")
    thread_id = body.get("thread_id")
    run_id = body.get("run_id")
    preferred_provider = body.get("provider")  # optional
    user_id = user.get("id") or user.get("sub", "anon")

    db = None
    try:
        from ..db_pg import get_db
        db = await get_db()
    except Exception:
        db = None

    try:
        result = await image_generation.generate(
            prompt=prompt,
            context_type=context_type,
            thread_id=thread_id,
            run_id=run_id,
            user_id=user_id,
            db=db,
            preferred_provider=preferred_provider,
        )
        return _result_to_dict(result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"image_generation failed: {exc}")


@router.post("/batch")
async def generate_image_batch(
    request: Request,
    user: dict = Depends(_get_auth()),
) -> Dict[str, Any]:
    """Generate multiple images (map of context_type -> prompt). Returns list."""
    from ..services.image_generation import image_generation

    body = await request.json()
    prompts = body.get("prompts") or {}
    if not isinstance(prompts, dict) or not prompts:
        raise HTTPException(status_code=400, detail="prompts must be a non-empty map")

    thread_id = body.get("thread_id")
    run_id = body.get("run_id")
    preferred_provider = body.get("provider")
    user_id = user.get("id") or user.get("sub", "anon")

    db = None
    try:
        from ..db_pg import get_db
        db = await get_db()
    except Exception:
        db = None

    try:
        results = await image_generation.generate_batch(
            prompts=prompts,
            thread_id=thread_id,
            run_id=run_id,
            user_id=user_id,
            db=db,
            preferred_provider=preferred_provider,
        )
        out = [_result_to_dict(r) for r in (results or [])]
        return {"results": out, "count": len(out)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"image_generation batch failed: {exc}")
