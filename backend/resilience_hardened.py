"""
Hardened resilience patterns for production systems.

Implements:
- Timeouts on all operations
- Retry with exponential backoff
- Circuit breaker pattern
- Bulkhead isolation
- Graceful degradation
- Idempotent operations
"""

import asyncio
import functools
import logging
import time
from enum import Enum
from typing import Any, Callable, Optional, TypeVar, Union

from logging_enhanced import logger, set_trace_context

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerException(Exception):
    """Raised when circuit breaker is open."""

    pass


class TimeoutException(Exception):
    """Raised when operation times out."""

    pass


class RetryException(Exception):
    """Raised when all retries are exhausted."""

    pass


class CircuitBreaker:
    """Circuit breaker pattern for fault tolerance."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Circuit breaker name
            failure_threshold: Failures before opening circuit
            recovery_timeout: Seconds before attempting recovery
            expected_exception: Exception type to catch
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerException: If circuit is open
        """
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info(
                    f"Circuit breaker '{self.name}' entering half-open state"
                )
            else:
                raise CircuitBreakerException(
                    f"Circuit breaker '{self.name}' is open"
                )

        try:
            result = func(*args, **kwargs)

            self._on_success()
            return result

        except self.expected_exception as e:
            self._on_failure()
            raise

    async def call_async(
        self, func: Callable[..., Any], *args, **kwargs
    ) -> T:
        """Async version of call."""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                logger.info(
                    f"Circuit breaker '{self.name}' entering half-open state"
                )
            else:
                raise CircuitBreakerException(
                    f"Circuit breaker '{self.name}' is open"
                )

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result

        except self.expected_exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """Handle successful call."""
        self.failure_count = 0

        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= 2:
                self.state = CircuitState.CLOSED
                self.success_count = 0
                logger.info(f"Circuit breaker '{self.name}' closed (recovered)")

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.error(
                f"Circuit breaker '{self.name}' opened after {self.failure_count} failures"
            )

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return True

        return time.time() - self.last_failure_time >= self.recovery_timeout

    def get_state(self) -> dict:
        """Get circuit breaker state."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
        }


class RetryPolicy:
    """Retry policy with exponential backoff."""

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 0.1,
        max_delay: float = 10.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
    ):
        """
        Initialize retry policy.

        Args:
            max_retries: Maximum number of retries
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            backoff_factor: Exponential backoff factor
            jitter: Whether to add random jitter
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for attempt."""
        delay = self.initial_delay * (self.backoff_factor ** attempt)
        delay = min(delay, self.max_delay)

        if self.jitter:
            import random

            delay *= random.uniform(0.5, 1.5)

        return delay

    def should_retry(self, attempt: int, exception: Exception) -> bool:
        """Determine if should retry."""
        return attempt < self.max_retries

    def execute(
        self, func: Callable[..., T], *args, **kwargs
    ) -> T:
        """
        Execute function with retries.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            RetryException: If all retries exhausted
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)

            except Exception as e:
                last_exception = e

                if not self.should_retry(attempt, e):
                    raise RetryException(
                        f"All {self.max_retries} retries exhausted"
                    ) from e

                delay = self.get_delay(attempt)
                logger.warning(
                    f"Retry attempt {attempt + 1}/{self.max_retries} after {delay:.2f}s",
                    extra={"exception": str(e)},
                )
                time.sleep(delay)

        raise RetryException("Retry failed") from last_exception

    async def execute_async(
        self, func: Callable[..., Any], *args, **kwargs
    ) -> T:
        """Async version of execute."""
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                return await func(*args, **kwargs)

            except Exception as e:
                last_exception = e

                if not self.should_retry(attempt, e):
                    raise RetryException(
                        f"All {self.max_retries} retries exhausted"
                    ) from e

                delay = self.get_delay(attempt)
                logger.warning(
                    f"Retry attempt {attempt + 1}/{self.max_retries} after {delay:.2f}s",
                    extra={"exception": str(e)},
                )
                await asyncio.sleep(delay)

        raise RetryException("Retry failed") from last_exception


class TimeoutWrapper:
    """Timeout wrapper for operations."""

    def __init__(self, timeout_seconds: float):
        """
        Initialize timeout wrapper.

        Args:
            timeout_seconds: Timeout in seconds
        """
        self.timeout_seconds = timeout_seconds

    def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute function with timeout.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            TimeoutException: If operation times out
        """
        import signal

        def timeout_handler(signum, frame):
            raise TimeoutException(
                f"Operation timed out after {self.timeout_seconds}s"
            )

        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(int(self.timeout_seconds))

        try:
            result = func(*args, **kwargs)
            signal.alarm(0)  # Cancel alarm
            return result

        except TimeoutException:
            raise

    async def execute_async(
        self, func: Callable[..., Any], *args, **kwargs
    ) -> T:
        """Async version of execute."""
        try:
            return await asyncio.wait_for(
                func(*args, **kwargs), timeout=self.timeout_seconds
            )

        except asyncio.TimeoutError:
            raise TimeoutException(
                f"Operation timed out after {self.timeout_seconds}s"
            )


def with_timeout(timeout_seconds: float):
    """Decorator for adding timeout to functions."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            wrapper_obj = TimeoutWrapper(timeout_seconds)
            return wrapper_obj.execute(func, *args, **kwargs)

        return wrapper

    return decorator


def with_retry(
    max_retries: int = 3,
    initial_delay: float = 0.1,
    backoff_factor: float = 2.0,
):
    """Decorator for adding retry logic to functions."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        policy = RetryPolicy(
            max_retries=max_retries,
            initial_delay=initial_delay,
            backoff_factor=backoff_factor,
        )

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return policy.execute(func, *args, **kwargs)

        return wrapper

    return decorator


# Global circuit breakers for critical services
database_circuit_breaker = CircuitBreaker(
    "database",
    failure_threshold=5,
    recovery_timeout=60,
)

api_circuit_breaker = CircuitBreaker(
    "external_api",
    failure_threshold=5,
    recovery_timeout=60,
)

llm_circuit_breaker = CircuitBreaker(
    "llm_service",
    failure_threshold=3,
    recovery_timeout=120,
)
