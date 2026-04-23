"""Wave 4 — Performance budget harness.

Measures p95 latency for key API endpoints using the _app_for() in-process
helper. No live Postgres or Redis is required.

Budgets:
    /api/onboard/metrics        p95 < 500 ms  (50 sequential calls)
    /api/benchmarks/scorecards  p95 < 300 ms  (50 sequential calls)
    /api/changelog              p95 < 400 ms  (50 sequential calls; skipped if route not mountable)
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import List

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

_HERE = Path(__file__).resolve().parent
_BACKEND = _HERE.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


def _app_for(module_name: str, attr: str = "router") -> FastAPI:
    """Build a minimal FastAPI app with a single router, auth deps overridden."""
    import importlib
    mod = importlib.import_module(module_name)
    router = getattr(mod, attr)
    app = FastAPI()
    app.include_router(router)

    try:
        from server import get_current_user  # type: ignore
        app.dependency_overrides[get_current_user] = lambda: {"id": "perf-test-user"}
    except Exception:
        pass
    try:
        from deps import get_current_user as deps_gcu  # type: ignore
        app.dependency_overrides[deps_gcu] = lambda: {"id": "perf-test-user"}
    except Exception:
        pass
    return app


def _percentile(samples: List[float], pct: float) -> float:
    """Compute the given percentile (0–100) of a sorted sample list."""
    if not samples:
        return 0.0
    sorted_s = sorted(samples)
    idx = (pct / 100.0) * (len(sorted_s) - 1)
    lo, hi = int(idx), min(int(idx) + 1, len(sorted_s) - 1)
    frac = idx - lo
    return sorted_s[lo] + frac * (sorted_s[hi] - sorted_s[lo])


def _measure_sequential(client: TestClient, path: str, n: int = 50) -> List[float]:
    """Make *n* sequential GET requests and return per-call durations in ms."""
    durations: List[float] = []
    for _ in range(n):
        t0 = time.perf_counter()
        client.get(path)
        durations.append((time.perf_counter() - t0) * 1000)
    return durations


# ── /api/onboard/metrics — p95 < 500 ms ──────────────────────────────────────

def test_onboard_metrics_p95_under_500ms():
    app = _app_for("routes.onboard")
    client = TestClient(app)

    # Warm-up
    client.get("/api/onboard/metrics")

    durations = _measure_sequential(client, "/api/onboard/metrics", n=50)
    p95 = _percentile(durations, 95)
    budget_ms = 500.0
    assert p95 < budget_ms, (
        f"/api/onboard/metrics p95={p95:.1f}ms exceeded budget={budget_ms}ms. "
        f"min={min(durations):.1f}ms max={max(durations):.1f}ms"
    )


# ── /api/benchmarks/scorecards — p95 < 300 ms ─────────────────────────────────

def test_benchmarks_scorecards_p95_under_300ms():
    app = _app_for("routes.benchmarks_api")
    client = TestClient(app)

    # Warm-up
    client.get("/api/benchmarks/scorecards")

    durations = _measure_sequential(client, "/api/benchmarks/scorecards", n=50)
    p95 = _percentile(durations, 95)
    budget_ms = 300.0
    assert p95 < budget_ms, (
        f"/api/benchmarks/scorecards p95={p95:.1f}ms exceeded budget={budget_ms}ms. "
        f"min={min(durations):.1f}ms max={max(durations):.1f}ms"
    )


# ── /api/changelog — p95 < 400 ms ─────────────────────────────────────────────

def test_changelog_p95_under_400ms():
    try:
        app = _app_for("routes.changelog")
    except Exception as exc:
        pytest.skip(f"changelog route not mountable: {exc}")

    client = TestClient(app)

    # Verify the route responds (degrade gracefully if git is absent)
    resp = client.get("/api/changelog")
    if resp.status_code not in (200, 404):
        pytest.skip("changelog route not mounted yet")

    # Warm-up
    client.get("/api/changelog")

    durations = _measure_sequential(client, "/api/changelog", n=50)
    p95 = _percentile(durations, 95)
    budget_ms = 400.0
    assert p95 < budget_ms, (
        f"/api/changelog p95={p95:.1f}ms exceeded budget={budget_ms}ms. "
        f"min={min(durations):.1f}ms max={max(durations):.1f}ms"
    )
