"""
Comprehensive error handling utilities for CrucibAI
Provides structured error handling, logging, and recovery strategies
"""

import logging
from typing import Optional, Dict, Any, Callable
from fastapi import HTTPException
from enum import Enum
import traceback
import asyncio

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CrucibError(Exception):
    """Base exception class for CrucibAI"""

    def __init__(
        self,
        message: str,
        error_code: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
        recoverable: bool = False,
    ):
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.status_code = status_code
        self.details = details or {}
        self.recoverable = recoverable
        super().__init__(self.message)


class ValidationError(CrucibError):
    """Raised when input validation fails"""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            severity=ErrorSeverity.LOW,
            status_code=400,
            details=details,
            recoverable=True,
        )


class AuthenticationError(CrucibError):
    """Raised when authentication fails"""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            error_code="AUTH_ERROR",
            severity=ErrorSeverity.MEDIUM,
            status_code=401,
            recoverable=False,
        )


class AuthorizationError(CrucibError):
    """Raised when user lacks permissions"""

    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            message=message,
            error_code="AUTHZ_ERROR",
            severity=ErrorSeverity.MEDIUM,
            status_code=403,
            recoverable=False,
        )


class NotFoundError(CrucibError):
    """Raised when resource is not found"""

    def __init__(self, resource: str, identifier: str):
        super().__init__(
            message=f"{resource} not found: {identifier}",
            error_code="NOT_FOUND",
            severity=ErrorSeverity.LOW,
            status_code=404,
            details={"resource": resource, "identifier": identifier},
            recoverable=True,
        )


class ConflictError(CrucibError):
    """Raised when resource conflict occurs"""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="CONFLICT",
            severity=ErrorSeverity.MEDIUM,
            status_code=409,
            details=details,
            recoverable=True,
        )


class RateLimitError(CrucibError):
    """Raised when rate limit is exceeded"""

    def __init__(self, retry_after: int = 60):
        super().__init__(
            message=f"Rate limit exceeded. Retry after {retry_after} seconds",
            error_code="RATE_LIMIT",
            severity=ErrorSeverity.LOW,
            status_code=429,
            details={"retry_after": retry_after},
            recoverable=True,
        )


class ExternalServiceError(CrucibError):
    """Raised when external service fails"""

    def __init__(self, service: str, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=f"{service} service error: {message}",
            error_code="EXTERNAL_SERVICE_ERROR",
            severity=ErrorSeverity.HIGH,
            status_code=503,
            details={**(details or {}), "service": service},
            recoverable=True,
        )


class DatabaseError(CrucibError):
    """Raised when database operation fails"""

    def __init__(self, operation: str, message: str):
        super().__init__(
            message=f"Database {operation} failed: {message}",
            error_code="DATABASE_ERROR",
            severity=ErrorSeverity.HIGH,
            status_code=500,
            details={"operation": operation},
            recoverable=True,
        )


class ProcessingError(CrucibError):
    """Raised when processing fails"""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message=message,
            error_code="PROCESSING_ERROR",
            severity=ErrorSeverity.MEDIUM,
            status_code=500,
            details=details,
            recoverable=True,
        )


class TimeoutError(CrucibError):
    """Raised when operation times out"""

    def __init__(self, operation: str, timeout_seconds: int):
        super().__init__(
            message=f"{operation} timed out after {timeout_seconds} seconds",
            error_code="TIMEOUT",
            severity=ErrorSeverity.MEDIUM,
            status_code=504,
            details={"operation": operation, "timeout": timeout_seconds},
            recoverable=True,
        )


def log_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
) -> None:
    """
    Log error with full context and traceback

    Args:
        error: The exception to log
        context: Additional context information
        user_id: User ID for audit trail
    """
    error_info = {
        "error_type": type(error).__name__,
        "message": str(error),
        "traceback": traceback.format_exc(),
        **(context or {}),
        **({"user_id": user_id} if user_id else {}),
    }

    if isinstance(error, CrucibError):
        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"CRITICAL ERROR: {error_info}")
        elif error.severity == ErrorSeverity.HIGH:
            logger.error(f"HIGH SEVERITY ERROR: {error_info}")
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"MEDIUM SEVERITY ERROR: {error_info}")
        else:
            logger.info(f"LOW SEVERITY ERROR: {error_info}")
    else:
        logger.error(f"UNEXPECTED ERROR: {error_info}")


async def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    *args,
    **kwargs,
) -> Any:
    """
    Retry a function with exponential backoff

    Args:
        func: Async function to retry
        max_retries: Maximum number of retries
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        *args, **kwargs: Arguments to pass to func

    Returns:
        Result of func if successful

    Raises:
        The last exception if all retries fail
    """
    last_error = None

    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                delay = min(base_delay * (2**attempt), max_delay)
                logger.warning(
                    f"Attempt {attempt + 1} failed, retrying in {delay}s: {str(e)}"
                )
                await asyncio.sleep(delay)
            else:
                logger.error(f"All {max_retries} retries failed: {str(e)}")

    raise last_error


def to_http_exception(error: Exception) -> HTTPException:
    """
    Convert CrucibError to HTTPException

    Args:
        error: Exception to convert

    Returns:
        HTTPException with appropriate status code and detail
    """
    if isinstance(error, CrucibError):
        return HTTPException(
            status_code=error.status_code,
            detail={
                "error_code": error.error_code,
                "message": error.message,
                "details": error.details,
                "recoverable": error.recoverable,
            },
        )
    else:
        return HTTPException(
            status_code=500,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "recoverable": False,
            },
        )


def create_error_response(
    error: Exception, request_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a structured error response

    Args:
        error: The exception
        request_id: Request ID for tracking

    Returns:
        Structured error response dict
    """
    if isinstance(error, CrucibError):
        return {
            "success": False,
            "error": {
                "code": error.error_code,
                "message": error.message,
                "severity": error.severity.value,
                "details": error.details,
                "recoverable": error.recoverable,
                "request_id": request_id,
            },
        }
    else:
        return {
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "severity": ErrorSeverity.HIGH.value,
                "recoverable": False,
                "request_id": request_id,
            },
        }


# Error recovery strategies
async def recover_from_external_service_error(
    service: str, fallback_func: Optional[Callable] = None, *args, **kwargs
) -> Any:
    """
    Attempt to recover from external service error

    Args:
        service: Name of the service that failed
        fallback_func: Optional fallback function to call
        *args, **kwargs: Arguments for fallback function

    Returns:
        Result from fallback function or None
    """
    logger.warning(f"Attempting recovery from {service} failure")

    if fallback_func:
        try:
            return (
                await fallback_func(*args, **kwargs)
                if asyncio.iscoroutinefunction(fallback_func)
                else fallback_func(*args, **kwargs)
            )
        except Exception as e:
            logger.error(f"Fallback recovery failed: {str(e)}")
            return None

    return None


def safe_dict_access(d: Dict, path: str, default: Any = None) -> Any:
    """
    Safely access nested dict values

    Args:
        d: Dictionary to access
        path: Dot-separated path (e.g., "user.profile.name")
        default: Default value if path not found

    Returns:
        Value at path or default
    """
    try:
        keys = path.split(".")
        value = d
        for key in keys:
            value = value[key]
        return value
    except (KeyError, TypeError, AttributeError):
        return default
