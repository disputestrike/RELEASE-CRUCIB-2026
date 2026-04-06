"""
Elite builder directive as execution context (not only a workspace file).

Loads `proof/ELITE_EXECUTION_DIRECTIVE.md` or falls back to `load_elite_autonomous_prompt()`,
attaches metadata to the in-memory job dict for handlers and verification, and builds
fragments for agent/LLM payloads.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, Optional

from .elite_prompt_loader import elite_prompt_fingerprint, load_elite_autonomous_prompt

logger = logging.getLogger(__name__)

_JOB_ELITE_KEY = "_elite_execution_context"


def _read_workspace_elite(workspace_path: str) -> Optional[str]:
    if not workspace_path or not os.path.isdir(workspace_path):
        return None
    p = os.path.join(workspace_path, "proof", "ELITE_EXECUTION_DIRECTIVE.md")
    if not os.path.isfile(p):
        return None
    try:
        with open(p, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def resolve_elite_execution_text(workspace_path: str) -> tuple[Optional[str], str]:
    """
    Returns (full_text_or_none, source_label).
    source: workspace_file | repo_file | disabled
    """
    if (os.environ.get("CRUCIBAI_ELITE_SYSTEM_PROMPT") or "").strip().lower() in (
        "0",
        "false",
        "no",
        "off",
    ):
        return None, "disabled"
    ws = _read_workspace_elite(workspace_path)
    if ws and ws.strip():
        return ws, "workspace_file"
    repo = load_elite_autonomous_prompt()
    if repo and repo.strip():
        return repo, "repo_file"
    return None, "missing"


def attach_elite_context_to_job(job: Dict[str, Any], workspace_path: str) -> None:
    """Mutate job dict once per process with elite metadata for execute_step / agents."""
    if _JOB_ELITE_KEY in job:
        return
    text, src = resolve_elite_execution_text(workspace_path)
    if not text:
        job[_JOB_ELITE_KEY] = {
            "active": False,
            "source": src,
            "sha16": None,
            "excerpt": "",
            "chars": 0,
        }
        return
    job[_JOB_ELITE_KEY] = {
        "active": True,
        "source": src,
        "sha16": elite_prompt_fingerprint(text),
        "excerpt": text[:4000],
        "chars": len(text),
    }


def elite_context_for_model(job: Dict[str, Any]) -> str:
    """System-appendable block for any LLM call on this job."""
    ctx = job.get(_JOB_ELITE_KEY) or {}
    if not ctx.get("active"):
        return ""
    ex = (ctx.get("excerpt") or "").strip()
    if not ex:
        return ""
    sha = ctx.get("sha16") or "?"
    return (
        "\n\n## Elite execution authority (bound to this job)\n"
        f"sha16={sha} source={ctx.get('source')}\n"
        "You must follow builder-mode rules: behavior over presence; classify Implemented/Mocked/Stubbed/Unverified;\n"
        "no silent production claims; use mock env keys for third parties when secrets absent.\n\n"
        f"{ex[:3500]}"
    )


def elite_job_metadata(job: Dict[str, Any]) -> Dict[str, Any]:
    ctx = job.get(_JOB_ELITE_KEY) or {}
    return {
        "elite_mode_active": bool(ctx.get("active")),
        "elite_prompt_sha16": ctx.get("sha16"),
        "elite_source": ctx.get("source"),
        "elite_chars": ctx.get("chars") or 0,
    }
