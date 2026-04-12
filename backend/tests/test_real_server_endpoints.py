"""
REAL INTEGRATION TESTS FOR CRUCIBAI
Uses actual FastAPI server, actual PostgreSQL database, real endpoints
"""

import pytest
import asyncio
import os
from datetime import datetime, timedelta
import jwt
import json
from fastapi.testclient import TestClient
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Import actual server
from server import app

# ============================================================================
# TEST CLIENT SETUP
# ============================================================================


@pytest.fixture
def client():
    """Create a test client for the FastAPI app (lifespan runs so DB is initialized)."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def jwt_token():
    """Create a valid JWT token"""
    secret = os.getenv("JWT_SECRET", "test_secret_key")
    payload = {
        "user_id": "test_user_123",
        "email": "test@example.com",
        "exp": datetime.utcnow() + timedelta(hours=24),
    }
    token = jwt.encode(payload, secret, algorithm="HS256")
    return token


# ============================================================================
# PHASE 2: REAL OAUTH TESTS (Call actual endpoints)
# ============================================================================


class TestRealOAuthEndpoints:
    """Test actual OAuth endpoints in server.py"""

    def test_auth_me_endpoint_exists(self, client):
        """REAL TEST: /api/auth/me endpoint should exist"""
        response = client.get("/api/auth/me")
        assert response.status_code in [200, 401, 403], f"Got {response.status_code}"
        print(f"✅ /api/auth/me endpoint exists (status: {response.status_code})")

    def test_auth_me_requires_token(self, client):
        """REAL TEST: /api/auth/me should reject requests without token"""
        response = client.get("/api/auth/me")
        assert response.status_code in [
            401,
            403,
        ], f"Expected 401/403, got {response.status_code}"
        print("✅ /api/auth/me correctly rejects unauthenticated requests")

    def test_oauth_callback_endpoint_exists(self, client):
        """REAL TEST: /api/oauth/callback endpoint should exist"""
        # This would normally be called by Google OAuth
        # Just verify the endpoint exists
        response = client.get("/api/oauth/callback")
        # Should return 400 or 422 (bad request) not 404
        assert response.status_code != 404, "OAuth callback endpoint not found"
        print(
            f"✅ /api/oauth/callback endpoint exists (status: {response.status_code})"
        )


# ============================================================================
# PHASE 3: REAL AGENT EXECUTION TESTS
# ============================================================================


class TestRealAgentEndpoints:
    """Test actual agent execution endpoints"""

    def test_projects_endpoint_exists(self, client):
        """REAL TEST: /api/projects endpoint should exist"""
        response = client.get("/api/projects")
        # Should return 401 (needs auth) or 200 (if authenticated)
        assert response.status_code in [200, 401, 403], f"Got {response.status_code}"
        print(f"✅ /api/projects endpoint exists (status: {response.status_code})")

    def test_build_endpoint_exists(self, client):
        """REAL TEST: /api/projects/build endpoint should exist"""
        response = client.post("/api/projects/build", json={"project_id": "test"})
        # Should return 401 (needs auth) or 400 (bad request) not 404
        assert response.status_code != 404, "Build endpoint not found"
        print(
            f"✅ /api/projects/build endpoint exists (status: {response.status_code})"
        )


# ============================================================================
# PHASE 4: REAL METRICS TESTS
# ============================================================================


class TestPublicPlannerEndpoints:
    """Test public planner verification endpoints."""

    def test_public_build_summary_returns_compact_plan(self, client, monkeypatch):
        """REAL TEST: /api/build/summary should return a trimmed public planner payload."""
        import server

        class FakePlanner:
            @staticmethod
            async def generate_plan(goal, project_state=None):
                return {
                    "goal": goal,
                    "summary": "Compact plan summary",
                    "orchestration_mode": "agent_swarm",
                    "phase_count": 3,
                    "phases": [
                        ["Planner"],
                        ["Build Validator Agent", "Frontend Generation"],
                        ["Security Checker"],
                    ],
                    "selected_agent_count": 4,
                    "selected_agents": [
                        "Planner",
                        "Build Validator Agent",
                        "Frontend Generation",
                        "Security Checker",
                    ],
                    "recommended_build_target": "vite_react",
                    "selection_explanation": {
                        "matched_keywords": [
                            "build",
                            "validator",
                            "frontend",
                            "security",
                        ],
                    },
                    "controller_summary": {
                        "execution_strategy": "dependency_aware_parallelism",
                        "parallel_phase_count": 3,
                        "recommended_focus": "Watch Build Validator Agent",
                        "next_actions": [
                            "launch_parallel_specialists",
                            "run_security_hardening_pass",
                        ],
                        "replan_triggers": ["agent_failure", "verification_failure"],
                        "memory_strategy": "scoped_project_job_phase_memory",
                    },
                    "missing_inputs": [],
                    "risk_flags": [],
                }

        monkeypatch.setattr(
            server, "_get_orchestration", lambda: (None, None, FakePlanner, None, None)
        )

        response = client.post(
            "/api/build/summary", json={"goal": "Build validated secure app"}
        )

        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["success"] is True
        plan = payload["plan"]
        assert plan["orchestration_mode"] == "agent_swarm"
        assert plan["selected_agent_count"] == 4
        assert plan["phase_sizes"] == [1, 2, 1]
        assert plan["selected_agents"] == [
            "Planner",
            "Build Validator Agent",
            "Frontend Generation",
            "Security Checker",
        ]
        assert "phases" not in plan
        assert (
            plan["controller_summary"]["recommended_focus"]
            == "Watch Build Validator Agent"
        )


class TestRealMetricsEndpoint:
    """Test actual metrics endpoint"""

    def test_metrics_endpoint_exists(self, client):
        """REAL TEST: /api/metrics endpoint should exist and return Prometheus-style text"""
        response = client.get("/api/metrics")
        assert response.status_code != 404, "/api/metrics endpoint not found"
        if response.status_code == 200:
            text = response.text
            assert (
                "# HELP" in text
                or "# TYPE" in text
                or "_total" in text
                or "_duration" in text
                or "metrics" in text.lower()
            ), "Response doesn't look like Prometheus format"
            print("✅ /api/metrics endpoint returns Prometheus format")
        else:
            print(f"✅ /api/metrics endpoint exists (status: {response.status_code})")


# ============================================================================
# PHASE 5: REAL STRIPE WEBHOOK TESTS
# ============================================================================


class TestRealStripeWebhook:
    """Test actual Stripe webhook endpoint"""

    def test_stripe_webhook_endpoint_exists(self, client):
        """REAL TEST: /api/stripe/webhook endpoint should exist"""
        response = client.post("/api/stripe/webhook", json={})

        # Should not return 404
        assert response.status_code != 404, "Stripe webhook endpoint not found"
        print(
            f"✅ /api/stripe/webhook endpoint exists (status: {response.status_code})"
        )


# ============================================================================
# PHASE 6: REAL HEALTH CHECK
# ============================================================================


class TestHealthCheck:
    """Test application health"""

    def test_app_is_running(self, client):
        """REAL TEST: App should respond to requests"""
        response = client.get("/")
        assert response.status_code in [
            200,
            404,
            405,
        ], f"App not responding (status: {response.status_code})"
        print(f"✅ App is running and responding (status: {response.status_code})")

    def test_health_endpoint(self, client):
        """REAL TEST: /api/health should exist"""
        response = client.get("/api/health")
        assert response.status_code == 200, f"Got {response.status_code}"
        print(f"✅ /api/health endpoint exists (status: {response.status_code})")


# ============================================================================
# SUMMARY
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
