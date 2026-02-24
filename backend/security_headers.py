"""
Security headers and configuration middleware.

Implements:
- HSTS (HTTP Strict Transport Security)
- CSP (Content Security Policy)
- X-Content-Type-Options
- X-Frame-Options
- X-XSS-Protection
- Referrer-Policy
- Permissions-Policy
- Rate limiting
- CORS configuration
"""

import logging
from typing import Optional, List, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SecurityHeaders:
    """Security headers configuration."""

    # HSTS: Force HTTPS for 1 year
    HSTS = "max-age=31536000; includeSubDomains; preload"

    # CSP: Restrict content sources
    CSP = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://api.manus.im; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )

    # X-Content-Type-Options: Prevent MIME type sniffing
    X_CONTENT_TYPE_OPTIONS = "nosniff"

    # X-Frame-Options: Prevent clickjacking
    X_FRAME_OPTIONS = "DENY"

    # X-XSS-Protection: Enable XSS filter
    X_XSS_PROTECTION = "1; mode=block"

    # Referrer-Policy: Control referrer information
    REFERRER_POLICY = "strict-origin-when-cross-origin"

    # Permissions-Policy: Restrict browser features
    PERMISSIONS_POLICY = (
        "accelerometer=(), "
        "ambient-light-sensor=(), "
        "autoplay=(), "
        "battery=(), "
        "camera=(), "
        "display-capture=(), "
        "document-domain=(), "
        "encrypted-media=(), "
        "fullscreen=(), "
        "geolocation=(), "
        "gyroscope=(), "
        "magnetometer=(), "
        "microphone=(), "
        "midi=(), "
        "payment=(), "
        "usb=()"
    )

    @staticmethod
    def get_headers() -> Dict[str, str]:
        """Get all security headers."""
        return {
            "Strict-Transport-Security": SecurityHeaders.HSTS,
            "Content-Security-Policy": SecurityHeaders.CSP,
            "X-Content-Type-Options": SecurityHeaders.X_CONTENT_TYPE_OPTIONS,
            "X-Frame-Options": SecurityHeaders.X_FRAME_OPTIONS,
            "X-XSS-Protection": SecurityHeaders.X_XSS_PROTECTION,
            "Referrer-Policy": SecurityHeaders.REFERRER_POLICY,
            "Permissions-Policy": SecurityHeaders.PERMISSIONS_POLICY,
        }


class CORSConfig:
    """CORS configuration."""

    def __init__(
        self,
        allowed_origins: List[str] = None,
        allowed_methods: List[str] = None,
        allowed_headers: List[str] = None,
        expose_headers: List[str] = None,
        allow_credentials: bool = True,
        max_age: int = 3600,
    ):
        """
        Initialize CORS configuration.

        Args:
            allowed_origins: Allowed origins
            allowed_methods: Allowed HTTP methods
            allowed_headers: Allowed headers
            expose_headers: Exposed headers
            allow_credentials: Whether to allow credentials
            max_age: Max age for preflight cache
        """
        self.allowed_origins = allowed_origins or [
            "https://crucibai.com",
            "https://www.crucibai.com",
        ]
        self.allowed_methods = allowed_methods or ["GET", "POST", "PUT", "DELETE"]
        self.allowed_headers = allowed_headers or [
            "Content-Type",
            "Authorization",
            "X-Requested-With",
        ]
        self.expose_headers = expose_headers or ["Content-Type", "X-Total-Count"]
        self.allow_credentials = allow_credentials
        self.max_age = max_age

    def get_headers(self, origin: str) -> Dict[str, str]:
        """
        Get CORS headers for origin.

        Args:
            origin: Request origin

        Returns:
            CORS headers
        """
        headers = {}

        # Check if origin is allowed
        if origin in self.allowed_origins or "*" in self.allowed_origins:
            headers["Access-Control-Allow-Origin"] = origin
            headers["Access-Control-Allow-Methods"] = ", ".join(self.allowed_methods)
            headers["Access-Control-Allow-Headers"] = ", ".join(self.allowed_headers)
            headers["Access-Control-Expose-Headers"] = ", ".join(self.expose_headers)
            headers["Access-Control-Max-Age"] = str(self.max_age)

            if self.allow_credentials:
                headers["Access-Control-Allow-Credentials"] = "true"

        return headers


class RateLimiter:
    """Rate limiting implementation."""

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
        requests_per_day: int = 10000,
    ):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Max requests per minute
            requests_per_hour: Max requests per hour
            requests_per_day: Max requests per day
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.requests_per_day = requests_per_day

        # In-memory request tracking (use Redis in production)
        self.requests: Dict[str, List[datetime]] = {}

    def is_allowed(self, client_id: str) -> bool:
        """
        Check if request is allowed.

        Args:
            client_id: Client identifier (IP, user ID, etc.)

        Returns:
            True if request is allowed, False otherwise
        """
        now = datetime.utcnow()

        # Initialize client tracking
        if client_id not in self.requests:
            self.requests[client_id] = []

        # Clean old requests
        one_day_ago = now - timedelta(days=1)
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > one_day_ago
        ]

        # Check limits
        one_minute_ago = now - timedelta(minutes=1)
        one_hour_ago = now - timedelta(hours=1)

        requests_last_minute = sum(
            1 for req_time in self.requests[client_id]
            if req_time > one_minute_ago
        )
        requests_last_hour = sum(
            1 for req_time in self.requests[client_id]
            if req_time > one_hour_ago
        )
        requests_last_day = len(self.requests[client_id])

        # Check against limits
        if requests_last_minute >= self.requests_per_minute:
            logger.warning(
                f"Rate limit exceeded (per minute) for {client_id}",
                extra={"client_id": client_id, "limit": self.requests_per_minute},
            )
            return False

        if requests_last_hour >= self.requests_per_hour:
            logger.warning(
                f"Rate limit exceeded (per hour) for {client_id}",
                extra={"client_id": client_id, "limit": self.requests_per_hour},
            )
            return False

        if requests_last_day >= self.requests_per_day:
            logger.warning(
                f"Rate limit exceeded (per day) for {client_id}",
                extra={"client_id": client_id, "limit": self.requests_per_day},
            )
            return False

        # Record request
        self.requests[client_id].append(now)
        return True

    def get_remaining(self, client_id: str) -> Dict[str, int]:
        """
        Get remaining requests for client.

        Args:
            client_id: Client identifier

        Returns:
            Remaining requests by time window
        """
        now = datetime.utcnow()

        if client_id not in self.requests:
            return {
                "per_minute": self.requests_per_minute,
                "per_hour": self.requests_per_hour,
                "per_day": self.requests_per_day,
            }

        one_minute_ago = now - timedelta(minutes=1)
        one_hour_ago = now - timedelta(hours=1)

        requests_last_minute = sum(
            1 for req_time in self.requests[client_id]
            if req_time > one_minute_ago
        )
        requests_last_hour = sum(
            1 for req_time in self.requests[client_id]
            if req_time > one_hour_ago
        )
        requests_last_day = len(self.requests[client_id])

        return {
            "per_minute": max(0, self.requests_per_minute - requests_last_minute),
            "per_hour": max(0, self.requests_per_hour - requests_last_hour),
            "per_day": max(0, self.requests_per_day - requests_last_day),
        }


# Global instances
security_headers = SecurityHeaders()
cors_config = CORSConfig()
rate_limiter = RateLimiter()
