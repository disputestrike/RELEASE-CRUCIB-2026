"""
Resilience patterns for CrucibAI.

Implements circuit breaker, retry logic, and graceful degradation.
"""

import asyncio
import random
import time
from enum import Enum
from typing import Any, Callable, Optional, TypeVar

from logging_system import app_logger

T = TypeVar("T")


class CircuitState(Enum):
    """States of a circuit breaker."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker pattern for fault tolerance."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
    ):
        """Initialize circuit breaker."""
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                app_logger.info(
                    f"Circuit breaker {self.name} attempting reset",
                    circuit_state=self.state.value,
                )
            else:
                raise Exception(f"Circuit breaker {self.name} is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise

    async def call_async(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute async function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                app_logger.info(
                    f"Circuit breaker {self.name} attempting reset",
                    circuit_state=self.state.value,
                )
            else:
                raise Exception(f"Circuit breaker {self.name} is OPEN")

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
            self.state = CircuitState.CLOSED
            self.success_count += 1
            app_logger.info(
                f"Circuit breaker {self.name} recovered",
                circuit_state=self.state.value,
            )

    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            app_logger.error(
                f"Circuit breaker {self.name} opened",
                circuit_state=self.state.value,
                failure_count=self.failure_count,
            )

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return False
        return time.time() - self.last_failure_time >= self.recovery_timeout


class RetryPolicy:
    """Retry policy with exponential backoff."""

    def __init__(
        self,
        max_attempts: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        """Initialize retry policy."""
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

    def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with retry logic."""
        last_exception = None

        for attempt in range(self.max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    app_logger.warning(
                        f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s",
                        attempt=attempt + 1,
                        max_attempts=self.max_attempts,
                        error=str(e),
                    )
                    time.sleep(delay)

        raise last_exception

    async def execute_async(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute async function with retry logic."""
        last_exception = None

        for attempt in range(self.max_attempts):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < self.max_attempts - 1:
                    delay = self._calculate_delay(attempt)
                    app_logger.warning(
                        f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s",
                        attempt=attempt + 1,
                        max_attempts=self.max_attempts,
                        error=str(e),
                    )
                    await asyncio.sleep(delay)

        raise last_exception

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for exponential backoff."""
        delay = self.initial_delay * (self.exponential_base ** attempt)
        delay = min(delay, self.max_delay)

        if self.jitter:
            # Add random jitter (±20%)
            jitter_amount = delay * 0.2
            delay += random.uniform(-jitter_amount, jitter_amount)

        return max(delay, 0)  # Ensure non-negative


class Timeout:
    """Timeout wrapper for operations."""

    def __init__(self, seconds: float):
        """Initialize timeout."""
        self.seconds = seconds

    def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with timeout."""
        start_time = time.time()

        while time.time() - start_time < self.seconds:
            try:
                return func(*args, **kwargs)
            except TimeoutError:
                remaining = self.seconds - (time.time() - start_time)
                if remaining <= 0:
                    raise
                time.sleep(min(0.1, remaining))

        raise TimeoutError(f"Operation exceeded timeout of {self.seconds}s")

    async def execute_async(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute async function with timeout."""
        try:
            return await asyncio.wait_for(func(*args, **kwargs), timeout=self.seconds)
        except asyncio.TimeoutError:
            raise TimeoutError(f"Operation exceeded timeout of {self.seconds}s")


class Bulkhead:
    """Bulkhead pattern for resource isolation."""

    def __init__(self, name: str, max_concurrent: int = 10):
        """Initialize bulkhead."""
        self.name = name
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.current_count = 0

    async def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with bulkhead protection."""
        async with self.semaphore:
            self.current_count += 1
            try:
                return await func(*args, **kwargs)
            finally:
                self.current_count -= 1

    def get_utilization(self) -> float:
        """Get bulkhead utilization as percentage."""
        return (self.current_count / self.max_concurrent) * 100


class RateLimiter:
    """Token bucket rate limiter."""

    def __init__(self, rate: float, capacity: float):
        """Initialize rate limiter."""
        self.rate = rate  # Tokens per second
        self.capacity = capacity  # Max tokens
        self.tokens = capacity
        self.last_update = time.time()

    def allow(self) -> bool:
        """Check if operation is allowed."""
        now = time.time()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now

        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False

    async def allow_async(self) -> bool:
        """Async version of allow."""
        while not self.allow():
            await asyncio.sleep(0.01)
        return True


# Global resilience patterns
database_circuit_breaker = CircuitBreaker("database", failure_threshold=5, recovery_timeout=30)
s3_circuit_breaker = CircuitBreaker("s3", failure_threshold=5, recovery_timeout=30)
api_circuit_breaker = CircuitBreaker("api", failure_threshold=10, recovery_timeout=60)

default_retry_policy = RetryPolicy(max_attempts=3, initial_delay=1.0, max_delay=30.0)
agent_retry_policy = RetryPolicy(max_attempts=5, initial_delay=0.5, max_delay=10.0)

agent_bulkhead = Bulkhead("agents", max_concurrent=20)
api_rate_limiter = RateLimiter(rate=100, capacity=100)  # 100 requests per second
