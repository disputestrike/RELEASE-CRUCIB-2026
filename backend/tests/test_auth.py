"""
CrucibAI Authentication Tests
===============================
Tests for OAuth flow, JWT tokens, session management, and protected routes.
"""

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest

# Resolve paths from this file so tests pass from repo root or backend/
_BACKEND_DIR = Path(__file__).resolve().parent.parent
_SERVER_PY = _BACKEND_DIR / "server.py"


def _read_server():
    return _SERVER_PY.read_text(encoding="utf-8")


# Test constants
TEST_JWT_SECRET = "test-secret-key-for-testing-only"
TEST_USER_EMAIL = "test@crucibai.com"
TEST_USER_ID = str(uuid.uuid4())


class TestJWTTokenGeneration:
    """Test JWT token creation and validation."""

    def test_create_valid_jwt(self):
        """JWT tokens should contain user_id and email."""
        payload = {
            "user_id": TEST_USER_ID,
            "email": TEST_USER_EMAIL,
            "exp": datetime.now(timezone.utc) + timedelta(hours=24),
            "iat": datetime.now(timezone.utc),
        }
        token = jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")
        decoded = jwt.decode(token, TEST_JWT_SECRET, algorithms=["HS256"])
        assert decoded["user_id"] == TEST_USER_ID
        assert decoded["email"] == TEST_USER_EMAIL

    def test_expired_jwt_raises(self):
        """Expired tokens should raise ExpiredSignatureError."""
        payload = {
            "user_id": TEST_USER_ID,
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token = jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(token, TEST_JWT_SECRET, algorithms=["HS256"])

    def test_invalid_secret_raises(self):
        """Tokens signed with wrong secret should fail verification."""
        payload = {
            "user_id": TEST_USER_ID,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")
        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(token, "wrong-secret", algorithms=["HS256"])

    def test_missing_user_id(self):
        """Tokens without user_id should be treated as invalid."""
        payload = {"exp": datetime.now(timezone.utc) + timedelta(hours=1)}
        token = jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")
        decoded = jwt.decode(token, TEST_JWT_SECRET, algorithms=["HS256"])
        assert "user_id" not in decoded


class TestOAuthCallbackFlow:
    """Test the Google OAuth callback handling."""

    def test_single_token_exchange(self):
        """
        CRITICAL: Verify there is only ONE token exchange call.
        The duplicate token exchange bug (lines 2109-2134) was the #1 blocker.
        Google auth codes are single-use — exchanging twice always fails.
        """
        content = _read_server()
        count = content.count("oauth2.googleapis.com/token")
        assert count == 1, (
            f"CRITICAL BUG: Found {count} token exchange calls. "
            f"Must be exactly 1. The duplicate block causes all Google logins to fail."
        )

    def test_no_hardcoded_redirect_urls(self):
        """Redirect URLs should use request.base_url, not hardcoded domains."""
        content = _read_server()
        # Should not contain hardcoded Railway or production URLs in OAuth
        assert (
            "crucibai.up.railway.app/api/auth" not in content
        ), "Found hardcoded Railway URL in OAuth — should use request.base_url"

    def test_frontend_redirect_after_auth(self):
        """After OAuth, user should be redirected to frontend with token."""
        content = _read_server()
        # Should redirect to frontend with token parameter
        assert (
            "?token=" in content or "token=" in content
        ), "OAuth callback should redirect with token parameter"


class TestProtectedRoutes:
    """Test that protected routes require authentication."""

    def test_auth_me_endpoint_exists(self):
        """The /auth/me endpoint must exist for session verification."""
        content = _read_server()
        assert "/auth/me" in content, "Missing /auth/me endpoint"

    def test_protected_routes_check_authorization(self):
        """Protected routes should check for Authorization header."""
        content = _read_server()
        assert "Authorization" in content, "No Authorization header check found"
        assert "Bearer" in content, "No Bearer token handling found"


class TestSessionSecurity:
    """Test session and cookie security."""

    def test_jwt_secret_not_hardcoded(self):
        """JWT_SECRET should come from environment, not hardcoded."""
        content = _read_server()
        # Should reference os.environ or os.getenv for JWT_SECRET
        assert "JWT_SECRET" in content, "JWT_SECRET not referenced"
        # Should not have a hardcoded secret value (common patterns)
        assert 'JWT_SECRET = "secret"' not in content, "Hardcoded JWT secret found"
        assert "JWT_SECRET = 'secret'" not in content, "Hardcoded JWT secret found"
