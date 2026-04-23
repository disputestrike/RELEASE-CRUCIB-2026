from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BENCH_DIR = ROOT / "proof" / "benchmarks"
COMPETITOR_RUNS_DIR = BENCH_DIR / "competitor_runs"
REPEATABILITY_SUMMARY = BENCH_DIR / "repeatability_v1" / "summary.json"
OUT_JSON = BENCH_DIR / "competitor_comparison_latest.json"
OUT_MD = BENCH_DIR / "COMPETITOR_COMPARISON_SCORECARD.md"


@dataclass
class SystemMetrics:
    system: str
    prompt_count: int
    average_score: float
    pass_rate: float
    generated_at_utc: str | None
    latency_p50_sec: float | None = None
    cost_per_prompt_usd: float | None = None
    notes: str | None = None


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _as_int(v: Any, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def load_crucibai_metrics() -> SystemMetrics:
    if not REPEATABILITY_SUMMARY.exists():
        raise FileNotFoundError(f"Missing repeatability summary: {REPEATABILITY_SUMMARY}")

    payload = _read_json(REPEATABILITY_SUMMARY)
    return SystemMetrics(
        system="crucibai",
        prompt_count=_as_int(payload.get("prompt_count"), 0),
        average_score=_as_float(payload.get("average_score"), 0.0),
        pass_rate=_as_float(payload.get("pass_rate"), 0.0),
        generated_at_utc=payload.get("generated_at"),
        notes="Derived from repeatability_v1 summary",
    )


def load_competitor_metrics() -> list[SystemMetrics]:
    rows: list[SystemMetrics] = []
    if not COMPETITOR_RUNS_DIR.exists():
        return rows

    for path in sorted(COMPETITOR_RUNS_DIR.glob("*.json")):
        if path.name.endswith(".sample.json"):
            continue
        try:
            payload = _read_json(path)
        except Exception:
            continue

        system = str(payload.get("system") or "").strip().lower()
        if not system or system == "crucibai":
            continue

        rows.append(
            SystemMetrics(
                system=system,
                prompt_count=_as_int(payload.get("prompt_count"), 0),
                average_score=_as_float(payload.get("average_score"), 0.0),
                pass_rate=_as_float(payload.get("pass_rate"), 0.0),
                generated_at_utc=payload.get("generated_at_utc"),
                latency_p50_sec=(None if payload.get("latency_p50_sec") is None else _as_float(payload.get("latency_p50_sec"), 0.0)),
                cost_per_prompt_usd=(None if payload.get("cost_per_prompt_usd") is None else _as_float(payload.get("cost_per_prompt_usd"), 0.0)),
                notes=payload.get("notes"),
            )
        )

    return rows


def build_payload() -> dict[str, Any]:
    crucib = load_crucibai_metrics()
    competitors = load_competitor_metrics()

    systems: list[dict[str, Any]] = [crucib.__dict__] + [c.__dict__ for c in competitors]

    comparisons: list[dict[str, Any]] = []
    for c in competitors:
        winner_quality: str
        if c.average_score > crucib.average_score:
            winner_quality = c.system
        elif c.average_score < crucib.average_score:
            winner_quality = "crucibai"
        else:
            winner_quality = "tie"

        comparisons.append(
            {
                "against": c.system,
                "prompt_count_match": c.prompt_count == crucib.prompt_count and c.prompt_count > 0,
                "delta_average_score": round(crucib.average_score - c.average_score, 4),
                "delta_pass_rate": round(crucib.pass_rate - c.pass_rate, 4),
                "winner_by_quality": winner_quality,
            }
        )

    winner: str | None = None
    if competitors:
        ranked = sorted(
            [crucib, *competitors],
            key=lambda x: (x.average_score, x.pass_rate),
            reverse=True,
        )
        winner = ranked[0].system

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "suite_name": "repeatability_prompts_v1",
        "systems": systems,
        "comparisons": comparisons,
        "winner": winner,
        "notes": "Comparisons are generated from local normalized competitor run files.",
    }


def write_markdown(payload: dict[str, Any]) -> None:
    lines: list[str] = []
    lines.append("# Competitor Comparison Scorecard")
    lines.append("")
    lines.append(f"Generated: {payload.get('generated_at_utc')}")
    lines.append("")
    lines.append(f"Winner: {payload.get('winner')}")
    lines.append("")

    lines.append("## Systems")
    lines.append("")
    for s in payload.get("systems", []):
        lines.append(
            "- "
            + f"{s.get('system')}: avg={s.get('average_score')} pass_rate={s.get('pass_rate')} prompts={s.get('prompt_count')}"
        )
    lines.append("")

    lines.append("## Comparisons")
    lines.append("")
    comparisons = payload.get("comparisons", [])
    if comparisons:
        for c in comparisons:
            lines.append(
                "- "
                + f"vs {c.get('against')}: "
                + f"delta_avg={c.get('delta_average_score')} "
                + f"delta_pass={c.get('delta_pass_rate')} "
                + f"winner_by_quality={c.get('winner_by_quality')} "
                + f"prompt_count_match={c.get('prompt_count_match')}"
            )
    else:
        lines.append("- No competitor runs loaded. Add JSON files under proof/benchmarks/competitor_runs/.")

    OUT_MD.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def main() -> int:
    BENCH_DIR.mkdir(parents=True, exist_ok=True)
    payload = build_payload()
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    write_markdown(payload)

    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {OUT_MD}")
    print(f"comparisons={len(payload.get('comparisons', []))} winner={payload.get('winner')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
