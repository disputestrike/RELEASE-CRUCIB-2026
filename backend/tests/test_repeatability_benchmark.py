import json
from pathlib import Path

import pytest

from benchmarks.repeatability_scorecard import (
    BENCHMARK_VERSION,
    load_prompt_suite,
    parse_cases,
    run_benchmark,
)


ROOT = Path(__file__).resolve().parents[2]
SUITE = ROOT / "benchmarks" / "repeatability_prompts_v1.json"


def test_repeatability_prompt_suite_has_first_fifty_categories():
    suite = load_prompt_suite(SUITE)
    cases = parse_cases(suite)

    assert suite["version"] == BENCHMARK_VERSION
    assert len(cases) == 50
    assert len({case.id for case in cases}) == 50
    assert {"saas", "marketplace", "automation", "byoc", "marketing", "healthcare", "finance", "legal", "civic"}.issubset(
        {case.category for case in cases}
    )
    assert all(case.goal and case.required_terms for case in cases)


@pytest.mark.asyncio
async def test_repeatability_benchmark_writes_passing_scorecard(tmp_path, monkeypatch):
    monkeypatch.setenv("CRUCIBAI_SKIP_BROWSER_PREVIEW", "1")
    summary = await run_benchmark(
        suite_path=SUITE,
        output_dir=tmp_path / "repeatability",
        run_browser_preview=False,
        min_pass_rate=0.90,
        min_average_score=90.0,
    )

    assert summary["benchmark_version"] == BENCHMARK_VERSION
    assert summary["prompt_count"] == 50
    assert summary["passed_count"] == 50
    assert summary["pass_rate"] == 1.0
    assert summary["average_score"] >= 90.0
    assert summary["passed"] is True
    assert not summary["blockers"]
    assert (tmp_path / "repeatability" / "summary.json").is_file()
    assert (tmp_path / "repeatability" / "PASS_FAIL.md").is_file()
    assert (tmp_path / "repeatability" / "cases" / "saas_dashboard.json").is_file()
    assert (tmp_path / "repeatability" / "workspaces" / "saas_dashboard" / "package.json").is_file()

    case_data = json.loads((tmp_path / "repeatability" / "cases" / "workflow_automation.json").read_text())
    assert case_data["stages"]["preview"]["passed"] is True
    assert case_data["stages"]["elite_proof"]["passed"] is True
    assert case_data["stages"]["deploy_build"]["passed"] is True
    assert case_data["stages"]["deploy_publish"]["passed"] is True
