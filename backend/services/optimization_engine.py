"""
Optimization Engine — Phase 3: Closed-Loop Optimization.

Background asyncio task that:
  1. Periodically sweeps all tracked apps via MetricStore.
  2. Calls analyze_and_signal() for each app that has >= MIN_SAMPLES data.
  3. Persists actionable signals (warning/critical) to the job event log so
     the build pipeline can pick them up as improvement prompts.
  4. Optionally re-queues a repair build via the orchestration executor when
     a critical signal is detected and AUTO_REPAIR is enabled.

Lifecycle:
  start_optimization_engine()  — call once at FastAPI startup
  stop_optimization_engine()   — call at FastAPI shutdown
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# How often to run the sweep (seconds)
SWEEP_INTERVAL = int(os.environ.get("OPT_SWEEP_INTERVAL", "300"))   # 5 minutes

# Only act on signals at or above this severity
MIN_SEVERITY = os.environ.get("OPT_MIN_SEVERITY", "warning")        # "warning" | "critical"

# When True, critical signals automatically queue a repair build
AUTO_REPAIR = os.environ.get("OPT_AUTO_REPAIR", "false").lower() == "true"

_SEVERITY_RANK = {"info": 0, "warning": 1, "critical": 2}

_engine_task: Optional[asyncio.Task] = None
_running = False

# In-memory log of signals already acted on (prevent duplicate triggers)
_acted_signals: Dict[str, float] = {}   # key = f"{app_id}:{signal_type}", value = last_acted_ts
SIGNAL_COOLDOWN = int(os.environ.get("OPT_SIGNAL_COOLDOWN", "3600"))  # 1 hour between same signal


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _above_min_severity(severity: str) -> bool:
    return _SEVERITY_RANK.get(severity, 0) >= _SEVERITY_RANK.get(MIN_SEVERITY, 1)


def _on_cooldown(app_id: str, signal_type: str) -> bool:
    key = f"{app_id}:{signal_type}"
    last = _acted_signals.get(key, 0.0)
    return (time.time() - last) < SIGNAL_COOLDOWN


def _mark_acted(app_id: str, signal_type: str) -> None:
    _acted_signals[f"{app_id}:{signal_type}"] = time.time()


async def _persist_signal_to_job_events(app_id: str, signal_dict: dict) -> None:
    """
    Write the signal as a job event so the build pipeline can surface it.
    Gracefully skips if the event service is unavailable.
    """
    try:
        from .job_event_service import emit_event
        await emit_event(
            job_id=app_id,
            event_type="optimization_signal",
            payload={
                "severity": signal_dict.get("severity"),
                "signal_type": signal_dict.get("signal_type"),
                "message": signal_dict.get("message"),
                "improvement_prompt": signal_dict.get("improvement_prompt"),
                "metrics_summary": signal_dict.get("metrics_summary", {}),
            },
        )
        logger.info(
            "[OPT_ENGINE] Signal persisted — app=%s type=%s severity=%s",
            app_id, signal_dict.get("signal_type"), signal_dict.get("severity"),
        )
    except Exception as exc:
        logger.debug("[OPT_ENGINE] Could not persist signal to job events: %s", exc)


async def _trigger_auto_repair(app_id: str, improvement_prompt: str) -> None:
    """
    Queue a repair build for the app using the improvement prompt as the goal.
    Only fires when AUTO_REPAIR=true and signal is critical.
    """
    if not AUTO_REPAIR:
        return
    try:
        from ..orchestration import runtime_state

        logger.info("[OPT_ENGINE] AUTO_REPAIR: recording repair request for app=%s", app_id)
        await runtime_state.append_job_event(
            app_id,
            "user_steering",
            {
                "message": improvement_prompt,
                "source": "optimization_engine",
                "resume_required": True,
            },
        )
    except Exception as exc:
        logger.warning("[OPT_ENGINE] AUTO_REPAIR failed to queue for app=%s: %s", app_id, exc)


async def _sweep_once() -> None:
    """Run a single analysis pass over all tracked apps."""
    from .performance_monitor import _store, analyze_and_signal

    app_ids: List[str] = await _store.get_all_app_ids()
    if not app_ids:
        logger.debug("[OPT_ENGINE] Sweep: no apps tracked yet.")
        return

    logger.info("[OPT_ENGINE] Sweep started — %d apps to analyze", len(app_ids))
    acted = 0

    for app_id in app_ids:
        try:
            signals = await analyze_and_signal(app_id)
            for signal in signals:
                if not _above_min_severity(signal.severity):
                    continue
                if _on_cooldown(app_id, signal.signal_type):
                    continue

                _mark_acted(app_id, signal.signal_type)
                acted += 1
                signal_dict = signal.to_dict()

                # Persist to job events (non-blocking)
                await _persist_signal_to_job_events(app_id, signal_dict)

                # Auto-repair on critical signals
                if signal.severity == "critical":
                    await _trigger_auto_repair(app_id, signal.improvement_prompt)

        except Exception as exc:
            logger.error("[OPT_ENGINE] Error analyzing app=%s: %s", app_id, exc)

    logger.info("[OPT_ENGINE] Sweep complete — %d signals acted on across %d apps", acted, len(app_ids))


# ---------------------------------------------------------------------------
# Engine lifecycle
# ---------------------------------------------------------------------------

async def _engine_loop() -> None:
    global _running
    logger.info(
        "[OPT_ENGINE] Started. sweep_interval=%ds min_severity=%s auto_repair=%s",
        SWEEP_INTERVAL, MIN_SEVERITY, AUTO_REPAIR,
    )
    while _running:
        try:
            await _sweep_once()
        except Exception as exc:
            logger.error("[OPT_ENGINE] Unhandled error in sweep: %s", exc, exc_info=True)
        # Sleep in short chunks so we can respond to stop() quickly
        for _ in range(SWEEP_INTERVAL):
            if not _running:
                break
            await asyncio.sleep(1)

    logger.info("[OPT_ENGINE] Stopped.")


def start_optimization_engine() -> None:
    """Start the background optimization sweep. Call once at FastAPI startup."""
    global _engine_task, _running
    if _engine_task and not _engine_task.done():
        logger.warning("[OPT_ENGINE] Already running — ignoring start() call.")
        return
    _running = True
    _engine_task = asyncio.create_task(_engine_loop())
    logger.info("[OPT_ENGINE] Background task created.")


def stop_optimization_engine() -> None:
    """Stop the background optimization sweep. Call at FastAPI shutdown."""
    global _running
    _running = False
    if _engine_task and not _engine_task.done():
        _engine_task.cancel()
    logger.info("[OPT_ENGINE] Stop signal sent.")


# ---------------------------------------------------------------------------
# Manual trigger (for admin / testing)
# ---------------------------------------------------------------------------

async def run_sweep_now() -> dict:
    """Trigger an immediate sweep and return a summary dict."""
    t0 = time.time()
    await _sweep_once()
    return {
        "ok": True,
        "duration_ms": round((time.time() - t0) * 1000),
        "acted_signals": dict(_acted_signals),
    }
