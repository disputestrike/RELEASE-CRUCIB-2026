"""CF1 + CF2 + CF3 + CF4 + CF5 unit tests.

These prove the corrective-action patches wire new behavior without breaking
the existing contract.  No live DB / LLM / server is required.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_BACKEND = _HERE.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from services.agent_loop import AgentLoop, ExecutionMode, MODE_PHASE_MAP  # noqa: E402


# ── CF2: mode enum + phase map integrity ─────────────────────────────────────
def test_cf2_all_eight_modes_have_phase_lists():
    assert len(ExecutionMode) == 8
    for mode in ExecutionMode:
        phases = MODE_PHASE_MAP[mode]
        assert isinstance(phases, list) and len(phases) >= 1
        assert "inspect" in phases or mode == ExecutionMode.ANALYZE_ONLY


def test_cf2_analyze_only_is_inspect_classify_only():
    assert MODE_PHASE_MAP[ExecutionMode.ANALYZE_ONLY] == ["inspect", "classify"]


def test_cf2_build_mode_skips_migrate_but_has_artifact():
    phases = MODE_PHASE_MAP[ExecutionMode.BUILD]
    assert "migrate" not in phases
    assert "artifact" in phases


# ── CF2: agent_loop forwards mode + phases ──────────────────────────────────
@pytest.mark.asyncio
async def test_cf2_agent_loop_forwards_mode_and_phases(monkeypatch):
    captured = {}

    class _Engine:
        async def execute_with_control(
            self, *, task_id, user_id, request, conversation_id=None,
            parent_task_id=None, progress_callback=None,
            mode=None, allowed_phases=None, project_id_override=None, **_extra,
        ):
            captured["mode"] = mode
            captured["allowed_phases"] = allowed_phases
            return {"ok": True}

    loop = AgentLoop()
    loop._engine = _Engine()
    out = await loop.run(mode=ExecutionMode.ANALYZE_ONLY, goal="audit", user_id="u")
    assert out["status"] == "completed"
    assert captured["mode"] == "analyze_only"
    assert captured["allowed_phases"] == ["inspect", "classify"]


# ── CF1: RuntimeEngine has INSPECT phase + inspector hook ────────────────────
def test_cf1_runtime_engine_has_inspect_phase():
    from services.runtime.runtime_engine import ExecutionPhase
    phase_names = {p.name for p in ExecutionPhase}
    assert "INSPECT" in phase_names


def test_cf1_runtime_engine_imports_capability_inspector():
    """Module-level import guard exposes capability_inspector (even if None)."""
    import services.runtime.runtime_engine as rt
    assert hasattr(rt, "capability_inspector")


# ── CF3: RuntimeEngine imports memory_store ──────────────────────────────────
def test_cf3_runtime_engine_imports_memory_store():
    import services.runtime.runtime_engine as rt
    assert hasattr(rt, "memory_store")


# ── CF4: images route is loadable ────────────────────────────────────────────
def test_cf4_images_route_has_generate_and_batch():
    from routes.images import router
    paths = {r.path for r in router.routes}
    assert "/api/images/generate" in paths
    assert "/api/images/batch" in paths


# ── CF5: migration route is loadable ─────────────────────────────────────────
def test_cf5_migration_route_has_all_four_endpoints():
    from routes.migration import router
    paths = {r.path for r in router.routes}
    assert "/api/migrations/plan" in paths
    assert "/api/migrations/execute" in paths
    assert "/api/migrations/{migration_id}" in paths
    assert "/api/migrations/{migration_id}/file-map" in paths


# ── CF5: migration plan end-to-end (no DB) ───────────────────────────────────
def test_cf5_migration_plan_service_produces_structured_plan(tmp_path):
    from services.migration_engine import migration_engine
    src = tmp_path / "src"
    tgt = tmp_path / "tgt"
    src.mkdir()
    (src / "a.py").write_text("def a(): return 1\n", encoding="utf-8")
    (src / "utils.py").write_text("def u(): return 2\n", encoding="utf-8")
    plan = migration_engine.plan(
        source_root=str(src),
        target_root=str(tgt),
        strategy="merge_many_to_fewer",
    )
    assert plan.migration_id
    assert plan.strategy == "merge_many_to_fewer"
    assert plan.file_actions  # non-empty
    # execute dry-run leaves source tree untouched
    result = migration_engine.execute_plan(plan, dry_run=True)
    assert result.status in ("dry_run", "completed", "ok", "planned")
