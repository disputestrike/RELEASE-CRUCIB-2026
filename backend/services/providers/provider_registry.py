"""Provider selection with feature-flagged deterministic fallback policy."""

from __future__ import annotations

import os
from typing import Dict, List, Tuple

from services.providers.provider_contracts import PROVIDER_CONTRACTS


def _enabled() -> bool:
    return os.environ.get("CRUCIB_ENABLE_PROVIDER_REGISTRY", "0").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def choose_chain(
    current_chain: List[Tuple[str, str, str]],
    *,
    need_tools: bool = False,
    need_vision: bool = False,
) -> List[Tuple[str, str, str]]:
    """
    Return current_chain unchanged unless feature flag is enabled.

    If enabled, applies capability-aware ordering while preserving supplied models.
    """
    if not _enabled():
        return list(current_chain)

    scored: List[Tuple[int, Tuple[str, str, str]]] = []
    for entry in current_chain:
        alias, model, provider = entry
        contract = PROVIDER_CONTRACTS.get(provider)
        if not contract:
            scored.append((999, entry))
            continue
        if need_tools and not contract.supports_tools:
            score = 800
        elif need_vision and not contract.supports_vision:
            score = 700
        else:
            # Lower score is better. Prefer capability + lower cost where equal.
            base = 10
            if contract.cost_class == "low":
                base -= 2
            elif contract.cost_class == "high":
                base += 2
            score = base
        scored.append((score, entry))

    scored.sort(key=lambda x: x[0])
    return [item for _, item in scored]


def selection_meta() -> Dict[str, str]:
    return {
        "mode": "enabled" if _enabled() else "disabled",
        "strategy": "capability_fallback_v1",
    }
