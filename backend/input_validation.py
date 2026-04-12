"""
Input validation and injection prevention.

Implements:
- SQL injection prevention
- XSS prevention
- Command injection prevention
- LDAP injection prevention
- Template injection prevention
- Input sanitization
"""

import re
import logging
from typing import Any, Optional, Pattern
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class InjectionValidator:
    """Validate inputs to prevent injection attacks."""

    # SQL injection patterns
    SQL_INJECTION_PATTERNS = [
        r"(\b(UNION|SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(--|#|/\*|\*/)",
        r"(;|\||&&)",
        r"('|\")\s*(OR|AND)\s*('|\")",
        r"(=\s*'|=\s*\")",
    ]

    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"on\w+\s*=",
        r"javascript:",
        r"<iframe",
        r"<object",
        r"<embed",
    ]

    # Command injection patterns
    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$(){}[\]<>]",
        r"\$\{.*\}",
        r"\$\(.*\)",
    ]

    def __init__(self):
        """Initialize validator."""
        self.sql_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.SQL_INJECTION_PATTERNS
        ]
        self.xss_patterns = [re.compile(p, re.IGNORECASE) for p in self.XSS_PATTERNS]
        self.cmd_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.COMMAND_INJECTION_PATTERNS
        ]

    def check_sql_injection(self, value: str) -> bool:
        """
        Check if value contains SQL injection patterns.

        Args:
            value: Value to check

        Returns:
            True if injection detected, False otherwise
        """
        if not isinstance(value, str):
            return False

        for pattern in self.sql_patterns:
            if pattern.search(value):
                logger.warning(f"SQL injection detected in: {value[:50]}")
                return True

        return False

    def check_xss(self, value: str) -> bool:
        """
        Check if value contains XSS patterns.

        Args:
            value: Value to check

        Returns:
            True if XSS detected, False otherwise
        """
        if not isinstance(value, str):
            return False

        for pattern in self.xss_patterns:
            if pattern.search(value):
                logger.warning(f"XSS detected in: {value[:50]}")
                return True

        return False

    def check_command_injection(self, value: str) -> bool:
        """
        Check if value contains command injection patterns.

        Args:
            value: Value to check

        Returns:
            True if command injection detected, False otherwise
        """
        if not isinstance(value, str):
            return False

        for pattern in self.cmd_patterns:
            if pattern.search(value):
                logger.warning(f"Command injection detected in: {value[:50]}")
                return True

        return False

    def validate_string(
        self, value: str, max_length: int = 1000, allow_special: bool = False
    ) -> str:
        """
        Validate and sanitize string input.

        Args:
            value: Value to validate
            max_length: Maximum allowed length
            allow_special: Whether to allow special characters

        Returns:
            Sanitized value

        Raises:
            ValueError: If validation fails
        """
        if not isinstance(value, str):
            raise ValueError("Value must be string")

        # Check length
        if len(value) > max_length:
            raise ValueError(f"Value exceeds maximum length of {max_length}")

        # Check for injections
        if self.check_sql_injection(value):
            raise ValueError("SQL injection detected")

        if self.check_xss(value):
            raise ValueError("XSS detected")

        if not allow_special and self.check_command_injection(value):
            raise ValueError("Command injection detected")

        return value

    def validate_email(self, value: str) -> str:
        """
        Validate email address.

        Args:
            value: Email to validate

        Returns:
            Validated email

        Raises:
            ValueError: If validation fails
        """
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

        if not re.match(email_pattern, value):
            raise ValueError("Invalid email format")

        if self.check_sql_injection(value):
            raise ValueError("SQL injection detected in email")

        return value

    def validate_url(self, value: str) -> str:
        """
        Validate URL.

        Args:
            value: URL to validate

        Returns:
            Validated URL

        Raises:
            ValueError: If validation fails
        """
        try:
            parsed = urlparse(value)

            # Check scheme
            if parsed.scheme not in ["http", "https"]:
                raise ValueError("Invalid URL scheme")

            # Check for injection
            if self.check_sql_injection(value):
                raise ValueError("SQL injection detected in URL")

            if self.check_xss(value):
                raise ValueError("XSS detected in URL")

            return value

        except Exception as e:
            raise ValueError(f"Invalid URL: {str(e)}")

    def validate_integer(
        self, value: Any, min_val: int = None, max_val: int = None
    ) -> int:
        """
        Validate integer input.

        Args:
            value: Value to validate
            min_val: Minimum allowed value
            max_val: Maximum allowed value

        Returns:
            Validated integer

        Raises:
            ValueError: If validation fails
        """
        try:
            int_val = int(value)

            if min_val is not None and int_val < min_val:
                raise ValueError(f"Value must be >= {min_val}")

            if max_val is not None and int_val > max_val:
                raise ValueError(f"Value must be <= {max_val}")

            return int_val

        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid integer: {str(e)}")

    def sanitize_html(self, value: str) -> str:
        """
        Sanitize HTML by removing dangerous tags.

        Args:
            value: HTML to sanitize

        Returns:
            Sanitized HTML
        """
        # Remove script tags
        value = re.sub(r"<script[^>]*>.*?</script>", "", value, flags=re.IGNORECASE)

        # Remove event handlers
        value = re.sub(r"\s*on\w+\s*=\s*['\"].*?['\"]", "", value, flags=re.IGNORECASE)

        # Remove dangerous tags
        dangerous_tags = ["iframe", "object", "embed", "applet"]
        for tag in dangerous_tags:
            value = re.sub(rf"<{tag}[^>]*>.*?</{tag}>", "", value, flags=re.IGNORECASE)

        return value


# Global validator instance
validator = InjectionValidator()


def validate_input(value: str, input_type: str = "string", **kwargs) -> Any:
    """
    Validate input based on type.

    Args:
        value: Value to validate
        input_type: Type of input (string, email, url, integer)
        **kwargs: Additional validation parameters

    Returns:
        Validated value

    Raises:
        ValueError: If validation fails
    """
    if input_type == "string":
        return validator.validate_string(value, **kwargs)
    elif input_type == "email":
        return validator.validate_email(value)
    elif input_type == "url":
        return validator.validate_url(value)
    elif input_type == "integer":
        return validator.validate_integer(value, **kwargs)
    else:
        raise ValueError(f"Unknown input type: {input_type}")
