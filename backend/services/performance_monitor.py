"""
Performance Monitor — Phase 3: Closed-Loop Optimization.

Collects, stores, and analyzes performance metrics from deployed apps.
Metrics arrive via the /api/apps/{app_id}/metrics POST endpoint.
A background analyzer compares against baselines and emits improvement signals.

Metric schema (per ping from deployed app):
    {
        "app_id":        str,           # job_id or site_id
        "ts":            float,         # unix epoch
        "load_ms":       int,           # page load time
        "error_rate":    float,         # fraction 0.0–1.0
        "active_users":  int,
        "requests":      int,           # requests in this period
        "endpoint_p95":  float | None,  # API p95 latency (ms)
        "custom":        dict,          # any extra key/values
    }
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Keep last N metric snapshots per app in memory
METRIC_WINDOW = int(os.environ.get("METRIC_WINDOW", "200"))

# Thresholds that trigger an optimization signal
LOAD_MS_WARN = int(os.environ.get("LOAD_MS_WARN", "3000"))       # warn if p50 load > 3s
LOAD_MS_CRIT = int(os.environ.get("LOAD_MS_CRIT", "6000"))       # crit if p50 load > 6s
ERROR_RATE_WARN = float(os.environ.get("ERROR_RATE_WARN", "0.05"))  # warn if > 5% errors
ERROR_RATE_CRIT = float(os.environ.get("ERROR_RATE_CRIT", "0.15"))  # crit if > 15% errors
MIN_SAMPLES_FOR_ANALYSIS = int(os.environ.get("MIN_SAMPLES", "5"))


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class MetricSnapshot:
    app_id: str
    ts: float
    load_ms: int = 0
    error_rate: float = 0.0
    active_users: int = 0
    requests: int = 0
    endpoint_p95: Optional[float] = None
    custom: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OptimizationSignal:
    app_id: str
    severity: str           # "info" | "warning" | "critical"
    signal_type: str        # "slow_load" | "high_errors" | "low_usage" | "api_latency"
    message: str
    improvement_prompt: str # ready-to-feed prompt for the build pipeline
    created_at: float = field(default_factory=time.time)
    metrics_summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# In-memory metric store (swap for Redis/Postgres in production)
# ---------------------------------------------------------------------------

class MetricStore:
    """Thread-safe in-memory store for metric snapshots."""

    def __init__(self, window: int = METRIC_WINDOW):
        self._data: Dict[str, Deque[MetricSnapshot]] = defaultdict(
            lambda: deque(maxlen=window)
        )
        self._lock = asyncio.Lock()

    async def record(self, snap: MetricSnapshot) -> None:
        async with self._lock:
            self._data[snap.app_id].append(snap)

    async def get_snapshots(self, app_id: str) -> List[MetricSnapshot]:
        async with self._lock:
            return list(self._data.get(app_id, []))

    async def get_all_app_ids(self) -> List[str]:
        async with self._lock:
            return list(self._data.keys())

    async def summary(self, app_id: str) -> Dict[str, Any]:
        snaps = await self.get_snapshots(app_id)
        if not snaps:
            return {}
        load_vals = [s.load_ms for s in snaps if s.load_ms > 0]
        err_vals = [s.error_rate for s in snaps]
        user_vals = [s.active_users for s in snaps]
        p95_vals = [s.endpoint_p95 for s in snaps if s.endpoint_p95 is not None]
        def avg(lst): return sum(lst) / len(lst) if lst else 0.0
        def pct(lst, p):
            if not lst: return 0.0
            lst2 = sorted(lst)
            idx = max(0, int(len(lst2) * p / 100) - 1)
            return lst2[idx]
        return {
            "sample_count": len(snaps),
            "load_ms_avg": round(avg(load_vals)),
            "load_ms_p95": round(pct(load_vals, 95)),
            "error_rate_avg": round(avg(err_vals), 4),
            "error_rate_max": round(max(err_vals), 4) if err_vals else 0.0,
            "active_users_avg": round(avg(user_vals)),
            "endpoint_p95_avg": round(avg(p95_vals)) if p95_vals else None,
            "oldest_ts": snaps[0].ts,
            "latest_ts": snaps[-1].ts,
        }


# Singleton store
_store = MetricStore()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def record_metric(payload: Dict[str, Any]) -> None:
    """Validate and store an incoming metric payload."""
    try:
        snap = MetricSnapshot(
            app_id=str(payload.get("app_id") or ""),
            ts=float(payload.get("ts") or time.time()),
            load_ms=int(payload.get("load_ms") or 0),
            error_rate=float(payload.get("error_rate") or 0.0),
            active_users=int(payload.get("active_users") or 0),
            requests=int(payload.get("requests") or 0),
            endpoint_p95=float(payload["endpoint_p95"]) if payload.get("endpoint_p95") is not None else None,
            custom=dict(payload.get("custom") or {}),
        )
        if not snap.app_id:
            logger.warning("[MONITOR] Metric received with empty app_id — dropped")
            return
        await _store.record(snap)
        logger.debug("[MONITOR] Recorded metric app=%s load_ms=%d err=%.3f",
                     snap.app_id, snap.load_ms, snap.error_rate)
    except Exception as exc:
        logger.error("[MONITOR] Failed to record metric: %s payload=%s", exc, payload)


async def get_app_summary(app_id: str) -> Dict[str, Any]:
    """Return aggregated metrics summary for one app."""
    return await _store.summary(app_id)


async def analyze_and_signal(app_id: str) -> List[OptimizationSignal]:
    """
    Analyze metrics for an app and return optimization signals.
    Returns an empty list if not enough data yet.
    """
    summary = await _store.summary(app_id)
    if not summary or summary.get("sample_count", 0) < MIN_SAMPLES_FOR_ANALYSIS:
        return []

    signals: List[OptimizationSignal] = []

    # ── Check 1: Page load time ────────────────────────────────────────────
    avg_load = summary.get("load_ms_avg", 0)
    p95_load = summary.get("load_ms_p95", 0)
    if avg_load > LOAD_MS_CRIT:
        signals.append(OptimizationSignal(
            app_id=app_id,
            severity="critical",
            signal_type="slow_load",
            message=f"Average page load {avg_load}ms exceeds critical threshold ({LOAD_MS_CRIT}ms). Users will abandon.",
            improvement_prompt=(
                f"The deployed app (id={app_id}) has critically slow page loads: "
                f"avg={avg_load}ms, p95={p95_load}ms. "
                "Please optimize: (1) add code splitting / lazy loading to large JS bundles, "
                "(2) move heavy API calls to useEffect with loading states, "
                "(3) add a CDN cache header to static assets, "
                "(4) ensure images use WebP format and are lazy-loaded. "
                "Output optimized frontend files only — do not change backend logic."
            ),
            metrics_summary=summary,
        ))
    elif avg_load > LOAD_MS_WARN:
        signals.append(OptimizationSignal(
            app_id=app_id,
            severity="warning",
            signal_type="slow_load",
            message=f"Average page load {avg_load}ms is above recommended threshold ({LOAD_MS_WARN}ms).",
            improvement_prompt=(
                f"The deployed app (id={app_id}) has slow page loads: avg={avg_load}ms. "
                "Suggest: add React.memo() to expensive components, reduce initial bundle size, "
                "and implement image lazy loading."
            ),
            metrics_summary=summary,
        ))

    # ── Check 2: Error rate ────────────────────────────────────────────────
    err_rate = summary.get("error_rate_avg", 0.0)
    err_max = summary.get("error_rate_max", 0.0)
    if err_rate > ERROR_RATE_CRIT:
        signals.append(OptimizationSignal(
            app_id=app_id,
            severity="critical",
            signal_type="high_errors",
            message=f"Error rate {err_rate:.1%} (max {err_max:.1%}) is critically high.",
            improvement_prompt=(
                f"The deployed app (id={app_id}) has a {err_rate:.1%} error rate. "
                "Please: (1) add try/catch error boundaries around all API calls, "
                "(2) implement exponential backoff for failed requests, "
                "(3) add a global error handler that reports errors to /api/errors, "
                "(4) ensure all form submissions validate inputs before sending. "
                "Focus on error handling improvements only."
            ),
            metrics_summary=summary,
        ))
    elif err_rate > ERROR_RATE_WARN:
        signals.append(OptimizationSignal(
            app_id=app_id,
            severity="warning",
            signal_type="high_errors",
            message=f"Error rate {err_rate:.1%} is above recommended threshold.",
            improvement_prompt=(
                f"The deployed app (id={app_id}) shows a {err_rate:.1%} error rate. "
                "Add defensive error handling and retry logic to API calls."
            ),
            metrics_summary=summary,
        ))

    # ── Check 3: API latency ───────────────────────────────────────────────
    api_p95 = summary.get("endpoint_p95_avg")
    if api_p95 and api_p95 > 2000:
        signals.append(OptimizationSignal(
            app_id=app_id,
            severity="warning",
            signal_type="api_latency",
            message=f"API p95 latency is {api_p95:.0f}ms — consider caching and query optimization.",
            improvement_prompt=(
                f"The deployed app (id={app_id}) has high API p95 latency: {api_p95:.0f}ms. "
                "Please: (1) add Redis caching to frequently-queried endpoints, "
                "(2) add database indexes to slow queries, "
                "(3) implement pagination for list endpoints. "
                "Output backend changes only."
            ),
            metrics_summary=summary,
        ))

    return signals
