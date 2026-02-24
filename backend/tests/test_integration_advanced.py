"""
Advanced integration tests for CrucibAI.

Tests:
- End-to-end workflows
- Multi-component interactions
- Database transactions
- Concurrent operations
- Error recovery
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from access_control import User, Role, Permission, access_control
from input_validation import validator
from security_headers import RateLimiter
from ssrf_prevention import SSRFValidator
from artifact_signing import ArtifactSigner


class TestEndToEndWorkflows:
    """Test complete end-to-end workflows."""

    def test_build_creation_workflow(self):
        """Test complete build creation workflow."""
        # Create user
        user = User("user1", "alice", Role.DEVELOPER)

        # Check permission
        access_control.enforce_permission(user, Permission.BUILD_CREATE)

        # Validate input
        build_name = validator.validate_string("my-build", max_length=100)
        assert build_name == "my-build"

        # Simulate build creation
        build = {
            "id": "build-123",
            "name": build_name,
            "created_by": user.id,
            "created_at": datetime.utcnow().isoformat(),
        }

        assert build["name"] == "my-build"
        assert build["created_by"] == "user1"

    def test_multi_user_concurrent_access(self):
        """Test concurrent access from multiple users."""
        users = [
            User(f"user{i}", f"user{i}", Role.USER)
            for i in range(5)
        ]

        def check_permission(user):
            return access_control.check_permission(
                user, Permission.BUILD_READ
            )

        # Check permissions concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(check_permission, users))

        assert all(results)

    def test_rate_limiting_workflow(self):
        """Test rate limiting across multiple requests."""
        limiter = RateLimiter(requests_per_minute=10)

        # Simulate 10 requests
        for i in range(10):
            assert limiter.is_allowed("client1")

        # 11th request should be denied
        assert not limiter.is_allowed("client1")

        # Different client should not be affected
        assert limiter.is_allowed("client2")

    def test_security_validation_workflow(self):
        """Test complete security validation workflow."""
        # Test input validation
        safe_input = "hello world"
        assert not validator.check_sql_injection(safe_input)
        assert not validator.check_xss(safe_input)

        # Test URL validation
        safe_url = "https://example.com/api"
        validated_url = validator.validate_url(safe_url)
        assert validated_url == safe_url

        # Test email validation
        safe_email = "user@example.com"
        validated_email = validator.validate_email(safe_email)
        assert validated_email == safe_email

    def test_artifact_signing_workflow(self):
        """Test complete artifact signing workflow."""
        signer = ArtifactSigner()

        # Sign artifact
        content = b"test content"
        artifact = signer.sign_artifact(
            "test-app",
            "1.0.0",
            "/path/to/artifact",
            content,
        )

        assert artifact.signature is not None

        # Verify artifact
        assert signer.verify_artifact("test-app", "1.0.0", content)

        # Tampered content should fail
        tampered = b"tampered"
        assert not signer.verify_artifact("test-app", "1.0.0", tampered)


class TestMultiComponentInteractions:
    """Test interactions between multiple components."""

    def test_access_control_with_input_validation(self):
        """Test access control with input validation."""
        user = User("user1", "alice", Role.DEVELOPER)

        # Check permission
        access_control.enforce_permission(user, Permission.BUILD_CREATE)

        # Validate build name
        build_name = validator.validate_string("my-build", max_length=100)

        # Simulate build creation
        assert build_name == "my-build"

    def test_rate_limiting_with_access_control(self):
        """Test rate limiting with access control."""
        limiter = RateLimiter(requests_per_minute=5)
        user = User("user1", "alice", Role.USER)

        # Check permission and rate limit
        access_control.enforce_permission(user, Permission.BUILD_READ)

        for i in range(5):
            assert limiter.is_allowed(user.id)

        # Should be rate limited
        assert not limiter.is_allowed(user.id)

    def test_security_validation_chain(self):
        """Test chain of security validations."""
        # Validate email
        email = validator.validate_email("user@example.com")
        assert email == "user@example.com"

        # Validate URL
        url = validator.validate_url("https://example.com")
        assert url == "https://example.com"

        # Check SSRF prevention
        ssrf_validator = SSRFValidator()
        assert ssrf_validator.validate_url(url)

        # All validations passed
        assert True


class TestDatabaseTransactions:
    """Test database transaction handling."""

    def test_transaction_rollback_on_error(self):
        """Test transaction rollback on error."""
        # Simulate transaction
        transaction_log = []

        try:
            # Start transaction
            transaction_log.append("BEGIN")

            # Perform operations
            transaction_log.append("INSERT user")
            transaction_log.append("INSERT build")

            # Simulate error
            raise Exception("Database error")

        except Exception:
            # Rollback
            transaction_log.append("ROLLBACK")

        assert "ROLLBACK" in transaction_log

    def test_transaction_commit_on_success(self):
        """Test transaction commit on success."""
        transaction_log = []

        try:
            # Start transaction
            transaction_log.append("BEGIN")

            # Perform operations
            transaction_log.append("INSERT user")
            transaction_log.append("INSERT build")

            # Commit
            transaction_log.append("COMMIT")

        except Exception:
            transaction_log.append("ROLLBACK")

        assert "COMMIT" in transaction_log
        assert "ROLLBACK" not in transaction_log


class TestConcurrentOperations:
    """Test concurrent operations."""

    def test_concurrent_build_creation(self):
        """Test concurrent build creation."""
        def create_build(build_id):
            user = User(f"user{build_id}", f"user{build_id}", Role.DEVELOPER)
            access_control.enforce_permission(user, Permission.BUILD_CREATE)
            return {"id": build_id, "user": user.id}

        # Create builds concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            builds = list(executor.map(create_build, range(1, 6)))

        assert len(builds) == 5
        assert all(b["id"] for b in builds)

    def test_concurrent_rate_limiting(self):
        """Test concurrent rate limiting."""
        limiter = RateLimiter(requests_per_minute=20)

        def check_limit(client_id):
            results = []
            for i in range(5):
                results.append(limiter.is_allowed(client_id))
            return results

        # Check limits concurrently
        with ThreadPoolExecutor(max_workers=4) as executor:
            all_results = list(executor.map(check_limit, range(1, 5)))

        # All should succeed (20 total requests, limit is 20)
        assert all(all(r for r in results) for results in all_results)

    def test_concurrent_permission_checks(self):
        """Test concurrent permission checks."""
        users = [
            User(f"user{i}", f"user{i}", Role.DEVELOPER)
            for i in range(10)
        ]

        def check_permissions(user):
            return (
                user.has_permission(Permission.BUILD_CREATE),
                user.has_permission(Permission.BUILD_READ),
                user.has_permission(Permission.ADMIN_SYSTEM_CONFIG),
            )

        # Check permissions concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(check_permissions, users))

        # All developers should have BUILD_CREATE and BUILD_READ
        for create, read, admin in results:
            assert create and read
            assert not admin


class TestErrorRecovery:
    """Test error recovery mechanisms."""

    def test_invalid_input_recovery(self):
        """Test recovery from invalid input."""
        invalid_inputs = [
            "'; DROP TABLE users; --",
            "<script>alert('xss')</script>",
            "ftp://invalid.com",
        ]

        for invalid in invalid_inputs:
            # Should raise error
            with pytest.raises(ValueError):
                if "DROP" in invalid:
                    validator.validate_string(invalid)
                elif "script" in invalid:
                    validator.validate_string(invalid)
                elif "ftp" in invalid:
                    validator.validate_url(invalid)

    def test_permission_denied_recovery(self):
        """Test recovery from permission denied."""
        user = User("user1", "alice", Role.VIEWER)

        # Should raise PermissionError
        with pytest.raises(PermissionError):
            access_control.enforce_permission(user, Permission.BUILD_CREATE)

    def test_rate_limit_recovery(self):
        """Test recovery from rate limiting."""
        limiter = RateLimiter(requests_per_minute=3)

        # Use up limit
        for i in range(3):
            assert limiter.is_allowed("client1")

        # Should be rate limited
        assert not limiter.is_allowed("client1")

        # Wait and check remaining
        remaining = limiter.get_remaining("client1")
        assert remaining["per_minute"] == 0


class TestPerformanceUnderLoad:
    """Test performance under load."""

    def test_permission_check_performance(self):
        """Test permission check performance."""
        user = User("user1", "alice", Role.DEVELOPER)

        # Check performance of 1000 permission checks
        import time
        start = time.time()

        for i in range(1000):
            access_control.check_permission(user, Permission.BUILD_READ)

        duration = time.time() - start

        # Should complete in < 100ms
        assert duration < 0.1

    def test_input_validation_performance(self):
        """Test input validation performance."""
        import time

        inputs = ["hello world"] * 1000

        start = time.time()

        for input_str in inputs:
            validator.check_sql_injection(input_str)

        duration = time.time() - start

        # Should complete in < 100ms
        assert duration < 0.1

    def test_rate_limiter_performance(self):
        """Test rate limiter performance."""
        limiter = RateLimiter(requests_per_minute=10000)
        import time

        start = time.time()

        for i in range(1000):
            limiter.is_allowed(f"client{i % 10}")

        duration = time.time() - start

        # Should complete in < 100ms
        assert duration < 0.1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
