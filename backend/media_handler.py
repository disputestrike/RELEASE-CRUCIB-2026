"""
Media Handler: Manages image/video generation with fallbacks.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class MediaHandler:
    """Handles media generation with graceful fallbacks."""

    # Fallback image URLs (placeholder service)
    FALLBACK_IMAGES = {
        "hero": "https://via.placeholder.com/1920x1080/1A1A1A/FFFFFF?text=Hero+Image",
        "feature_1": "https://via.placeholder.com/800x600/2A2A2A/FFFFFF?text=Feature+1",
        "feature_2": "https://via.placeholder.com/800x600/2A2A2A/FFFFFF?text=Feature+2",
        "feature_3": "https://via.placeholder.com/800x600/2A2A2A/FFFFFF?text=Feature+3",
        "testimonial": "https://via.placeholder.com/200x200/3A3A3A/FFFFFF?text=Testimonial",
        "cta": "https://via.placeholder.com/600x400/1A1A1A/FFFFFF?text=Call+to+Action",
    }

    # Fallback video URLs (from Pexels)
    FALLBACK_VIDEOS = {
        "hero": "https://videos.pexels.com/video-files/3571200/3571200-sd_640_360_30fps.mp4",
        "background": "https://videos.pexels.com/video-files/3571198/3571198-sd_640_360_30fps.mp4",
        "feature": "https://videos.pexels.com/video-files/3571199/3571199-sd_640_360_30fps.mp4",
    }

    def __init__(self, together_api_key: Optional[str] = None):
        self.together_api_key = together_api_key
        self.generation_failures = {}

    async def generate_image(
        self, prompt: str, image_type: str = "feature", fallback: bool = True
    ) -> Dict[str, Any]:
        """
        Generate image with fallback.

        Returns: {
            "success": bool,
            "url": str,
            "used_fallback": bool,
            "error": str
        }
        """
        try:
            # Try to generate with Together.ai
            if self.together_api_key:
                result = await self._generate_with_together(prompt)
                if result.get("success"):
                    return result

                logger.warning(f"Together.ai generation failed: {result.get('error')}")

            # Fallback to placeholder
            if fallback:
                logger.info(f"Using fallback image for {image_type}")
                return {
                    "success": True,
                    "url": self.FALLBACK_IMAGES.get(
                        image_type, self.FALLBACK_IMAGES["feature_1"]
                    ),
                    "used_fallback": True,
                    "error": None,
                }

            return {
                "success": False,
                "url": None,
                "used_fallback": False,
                "error": "Image generation failed and fallback disabled",
            }

        except Exception as e:
            logger.error(f"Image generation error: {e}")

            if fallback:
                return {
                    "success": True,
                    "url": self.FALLBACK_IMAGES.get(
                        image_type, self.FALLBACK_IMAGES["feature_1"]
                    ),
                    "used_fallback": True,
                    "error": str(e),
                }

            return {
                "success": False,
                "url": None,
                "used_fallback": False,
                "error": str(e),
            }

    async def generate_video(
        self, prompt: str, video_type: str = "feature", fallback: bool = True
    ) -> Dict[str, Any]:
        """
        Generate video with fallback.

        Returns: {
            "success": bool,
            "url": str,
            "used_fallback": bool,
            "error": str
        }
        """
        try:
            # Try to generate with Together.ai or Pexels
            if self.together_api_key:
                result = await self._generate_video_with_together(prompt)
                if result.get("success"):
                    return result

                logger.warning(
                    f"Together.ai video generation failed: {result.get('error')}"
                )

            # Fallback to Pexels video
            if fallback:
                logger.info(f"Using fallback video for {video_type}")
                return {
                    "success": True,
                    "url": self.FALLBACK_VIDEOS.get(
                        video_type, self.FALLBACK_VIDEOS["feature"]
                    ),
                    "used_fallback": True,
                    "error": None,
                }

            return {
                "success": False,
                "url": None,
                "used_fallback": False,
                "error": "Video generation failed and fallback disabled",
            }

        except Exception as e:
            logger.error(f"Video generation error: {e}")

            if fallback:
                return {
                    "success": True,
                    "url": self.FALLBACK_VIDEOS.get(
                        video_type, self.FALLBACK_VIDEOS["feature"]
                    ),
                    "used_fallback": True,
                    "error": str(e),
                }

            return {
                "success": False,
                "url": None,
                "used_fallback": False,
                "error": str(e),
            }

    async def _generate_with_together(self, prompt: str) -> Dict[str, Any]:
        """Generate image with Together.ai API."""
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.together_api_key}",
                    "Content-Type": "application/json",
                }

                data = {
                    "model": "black-forest-labs/FLUX.1-schnell",
                    "prompt": prompt,
                    "width": 1024,
                    "height": 768,
                    "steps": 1,
                    "n": 1,
                }

                async with session.post(
                    "https://api.together.xyz/v1/images/generations",
                    json=data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        if result.get("data") and len(result["data"]) > 0:
                            return {
                                "success": True,
                                "url": result["data"][0].get("url"),
                                "used_fallback": False,
                                "error": None,
                            }

                    error_text = await resp.text()
                    return {
                        "success": False,
                        "url": None,
                        "used_fallback": False,
                        "error": f"API error: {resp.status} - {error_text}",
                    }

        except Exception as e:
            return {
                "success": False,
                "url": None,
                "used_fallback": False,
                "error": str(e),
            }

    async def _generate_video_with_together(self, prompt: str) -> Dict[str, Any]:
        """Generate video with Together.ai API (if available)."""
        # Together.ai doesn't have video generation yet
        # Return failure to trigger fallback
        return {
            "success": False,
            "url": None,
            "used_fallback": False,
            "error": "Video generation not available",
        }

    def get_fallback_image(self, image_type: str) -> str:
        """Get fallback image URL."""
        return self.FALLBACK_IMAGES.get(image_type, self.FALLBACK_IMAGES["feature_1"])

    def get_fallback_video(self, video_type: str) -> str:
        """Get fallback video URL."""
        return self.FALLBACK_VIDEOS.get(video_type, self.FALLBACK_VIDEOS["feature"])

    def get_media_stats(self) -> Dict[str, Any]:
        """Get media generation statistics."""
        return {
            "fallback_images_available": len(self.FALLBACK_IMAGES),
            "fallback_videos_available": len(self.FALLBACK_VIDEOS),
            "generation_failures": self.generation_failures,
        }
