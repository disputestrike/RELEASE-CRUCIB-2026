import json
import os
import tempfile

import pytest

from orchestration.auto_runner import _step_failure_context
from orchestration.executor import (
    _ensure_backend_elite_hardening,
    _main_py_sketch,
    _safe_write,
    _verification_failure_message,
    _verification_failure_payload,
    handle_delivery_manifest,
    handle_deploy,
    handle_frontend_generate,
)
from orchestration.generated_app_template import build_frontend_file_set
from orchestration.preview_gate import verify_preview_workspace
from orchestration.runtime_state import _coerce_json_text_updates
from orchestration.verification_api_smoke import verify_api_smoke_workspace
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


@pytest.mark.asyncio
async def test_frontend_empty_agent_output_falls_back_to_preview_scaffold(monkeypatch):
    from agents.frontend_agent import FrontendAgent
    import orchestration.plan_context as plan_context

    async def empty_execute(self, context):
        return {"files": {}, "structure": {}, "setup_instructions": []}

    async def fake_fetch_build_target(job_id):
        return "vite_react"

    monkeypatch.setattr(FrontendAgent, "execute", empty_execute)
    monkeypatch.setattr(plan_context, "fetch_build_target_for_job", fake_fetch_build_target)

    with tempfile.TemporaryDirectory() as d:
        result = await handle_frontend_generate(
            {"step_key": "frontend.scaffold"},
            {"id": "job-empty-frontend", "goal": "Build a tiny product dashboard"},
            d,
        )

        assert result["output_files"]
        assert "package.json" in result["output_files"]
        assert "src/App.jsx" in result["output_files"]
        assert os.path.isfile(os.path.join(d, "package.json"))
        assert os.path.isfile(os.path.join(d, "src", "main.jsx"))


@pytest.mark.asyncio
async def test_live_frontend_output_gets_preview_contract_hardening(monkeypatch):
    from agents.frontend_agent import FrontendAgent
    import orchestration.plan_context as plan_context

    async def thin_execute(self, context):
        return {
            "files": {
                "package.json": json.dumps(
                    {
                        "name": "thin-app",
                        "private": True,
                        "version": "0.1.0",
                        "type": "module",
                        "scripts": {"dev": "vite", "build": "vite build", "preview": "vite preview"},
                        "dependencies": {
                            "react": "^18.2.0",
                            "react-dom": "^18.2.0",
                            "react-router-dom": "^6.22.0",
                        },
                        "devDependencies": {"vite": "^5.4.11", "@vitejs/plugin-react": "^4.3.4"},
                    }
                ),
                "index.html": "<!doctype html><html><body><div id='root'></div><script type='module' src='/src/main.jsx'></script></body></html>",
                "src/App.jsx": "export default function App(){ return <main><h1>Thin app</h1></main>; }",
                "src/main.jsx": "import React from 'react'; import { createRoot } from 'react-dom/client'; import { MemoryRouter } from 'react-router-dom'; import App from './App.jsx'; createRoot(document.getElementById('root')).render(<MemoryRouter><App /></MemoryRouter>);",
            }
        }

    async def fake_fetch_build_target(job_id):
        return "vite_react"

    monkeypatch.setattr(FrontendAgent, "execute", thin_execute)
    monkeypatch.setattr(plan_context, "fetch_build_target_for_job", fake_fetch_build_target)
    monkeypatch.setenv("CRUCIBAI_SKIP_BROWSER_PREVIEW", "1")

    with tempfile.TemporaryDirectory() as d:
        result = await handle_frontend_generate(
            {"step_key": "frontend.scaffold"},
            {"id": "job-thin-frontend", "goal": "Build a tiny product dashboard"},
            d,
        )

        assert "src/components/ShellLayout.jsx" in result["output_files"]
        assert "src/context/AuthContext.jsx" in result["output_files"]
        preview = await verify_preview_workspace(d)
        assert preview["passed"] is True, preview.get("issues")


def test_preview_contract_merge_removes_invalid_react_router_types_dependency():
    from orchestration.executor import _merge_package_dependencies

    existing = json.dumps(
        {
            "name": "thin-app",
            "private": True,
            "dependencies": {"react": "^18.2.0"},
            "devDependencies": {"@types/react-router-dom": "6.2.1"},
        }
    )
    fallback = json.dumps({"dependencies": {"zustand": "^4.5.0"}, "devDependencies": {}})

    merged = json.loads(_merge_package_dependencies(existing, fallback))

    assert "@types/react-router-dom" not in merged["devDependencies"]
    assert merged["dependencies"]["zustand"] == "^4.5.0"


@pytest.mark.asyncio
async def test_fallback_scaffold_passes_preview_and_elite_gates(monkeypatch):
    monkeypatch.setenv("CRUCIBAI_SKIP_BROWSER_PREVIEW", "1")
    monkeypatch.setenv("CRUCIBAI_ELITE_BUILDER_GATE", "strict")

    job = {
        "id": "job-template-proof",
        "goal": "Build a tiny production proof app with auth, localStorage, routing, and deploy readiness",
        "build_target": "vite_react",
    }
    with tempfile.TemporaryDirectory() as d:
        for rel, content in build_frontend_file_set(job):
            _safe_write(d, rel, content)
        _safe_write(d, "backend/main.py", _main_py_sketch(multitenant=False))
        _ensure_backend_elite_hardening(d)
        await handle_delivery_manifest({"step_key": "implementation.delivery_manifest"}, job, d)

        preview = await verify_preview_workspace(d)
        elite = await verify_step(
            {"step_key": "verification.elite_builder", "job_goal": job["goal"]},
            d,
        )

        assert preview["passed"] is True, preview.get("issues")
        assert elite["passed"] is True, elite.get("issues")


@pytest.mark.asyncio
async def test_delivery_manifest_assembles_swarm_runtime_contract(monkeypatch):
    monkeypatch.setenv("CRUCIBAI_SKIP_BROWSER_PREVIEW", "1")

    job = {
        "id": "job-swarm-contract",
        "goal": "Build Helios Aegis Command with auth, API, tenant isolation, and analytics",
        "build_target": "full_system_generator",
    }
    with tempfile.TemporaryDirectory() as d:
        _safe_write(
            d,
            "src/App.jsx",
            """export default function App() { return <main>Helios Aegis Command</main>; }""",
        )
        _safe_write(
            d,
            "server.py",
            """from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "ok"}
""",
        )

        result = await handle_delivery_manifest({"step_key": "implementation.delivery_manifest"}, job, d)

        assert "package.json" in result["output_files"]
        assert "index.html" in result["output_files"]
        assert "vite.config.js" in result["output_files"]
        assert "backend/main.py" in result["output_files"]
        assert "deploy/healthcheck.sh" in result["output_files"]

        preview = await verify_preview_workspace(d)
        api_smoke = await verify_api_smoke_workspace(d)

        assert preview["passed"] is True, preview.get("issues")
        assert api_smoke["passed"] is True, api_smoke.get("issues")


def test_job_state_structured_lists_are_json_text():
    updates = {
        "blocked_steps": ["deploy.build", "deploy.publish"],
        "failed_step_keys": ["verification.preview"],
        "non_completed": [{"key": "deploy.publish", "status": "blocked"}],
        "failure_details": {"reason": "late_stage_failure"},
    }

    _coerce_json_text_updates(updates)

    assert json.loads(updates["blocked_steps"]) == ["deploy.build", "deploy.publish"]
    assert json.loads(updates["failed_step_keys"]) == ["verification.preview"]
    assert json.loads(updates["non_completed"])[0]["status"] == "blocked"
    assert json.loads(updates["failure_details"])["reason"] == "late_stage_failure"


def test_browser_preview_installs_dev_dependencies_for_vite():
    from pathlib import Path

    source = Path("backend/orchestration/browser_preview_verify.py").read_text(encoding="utf-8")

    assert '"--include=dev"' in source
    assert '"install", "--include=dev", "--no-fund", "--no-audit"' in source


def test_production_image_installs_playwright_chromium():
    from pathlib import Path

    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
    preflight = Path("backend/orchestration/preflight_report.py").read_text(encoding="utf-8")

    assert "python -m playwright install --with-deps chromium" in dockerfile
    assert '"id": "playwright_chromium"' in preflight


def test_published_app_url_uses_public_base(monkeypatch):
    from orchestration.publish_urls import published_app_url

    monkeypatch.setenv("CRUCIBAI_PUBLIC_BASE_URL", "https://crucibai.example.com/")

    assert published_app_url("job-123") == "https://crucibai.example.com/published/job-123/"


@pytest.mark.asyncio
async def test_deploy_publish_emits_public_generated_app_url_when_configured(monkeypatch):
    monkeypatch.setenv("CRUCIBAI_PUBLIC_BASE_URL", "https://crucibai.example.com")
    with tempfile.TemporaryDirectory() as d:
        result = await handle_deploy(
            {"step_key": "deploy.publish"},
            {"id": "job-public-url"},
            d,
        )

        assert result["deploy_url"] == "https://crucibai.example.com/published/job-public-url/"
        assert "deploy/PUBLISH.md" in result["output_files"]
        assert "https://crucibai.example.com/published/job-public-url/" in open(
            os.path.join(d, "deploy", "PUBLISH.md"),
            encoding="utf-8",
        ).read()
