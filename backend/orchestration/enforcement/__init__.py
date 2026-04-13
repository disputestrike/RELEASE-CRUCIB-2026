"""Permanent enforcement layer: critical features, proof strength, hard completion gates."""

from __future__ import annotations

from .critical_registry import CRITICAL_FEATURES, CRITICAL_REGISTRY_VERSION
from .enforcement_engine import (
    evaluate_enforcement,
    run_completion_enforcement_gate,
    write_enforcement_artifacts,
)

__all__ = [
    "evaluate_enforcement",
    "run_completion_enforcement_gate",
    "write_enforcement_artifacts",
    "CRITICAL_REGISTRY_VERSION",
    "CRITICAL_FEATURES",
]
