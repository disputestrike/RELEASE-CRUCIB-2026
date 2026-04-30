"""
Image generation via Together.ai. Generates hero and feature images for built apps.
Legal: Generated images are for user's app only; no scraping or unauthorized use.
"""

import json
import logging
import os
from typing import Any, Dict, Optional

from backend.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

TOGETHER_API_KEY = os.environ.get("TOGETHER_API_KEY")
IMAGE_MODEL = os.environ.get("TOGETHER_IMAGE_MODEL", "black-forest-labs/FLUX.1-schnell")


async def generate_image(prompt: str) -> Optional[str]:
    """
    Generate one image using Together.ai. Returns public URL or None if key missing/fails.
    """
    if not TOGETHER_API_KEY or not prompt or not prompt.strip():
        return None
    try:
        from together import Together

        client = Together(api_key=TOGETHER_API_KEY)
        response = client.images.generate(
            model=IMAGE_MODEL,
            prompt=prompt.strip()[:2000],
            steps=10,
            n=1,
            width=1024,
            height=1024,
            response_format="url",
        )
        if response.data and len(response.data) > 0:
            url = getattr(response.data[0], "url", None)
            if url:
                return url
            b64 = getattr(response.data[0], "b64_json", None)
            if b64:
                return f"data:image/png;base64,{b64}"
        return None
    except Exception as e:
        logger.warning("Together.ai image generation failed: %s", e)
        return None


def parse_image_prompts(llm_output: str) -> Dict[str, str]:
    """Parse LLM JSON output to get hero, feature_1, feature_2 prompts. Tolerate markdown code blocks."""
    text = (llm_output or "").strip()
    if not text:
        return {}
    # Strip markdown code block if present
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    try:
        data = json.loads(text)
        if not isinstance(data, dict):
            return {}
        return {
            k: (v if isinstance(v, str) else str(v))
            for k, v in data.items()
            if isinstance(v, str) and v.strip()
        }
    except json.JSONDecodeError:
        return {}


async def generate_images_for_app(
    design_description: str, prompts_dict: Optional[Dict[str, str]] = None
) -> Dict[str, str]:
    """
    Generate multiple images for an app. Either use prompts_dict (from Image Generation agent)
    or derive from design_description. Returns {"hero": "url", "feature_1": "url", "feature_2": "url"}.
    """
    images: Dict[str, str] = {}
    if prompts_dict:
        for key in ("hero", "feature_1", "feature_2"):
            p = (prompts_dict.get(key) or "").strip()
            if p:
                url = await generate_image(p)
                if url:
                    images[key] = url
    if not images and design_description:
        hero_prompt = f"Professional hero image for {design_description[:500]}. Modern, clean, professional."
        images["hero"] = (await generate_image(hero_prompt)) or ""
        fp = f"Feature showcase for {design_description[:500]}. Minimalist, professional."
        u1 = await generate_image(fp)
        if u1:
            images["feature_1"] = u1
        u2 = await generate_image(fp)
        if u2:
            images["feature_2"] = u2
    return {k: v for k, v in images.items() if v}
