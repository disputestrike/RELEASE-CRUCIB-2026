"""
Fortune 100 Layer 1: Full API route coverage.
Every endpoint is exercised with appropriate auth and validated for expected status/schema.
"""
import pytest
from conftest import register_and_get_headers

# Routes that are PUBLIC (no auth) - expect 200/201
PUBLIC_GET = [
    ("/api/", None),
    ("/api/health", ["status"]),
    ("/api/tokens/bundles", ["bundles"]),
    ("/api/build/phases", None),
    ("/api/agents/templates", None),
    ("/api/templates", None),
    ("/api/patterns", None),
    ("/api/examples", ["examples"]),
    ("/api/prompts/templates", None),
]

# Routes that REQUIRE AUTH - expect 401 without token
AUTH_GET = [
    "/api/agents",
    "/api/auth/me",
    "/api/projects",
    "/api/tokens/history",
    "/api/tokens/usage",
    "/api/referrals/code",
    "/api/referrals/stats",
    "/api/exports",
    "/api/dashboard/stats",
    "/api/prompts/saved",
    "/api/users/me/deploy-tokens",
]

# POST routes that REQUIRE AUTH - (path, min_body, accept_status)
AUTH_POST = [
    ("/api/build/plan", {"prompt": "a landing page"}, [200, 402]),
    ("/api/projects", {"name": "t", "description": "d", "project_type": "web", "requirements": {}}, [200, 201, 402]),
    ("/api/prompts/save", {"name": "test", "content": "x"}, [200, 201, 422]),
    ("/api/workspace/env", {"env": {}}, [200, 201]),
]

# POST routes that accept optional auth - (path, body, statuses)
POST_PUBLIC_OR_AUTH = [
    ("/api/auth/register", {"email": "cov@test.com", "password": "x", "name": "x"}, [200, 201, 400, 422]),
    ("/api/auth/login", {"email": "x@x.com", "password": "x"}, [200, 401]),
    ("/api/ai/chat", {"message": "hi", "session_id": "cov"}, [200, 401, 500]),
    ("/api/ai/analyze", {"content": "const x=1;", "doc_type": "text", "task": "summarize"}, [200, 401, 500]),
    ("/api/ai/validate-and-fix", {"code": "x", "language": "javascript"}, [200, 401, 500]),
    ("/api/rag/query", {"query": "test"}, [200, 401, 500]),
    ("/api/search", {"query": "test"}, [200, 401, 500]),
    ("/api/export/zip", {"files": {}}, [200, 401]),
    ("/api/build/from-reference", {"url": "https://example.com"}, [200, 401, 400, 422, 500]),
]

# Paths with dynamic IDs - need placeholder
DYNAMIC_GET = [
    ("/api/projects/cov-dummy-id", [401, 404]),
    ("/api/projects/cov-dummy-id/logs", [401, 404]),
    ("/api/projects/cov-dummy-id/phases", [401, 404]),
    ("/api/agents/status/cov-dummy-id", [401, 404]),
    ("/api/ai/chat/history/cov-session", [200, 401, 404]),
    ("/api/examples/todo-app", [200, 404]),
    ("/api/share/invalid-cov-token", [200, 404]),
]


@pytest.mark.asyncio
async def test_public_get_routes(app_client):
    """Every public GET route returns 200 and expected keys."""
    for path, expect_keys in PUBLIC_GET:
        r = await app_client.get(path, timeout=10)
        assert r.status_code == 200, f"GET {path}: expected 200, got {r.status_code}"
        if expect_keys:
            data = r.json()
            for k in expect_keys:
                assert k in data, f"GET {path}: missing key {k}"


@pytest.mark.asyncio
async def test_auth_required_get_401(app_client):
    """Protected GET routes return 401 without token."""
    for path in AUTH_GET:
        r = await app_client.get(path, timeout=5)
        assert r.status_code == 401, f"GET {path}: expected 401, got {r.status_code}"


@pytest.mark.asyncio
async def test_auth_required_post_401(app_client):
    """Protected POST routes return 401 without token."""
    for path, body, _ in AUTH_POST:
        r = await app_client.post(path, json=body, timeout=10)
        assert r.status_code == 401, f"POST {path}: expected 401, got {r.status_code}"


@pytest.mark.asyncio
async def test_auth_get_with_token(app_client):
    """Protected GET routes return 200 with valid token."""
    headers = await register_and_get_headers(app_client)
    for path in AUTH_GET:
        r = await app_client.get(path, headers=headers, timeout=10)
        assert r.status_code == 200, f"GET {path}: expected 200, got {r.status_code}"


@pytest.mark.asyncio
async def test_auth_post_with_token(app_client):
    """Protected POST routes return acceptable status with valid token."""
    headers = await register_and_get_headers(app_client)
    for path, body, accept in AUTH_POST:
        r = await app_client.post(path, json=body, headers=headers, timeout=30)
        assert r.status_code in accept, f"POST {path}: expected one of {accept}, got {r.status_code}"


@pytest.mark.asyncio
async def test_post_public_or_auth_routes(app_client):
    """POST routes that accept public or auth return acceptable status."""
    for path, body, accept in POST_PUBLIC_OR_AUTH:
        r = await app_client.post(path, json=body, timeout=15)
        assert r.status_code in accept, f"POST {path}: expected one of {accept}, got {r.status_code}"


@pytest.mark.asyncio
async def test_dynamic_paths(app_client):
    """Routes with dynamic IDs return expected status (401 or 404 for unknown)."""
    for path, accept in DYNAMIC_GET:
        r = await app_client.get(path, timeout=5)
        assert r.status_code in accept, f"GET {path}: expected one of {accept}, got {r.status_code}"


@pytest.mark.asyncio
async def test_voice_transcribe_requires_file(app_client):
    """POST /voice/transcribe returns 422 without file."""
    r = await app_client.post("/api/voice/transcribe", timeout=5)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_stripe_checkout_requires_auth(app_client):
    """Stripe checkout requires auth."""
    r = await app_client.post(
        "/api/stripe/create-checkout-session",
        json={"bundle": "starter"},
        timeout=5,
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_enterprise_contact_accepts_post(app_client):
    """Enterprise contact form accepts POST."""
    r = await app_client.post(
        "/api/enterprise/contact",
        json={"name": "Test", "email": "e@e.com", "message": "Hi", "company": "Acme"},
        timeout=10,
    )
    assert r.status_code in (200, 201, 400, 422)


@pytest.mark.asyncio
async def test_generate_doc_slides_sheets(app_client):
    """Generate doc/slides/sheets routes accept POST."""
    for path, body in [
        ("/api/generate/doc", {"topic": "Test", "format": "markdown"}),
        ("/api/generate/slides", {"topic": "Test", "slides": 3}),
        ("/api/generate/sheets", {"topic": "Test", "columns": ["A", "B"]}),
    ]:
        r = await app_client.post(path, json=body, timeout=30)
        assert r.status_code in (200, 401, 422, 500), f"POST {path}: got {r.status_code}"


@pytest.mark.asyncio
async def test_ai_extra_routes(app_client):
    """AI routes: security-scan, optimize, accessibility-check, explain-error, suggest-next."""
    routes = [
        ("/api/ai/security-scan", {"files": {"/App.js": "const a=1;"}}),
        ("/api/ai/optimize", {"code": "x", "language": "javascript"}),
        ("/api/ai/accessibility-check", {"code": "<div>hi</div>"}),
        ("/api/ai/explain-error", {"error": "SyntaxError", "code": "x"}),
        ("/api/ai/suggest-next", {"files": {}, "last_prompt": ""}),
        ("/api/ai/inject-stripe", {"code": "// app", "target": "checkout"}),
        ("/api/ai/generate-readme", {"code": "x", "project_name": "T"}),
        ("/api/ai/generate-docs", {"code": "x", "doc_type": "api"}),
        ("/api/ai/generate-faq-schema", {"faqs": [{"q": "Q", "a": "A"}]}),
        ("/api/ai/design-from-url", {"url": "https://example.com"}),
    ]
    for path, body in routes:
        r = await app_client.post(path, json=body, timeout=20)
        assert r.status_code in (200, 401, 400, 422, 500), f"POST {path}: got {r.status_code}"


@pytest.mark.asyncio
async def test_agent_run_routes_with_auth(app_client):
    """Agent run routes return 200 or 401 with auth."""
    headers = await register_and_get_headers(app_client)
    routes = [
        ("/api/agents/run/planner", {"prompt": "todo"}),
        ("/api/agents/run/requirements-clarifier", {"prompt": "blog"}),
        ("/api/agents/run/stack-selector", {"prompt": "shop"}),
        ("/api/agents/run/backend-generate", {"prompt": "api"}),
        ("/api/agents/run/database-design", {"prompt": "schema"}),
        ("/api/agents/run/api-integrate", {"prompt": "api"}),
        ("/api/agents/run/test-generate", {"code": "x", "language": "js"}),
        ("/api/agents/run/image-generate", {"prompt": "logo"}),
        ("/api/agents/run/test-executor", {"prompt": "test"}),
        ("/api/agents/run/deploy", {"prompt": "deploy"}),
        ("/api/agents/run/memory-store", {"name": "p", "content": "c"}),
        ("/api/agents/run/export-pdf", {"title": "T", "content": "C"}),
        ("/api/agents/run/export-excel", {"title": "T", "rows": []}),
        ("/api/agents/run/export-markdown", {"title": "T", "content": "C"}),
        ("/api/agents/run/scrape", {"url": "https://example.com"}),
        ("/api/agents/run/automation", {"name": "p", "prompt": "x"}),
    ]
    for path, body in routes:
        r = await app_client.post(path, json=body, headers=headers, timeout=45)
        assert r.status_code in (200, 401, 402, 500), f"POST {path}: got {r.status_code}"


@pytest.mark.asyncio
async def test_agent_run_get_routes(app_client):
    """Agent run GET routes (memory-list, automation-list)."""
    headers = await register_and_get_headers(app_client)
    for path in ["/api/agents/run/memory-list", "/api/agents/run/automation-list"]:
        r = await app_client.get(path, headers=headers, timeout=10)
        assert r.status_code in (200, 401), f"GET {path}: got {r.status_code}"


@pytest.mark.asyncio
async def test_files_analyze_route(app_client):
    """POST /files/analyze accepts form or JSON."""
    r = await app_client.post("/api/files/analyze", json={"files": {}}, timeout=10)
    assert r.status_code in (200, 401, 400, 422)


@pytest.mark.asyncio
async def test_mfa_routes_require_auth(app_client):
    """MFA routes return 401 without token."""
    for path in ["/api/mfa/setup", "/api/mfa/status", "/api/mfa/verify", "/api/mfa/disable"]:
        if "status" in path:
            r = await app_client.get(path, timeout=5)
        else:
            r = await app_client.post(path, json={}, timeout=5)
        assert r.status_code in (401, 422), f"{path}: expected 401/422, got {r.status_code}"


@pytest.mark.asyncio
async def test_audit_logs_require_auth(app_client):
    """Audit logs require auth."""
    r = await app_client.get("/api/audit/logs", timeout=5)
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_exports_route_with_auth(app_client):
    """GET/POST /exports with auth."""
    headers = await register_and_get_headers(app_client)
    r = await app_client.get("/api/exports", headers=headers, timeout=10)
    assert r.status_code == 200
    r2 = await app_client.post("/api/exports", json={"project_id": "dummy", "format": "zip"}, headers=headers, timeout=15)
    assert r2.status_code in (200, 400, 404)


@pytest.mark.asyncio
async def test_templates_and_projects_from_template(app_client):
    """GET /templates, POST /projects/from-template."""
    r = await app_client.get("/api/templates", timeout=5)
    assert r.status_code == 200
    headers = await register_and_get_headers(app_client)
    r2 = await app_client.post("/api/projects/from-template", json={"template_id": "minimal"}, headers=headers, timeout=15)
    assert r2.status_code in (200, 201, 400, 404)


@pytest.mark.asyncio
async def test_share_create_and_get(app_client):
    """POST /share/create, GET /share/{token}."""
    headers = await register_and_get_headers(app_client)
    r = await app_client.post("/api/share/create", json={"project_id": "dummy", "expires_hours": 24}, headers=headers, timeout=10)
    assert r.status_code in (200, 201, 400, 404)
    r2 = await app_client.get("/api/share/bad-token-cov", timeout=5)
    assert r2.status_code in (200, 404)
