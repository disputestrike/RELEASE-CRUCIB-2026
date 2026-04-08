"""
Layer 9 – Post-deployment / smoke tests.
Verifies app is up and critical endpoints respond (in-process via app_client).
"""
import time
import uuid
import pytest


async def _create_smoke_project(app_client, auth_headers):
    """Create a user-owned project row and workspace for path-scoped smoke tests."""
    import server

    r = await app_client.post(
        "/api/projects",
        json={
            "name": f"Smoke Project {uuid.uuid4().hex[:8]}",
            "description": "Smoke test workspace",
            "project_type": "fullstack",
            "requirements": {"prompt": "smoke"},
        },
        headers=auth_headers,
        timeout=15,
    )
    assert r.status_code in (200, 201), f"Project create failed: {r.status_code} {r.text}"
    data = r.json()
    project = data.get("project") or data
    project_id = project["id"]
    root = server._project_workspace_path(project_id)
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text("# Smoke Project\n", encoding="utf-8")
    return project_id


async def _create_smoke_task(auth_headers, files=None):
    """Create a user-owned task row for state-scoped smoke tests."""
    import server

    token = auth_headers["Authorization"].split(" ", 1)[1]
    payload = server.jwt.decode(token, server.JWT_SECRET, algorithms=[server.JWT_ALGORITHM])
    task_id = str(uuid.uuid4())
    await server.db.tasks.insert_one({
        "id": task_id,
        "user_id": payload["user_id"],
        "name": "Smoke Task",
        "status": "complete",
        "files": files or {"schema.sql": "CREATE TABLE IF NOT EXISTS smoke_items (id text);"},
        "created_at": "2026-01-01T00:00:00+00:00",
        "updated_at": "2026-01-01T00:00:00+00:00",
    })
    return task_id


def _user_id_from_auth_headers(auth_headers):
    """Decode the test JWT and return the owning user id."""
    import server

    token = auth_headers["Authorization"].split(" ", 1)[1]
    payload = server.jwt.decode(token, server.JWT_SECRET, algorithms=[server.JWT_ALGORITHM])
    return payload["user_id"]


async def _create_failed_smoke_job_step(auth_headers):
    """Create a user-owned failed job step for retry ownership smoke tests."""
    from db_pg import get_pg_pool
    from orchestration import runtime_state

    pool = await get_pg_pool()
    runtime_state.set_pool(pool)
    user_id = _user_id_from_auth_headers(auth_headers)
    job = await runtime_state.create_job(
        project_id=f"smoke-project-{uuid.uuid4().hex[:8]}",
        mode="guided",
        goal="Smoke retry",
        user_id=user_id,
    )
    step = await runtime_state.create_step(
        job_id=job["id"],
        step_key="smoke-step",
        agent_name="Smoke Agent",
        phase="test",
    )
    await runtime_state.update_step_state(step["id"], "failed", {"error_message": "smoke"})
    step = await runtime_state.get_step(step["id"])
    return job["id"], step["id"]


async def _create_smoke_auto_job(auth_headers):
    """Create a user-owned Auto-Runner job for execution-boundary smoke tests."""
    from db_pg import get_pg_pool
    from orchestration import runtime_state

    pool = await get_pg_pool()
    runtime_state.set_pool(pool)
    user_id = _user_id_from_auth_headers(auth_headers)
    project_id = f"smoke-project-{uuid.uuid4().hex[:8]}"
    job = await runtime_state.create_job(
        project_id=project_id,
        mode="guided",
        goal="Build a smoke app",
        user_id=user_id,
    )
    return job["id"], project_id


async def _register_smoke_headers(app_client):
    """Register another test user and return auth headers."""
    email = f"smoke-{uuid.uuid4().hex[:12]}@example.com"
    r = await app_client.post(
        "/api/auth/register",
        json={"email": email, "password": "TestPass123!", "name": "Smoke User"},
        timeout=10,
    )
    assert r.status_code in (200, 201), f"Register failed: {r.status_code} {r.text}"
    data = r.json()
    user_id = data.get("user", {}).get("id")
    if user_id:
        import server

        await server.db.users.update_one(
            {"id": user_id},
            {"$set": {"credit_balance": 10000, "plan": "pro"}},
        )
    return {"Authorization": f"Bearer {data['token']}"}


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
        ("/api/trust/benchmark-summary", "GET"),
        ("/api/trust/security-posture", "GET"),
        ("/api/trust/full-systems-summary", "GET"),
        ("/api/community/templates", "GET"),
        ("/api/community/case-studies", "GET"),
        ("/api/community/moderation-policy", "GET"),
    ]
    for path, method in endpoints:
        if method == "GET":
            r = await app_client.get(path, timeout=10)
        else:
            r = await app_client.post(path, json={}, timeout=10)
        assert r.status_code != 500, f"{path} returned 500"


async def test_smoke_published_generated_app_url_serves_dist(app_client, auth_headers):
    """Completed generated jobs can serve a public in-platform generated-app URL."""
    import server
    from db_pg import get_pg_pool
    from orchestration import runtime_state

    pool = await get_pg_pool()
    runtime_state.set_pool(pool)
    user_id = _user_id_from_auth_headers(auth_headers)
    project_id = f"published-smoke-{uuid.uuid4().hex[:8]}"
    job = await runtime_state.create_job(
        project_id=project_id,
        mode="guided",
        goal="Published app smoke",
        user_id=user_id,
    )
    root = server._project_workspace_path(project_id)
    (root / "dist").mkdir(parents=True, exist_ok=True)
    (root / "dist" / "index.html").write_text("<!doctype html><h1>Published smoke</h1>", encoding="utf-8")
    await runtime_state.update_job_state(job["id"], "completed", {"current_phase": "completed"})

    r = await app_client.get(f"/published/{job['id']}/", timeout=10)

    assert r.status_code == 200
    assert "Published smoke" in r.text


async def test_smoke_published_generated_app_rewrites_asset_paths_and_serves_job_assets(app_client, auth_headers):
    """Published app HTML must point at job-scoped assets, not CrucibAI's root frontend bundle."""
    import server
    from db_pg import get_pg_pool
    from orchestration import runtime_state

    pool = await get_pg_pool()
    runtime_state.set_pool(pool)
    user_id = _user_id_from_auth_headers(auth_headers)
    project_id = f"published-assets-{uuid.uuid4().hex[:8]}"
    job = await runtime_state.create_job(
        project_id=project_id,
        mode="guided",
        goal="Published asset rewrite smoke",
        user_id=user_id,
    )
    root = server._project_workspace_path(project_id)
    (root / "dist" / "assets").mkdir(parents=True, exist_ok=True)
    (root / "dist" / "index.html").write_text(
        """<!doctype html><html><head><script type="module" src="/assets/app.js"></script></head><body><div id="root"></div></body></html>""",
        encoding="utf-8",
    )
    (root / "dist" / "assets" / "app.js").write_text("console.log('published-job-asset');", encoding="utf-8")
    await runtime_state.update_job_state(job["id"], "completed", {"current_phase": "completed"})

    html = await app_client.get(f"/published/{job['id']}/", timeout=10)
    asset = await app_client.get(f"/published/{job['id']}/assets/app.js", timeout=10)

    assert html.status_code == 200
    assert f'/published/{job["id"]}/assets/app.js' in html.text
    assert asset.status_code == 200
    assert "published-job-asset" in asset.text


async def test_smoke_published_missing_asset_returns_404(app_client, auth_headers):
    """Missing asset files should not silently fall back to index.html."""
    import server
    from db_pg import get_pg_pool
    from orchestration import runtime_state

    pool = await get_pg_pool()
    runtime_state.set_pool(pool)
    user_id = _user_id_from_auth_headers(auth_headers)
    project_id = f"published-missing-{uuid.uuid4().hex[:8]}"
    job = await runtime_state.create_job(
        project_id=project_id,
        mode="guided",
        goal="Published missing asset smoke",
        user_id=user_id,
    )
    root = server._project_workspace_path(project_id)
    (root / "dist").mkdir(parents=True, exist_ok=True)
    (root / "dist" / "index.html").write_text("<!doctype html><h1>Published smoke</h1>", encoding="utf-8")
    await runtime_state.update_job_state(job["id"], "completed", {"current_phase": "completed"})

    missing = await app_client.get(f"/published/{job['id']}/assets/missing.js", timeout=10)

    assert missing.status_code == 404


async def test_smoke_job_api_exposes_preview_url_for_completed_published_app(app_client, auth_headers):
    """Completed published jobs should return a preview_url so the workspace iframe can boot."""
    import server
    from db_pg import get_pg_pool
    from orchestration import runtime_state

    pool = await get_pg_pool()
    runtime_state.set_pool(pool)
    user_id = _user_id_from_auth_headers(auth_headers)
    project_id = f"job-preview-{uuid.uuid4().hex[:8]}"
    job = await runtime_state.create_job(
        project_id=project_id,
        mode="guided",
        goal="Job preview url smoke",
        user_id=user_id,
    )
    root = server._project_workspace_path(project_id)
    (root / "dist").mkdir(parents=True, exist_ok=True)
    (root / "dist" / "index.html").write_text("<!doctype html><h1>Preview smoke</h1>", encoding="utf-8")
    await runtime_state.update_job_state(job["id"], "completed", {"current_phase": "completed"})

    r = await app_client.get(f"/api/jobs/{job['id']}", headers=auth_headers, timeout=10)

    assert r.status_code == 200
    payload = r.json()["job"]
    assert payload["preview_url"].endswith(f"/published/{job['id']}/")
    assert payload["deploy_url"].endswith(f"/published/{job['id']}/")


async def test_smoke_visual_edit_patches_owned_job_workspace(app_client, auth_headers):
    """Visual edit loop can patch a generated file and leaves an undo snapshot."""
    import server
    from db_pg import get_pg_pool
    from orchestration import runtime_state

    pool = await get_pg_pool()
    runtime_state.set_pool(pool)
    user_id = _user_id_from_auth_headers(auth_headers)
    project_id = f"visual-edit-smoke-{uuid.uuid4().hex[:8]}"
    job = await runtime_state.create_job(
        project_id=project_id,
        mode="guided",
        goal="Visual edit smoke",
        user_id=user_id,
    )
    root = server._project_workspace_path(project_id)
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "src" / "App.jsx").write_text("export default function App(){return <h1>Old copy</h1>}", encoding="utf-8")
    await runtime_state.update_job_state(job["id"], "completed", {"current_phase": "completed"})

    r = await app_client.post(
        f"/api/jobs/{job['id']}/visual-edit",
        json={"file_path": "src/App.jsx", "find_text": "Old copy", "replace_text": "New copy"},
        headers=auth_headers,
        timeout=10,
    )

    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "patched"
    assert "New copy" in (root / "src" / "App.jsx").read_text(encoding="utf-8")
    assert (root / data["snapshot_path"]).is_file()


async def test_smoke_visual_edit_rejects_cross_user_job(app_client, auth_headers):
    """Visual edit loop is scoped to the owning job user."""
    from db_pg import get_pg_pool
    from orchestration import runtime_state

    other_headers = await _register_smoke_headers(app_client)
    pool = await get_pg_pool()
    runtime_state.set_pool(pool)
    user_id = _user_id_from_auth_headers(auth_headers)
    job = await runtime_state.create_job(
        project_id=f"visual-edit-cross-{uuid.uuid4().hex[:8]}",
        mode="guided",
        goal="Visual edit cross user",
        user_id=user_id,
    )

    r = await app_client.post(
        f"/api/jobs/{job['id']}/visual-edit",
        json={"file_path": "src/App.jsx", "find_text": "Old", "replace_text": "New"},
        headers=other_headers,
        timeout=10,
    )

    assert r.status_code == 403


async def test_smoke_examples_returns_200(app_client):
    """GET /api/examples returns 200 and examples array (Landing + ExamplesGallery)."""
    r = await app_client.get("/api/examples", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert "examples" in data
    assert isinstance(data["examples"], list)


async def test_smoke_template_remix_plan_and_remix(app_client, auth_headers):
    """Template gallery has a deterministic remix path into the golden workspace."""
    plan = await app_client.get("/api/templates/dashboard/remix-plan", timeout=10)
    assert plan.status_code == 200
    assert plan.json()["route"] == "/app/workspace"

    remix = await app_client.post(
        "/api/templates/dashboard/remix",
        json={"goal": "make it founder friendly"},
        headers=auth_headers,
        timeout=10,
    )
    assert remix.status_code == 200
    data = remix.json()
    assert data["remix"] is True
    assert data["next_route"] == "/app/workspace"
    assert "src/App.jsx" in data["files"]


async def test_smoke_public_community_templates_are_curated_and_remixable(app_client):
    """Public template/community layer exposes only curated remixable templates."""
    templates = await app_client.get("/api/community/templates", timeout=10)
    assert templates.status_code == 200
    data = templates.json()
    assert data["status"] == "ready"
    assert data["moderation"] == "curated_pre_publish"
    items = data["templates"]
    assert len(items) >= 4
    assert all(item["moderation_status"] == "approved" for item in items)
    assert all(item["remix_endpoint"] for item in items)

    plan = await app_client.get("/api/community/templates/dashboard/remix-plan", timeout=10)
    assert plan.status_code == 200
    assert plan.json()["proof_score"] >= 90

    moderation = await app_client.get("/api/community/moderation-policy", timeout=10)
    assert moderation.status_code == 200
    assert "secret scan" in moderation.json()["checks"]

    cases = await app_client.get("/api/community/case-studies", timeout=10)
    assert cases.status_code == 200
    assert len(cases.json()["case_studies"]) >= 3


async def test_smoke_health_with_retries(app_client):
    """Health responds (retries not needed in-process)."""
    r = await app_client.get("/api/health", timeout=5)
    assert r.status_code == 200


async def test_smoke_health_llm_preflight_returns_provider_contract(app_client):
    """LLM readiness probe reports provider configuration without secret values."""
    r = await app_client.get(
        "/api/health/llm",
        params={"prompt": "Build a full-stack todo app with deploy proof."},
        timeout=10,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["secret_values_included"] is False
    assert "providers" in data
    assert data["env_contract"]["providers"]["anthropic"]["key_env"] == "ANTHROPIC_API_KEY"


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


async def test_smoke_ide_debug_start_returns_200(app_client, auth_headers):
    """POST /api/ide/debug/start returns 200 for an authenticated project workspace."""
    project_id = await _create_smoke_project(app_client, auth_headers)
    r = await app_client.post(
        "/api/ide/debug/start",
        params={"project_id": project_id},
        headers=auth_headers,
        timeout=10,
    )
    assert r.status_code == 200
    data = r.json()
    assert "session_id" in data
    assert data.get("project_id") == project_id


async def test_smoke_ide_debug_start_requires_auth(app_client):
    """POST /api/ide/debug/start requires auth."""
    r = await app_client.post("/api/ide/debug/start", params={"project_id": "test-project"}, timeout=10)
    assert r.status_code == 401


async def test_smoke_ide_lint_returns_200(app_client, auth_headers):
    """POST /api/ide/lint returns 200 for an authenticated project workspace."""
    project_id = await _create_smoke_project(app_client, auth_headers)
    r = await app_client.post(
        "/api/ide/lint",
        params={"project_id": project_id, "file_path": "src/App.js", "code": "const x = 1;"},
        headers=auth_headers,
        timeout=10,
    )
    assert r.status_code == 200
    assert "issues" in r.json()


async def test_smoke_ide_profiler_requires_owned_project(app_client, auth_headers):
    """POST /api/ide/profiler/start rejects unknown or unowned projects."""
    r = await app_client.post(
        "/api/ide/profiler/start",
        params={"project_id": "not-owned"},
        headers=auth_headers,
        timeout=10,
    )
    assert r.status_code == 404


async def test_smoke_ide_profiler_start_stop_returns_200(app_client, auth_headers):
    """POST /api/ide/profiler/start and stop are scoped to the authenticated user."""
    project_id = await _create_smoke_project(app_client, auth_headers)
    start = await app_client.post(
        "/api/ide/profiler/start",
        params={"project_id": project_id},
        headers=auth_headers,
        timeout=10,
    )
    assert start.status_code == 200
    session_id = start.json().get("session_id")
    assert session_id
    stop = await app_client.post(
        "/api/ide/profiler/stop",
        params={"session_id": session_id},
        headers=auth_headers,
        timeout=10,
    )
    assert stop.status_code == 200
    assert stop.json().get("status") == "stopped"


async def test_smoke_git_status_returns_200(app_client, auth_headers):
    """GET /api/git/status returns 200 for an authenticated project workspace."""
    project_id = await _create_smoke_project(app_client, auth_headers)
    r = await app_client.get(
        "/api/git/status",
        params={"project_id": project_id},
        headers=auth_headers,
        timeout=10,
    )
    assert r.status_code == 200
    data = r.json()
    assert "branch" in data
    assert "modified" in data


async def test_smoke_git_status_rejects_raw_repo_path(app_client, auth_headers):
    """GET /api/git/status no longer accepts raw server paths."""
    r = await app_client.get(
        "/api/git/status",
        params={"repo_path": "/tmp/repo"},
        headers=auth_headers,
        timeout=10,
    )
    assert r.status_code == 400


async def test_smoke_terminal_create_returns_200(app_client, auth_headers):
    """POST /api/terminal/create returns 200 for an authenticated project workspace."""
    project_id = await _create_smoke_project(app_client, auth_headers)
    r = await app_client.post(
        "/api/terminal/create",
        params={"project_id": project_id},
        headers=auth_headers,
        timeout=10,
    )
    assert r.status_code == 200
    data = r.json()
    assert "session_id" in data


async def test_smoke_terminal_create_requires_auth(app_client):
    """POST /api/terminal/create requires auth."""
    r = await app_client.post("/api/terminal/create", params={"project_id": "test-project"}, timeout=10)
    assert r.status_code == 401


async def test_smoke_terminal_create_respects_disabled_env(app_client, auth_headers, monkeypatch):
    """Terminal execution is disabled in production unless explicitly enabled."""
    project_id = await _create_smoke_project(app_client, auth_headers)
    monkeypatch.setenv("CRUCIBAI_TERMINAL_ENABLED", "0")
    r = await app_client.post(
        "/api/terminal/create",
        params={"project_id": project_id},
        headers=auth_headers,
        timeout=10,
    )
    assert r.status_code == 403


async def test_smoke_terminal_policy_blocks_non_admin_host_shell_in_production(monkeypatch):
    """Enabling terminal explicitly is not enough for non-admin host shell in production."""
    import server

    monkeypatch.delenv("CRUCIBAI_TEST", raising=False)
    monkeypatch.delenv("CRUCIBAI_DEV", raising=False)
    monkeypatch.setenv("CRUCIBAI_TERMINAL_ENABLED", "1")

    assert server._terminal_execution_allowed({"id": "user-1", "admin_role": None}) is False


async def test_smoke_terminal_execute_returns_result(app_client, auth_headers):
    """Create session, POST /api/terminal/{id}/execute with a command; get returncode/stdout."""
    project_id = await _create_smoke_project(app_client, auth_headers)
    create_r = await app_client.post(
        "/api/terminal/create",
        params={"project_id": project_id},
        headers=auth_headers,
        timeout=10,
    )
    assert create_r.status_code == 200
    session_id = create_r.json().get("session_id")
    assert session_id
    exec_r = await app_client.post(
        f"/api/terminal/{session_id}/execute",
        json={"command": "echo hello", "timeout": 10},
        headers=auth_headers,
        timeout=15,
    )
    assert exec_r.status_code == 200
    data = exec_r.json()
    assert "returncode" in data
    assert data.get("returncode") == 0, f"expected 0, got {data}"
    assert "stdout" in data
    assert "hello" in data.get("stdout", "")


async def test_smoke_terminal_execute_blocks_dangerous_commands(app_client, auth_headers, monkeypatch):
    """Terminal policy blocks high-risk commands while host-shell execution remains launch-gated."""
    project_id = await _create_smoke_project(app_client, auth_headers)
    monkeypatch.setenv("CRUCIBAI_TERMINAL_ENABLED", "1")
    create_r = await app_client.post(
        "/api/terminal/create",
        params={"project_id": project_id},
        headers=auth_headers,
        timeout=10,
    )
    assert create_r.status_code == 200
    session_id = create_r.json().get("session_id")
    exec_r = await app_client.post(
        f"/api/terminal/{session_id}/execute",
        json={"command": "rm -rf /", "timeout": 10},
        headers=auth_headers,
        timeout=15,
    )
    assert exec_r.status_code == 200
    data = exec_r.json()
    assert data.get("returncode") == -1
    assert "terminal policy" in data.get("stderr", "")
    audit_r = await app_client.get("/api/terminal/audit", headers=auth_headers, timeout=10)
    assert audit_r.status_code == 200
    events = audit_r.json().get("events") or []
    assert any(event.get("blocked") is True and event.get("command") == "rm -rf /" for event in events)


async def test_smoke_terminal_audit_requires_auth(app_client):
    """Terminal audit trail is not public."""
    r = await app_client.get("/api/terminal/audit", timeout=10)
    assert r.status_code == 401


async def test_smoke_terminal_execute_respects_disabled_env(app_client, auth_headers, monkeypatch):
    """Terminal command execution can be gated off after a session exists."""
    project_id = await _create_smoke_project(app_client, auth_headers)
    monkeypatch.setenv("CRUCIBAI_TERMINAL_ENABLED", "1")
    create_r = await app_client.post(
        "/api/terminal/create",
        params={"project_id": project_id},
        headers=auth_headers,
        timeout=10,
    )
    assert create_r.status_code == 200
    session_id = create_r.json().get("session_id")
    monkeypatch.setenv("CRUCIBAI_TERMINAL_ENABLED", "0")
    exec_r = await app_client.post(
        f"/api/terminal/{session_id}/execute",
        json={"command": "echo blocked", "timeout": 10},
        headers=auth_headers,
        timeout=15,
    )
    assert exec_r.status_code == 403


async def test_smoke_terminal_execute_rejects_cross_user_session(app_client, auth_headers, monkeypatch):
    """Terminal sessions are scoped to the owning user and hidden from other users."""
    other_headers = await _register_smoke_headers(app_client)
    project_id = await _create_smoke_project(app_client, auth_headers)
    monkeypatch.setenv("CRUCIBAI_TERMINAL_ENABLED", "1")
    create_r = await app_client.post(
        "/api/terminal/create",
        params={"project_id": project_id},
        headers=auth_headers,
        timeout=10,
    )
    assert create_r.status_code == 200
    session_id = create_r.json().get("session_id")
    exec_r = await app_client.post(
        f"/api/terminal/{session_id}/execute",
        json={"command": "echo should-not-run", "timeout": 10},
        headers=other_headers,
        timeout=15,
    )
    assert exec_r.status_code == 404


async def test_smoke_git_branches_returns_200(app_client, auth_headers):
    """GET /api/git/branches returns 200 and branches list for an authenticated project workspace."""
    project_id = await _create_smoke_project(app_client, auth_headers)
    r = await app_client.get(
        "/api/git/branches",
        params={"project_id": project_id},
        headers=auth_headers,
        timeout=10,
    )
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


async def test_smoke_vibecoding_detect_frameworks_project_requires_auth(app_client):
    """Project-backed framework detection requires auth before reading project metadata."""
    r = await app_client.post("/api/vibecoding/detect-frameworks", json={"project_id": "not-owned"}, timeout=10)
    assert r.status_code == 401


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
    """POST /api/cache/invalidate requires admin auth."""
    r = await app_client.post("/api/cache/invalidate", timeout=10)
    assert r.status_code == 401


async def test_smoke_agent_memory_requires_auth(app_client):
    """Agent memory routes require auth."""
    store = await app_client.post(
        "/api/agents/run/memory-store",
        json={"name": "pattern", "content": "private"},
        timeout=10,
    )
    listing = await app_client.get("/api/agents/run/memory-list", timeout=10)
    assert store.status_code == 401
    assert listing.status_code == 401


async def test_smoke_agent_memory_list_is_user_scoped(app_client, auth_headers):
    """Agent memory list only returns the current user's rows."""
    other_headers = await _register_smoke_headers(app_client)
    other = await app_client.post(
        "/api/agents/run/memory-store",
        json={"name": "other-memory", "content": "not yours"},
        headers=other_headers,
        timeout=10,
    )
    own = await app_client.post(
        "/api/agents/run/memory-store",
        json={"name": "own-memory", "content": "yours"},
        headers=auth_headers,
        timeout=10,
    )
    assert other.status_code == 200
    assert own.status_code == 200
    listing = await app_client.get("/api/agents/run/memory-list", headers=auth_headers, timeout=10)
    assert listing.status_code == 200
    names = [item.get("name") for item in listing.json().get("items", [])]
    assert "own-memory" in names
    assert "other-memory" not in names


async def test_smoke_agent_automation_requires_auth(app_client):
    """Agent automation routes require auth."""
    store = await app_client.post(
        "/api/agents/run/automation",
        json={"name": "job", "prompt": "private"},
        timeout=10,
    )
    listing = await app_client.get("/api/agents/run/automation-list", timeout=10)
    assert store.status_code == 401
    assert listing.status_code == 401


async def test_smoke_agent_automation_list_is_user_scoped(app_client, auth_headers):
    """Agent automation list only returns the current user's rows."""
    other_headers = await _register_smoke_headers(app_client)
    other = await app_client.post(
        "/api/agents/run/automation",
        json={"name": "other-automation", "prompt": "not yours"},
        headers=other_headers,
        timeout=10,
    )
    own = await app_client.post(
        "/api/agents/run/automation",
        json={"name": "own-automation", "prompt": "yours"},
        headers=auth_headers,
        timeout=10,
    )
    assert other.status_code == 200
    assert own.status_code == 200
    listing = await app_client.get("/api/agents/run/automation-list", headers=auth_headers, timeout=10)
    assert listing.status_code == 200
    names = [item.get("name") for item in listing.json().get("items", [])]
    assert "own-automation" in names
    assert "other-automation" not in names


async def test_smoke_agent_run_generic_requires_auth(app_client):
    """Generic LLM-backed agent runner requires user auth."""
    r = await app_client.post(
        "/api/agents/run/generic",
        json={"agent_name": "Content Agent", "prompt": "Summarize this"},
        timeout=10,
    )
    assert r.status_code == 401


@pytest.mark.parametrize(
    ("path", "payload"),
    [
        ("/api/ai/chat", {"message": "hello"}),
        ("/api/ai/analyze", {"content": "hello", "task": "summarize"}),
        ("/api/generate/doc", {"prompt": "write a launch plan"}),
        ("/api/agents/run/planner", {"prompt": "plan a todo app"}),
        ("/api/build/from-reference", {"prompt": "build from this reference"}),
        ("/api/ai/generate-readme", {"code": "print('hi')", "project_name": "Demo"}),
    ],
)
async def test_smoke_phase2_llm_action_routes_reject_anonymous(app_client, path, payload):
    """Anonymous callers cannot spend server-side LLM/action capacity."""
    r = await app_client.post(path, json=payload, timeout=10)
    assert r.status_code == 401, f"{path} returned {r.status_code}: {r.text}"


async def test_smoke_phase2_chat_history_requires_owner(app_client, auth_headers):
    """Chat history is scoped to the authenticated user's session rows."""
    import server

    other_headers = await _register_smoke_headers(app_client)
    own_user_id = _user_id_from_auth_headers(auth_headers)
    other_user_id = _user_id_from_auth_headers(other_headers)
    session_id = f"phase2-chat-{uuid.uuid4().hex[:8]}"
    await server.db.chat_history.insert_one({
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "user_id": other_user_id,
        "message": "other secret",
        "response": "other response",
        "model": "test",
        "tokens_used": 1,
        "created_at": "2026-01-01T00:00:00+00:00",
    })
    await server.db.chat_history.insert_one({
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "user_id": own_user_id,
        "message": "own prompt",
        "response": "own response",
        "model": "test",
        "tokens_used": 1,
        "created_at": "2026-01-01T00:01:00+00:00",
    })

    anon = await app_client.get(f"/api/ai/chat/history/{session_id}", timeout=10)
    assert anon.status_code == 401
    own = await app_client.get(f"/api/ai/chat/history/{session_id}", headers=auth_headers, timeout=10)
    assert own.status_code == 200
    messages = [row["message"] for row in own.json().get("history", [])]
    assert "own prompt" in messages
    assert "other secret" not in messages


async def test_smoke_phase2_blueprint_persona_rejects_cross_user_access(app_client, auth_headers):
    """Blueprint persona routes filter by the owning user_id."""
    other_headers = await _register_smoke_headers(app_client)
    created = await app_client.post(
        "/api/personas",
        json={"name": "Other Persona", "description": "tenant private"},
        headers=other_headers,
        timeout=10,
    )
    assert created.status_code == 201, created.text
    persona_id = created.json()["persona"]["id"]
    get_r = await app_client.get(f"/api/personas/{persona_id}", headers=auth_headers, timeout=10)
    assert get_r.status_code == 404
    delete_r = await app_client.delete(f"/api/personas/{persona_id}", headers=auth_headers, timeout=10)
    assert delete_r.status_code == 404


async def test_smoke_phase2_blueprint_session_messages_require_owned_session(app_client, auth_headers):
    """Blueprint session messages cannot be written anonymously or across users."""
    other_headers = await _register_smoke_headers(app_client)
    created = await app_client.post(
        "/api/sessions",
        json={"user_identifier": "other-user-widget"},
        headers=other_headers,
        timeout=10,
    )
    assert created.status_code == 201, created.text
    session_id = created.json()["session"]["id"]
    payload = {"role": "user", "content": "hello"}

    anon = await app_client.post(f"/api/sessions/{session_id}/messages", json=payload, timeout=10)
    assert anon.status_code == 401
    cross = await app_client.post(f"/api/sessions/{session_id}/messages", json=payload, headers=auth_headers, timeout=10)
    assert cross.status_code == 404
    owned = await app_client.post(f"/api/sessions/{session_id}/messages", json=payload, headers=other_headers, timeout=10)
    assert owned.status_code == 201


async def test_smoke_agent_run_generic_unknown_agent_returns_404_for_user(app_client, auth_headers):
    """Authenticated generic runner rejects unknown agents before LLM execution."""
    r = await app_client.post(
        "/api/agents/run/generic",
        json={"agent_name": "Not A Real Agent", "prompt": "Summarize this"},
        headers=auth_headers,
        timeout=10,
    )
    assert r.status_code == 404


async def test_smoke_agents_from_description_creates_run_agent_automation(app_client, auth_headers, monkeypatch):
    """Prompt-to-automation can save an automation that calls the app-building agent DAG."""
    import server

    async def fake_llm_with_fallback(**kwargs):
        return (
            """
            {
              "name": "Daily build summary",
              "description": "Summarize new build output every morning.",
              "trigger": {"type": "schedule", "cron_expression": "0 9 * * *"},
              "actions": [
                {
                  "type": "run_agent",
                  "config": {
                    "agent_name": "Content Agent",
                    "prompt": "Summarize yesterday's build output and list blockers."
                  }
                }
              ]
            }
            """,
            "test-model",
        )

    monkeypatch.setattr(server, "_call_llm_with_fallback", fake_llm_with_fallback)

    r = await app_client.post(
        "/api/agents/from-description",
        json={"description": "Every day at 9am, summarize yesterday's build output with Content Agent."},
        headers=auth_headers,
        timeout=10,
    )

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["name"] == "Daily build summary"
    assert data["trigger_type"] == "schedule"
    assert data["actions"][0]["type"] == "run_agent"
    assert data["actions"][0]["config"]["agent_name"] == "Content Agent"


async def test_smoke_agent_run_executes_run_agent_action(app_client, auth_headers, monkeypatch):
    """Manual automation runs execute saved run_agent actions and persist output."""
    import server

    calls = []

    async def fake_llm_with_fallback(**kwargs):
        calls.append(kwargs)
        return ("Bridge run output", "test-model")

    monkeypatch.setattr(server, "_call_llm_with_fallback", fake_llm_with_fallback)

    create = {
        "name": "Manual bridge proof",
        "trigger": {"type": "webhook", "webhook_secret": "bridge-secret"},
        "actions": [
            {
                "type": "run_agent",
                "config": {
                    "agent_name": "Content Agent",
                    "prompt": "Summarize today's build proof.",
                },
            }
        ],
    }
    created = await app_client.post("/api/agents", json=create, headers=auth_headers, timeout=10)
    assert created.status_code in (200, 201), created.text
    agent_id = created.json()["id"]

    run = await app_client.post(f"/api/agents/{agent_id}/run", headers=auth_headers, timeout=20)
    assert run.status_code == 200, run.text
    assert run.json()["status"] == "success"
    run_id = run.json()["run_id"]

    detail = await app_client.get(f"/api/agents/runs/{run_id}", headers=auth_headers, timeout=10)
    assert detail.status_code == 200, detail.text
    output_summary = detail.json()["output_summary"]
    assert output_summary["steps"][0]["output"]["result"] == "Bridge run output"
    assert calls
    assert calls[0]["message"] == "Summarize today's build proof."


async def test_smoke_retry_step_rejects_unowned_job(app_client, auth_headers):
    """POST /api/jobs/{job_id}/retry-step/{step_id} rejects another user's job step."""
    other_headers = await _register_smoke_headers(app_client)
    job_id, step_id = await _create_failed_smoke_job_step(other_headers)
    r = await app_client.post(
        f"/api/jobs/{job_id}/retry-step/{step_id}",
        headers=auth_headers,
        timeout=10,
    )
    assert r.status_code == 403


async def test_smoke_retry_step_returns_200_for_owned_failed_step(app_client, auth_headers):
    """POST /api/jobs/{job_id}/retry-step/{step_id} resets an owned failed step."""
    job_id, step_id = await _create_failed_smoke_job_step(auth_headers)
    r = await app_client.post(
        f"/api/jobs/{job_id}/retry-step/{step_id}",
        headers=auth_headers,
        timeout=10,
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("success") is True
    assert data.get("status") == "pending"


async def test_smoke_run_auto_ignores_client_workspace_path(app_client, auth_headers, monkeypatch):
    """POST /api/orchestrator/run-auto resolves workspace from job project_id, not request path."""
    import server

    captured = {}

    async def fake_background(job_id, workspace_path):
        captured["job_id"] = job_id
        captured["workspace_path"] = workspace_path

    monkeypatch.setattr(server, "_background_auto_runner_job", fake_background)
    job_id, project_id = await _create_smoke_auto_job(auth_headers)
    malicious = "C:\\Windows\\System32"
    r = await app_client.post(
        "/api/orchestrator/run-auto",
        json={"job_id": job_id, "workspace_path": malicious},
        headers=auth_headers,
        timeout=20,
    )
    assert r.status_code == 200, r.text
    assert captured.get("job_id") == job_id
    assert captured.get("workspace_path")
    assert malicious not in captured["workspace_path"]
    assert project_id in captured["workspace_path"]


async def test_smoke_background_runner_exception_has_precise_reason(app_client, auth_headers, monkeypatch, tmp_path):
    """Background wrapper records explicit exception metadata, not generic background_crash."""
    import json
    import server
    from db_pg import get_pg_pool
    from orchestration import auto_runner, runtime_state

    pool = await get_pg_pool()
    runtime_state.set_pool(pool)
    job_id, _project_id = await _create_smoke_auto_job(auth_headers)

    async def fake_run_job_to_completion(job_id, workspace_path="", db_pool=None):
        raise RuntimeError("late-stage verifier boom")

    monkeypatch.setattr(auto_runner, "run_job_to_completion", fake_run_job_to_completion)

    await server._background_auto_runner_job(job_id, str(tmp_path))

    job = await runtime_state.get_job(job_id)
    assert job["status"] == "failed"
    assert job["current_phase"] == "background_runner_exception"

    events = await runtime_state.get_job_events(job_id, limit=50)
    payloads = [json.loads(event["payload_json"]) for event in events]
    reasons = [payload.get("reason") for payload in payloads]
    assert "background_runner_exception" in reasons
    assert "background_crash" not in reasons
    assert any(payload.get("exception_type") == "RuntimeError" for payload in payloads)


async def test_smoke_job_state_routes_require_auth(app_client, auth_headers):
    """Stateful job/proof endpoints require an authenticated owner."""
    job_id, _project_id = await _create_smoke_auto_job(auth_headers)
    endpoints = [
        ("GET", f"/api/jobs/{job_id}", None),
        ("GET", "/api/jobs", None),
        ("POST", "/api/ai/build/async", {"message": "Build a smoke app"}),
        ("GET", f"/api/jobs/{job_id}/steps", None),
        ("GET", f"/api/jobs/{job_id}/plan-draft", None),
        ("GET", f"/api/jobs/{job_id}/events", None),
        ("GET", f"/api/jobs/{job_id}/proof", None),
        ("GET", f"/api/jobs/{job_id}/trust-report", None),
        ("GET", f"/api/jobs/{job_id}/stream", None),
    ]
    for method, path, body in endpoints:
        if method == "POST":
            r = await app_client.post(path, json=body or {}, timeout=10)
        else:
            r = await app_client.get(path, timeout=10)
        assert r.status_code == 401, f"{path} returned {r.status_code}: {r.text[:200]}"


async def test_smoke_job_state_routes_reject_unowned_job(app_client, auth_headers):
    """Stateful job/proof endpoints reject another user's job."""
    other_headers = await _register_smoke_headers(app_client)
    job_id, _project_id = await _create_smoke_auto_job(other_headers)
    endpoints = [
        f"/api/jobs/{job_id}",
        f"/api/jobs/{job_id}/steps",
        f"/api/jobs/{job_id}/plan-draft",
        f"/api/jobs/{job_id}/events",
        f"/api/jobs/{job_id}/proof",
        f"/api/jobs/{job_id}/trust-report",
        f"/api/jobs/{job_id}/stream",
    ]
    for path in endpoints:
        r = await app_client.get(path, headers=auth_headers, timeout=10)
        assert r.status_code == 403, f"{path} returned {r.status_code}: {r.text[:200]}"
    run = await app_client.post(
        "/api/orchestrator/run-auto",
        json={"job_id": job_id, "workspace_path": "C:\\Windows\\System32"},
        headers=auth_headers,
        timeout=20,
    )
    assert run.status_code == 403


async def test_smoke_job_proof_includes_build_contract(app_client, auth_headers):
    """GET /api/jobs/{job_id}/proof includes the stable build contract envelope."""
    job_id, _project_id = await _create_smoke_auto_job(auth_headers)
    r = await app_client.get(f"/api/jobs/{job_id}/proof", headers=auth_headers, timeout=10)
    assert r.status_code == 200, r.text
    contract = r.json().get("build_contract")
    assert contract
    assert contract.get("version") == "2026-04-08.v1"
    assert contract.get("job_id") == job_id
    assert contract.get("goal") == "Build a smoke app"
    assert contract.get("deploy_ready") is False
    assert "missing_verification_evidence" in contract.get("blockers", [])


async def test_smoke_orchestrator_plan_rejects_unowned_project(app_client, auth_headers):
    """POST /api/orchestrator/plan rejects a project_id owned by another user."""
    other_headers = await _register_smoke_headers(app_client)
    other_project_id = await _create_smoke_project(app_client, other_headers)
    r = await app_client.post(
        "/api/orchestrator/plan",
        json={"project_id": other_project_id, "goal": "Build a smoke todo app", "mode": "guided"},
        headers=auth_headers,
        timeout=20,
    )
    assert r.status_code == 404


async def test_smoke_create_job_rejects_unowned_project(app_client, auth_headers):
    """POST /api/jobs rejects a project_id owned by another user."""
    other_headers = await _register_smoke_headers(app_client)
    other_project_id = await _create_smoke_project(app_client, other_headers)
    r = await app_client.post(
        "/api/jobs",
        json={"project_id": other_project_id, "goal": "Build a smoke todo app", "mode": "guided"},
        headers=auth_headers,
        timeout=20,
    )
    assert r.status_code == 404


async def test_smoke_create_job_allows_owned_project(app_client, auth_headers):
    """POST /api/jobs accepts a project_id owned by the current user."""
    project_id = await _create_smoke_project(app_client, auth_headers)
    r = await app_client.post(
        "/api/jobs",
        json={"project_id": project_id, "goal": "Build a smoke todo app", "mode": "guided"},
        headers=auth_headers,
        timeout=20,
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("success") is True
    assert data.get("job", {}).get("project_id") == project_id


async def test_smoke_app_db_schema_returns_200_for_owned_task(app_client, auth_headers):
    """GET /api/app-db/{task_id} returns schema only for an owned task."""
    task_id = await _create_smoke_task(auth_headers)
    r = await app_client.get(f"/api/app-db/task/{task_id}", headers=auth_headers, timeout=10)
    assert r.status_code == 200
    schema = r.json().get("schema")
    assert schema
    assert "smoke_items" in schema.get("tables", [])


async def test_smoke_app_db_schema_requires_auth(app_client):
    """GET /api/app-db/{task_id} requires auth."""
    r = await app_client.get("/api/app-db/task/not-owned", timeout=10)
    assert r.status_code == 401


async def test_smoke_app_db_schema_rejects_unowned_task(app_client, auth_headers):
    """GET /api/app-db/{task_id} rejects another user's task."""
    other_headers = await _register_smoke_headers(app_client)
    task_id = await _create_smoke_task(other_headers)
    r = await app_client.get(f"/api/app-db/task/{task_id}", headers=auth_headers, timeout=10)
    assert r.status_code == 403


async def test_smoke_app_db_provision_returns_200_for_owned_task(app_client, auth_headers):
    """POST /api/app-db/provision accepts an owned task."""
    task_id = await _create_smoke_task(auth_headers)
    r = await app_client.post(
        "/api/app-db/provision",
        json={"task_id": task_id, "prompt": "schema"},
        headers=auth_headers,
        timeout=10,
    )
    assert r.status_code in (200, 201)
    assert r.json().get("status") == "ok"


async def test_smoke_app_db_provision_rejects_unowned_project(app_client, auth_headers):
    """POST /api/app-db/provision rejects a project_id owned by another user."""
    other_headers = await _register_smoke_headers(app_client)
    project_id = await _create_smoke_project(app_client, other_headers)
    r = await app_client.post(
        "/api/app-db/provision",
        json={"project_id": project_id, "description": "Generate a schema for a private CRM workspace."},
        headers=auth_headers,
        timeout=10,
    )
    assert r.status_code == 404


async def test_smoke_legacy_vercel_deploy_rejects_unowned_task(app_client, auth_headers):
    """Legacy deploy helper rejects another user's task."""
    other_headers = await _register_smoke_headers(app_client)
    task_id = await _create_smoke_task(other_headers)
    r = await app_client.post(
        "/api/deploy/vercel",
        json={"task_id": task_id},
        headers=auth_headers,
        timeout=10,
    )
    assert r.status_code == 403


async def test_smoke_git_sync_rejects_unowned_task(app_client, auth_headers):
    """POST /api/git-sync/push rejects another user's task before external GitHub work."""
    other_headers = await _register_smoke_headers(app_client)
    task_id = await _create_smoke_task(other_headers, files={"README.md": "# private"})
    r = await app_client.post(
        "/api/git-sync/push",
        json={"task_id": task_id, "repo_name": "smoke-private"},
        headers=auth_headers,
        timeout=10,
    )
    assert r.status_code == 403


async def test_smoke_git_sync_rejects_unowned_project(app_client, auth_headers):
    """POST /api/git-sync/push rejects another user's project."""
    other_headers = await _register_smoke_headers(app_client)
    project_id = await _create_smoke_project(app_client, other_headers)
    r = await app_client.post(
        "/api/git-sync/push",
        json={"project_id": project_id, "repo_name": "smoke-private"},
        headers=auth_headers,
        timeout=10,
    )
    assert r.status_code == 404


async def test_smoke_railway_deploy_rejects_unowned_task(app_client, auth_headers):
    """POST /api/deploy/railway rejects another user's task before external Railway work."""
    other_headers = await _register_smoke_headers(app_client)
    task_id = await _create_smoke_task(other_headers, files={"README.md": "# private"})
    r = await app_client.post(
        "/api/deploy/railway",
        json={"task_id": task_id, "service_name": "smoke-private"},
        headers=auth_headers,
        timeout=10,
    )
    assert r.status_code == 403


async def test_smoke_railway_deploy_rejects_unowned_project(app_client, auth_headers):
    """POST /api/deploy/railway rejects another user's project."""
    other_headers = await _register_smoke_headers(app_client)
    project_id = await _create_smoke_project(app_client, other_headers)
    r = await app_client.post(
        "/api/deploy/railway",
        json={"project_id": project_id, "service_name": "smoke-private"},
        headers=auth_headers,
        timeout=10,
    )
    assert r.status_code == 404
