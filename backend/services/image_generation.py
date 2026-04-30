"""
backend/services/image_generation.py
──────────────────────────────────────
Pluggable image generation entrypoint.

Spec: K – Image Generation
Branch: engineering/master-list-closeout

Wraps agents/image_generator.py (Together.ai FLUX-schnell).
Adds:
  • Multi-provider support (Together, OpenAI DALL·E, Stability.ai)
  • Artifact row emission on completion
  • Consistent return type: ImageResult
"""

from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Result type
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ImageResult:
    image_id:    str
    url:         Optional[str]
    prompt:      str
    provider:    str
    model:       str
    artifact_id: Optional[str] = None
    error:       Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Provider implementations
# ─────────────────────────────────────────────────────────────────────────────

async def _generate_together(prompt: str, model: str) -> Optional[str]:
    """Together.ai FLUX-schnell provider (existing implementation)."""
    try:
        from ....agents.image_generator import generate_image        return await generate_image(prompt)
    except Exception as exc:
        logger.warning("[image_generation] together failed: %s", exc)
        return None


async def _generate_openai(prompt: str, model: str) -> Optional[str]:
    """OpenAI DALL·E 3 provider."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return None
    try:
        import httpx
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                "https://api.openai.com/v1/images/generations",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": model, "prompt": prompt[:4000], "n": 1, "size": "1024x1024"},
            )
            r.raise_for_status()
            data = r.json().get("data", [])
            return data[0].get("url") if data else None
    except Exception as exc:
        logger.warning("[image_generation] openai failed: %s", exc)
        return None


async def _generate_stability(prompt: str, model: str) -> Optional[str]:
    """Stability.ai provider."""
    api_key = os.environ.get("STABILITY_API_KEY", "")
    if not api_key:
        return None
    try:
        import httpx
        import base64
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.post(
                "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image",
                headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
                json={"text_prompts": [{"text": prompt[:2000]}], "samples": 1},
            )
            r.raise_for_status()
            artifacts = r.json().get("artifacts", [])
            if artifacts:
                b64 = artifacts[0].get("base64", "")
                return f"data:image/png;base64,{b64}"
            return None
    except Exception as exc:
        logger.warning("[image_generation] stability failed: %s", exc)
        return None


# Provider chain — tried in order, first success wins.
# Keep function names here so callables are resolved at runtime.
_PROVIDER_SPECS = [
    ("together",   "black-forest-labs/FLUX.1-schnell", "_generate_together"),
    ("openai",     "dall-e-3",                         "_generate_openai"),
    ("stability",  "stable-diffusion-xl",              "_generate_stability"),
]


def _providers() -> List[tuple[str, str, Any]]:
    providers: List[tuple[str, str, Any]] = []
    for provider_name, model_name, fn_name in _PROVIDER_SPECS:
        fn = globals().get(fn_name)
        if fn is not None:
            providers.append((provider_name, model_name, fn))
    return providers


# ─────────────────────────────────────────────────────────────────────────────
# ImageGenerationService
# ─────────────────────────────────────────────────────────────────────────────

class ImageGenerationService:
    """
    Generate images from prompts.  Emits an artifact row on success.

    Usage::

        result = await image_generation.generate(
            prompt="Hero image for a SaaS dashboard",
            context_type="landing_visual",
            thread_id="...",
            user_id="...",
            db=db,
        )
    """

    async def generate(
        self,
        *,
        prompt: str,
        context_type: str = "ui_concept",    # ui_concept|landing_visual|feature_mockup|slide_asset|design_idea
        thread_id: Optional[str] = None,
        run_id: Optional[str] = None,
        user_id: str = "system",
        db: Optional[Any] = None,
        preferred_provider: Optional[str] = None,
    ) -> ImageResult:
        """Generate an image and optionally persist as an artifact."""
        image_id = str(uuid.uuid4())
        url: Optional[str] = None
        used_provider = ""
        used_model = ""

        # Try providers in order (or skip to preferred)
        ordered = _providers()
        if preferred_provider:
            ordered = [p for p in ordered if p[0] == preferred_provider] + \
                      [p for p in ordered if p[0] != preferred_provider]

        for provider_name, model_name, fn in ordered:
            url = await fn(prompt, model_name)
            if url:
                used_provider = provider_name
                used_model = model_name
                break

        if not url:
            return ImageResult(image_id=image_id, url=None, prompt=prompt,
                               provider="none", model="none", error="All providers failed")

        artifact_id: Optional[str] = None
        if db is not None:
            artifact_id = await self._emit_artifact(
                image_id=image_id,
                url=url,
                prompt=prompt,
                context_type=context_type,
                thread_id=thread_id,
                run_id=run_id,
                user_id=user_id,
                provider=used_provider,
                db=db,
            )

        return ImageResult(
            image_id=image_id,
            url=url,
            prompt=prompt,
            provider=used_provider,
            model=used_model,
            artifact_id=artifact_id,
        )

    async def generate_batch(
        self,
        *,
        prompts: Dict[str, str],
        thread_id: Optional[str] = None,
        user_id: str = "system",
        db: Optional[Any] = None,
    ) -> Dict[str, ImageResult]:
        """Generate multiple images (e.g. hero + feature_1 + feature_2)."""
        results: Dict[str, ImageResult] = {}
        for key, prompt in prompts.items():
            results[key] = await self.generate(
                prompt=prompt,
                context_type=key,
                thread_id=thread_id,
                user_id=user_id,
                db=db,
            )
        return results

    async def _emit_artifact(
        self,
        *,
        image_id: str,
        url: str,
        prompt: str,
        context_type: str,
        thread_id: Optional[str],
        run_id: Optional[str],
        user_id: str,
        provider: str,
        db: Any,
    ) -> Optional[str]:
        """Write an artifact row linking to the generated image."""
        import json
        artifact_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        try:
            await db.execute(
                """INSERT INTO artifacts
                   (id, thread_id, run_id, user_id, artifact_type, title, download_url, mime_type, metadata, version, created_at)
                   VALUES (:id, :thread_id, :run_id, :user_id, :artifact_type, :title, :download_url, :mime_type, :metadata::jsonb, 1, :created_at)
                   ON CONFLICT (id) DO NOTHING""",
                {
                    "id": artifact_id,
                    "thread_id": thread_id,
                    "run_id": run_id,
                    "user_id": user_id,
                    "artifact_type": "image",
                    "title": f"Image: {context_type} — {prompt[:60]}",
                    "download_url": url,
                    "mime_type": "image/png",
                    "metadata": json.dumps({
                        "image_id": image_id,
                        "prompt": prompt,
                        "context_type": context_type,
                        "provider": provider,
                    }),
                    "created_at": now,
                },
            )
            return artifact_id
        except Exception as exc:
            logger.warning("[image_generation] artifact emit failed: %s", exc)
            return None


# Module-level singleton
image_generation = ImageGenerationService()
