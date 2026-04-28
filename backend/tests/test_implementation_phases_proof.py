"""
Deterministic proofs for IMPLEMENTATION_TRACKER phases 2–7.
Run with: pytest tests/test_implementation_phases_proof.py tests/test_vector_memory_fallback.py -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

from backend.agent_dag import AGENT_DAG


def test_phase2_controller_live_progress_shape_and_controller_block():
    from backend.orchestration.controller_brain import build_live_job_progress

    job = {"id": "jb_proof", "status": "running"}
    steps = [
        {
            "id": "step1",
            "order_index": 0,
            "phase": "prep",
            "step_key": "plan_step",
            "agent_name": "Planner",
            "status": "running",
            "error_message": None,
            "created_at": "2020-01-01",
        },
    ]
    prog = build_live_job_progress(job=job, steps=steps, events=[])
    assert prog["job_id"] == "jb_proof"
    assert "controller" in prog and isinstance(prog["controller"], dict)
    assert prog["controller"].get("status") in ("executing", "attention_required", "completed")


@pytest.mark.parametrize(
    "goal",
    [
        "Enterprise CRM with HIPAA compliance and audit trail",
        "Real-time WebGL multiplayer game client",
        "FastAPI PostgreSQL Stripe billing SaaS",
    ],
)
def test_phase3_select_agents_resolves_existing_dag_vertices(goal):
    from backend.orchestration.agent_selection_logic import select_agents_for_goal

    sel = select_agents_for_goal(goal)
    assert isinstance(sel, list) and len(sel) >= 4
    bad = [a for a in sel if a not in AGENT_DAG]
    assert not bad, f"DAG missing agents {bad}"


@pytest.mark.asyncio
async def test_phase4_preview_gate_returns_structured_result(tmp_path):
    from backend.orchestration.preview_gate import verify_preview_workspace

    ws = tmp_path / "ws"
    ws.mkdir(parents=True, exist_ok=True)
    # Minimal deterministic failure path (still exercises async gate surface)
    res = await verify_preview_workspace(str(ws))
    assert isinstance(res, dict)
    assert "passed" in res or "failure_reason" in res or "score" in res


def test_phase5_vector_memory_module_import_contract():
    from backend.memory.vector_db import VectorMemory, get_vector_memory

    assert callable(get_vector_memory)
    vm = VectorMemory()
    assert getattr(vm, "provider", None) == "memory" or getattr(vm, "provider", "") in ("memory", "pinecone")


def test_phase6_server_registers_simulations_and_jobs_routers():
    from backend import server as srv

    mods = [
        row.get("module")
        for row in (srv.ROUTE_REGISTRATION_REPORT or [])
        if row.get("status") == "loaded"
    ]
    assert "backend.routes.simulations" in mods
    assert "backend.routes.jobs" in mods


def test_phase7_frontend_simulation_page_exists():
    repo = Path(__file__).resolve().parents[2]
    what_if = repo / "frontend" / "src" / "pages" / "WhatIfPage.jsx"
    assert what_if.is_file(), f"Missing {what_if}"
