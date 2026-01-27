"""Circuit breaker pattern for external dependencies.

This module implements a circuit breaker to prevent cascading failures
when external dependencies (Neo4j, LLM) are unavailable or slow.

The circuit breaker has three states:
- CLOSED: Normal operation, calls are allowed
- OPEN: Dependency is failing, calls are rejected immediately
- HALF_OPEN: Testing recovery, limited calls allowed

Typical usage:
    breaker = CircuitBreaker(name="neo4j", failure_threshold=3, recovery_timeout=60.0)

    try:
        result = await breaker.call(some_async_function, arg1, arg2)
    except CircuitOpenError:
        # Handle circuit open (e.g., skip this stage)
        pass
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, TypeVar

import structlog

T = TypeVar("T")


class CircuitState(Enum):
    """States of the circuit breaker."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitOpenError(Exception):
    """Raised when circuit is open and call is rejected."""

    def __init__(self, name: str, time_until_recovery: float):
        self.name = name
        self.time_until_recovery = time_until_recovery
        super().__init__(
            f"Circuit '{name}' is OPEN. Recovery in {time_until_recovery:.1f}s"
        )


@dataclass
class CircuitBreaker:
    """Circuit breaker for external dependencies.

    Prevents cascading failures by failing fast when a dependency is unhealthy.
    After a recovery timeout, allows limited traffic to test if the dependency
    has recovered.

    Attributes:
        name: Identifier for logging
        failure_threshold: Number of failures before opening
        recovery_timeout: Seconds before transitioning from OPEN to HALF_OPEN
        half_open_max_calls: Successful calls needed in HALF_OPEN to close

    Example:
        >>> breaker = CircuitBreaker(name="claude", failure_threshold=3)
        >>> result = await breaker.call(call_claude_api, prompt)
    """

    name: str
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 3

    # Internal state (not meant to be set by caller)
    _state: CircuitState = field(default=CircuitState.CLOSED, repr=False)
    _failure_count: int = field(default=0, repr=False)
    _last_failure_time: float = field(default=0.0, repr=False)
    _half_open_success_count: int = field(default=0, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    def __post_init__(self) -> None:
        """Initialize the logger."""
        self._logger = structlog.get_logger().bind(circuit_breaker=self.name)

    @property
    def state(self) -> CircuitState:
        """Get current circuit state (may trigger state transition)."""
        if self._state == CircuitState.OPEN:
            if time.monotonic() - self._last_failure_time > self.recovery_timeout:
                return CircuitState.HALF_OPEN
        return self._state

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self.state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (rejecting calls)."""
        return self.state == CircuitState.OPEN

    async def call(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute function through the circuit breaker.

        Args:
            func: The async function to call
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            The result of the function call

        Raises:
            CircuitOpenError: If circuit is open
            Exception: Any exception from the wrapped function
        """
        async with self._lock:
            current_state = self.state

            # Check if we should reject the call
            if current_state == CircuitState.OPEN:
                time_until_recovery = (
                    self._last_failure_time + self.recovery_timeout - time.monotonic()
                )
                raise CircuitOpenError(self.name, max(0, time_until_recovery))

            # Transition to half-open if needed
            if current_state == CircuitState.HALF_OPEN and self._state == CircuitState.OPEN:
                self._state = CircuitState.HALF_OPEN
                self._half_open_success_count = 0
                self._logger.info("circuit_half_open", name=self.name)

        try:
            # Execute the function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            # Record success
            async with self._lock:
                self._on_success()

            return result

        except Exception as e:
            # Record failure
            async with self._lock:
                self._on_failure()

            raise

    def _on_success(self) -> None:
        """Handle successful call (must be called within lock)."""
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_success_count += 1
            if self._half_open_success_count >= self.half_open_max_calls:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._logger.info("circuit_closed", name=self.name)
        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success
            self._failure_count = 0

    def _on_failure(self) -> None:
        """Handle failed call (must be called within lock)."""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()

        if self._state == CircuitState.HALF_OPEN:
            # Any failure in half-open immediately opens
            self._state = CircuitState.OPEN
            self._logger.warning(
                "circuit_opened_from_half_open",
                name=self.name,
                recovery_timeout=self.recovery_timeout,
            )
        elif self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            self._logger.warning(
                "circuit_opened",
                name=self.name,
                failure_count=self._failure_count,
                recovery_timeout=self.recovery_timeout,
            )

    def reset(self) -> None:
        """Manually reset the circuit breaker to closed state.

        This is mainly useful for testing.
        """
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_success_count = 0
        self._last_failure_time = 0.0
        self._logger.info("circuit_reset", name=self.name)

    def get_stats(self) -> dict[str, Any]:
        """Get circuit breaker statistics.

        Returns:
            Dictionary with state, failure count, and timing info
        """
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "last_failure_time": self._last_failure_time,
        }
