"""
Comprehensive security tests for all security implementations.

Tests:
- Access control and permissions
- Input validation and injection prevention
- Security headers
- SSRF prevention
- Artifact signing and verification
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from access_control import (
    User,
    Role,
    Permission,
    access_control,
    require_permission,
)
from input_validation import validator, validate_input
from security_headers import (
    SecurityHeaders,
    CORSConfig,
    RateLimiter,
)
from ssrf_prevention import SSRFValidator, SafeRequestHandler
from artifact_signing import ArtifactSigner, SBOMGenerator


class TestAccessControl:
    """Test access control system."""

    def test_user_has_permission(self):
        """Test user permission checking."""
        user = User("user1", "alice", Role.DEVELOPER)

        assert user.has_permission(Permission.BUILD_CREATE)
        assert user.has_permission(Permission.BUILD_READ)
        assert not user.has_permission(Permission.ADMIN_SYSTEM_CONFIG)

    def test_admin_has_all_permissions(self):
        """Test admin has all permissions."""
        user = User("admin1", "bob", Role.ADMIN)

        assert user.has_permission(Permission.BUILD_CREATE)
        assert user.has_permission(Permission.ADMIN_SYSTEM_CONFIG)
        assert user.has_permission(Permission.USER_MANAGE_ROLES)

    def test_viewer_has_limited_permissions(self):
        """Test viewer has limited permissions."""
        user = User("viewer1", "charlie", Role.VIEWER)

        assert user.has_permission(Permission.BUILD_READ)
        assert not user.has_permission(Permission.BUILD_CREATE)
        assert not user.has_permission(Permission.BUILD_DELETE)

    def test_permission_enforcement(self):
        """Test permission enforcement."""
        user = User("user1", "alice", Role.USER)

        # Should allow
        access_control.enforce_permission(user, Permission.BUILD_CREATE)

        # Should deny
        with pytest.raises(PermissionError):
            access_control.enforce_permission(user, Permission.ADMIN_SYSTEM_CONFIG)

    def test_custom_permissions(self):
        """Test custom permissions."""
        user = User("user1", "alice", Role.USER)
        user.custom_permissions.add(Permission.ANALYTICS_EXPORT)

        assert user.has_permission(Permission.ANALYTICS_EXPORT)

    def test_permission_decorator(self):
        """Test permission decorator."""

        @require_permission(Permission.BUILD_CREATE)
        def create_build(user):
            return "build_created"

        user = User("user1", "alice", Role.DEVELOPER)
        result = create_build(user)
        assert result == "build_created"

        # Should fail for user without permission
        user_no_perm = User("user2", "bob", Role.VIEWER)
        with pytest.raises(PermissionError):
            create_build(user_no_perm)


class TestInputValidation:
    """Test input validation and injection prevention."""

    def test_sql_injection_detection(self):
        """Test SQL injection detection."""
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin' --",
            "1; DELETE FROM users",
        ]

        for payload in malicious_inputs:
            assert validator.check_sql_injection(payload)

    def test_xss_detection(self):
        """Test XSS detection."""
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<iframe src='evil.com'></iframe>",
        ]

        for payload in malicious_inputs:
            assert validator.check_xss(payload)

    def test_command_injection_detection(self):
        """Test command injection detection."""
        malicious_inputs = [
            "; rm -rf /",
            "| cat /etc/passwd",
            "` whoami `",
            "$(whoami)",
        ]

        for payload in malicious_inputs:
            assert validator.check_command_injection(payload)

    def test_safe_input_validation(self):
        """Test safe input validation."""
        safe_inputs = [
            "hello world",
            "user@example.com",
            "https://example.com",
            "123",
        ]

        for payload in safe_inputs:
            assert not validator.check_sql_injection(payload)
            assert not validator.check_xss(payload)

    def test_email_validation(self):
        """Test email validation."""
        valid_emails = [
            "user@example.com",
            "test.user@example.co.uk",
        ]

        invalid_emails = [
            "invalid.email",
            "user@",
            "@example.com",
        ]

        for email in valid_emails:
            assert validator.validate_email(email) == email

        for email in invalid_emails:
            with pytest.raises(ValueError):
                validator.validate_email(email)

    def test_url_validation(self):
        """Test URL validation."""
        valid_urls = [
            "https://example.com",
            "http://example.com/path",
        ]

        invalid_urls = [
            "ftp://example.com",
            "not-a-url",
        ]

        for url in valid_urls:
            assert validator.validate_url(url) == url

        for url in invalid_urls:
            with pytest.raises(ValueError):
                validator.validate_url(url)

    def test_html_sanitization(self):
        """Test HTML sanitization."""
        dirty_html = "<p>Hello <script>alert('xss')</script></p>"
        clean_html = validator.sanitize_html(dirty_html)

        assert "<script>" not in clean_html
        assert "Hello" in clean_html


class TestSecurityHeaders:
    """Test security headers."""

    def test_hsts_header(self):
        """Test HSTS header."""
        headers = SecurityHeaders.get_headers()
        assert "Strict-Transport-Security" in headers
        assert "max-age=31536000" in headers["Strict-Transport-Security"]

    def test_csp_header(self):
        """Test CSP header."""
        headers = SecurityHeaders.get_headers()
        assert "Content-Security-Policy" in headers
        assert "default-src 'self'" in headers["Content-Security-Policy"]

    def test_x_frame_options_header(self):
        """Test X-Frame-Options header."""
        headers = SecurityHeaders.get_headers()
        assert headers["X-Frame-Options"] == "DENY"

    def test_cors_configuration(self):
        """Test CORS configuration."""
        cors = CORSConfig()
        headers = cors.get_headers("https://crucibai.com")

        assert "Access-Control-Allow-Origin" in headers
        assert headers["Access-Control-Allow-Origin"] == "https://crucibai.com"

    def test_cors_origin_validation(self):
        """Test CORS origin validation."""
        cors = CORSConfig()
        headers = cors.get_headers("https://evil.com")

        # Should not allow unknown origin
        assert "Access-Control-Allow-Origin" not in headers


class TestRateLimiting:
    """Test rate limiting."""

    def test_rate_limit_per_minute(self):
        """Test rate limiting per minute."""
        limiter = RateLimiter(requests_per_minute=5)

        # Should allow first 5 requests
        for i in range(5):
            assert limiter.is_allowed("client1")

        # Should deny 6th request
        assert not limiter.is_allowed("client1")

    def test_rate_limit_multiple_clients(self):
        """Test rate limiting for multiple clients."""
        limiter = RateLimiter(requests_per_minute=5)

        # Client 1 should be limited
        for i in range(5):
            assert limiter.is_allowed("client1")
        assert not limiter.is_allowed("client1")

        # Client 2 should not be affected
        assert limiter.is_allowed("client2")

    def test_remaining_requests(self):
        """Test getting remaining requests."""
        limiter = RateLimiter(requests_per_minute=10)

        remaining = limiter.get_remaining("client1")
        assert remaining["per_minute"] == 10

        limiter.is_allowed("client1")
        remaining = limiter.get_remaining("client1")
        assert remaining["per_minute"] == 9


class TestSSRFPrevention:
    """Test SSRF prevention."""

    def test_private_ip_detection(self):
        """Test private IP detection."""
        validator_obj = SSRFValidator()

        private_ips = [
            "127.0.0.1",
            "192.168.1.1",
            "10.0.0.1",
            "172.16.0.1",
        ]

        for ip in private_ips:
            assert validator_obj.is_private_ip(ip)

    def test_public_ip_allowed(self):
        """Test public IP is allowed."""
        validator_obj = SSRFValidator()

        public_ips = [
            "8.8.8.8",
            "1.1.1.1",
        ]

        for ip in public_ips:
            assert not validator_obj.is_private_ip(ip)

    def test_dangerous_port_detection(self):
        """Test dangerous port detection."""
        validator_obj = SSRFValidator()

        dangerous_ports = [22, 23, 25, 3306, 5432]
        for port in dangerous_ports:
            assert validator_obj.is_dangerous_port(port)

    def test_safe_port_allowed(self):
        """Test safe port is allowed."""
        validator_obj = SSRFValidator()

        safe_ports = [80, 443, 8000, 8080]
        for port in safe_ports:
            assert not validator_obj.is_dangerous_port(port)

    def test_whitelist_validation(self):
        """Test whitelist validation."""
        validator_obj = SSRFValidator(
            allowed_domains={"api.example.com"}
        )

        # Whitelisted domain should pass
        assert validator_obj.validate_url("https://api.example.com/data")

    def test_private_ip_blocked(self):
        """Test private IP is blocked."""
        validator_obj = SSRFValidator()

        # Should fail for private IPs
        assert not validator_obj.validate_url("http://192.168.1.1")
        assert not validator_obj.validate_url("http://localhost")


class TestArtifactSigning:
    """Test artifact signing and verification."""

    def test_artifact_signing(self):
        """Test artifact signing."""
        signer = ArtifactSigner()
        content = b"test artifact content"

        artifact = signer.sign_artifact(
            "test-app",
            "1.0.0",
            "/path/to/artifact",
            content,
        )

        assert artifact.name == "test-app"
        assert artifact.version == "1.0.0"
        assert artifact.signature is not None

    def test_artifact_verification(self):
        """Test artifact verification."""
        signer = ArtifactSigner()
        content = b"test artifact content"

        # Sign artifact
        signer.sign_artifact(
            "test-app",
            "1.0.0",
            "/path/to/artifact",
            content,
        )

        # Verify artifact
        assert signer.verify_artifact("test-app", "1.0.0", content)

    def test_artifact_tampering_detection(self):
        """Test detection of tampered artifacts."""
        signer = ArtifactSigner()
        content = b"test artifact content"

        # Sign artifact
        signer.sign_artifact(
            "test-app",
            "1.0.0",
            "/path/to/artifact",
            content,
        )

        # Try to verify with tampered content
        tampered_content = b"tampered content"
        assert not signer.verify_artifact("test-app", "1.0.0", tampered_content)

    def test_sbom_generation(self):
        """Test SBOM generation."""
        sbom_gen = SBOMGenerator()

        sbom_gen.add_component("react", "18.0.0", license="MIT")
        sbom_gen.add_component("express", "4.18.0", license="MIT")

        sbom = sbom_gen.generate_sbom("test-app", "1.0.0")

        assert sbom["metadata"]["component"]["name"] == "test-app"
        assert len(sbom["components"]) == 2

    def test_sbom_export_json(self):
        """Test SBOM export to JSON."""
        sbom_gen = SBOMGenerator()
        sbom_gen.add_component("react", "18.0.0")

        json_sbom = sbom_gen.export_sbom_json("test-app", "1.0.0")

        assert "test-app" in json_sbom
        assert "react" in json_sbom


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
