"""Provider capability contracts used for deterministic fallback selection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class ProviderContract:
    provider: str
    supports_streaming: bool
    supports_tools: bool
    supports_vision: bool
    context_window: int
    cost_class: str  # low | medium | high


PROVIDER_CONTRACTS: Dict[str, ProviderContract] = {
    "anthropic": ProviderContract("anthropic", True, True, True, 200000, "high"),
    "cerebras": ProviderContract("cerebras", True, False, False, 128000, "low"),
    "together": ProviderContract("together", True, False, False, 128000, "medium"),
}
