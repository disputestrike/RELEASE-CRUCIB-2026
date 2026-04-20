"""
backend/services/preview_session.py
──────────────────────────────────────
Preview session management.

Spec: H – Preview + Operator Mode
Branch: engineering/master-list-closeout

Responsibilities:
  • Delegates to existing project_preview_service + preview_manager
  • Opens local / deployed preview
  • Tracks open sessions
  • Stores screenshots linked to thread
  • Converts page comments into fix tasks
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class PreviewSession:
    session_id: str
    thread_id:  Optional[str]
    url:        str
    status:     str = "open"         # open | closed | error
    screenshots: List[str] = field(default_factory=list)
    comments:    List[Dict] = field(default_factory=list)
    created_at:  str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PreviewSessionService:
    """Manage browser preview sessions linked to agent threads."""

    def __init__(self) -> None:
        self._sessions: Dict[str, PreviewSession] = {}

    # ── Session lifecycle ──────────────────────────────────────────────────

    async def open(
        self,
        *,
        url: str,
        thread_id: Optional[str] = None,
        project_id: Optional[str] = None,
        db: Optional[Any] = None,
    ) -> PreviewSession:
        """Open a preview session for *url*."""
        session_id = str(uuid.uuid4())
        # Delegate URL resolution to existing preview_manager if available
        resolved_url = await self._resolve_url(url, project_id)
        session = PreviewSession(session_id=session_id, thread_id=thread_id, url=resolved_url)
        self._sessions[session_id] = session
        logger.info("[PreviewSession] opened %s → %s", session_id, resolved_url)
        return session

    async def close(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session:
            session.status = "closed"
            return True
        return False

    def get(self, session_id: str) -> Optional[PreviewSession]:
        return self._sessions.get(session_id)

    # ── Screenshot ────────────────────────────────────────────────────────

    async def take_screenshot(
        self,
        *,
        session_id: str,
        user_id: str = "system",
        db: Optional[Any] = None,
    ) -> Optional[Dict[str, Any]]:
        """Take a screenshot via operator_runner and store the record."""
        session = self._sessions.get(session_id)
        if not session:
            return None
        try:
            from services.operator_runner import operator_runner
            screenshot_url = await operator_runner.screenshot(session.url)
        except Exception as exc:
            logger.warning("[PreviewSession] screenshot failed: %s", exc)
            screenshot_url = None

        screenshot_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        if db is not None and screenshot_url:
            try:
                import json
                await db.execute(
                    """INSERT INTO screenshots (id, thread_id, run_id, url, mime_type, metadata, created_at)
                       VALUES (:id, :thread_id, :run_id, :url, :mime_type, :metadata::jsonb, :created_at)
                       ON CONFLICT (id) DO NOTHING""",
                    {
                        "id": screenshot_id,
                        "thread_id": session.thread_id,
                        "run_id": None,
                        "url": screenshot_url,
                        "mime_type": "image/png",
                        "metadata": json.dumps({"session_id": session_id, "page_url": session.url}),
                        "created_at": now,
                    },
                )
            except Exception as exc:
                logger.warning("[PreviewSession] screenshot persist failed: %s", exc)

        if screenshot_url:
            session.screenshots.append(screenshot_url)
        return {"screenshot_id": screenshot_id, "url": screenshot_url}

    # ── Comments ──────────────────────────────────────────────────────────

    async def add_comment(
        self,
        *,
        session_id: str,
        comment: str,
        region: Optional[Dict[str, int]] = None,
        screenshot_id: Optional[str] = None,
        user_id: str = "system",
        db: Optional[Any] = None,
    ) -> Optional[str]:
        """Add a page comment, optionally pinned to a region."""
        session = self._sessions.get(session_id)
        if not session:
            return None
        comment_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        comment_doc = {
            "id": comment_id,
            "thread_id": session.thread_id,
            "screenshot_id": screenshot_id,
            "user_id": user_id,
            "comment": comment,
            "region": region,
            "status": "open",
            "created_at": now,
        }
        session.comments.append(comment_doc)

        if db is not None:
            try:
                import json
                await db.execute(
                    """INSERT INTO preview_comments
                       (id, thread_id, screenshot_id, user_id, comment, region, status, created_at)
                       VALUES (:id, :thread_id, :screenshot_id, :user_id, :comment, :region::jsonb, :status, :created_at)
                       ON CONFLICT (id) DO NOTHING""",
                    {
                        "id": comment_id,
                        "thread_id": session.thread_id,
                        "screenshot_id": screenshot_id,
                        "user_id": user_id,
                        "comment": comment,
                        "region": json.dumps(region or {}),
                        "status": "open",
                        "created_at": now,
                    },
                )
            except Exception as exc:
                logger.warning("[PreviewSession] comment persist failed: %s", exc)

        return comment_id

    # ── URL resolution ────────────────────────────────────────────────────

    async def _resolve_url(self, url: str, project_id: Optional[str]) -> str:
        """Resolve URL using existing preview_manager if possible."""
        if url.startswith("http"):
            return url
        try:
            from adapter.services.preview_manager import get_preview_url
            resolved = await get_preview_url(project_id or url)
            return resolved or url
        except Exception:
            pass
        return url


# Module-level singleton
preview_session_service = PreviewSessionService()
