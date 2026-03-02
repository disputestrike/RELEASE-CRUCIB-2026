"""Security headers middleware"""
from fastapi import Request
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
import secrets

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Content Security Policy - strict, no unsafe-inline
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'wasm-unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self' https://api.cerebras.ai https://api.anthropic.com; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Enable XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions policy (formerly Feature Policy)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )
        
        # HSTS (only in production)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF token validation middleware"""
    
    CSRF_TOKEN_LENGTH = 32
    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
    
    async def dispatch(self, request: Request, call_next):
        # Skip CSRF check for safe methods
        if request.method in self.SAFE_METHODS:
            response = await call_next(request)
            # Generate and set CSRF token in response
            csrf_token = secrets.token_urlsafe(self.CSRF_TOKEN_LENGTH)
            response.set_cookie(
                "X-CSRF-Token",
                csrf_token,
                httponly=False,  # Must be readable by JS
                secure=True,
                samesite="Strict",
                max_age=3600
            )
            return response
        
        # For state-changing methods, validate CSRF token
        csrf_token_from_header = request.headers.get("X-CSRF-Token")
        csrf_token_from_cookie = request.cookies.get("X-CSRF-Token")
        
        if not csrf_token_from_header or csrf_token_from_header != csrf_token_from_cookie:
            return Response(
                content={"error": "CSRF token validation failed"},
                status_code=403
            )
        
        response = await call_next(request)
        return response
