import os
import tempfile

import pytest

from orchestration.auto_runner import _step_failure_context
from orchestration.executor import _verification_failure_message, _verification_failure_payload
from orchestration.verifier import verify_deploy_step, verify_step


@pytest.mark.asyncio
async def test_preview_verifier_preserves_failure_reason():
    with tempfile.TemporaryDirectory() as d:
        result = await verify_step({"step_key": "verification.preview"}, d)

    assert result["passed"] is False
    assert result["stage"] == "preview_boot"
    assert result["failure_reason"] in {
        "no_source_files",
        "missing_package_json",
        "invalid_package_json",
        "missing_dependencies",
        "no_entry_point",
        "browser_preview_failed",
    }
    assert result["issues"]


@pytest.mark.asyncio
async def test_elite_builder_verifier_preserves_failed_checks_and_recommendation(monkeypatch):
    monkeypatch.setenv("CRUCIBAI_ELITE_BUILDER_GATE", "strict")
    with tempfile.TemporaryDirectory() as d:
        result = await verify_step(
            {
                "step_key": "verification.elite_builder",
                "job_goal": "Build a production app with auth and database",
            },
            d,
        )

    assert result["passed"] is False
    assert result["stage"] == "elite_builder"
    assert result["failure_reason"] == "elite_checks_failed"
    assert result["failed_checks"]
    assert "recommendation" in result
    assert result["checks_total"] >= result["checks_passed"]


@pytest.mark.asyncio
async def test_deploy_build_reports_missing_artifact_reason():
    with tempfile.TemporaryDirectory() as d:
        result = await verify_deploy_step(
            {
                "step_key": "deploy.build",
                "output_files": ["Dockerfile", "deploy/PRODUCTION_SKETCH.md"],
                "deploy_url": None,
            },
            d,
        )

    assert result["passed"] is False
    assert result["stage"] == "deploy.build"
    assert result["failure_reason"] == "deploy_artifact_missing"
    assert any("Dockerfile" in issue for issue in result["issues"])


@pytest.mark.asyncio
async def test_deploy_publish_readiness_only_is_explicit_without_live_url(monkeypatch):
    monkeypatch.delenv("CRUCIBAI_REQUIRE_LIVE_DEPLOY_PUBLISH", raising=False)
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "deploy"), exist_ok=True)
        with open(os.path.join(d, "deploy", "PUBLISH.md"), "w", encoding="utf-8") as fh:
            fh.write("# Publish plan\n")
        result = await verify_deploy_step(
            {
                "step_key": "deploy.publish",
                "output_files": ["deploy/PUBLISH.md"],
                "deploy_url": None,
            },
            d,
        )

    assert result["passed"] is True
    assert result["stage"] == "deploy.publish"
    assert any(
        (proof.get("payload") or {}).get("publish_mode") == "readiness_only"
        for proof in result["proof"]
    )


@pytest.mark.asyncio
async def test_deploy_publish_live_requirement_fails_loudly(monkeypatch):
    monkeypatch.setenv("CRUCIBAI_REQUIRE_LIVE_DEPLOY_PUBLISH", "1")
    with tempfile.TemporaryDirectory() as d:
        result = await verify_deploy_step(
            {
                "step_key": "deploy.publish",
                "output_files": [],
                "deploy_url": None,
            },
            d,
        )

    assert result["passed"] is False
    assert result["failure_reason"] == "deploy_publish_url_missing"
    assert any("deploy_url" in issue for issue in result["issues"])


def test_executor_failure_payload_includes_precise_metadata():
    vr = {
        "failure_reason": "elite_checks_failed",
        "stage": "elite_builder",
        "score": 50,
        "issues": ["Missing proof/DELIVERY_CLASSIFICATION.md"],
        "failed_checks": ["delivery_classification"],
        "checks_passed": 8,
        "checks_total": 10,
        "recommendation": "Generate missing proof files before deploy.",
    }

    message = _verification_failure_message("verification.elite_builder", vr)
    payload = _verification_failure_payload("verification.elite_builder", vr, duration_ms=12)

    assert "elite_checks_failed" in message
    assert "delivery_classification" in message
    assert payload["failure_reason"] == "elite_checks_failed"
    assert payload["stage"] == "elite_builder"
    assert payload["failed_checks"] == ["delivery_classification"]
    assert payload["duration_ms"] == 12


def test_auto_runner_failure_context_preserves_verification_reason():
    ctx = _step_failure_context(
        {"step_key": "verification.preview"},
        {
            "success": False,
            "error": "verification.preview | browser_preview_failed",
            "verification": {
                "failure_reason": "browser_preview_failed",
                "stage": "preview_boot",
                "issues": ["Preview boot failed: port closed"],
                "score": 0,
            },
        },
    )

    assert ctx["failure_reason"] == "browser_preview_failed"
    assert ctx["stage"] == "preview_boot"
    assert ctx["issues"] == ["Preview boot failed: port closed"]
