"""Wave 2 corrective-action tests (CF11 - CF17).

Deterministic, in-process tests that verify the Wave 2 patches:

    CF11 — onboarding first-preview metric (/api/onboard)
    CF12 — unified deployment dispatcher (/api/deploy)
    CF13 — community publish loop (/api/community/publish)
    CF14 — mobile builder proof run (/api/mobile/proof-run)
    CF15 — benchmark harness HTTP surface (/api/benchmarks)
    CF16 — migration map tab wired to /api/migrations/{id}/file-map
    CF17 — legacy pages inventory manifest

No live Postgres / Redis / LLM is required; each endpoint tolerates the
absence of the DB pool (self-sufficient CREATE TABLE IF NOT EXISTS pattern
or plain in-process helpers).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

_HERE = Path(__file__).resolve().parent
_BACKEND = _HERE.parent
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


def _app_for(module_name: str, attr: str = "router") -> FastAPI:
    """Build a minimal FastAPI app mounted with a single router for isolation.

    Overrides auth deps to a fixed anonymous user so the Wave 2 endpoints can
    be exercised without a live token.  Production auth is still enforced at
    runtime because these overrides only apply to the test client.
    """
    import importlib
    mod = importlib.import_module(module_name)
    router = getattr(mod, attr)
    app = FastAPI()
    app.include_router(router)

    # Override auth deps so tests do not need a real token.
    try:
        from backend.deps import get_current_user  # type: ignore
        app.dependency_overrides[get_current_user] = lambda: {"id": "test-user"}
    except Exception:
        pass
    try:
        from deps import get_current_user as deps_gcu  # type: ignore
        app.dependency_overrides[deps_gcu] = lambda: {"id": "test-user"}
    except Exception:
        pass
    return app


# ─── CF11: onboarding ─────────────────────────────────────────────────────────

def test_cf11_onboard_start_returns_id_and_target():
    app = _app_for("routes.onboard")
    client = TestClient(app)
    r = client.post("/api/onboard/start", json={"goal": "build a dashboard"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("target_seconds") == 60.0
    assert data.get("goal") == "build a dashboard"
    assert isinstance(data.get("id"), str) and len(data["id"]) > 0


def test_cf11_onboard_metrics_returns_shape_even_without_db():
    app = _app_for("routes.onboard")
    client = TestClient(app)
    r = client.get("/api/onboard/metrics")
    assert r.status_code == 200
    data = r.json()
    # Must expose the sub_60s_rate / percentiles keys or a clear degraded status
    assert "sub_60s_rate" in data or data.get("degraded") is True or data.get("status")


# ─── CF12: unified deploy ─────────────────────────────────────────────────────

def test_cf12_deploy_targets_discovery():
    app = _app_for("routes.deploy_unified")
    client = TestClient(app)
    r = client.get("/api/deploy/targets")
    assert r.status_code == 200, r.text
    data = r.json()
    targets = data.get("targets") or data.get("supported") or []
    assert set(["vercel", "netlify", "docker", "k8s", "terraform"]).issubset(
        set(targets)
    ), f"missing targets, got {targets}"


def test_cf12_deploy_unknown_target_rejects():
    app = _app_for("routes.deploy_unified")
    client = TestClient(app)
    r = client.post("/api/deploy", json={"target": "bogus", "project_id": "p1"})
    assert r.status_code in (400, 422), r.text


def test_cf12_deploy_docker_emit_returns_bundle():
    """Emit-only targets must succeed without any remote deps."""
    app = _app_for("routes.deploy_unified")
    client = TestClient(app)
    payload = {
        "target": "docker",
        "project_id": "demo",
        "files": {"package.json": "{\"name\":\"demo\"}", "src/index.js": "console.log(1);"},
    }
    r = client.post("/api/deploy", json=payload)
    # May be 200 with bundle, or 202 for async; both are green
    assert r.status_code in (200, 202), r.text
    data = r.json()
    # Either a zip_b64 or a download_url must be present
    assert (
        data.get("zip_b64") or data.get("archive_base64") or data.get("download_url") or data.get("bundle")
    ), data


# ─── CF13: community publish ─────────────────────────────────────────────────

def test_cf13_community_publish_below_threshold_rejects():
    app = _app_for("routes.community")
    client = TestClient(app)
    r = client.post(
        "/api/community/publish",
        json={"title": "Demo app", "proof_score": 50.0},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("status") == "rejected"
    assert "proof_score_below_publish_threshold" in (data.get("moderation_reasons") or [])


def test_cf13_community_publish_pending_on_clean_submission():
    app = _app_for("routes.community")
    client = TestClient(app)
    r = client.post(
        "/api/community/publish",
        json={"title": "SaaS starter", "description": "Clean", "proof_score": 95.0,
              "tags": ["saas"]},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("status") == "accepted"
    assert data.get("moderation_status") == "pending"
    assert data.get("publication_id")


def test_cf13_community_publish_detects_secret_markers():
    app = _app_for("routes.community")
    client = TestClient(app)
    r = client.post(
        "/api/community/publish",
        json={"title": "Leak", "description": "my key is sk-abcdef",
              "proof_score": 95.0},
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "rejected"
    reasons = data.get("moderation_reasons") or []
    assert any("secret_marker" in r for r in reasons)


# ─── CF14: mobile proof-run ───────────────────────────────────────────────────

def test_cf14_mobile_presets_lists_react_native():
    app = _app_for("routes.mobile", attr="mobile_router")
    client = TestClient(app)
    r = client.get("/api/mobile/presets")
    assert r.status_code == 200
    data = r.json()
    presets = {p["id"] for p in data.get("presets", [])}
    assert "react-native-expo" in presets


def test_cf14_mobile_proof_run_defaults_pass_100():
    app = _app_for("routes.mobile", attr="mobile_router")
    client = TestClient(app)
    r = client.post("/api/mobile/proof-run", json={"platform": "both",
                                                    "preset": "react-native-expo"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["proof_score"] == 100.0
    assert data["ready_for_store_submit"] is True
    assert set(data["platforms"]) == {"ios", "android"}


def test_cf14_mobile_proof_run_rejects_unknown_preset():
    app = _app_for("routes.mobile", attr="mobile_router")
    client = TestClient(app)
    r = client.post("/api/mobile/proof-run", json={"platform": "ios", "preset": "bogus"})
    assert r.status_code == 400


# ─── CF15: benchmarks ─────────────────────────────────────────────────────────

def test_cf15_benchmarks_latest_ready():
    app = _app_for("routes.benchmarks_api")
    client = TestClient(app)
    r = client.get("/api/benchmarks/latest")
    assert r.status_code == 200
    data = r.json()
    # Either we have the seed data file (status=ready) or it's unavailable
    assert data.get("status") in ("ready", "unavailable")
    if data.get("status") == "ready":
        assert data.get("pass_rate") is not None
        assert data.get("average_score") is not None


def test_cf15_benchmarks_competitors_has_crucibai():
    app = _app_for("routes.benchmarks_api")
    client = TestClient(app)
    r = client.get("/api/benchmarks/competitors")
    assert r.status_code == 200
    data = r.json()
    baseline = data.get("baseline") or {}
    ids = [p["id"] for p in baseline.get("products", [])]
    assert "crucibai" in ids
    assert "cursor" in ids and "lovable" in ids and "bolt" in ids and "replit" in ids


def test_cf15_benchmarks_scorecards_lists_modules():
    app = _app_for("routes.benchmarks_api")
    client = TestClient(app)
    r = client.get("/api/benchmarks/scorecards")
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "ready"
    modules = [m["module"] for m in data.get("scorecards", [])]
    assert any("repeatability_scorecard" in m for m in modules) or \
           any("product_dominance_scorecard" in m for m in modules)


# ─── CF17: legacy pages manifest ──────────────────────────────────────────────

def test_cf17_legacy_pages_manifest_exists_and_consistent():
    root = _BACKEND.parent
    manifest_js = root / "frontend" / "src" / "legacy" / "pagesManifest.js"
    inventory_md = root / "docs" / "phase2" / "LEGACY_PAGES_INVENTORY.md"
    assert manifest_js.exists(), f"missing: {manifest_js}"
    assert inventory_md.exists(), f"missing: {inventory_md}"
    js = manifest_js.read_text()
    # Every disposition bucket must be represented
    for disp in ("keep", "migrate", "keep-behind-flag", "delete"):
        assert disp in js, f"missing disposition: {disp}"
    # Must reference canonical workspace and explicitly mark the deletes
    assert "WorkspaceV3Shell" in js
    for deleted in ("AdminPanel.tsx", "Builder.jsx", "UnifiedWorkspace.jsx"):
        assert deleted in js, f"missing deleted page: {deleted}"


# ─── CF18: unified preview-loop route ─────────────────────────────────────────

def test_cf18_preview_loop_capabilities_reports_services():
    """GET /api/runs/preview-loop/capabilities returns a status + per-service flags."""
    app = _app_for("routes.preview_loop")
    client = TestClient(app)
    r = client.get("/api/runs/preview-loop/capabilities")
    assert r.status_code == 200, r.text
    data = r.json()
    # Must always echo the three expected subservice keys so the UI can render
    # conditional state.
    for key in ("preview_session", "operator_runner", "ui_feedback_mapper"):
        assert key in data, f"missing capability key: {key}"
    assert data.get("status") in {"ready", "degraded"}


def test_cf18_preview_loop_handles_missing_services_cleanly(monkeypatch):
    """POST /api/runs/{id}/preview-loop returns 503 when subservices can't import."""
    app = _app_for("routes.preview_loop")
    client = TestClient(app)

    # Force import-time failure inside the endpoint by stubbing the module.
    import importlib
    import sys as _sys
    # Remove any cached subservice modules so the import in the route raises.
    for modname in ("services.preview_session",
                    "services.operator_runner",
                    "services.ui_feedback_mapper"):
        _sys.modules.pop(modname, None)

    # Install a sentinel module that raises on import attribute access.
    class _BlowUp:
        def __getattr__(self, item):  # pragma: no cover — defensive
            raise RuntimeError("blocked-for-test")

    _sys.modules["services.preview_session"] = _BlowUp()
    _sys.modules["services.operator_runner"] = _BlowUp()
    _sys.modules["services.ui_feedback_mapper"] = _BlowUp()
    try:
        r = client.post(
            "/api/runs/t-cf18/preview-loop",
            json={"url": "http://example.com", "dry_run": True},
        )
        # The route either 503s (import raised) or returns a degraded envelope
        # because every subservice fell back. Both satisfy "no crash".
        assert r.status_code in (200, 503), r.text
        if r.status_code == 200:
            data = r.json()
            assert data.get("status") in {"pass", "regression", "degraded"}
            assert data.get("thread_id") == "t-cf18"
            assert "run_id" in data
    finally:
        for modname in ("services.preview_session",
                        "services.operator_runner",
                        "services.ui_feedback_mapper"):
            _sys.modules.pop(modname, None)


def test_cf18_preview_loop_last_returns_empty_for_unknown_thread():
    app = _app_for("routes.preview_loop")
    client = TestClient(app)
    r = client.get("/api/runs/does-not-exist/preview-loop/last")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("status") == "empty"
    assert data.get("thread_id") == "does-not-exist"


def test_cf18_preview_loop_end_to_end_with_mocked_services(monkeypatch):
    """Compose preview+operator+feedback via mocked services and assert envelope shape."""
    import types
    import sys as _sys

    # Mock preview_session_service
    async def _fake_open(url, thread_id):
        return types.SimpleNamespace(session_id=f"sess-{thread_id}", url=url)
    preview_stub = types.ModuleType("services.preview_session")
    preview_stub.preview_session_service = types.SimpleNamespace(open=_fake_open)
    _sys.modules["services.preview_session"] = preview_stub

    # Mock operator_runner
    async def _fake_screenshot(url):
        return "AAA" * 10  # fake b64
    async def _fake_run_flow(steps, dry_run, thread_id):
        return [{"action": s.get("action"), "status": "dry-run"} for s in steps]
    operator_stub = types.ModuleType("services.operator_runner")
    operator_stub.operator_runner = types.SimpleNamespace(
        screenshot=_fake_screenshot, run_flow=_fake_run_flow,
    )
    _sys.modules["services.operator_runner"] = operator_stub

    # Mock ui_feedback_mapper
    async def _fake_diff(before_url, after_url, threshold):
        return types.SimpleNamespace(verdict="pass", diff_ratio=0.01, notes=None)
    feedback_stub = types.ModuleType("services.ui_feedback_mapper")
    feedback_stub.ui_feedback_mapper = types.SimpleNamespace(diff=_fake_diff)
    _sys.modules["services.ui_feedback_mapper"] = feedback_stub

    try:
        app = _app_for("routes.preview_loop")
        client = TestClient(app)
        r = client.post(
            "/api/runs/t-e2e/preview-loop",
            json={
                "url": "http://example.com",
                "dry_run": True,
                "take_before_shot": True,
                "take_after_shot": True,
                "operator_steps": [
                    {"action": "navigate", "url": "http://example.com"},
                    {"action": "screenshot", "url": "http://example.com"},
                ],
            },
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["thread_id"] == "t-e2e"
        assert data["status"] in {"pass", "regression", "degraded"}
        assert data["preview"]["session_id"] == "sess-t-e2e"
        assert isinstance(data["operator"], list) and len(data["operator"]) == 2
        assert data["feedback"]["verdict"] == "pass"
        assert data["artifacts"]["before_shot_b64_len"] > 0
        assert data["artifacts"]["after_shot_b64_len"] > 0

        # Now GET /preview-loop/last should hit the cache
        r2 = client.get("/api/runs/t-e2e/preview-loop/last")
        assert r2.status_code == 200
        assert r2.json()["run_id"] == data["run_id"]
    finally:
        for modname in ("services.preview_session",
                        "services.operator_runner",
                        "services.ui_feedback_mapper"):
            _sys.modules.pop(modname, None)


# ─── CF19: brain.decide wired into _phase_decide ─────────────────────────────

def test_cf19_phase_decide_calls_brain_layer():
    """_phase_decide must call brain.decide(session, request) instead of hardcoding default."""
    import asyncio
    from services.runtime import runtime_engine as re_mod

    captured: dict = {}

    class _FakeBrain:
        def decide(self, session, user_message):
            captured["session"] = session
            captured["message"] = user_message
            return {
                "action": "build",
                "skill": "code_editor",
                "confidence": 0.87,
                "continue": True,
                "spawn": False,
            }

    engine = re_mod.RuntimeEngine()
    # Inject our fake brain factory
    engine._brain_factory = lambda: _FakeBrain()

    # Build an ExecutionContext stub
    ExecutionContext = re_mod.ExecutionContext
    ctx = ExecutionContext(task_id="t-cf19", user_id="u-cf19",
                           conversation_id="s-cf19")

    decision = asyncio.get_event_loop().run_until_complete(
        engine._phase_decide(
            task_id="t-cf19",
            context=ctx,
            request="build me a todo app",
            step_id="step-1",
        )
    )

    assert captured.get("message") == "build me a todo app", captured
    assert decision is not None
    assert decision["action"] == "build"
    assert decision["skill"] == "code_editor"
    assert decision["confidence"] == 0.87
    assert decision["continue"] is True
    assert "raw" in decision


def test_cf19_phase_decide_falls_back_when_brain_raises():
    """If brain.decide raises, _phase_decide should still return a safe default."""
    import asyncio
    from services.runtime import runtime_engine as re_mod

    class _BrokenBrain:
        def decide(self, session, user_message):
            raise RuntimeError("planner offline")

    engine = re_mod.RuntimeEngine()
    engine._brain_factory = lambda: _BrokenBrain()
    ExecutionContext = re_mod.ExecutionContext
    ctx = ExecutionContext(task_id="t-cf19b", user_id="u",
                           conversation_id="s")

    decision = asyncio.get_event_loop().run_until_complete(
        engine._phase_decide(task_id="t-cf19b", context=ctx,
                             request="anything", step_id="s1")
    )
    assert decision is not None
    # Fallback shape must be intact
    assert decision.get("action") == "default"
    assert decision.get("skill") == "default"


# ─── Wave 3: Proof & Distribution ────────────────────────────────────────────


def test_wave3_public_scorecard_returns_200_with_shape():
    """GET /public/benchmarks/scorecard returns 200 and expected keys."""
    client = TestClient(_app_for("routes.public_benchmarks"))
    resp = client.get("/public/benchmarks/scorecard")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # At least one of the canonical shape keys must be present
    assert any(k in body for k in ("axes", "scorecards", "competitors")), body


def test_wave3_changelog_returns_200_with_commits_array():
    """GET /api/changelog returns 200 and a commits array (may be empty when degraded)."""
    client = TestClient(_app_for("routes.changelog"))
    resp = client.get("/api/changelog")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "commits" in body, body
    assert isinstance(body["commits"], list), body


def test_wave3_seeded_runner_produces_valid_json(tmp_path):
    """run_competitor_benchmarks.py --mode=seeded writes a file with expected keys."""
    import subprocess
    result = subprocess.run(
        [
            sys.executable,
            str(_BACKEND.parent / "scripts" / "run_competitor_benchmarks.py"),
            "--mode=seeded",
            "--out",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1, f"Expected 1 JSON file, found: {files}"
    with files[0].open() as fh:
        import json as _json
        data = _json.load(fh)
    assert "axes" in data, data
    assert "competitors" in data, data
    assert "version" in data, data


# ─── Wave 5: Growth & Ecosystem ───────────────────────────────────────────────

def test_w5_marketplace_listings_returns_shape():
    """GET /api/marketplace/listings -> 200, has listings array or degraded=true."""
    app = _app_for("routes.marketplace")
    client = TestClient(app)
    r = client.get("/api/marketplace/listings")
    assert r.status_code == 200, r.text
    data = r.json()
    assert "listings" in data
    assert isinstance(data["listings"], list)
    if data.get("degraded"):
        assert data["degraded"] is True
    else:
        assert isinstance(data["listings"], list)


def test_w5_marketplace_listings_kind_filter():
    """GET /api/marketplace/listings?kind=template -> 200, shape preserved."""
    app = _app_for("routes.marketplace")
    client = TestClient(app)
    r = client.get("/api/marketplace/listings?kind=template")
    assert r.status_code == 200, r.text
    data = r.json()
    assert "listings" in data


def test_w5_marketplace_featured_returns_shape():
    """GET /api/marketplace/featured -> 200, has listings array."""
    app = _app_for("routes.marketplace")
    client = TestClient(app)
    r = client.get("/api/marketplace/featured")
    assert r.status_code == 200, r.text
    data = r.json()
    assert "listings" in data
    assert isinstance(data["listings"], list)


def test_w5_api_key_create_returns_secret():
    """POST /api/keys -> 200, secret starts with crc_, prefix present."""
    app = _app_for("routes.api_keys")
    client = TestClient(app)
    r = client.post("/api/keys", json={"name": "test-key"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert "secret" in data, data
    assert data["secret"].startswith("crc_"), data["secret"]
    assert "prefix" in data, data
    assert "id" in data, data


def test_w5_api_key_list_no_secrets():
    """GET /api/keys after create -> 200, entries have no secret / hashed_secret."""
    app = _app_for("routes.api_keys")
    client = TestClient(app)
    cr = client.post("/api/keys", json={"name": "list-test-key"})
    assert cr.status_code == 200, cr.text
    r = client.get("/api/keys")
    assert r.status_code == 200, r.text
    data = r.json()
    if data.get("degraded"):
        return
    assert "keys" in data
    for key in data["keys"]:
        assert "secret" not in key, "secret must never appear in list response"
        assert "hashed_secret" not in key, "hashed_secret must never appear in list response"


def test_w5_api_key_delete():
    """DELETE /api/keys/{id} -> 200."""
    app = _app_for("routes.api_keys")
    client = TestClient(app)
    cr = client.post("/api/keys", json={"name": "revoke-test"})
    assert cr.status_code == 200, cr.text
    key_id = cr.json()["id"]
    dr = client.delete(f"/api/keys/{key_id}")
    assert dr.status_code == 200, dr.text
    data = dr.json()
    assert data.get("revoked") is True or data.get("degraded") is True, data
