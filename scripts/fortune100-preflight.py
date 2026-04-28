#!/usr/bin/env python3
"""Public readiness preflight for the production-facing CrucibAI surface."""
from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


ENDPOINTS = [
    {"id": "health", "path": "/api/health", "kind": "json"},
    {"id": "llm_health", "path": "/api/health/llm", "kind": "json"},
    {"id": "runtime_health", "path": "/api/orchestrator/runtime-health", "kind": "json"},
    {"id": "braintree_status", "path": "/api/payments/braintree/status", "kind": "json"},
    {"id": "benchmark_summary", "path": "/api/trust/benchmark-summary", "kind": "json"},
    {"id": "security_posture", "path": "/api/trust/security-posture", "kind": "json"},
    {"id": "full_systems_summary", "path": "/api/trust/full-systems-summary", "kind": "json"},
    {"id": "community_templates", "path": "/api/community/templates", "kind": "json"},
    {"id": "community_case_studies", "path": "/api/community/case-studies", "kind": "json"},
    {"id": "community_moderation", "path": "/api/community/moderation-policy", "kind": "json"},
    {"id": "benchmarks_page", "path": "/benchmarks", "kind": "html"},
    {"id": "security_page", "path": "/security", "kind": "html"},
    {"id": "status_page", "path": "/status", "kind": "html"},
    {"id": "templates_page", "path": "/templates", "kind": "html"},
]


def fetch(base_url: str, endpoint: dict[str, str], timeout: float) -> dict[str, Any]:
    url = base_url.rstrip("/") + endpoint["path"]
    started = time.perf_counter()
    record: dict[str, Any] = {
        "id": endpoint["id"],
        "url": url,
        "kind": endpoint["kind"],
        "status_code": None,
        "duration_ms": None,
        "ok": False,
        "error": None,
        "json": None,
        "body_prefix": None,
    }
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "CrucibAI-Fortune100-Preflight/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read(512_000)
            body = raw.decode("utf-8", errors="replace")
            record["status_code"] = response.status
            record["body_prefix"] = body[:500]
            content_type = response.headers.get("content-type", "")
            if "json" in content_type or endpoint["kind"] == "json":
                try:
                    record["json"] = json.loads(body)
                except json.JSONDecodeError as exc:
                    record["error"] = f"json_decode_failed: {exc}"
            record["ok"] = 200 <= response.status < 400 and not record["error"]
    except urllib.error.HTTPError as exc:
        record["status_code"] = exc.code
        record["error"] = f"http_error: {exc.code}"
    except Exception as exc:  # pragma: no cover - environment dependent
        record["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        record["duration_ms"] = round((time.perf_counter() - started) * 1000, 2)
    return record


def check_contract(records: list[dict[str, Any]], require_payments_configured: bool = False) -> list[dict[str, Any]]:
    by_id = {record["id"]: record for record in records}
    checks: list[dict[str, Any]] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    add(
        "all_required_endpoints_healthy",
        all(record.get("ok") for record in records),
        "All public readiness endpoints/pages must return 2xx/3xx and valid JSON where expected.",
    )

    braintree = by_id.get("braintree_status", {}).get("json") or {}
    add(
        "payment_provider_is_braintree",
        braintree.get("provider") == "braintree",
        f"provider={braintree.get('provider')} configured={braintree.get('configured')}",
    )
    if require_payments_configured:
        add(
            "braintree_credentials_configured",
            braintree.get("configured") is True,
            f"configured={braintree.get('configured')} required_config={braintree.get('required_config')}",
        )

    benchmark = by_id.get("benchmark_summary", {}).get("json") or {}
    prompt_count = benchmark.get("prompt_count") or 0
    pass_rate = benchmark.get("pass_rate") or 0
    add(
        "benchmark_50_prompt_90_percent",
        prompt_count >= 50 and pass_rate >= 0.9 and benchmark.get("status") == "ready",
        f"benchmark status={benchmark.get('status')} prompt_count={prompt_count} pass_rate={pass_rate}",
    )

    full_systems = by_id.get("full_systems_summary", {}).get("json") or {}
    add(
        "full_systems_zero_required_failures",
        full_systems.get("status") == "ready" and full_systems.get("required_failures") == 0,
        f"full_systems status={full_systems.get('status')} required_failures={full_systems.get('required_failures')}",
    )

    security = by_id.get("security_posture", {}).get("json") or {}
    terminal_policy = security.get("terminal_policy") or {}
    add(
        "terminal_public_host_shell_blocked",
        "disabled" in str(terminal_policy.get("public_default", "")).lower(),
        f"terminal public_default={terminal_policy.get('public_default')}",
    )

    sandbox_policy = security.get("sandbox_policy") or {}
    add(
        "generated_code_sandbox_policy_visible",
        "sandbox" in str(sandbox_policy.get("generated_code", "")).lower()
        and "disabled" in str(sandbox_policy.get("interactive_terminal", "")).lower(),
        f"sandbox generated_code={sandbox_policy.get('generated_code')} interactive_terminal={sandbox_policy.get('interactive_terminal')}",
    )

    community = by_id.get("community_templates", {}).get("json") or {}
    templates = community.get("templates") or []
    moderation = by_id.get("community_moderation", {}).get("json") or {}
    case_studies = by_id.get("community_case_studies", {}).get("json") or {}
    add(
        "community_templates_curated_and_remixable",
        len(templates) >= 4
        and all(item.get("moderation_status") == "approved" for item in templates if isinstance(item, dict))
        and all(item.get("remix_endpoint") for item in templates if isinstance(item, dict))
        and moderation.get("status") == "ready"
        and len(case_studies.get("case_studies") or []) >= 3,
        f"templates={len(templates)} moderation={moderation.get('status')} case_studies={len(case_studies.get('case_studies') or [])}",
    )

    durations = [record["duration_ms"] for record in records if isinstance(record.get("duration_ms"), (int, float))]
    p95 = max(durations) if len(durations) < 2 else statistics.quantiles(durations, n=20, method="inclusive")[18]
    add(
        "readiness_p95_under_5000ms",
        p95 < 5000,
        f"p95_ms={round(p95, 2)}",
    )
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description="Run production-facing public readiness checks.")
    parser.add_argument("--base-url", default="https://crucibai-production.up.railway.app")
    parser.add_argument("--proof-dir", default="proof/fortune100_preflight")
    parser.add_argument("--timeout-sec", type=float, default=30)
    parser.add_argument("--rounds", type=int, default=2)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument(
        "--require-payments-configured",
        action="store_true",
        help="Fail the readiness gate unless Braintree reports configured=true.",
    )
    args = parser.parse_args()

    proof_dir = ROOT / args.proof_dir
    proof_dir.mkdir(parents=True, exist_ok=True)

    tasks = []
    for _ in range(max(1, args.rounds)):
        tasks.extend(ENDPOINTS)

    records: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as executor:
        futures = [executor.submit(fetch, args.base_url, endpoint, args.timeout_sec) for endpoint in tasks]
        for future in as_completed(futures):
            records.append(future.result())

    records.sort(key=lambda item: (item["id"], item["duration_ms"] or 0))
    checks = check_contract(records, require_payments_configured=args.require_payments_configured)
    passed = all(check["passed"] for check in checks)
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": args.base_url,
        "passed": passed,
        "rounds": args.rounds,
        "concurrency": args.concurrency,
        "checks": checks,
        "request_count": len(records),
        "failed_requests": [record for record in records if not record.get("ok")],
    }

    (proof_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    with (proof_dir / "requests.jsonl").open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record) + "\n")

    rows = [
        "# Fortune 100 Public Readiness Preflight",
        "",
        f"Generated: {summary['generated_at']}",
        f"Base URL: {args.base_url}",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in checks:
        rows.append(f"| {check['name']} | {'PASS' if check['passed'] else 'FAIL'} | {check['detail']} |")
    rows.extend(["", f"Failed requests: {len(summary['failed_requests'])}", f"Overall: {'PASS' if passed else 'FAIL'}"])
    (proof_dir / "PASS_FAIL.md").write_text("\n".join(rows), encoding="utf-8")

    print(json.dumps(summary, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
