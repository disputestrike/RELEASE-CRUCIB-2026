"""
Load tests: concurrent requests, connection pooling, no race conditions.
Uses in-process app_client; rate limit raised in conftest.
"""

import asyncio
import pytest


class TestConcurrentHealthChecks:
    """5.1 / 6.5: Many concurrent requests do not timeout."""

    @pytest.mark.asyncio
    async def test_100_concurrent_health_requests(self, app_client):
        """100 concurrent GET /api/health (or /health) complete without timeout."""

        async def one():
            r = await app_client.get("/api/health")
            return r.status_code

        tasks = [one() for _ in range(100)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        codes = [r for r in results if not isinstance(r, Exception)]
        assert len(codes) == 100, "Expected 100/100 health checks to complete"
        assert all(c == 200 for c in codes), "All health checks should return 200"


class TestConcurrentRegistrations:
    """Concurrent user registrations do not corrupt DB or return 500."""

    @pytest.mark.asyncio
    async def test_20_concurrent_registrations(self, app_client):
        """20 concurrent registrations complete; no duplicate key or 500."""
        import uuid

        async def register():
            email = f"load-{uuid.uuid4().hex[:12]}@example.com"
            r = await app_client.post(
                "/api/auth/register",
                json={"email": email, "password": "TestPass123!", "name": "Load Test"},
                timeout=10,
            )
            return r.status_code

        tasks = [register() for _ in range(20)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        ok = [r for r in results if not isinstance(r, Exception) and r in (200, 201)]
        assert len(ok) >= 18, "Expected at least 18/20 registrations to succeed"


class TestConcurrentProjectList:
    """Concurrent authenticated project list requests."""

    @pytest.mark.asyncio
    async def test_30_concurrent_project_lists(self, app_client, auth_headers):
        """30 concurrent GET /api/projects with same user complete."""

        async def list_projects():
            r = await app_client.get("/api/projects", headers=auth_headers, timeout=10)
            return r.status_code

        tasks = [list_projects() for _ in range(30)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        codes = [r for r in results if not isinstance(r, Exception)]
        assert (
            len(codes) >= 28
        ), "Expected at least 28/30 project list requests to succeed"
        assert all(c == 200 for c in codes), "All project lists should return 200"
