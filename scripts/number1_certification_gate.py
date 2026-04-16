from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
PROOF_DIR = ROOT / "proof" / "benchmarks"


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


@dataclass
class GateResult:
    category: str
    required: bool
    checks: list[CheckResult]

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)


def run_pytest(cmd: list[str]) -> tuple[bool, str]:
    full_cmd = [sys.executable, "-m", *cmd]
    try:
        proc = subprocess.run(
            full_cmd,
            cwd=str(BACKEND),
            capture_output=True,
            text=True,
            check=False,
            timeout=180,
        )
    except subprocess.TimeoutExpired as exc:
        return False, f"timeout after 180s while running: {' '.join(full_cmd)}"
    except KeyboardInterrupt:
        return False, "interrupted while running pytest subprocess"
    except Exception as exc:  # pragma: no cover - defensive runtime guard
        return False, f"subprocess error: {exc}"

    out = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return proc.returncode == 0, out.strip()


def run_builder(cmd: list[str]) -> tuple[bool, str]:
    full_cmd = [sys.executable, *cmd]
    try:
        proc = subprocess.run(
            full_cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        return False, f"timeout after 120s while running: {' '.join(full_cmd)}"
    except Exception as exc:  # pragma: no cover - defensive runtime guard
        return False, f"builder error: {exc}"

    out = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    return proc.returncode == 0, out.strip()


def exists(path: Path, label: str) -> CheckResult:
    return CheckResult(label, path.exists(), f"exists={path.exists()} path={path}")


def has_competitor_data(path: Path) -> CheckResult:
    if not path.exists():
        return CheckResult(
            "Competitor comparison artifact has real data",
            False,
            f"missing path={path}",
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return CheckResult(
            "Competitor comparison artifact has real data",
            False,
            f"invalid json: {exc}",
        )

    comparisons = payload.get("comparisons")
    winner = payload.get("winner")
    generated = payload.get("generated_at_utc")
    
    # AUDIT FIX: Require that competitor data be marked as verified/real
    # This prevents shipping with fabricated benchmark claims
    has_comparisons = isinstance(comparisons, list) and len(comparisons) > 0
    has_winner = bool(winner)
    has_timestamp = bool(generated)
    
    # Check if any systems in the artifact are marked as verified real benchmarks
    systems = payload.get("systems", [])
    has_verified_competitors = any(
        sys.get("data_source") == "real_benchmark_run" 
        for sys in systems 
        if sys.get("system") != "crucibai"
    )
    
    valid = has_comparisons and has_winner and has_timestamp and has_verified_competitors
    detail = (
        f"comparisons={len(comparisons) if isinstance(comparisons, list) else 'invalid'} "
        f"winner={winner!r} verified_competitors={has_verified_competitors}"
    )
    return CheckResult("Competitor comparison artifact has real data", valid, detail)


def build_results() -> list[GateResult]:
    build_ok, build_out = run_builder(["scripts/build_competitor_comparison.py"])

    focused_ok, focused_out = run_pytest(
        [
            "pytest",
            "tests/test_runtime_routes.py",
            "tests/test_worktrees_routes.py",
            "tests/test_spawn_simulation.py",
            "tests/test_runtime_eventing.py",
            "-q",
        ]
    )

    repeatability_test_ok, repeatability_test_out = run_pytest(
        ["pytest", "tests/test_repeatability_benchmark.py", "-q"]
    )

    internal = GateResult(
        category="Internal Engineering Integrity",
        required=True,
        checks=[
            CheckResult("Focused runtime/simulation suite", focused_ok, focused_out.splitlines()[-1] if focused_out else "no output"),
            exists(ROOT / "docs" / "ENGINEERING_COMPLETION_AUDIT_2026-04-15.md", "Engineering completion audit doc"),
            exists(ROOT / "backend" / "routes" / "runtime.py", "Runtime routes module"),
            exists(ROOT / "backend" / "routes" / "worktrees.py", "Worktrees routes module"),
        ],
    )

    reliability = GateResult(
        category="Reliability and Repeatability",
        required=True,
        checks=[
            CheckResult("Repeatability benchmark test", repeatability_test_ok, repeatability_test_out.splitlines()[-1] if repeatability_test_out else "no output"),
            exists(ROOT / "docs" / "REPEATABILITY_BENCHMARK.md", "Repeatability benchmark doc"),
        ],
    )

    production = GateResult(
        category="Production Evidence",
        required=True,
        checks=[
            exists(ROOT / "proof" / "END_TO_END_PROOF_REPORT.md", "End-to-end proof report"),
            exists(ROOT / "proof" / "COMPLETION_GATE_PROOF.md", "Completion gate proof"),
        ],
    )

    competitive = GateResult(
        category="Competitive Evidence",
        required=True,
        checks=[
            CheckResult("Competitor builder run", build_ok, build_out.splitlines()[-1] if build_out else "no output"),
            has_competitor_data(ROOT / "proof" / "benchmarks" / "competitor_comparison_latest.json"),
            exists(ROOT / "proof" / "benchmarks" / "competitor_methodology.md", "Competitor methodology"),
        ],
    )

    return [internal, reliability, production, competitive]


def write_scorecard(gates: list[GateResult]) -> None:
    PROOF_DIR.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).isoformat()
    overall = all(g.passed for g in gates if g.required)

    payload = {
        "timestamp_utc": ts,
        "overall_pass": overall,
        "number1_claim_allowed": overall,
        "gates": [
            {
                "category": g.category,
                "required": g.required,
                "passed": g.passed,
                "checks": [asdict(c) for c in g.checks],
            }
            for g in gates
        ],
    }

    json_path = PROOF_DIR / "number1_gate_latest.json"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines: list[str] = []
    lines.append("# Number 1 Gate Scorecard")
    lines.append("")
    lines.append(f"Generated: {ts}")
    lines.append("")
    lines.append(f"Overall pass: {'YES' if overall else 'NO'}")
    lines.append(f"Number 1 claim allowed: {'YES' if overall else 'NO'}")
    lines.append("")

    for g in gates:
        lines.append(f"## {g.category} ({'PASS' if g.passed else 'FAIL'})")
        lines.append("")
        for c in g.checks:
            status = "PASS" if c.passed else "FAIL"
            lines.append(f"- [{status}] {c.name}: {c.detail}")
        lines.append("")

    md_path = PROOF_DIR / "NUMBER1_GATE_SCORECARD.md"
    md_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    gates = build_results()
    write_scorecard(gates)
    overall = all(g.passed for g in gates if g.required)
    print("NUMBER1_GATE:", "PASS" if overall else "FAIL")
