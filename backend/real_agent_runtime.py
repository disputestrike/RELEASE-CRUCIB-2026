"""Runtime key checks for the real builder path."""

from __future__ import annotations

import os

REAL_AGENT_NO_LLM_KEYS_DETAIL = {
    "error": "real_agent_missing_llm_key",
    "message": (
        "Real builder mode requires an Anthropic, Cerebras, or Together API key. "
        "Add a key in workspace settings or Railway variables."
    ),
}


def is_real_agent_only() -> bool:
    return os.getenv("CRUCIBAI_REAL_AGENT_ONLY", "1").lower() not in {"0", "false", "no"}


def chat_llm_available(effective_keys=None) -> bool:
    keys = effective_keys or {}
    return bool(
        keys.get("anthropic")
        or keys.get("cerebras")
        or keys.get("together")
        or os.getenv("ANTHROPIC_API_KEY")
        or os.getenv("CEREBRAS_API_KEY")
        or os.getenv("TOGETHER_API_KEY")
    )
