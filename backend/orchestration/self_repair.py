"""
Deterministic verification self-repair + optional git commit for generated workspaces.

The executor owns the multi-attempt loop (CRUCIBAI_INNER_VERIFY_REPAIR_MAX).
Set CRUCIBAI_VERIFICATION_AUTO_COMMIT=1 to record patches as local commits inside the job workspace.
"""
from __future__ import annotations

import logging
import os
import subprocess
from typing import Any, Dict, List

from .fixer import try_deterministic_verification_fix

logger = logging.getLogger(__name__)


def attempt_verification_self_repair(
    step_key: str,
    workspace_path: str,
    verification_result: Dict[str, Any],
) -> List[str]:
    """Return posix-relative paths modified under workspace (may be empty)."""
    return try_deterministic_verification_fix(step_key, workspace_path, verification_result)


def _auto_commit_enabled() -> bool:
    return os.environ.get("CRUCIBAI_VERIFICATION_AUTO_COMMIT", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def maybe_commit_workspace_repairs(
    workspace_path: str,
    changed_paths: List[str],
    *,
    job_id: str | None = None,
    step_key: str | None = None,
) -> bool:
    """
    If CRUCIBAI_VERIFICATION_AUTO_COMMIT is set, git add/commit changed files in workspace_path.
    Returns True if a commit was created (or would have been a no-op with nothing staged).
    """
    if not _auto_commit_enabled():
        return False
    if not workspace_path or not os.path.isdir(workspace_path):
        return False
    paths = [p for p in changed_paths if p and not p.startswith("..")]
    if not paths:
        return False
    # Only operate inside a git worktree
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if r.returncode != 0 or "true" not in (r.stdout or "").lower():
            logger.info("self_repair: skip commit — not a git worktree at %s", workspace_path)
            return False
    except (OSError, subprocess.TimeoutExpired) as e:
        logger.warning("self_repair: git probe failed: %s", e)
        return False

    norm_paths = [os.path.normpath(os.path.join(workspace_path, *p.split("/"))) for p in paths]
    for fp in norm_paths:
        if not fp.startswith(os.path.normpath(workspace_path)):
            logger.warning("self_repair: skip out-of-tree path %s", fp)
            return False

    msg_parts = ["chore(crucibai): auto-repair verification"]
    if step_key:
        msg_parts.append(f"step={step_key}")
    if job_id:
        msg_parts.append(f"job={job_id}")
    message = " ".join(msg_parts)

    try:
        add = subprocess.run(
            ["git", "add", "--"] + norm_paths,
            cwd=workspace_path,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if add.returncode != 0:
            logger.warning("self_repair: git add failed: %s", (add.stderr or add.stdout or "").strip()[:500])
            return False
        commit = subprocess.run(
            ["git", "commit", "-m", message, "--no-verify"],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if commit.returncode != 0:
            # Nothing to commit is OK
            out = (commit.stderr or commit.stdout or "").lower()
            if "nothing to commit" in out or "no changes added" in out:
                return False
            logger.warning(
                "self_repair: git commit failed: %s",
                (commit.stderr or commit.stdout or "").strip()[:500],
            )
            return False
        logger.info("self_repair: committed verification repair in %s", workspace_path)
        return True
    except (OSError, subprocess.TimeoutExpired) as e:
        logger.warning("self_repair: git commit error: %s", e)
        return False
