"""
Load execution-layer builder prompt from repo (not UI).

Env:
  CRUCIBAI_ELITE_SYSTEM_PROMPT — unset or 1/true/yes: load file if present.
  0/false/no/off: do not load (returns None).

When enabled, ``write_elite_directive_to_workspace`` runs at Auto-Runner job start
(server background task) so every job workspace gets ``proof/ELITE_EXECUTION_DIRECTIVE.md``,
not only the crew planning step.
"""
from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_ELITE_FILENAME = "ELITE_AUTONOMOUS_PROMPT.md"


def _repo_root() -> Path:
    # backend/orchestration/this_file.py -> parents[2] == repo root (crucib)
    return Path(__file__).resolve().parents[2]


def elite_prompt_path() -> Path:
    return _repo_root() / "config" / "agent_prompts" / _ELITE_FILENAME


def _elite_prompt_enabled() -> bool:
    v = (os.environ.get("CRUCIBAI_ELITE_SYSTEM_PROMPT") or "").strip().lower()
    if v in ("0", "false", "no", "off"):
        return False
    return True


def load_elite_autonomous_prompt() -> Optional[str]:
    """
    Return full markdown text if enabled and file exists; otherwise None.
    """
    if not _elite_prompt_enabled():
        return None
    path = elite_prompt_path()
    if not path.is_file():
        logger.debug("elite prompt file missing: %s", path)
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("elite prompt read failed: %s", exc)
        return None


def write_elite_directive_to_workspace(workspace_path: str, prompt_text: Optional[str] = None) -> bool:
    """
    Write proof/ELITE_EXECUTION_DIRECTIVE.md under workspace_path so every Auto-Runner job
    carries the active builder prompt (not only the crew planning step).
    """
    root = (workspace_path or "").strip()
    if not root or not os.path.isdir(root):
        return False
    text = prompt_text if prompt_text is not None else load_elite_autonomous_prompt()
    if not (text or "").strip():
        return False
    try:
        fp = elite_prompt_fingerprint(text)
        excerpt = text[:4096] + ("\n\n… [truncated]\n" if len(text) > 4096 else "")
        body = (
            "# Elite builder execution directive\n\n"
            "Source: `config/agent_prompts/ELITE_AUTONOMOUS_PROMPT.md` in the CrucibAI repo.\n\n"
            f"SHA256 prefix: `{fp}`\n\n"
            "---\n\n"
            + excerpt
        )
        proof_dir = os.path.join(root, "proof")
        os.makedirs(proof_dir, exist_ok=True)
        out = os.path.join(proof_dir, "ELITE_EXECUTION_DIRECTIVE.md")
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(body)
        return True
    except OSError as exc:
        logger.warning("elite directive write failed: %s", exc)
        return False


def elite_prompt_fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
