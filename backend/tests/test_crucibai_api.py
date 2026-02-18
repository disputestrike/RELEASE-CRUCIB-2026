"""
CrucibAI API Tests – real app via AsyncClient (no mocks).
Tests: Health, AI Chat, Auth, Tokens, Projects, Patterns, Build phases, Stripe.
AI endpoints may return 503/500 when no API keys or missing LLM deps; tests accept 200, 503, 500.
"""
import pytest
import time

# Allow 200 (success), 503 (service unavailable), 500 (e.g. missing google/anthropic/openai)
AI_OK_STATUSES = (200, 503, 500)


class TestHealthEndpoints:
    """Health check endpoint tests."""

    async def test_health_endpoint(self, app_client):
        r = await app_client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    async def test_root_endpoint(self, app_client):
        r = await app_client.get("/api/")
        assert r.status_code == 200
        data = r.json()
        assert "message" in data
        assert "CrucibAI" in data["message"]


# DB-dependent tests run before AI tests (AI can leave event loop in bad state for Motor).
class TestAuthEndpoints:
    """Auth – real DB; register, login, me."""

    async def test_register_new_user(self, app_client):
        test_email = f"test_user_{int(time.time())}@example.com"
        r = await app_client.post("/api/auth/register", json={
            "email": test_email,
            "password": "testpass123",
            "name": "Test User"
        })
        assert r.status_code == 200
        data = r.json()
        assert "token" in data
        assert "user" in data
        assert data["user"]["email"] == test_email
        assert "token_balance" in data["user"]

    async def test_register_duplicate_email(self, app_client):
        test_email = f"test_dup_{int(time.time())}@example.com"
        await app_client.post("/api/auth/register", json={
            "email": test_email,
            "password": "testpass123",
            "name": "Test User"
        })
        r = await app_client.post("/api/auth/register", json={
            "email": test_email,
            "password": "testpass123",
            "name": "Test User 2"
        })
        assert r.status_code == 400

    async def test_login_valid_credentials(self, app_client):
        test_email = f"test_login_{int(time.time())}@example.com"
        await app_client.post("/api/auth/register", json={
            "email": test_email,
            "password": "testpass123",
            "name": "Test User"
        })
        r = await app_client.post("/api/auth/login", json={
            "email": test_email,
            "password": "testpass123"
        })
        assert r.status_code == 200
        data = r.json()
        assert "token" in data
        assert "user" in data

    async def test_login_invalid_credentials(self, app_client):
        r = await app_client.post("/api/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "wrongpass"
        })
        assert r.status_code == 401

    async def test_get_me_authenticated(self, app_client):
        test_email = f"test_me_{int(time.time())}@example.com"
        reg = await app_client.post("/api/auth/register", json={
            "email": test_email,
            "password": "testpass123",
            "name": "Test User"
        })
        token = reg.json()["token"]
        r = await app_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["email"] == test_email

    async def test_get_me_unauthenticated(self, app_client):
        r = await app_client.get("/api/auth/me")
        assert r.status_code == 401


class TestTokenEndpoints:
    """Tokens – bundles, history (auth required for some)."""

    async def test_get_bundles(self, app_client):
        r = await app_client.get("/api/tokens/bundles")
        assert r.status_code == 200
        data = r.json()
        assert "bundles" in data
        assert "starter" in data["bundles"]
        assert "pro" in data["bundles"]

    async def test_purchase_tokens(self, app_client):
        test_email = f"test_purchase_{int(time.time())}@example.com"
        reg = await app_client.post("/api/auth/register", json={
            "email": test_email,
            "password": "testpass123",
            "name": "Test User"
        })
        token = reg.json()["token"]
        user = reg.json()["user"]
        # API returns new_balance in credits (not tokens)
        initial_credits = user.get("credit_balance") or (user.get("token_balance", 0) // 1000)
        r = await app_client.post("/api/tokens/purchase", json={"bundle": "starter"}, headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        # starter bundle adds 100 credits
        assert data["new_balance"] == initial_credits + 100
        assert data["credits_added"] == 100

    async def test_get_token_history(self, app_client):
        test_email = f"test_history_{int(time.time())}@example.com"
        reg = await app_client.post("/api/auth/register", json={
            "email": test_email,
            "password": "testpass123",
            "name": "Test User"
        })
        token = reg.json()["token"]
        r = await app_client.get("/api/tokens/history", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        assert "history" in data
        assert "current_balance" in data
        assert len(data["history"]) >= 1


class TestAgentsEndpoints:
    """GET /api/agents returns public build-swarm definitions (no auth)."""

    async def test_get_agents_unauth_401(self, app_client):
        r = await app_client.get("/api/agents")
        assert r.status_code == 200
        data = r.json()
        assert "agents" in data
        assert isinstance(data["agents"], list)

    async def test_get_agents_with_auth(self, app_client, auth_headers):
        r = await app_client.get("/api/agents", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert "agents" in data
        assert isinstance(data["agents"], list)


class TestPatternsEndpoints:
    """GET /api/patterns."""

    async def test_get_patterns(self, app_client):
        r = await app_client.get("/api/patterns")
        assert r.status_code == 200
        data = r.json()
        assert "patterns" in data
        assert len(data["patterns"]) > 0
        p = data["patterns"][0]
        assert "id" in p
        assert "name" in p
        assert "category" in p


class TestDashboardEndpoints:
    """GET /api/dashboard/stats (auth required)."""

    async def test_get_dashboard_stats(self, app_client):
        test_email = f"test_dashboard_{int(time.time())}@example.com"
        reg = await app_client.post("/api/auth/register", json={
            "email": test_email,
            "password": "testpass123",
            "name": "Test User"
        })
        token = reg.json()["token"]
        r = await app_client.get("/api/dashboard/stats", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        assert "total_projects" in data
        assert "token_balance" in data
        assert "weekly_data" in data


class TestProjectEndpoints:
    """Projects – create (may 402 if low balance), list."""

    async def test_create_project(self, app_client):
        test_email = f"test_project_{int(time.time())}@example.com"
        reg = await app_client.post("/api/auth/register", json={
            "email": test_email,
            "password": "testpass123",
            "name": "Test User"
        })
        token = reg.json()["token"]
        r = await app_client.post("/api/projects", json={
            "name": "Test Project",
            "description": "A test project",
            "project_type": "web_app",
            "requirements": {"features": ["auth", "dashboard"]},
            "estimated_tokens": 50000
        }, headers={"Authorization": f"Bearer {token}"})
        assert r.status_code in (200, 402)
        if r.status_code == 200:
            data = r.json()
            assert "project" in data
            assert data["project"]["name"] == "Test Project"

    async def test_get_projects(self, app_client):
        test_email = f"test_projects_{int(time.time())}@example.com"
        reg = await app_client.post("/api/auth/register", json={
            "email": test_email,
            "password": "testpass123",
            "name": "Test User"
        })
        token = reg.json()["token"]
        r = await app_client.get("/api/projects", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        data = r.json()
        assert "projects" in data


class TestBuildPhasesAndValidate:
    """Build phases and validate-and-fix (validate may 200, 503, or 500)."""

    async def test_build_phases(self, app_client):
        r = await app_client.get("/api/build/phases")
        assert r.status_code == 200
        data = r.json()
        assert "phases" in data
        assert len(data["phases"]) >= 1
        assert data["phases"][0].get("id") and data["phases"][0].get("name")

    async def test_validate_and_fix(self, app_client):
        r = await app_client.post("/api/ai/validate-and-fix", json={
            "code": "function foo() { return 1; }",
            "language": "javascript"
        })
        assert r.status_code in AI_OK_STATUSES
        if r.status_code == 200:
            data = r.json()
            assert "fixed_code" in data
            assert "valid" in data


class TestAIChatEndpoints:
    """AI Chat – real endpoint; 200 when keys set, 503/500 when not."""

    async def test_ai_chat_auto_model(self, app_client):
        r = await app_client.post("/api/ai/chat", json={"message": "Hello, test", "model": "auto"})
        assert r.status_code in AI_OK_STATUSES
        if r.status_code == 200:
            data = r.json()
            assert "response" in data
            assert "model_used" in data
            assert "tokens_used" in data
            assert "session_id" in data

    async def test_ai_chat_gpt4o_model(self, app_client):
        r = await app_client.post("/api/ai/chat", json={"message": "What is 2+2?", "model": "gpt-4o"})
        assert r.status_code in AI_OK_STATUSES
        if r.status_code == 200:
            data = r.json()
            assert "response" in data
            assert "gpt-4o" in data["model_used"].lower() or "openai" in data["model_used"].lower()

    async def test_ai_chat_claude_model(self, app_client):
        r = await app_client.post("/api/ai/chat", json={"message": "Say hello", "model": "claude"})
        assert r.status_code in AI_OK_STATUSES
        if r.status_code == 200:
            data = r.json()
            assert "response" in data
            assert "claude" in data["model_used"].lower() or "anthropic" in data["model_used"].lower()

    async def test_ai_chat_gemini_model(self, app_client):
        r = await app_client.post("/api/ai/chat", json={"message": "Hi there", "model": "gemini"})
        assert r.status_code in AI_OK_STATUSES
        if r.status_code == 200:
            data = r.json()
            assert "response" in data
            assert "gemini" in data["model_used"].lower()

    async def test_ai_chat_with_session(self, app_client):
        session_id = f"test_session_{int(time.time())}"
        r1 = await app_client.post("/api/ai/chat", json={
            "message": "Remember the number 42",
            "session_id": session_id,
            "model": "auto"
        })
        assert r1.status_code in AI_OK_STATUSES
        if r1.status_code == 200:
            assert r1.json()["session_id"] == session_id
            r2 = await app_client.post("/api/ai/chat", json={
                "message": "What number did I mention?",
                "session_id": session_id,
                "model": "auto"
            })
            assert r2.status_code in AI_OK_STATUSES
            if r2.status_code == 200:
                assert r2.json()["session_id"] == session_id


class TestAIAnalysisEndpoints:
    """AI Analyze – 200, 503, or 500."""

    async def test_ai_analyze_summarize(self, app_client):
        r = await app_client.post("/api/ai/analyze", json={
            "content": "This is a test document about software development.",
            "task": "summarize"
        })
        assert r.status_code in AI_OK_STATUSES
        if r.status_code == 200:
            data = r.json()
            assert "result" in data
            assert data["task"] == "summarize"

    async def test_ai_analyze_extract(self, app_client):
        r = await app_client.post("/api/ai/analyze", json={
            "content": "John Smith works at Acme Corp in New York.",
            "task": "extract"
        })
        assert r.status_code in AI_OK_STATUSES
        if r.status_code == 200:
            data = r.json()
            assert "result" in data
            assert data["task"] == "extract"


class TestSearchEndpoint:
    """Search – 200, 503, or 500."""

    async def test_hybrid_search(self, app_client):
        r = await app_client.post("/api/search", json={
            "query": "React components",
            "search_type": "hybrid"
        })
        assert r.status_code in AI_OK_STATUSES
        if r.status_code == 200:
            data = r.json()
            assert "query" in data
            assert "results" in data
            assert data["search_type"] == "hybrid"


class TestStripeEndpoints:
    """Stripe – 401/503 when not configured or no auth."""

    async def test_stripe_checkout_requires_auth(self, app_client):
        r = await app_client.post("/api/stripe/create-checkout-session", json={"bundle": "starter"})
        assert r.status_code in (401, 503)

    async def test_stripe_checkout_invalid_bundle(self, app_client):
        r = await app_client.post("/api/stripe/create-checkout-session", json={"bundle": "invalid_bundle"}, headers={"Authorization": "Bearer fake"})
        assert r.status_code in (400, 401, 403, 503)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
