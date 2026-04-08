"""Generate deterministic proof for the late-stage pipeline crash fix."""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
PROOF_DIR = REPO_ROOT / "proof" / "pipeline_crash_fix"

sys.path.insert(0, str(BACKEND_DIR))


def _pass_fail_row(name: str, passed: bool, evidence: str) -> Dict[str, Any]:
    return {"item": name, "status": "PASS" if passed else "FAIL", "evidence": evidence}


async def _run_checks() -> Dict[str, Any]:
    from orchestration.verifier import verify_deploy_step, verify_step

    checks: List[Dict[str, Any]] = []

    with tempfile.TemporaryDirectory() as d:
        preview = await verify_step({"step_key": "verification.preview"}, d)
    checks.append(
        _pass_fail_row(
            "preview boot",
            bool(preview.get("failure_reason")),
            f"verification.preview failure_reason={preview.get('failure_reason')} stage={preview.get('stage')}",
        )
    )

    old_gate = os.environ.get("CRUCIBAI_ELITE_BUILDER_GATE")
    os.environ["CRUCIBAI_ELITE_BUILDER_GATE"] = "strict"
    try:
        with tempfile.TemporaryDirectory() as d:
            elite = await verify_step(
                {"step_key": "verification.elite_builder", "job_goal": "production auth app"},
                d,
            )
    finally:
        if old_gate is None:
            os.environ.pop("CRUCIBAI_ELITE_BUILDER_GATE", None)
        else:
            os.environ["CRUCIBAI_ELITE_BUILDER_GATE"] = old_gate
    checks.append(
        _pass_fail_row(
            "elite/proof verification",
            elite.get("failure_reason") == "elite_checks_failed" and bool(elite.get("failed_checks")),
            f"failure_reason={elite.get('failure_reason')} failed_checks={elite.get('failed_checks')}",
        )
    )

    with tempfile.TemporaryDirectory() as d:
        deploy_build = await verify_deploy_step(
            {
                "step_key": "deploy.build",
                "output_files": ["Dockerfile", "deploy/PRODUCTION_SKETCH.md"],
                "deploy_url": None,
            },
            d,
        )
    checks.append(
        _pass_fail_row(
            "deploy build",
            deploy_build.get("failure_reason") == "deploy_artifact_missing",
            f"failure_reason={deploy_build.get('failure_reason')} issues={deploy_build.get('issues')}",
        )
    )

    with tempfile.TemporaryDirectory() as d:
        publish_dir = Path(d) / "deploy"
        publish_dir.mkdir(parents=True, exist_ok=True)
        (publish_dir / "PUBLISH.md").write_text("# Publish plan\n", encoding="utf-8")
        deploy_publish = await verify_deploy_step(
            {
                "step_key": "deploy.publish",
                "output_files": ["deploy/PUBLISH.md"],
                "deploy_url": None,
            },
            d,
        )
    publish_readiness = any(
        (proof.get("payload") or {}).get("publish_mode") == "readiness_only"
        for proof in deploy_publish.get("proof") or []
    )
    checks.append(
        _pass_fail_row(
            "deploy publish",
            deploy_publish.get("passed") is True and publish_readiness,
            f"passed={deploy_publish.get('passed')} readiness_only={publish_readiness}",
        )
    )

    server_text = (REPO_ROOT / "backend" / "server.py").read_text(encoding="utf-8")
    executor_text = (REPO_ROOT / "backend" / "orchestration" / "executor.py").read_text(encoding="utf-8")
    auto_runner_text = (REPO_ROOT / "backend" / "orchestration" / "auto_runner.py").read_text(encoding="utf-8")
    migration_text = (REPO_ROOT / "backend" / "migrations" / "006_complete_schema.sql").read_text(encoding="utf-8")
    runner_stable = all(
        [
            "background_runner_exception" in server_text,
            "background_crash" not in server_text,
            "verification_attempt_failed" in executor_text,
            "step_retry_exhausted" in auto_runner_text,
            "failure_reason TEXT" in migration_text,
            "failure_details TEXT" in migration_text,
        ]
    )
    checks.append(
        _pass_fail_row(
            "background runner stability",
            runner_stable,
            "server wrapper uses background_runner_exception, retry/verification events exist, jobs schema has failure columns",
        )
    )

    return {
        "checks": checks,
        "preview": preview,
        "elite": elite,
        "deploy_build": deploy_build,
        "deploy_publish": deploy_publish,
    }


def _write_markdown(bundle: Dict[str, Any]) -> None:
    rows = bundle["checks"]
    pass_fail = [
        "# Pipeline Crash Fix PASS/FAIL",
        "",
        "| Requirement | Status | Evidence |",
        "| --- | --- | --- |",
    ]
    for row in rows:
        evidence = str(row["evidence"]).replace("|", "\\|")
        pass_fail.append(f"| {row['item']} | {row['status']} | {evidence} |")
    (PROOF_DIR / "PASS_FAIL.md").write_text("\n".join(pass_fail) + "\n", encoding="utf-8")

    root_cause = """# Pipeline Crash Root Cause

1. `verification.preview` already produced precise causes in `preview_gate.py`, but `verifier.verify_step` dropped `failure_reason` before executor events. The fix preserves `failure_reason` with stage `preview_boot`.
2. `verification.elite_builder` already produced `failed_checks`, `failure_reason`, and `recommendation`, but `verifier.verify_step` dropped them. The fix preserves those fields.
3. `deploy.build` and `deploy.publish` were too ambiguous: missing artifacts and no live publish URL did not produce a deploy-specific failure reason. The fix makes artifact, smoke, strict live publish, and readiness-only publish outcomes explicit.
4. The background wrapper could still record generic `background_crash`; it now records `background_runner_exception` with exception type and traceback tail. A hidden schema defect also existed: job failure metadata columns were referenced in code but missing from the jobs table. The fix adds `failure_reason` and `failure_details`.
5. Retry exhaustion now emits `step_retry_exhausted` and retry events carry stage/failure metadata, so late-stage retries are explainable in the stream and event log.
"""
    (PROOF_DIR / "root_cause.md").write_text(root_cause, encoding="utf-8")


def main() -> int:
    PROOF_DIR.mkdir(parents=True, exist_ok=True)
    bundle = asyncio.run(_run_checks())
    (PROOF_DIR / "proof_bundle.json").write_text(
        json.dumps(bundle, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    _write_markdown(bundle)
    print(json.dumps({"passed": all(row["status"] == "PASS" for row in bundle["checks"]), "proof_dir": str(PROOF_DIR)}, indent=2))
    return 0 if all(row["status"] == "PASS" for row in bundle["checks"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
