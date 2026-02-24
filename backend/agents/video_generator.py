"""
Video placeholders via Pexels API. Finds relevant stock videos for app hero/feature sections.
Legal: Pexels content is free to use; we only search and return URLs per their API terms.
"""
import os
from agents.base_agent import BaseAgent
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
PEXELS_VIDEO_SEARCH = "https://api.pexels.com/videos/search"


async def find_video(query: str) -> Optional[str]:
    """
    Search Pexels for one video matching query. Returns HD video URL or None.
    """
    if not PEXELS_API_KEY or not query or not query.strip():
        return None
    try:
        import httpx
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(
                PEXELS_VIDEO_SEARCH,
                params={"query": query.strip()[:200], "per_page": 1, "orientation": "landscape"},
                headers={"Authorization": PEXELS_API_KEY},
            )
            r.raise_for_status()
            data = r.json()
        videos = data.get("videos") or []
        if not videos:
            return None
        video = videos[0]
        files = video.get("video_files") or []
        # Prefer HD (width >= 1280 or 720)
        best = None
        for f in files:
            url = f.get("link")
            w = f.get("width") or 0
            if url and w >= 1280:
                return url
            if url and not best:
                best = url
        return best or (files[0].get("link") if files else None)
    except Exception as e:
        logger.warning("Pexels video search failed: %s", e)
        return None


def parse_video_queries(llm_output: str) -> Dict[str, str]:
    """Parse LLM JSON to get hero and feature video search queries."""
    import json
    text = (llm_output or "").strip()
    if not text:
        return {}
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    try:
        data = json.loads(text)
        if not isinstance(data, dict):
            return {}
        return {k: (v if isinstance(v, str) else str(v)) for k, v in data.items() if isinstance(v, str) and v.strip()}
    except json.JSONDecodeError:
        return {}


async def generate_videos_for_app(design_description: str, queries_dict: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Find stock videos for an app. Returns {"hero": "url", "feature": "url"} (keys missing if not found).
    """
    videos: Dict[str, str] = {}
    if queries_dict:
        for key in ("hero", "feature"):
            q = (queries_dict.get(key) or "").strip()
            if q:
                url = await find_video(q)
                if url:
                    videos[key] = url
    if not videos and design_description:
        hero_url = await find_video(f"professional {design_description[:200]}")
        if hero_url:
            videos["hero"] = hero_url
        feat_url = await find_video(f"tech {design_description[:200]}")
        if feat_url:
            videos["feature"] = feat_url
    return videos
