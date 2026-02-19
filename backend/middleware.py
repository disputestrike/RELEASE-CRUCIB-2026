"""
Advanced middleware for CrucibAI
Includes rate limiting, security headers, CORS, and request tracking
"""

import os
import time
import logging
from typing import Dict, Optional, Callable
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi import Request, Response
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
import asyncio

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
        if os.environ.get("HTTPS_REDIRECT", "").strip().lower() not in ("1", "true", "yes"):
            return await call_next(request)
        proto = (request.headers.get("X-Forwarded-Proto") or request.url.scheme or "").strip().lower()
        if proto == "https":
            return await call_next(request)
        host = request.headers.get("X-Forwarded-Host") or request.headers.get("Host") or request.url.netloc or "localhost"
        url = f"https://{host}{request.url.path}"
        if request.url.query:
            url += f"?{request.url.query}"
        return RedirectResponse(url=url, status_code=301)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with per-IP and per-user tracking.
    Stricter limits for auth and payment endpoints (register, login, checkout).
    """
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_times: Dict[str, list] = defaultdict(list)
        self.strict_times: Dict[str, list] = defaultdict(list)
        self.cleanup_task = None
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = (request.url.path or "").rstrip("/")
        if not path.startswith("/api/"):
            path_for_key = path
        else:
            path_for_key = "/api/" + path[4:].split("?")[0].rstrip("/")
        identifier = self._get_identifier(request)
        strict_limit = STRICT_RATE_LIMITS.get(path_for_key)

        # Stricter limit for auth/payment
        if strict_limit is not None:
            key = f"strict_{path_for_key}_{identifier}"
            if not self._check_limit(key, strict_limit, self.strict_times):
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "message": f"Maximum {strict_limit} requests per minute for this endpoint",
                        "retry_after": 60
                    }
                )
            self.strict_times[key].append(time.time())
        
        # Global rate limit
        if not self._check_rate_limit(identifier):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Maximum {self.requests_per_minute} requests per minute allowed",
                    "retry_after": 60
                }
            )
        
        self.request_times[identifier].append(time.time())
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            self.requests_per_minute - len(self.request_times[identifier])
        )
        return response
    
    def _check_limit(self, key: str, limit: int, bucket: Dict[str, list]) -> bool:
        now = time.time()
        minute_ago = now - 60
        bucket[key] = [t for t in bucket[key] if t > minute_ago]
        return len(bucket[key]) < limit

    def _get_identifier(self, request: Request) -> str:
        """Get unique identifier for rate limiting"""
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]
        client_ip = request.client.host if request.client else "unknown"
        return f"ip_{client_ip}"
    
    def _check_rate_limit(self, identifier: str) -> bool:
        """Check if identifier has exceeded rate limit"""
        now = time.time()
        minute_ago = now - 60
        self.request_times[identifier] = [
            t for t in self.request_times[identifier] if t > minute_ago
        ]
        return len(self.request_times[identifier]) < self.requests_per_minute

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        # SECURITY: Strict CSP without unsafe-inline/unsafe-eval
        # For production, use nonces or hashes for inline scripts
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "  # No unsafe-inline or unsafe-eval
            "style-src 'self'; "   # No unsafe-inline
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=()"
        )
        
        return response

class RequestTrackerMiddleware(BaseHTTPMiddleware):
    """
    Track requests for logging and monitoring
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = request.headers.get("X-Request-ID", f"{int(time.time() * 1000)}")
        request.state.request_id = request_id
        
        # Record start time
        start_time = time.time()
        
        # Log request
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )
        
        try:
            response = await call_next(request)
        except Exception as e:
            logger.error(f"[{request_id}] Request failed: {str(e)}")
            raise
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log response
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} "
            f"completed with {response.status_code} in {duration:.3f}s"
        )
        
        # Add headers
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time"] = f"{duration:.3f}s"
        
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
        max_age: int = 3600
    ):
        super().__init__(app)
        # CRITICAL: Never allow * with credentials in production
        if allow_origins is None:
            allow_origins = os.environ.get('CORS_ORIGINS', 'http://localhost:3000').split(',')
            if "*" in allow_origins and allow_credentials:
                logger.error("SECURITY: CORS with allow_credentials=True and allow_origins=['*'] is a vulnerability!")
                allow_origins = ["http://localhost:3000"]
        self.allow_origins = allow_origins
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
        self.allow_headers = allow_headers or [
            "Content-Type",
            "Authorization",
            "X-Requested-With",
            "X-Request-ID",
            "Accept"
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
                    "message": f"Maximum payload size is {self.MAX_BODY_SIZE} bytes"
                }
            )
        
        # Check for suspicious headers
        if self._has_suspicious_headers(request):
            logger.warning(f"Suspicious request from {request.client.host if request.client else 'unknown'}")
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid request"}
            )
        
        return await call_next(request)
    
    def _has_suspicious_headers(self, request: Request) -> bool:
        """Check for suspicious headers"""
        suspicious_patterns = [
            "../",
            "..\\",
            "<script",
            "javascript:",
            "onerror=",
            "onclick="
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
