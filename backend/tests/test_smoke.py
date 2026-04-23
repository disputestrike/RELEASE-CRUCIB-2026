"""
Layer 9 – Post-deployment / smoke tests.
Verifies app is up and critical endpoints respond (in-process via app_client).
"""
import time
import pytest


async def test_smoke_health_returns_200(app_client):
    """App starts and /api/health returns 200."""
    r = await app_client.get("/api/health", timeout=10)
    assert r.status_code == 200
    assert r.json().get("status") == "healthy"


async def test_smoke_root_returns_200(app_client):
    """GET /api/ returns 200."""
    r = await app_client.get("/api/", timeout=10)
    assert r.status_code == 200


async def test_smoke_critical_endpoints_respond(app_client):
    """Critical read-only endpoints respond (no 500)."""
    endpoints = [
        ("/api/build/phases", "GET"),
        ("/api/tokens/bundles", "GET"),
        ("/api/agents", "GET"),
        ("/api/templates", "GET"),
        ("/api/patterns", "GET"),
        ("/api/examples", "GET"),  # Landing + ExamplesGallery
    ]
    for path, method in endpoints:
        if method == "GET":
            r = await app_client.get(path, timeout=10)
        else:
            r = await app_client.post(path, json={}, timeout=10)
        assert r.status_code != 500, f"{path} returned 500"


async def test_smoke_examples_returns_200(app_client):
    """GET /api/examples returns 200 and examples array (Landing + ExamplesGallery)."""
    r = await app_client.get("/api/examples", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert "examples" in data
    assert isinstance(data["examples"], list)


async def test_smoke_health_with_retries(app_client):
    """Health responds (retries not needed in-process)."""
    r = await app_client.get("/api/health", timeout=5)
    assert r.status_code == 200


async def test_smoke_health_response_time(app_client):
    """Health endpoint responds within acceptable time (e.g. 2s for CI variability)."""
    start = time.perf_counter()
    r = await app_client.get("/api/health", timeout=10)
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert r.status_code == 200
    assert elapsed_ms < 5000, f"/api/health took {elapsed_ms:.0f}ms (target < 5000ms)"


async def test_smoke_monitoring_track_returns_200(app_client):
    """POST /api/monitoring/events/track returns 200 and event_id (proof)."""
    r = await app_client.post(
        "/api/monitoring/events/track",
        json={"event_type": "feature_usage", "user_id": "test-user", "success": True},
        timeout=10,
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "ok"
    assert "event_id" in data


async def test_smoke_monitoring_events_list_returns_200(app_client):
    """GET /api/monitoring/events returns 200 and events list (proof)."""
    r = await app_client.get("/api/monitoring/events", params={"limit": 10}, timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert "events" in data
    assert isinstance(data["events"], list)


async def test_smoke_vibecoding_analyze_returns_200(app_client):
    """POST /api/vibecoding/analyze returns 200 and vibe (Phase 2)."""
    r = await app_client.post("/api/vibecoding/analyze", json={"text": "Build a React todo app"}, timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "success"
    assert "vibe" in data
    assert "confidence" in data


async def test_smoke_vibecoding_generate_returns_200(app_client):
    """POST /api/vibecoding/generate returns 200 and code (Phase 2)."""
    r = await app_client.post("/api/vibecoding/generate", json={"prompt": "hello world component"}, timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "success"
    assert "code" in data


async def test_smoke_ide_debug_start_returns_200(app_client):
    """POST /api/ide/debug/start returns 200 (Phase 2)."""
    r = await app_client.post("/api/ide/debug/start", params={"project_id": "test-project"}, timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert "session_id" in data
    assert data.get("project_id") == "test-project"


async def test_smoke_git_status_returns_200(app_client):
    """GET /api/git/status returns 200 (Phase 2)."""
    r = await app_client.get("/api/git/status", params={"repo_path": "/tmp/repo"}, timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert "branch" in data
    assert "modified" in data


async def test_smoke_terminal_create_returns_200(app_client):
    """POST /api/terminal/create returns 200 (Phase 2)."""
    r = await app_client.post("/api/terminal/create", params={"project_path": "/app"}, timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert "session_id" in data


async def test_smoke_terminal_execute_returns_result(app_client):
    """Create session, POST /api/terminal/{id}/execute with a command; get returncode/stdout (full impl)."""
    # Use "." so cwd exists (server's cwd is backend); on Windows use "echo hello", on Unix same
    create_r = await app_client.post("/api/terminal/create", params={"project_path": "."}, timeout=10)
    assert create_r.status_code == 200
    session_id = create_r.json().get("session_id")
    assert session_id
    exec_r = await app_client.post(
        f"/api/terminal/{session_id}/execute",
        json={"command": "echo hello", "timeout": 10},
        timeout=15,
    )
    assert exec_r.status_code == 200
    data = exec_r.json()
    assert "returncode" in data
    assert data.get("returncode") == 0, f"expected 0, got {data}"
    assert "stdout" in data
    assert "hello" in data.get("stdout", "")


async def test_smoke_git_branches_returns_200(app_client):
    """GET /api/git/branches returns 200 and branches list."""
    r = await app_client.get("/api/git/branches", params={"repo_path": "."}, timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert "branches" in data
    assert isinstance(data["branches"], list)


async def test_smoke_vibecoding_analyze_audio_returns_200(app_client):
    """POST /api/vibecoding/analyze-audio with transcript returns 200."""
    r = await app_client.post("/api/vibecoding/analyze-audio", json={"transcript": "Build a minimal React todo app"}, timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") in ("success", "error")
    if data.get("status") == "success":
        assert "vibe" in data


async def test_smoke_vibecoding_detect_frameworks_returns_200(app_client):
    """POST /api/vibecoding/detect-frameworks returns 200."""
    r = await app_client.post("/api/vibecoding/detect-frameworks", json={"text": "React and Node.js app with Express"}, timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "success"
    assert "frameworks" in data
    assert "languages" in data


async def test_smoke_ai_docs_generate_returns_200(app_client):
    """POST /api/ai/docs/generate returns 200 and readme."""
    r = await app_client.post("/api/ai/docs/generate", json={"project_name": "TestApp", "description": "A test app"}, timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "success"
    assert "readme" in data


async def test_smoke_deploy_validate_returns_200(app_client):
    """POST /api/deploy/validate returns 200."""
    r = await app_client.post("/api/deploy/validate", json={"platform": "vercel", "files": {"package.json": "{}"}}, timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert "valid" in data
    assert "platform" in data


async def test_smoke_cache_invalidate_returns_200(app_client):
    """POST /api/cache/invalidate returns 200."""
    r = await app_client.post("/api/cache/invalidate", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert data.get("status") == "ok"
    assert "deleted" in data
