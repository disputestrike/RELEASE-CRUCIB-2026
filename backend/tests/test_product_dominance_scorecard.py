from __future__ import annotations

from pathlib import Path

import pytest

from benchmarks.product_dominance_scorecard import (
    _repair_completion_flags,
    _final_score,
    build_run_plan,
    load_suite,
    parse_cases,
    run_benchmark,
)


def test_product_dominance_formula_matches_weights():
    dims = {
        "success": 100.0,
        "accuracy": 80.0,
        "speed": 60.0,
        "reliability": 90.0,
        "ux": 70.0,
    }
    score = _final_score(dims)
    assert score == 85.5


def test_product_dominance_plan_distribution():
    suite_path = Path(__file__).resolve().parents[2] / "benchmarks" / "product_dominance_suite_v1.json"
    suite = load_suite(suite_path)
    cases = parse_cases(suite)
    plan = build_run_plan(cases, {"full_app_build": 4, "repair": 2, "what_if": 1})
    assert len(plan) == 7
    assert sum(1 for item in plan if item.case.category == "full_app_build") == 4
    assert sum(1 for item in plan if item.case.category == "repair") == 2
    assert sum(1 for item in plan if item.case.category == "what_if") == 1


@pytest.mark.asyncio
async def test_product_dominance_run_benchmark_simulated(tmp_path: Path):
    suite_path = Path(__file__).resolve().parents[2] / "benchmarks" / "product_dominance_suite_v1.json"
    out_dir = tmp_path / "product_dominance"

    summary = await run_benchmark(
        suite_path=suite_path,
        output_dir=out_dir,
        user_id="pytest-user",
        execute_live=False,
        max_runs=5,
    )

    assert summary["mode"] == "simulated"
    assert summary["aggregate"]["total_runs"] == 5
    assert "summary_sha256" in summary
    assert (out_dir / "summary.json").exists()
    assert (out_dir / "BENCHMARK_REPORT.md").exists()


def test_repair_completion_flags_pass_for_repair_language():
    text = "Detected root cause, applied repair patch, and verified runtime status is working."
    flags = _repair_completion_flags(text)
    assert flags["has_diagnosis"] is True
    assert flags["has_fix"] is True
    assert flags["has_verify"] is True


def test_repair_completion_flags_fail_when_no_verification_signal():
    text = "Detected root cause and applied a fix, but no final confirmation provided."
    flags = _repair_completion_flags(text)
    assert flags["has_diagnosis"] is True
    assert flags["has_fix"] is True
    assert flags["has_verify"] is False
