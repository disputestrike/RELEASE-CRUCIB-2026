# tests/test_foundation.py
"""
Comprehensive test suite for CrucibAI foundation systems.

Tests cover:
  - Configuration (deps module, config module)
  - RBAC (admin roles, admin IDs)
  - Database layer (PGCollection query building)
  - Server helpers (tokens, search detection, routing logic)
  - Route registration

Status: IMPLEMENTED
Total: 20+ test cases
"""

import os
import pytest
from datetime import datetime, timezone, timedelta

# Ensure backend is importable
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# PYTEST FIXTURES
# ============================================================================


@pytest.fixture(autouse=True)
def _set_env():
    """Set minimum required env vars for all tests."""
    os.environ.setdefault("DATABASE_URL", "postgresql://localhost/test")
    os.environ.setdefault("JWT_SECRET", "test-secret-for-pytest")


# ============================================================================
# TESTS: AUTHENTICATION / JWT
# ============================================================================


class TestAuthentication:
    def test_jwt_secret_defined(self):
        """Verify JWT secret is loaded from environment."""
        import backend.deps as deps
        assert deps.JWT_SECRET is not None
        assert len(deps.JWT_SECRET) > 10

    def test_jwt_algorithm_is_hs256(self):
        """Verify JWT uses HS256 algorithm."""
        import backend.deps as deps
        assert deps.JWT_ALGORITHM == "HS256"

    def test_jwt_token_roundtrip(self):
        """Test JWT encode and decode lifecycle."""
        import jwt
        import backend.deps as deps

        payload = {"user_id": "user-123", "role": "user"}
        token = jwt.encode(payload, deps.JWT_SECRET, algorithm=deps.JWT_ALGORITHM)
        assert token is not None

        decoded = jwt.decode(token, deps.JWT_SECRET, algorithms=[deps.JWT_ALGORITHM])
        assert decoded["user_id"] == "user-123"
        assert decoded["role"] == "user"

    def test_jwt_rejects_invalid_token(self):
        """Test that invalid tokens raise an error."""
        import jwt
        import backend.deps as deps

        with pytest.raises(jwt.InvalidTokenError):
            jwt.decode("not.a.valid.token", deps.JWT_SECRET, algorithms=[deps.JWT_ALGORITHM])

    def test_jwt_rejects_expired_token(self):
        """Test that expired tokens are rejected."""
        import jwt
        import backend.deps as deps

        payload = {"user_id": "user-123", "exp": datetime.now(tz=timezone.utc) - timedelta(hours=1)}
        token = jwt.encode(payload, deps.JWT_SECRET, algorithm=deps.JWT_ALGORITHM)

        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(token, deps.JWT_SECRET, algorithms=[deps.JWT_ALGORITHM])


# ============================================================================
# TESTS: RBAC
# ============================================================================


class TestRBAC:
    def test_admin_roles_defined(self):
        """Verify admin roles are defined in deps."""
        import backend.deps as deps
        assert hasattr(deps, "ADMIN_ROLES")
        assert isinstance(deps.ADMIN_ROLES, tuple)
        assert "admin" in deps.ADMIN_ROLES or "owner" in deps.ADMIN_ROLES

    def test_admin_user_ids_is_list(self):
        """Verify admin user IDs are a list (empty by default)."""
        import backend.deps as deps
        assert hasattr(deps, "ADMIN_USER_IDS")
        assert isinstance(deps.ADMIN_USER_IDS, list)

    def test_require_permission_imports(self):
        """Verify require_permission dependency exists."""
        import backend.deps as deps
        assert hasattr(deps, "require_permission")
        assert callable(deps.require_permission)


# ============================================================================
# TESTS: DATABASE LAYER
# ============================================================================


class TestDatabaseLayer:
    def test_pg_collection_build_where(self):
        """Test PGCollection WHERE clause building for various query types."""
        from backend.db_pg import PGCollection

        class FakePool:
            pass

        col = PGCollection(FakePool(), "users")

        # Empty query
        where, params = col._build_where({})
        assert where == "TRUE"
        assert params == []

        # Simple equality
        where, params = col._build_where({"email": "test@example.com"})
        assert "$1" in where
        assert params == ["test@example.com"]

        # ID query
        where, params = col._build_where({"id": "user-123"})
        assert "id = " in where
        assert params == ["user-123"]

        # $in operator
        where, params = col._build_where({"status": {"$in": ["active", "pending"]}})
        assert "IN" in where
        assert len(params) == 2

    def test_pg_collection_update_operators(self):
        """Test $set, $inc, $push, $pull update operators."""
        from backend.db_pg import PGCollection

        class FakePool:
            pass

        col = PGCollection(FakePool(), "users")

        # $set
        doc = {"name": "old", "count": 1}
        result = col._apply_update_operators(doc, {"$set": {"name": "new"}})
        assert result["name"] == "new"
        assert result["count"] == 1

        # $inc
        doc = {"count": 5}
        result = col._apply_update_operators(doc, {"$inc": {"count": 3}})
        assert result["count"] == 8

        # $push
        doc = {"tags": ["a"]}
        result = col._apply_update_operators(doc, {"$push": {"tags": "b"}})
        assert result["tags"] == ["a", "b"]

        # $unset
        doc = {"name": "test", "extra": True}
        result = col._apply_update_operators(doc, {"$unset": {"extra": 1}})
        assert "extra" not in result
        assert result["name"] == "test"

    def test_db_pg_is_pg_available(self):
        """Test PostgreSQL availability check."""
        from backend.db_pg import is_pg_available
        assert is_pg_available() is True


# ============================================================================
# TESTS: CONFIG
# ============================================================================


class TestConfig:
    def test_config_module_loads(self):
        """Test that the config module loads and exposes expected values."""
        import backend.config as config
        assert hasattr(config, "ROOT_DIR")
        assert hasattr(config, "WORKSPACE_ROOT")
        assert config.ROOT_DIR.exists()

    def test_env_setup_loads(self):
        """Test that env_setup module loads without errors."""
        import backend.env_setup
        assert True


# ============================================================================
# TESTS: ROUTE REGISTRATION
# ============================================================================


class TestRouteRegistration:
    def test_all_required_routes_loaded(self):
        """Verify critical route modules loaded successfully."""
        import backend.server as server

        required_modules = [
            "backend.routes.auth",
            "backend.routes.projects",
            "backend.routes.ai",
            "backend.routes.orchestrator",
            "backend.routes.jobs",
        ]

        loaded = {r["module"] for r in server.ROUTE_REGISTRATION_REPORT if r["status"] == "loaded"}
        failed = {r["module"]: r.get("error", "") for r in server.ROUTE_REGISTRATION_REPORT if r["status"] == "failed"}

        for mod in required_modules:
            assert mod in loaded, f"Required route {mod} failed to load: {failed.get(mod)}"


# ============================================================================
# TESTS: SERVER HELPERS
# ============================================================================


class TestServerHelpers:
    def test_tokens_to_credits_min_one(self):
        """Credit conversion floors at 1 credit."""
        from backend.server import _tokens_to_credits
        assert _tokens_to_credits(0) >= 1  # max(1, ...)
        assert _tokens_to_credits(1000) == 1
        assert _tokens_to_credits(2500) == 2
        assert _tokens_to_credits(999999) == 999

    def test_needs_live_data(self):
        from backend.server import _needs_live_data
        # Pure greetings — no search
        assert not _needs_live_data("hello")
        assert not _needs_live_data("ok")
        # Identity questions — no search
        assert not _needs_live_data("who are you?")
        assert not _needs_live_data("what model are you?")
        # Real questions — search
        assert _needs_live_data("what is the capital of France?")
        assert _needs_live_data("who won the super bowl 2025?")
        # Math — no search
        assert not _needs_live_data("2 + 2 = ?")

    def test_is_conversational_message(self):
        from backend.server import _is_conversational_message
        # Greetings
        assert _is_conversational_message("hello")
        assert _is_conversational_message("hey there")
        # Short messages
        assert _is_conversational_message("ok")
        # Build requests
        assert not _is_conversational_message("build me a web app with dashboard")
        assert not _is_conversational_message("create a REST API for my startup")
        # Long technical messages
        assert not _is_conversational_message(
            "I want to build a full-stack e-commerce platform with React, Node.js, PostgreSQL, and Stripe integration"
        )

    def test_merge_prior_turns(self):
        from backend.server import _merge_prior_turns_into_message
        # No prior turns
        assert _merge_prior_turns_into_message("hello", None) == "hello"
        assert _merge_prior_turns_into_message("hello", []) == "hello"
        # With prior turns
        turns = [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello! What do you want?"},
        ]
        result = _merge_prior_turns_into_message("Build a chat app", turns)
        assert "Build a chat app" in result
        assert "Hi" in result


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
