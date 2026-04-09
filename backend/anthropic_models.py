"""Central Anthropic model defaults and retired-model normalization.

Anthropic retired Claude Haiku 3.5 (`claude-3-5-haiku-20241022`) and
Claude Sonnet 3.5 / 3.7 snapshots in 2025-2026. Production code should
normalize stale model IDs so old env vars and hard-coded defaults do not
keep returning API errors after retirement.
"""
from __future__ import annotations

from typing import Optional


ANTHROPIC_HAIKU_MODEL = "claude-haiku-4-5-20251001"
ANTHROPIC_HAIKU_ALIAS = "claude-haiku-4-5"
ANTHROPIC_SONNET_MODEL = "claude-sonnet-4-6"

RETIRED_MODEL_REPLACEMENTS = {
    "claude-3-haiku-20240307": ANTHROPIC_HAIKU_MODEL,
    "claude-3-5-haiku-20241022": ANTHROPIC_HAIKU_MODEL,
    "claude-3-5-haiku": ANTHROPIC_HAIKU_MODEL,
    "claude-haiku": ANTHROPIC_HAIKU_MODEL,
    "claude-3-5-sonnet-20240620": ANTHROPIC_SONNET_MODEL,
    "claude-3-5-sonnet-20241022": ANTHROPIC_SONNET_MODEL,
    "claude-3-5-sonnet": ANTHROPIC_SONNET_MODEL,
    "claude-3-7-sonnet-20250219": ANTHROPIC_SONNET_MODEL,
    "claude-sonnet": ANTHROPIC_SONNET_MODEL,
}


def normalize_anthropic_model(
    model: Optional[str],
    *,
    default: str = ANTHROPIC_HAIKU_MODEL,
) -> str:
    """Return a supported Anthropic model ID.

    - Empty / missing values resolve to the provided default.
    - Retired or shorthand Claude IDs are mapped to current supported models.
    - Unknown `claude-*` values are returned as-is to preserve explicit user
      intent for newer supported snapshots.
    """
    normalized = str(model or "").strip()
    if not normalized:
        return default
    return RETIRED_MODEL_REPLACEMENTS.get(normalized, normalized)

