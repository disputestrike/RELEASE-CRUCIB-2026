"""CSRF token utilities"""
import secrets
from typing import Optional

CSRF_TOKEN_LENGTH = 32

def generate_csrf_token() -> str:
    """Generate a new CSRF token"""
    return secrets.token_urlsafe(CSRF_TOKEN_LENGTH)

def validate_csrf_token(token_from_header: Optional[str], token_from_cookie: Optional[str]) -> bool:
    """Validate CSRF token from header against cookie"""
    if not token_from_header or not token_from_cookie:
        return False
    return token_from_header == token_from_cookie
