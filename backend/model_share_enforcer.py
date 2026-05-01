"""
Model-Share Enforcer — active runtime monitoring and enforcement of the
three-tier model quota policy.

Policy (mirrors llm_router.py constants):
  Cerebras  ≥ 60 % of platform tokens  → ALERT if below
  Haiku     ≤ 35 % of platform tokens  → WARNING if above
  Sonnet    ≤  1 % of platform tokens  → BLOCK if above (returns False)

The enforcer reads the running totals from credit_tracker (which writes to
the usage_log table) and updates in-process accumulators on every LLM call.

Usage
-----
Called by get_llm_config() (llm_client.py) before every provider dispatch:

    from backend.model_share_enforcer import share_enforcer

    # Returns False → caller must downgrade model (Sonnet → Haiku)
    if not share_enforcer.allow(provider="anthropic", model="claude-sonnet-*"):
        ...

Registers a usage event after a successful call:

    share_enforcer.record(provider="anthropic", model="claude-haiku-*", tokens=1234)
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ─── Thresholds (mirrored from llm_router.py env vars) ────────────────────────
_SONNET_MAX_SHARE  = float(os.environ.get("SONNET_MAX_PLATFORM_TOKEN_SHARE",  "0.01"))
_HAIKU_WARN_SHARE  = float(os.environ.get("HAIKU_MAX_TOKEN_SHARE_WARN",       "0.35"))
_CEREBRAS_MIN_SHARE= float(os.environ.get("CEREBRAS_MIN_TOKEN_SHARE_ALERT",   "0.60"))

# Observation window: shares are calculated over the last N tokens processed.
# This prevents early-session oscillation (e.g., first 10 tokens all Sonnet).
_MIN_TOKENS_FOR_ENFORCEMENT = int(os.environ.get("MODEL_SHARE_MIN_TOKENS", "10000"))


class ModelShareEnforcer:
    """
    Thread-safe, in-process token accumulator.

    Tracks tokens by bucket:
      "cerebras", "haiku", "sonnet", "other"

    Provides:
      allow(provider, model) → bool   : pre-call gate
      record(provider, model, tokens) : post-call accounting
      shares() → dict                 : current percentages
      reset()                         : clear counters (e.g., per-job)
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counts: Dict[str, int] = {
            "cerebras": 0,
            "haiku":    0,
            "sonnet":   0,
            "other":    0,
        }
        self._total: int = 0
        self._violations: int = 0
        self._last_alert_at: float = 0.0

    # ------------------------------------------------------------------ #
    #  Gate                                                                #
    # ------------------------------------------------------------------ #

    def allow(self, provider: str, model: str) -> bool:
        """Return False if this provider/model would exceed its quota cap.

        Only Sonnet has a hard BLOCK.  Haiku and Cerebras get WARNING / ALERT
        but are never blocked (blocking either would stop builds).
        """
        bucket = _bucket(provider, model)

        # Sonnet is the only hard-blocked tier.
        if bucket != "sonnet":
            return True

        with self._lock:
            if self._total < _MIN_TOKENS_FOR_ENFORCEMENT:
                # Not enough data yet — allow but log
                logger.debug(
                    "model_share_enforcer: allow sonnet — insufficient history "
                    "(%d / %d tokens)", self._total, _MIN_TOKENS_FOR_ENFORCEMENT
                )
                return True

            current_share = self._counts["sonnet"] / self._total
            if current_share >= _SONNET_MAX_SHARE:
                self._violations += 1
                now = time.time()
                if now - self._last_alert_at > 60:          # rate-limit the log
                    logger.warning(
                        "model_share_enforcer: BLOCKING Sonnet — share=%.2f%% "
                        "(limit=%.2f%%); downgrade to Haiku. violations=%d",
                        current_share * 100, _SONNET_MAX_SHARE * 100, self._violations,
                    )
                    self._last_alert_at = now
                return False

        return True

    # ------------------------------------------------------------------ #
    #  Accounting                                                          #
    # ------------------------------------------------------------------ #

    def record(self, provider: str, model: str, tokens: int) -> None:
        """Register *tokens* used by this provider/model."""
        if tokens <= 0:
            return
        bucket = _bucket(provider, model)
        with self._lock:
            self._counts[bucket] += tokens
            self._total += tokens
        self._emit_alerts(bucket)

    def _emit_alerts(self, bucket: str) -> None:
        """Fire WARNING / ALERT logs when thresholds are crossed."""
        with self._lock:
            if self._total < _MIN_TOKENS_FOR_ENFORCEMENT:
                return
            shares = {k: v / self._total for k, v in self._counts.items()}

        now = time.time()
        if now - self._last_alert_at < 30:     # don't spam
            return

        if bucket == "haiku" and shares["haiku"] > _HAIKU_WARN_SHARE:
            logger.warning(
                "model_share_enforcer: WARNING — Haiku share=%.1f%% "
                "(threshold=%.0f%%). Cerebras underutilised.",
                shares["haiku"] * 100, _HAIKU_WARN_SHARE * 100,
            )
            self._last_alert_at = now

        if bucket == "cerebras" and shares["cerebras"] < _CEREBRAS_MIN_SHARE:
            logger.error(
                "model_share_enforcer: ALERT — Cerebras share=%.1f%% "
                "(minimum=%.0f%%). Cost/reliability at risk.",
                shares["cerebras"] * 100, _CEREBRAS_MIN_SHARE * 100,
            )
            self._last_alert_at = now

    # ------------------------------------------------------------------ #
    #  Observability                                                       #
    # ------------------------------------------------------------------ #

    def shares(self) -> Dict[str, Any]:
        """Return current token counts and percentage shares."""
        with self._lock:
            total = self._total
            counts = dict(self._counts)

        if total == 0:
            return {
                "total_tokens": 0,
                "shares": {k: 0.0 for k in counts},
                "violations": self._violations,
                "enforcement_active": False,
            }

        return {
            "total_tokens":       total,
            "counts":             counts,
            "shares": {
                k: round(v / total * 100, 2)
                for k, v in counts.items()
            },
            "violations":         self._violations,
            "enforcement_active": total >= _MIN_TOKENS_FOR_ENFORCEMENT,
            "thresholds": {
                "cerebras_min_pct":  round(_CEREBRAS_MIN_SHARE  * 100, 1),
                "haiku_warn_pct":    round(_HAIKU_WARN_SHARE    * 100, 1),
                "sonnet_max_pct":    round(_SONNET_MAX_SHARE    * 100, 1),
            },
        }

    def reset(self) -> None:
        """Clear all counters (call at job start for per-job reporting)."""
        with self._lock:
            self._counts = {k: 0 for k in self._counts}
            self._total  = 0
        logger.info("model_share_enforcer: counters reset")


# ─── helpers ──────────────────────────────────────────────────────────────────

def _bucket(provider: str, model: str) -> str:
    """Map provider + model name to a tracking bucket."""
    p = (provider or "").lower()
    m = (model or "").lower()

    if p == "cerebras" or "llama" in m or "cerebras" in m:
        return "cerebras"
    if "sonnet" in m:
        return "sonnet"
    if "haiku" in m:
        return "haiku"
    if p == "anthropic":
        return "haiku"   # default Anthropic bucket if model unclear
    return "other"


# Module-level singleton — import this everywhere.
share_enforcer = ModelShareEnforcer()
