"""Deterministic repeatability benchmark for the CrucibAI golden path.

This benchmark is intentionally production-shaped but cheap enough for a release
gate. It does not spend live LLM credits. Instead, it exercises the deterministic
fallback scaffold, preview gate, elite proof gate, and deploy readiness gates
across a suite of product prompts. Live replay remains covered by
scripts/live-production-golden-path.py.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from orchestration.executor import (
    _ensure_backend_elite_hardening,
    _main_py_sketch,
    _safe_write,
    handle_delivery_manifest,
    handle_deploy,
)
from orchestration.generated_app_template import build_frontend_file_set
from orchestration.preview_gate import verify_preview_workspace
from orchestration.verifier import verify_deploy_step, verify_step

BENCHMARK_VERSION = "2026-04-08.repeatability.v1"
DEFAULT_MIN_PASS_RATE = 0.90
DEFAULT_MIN_AVERAGE_SCORE = 90.0
DEFAULT_REQUIRED_FILES = [
    "package.json",
    "index.html",
    "vite.config.js",
    "src/App.jsx",
    "src/main.jsx",
    "src/components/ErrorBoundary.jsx",
    "src/context/AuthContext.jsx",
    "src/store/useAppStore.js",
    "proof/DELIVERY_CLASSIFICATION.md",
    "proof/ELITE_EXECUTION_DIRECTIVE.md",
    "backend/main.py",
    "Dockerfile",
    "deploy/PRODUCTION_SKETCH.md",
    "deploy/PUBLISH.md",
]


@dataclass(frozen=True)
class PromptCase:
    id: str
    category: str
    title: str
    goal: str
    build_target: str
    required_terms: List[str]


@contextmanager
def _temporary_env(updates: Mapping[str, str]):
    before = {key: os.environ.get(key) for key in updates}
    try:
        for key, value in updates.items():
            os.environ[key] = value
        yield
    finally:
        for key, value in before.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_sha256(value: Any) -> str:
    data = json.dumps(value, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def load_prompt_suite(path: Path) -> Dict[str, Any]:
    suite = json.loads(path.read_text(encoding="utf-8"))
    cases = suite.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError(f"Prompt suite has no cases: {path}")
    seen = set()
    for raw in cases:
        cid = raw.get("id")
        if not cid:
            raise ValueError("Prompt case missing id")
        if cid in seen:
            raise ValueError(f"Duplicate prompt id: {cid}")
        seen.add(cid)
        if not raw.get("goal"):
            raise ValueError(f"Prompt case missing goal: {cid}")
    return suite


def parse_cases(suite: Mapping[str, Any]) -> List[PromptCase]:
    out: List[PromptCase] = []
    for raw in suite.get("cases") or []:
        out.append(
            PromptCase(
                id=str(raw["id"]),
                category=str(raw.get("category") or "uncategorized"),
                title=str(raw.get("title") or raw["id"]),
                goal=str(raw["goal"]),
                build_target=str(raw.get("build_target") or "vite_react"),
                required_terms=[str(term) for term in raw.get("required_terms") or []],
            )
        )
    return out


def _read_workspace_texts(workspace: Path) -> Dict[str, str]:
    texts: Dict[str, str] = {}
    skip = {"node_modules", ".git", "dist", "build", ".next", "__pycache__"}
    for root, dirs, files in os.walk(workspace):
        dirs[:] = [d for d in dirs if d not in skip]
        for name in files:
            if not name.endswith(
                (".md", ".js", ".jsx", ".json", ".css", ".py", ".sh", ".html")
            ):
                continue
            full = Path(root) / name
            rel = full.relative_to(workspace).as_posix()
            try:
                texts[rel] = full.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
    return texts


def _file_status(workspace: Path, required_files: Iterable[str]) -> Dict[str, Any]:
    missing = [rel for rel in required_files if not (workspace / rel).is_file()]
    return {
        "passed": not missing,
        "missing": missing,
        "required_count": len(list(required_files)),
    }


def _term_coverage(case: PromptCase, workspace: Path) -> Dict[str, Any]:
    texts = _read_workspace_texts(workspace)
    haystack = "\n".join(texts.values()).lower()
    missing = [term for term in case.required_terms if term.lower() not in haystack]
    return {
        "passed": not missing,
        "required_terms": case.required_terms,
        "missing_terms": missing,
        "checked_file_count": len(texts),
    }


def _stage_result(
    name: str,
    passed: bool,
    *,
    score: float = 100.0,
    detail: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "name": name,
        "passed": bool(passed),
        "score": float(score if passed else min(score, 60.0)),
        "detail": detail or {},
    }


def _case_score(stages: Mapping[str, Mapping[str, Any]]) -> float:
    weights = {
        "generated_files": 15.0,
        "prompt_coverage": 10.0,
        "preview": 25.0,
        "elite_proof": 25.0,
        "deploy_build": 15.0,
        "deploy_publish": 10.0,
    }
    total = 0.0
    for name, weight in weights.items():
        stage = stages.get(name) or {}
        if stage.get("passed"):
            total += weight
        else:
            total += weight * (float(stage.get("score") or 0.0) / 100.0)
    return round(total, 2)


async def run_prompt_case(
    case: PromptCase,
    workspace_root: Path,
    *,
    run_browser_preview: bool = False,
) -> Dict[str, Any]:
    workspace = workspace_root / case.id
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True, exist_ok=True)

    job = {
        "id": f"benchmark-{case.id}",
        "goal": case.goal,
        "build_target": case.build_target,
        "mode": "benchmark",
    }

    generated_files: List[str] = []
    for rel, content in build_frontend_file_set(job):
        written = _safe_write(str(workspace), rel, content)
        if written:
            generated_files.append(written)
    backend_rel = _safe_write(
        str(workspace), "backend/main.py", _main_py_sketch(multitenant=False)
    )
    if backend_rel:
        generated_files.append(backend_rel)
    hardened = _ensure_backend_elite_hardening(str(workspace))
    if hardened and hardened not in generated_files:
        generated_files.append(hardened)

    manifest = await handle_delivery_manifest(
        {"step_key": "implementation.delivery_manifest"}, job, str(workspace)
    )
    generated_files.extend(manifest.get("output_files") or [])

    deploy_build_output = await handle_deploy(
        {"step_key": "deploy.build"}, job, str(workspace)
    )
    generated_files.extend(deploy_build_output.get("output_files") or [])
    deploy_publish_output = await handle_deploy(
        {"step_key": "deploy.publish"}, job, str(workspace)
    )
    generated_files.extend(deploy_publish_output.get("output_files") or [])

    env_updates = {
        "CRUCIBAI_ELITE_BUILDER_GATE": "strict",
        "CRUCIBAI_REQUIRE_LIVE_DEPLOY_PUBLISH": "",
    }
    if not run_browser_preview:
        env_updates["CRUCIBAI_SKIP_BROWSER_PREVIEW"] = "1"

    with _temporary_env(env_updates):
        preview = await verify_preview_workspace(str(workspace))
        elite = await verify_step(
            {"step_key": "verification.elite_builder", "job_goal": case.goal},
            str(workspace),
        )
        deploy_build = await verify_deploy_step(
            {**deploy_build_output, "step_key": "deploy.build"},
            str(workspace),
        )
        deploy_publish = await verify_deploy_step(
            {**deploy_publish_output, "step_key": "deploy.publish"},
            str(workspace),
        )

    file_gate = _file_status(workspace, DEFAULT_REQUIRED_FILES)
    coverage = _term_coverage(case, workspace)
    stages = {
        "generated_files": _stage_result(
            "generated_files",
            file_gate["passed"],
            detail={**file_gate, "generated_file_count": len(set(generated_files))},
        ),
        "prompt_coverage": _stage_result(
            "prompt_coverage",
            coverage["passed"],
            detail=coverage,
        ),
        "preview": _stage_result(
            "preview",
            bool(preview.get("passed")),
            score=float(preview.get("score") or 0.0),
            detail={
                "mode": (
                    "browser" if run_browser_preview else "static_plus_skipped_browser"
                ),
                "failure_reason": preview.get("failure_reason"),
                "issues": preview.get("issues") or [],
                "proof_count": len(preview.get("proof") or []),
            },
        ),
        "elite_proof": _stage_result(
            "elite_proof",
            bool(elite.get("passed")),
            score=float(elite.get("score") or 0.0),
            detail={
                "failure_reason": elite.get("failure_reason"),
                "issues": elite.get("issues") or [],
                "failed_checks": elite.get("failed_checks") or [],
                "proof_count": len(elite.get("proof") or []),
            },
        ),
        "deploy_build": _stage_result(
            "deploy_build",
            bool(deploy_build.get("passed")),
            score=float(deploy_build.get("score") or 0.0),
            detail={
                "failure_reason": deploy_build.get("failure_reason"),
                "issues": deploy_build.get("issues") or [],
                "proof_count": len(deploy_build.get("proof") or []),
            },
        ),
        "deploy_publish": _stage_result(
            "deploy_publish",
            bool(deploy_publish.get("passed")),
            score=float(deploy_publish.get("score") or 0.0),
            detail={
                "failure_reason": deploy_publish.get("failure_reason"),
                "issues": deploy_publish.get("issues") or [],
                "proof_count": len(deploy_publish.get("proof") or []),
                "publish_mode": "readiness_only",
            },
        ),
    }
    score = _case_score(stages)
    passed = all(stage.get("passed") for stage in stages.values())

    manifest_payload = {
        "case": case.__dict__,
        "score": score,
        "passed": passed,
        "stages": stages,
        "workspace": str(workspace),
        "generated_files": sorted(set(generated_files)),
    }
    (workspace / ".crucibai_benchmark_manifest.json").write_text(
        json.dumps(manifest_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return manifest_payload


def _write_markdown_report(out_dir: Path, summary: Mapping[str, Any]) -> None:
    lines = [
        "# CrucibAI Repeatability Benchmark",
        "",
        f"- Version: `{summary['benchmark_version']}`",
        f"- Generated at: `{summary['generated_at']}`",
        f"- Prompt count: `{summary['prompt_count']}`",
        f"- Passed count: `{summary['passed_count']}`",
        f"- Pass rate: `{summary['pass_rate']:.2%}`",
        f"- Average score: `{summary['average_score']:.2f}`",
        f"- Required pass rate: `{summary['thresholds']['min_pass_rate']:.2%}`",
        f"- Required average score: `{summary['thresholds']['min_average_score']:.2f}`",
        f"- Overall: `{'PASS' if summary['passed'] else 'FAIL'}`",
        "",
        "| Case | Category | Score | Status | Failed stages |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for result in summary["results"]:
        failed = [
            name for name, stage in result["stages"].items() if not stage.get("passed")
        ]
        lines.append(
            f"| `{result['case']['id']}` | {result['case']['category']} | "
            f"{result['score']:.2f} | {'PASS' if result['passed'] else 'FAIL'} | "
            f"{', '.join(failed) if failed else '-'} |"
        )
    lines.extend(["", "## Blockers"])
    if summary["blockers"]:
        lines.extend(f"- {item}" for item in summary["blockers"])
    else:
        lines.append("- None recorded.")
    (out_dir / "PASS_FAIL.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


async def run_benchmark(
    *,
    suite_path: Path,
    output_dir: Path,
    run_browser_preview: bool = False,
    min_pass_rate: float = DEFAULT_MIN_PASS_RATE,
    min_average_score: float = DEFAULT_MIN_AVERAGE_SCORE,
) -> Dict[str, Any]:
    suite = load_prompt_suite(suite_path)
    cases = parse_cases(suite)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    workspace_root = output_dir / "workspaces"
    case_dir = output_dir / "cases"
    workspace_root.mkdir(parents=True, exist_ok=True)
    case_dir.mkdir(parents=True, exist_ok=True)

    results: List[Dict[str, Any]] = []
    for case in cases:
        result = await run_prompt_case(
            case, workspace_root, run_browser_preview=run_browser_preview
        )
        results.append(result)
        (case_dir / f"{case.id}.json").write_text(
            json.dumps(result, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    passed_count = sum(1 for item in results if item["passed"])
    prompt_count = len(results)
    pass_rate = passed_count / max(1, prompt_count)
    average_score = round(
        sum(float(item["score"]) for item in results) / max(1, prompt_count), 2
    )
    blockers: List[str] = []
    if pass_rate < min_pass_rate:
        blockers.append(
            f"pass_rate_below_threshold:{pass_rate:.2%}<{min_pass_rate:.2%}"
        )
    if average_score < min_average_score:
        blockers.append(
            f"average_score_below_threshold:{average_score:.2f}<{min_average_score:.2f}"
        )
    for item in results:
        if not item["passed"]:
            blockers.append(f"case_failed:{item['case']['id']}")

    summary = {
        "benchmark_version": BENCHMARK_VERSION,
        "suite_version": suite.get("version"),
        "generated_at": utc_now(),
        "prompt_count": prompt_count,
        "passed_count": passed_count,
        "pass_rate": pass_rate,
        "average_score": average_score,
        "thresholds": {
            "min_pass_rate": min_pass_rate,
            "min_average_score": min_average_score,
        },
        "preview_mode": (
            "browser" if run_browser_preview else "static_plus_skipped_browser"
        ),
        "passed": not blockers,
        "blockers": blockers,
        "results": results,
    }
    summary["summary_sha256"] = stable_sha256(
        {k: v for k, v in summary.items() if k != "summary_sha256"}
    )

    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _write_markdown_report(output_dir, summary)
    return summary


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def main(argv: Optional[List[str]] = None) -> int:
    root = _default_repo_root()
    parser = argparse.ArgumentParser(
        description="Run CrucibAI repeatability benchmark."
    )
    parser.add_argument(
        "--suite", default=str(root / "benchmarks" / "repeatability_prompts_v1.json")
    )
    parser.add_argument(
        "--output-dir", default=str(root / "proof" / "benchmarks" / "repeatability_v1")
    )
    parser.add_argument("--run-browser-preview", action="store_true")
    parser.add_argument("--min-pass-rate", type=float, default=DEFAULT_MIN_PASS_RATE)
    parser.add_argument(
        "--min-average-score", type=float, default=DEFAULT_MIN_AVERAGE_SCORE
    )
    args = parser.parse_args(argv)

    summary = asyncio.run(
        run_benchmark(
            suite_path=Path(args.suite),
            output_dir=Path(args.output_dir),
            run_browser_preview=args.run_browser_preview,
            min_pass_rate=args.min_pass_rate,
            min_average_score=args.min_average_score,
        )
    )
    print(
        json.dumps(
            {
                "passed": summary["passed"],
                "prompt_count": summary["prompt_count"],
                "pass_rate": summary["pass_rate"],
                "average_score": summary["average_score"],
                "output_dir": str(Path(args.output_dir)),
                "summary_sha256": summary["summary_sha256"],
                "blockers": summary["blockers"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
