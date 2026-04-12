"""
Endpoint wrapper decorator to apply error handling, logging, and validation
to all endpoints automatically
"""

import time
import traceback
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, Optional

from error_handlers import (
    AuthenticationError,
    CrucibError,
    DatabaseError,
    ExternalServiceError,
    ValidationError,
    log_error,
    to_http_exception,
)
from fastapi import HTTPException, Request
from structured_logging import (
    get_error_logger,
    get_performance_logger,
    get_request_logger,
    log_performance,
)

request_logger = get_request_logger()
error_logger = get_error_logger()
performance_logger = get_performance_logger()


def safe_endpoint(
    operation_name: str,
    require_auth: bool = False,
    require_admin: bool = False,
    rate_limit: Optional[int] = None,
):
    """
    Decorator to wrap endpoints with error handling, logging, and validation

    Args:
        operation_name: Name of the operation for logging
        require_auth: Whether authentication is required
        require_admin: Whether admin role is required
        rate_limit: Rate limit (requests per minute) - None for no limit
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            request_id = kwargs.get("request_id") or f"req_{int(time.time() * 1000)}"
            user_id = kwargs.get("user_id")

            try:
                # Log incoming request
                request_logger.log_request(
                    method=kwargs.get("method", "UNKNOWN"),
                    path=kwargs.get("path", "UNKNOWN"),
                    user_id=user_id,
                    request_id=request_id,
                )

                # Check authentication if required
                if require_auth and not user_id:
                    raise AuthenticationError("Authentication required")

                # Check admin role if required
                if require_admin and kwargs.get("role") != "admin":
                    raise AuthenticationError("Admin role required")

                # Execute the endpoint
                result = await func(*args, **kwargs)

                # Log successful response
                duration_ms = (time.time() - start_time) * 1000
                response_size = len(str(result)) if result else 0

                request_logger.log_response(
                    status_code=200,
                    response_time=time.time() - start_time,
                    response_size=response_size,
                    user_id=user_id,
                    request_id=request_id,
                )

                # Log performance
                performance_logger.log_operation(
                    operation_name=operation_name, duration_ms=duration_ms, success=True
                )

                return result

            except CrucibError as e:
                # Handle known errors
                duration_ms = (time.time() - start_time) * 1000

                error_logger.log_error(
                    e,
                    context={
                        "operation": operation_name,
                        "request_id": request_id,
                        "duration_ms": duration_ms,
                    },
                    user_id=user_id,
                    severity="warning",
                )

                request_logger.log_response(
                    status_code=e.status_code,
                    response_time=time.time() - start_time,
                    response_size=0,
                    user_id=user_id,
                    request_id=request_id,
                    error=str(e),
                )

                raise to_http_exception(e)

            except HTTPException as e:
                # Pass through HTTP exceptions
                duration_ms = (time.time() - start_time) * 1000

                error_logger.log_error(
                    e,
                    context={
                        "operation": operation_name,
                        "request_id": request_id,
                        "status_code": e.status_code,
                        "duration_ms": duration_ms,
                    },
                    user_id=user_id,
                    severity="info",
                )

                request_logger.log_response(
                    status_code=e.status_code,
                    response_time=time.time() - start_time,
                    response_size=0,
                    user_id=user_id,
                    request_id=request_id,
                    error=str(e),
                )

                raise

            except Exception as e:
                # Handle unexpected errors
                duration_ms = (time.time() - start_time) * 1000

                error_logger.log_error(
                    e,
                    context={
                        "operation": operation_name,
                        "request_id": request_id,
                        "duration_ms": duration_ms,
                        "traceback": traceback.format_exc(),
                    },
                    user_id=user_id,
                    severity="critical",
                )

                request_logger.log_response(
                    status_code=500,
                    response_time=time.time() - start_time,
                    response_size=0,
                    user_id=user_id,
                    request_id=request_id,
                    error="Internal server error",
                )

                # Return generic error to client
                raise HTTPException(
                    status_code=500,
                    detail="An unexpected error occurred. Please try again later.",
                )

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            request_id = kwargs.get("request_id") or f"req_{int(time.time() * 1000)}"
            user_id = kwargs.get("user_id")

            try:
                # Log incoming request
                request_logger.log_request(
                    method=kwargs.get("method", "UNKNOWN"),
                    path=kwargs.get("path", "UNKNOWN"),
                    user_id=user_id,
                    request_id=request_id,
                )

                # Check authentication if required
                if require_auth and not user_id:
                    raise AuthenticationError("Authentication required")

                # Check admin role if required
                if require_admin and kwargs.get("role") != "admin":
                    raise AuthenticationError("Admin role required")

                # Execute the endpoint
                result = func(*args, **kwargs)

                # Log successful response
                duration_ms = (time.time() - start_time) * 1000
                response_size = len(str(result)) if result else 0

                request_logger.log_response(
                    status_code=200,
                    response_time=time.time() - start_time,
                    response_size=response_size,
                    user_id=user_id,
                    request_id=request_id,
                )

                # Log performance
                performance_logger.log_operation(
                    operation_name=operation_name, duration_ms=duration_ms, success=True
                )

                return result

            except CrucibError as e:
                duration_ms = (time.time() - start_time) * 1000

                error_logger.log_error(
                    e,
                    context={
                        "operation": operation_name,
                        "request_id": request_id,
                        "duration_ms": duration_ms,
                    },
                    user_id=user_id,
                    severity="warning",
                )

                request_logger.log_response(
                    status_code=e.status_code,
                    response_time=time.time() - start_time,
                    response_size=0,
                    user_id=user_id,
                    request_id=request_id,
                    error=str(e),
                )

                raise to_http_exception(e)

            except HTTPException as e:
                duration_ms = (time.time() - start_time) * 1000

                error_logger.log_error(
                    e,
                    context={
                        "operation": operation_name,
                        "request_id": request_id,
                        "status_code": e.status_code,
                        "duration_ms": duration_ms,
                    },
                    user_id=user_id,
                    severity="info",
                )

                request_logger.log_response(
                    status_code=e.status_code,
                    response_time=time.time() - start_time,
                    response_size=0,
                    user_id=user_id,
                    request_id=request_id,
                    error=str(e),
                )

                raise

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000

                error_logger.log_error(
                    e,
                    context={
                        "operation": operation_name,
                        "request_id": request_id,
                        "duration_ms": duration_ms,
                        "traceback": traceback.format_exc(),
                    },
                    user_id=user_id,
                    severity="critical",
                )

                request_logger.log_response(
                    status_code=500,
                    response_time=time.time() - start_time,
                    response_size=0,
                    user_id=user_id,
                    request_id=request_id,
                    error="Internal server error",
                )

                raise HTTPException(
                    status_code=500,
                    detail="An unexpected error occurred. Please try again later.",
                )

        # Return appropriate wrapper
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ==================== BATCH ENDPOINT WRAPPER ====================


def wrap_all_endpoints(app):
    """
    Automatically wrap all endpoints with error handling and logging
    This is called once during app initialization
    """
    from fastapi.routing import APIRoute

    wrapped_count = 0

    for route in app.routes:
        if isinstance(route, APIRoute) and route.endpoint:
            # Skip if already wrapped
            if hasattr(route.endpoint, "__wrapped__"):
                continue

            # Determine if auth is required
            require_auth = any(
                "auth" in str(dep).lower() or "user" in str(dep).lower()
                for dep in (route.dependencies or [])
            )

            # Wrap the endpoint
            operation_name = route.name or route.path
            route.endpoint = safe_endpoint(
                operation_name=operation_name, require_auth=require_auth
            )(route.endpoint)

            wrapped_count += 1

    return wrapped_count


# ==================== USAGE EXAMPLE ====================

"""
In server.py, after creating the app:

from endpoint_wrapper import wrap_all_endpoints, safe_endpoint

# Wrap all endpoints
wrapped = wrap_all_endpoints(app)
print(f"Wrapped {wrapped} endpoints with error handling and logging")

# Or manually wrap individual endpoints:
@api_router.post("/ai/chat")
@safe_endpoint("chat_endpoint", require_auth=True)
async def chat(data: ChatMessage, user_id: str = Depends(get_current_user)):
    # Your endpoint logic here
    pass
"""
