from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def run_script(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=120,
    )


def test_1010_readiness_script_proves_all_build_profiles():
    result = run_script("scripts/verify_1010_readiness.py")
    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads(result.stdout)
    assert report["status"] == "passed"
    labels = {case["label"] for case in report["cases"]}
    assert {
        "saas_ui_pass",
        "website_pass",
        "mobile_pass",
        "automation_pass",
        "api_backend_pass",
        "thin_saas_rejected",
        "targeted_retry_plan",
    }.issubset(labels)


def test_paypal_sandbox_proof_hook_skips_without_credentials_and_can_require_live():
    env = os.environ.copy()
    for key in (
        "PAYPAL_MODE",
        "PAYPAL_CLIENT_ID",
        "PAYPAL_CLIENT_SECRET",
    ):
        env.pop(key, None)

    skipped = run_script("scripts/prove_paypal_sandbox.py", env=env)
    assert skipped.returncode == 0, skipped.stderr + skipped.stdout
    assert json.loads(skipped.stdout)["status"] == "skipped_missing_credentials"

    required = run_script("scripts/prove_paypal_sandbox.py", "--require-live", env=env)
    assert required.returncode == 2
    assert json.loads(required.stdout)["required_live"] is True


def test_deployment_proof_hook_has_artifact_mode_and_live_required_mode():
    env = os.environ.copy()
    env.pop("APP_URL", None)

    artifact = run_script("scripts/prove_deployment_readiness.py", env=env)
    assert artifact.returncode == 0, artifact.stderr + artifact.stdout
    payload = json.loads(artifact.stdout)
    assert payload["live_checked"] is False
    assert payload["status"] == "artifact_ready"

    required = run_script("scripts/prove_deployment_readiness.py", "--require-live", env=env)
    assert required.returncode == 2
    assert json.loads(required.stdout)["required_live"] is True
