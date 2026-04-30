"""
stack_confidence.py — Enforced confidence scoring for technology stacks.

Every stack has a confidence score (0.0 – 1.0) based on:
  - Template quality and completeness
  - Validator coverage (syntax, build, runtime, integration)
  - Historical build success rate
  - Repair agent maturity

Enforcement tiers:
  - production (>= 0.80): Fully supported, no warnings
  - stable (>= 0.60): Supported, minor warnings
  - beta (>= 0.40): Supported with explicit warning logged
  - experimental (< 0.40): BLOCKED unless CRUCIBAI_ALLOW_EXPERIMENTAL=1

CRITICAL: This is NOT decorative. BuilderAgent MUST call check_stack_confidence()
before spending any LLM tokens.
"""

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Confidence Registry ───────────────────────────────────────────────────────

CONFIDENCE_REGISTRY: Dict[str, float] = {
    # Production tier (>= 0.80)
    "python_fastapi": 0.95,
    "react_vite": 0.90,
    "python_cli": 0.85,
    "node_express": 0.80,

    # Stable tier (>= 0.60)
    "cpp_cmake": 0.60,

    # Beta tier (>= 0.40)
    "go_gin": 0.50,
    "rust_axum": 0.45,
    "typescript_express": 0.70,
    "vue_nuxt": 0.65,
    "nextjs": 0.75,

    # Experimental (< 0.40) — blocked by default
    "ruby_rails": 0.30,
    "java_spring": 0.25,
    "elixir_phoenix": 0.20,
    "swift_vapor": 0.15,
}

# Tiers
TIER_PRODUCTION = "production"    # >= 0.80
TIER_STABLE = "stable"           # >= 0.60
TIER_BETA = "beta"               # >= 0.40
TIER_EXPERIMENTAL = "experimental"  # < 0.40

TIER_THRESHOLDS = {
    TIER_PRODUCTION: 0.80,
    TIER_STABLE: 0.60,
    TIER_BETA: 0.40,
}


def get_tier(score: float) -> str:
    """Classify a confidence score into its enforcement tier."""
    if score >= TIER_THRESHOLDS[TIER_PRODUCTION]:
        return TIER_PRODUCTION
    if score >= TIER_THRESHOLDS[TIER_STABLE]:
        return TIER_STABLE
    if score >= TIER_THRESHOLDS[TIER_BETA]:
        return TIER_BETA
    return TIER_EXPERIMENTAL


def get_stack_key(stack: Dict[str, Any]) -> str:
    """
    Derive a stack key from a stack dict (as returned by select_stack()).

    Examples:
        {"backend": {"language": "python", "framework": "fastapi"}, ...}
        → "python_fastapi"

        {"backend": {"language": "javascript", "framework": "express"}, ...}
        → "node_express"
    """
    backend = stack.get("backend") or {}
    lang = (backend.get("language") or "").lower()
    fw = (backend.get("framework") or "").lower()

    if not backend:
        # Frontend-only stack
        frontend = stack.get("frontend") or {}
        lang = (frontend.get("language") or "").lower()
        fw = (frontend.get("framework") or "").lower()

    # Normalize to stack_key
    mapping = {
        ("python", "fastapi"): "python_fastapi",
        ("python", "fastapi-websocket"): "python_fastapi",
        ("python", "cli"): "python_cli",
        ("python", "django"): "python_fastapi",
        ("python", "flask"): "python_fastapi",
        ("javascript", "express"): "node_express",
        ("typescript", "express"): "typescript_express",
        ("cpp", "cmake"): "cpp_cmake",
        ("go", "gin"): "go_gin",
        ("go", "actix"): "go_gin",
        ("rust", "axum"): "rust_axum",
        ("rust", "actix"): "rust_axum",
        ("rust", "rocket"): "rust_axum",
        ("typescript", "react-vite"): "react_vite",
        ("javascript", "react-vite"): "react_vite",
        ("typescript", "next.js"): "nextjs",
        ("vue", "nuxt"): "vue_nuxt",
        ("javascript", "vue"): "vue_nuxt",
    }

    return mapping.get((lang, fw), f"{lang}_{fw}" if lang else "unknown")


# ── Historical Tracking ──────────────────────────────────────────────────────

# In-memory EMA (exponential moving average) of actual build outcomes
_outcome_history: Dict[str, List[bool]] = {}  # stack_key → [True, False, True, ...]


def record_outcome(stack_key: str, success: bool) -> None:
    """Record a build outcome for EMA tracking."""
    if stack_key not in _outcome_history:
        _outcome_history[stack_key] = []
    _outcome_history[stack_key].append(success)
    # Keep last 50 outcomes
    if len(_outcome_history[stack_key]) > 50:
        _outcome_history[stack_key] = _outcome_history[stack_key][-50:]


def get_ema_score(stack_key: str) -> Optional[float]:
    """
    Get the exponential moving average success rate for a stack.
    Returns None if no history exists.
    """
    history = _outcome_history.get(stack_key, [])
    if not history:
        return None

    alpha = 0.3  # EMA smoothing factor
    ema = float(history[0])
    for outcome in history[1:]:
        ema = alpha * float(outcome) + (1 - alpha) * ema
    return ema


def get_effective_confidence(stack_key: str) -> float:
    """
    Get effective confidence by blending base confidence with EMA.
    If EMA exists, weight it 30% against 70% base.
    """
    base = CONFIDENCE_REGISTRY.get(stack_key, 0.4)
    ema = get_ema_score(stack_key)
    if ema is not None:
        effective = 0.7 * base + 0.3 * ema
        logger.debug(
            "stack_confidence: %s base=%.2f ema=%.2f effective=%.2f",
            stack_key, base, ema, effective,
        )
        return effective
    return base


# ── Gate Enforcement ─────────────────────────────────────────────────────────

class StackNotSupportedError(Exception):
    """Raised when a stack's confidence is below the allowed threshold."""
    pass


def check_stack_confidence(
    stack: Dict[str, Any],
    allow_experimental: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Check stack confidence and enforce gating rules.

    Args:
        stack: Stack dict from select_stack()
        allow_experimental: Override experimental blocking. If None, reads
            CRUCIBAI_ALLOW_EXPERIMENTAL env var (default: False).

    Returns:
        {
            "stack_key": str,
            "confidence": float,
            "tier": str,
            "warnings": [str],
            "blocked": bool,
            "reason": str | None,
        }

    Raises:
        StackNotSupportedError: If stack is below threshold and not explicitly allowed.
    """
    stack_key = get_stack_key(stack)
    confidence = get_effective_confidence(stack_key)
    tier = get_tier(confidence)

    warnings: List[str] = []
    blocked = False
    reason = None

    if allow_experimental is None:
        allow_experimental = os.environ.get("CRUCIBAI_ALLOW_EXPERIMENTAL", "0").lower() in ("1", "true", "yes")

    if tier == TIER_EXPERIMENTAL:
        if not allow_experimental:
            blocked = True
            reason = (
                f"Stack '{stack_key}' has confidence {confidence:.2f} (experimental tier). "
                f"This stack is not production-ready. "
                f"Set CRUCIBAI_ALLOW_EXPERIMENTAL=1 to override."
            )
            logger.error("[CONFIDENCE BLOCK] %s", reason)
            raise StackNotSupportedError(reason)
        else:
            warnings.append(
                f"Stack '{stack_key}' is experimental (confidence={confidence:.2f}). "
                f"Build quality is not guaranteed."
            )

    if tier == TIER_BETA:
        warnings.append(
            f"Stack '{stack_key}' is in beta (confidence={confidence:.2f}). "
            f"Some features may not work correctly."
        )
        logger.warning("[CONFIDENCE BETA] %s", warnings[-1])

    if tier == TIER_STABLE:
        logger.info(
            "[CONFIDENCE STABLE] stack=%s confidence=%.2f",
            stack_key, confidence,
        )

    if tier == TIER_PRODUCTION:
        logger.info(
            "[CONFIDENCE PRODUCTION] stack=%s confidence=%.2f",
            stack_key, confidence,
        )

    result = {
        "stack_key": stack_key,
        "confidence": confidence,
        "tier": tier,
        "warnings": warnings,
        "blocked": blocked,
        "reason": reason,
    }

    logger.info(
        "stack_confidence: key=%s score=%.2f tier=%s warnings=%d blocked=%s",
        stack_key, confidence, tier, len(warnings), blocked,
    )

    return result
