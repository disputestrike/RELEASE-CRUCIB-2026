"""
Opt-in content screening for user-supplied prompts (Fifty-point #42).

When CRUCIBAI_CONTENT_POLICY_STRICT is enabled, optional comma-separated
CRUCIBAI_CONTENT_BLOCK_SUBSTRINGS are matched case-insensitively against the full text.
Always enforces CRUCIBAI_MAX_USER_PROMPT_CHARS when set (default 200k).
"""
from __future__ import annotations

import os
from typing import Optional


def _truthy_env(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in ("1", "true", "yes", "on")


def screen_user_content(text: str) -> Optional[str]:
    """Return a short user-facing error if the content must be rejected; None if allowed."""
    if text is None:
        text = ""
    max_chars = int((os.environ.get("CRUCIBAI_MAX_USER_PROMPT_CHARS") or "200000").strip() or "200000")
    if len(text) > max_chars:
        return f"Input exceeds maximum length ({max_chars} characters)."
    if not _truthy_env("CRUCIBAI_CONTENT_POLICY_STRICT"):
        return None
    raw = (os.environ.get("CRUCIBAI_CONTENT_BLOCK_SUBSTRINGS") or "").strip()
    if not raw:
        return None
    low = text.lower()
    for part in (p.strip().lower() for p in raw.split(",") if p.strip()):
        if part in low:
            return "Request blocked by content policy."
    return None
