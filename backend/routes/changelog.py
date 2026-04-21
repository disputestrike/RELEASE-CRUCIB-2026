"""Wave 3 — Changelog endpoint.

Serves the last 50 Git commits from the repo so the frontend Changelog page
can display a live commit timeline without a separate CI/CD pipeline or a
static JSON file.

GET /api/changelog
    Returns up to 50 commits with sha, subject, ISO-8601 date, and author.
    If Git is unavailable (e.g. Docker image without .git) the endpoint
    degrades gracefully and returns {commits: [], degraded: true}.
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/changelog", tags=["changelog"])

# Repo root is two levels above backend/routes/
_REPO_ROOT = Path(__file__).resolve().parents[2]


def _parse_commits(raw: str) -> List[Dict[str, Any]]:
    commits: List[Dict[str, Any]] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t", 3)
        if len(parts) < 4:
            # Malformed line — skip gracefully
            continue
        sha, subject, committed_at, author = parts
        commits.append(
            {
                "sha": sha,
                "subject": subject,
                "committed_at": committed_at,
                "author": author,
            }
        )
    return commits


@router.get("")
async def changelog():
    """Return the last 50 commits from the repository."""
    try:
        raw = subprocess.check_output(
            ["git", "log", "--pretty=format:%h\t%s\t%cI\t%an", "-50"],
            cwd=str(_REPO_ROOT),
            stderr=subprocess.DEVNULL,
            timeout=10,
        ).decode("utf-8", errors="replace")
        commits = _parse_commits(raw)
        return {"commits": commits, "count": len(commits), "degraded": False}
    except Exception as exc:
        logger.warning("git log failed: %s", exc)
        return {"commits": [], "count": 0, "degraded": True}
