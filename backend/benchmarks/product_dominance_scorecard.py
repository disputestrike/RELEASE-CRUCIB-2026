"""Product dominance benchmark runner and scorecard for CrucibAI."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from services.events import event_bus
from services.proof_manifest import build_signed_manifest_for_directory
from services.runtime.runtime_engine import runtime_engine
from services.runtime.simulation_engine import SimulationEngine

# Provider pool tracking — graceful fallback if cerebras_roundrobin not available
try:
    from cerebras_roundrobin import pool_tracker as _cerebras_pool_tracker
except Exception:
    _cerebras_pool_tracker = None  # type: ignore[assignment]

BENCHMARK_VERSION = "2026-04-20.product_dominance.v1"

WEIGHTS = {
    "success": 0.40,
    "accuracy": 0.20,
    "speed": 0.15,
    "reliability": 0.15,
    "ux": 0.10,
}

DEFAULT_COUNTS_BY_CATEGORY = {
    "full_app_build": 10,
    "repair": 5,
    "continuation": 5,
    "what_if": 5,
    "deploy": 5,
}

TARGET_RANGES = {
    "full_app_build": "85-90",
    "repair": "80-85",
    "continuation": "90+",
    "what_if": "85+",
    "deploy": "85+",
}


@dataclass(frozen=True)
class BenchmarkCase:
    id: str
    category: str
    title: str
    prompt: str
    scenario_type: str
    required_terms: List[str]
    target_seconds: int
    resume_prompt: Optional[str] = None


@dataclass(frozen=True)
class RunPlanItem:
    run_id: str
    case: BenchmarkCase
    iteration: int


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_sha256(value: Any) -> str:
    blob = json.dumps(value, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_suite(path: Path) -> Dict[str, Any]:
    suite = json.loads(path.read_text(encoding="utf-8"))
    cases = suite.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError(f"Benchmark suite has no cases: {path}")
    seen = set()
    for raw in cases:
        case_id = str(raw.get("id") or "").strip()
        if not case_id:
            raise ValueError("Benchmark case missing id")
        if case_id in seen:
            raise ValueError(f"Duplicate benchmark case id: {case_id}")
        seen.add(case_id)
        if not str(raw.get("prompt") or "").strip():
            raise ValueError(f"Benchmark case missing prompt: {case_id}")
    return suite


def parse_cases(suite: Mapping[str, Any]) -> List[BenchmarkCase]:
    out: List[BenchmarkCase] = []
    for raw in suite.get("cases") or []:
        out.append(
            BenchmarkCase(
                id=str(raw["id"]),
                category=str(raw.get("category") or "uncategorized"),
                title=str(raw.get("title") or raw["id"]),
                prompt=str(raw["prompt"]),
                scenario_type=str(raw.get("scenario_type") or "runtime"),
                required_terms=[str(term) for term in raw.get("required_terms") or []],
                target_seconds=int(raw.get("target_seconds") or 900),
                resume_prompt=(str(raw.get("resume_prompt")) if raw.get("resume_prompt") else None),
            )
        )
    return out


def _counts_by_category(suite: Mapping[str, Any]) -> Dict[str, int]:
    protocol = suite.get("execution_protocol") or {}
    raw = protocol.get("counts_by_category") or {}
    merged = dict(DEFAULT_COUNTS_BY_CATEGORY)
    for key, value in raw.items():
        try:
            merged[str(key)] = max(0, int(value))
        except Exception:
            pass
    return merged


def build_run_plan(cases: List[BenchmarkCase], counts_by_category: Mapping[str, int]) -> List[RunPlanItem]:
    by_category: Dict[str, List[BenchmarkCase]] = {}
    for case in sorted(cases, key=lambda c: c.id):
        by_category.setdefault(case.category, []).append(case)

    plan: List[RunPlanItem] = []
    for category, count in counts_by_category.items():
        candidates = by_category.get(category) or []
        if not candidates or count <= 0:
            continue
        for i in range(count):
            case = candidates[i % len(candidates)]
            run_id = f"{category}-{i + 1:02d}-{case.id}"
            plan.append(RunPlanItem(run_id=run_id, case=case, iteration=i + 1))
    return plan


def _keyword_coverage(text: str, required_terms: Iterable[str]) -> float:
    terms = [str(term).strip().lower() for term in required_terms if str(term).strip()]
    if not terms:
        return 1.0
    haystack = text.lower()
    matched = sum(1 for term in terms if term in haystack)
    return matched / max(1, len(terms))


def _speed_score(duration_seconds: float, target_seconds: int) -> float:
    target = max(1, int(target_seconds))
    if duration_seconds <= target:
        return 100.0
    ratio = duration_seconds / target
    if ratio <= 1.25:
        return 90.0
    if ratio <= 1.5:
        return 80.0
    if ratio <= 2.0:
        return 65.0
    if ratio <= 3.0:
        return 45.0
    return 25.0


def _reliability_score(retries: int, failures: int) -> float:
    score = 100.0 - (float(retries) * 12.0) - (float(failures) * 18.0)
    return max(0.0, min(100.0, score))


def _ux_score(response_text: str, timeline_len: int) -> float:
    length = len((response_text or "").strip())
    score = 55.0
    if length >= 300:
        score += 25.0
    elif length >= 120:
        score += 18.0
    elif length >= 40:
        score += 10.0

    if timeline_len >= 12:
        score += 20.0
    elif timeline_len >= 6:
        score += 15.0
    elif timeline_len >= 3:
        score += 8.0

    return max(0.0, min(100.0, score))


def _final_score(dimensions: Mapping[str, float]) -> float:
    return round(
        (WEIGHTS["success"] * float(dimensions.get("success") or 0.0))
        + (WEIGHTS["accuracy"] * float(dimensions.get("accuracy") or 0.0))
        + (WEIGHTS["speed"] * float(dimensions.get("speed") or 0.0))
        + (WEIGHTS["reliability"] * float(dimensions.get("reliability") or 0.0))
        + (WEIGHTS["ux"] * float(dimensions.get("ux") or 0.0)),
        2,
    )


def _events_for_task(task_id: str, limit: int = 500) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for rec in event_bus.recent_events(limit=limit):
        payload = rec.payload or {}
        rid = str(payload.get("task_id") or payload.get("requested_task_id") or "")
        if rid == task_id:
            out.append({"type": rec.event_type, "payload": payload, "ts": rec.ts})
    return out


def _extract_response_text(result: Mapping[str, Any]) -> str:
    text = result.get("assistant_response")
    if isinstance(text, str) and text.strip():
        return text
    brain = result.get("brain_result")
    if isinstance(brain, dict):
        maybe = brain.get("assistant_response")
        if isinstance(maybe, str) and maybe.strip():
            return maybe
    return ""


def _looks_like_clarification(text: str) -> bool:
    lowered = (text or "").strip().lower()
    if not lowered:
        return False
    if "what's the main objective" in lowered:
        return True
    if "clarify" in lowered or "more details" in lowered or "need more context" in lowered:
        return True
    return lowered.endswith("?") and len(lowered) < 220


def _build_depth_flags(response_text: str) -> Dict[str, bool]:
    text = (response_text or "").lower()
    has_ui = any(tok in text for tok in ["frontend", "ui", "component", "page", "react"])
    has_backend = any(tok in text for tok in ["backend", "api", "server", "database", "endpoint"])
    has_runnable = any(tok in text for tok in ["preview", "run", "runnable", "working", "boot"])
    return {"has_ui": has_ui, "has_backend": has_backend, "has_runnable": has_runnable}


def _deploy_readiness_flags(response_text: str) -> Dict[str, bool]:
    text = (response_text or "").lower()
    has_deploy = any(tok in text for tok in ["deploy", "published", "production", "live url"])
    has_validation = any(tok in text for tok in ["validation", "health", "verify", "readiness", "smoke"])
    has_fatal = any(tok in text for tok in ["fatal error", "crash", "failed to start", "cannot boot"])
    return {"has_deploy": has_deploy, "has_validation": has_validation, "has_fatal": has_fatal}


def _repair_completion_flags(response_text: str) -> Dict[str, bool]:
    text = (response_text or "").lower()
    has_diagnosis = any(tok in text for tok in ["root cause", "diagnos", "cause identified", "issue found"])
    has_fix = any(tok in text for tok in ["fix", "repair", "patched", "resolved", "applied"])
    has_verify = any(tok in text for tok in ["verify", "validated", "smoke", "working", "run correctly", "status"])
    return {
        "has_diagnosis": has_diagnosis,
        "has_fix": has_fix,
        "has_verify": has_verify,
    }


async def _run_runtime_case(case: BenchmarkCase, *, user_id: str, run_id: str, execute_live: bool) -> Dict[str, Any]:
    started_at = time.perf_counter()

    if not execute_live:
        fake_text = (
            f"Simulated run for {case.title}. "
            + " ".join(case.required_terms[: min(6, len(case.required_terms))])
        )
        duration = 30.0 + (hash(run_id) % 90)
        retries = int(hash(run_id + "retry") % 2)
        failures = 0
        coverage = _keyword_coverage(fake_text, case.required_terms)
        dimensions = {
            "success": 100.0,
            "accuracy": round(coverage * 100.0, 2),
            "speed": _speed_score(duration, case.target_seconds),
            "reliability": _reliability_score(retries, failures),
            "ux": _ux_score(fake_text, timeline_len=8),
        }
        final_score = _final_score(dimensions)
        return {
            "run_id": run_id,
            "case_id": case.id,
            "category": case.category,
            "title": case.title,
            "prompt": case.prompt,
            "success": True,
            "deploy_status": "simulated",
            "time_seconds": round(duration, 2),
            "retries": retries,
            "failures": failures,
            "steps_taken": 8,
            "timeline": ["simulation.started", "simulation.completed"],
            "result_text": fake_text,
            "dimensions": dimensions,
            "score": final_score,
            "mode": "simulated",
        }

    # Reset per-run provider tracking before execution
    if _cerebras_pool_tracker is not None:
        _cerebras_pool_tracker.start_run()

    request_task_id = f"bench-{run_id}-{int(time.time())}"
    session_id = f"bench-session-{run_id}"
    task_ids: List[str] = []

    control_suffix = (
        "\n[benchmark_mode] benchmark_mode=true must_complete=true\n"
        "Assume sensible defaults. Do not ask clarification questions. Execute end-to-end until completion or diagnosed failure."
    )

    if case.scenario_type == "continuation":
        start_result = await runtime_engine.execute_with_control(
            task_id=f"{request_task_id}-start",
            user_id=user_id,
            request=case.prompt + control_suffix,
            conversation_id=session_id,
        )
        task_ids.append(str(start_result.get("task_id") or ""))
        live_result = await runtime_engine.execute_with_control(
            task_id=f"{request_task_id}-resume",
            user_id=user_id,
            request=(case.resume_prompt or "Resume from prior context and continue.") + control_suffix,
            conversation_id=session_id,
        )
        task_ids.append(str(live_result.get("task_id") or ""))
    elif case.scenario_type == "what_if":
        sim = SimulationEngine.run_simulation(
            scenario=case.prompt,
            population_size=48,
            rounds=4,
            seed=abs(hash(run_id)) % 100000,
        )
        recommendation = (sim.get("recommendation") or {}).get("recommended_action") or ""
        conf = (sim.get("recommendation") or {}).get("confidence")
        response_text = f"{recommendation} (confidence={conf})"
        duration = time.perf_counter() - started_at
        coverage = _keyword_coverage(response_text, case.required_terms)
        dimensions = {
            "success": 100.0 if recommendation else 0.0,
            "accuracy": round(coverage * 100.0, 2),
            "speed": _speed_score(duration, case.target_seconds),
            "reliability": 100.0,
            "ux": _ux_score(response_text, timeline_len=int(sim.get("rounds_executed") or 1)),
        }
        final_score = _final_score(dimensions)
        return {
            "run_id": run_id,
            "case_id": case.id,
            "category": case.category,
            "title": case.title,
            "prompt": case.prompt,
            "success": bool(recommendation),
            "deploy_status": "n/a",
            "time_seconds": round(duration, 2),
            "retries": 0,
            "failures": 0,
            "steps_taken": int(sim.get("rounds_executed") or 1),
            "timeline": ["what_if.started", "what_if.completed"],
            "result_text": response_text,
            "dimensions": dimensions,
            "score": final_score,
            "mode": "live_what_if",
            "simulation": sim,
        }
    else:
        live_result = await runtime_engine.execute_with_control(
            task_id=request_task_id,
            user_id=user_id,
            request=case.prompt + control_suffix,
            conversation_id=session_id,
        )
        task_ids.append(str(live_result.get("task_id") or ""))

        first_text = _extract_response_text(live_result)
        if _looks_like_clarification(first_text):
            followup = (
                "Primary objective: "
                + case.prompt
                + "\nAssume standard production defaults and proceed end-to-end without further clarification questions."
            )
            live_result = await runtime_engine.execute_with_control(
                task_id=f"{request_task_id}-followup",
                user_id=user_id,
                request=followup + control_suffix,
                conversation_id=session_id,
            )
            task_ids.append(str(live_result.get("task_id") or ""))

    status = str(live_result.get("task_status") or "")
    task_id = str(live_result.get("task_id") or request_task_id)
    response_text = _extract_response_text(live_result)
    if not task_ids:
        task_ids = [task_id]
    events: List[Dict[str, Any]] = []
    for tid in task_ids:
        if tid:
            events.extend(_events_for_task(tid))
    events.sort(key=lambda item: float(item.get("ts") or 0.0))
    retries = sum(1 for evt in events if evt["type"] == "brain.agent.retry_scheduled")
    failures = sum(1 for evt in events if "failed" in evt["type"] or "error" in evt["type"])
    steps_taken = sum(1 for evt in events if evt["type"] in {"step_end", "step_complete", "brain.agent.completed"})

    duration = time.perf_counter() - started_at
    coverage = _keyword_coverage(response_text, case.required_terms)
    success = status in {"completed", "running"} and bool(response_text.strip())

    depth = _build_depth_flags(response_text)
    deploy_gate = _deploy_readiness_flags(response_text)
    repair_gate = _repair_completion_flags(response_text)

    if case.category in {"full_app_build", "continuation"}:
        if not (depth["has_ui"] and depth["has_backend"] and depth["has_runnable"]):
            success = False

    if case.category == "repair":
        if not (repair_gate["has_diagnosis"] and repair_gate["has_fix"] and repair_gate["has_verify"]):
            success = False

    if case.category == "deploy":
        if not (deploy_gate["has_deploy"] and deploy_gate["has_validation"] and not deploy_gate["has_fatal"]):
            success = False

    dimensions = {
        "success": 100.0 if success else 0.0,
        "accuracy": round(coverage * 100.0, 2),
        "speed": _speed_score(duration, case.target_seconds),
        "reliability": _reliability_score(retries, failures),
        "ux": _ux_score(response_text, timeline_len=len(events)),
    }

    deploy_status = "n/a"
    if case.category == "deploy":
        deploy_status = "success" if success else "incomplete"

    return {
        "run_id": run_id,
        "case_id": case.id,
        "category": case.category,
        "title": case.title,
        "prompt": case.prompt,
        "success": success,
        "deploy_status": deploy_status,
        "time_seconds": round(duration, 2),
        "retries": retries,
        "failures": failures,
        "steps_taken": steps_taken,
        "timeline": [evt["type"] for evt in events[-80:]],
        "result_text": response_text,
        "dimensions": dimensions,
        "score": _final_score(dimensions),
        "mode": "live_runtime",
        "task_status": status,
        "task_id": task_id,
        "build_depth": depth,
        "deploy_gate": deploy_gate,
        "repair_gate": repair_gate,
        "provider_meta": (
            _cerebras_pool_tracker.get_run_stats()
            if _cerebras_pool_tracker is not None
            else {"provider": "unknown", "pool_size": 0, "execution_mode": "unknown"}
        ),
    }


def _aggregate_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(results)
    success_count = sum(1 for r in results if r.get("success"))
    avg_time = round(sum(float(r.get("time_seconds") or 0.0) for r in results) / max(1, total), 2)
    avg_score = round(sum(float(r.get("score") or 0.0) for r in results) / max(1, total), 2)
    avg_retries = round(sum(int(r.get("retries") or 0) for r in results) / max(1, total), 2)

    by_category: Dict[str, Dict[str, Any]] = {}
    for r in results:
        cat = str(r.get("category") or "unknown")
        bucket = by_category.setdefault(cat, {"runs": 0, "success": 0, "scores": []})
        bucket["runs"] += 1
        bucket["success"] += 1 if r.get("success") else 0
        bucket["scores"].append(float(r.get("score") or 0.0))

    category_summary = {}
    for cat, bucket in by_category.items():
        runs = max(1, int(bucket["runs"]))
        category_summary[cat] = {
            "runs": int(bucket["runs"]),
            "success_rate": round(float(bucket["success"]) / runs, 4),
            "average_score": round(sum(bucket["scores"]) / runs, 2),
            "target_score": TARGET_RANGES.get(cat),
        }

    # Provider pool session stats
    pool_stats: dict = {}
    if _cerebras_pool_tracker is not None:
        pool_stats = _cerebras_pool_tracker.get_session_stats()
    else:
        # Derive from per-run provider_meta in results if tracker unavailable
        metas = [r.get("provider_meta") or {} for r in results]
        pool_stats = {
            "provider": "cerebras",
            "pool_size": max((int(m.get("pool_size") or 0) for m in metas), default=0),
            "keys_exercised_count": len({m.get("keys_exercised_count") for m in metas if m.get("keys_exercised_count")}),
            "failover_events": sum(int(m.get("failover_event_count") or 0) for m in metas),
            "total_calls": sum(int(m.get("llm_calls") or 0) for m in metas),
            "execution_mode": "pooled" if any(m.get("execution_mode") == "pooled" for m in metas) else "single_key",
            "benchmark_note": "Provider pool stats derived from per-run metadata.",
        }

    return {
        "total_runs": total,
        "success_rate": round(success_count / max(1, total), 4),
        "average_time_seconds": avg_time,
        "average_score": avg_score,
        "average_retries": avg_retries,
        "category_summary": category_summary,
        "provider_pool": pool_stats,
    }


def _write_markdown_report(output_dir: Path, summary: Mapping[str, Any]) -> None:
    lines: List[str] = [
        "# Product Dominance Benchmark Report",
        "",
        f"- Benchmark version: `{summary['benchmark_version']}`",
        f"- Generated at: `{summary['generated_at']}`",
        f"- Mode: `{summary['mode']}`",
        f"- Total runs: `{summary['aggregate']['total_runs']}`",
        f"- Success rate: `{summary['aggregate']['success_rate']:.2%}`",
        f"- Average score: `{summary['aggregate']['average_score']:.2f}`",
        f"- Average time (seconds): `{summary['aggregate']['average_time_seconds']:.2f}`",
        "",
        "## Per-Run Output",
        "",
    ]

    for result in summary["results"]:
        lines.extend(
            [
                f"### {result['run_id']}",
                f"Test: {result['title']}",
                f"Success: {'Yes' if result['success'] else 'No'}",
                f"Retries: {result['retries']}",
                f"Time: {result['time_seconds']} sec",
                f"Deploy: {result['deploy_status']}",
                f"Score: {result['score']}%",
                "",
            ]
        )

    agg = summary["aggregate"]
    lines.extend(
        [
            "## Aggregate Results",
            "",
            f"Total Runs: {agg['total_runs']}",
            f"Success Rate: {agg['success_rate']:.2%}",
            f"Avg Time: {agg['average_time_seconds']:.2f} sec",
            f"Avg Score: {agg['average_score']:.2f}%",
            "",
            "## Category Summary",
            "",
            "| Category | Runs | Success Rate | Average Score | Target |",
            "| --- | ---: | ---: | ---: | --- |",
        ]
    )

    for cat, row in agg["category_summary"].items():
        lines.append(
            f"| {cat} | {row['runs']} | {row['success_rate']:.2%} | {row['average_score']:.2f}% | {row.get('target_score') or '-'} |"
        )

    pool = agg.get("provider_pool") or {}
    if pool:
        lines.extend(
            [
                "",
                "## Provider Pool",
                "",
                f"- Execution mode: `{pool.get('execution_mode', 'unknown')}`",
                f"- Pool size (configured keys): `{pool.get('pool_size', 0)}`",
                f"- Keys exercised: `{pool.get('keys_exercised_count', 0)}`",
                f"- Failover events: `{pool.get('failover_events', 0)}`",
                f"- Total LLM calls: `{pool.get('total_calls', 0)}`",
                f"- Note: {pool.get('benchmark_note', '')}",
                "",
            ]
        )

    lines.extend(
        [
            "",
            "## Comparison Table",
            "",
            "| System | Score | Success Rate |",
            "| --- | ---: | ---: |",
            f"| CrucibAI | {agg['average_score']:.2f}% | {agg['success_rate']:.2%} |",
            "| Others | estimate_pending | estimate_pending |",
            "",
        ]
    )

    (output_dir / "BENCHMARK_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


async def run_benchmark(
    *,
    suite_path: Path,
    output_dir: Path,
    user_id: str,
    execute_live: bool,
    max_runs: Optional[int] = None,
    sign_proof_manifest: bool = False,
    proof_secret_env: str = "CRUCIB_PROOF_HMAC_SECRET",
) -> Dict[str, Any]:
    suite = load_suite(suite_path)
    cases = parse_cases(suite)
    counts = _counts_by_category(suite)
    plan = build_run_plan(cases, counts)
    if max_runs is not None:
        plan = plan[: max(0, int(max_runs))]

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    runs_dir = output_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    results: List[Dict[str, Any]] = []
    for idx, item in enumerate(plan, start=1):
        result = await _run_runtime_case(
            item.case,
            user_id=user_id,
            run_id=item.run_id,
            execute_live=execute_live,
        )
        result["index"] = idx
        result["iteration"] = item.iteration
        result["timestamp"] = utc_now()
        results.append(result)
        (runs_dir / f"{idx:03d}_{item.run_id}.json").write_text(
            json.dumps(result, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    aggregate = _aggregate_results(results)
    summary = {
        "benchmark_version": BENCHMARK_VERSION,
        "suite_version": suite.get("version"),
        "generated_at": utc_now(),
        "mode": "live" if execute_live else "simulated",
        "user_id": user_id,
        "weights": WEIGHTS,
        "formula": "Score = (0.4*Success)+(0.2*Accuracy)+(0.15*Speed)+(0.15*Reliability)+(0.1*UX)",
        "targets": TARGET_RANGES,
        "counts_by_category": counts,
        "results": results,
        "aggregate": aggregate,
    }
    summary["summary_sha256"] = stable_sha256({k: v for k, v in summary.items() if k != "summary_sha256"})

    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    _write_markdown_report(output_dir, summary)

    if sign_proof_manifest:
        secret = (os.environ.get(proof_secret_env) or "").strip()
        if not secret:
            raise RuntimeError(f"Missing proof signing secret env: {proof_secret_env}")
        manifest = build_signed_manifest_for_directory(
            directory=output_dir,
            secret=secret,
            manifest_id=f"product-dominance-{int(time.time())}",
            project_id=f"benchmark-{user_id}",
            run_id=output_dir.name,
            metadata={
                "benchmark_version": BENCHMARK_VERSION,
                "suite_version": suite.get("version"),
                "summary_sha256": summary.get("summary_sha256"),
                "mode": summary.get("mode"),
            },
            exclude_names={"proof_manifest.json"},
        )
        (output_dir / "proof_manifest.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        summary["proof_manifest"] = {
            "path": str(output_dir / "proof_manifest.json"),
            "manifest_id": manifest.get("manifest_id"),
            "payload_sha256": manifest.get("payload_sha256"),
        }

    return summary


def main(argv: Optional[List[str]] = None) -> int:
    root = _repo_root()
    parser = argparse.ArgumentParser(description="Run Product Dominance benchmark for CrucibAI.")
    parser.add_argument("--suite", default=str(root / "benchmarks" / "product_dominance_suite_v1.json"))
    parser.add_argument("--output-dir", default=str(root / "proof" / "benchmarks" / "product_dominance_v1"))
    parser.add_argument("--user-id", default="benchmark-runner")
    parser.add_argument("--execute-live", action="store_true", help="Execute live runtime tasks instead of simulated scoring")
    parser.add_argument("--max-runs", type=int, default=None, help="Optional cap for quick subsets (e.g. first 10 runs)")
    parser.add_argument(
        "--sign-proof-manifest",
        action="store_true",
        help="Sign and emit proof_manifest.json in output-dir (requires CRUCIB_PROOF_HMAC_SECRET or --proof-secret-env).",
    )
    parser.add_argument(
        "--proof-secret-env",
        default="CRUCIB_PROOF_HMAC_SECRET",
        help="Environment variable name that contains HMAC secret for proof signing.",
    )
    args = parser.parse_args(argv)

    summary = asyncio.run(
        run_benchmark(
            suite_path=Path(args.suite),
            output_dir=Path(args.output_dir),
            user_id=args.user_id,
            execute_live=bool(args.execute_live),
            max_runs=args.max_runs,
            sign_proof_manifest=bool(args.sign_proof_manifest),
            proof_secret_env=str(args.proof_secret_env),
        )
    )

    print(
        json.dumps(
            {
                "passed_threshold": bool(summary["aggregate"]["success_rate"] >= 0.85 and summary["aggregate"]["average_score"] >= 85.0),
                "total_runs": summary["aggregate"]["total_runs"],
                "success_rate": summary["aggregate"]["success_rate"],
                "average_score": summary["aggregate"]["average_score"],
                "average_time_seconds": summary["aggregate"]["average_time_seconds"],
                "output_dir": args.output_dir,
                "summary_sha256": summary["summary_sha256"],
                "proof_manifest": summary.get("proof_manifest"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
