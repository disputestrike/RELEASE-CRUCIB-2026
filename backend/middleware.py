"""
Advanced middleware for CrucibAI
Includes rate limiting, security headers, CORS, and request tracking
"""

import asyncio
import logging
import os
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Callable, Dict, Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Stricter limits for auth/payment (per path, per identifier)
STRICT_RATE_LIMITS: Dict[str, int] = {
    "/api/auth/register": 5,
    "/api/auth/login": 20,
    "/api/stripe/create-checkout-session": 10,
}


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """When HTTPS_REDIRECT=1, redirect HTTP to HTTPS using X-Forwarded-Proto (for production behind proxy)."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if os.environ.get("HTTPS_REDIRECT", "").strip().lower() not in (
            "1",
            "true",
            "yes",
        ):
            return await call_next(request)
        proto = (
            (request.headers.get("X-Forwarded-Proto") or request.url.scheme or "")
            .strip()
            .lower()
        )
        if proto == "https":
            return await call_next(request)
        host = (
            request.headers.get("X-Forwarded-Host")
            or request.headers.get("Host")
            or request.url.netloc
            or "localhost"
        )
        url = f"https://{host}{request.url.path}"
        if request.url.query:
            url += f"?{request.url.query}"
        return RedirectResponse(url=url, status_code=301)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting: per-client-IP (X-Forwarded-For aware) plus per-user JWT when Bearer is valid.
    Stricter limits for auth/payment paths (always keyed by IP for credential-stuffing fairness).
    Env: RATE_LIMIT_PER_MINUTE (user bucket, default passed in), RATE_LIMIT_PER_IP_PER_MINUTE (optional).
    """

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.by_ip: Dict[str, list] = defaultdict(list)
        self.by_user: Dict[str, list] = defaultdict(list)
        self.strict_times: Dict[str, list] = defaultdict(list)

    @staticmethod
    def _client_ip(request: Request) -> str:
        xff = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
        if xff:
            return xff
        return (request.client.host if request.client else "") or "unknown"

    @staticmethod
    def _jwt_user_id(request: Request) -> Optional[str]:
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None
        token = auth[7:].strip()
        if not token:
            return None
        secret = os.environ.get("JWT_SECRET")
        if not secret:
            return None
        try:
            import jwt

            algo = (os.environ.get("JWT_ALGORITHM") or "HS256").strip() or "HS256"
            payload = jwt.decode(token, secret, algorithms=[algo])
            uid = payload.get("user_id")
            return str(uid) if uid is not None else None
        except Exception:
            return None

    def _ip_limit(self) -> int:
        raw = (os.environ.get("RATE_LIMIT_PER_IP_PER_MINUTE") or "").strip()
        if raw.isdigit():
            return max(1, int(raw))
        return max(self.requests_per_minute * 3, 120)

    def _prune(
        self, bucket: Dict[str, list], key: str, now: float, window: float = 60.0
    ) -> None:
        cutoff = now - window
        bucket[key] = [t for t in bucket[key] if t > cutoff]

    def _under(self, bucket: Dict[str, list], key: str, limit: int, now: float) -> bool:
        self._prune(bucket, key, now)
        return len(bucket[key]) < limit

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if os.environ.get("CRUCIBAI_DEV", "").strip().lower() in ("1", "true", "yes"):
            return await call_next(request)

        path = (request.url.path or "").rstrip("/")
        if not path.startswith("/api/"):
            path_for_key = path
        else:
            path_for_key = "/api/" + path[4:].split("?")[0].rstrip("/")

        now = time.time()
        ip_key = f"ip:{self._client_ip(request)}"
        user_id = self._jwt_user_id(request)
        limit_ip = self._ip_limit()
        limit_user = self.requests_per_minute

        strict_limit = STRICT_RATE_LIMITS.get(path_for_key)
        if strict_limit is not None:
            strict_key = f"strict:{path_for_key}:{ip_key}"
            if not self._under(self.strict_times, strict_key, strict_limit, now):
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "message": f"Maximum {strict_limit} requests per minute for this endpoint",
                        "retry_after": 60,
                    },
                )
            self.strict_times[strict_key].append(now)

        if not self._under(self.by_ip, ip_key, limit_ip, now):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {limit_ip} requests per minute from this network",
                    "retry_after": 60,
                },
            )

        user_key = f"user:{user_id}" if user_id else None
        if user_key and not self._under(self.by_user, user_key, limit_user, now):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {limit_user} requests per minute for this account",
                    "retry_after": 60,
                },
            )

        self.by_ip[ip_key].append(now)
        if user_key:
            self.by_user[user_key].append(now)

        response = await call_next(request)
        self._prune(self.by_ip, ip_key, time.time())
        response.headers["X-RateLimit-Limit-IP"] = str(limit_ip)
        rem_ip = max(0, limit_ip - len(self.by_ip[ip_key]))
        response.headers["X-RateLimit-Remaining-IP"] = str(rem_ip)
        if user_key:
            self._prune(self.by_user, user_key, time.time())
            rem_u = max(0, limit_user - len(self.by_user[user_key]))
            response.headers["X-RateLimit-Limit"] = str(limit_user)
            response.headers["X-RateLimit-Remaining"] = str(min(rem_ip, rem_u))
        else:
            response.headers["X-RateLimit-Limit"] = str(limit_ip)
            response.headers["X-RateLimit-Remaining"] = str(rem_ip)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        # NOTE: X-Frame-Options is intentionally set to SAMEORIGIN (not DENY)
        # because Sandpack renders previews inside iframes on the same origin.
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        # SECURITY: CSP policy for React frontend + Sandpack preview
        # Sandpack requires: frame-src for iframes, worker-src for web workers,
        # script-src 'unsafe-eval' for the bundler, and wss: for HMR websockets.
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://*.codesandbox.io https://sandpack-bundler.codesandbox.io https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://*.codesandbox.io https://cdn.jsdelivr.net; "
            "img-src 'self' data: https: blob:; "
            "font-src 'self' data: https://fonts.gstatic.com https://*.codesandbox.io; "
            "connect-src 'self' https: wss: ws:; "
            "frame-src 'self' https://*.codesandbox.io https://sandpack-bundler.codesandbox.io blob:; "
            "child-src 'self' https://*.codesandbox.io blob:; "
            "worker-src 'self' blob: https://*.codesandbox.io; "
            "frame-ancestors 'self'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), " "microphone=(), " "camera=(), " "payment=()"
        )

        return response


class RequestTrackerMiddleware(BaseHTTPMiddleware):
    """
    Track requests for logging and monitoring
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID (accept inbound header or emit UUID for log/metrics correlation)
        request_id = (request.headers.get("X-Request-ID") or "").strip() or str(
            uuid.uuid4()
        )
        request.state.request_id = request_id
        tenant_hdr = (request.headers.get("X-Tenant-ID") or "").strip()

        bind_http_request_context = None
        clear_http_request_context = None
        log_request_event = None
        observe_http_request = None
        try:
            from orchestration.observability import bind_http_request_context as _bind
            from orchestration.observability import clear_http_request_context as _clear
            from orchestration.observability import log_request_event as _log_ev
            from orchestration.observability import observe_http_request as _observe

            bind_http_request_context = _bind
            clear_http_request_context = _clear
            log_request_event = _log_ev
            observe_http_request = _observe
        except Exception:
            pass

        if bind_http_request_context:
            bind_http_request_context(
                request_id=request_id,
                trace_id=str(uuid.uuid4()),
                tenant_id=tenant_hdr,
            )

        start_time = time.time()

        logger.info(
            f"[{request_id}] {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )
        if log_request_event:
            log_request_event(
                logger,
                "http_request_start",
                method=request.method,
                path=request.url.path,
            )

        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            logger.error(f"[{request_id}] Request failed: {str(e)}")
            if observe_http_request:
                try:
                    observe_http_request(request.method, status_code)
                except Exception:
                    pass
            if clear_http_request_context:
                try:
                    clear_http_request_context()
                except Exception:
                    pass
            raise

        duration = time.time() - start_time

        if observe_http_request:
            try:
                observe_http_request(request.method, status_code)
            except Exception:
                pass

        logger.info(
            f"[{request_id}] {request.method} {request.url.path} "
            f"completed with {response.status_code} in {duration:.3f}s"
        )
        if log_request_event:
            log_request_event(
                logger,
                "http_request_complete",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_s=round(duration, 4),
            )

        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration:.3f}s"

        if clear_http_request_context:
            try:
                clear_http_request_context()
            except Exception:
                pass

        return response


class CORSMiddleware(BaseHTTPMiddleware):
    """
    Enhanced CORS middleware with configurable origins
    """

    def __init__(
        self,
        app,
        allow_origins: list = None,
        allow_methods: list = None,
        allow_headers: list = None,
        allow_credentials: bool = True,
        max_age: int = 3600,
    ):
        super().__init__(app)
        # CRITICAL: Never allow * with credentials in production
        if allow_origins is None:
            allow_origins = os.environ.get(
                "CORS_ORIGINS", "http://localhost:3000"
            ).split(",")
            if "*" in allow_origins and allow_credentials:
                logger.error(
                    "SECURITY: CORS with allow_credentials=True and allow_origins=['*'] is a vulnerability!"
                )
                allow_origins = ["http://localhost:3000"]
        self.allow_origins = allow_origins
        self.allow_methods = allow_methods or [
            "GET",
            "POST",
            "PUT",
            "DELETE",
            "OPTIONS",
            "PATCH",
        ]
        self.allow_headers = allow_headers or [
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "X-Request-ID",
            "Accept",
        ]
        self.allow_credentials = allow_credentials
        self.max_age = max_age

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Handle preflight requests
        if request.method == "OPTIONS":
            return self._preflight_response(request)

        # Process request
        response = await call_next(request)

        # Add CORS headers
        self._add_cors_headers(response, request)

        return response

    def _preflight_response(self, request: Request) -> Response:
        """Handle CORS preflight requests"""
        response = Response()
        self._add_cors_headers(response, request)
        return response

    def _add_cors_headers(self, response: Response, request: Request) -> None:
        """Add CORS headers to response"""
        origin = request.headers.get("Origin")

        # Check if origin is allowed
        if self.allow_origins == ["*"]:
            response.headers["Access-Control-Allow-Origin"] = "*"
        elif origin in self.allow_origins:
            response.headers["Access-Control-Allow-Origin"] = origin

        response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
        response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)
        response.headers["Access-Control-Max-Age"] = str(self.max_age)

        if self.allow_credentials:
            response.headers["Access-Control-Allow-Credentials"] = "true"


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Validate requests for security and compliance
    """

    MAX_BODY_SIZE = 100 * 1024 * 1024  # 100MB

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check content length
        content_length = request.headers.get("Content-Length")
        if content_length and int(content_length) > self.MAX_BODY_SIZE:
            return JSONResponse(
                status_code=413,
                content={
                    "error": "Payload too large",
                    "message": f"Maximum payload size is {self.MAX_BODY_SIZE} bytes",
                },
            )

        # Check for suspicious headers
        if self._has_suspicious_headers(request):
            logger.warning(
                f"Suspicious request from {request.client.host if request.client else 'unknown'}"
            )
            return JSONResponse(status_code=400, content={"error": "Invalid request"})

        return await call_next(request)

    def _has_suspicious_headers(self, request: Request) -> bool:
        """Check for suspicious headers"""
        suspicious_patterns = [
            "../",
            "..\\",
            "<script",
            "javascript:",
            "onerror=",
            "onclick=",
        ]

        for header_value in request.headers.values():
            for pattern in suspicious_patterns:
                if pattern.lower() in header_value.lower():
                    return True

        return False


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Monitor performance and log slow requests
    """

    SLOW_REQUEST_THRESHOLD = 5.0  # 5 seconds

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        response = await call_next(request)
        duration = time.time() - start_time

        if duration > self.SLOW_REQUEST_THRESHOLD:
            logger.warning(
                f"Slow request: {request.method} {request.url.path} "
                f"took {duration:.3f}s (threshold: {self.SLOW_REQUEST_THRESHOLD}s)"
            )

        return response
