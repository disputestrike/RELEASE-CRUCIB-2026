import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT / "scripts" / "build_competitor_comparison.py"


spec = importlib.util.spec_from_file_location("build_competitor_comparison", SCRIPT_PATH)
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules["build_competitor_comparison"] = mod
spec.loader.exec_module(mod)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_builder_writes_empty_comparisons_without_competitors(tmp_path, monkeypatch):
    bench = tmp_path / "proof" / "benchmarks"
    summary = bench / "repeatability_v1" / "summary.json"
    _write_json(
        summary,
        {
            "prompt_count": 50,
            "average_score": 100.0,
            "pass_rate": 1.0,
            "generated_at": "2026-04-16T00:00:00+00:00",
        },
    )

    monkeypatch.setattr(mod, "BENCH_DIR", bench)
    monkeypatch.setattr(mod, "COMPETITOR_RUNS_DIR", bench / "competitor_runs")
    monkeypatch.setattr(mod, "REPEATABILITY_SUMMARY", summary)
    monkeypatch.setattr(mod, "OUT_JSON", bench / "competitor_comparison_latest.json")
    monkeypatch.setattr(mod, "OUT_MD", bench / "COMPETITOR_COMPARISON_SCORECARD.md")

    rc = mod.main()
    assert rc == 0

    payload = json.loads((bench / "competitor_comparison_latest.json").read_text(encoding="utf-8"))
    assert payload["winner"] is None
    assert payload["comparisons"] == []
    assert len(payload["systems"]) == 1


def test_builder_creates_comparison_with_real_competitor(tmp_path, monkeypatch):
    bench = tmp_path / "proof" / "benchmarks"
    summary = bench / "repeatability_v1" / "summary.json"
    comp = bench / "competitor_runs" / "claude.json"

    _write_json(
        summary,
        {
            "prompt_count": 50,
            "average_score": 100.0,
            "pass_rate": 1.0,
            "generated_at": "2026-04-16T00:00:00+00:00",
        },
    )
    _write_json(
        comp,
        {
            "system": "claude",
            "generated_at_utc": "2026-04-16T00:10:00+00:00",
            "suite_name": "repeatability_prompts_v1",
            "prompt_count": 50,
            "average_score": 93.5,
            "pass_rate": 0.94,
        },
    )

    monkeypatch.setattr(mod, "BENCH_DIR", bench)
    monkeypatch.setattr(mod, "COMPETITOR_RUNS_DIR", bench / "competitor_runs")
    monkeypatch.setattr(mod, "REPEATABILITY_SUMMARY", summary)
    monkeypatch.setattr(mod, "OUT_JSON", bench / "competitor_comparison_latest.json")
    monkeypatch.setattr(mod, "OUT_MD", bench / "COMPETITOR_COMPARISON_SCORECARD.md")

    rc = mod.main()
    assert rc == 0

    payload = json.loads((bench / "competitor_comparison_latest.json").read_text(encoding="utf-8"))
    assert payload["winner"] == "crucibai"
    assert len(payload["comparisons"]) == 1

    c = payload["comparisons"][0]
    assert c["against"] == "claude"
    assert c["winner_by_quality"] == "crucibai"
    assert c["prompt_count_match"] is True
