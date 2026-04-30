"""
backend/services/ui_feedback_mapper.py
────────────────────────────────────────
Screenshot-diff → deterministic verdict mapper.

Spec: H – Preview + Operator Mode
Branch: engineering/master-list-closeout

Responsibilities:
  • Compare before/after screenshots
  • Produce a UiFeedbackReport with deterministic pass/fail verdict
  • Map page comments to actionable fix tasks
  • Integrates with preview_validator_agent where available
"""

from __future__ import annotations

import base64
import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class UiFeedbackReport:
    verdict:    str          # pass | fail | inconclusive
    score:      float        # 0.0 – 1.0 (1.0 = no visual regression)
    diff_hash:  Optional[str]
    issues:     List[str]    = field(default_factory=list)
    fix_tasks:  List[Dict]   = field(default_factory=list)
    raw:        Optional[Any] = None


class UiFeedbackMapper:
    """Compare screenshots and map visual feedback to fix tasks."""

    # ── Screenshot diff ────────────────────────────────────────────────────

    async def diff(
        self,
        *,
        before_url: Optional[str],
        after_url: Optional[str],
        threshold: float = 0.05,   # 5% pixel difference tolerance
    ) -> UiFeedbackReport:
        """
        Compare two screenshots.  Returns a UiFeedbackReport.
        Uses PIL/Pillow if available; otherwise falls back to hash comparison.
        """
        if not before_url or not after_url:
            return UiFeedbackReport(verdict="inconclusive", score=0.5, diff_hash=None,
                                    issues=["Missing before or after screenshot"])

        before_bytes = await self._fetch_image(before_url)
        after_bytes  = await self._fetch_image(after_url)

        if before_bytes is None or after_bytes is None:
            return UiFeedbackReport(verdict="inconclusive", score=0.5, diff_hash=None,
                                    issues=["Could not fetch screenshot bytes"])

        # Try PIL pixel diff
        report = self._pixel_diff(before_bytes, after_bytes, threshold)
        if report:
            return report

        # Fallback: hash comparison
        before_hash = hashlib.sha256(before_bytes).hexdigest()
        after_hash  = hashlib.sha256(after_bytes).hexdigest()
        if before_hash == after_hash:
            return UiFeedbackReport(verdict="pass", score=1.0, diff_hash=after_hash)
        return UiFeedbackReport(
            verdict="fail", score=0.0,
            diff_hash=after_hash,
            issues=["Screenshots differ (hash mismatch)"],
        )

    def _pixel_diff(self, before: bytes, after: bytes, threshold: float) -> Optional[UiFeedbackReport]:
        try:
            from PIL import Image, ImageChops
            import io
            img_a = Image.open(io.BytesIO(before)).convert("RGB")
            img_b = Image.open(io.BytesIO(after)).convert("RGB")
            if img_a.size != img_b.size:
                img_b = img_b.resize(img_a.size, Image.LANCZOS)
            diff = ImageChops.difference(img_a, img_b)
            pixels = list(diff.getdata())
            total = len(pixels)
            changed = sum(1 for p in pixels if any(c > 10 for c in p))
            diff_ratio = changed / total if total else 0
            score = 1.0 - diff_ratio
            diff_hash = hashlib.sha256(after).hexdigest()
            if diff_ratio <= threshold:
                return UiFeedbackReport(verdict="pass", score=score, diff_hash=diff_hash)
            return UiFeedbackReport(
                verdict="fail", score=score, diff_hash=diff_hash,
                issues=[f"Visual regression: {diff_ratio*100:.1f}% pixels changed (threshold {threshold*100:.0f}%)"],
            )
        except ImportError:
            return None
        except Exception as exc:
            logger.warning("[UiFeedbackMapper] pixel diff failed: %s", exc)
            return None

    async def _fetch_image(self, url: str) -> Optional[bytes]:
        """Fetch image bytes from URL or data URI."""
        if url.startswith("data:"):
            _, b64 = url.split(",", 1)
            return base64.b64decode(b64)
        try:
            import httpx
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(url)
                r.raise_for_status()
                return r.content
        except Exception as exc:
            logger.warning("[UiFeedbackMapper] fetch image failed: %s for %s", exc, url[:80])
            return None

    # ── Comment → fix task mapping ─────────────────────────────────────────

    def map_comments_to_tasks(self, comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert page comments into structured fix tasks."""
        tasks = []
        for c in comments:
            if c.get("status") in ("task_created",):
                continue
            task = {
                "task_id": c.get("id", ""),
                "title": f"Fix: {c.get('comment', '')[:80]}",
                "description": c.get("comment", ""),
                "region": c.get("region"),
                "screenshot_id": c.get("screenshot_id"),
                "priority": "medium",
                "source": "preview_comment",
            }
            tasks.append(task)
        return tasks

    # ── Preview validation ─────────────────────────────────────────────────

    async def validate_preview(
        self,
        *,
        url: str,
        expected_elements: Optional[List[str]] = None,
    ) -> UiFeedbackReport:
        """Validate a live preview by checking expected elements exist."""
        try:
            from ....agents.preview_validator_agent import PreviewValidatorAgent            agent = PreviewValidatorAgent()
            result = await agent.validate(url=url, expected_elements=expected_elements or [])
            issues = result.get("issues", [])
            score = 1.0 - min(len(issues) * 0.2, 1.0)
            return UiFeedbackReport(
                verdict="pass" if not issues else "fail",
                score=score,
                diff_hash=None,
                issues=issues,
                raw=result,
            )
        except ImportError:
            pass
        except Exception as exc:
            logger.warning("[UiFeedbackMapper] validate_preview failed: %s", exc)

        return UiFeedbackReport(verdict="inconclusive", score=0.5, diff_hash=None,
                                issues=["preview_validator_agent not available"])


# Module-level singleton
ui_feedback_mapper = UiFeedbackMapper()
