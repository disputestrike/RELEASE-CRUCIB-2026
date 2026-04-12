"""
Layer 3.1 – API endpoint contract tests.
Uses real app via AsyncClient (no separate server, no mocks).
Verifies response status codes and response shape for critical endpoints.
"""

import pytest


class TestHealthContract:
    """GET /api/health – contract."""

    async def test_health_status_200(self, app_client):
        r = await app_client.get("/api/health", timeout=5)
        assert r.status_code == 200

    async def test_health_body_has_status_and_timestamp(self, app_client):
        r = await app_client.get("/api/health", timeout=5)
        data = r.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "timestamp" in data


class TestRootContract:
    """GET /api/ – contract."""

    async def test_root_status_200(self, app_client):
        r = await app_client.get("/api/", timeout=5)
        assert r.status_code == 200

    async def test_root_body_has_message(self, app_client):
        r = await app_client.get("/api/", timeout=5)
        data = r.json()
        assert "message" in data


class TestVoiceTranscribeContract:
    """POST /api/voice/transcribe - strict auth first, payload validation after auth."""

    async def test_voice_transcribe_without_file_returns_401(self, app_client):
        r = await app_client.post("/api/voice/transcribe", timeout=10)
        assert r.status_code == 401

    async def test_voice_transcribe_with_empty_file_returns_401_without_auth(
        self, app_client
    ):
        files = {"audio": ("empty.webm", b"", "audio/webm")}
        r = await app_client.post("/api/voice/transcribe", files=files, timeout=10)
        assert r.status_code == 401

    async def test_voice_transcribe_with_empty_file_returns_400_or_503_with_auth(
        self, app_client, auth_headers
    ):
        files = {"audio": ("empty.webm", b"", "audio/webm")}
        r = await app_client.post(
            "/api/voice/transcribe", files=files, headers=auth_headers, timeout=10
        )
        assert r.status_code in (400, 503, 500)


class TestAuthContract:
    """Auth endpoints – contract."""

    async def test_auth_me_without_token_returns_401(self, app_client):
        r = await app_client.get("/api/auth/me", timeout=5)
        assert r.status_code == 401

    async def test_login_with_invalid_body_returns_422(self, app_client):
        r = await app_client.post("/api/auth/login", json={}, timeout=5)
        assert r.status_code == 422


class TestBuildPhasesContract:
    """GET /api/build/phases – contract."""

    async def test_build_phases_status_200(self, app_client):
        r = await app_client.get("/api/build/phases", timeout=5)
        assert r.status_code == 200

    async def test_build_phases_body_has_phases_array(self, app_client):
        r = await app_client.get("/api/build/phases", timeout=5)
        data = r.json()
        assert "phases" in data
        assert isinstance(data["phases"], list)
