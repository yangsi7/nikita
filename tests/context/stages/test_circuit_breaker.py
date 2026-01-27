"""Tests for CircuitBreaker class."""

import asyncio
import time
from unittest.mock import AsyncMock

import pytest

from nikita.context.stages.circuit_breaker import (
    CircuitBreaker,
    CircuitOpenError,
    CircuitState,
)


class TestCircuitBreakerState:
    """Test circuit breaker state transitions."""

    def test_initial_state_is_closed(self):
        """Circuit starts in CLOSED state."""
        breaker = CircuitBreaker(name="test")
        assert breaker.state == CircuitState.CLOSED
        assert breaker.is_closed
        assert not breaker.is_open

    @pytest.mark.asyncio
    async def test_stays_closed_on_success(self):
        """Circuit stays closed when calls succeed."""
        breaker = CircuitBreaker(name="test", failure_threshold=3)
        func = AsyncMock(return_value="ok")

        for _ in range(10):
            result = await breaker.call(func)
            assert result == "ok"

        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_opens_after_threshold_failures(self):
        """Circuit opens after failure_threshold consecutive failures."""
        breaker = CircuitBreaker(name="test", failure_threshold=3)
        func = AsyncMock(side_effect=Exception("fail"))

        for i in range(3):
            with pytest.raises(Exception, match="fail"):
                await breaker.call(func)

        assert breaker.state == CircuitState.OPEN
        assert breaker.is_open

    @pytest.mark.asyncio
    async def test_rejects_calls_when_open(self):
        """Open circuit rejects calls immediately."""
        breaker = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout=60.0)
        func = AsyncMock(side_effect=Exception("fail"))

        # Open the circuit
        with pytest.raises(Exception):
            await breaker.call(func)

        assert breaker.is_open

        # Calls should be rejected
        with pytest.raises(CircuitOpenError) as exc_info:
            await breaker.call(func)

        assert exc_info.value.name == "test"
        assert exc_info.value.time_until_recovery > 0

    @pytest.mark.asyncio
    async def test_transitions_to_half_open_after_timeout(self):
        """Circuit transitions to HALF_OPEN after recovery timeout."""
        breaker = CircuitBreaker(
            name="test",
            failure_threshold=1,
            recovery_timeout=0.1,  # 100ms for testing
        )
        func = AsyncMock(side_effect=Exception("fail"))

        # Open the circuit
        with pytest.raises(Exception):
            await breaker.call(func)

        assert breaker._state == CircuitState.OPEN

        # Wait for recovery timeout
        await asyncio.sleep(0.15)

        # Should now be HALF_OPEN
        assert breaker.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_closes_after_half_open_successes(self):
        """Circuit closes after successful calls in HALF_OPEN state."""
        breaker = CircuitBreaker(
            name="test",
            failure_threshold=1,
            recovery_timeout=0.05,
            half_open_max_calls=2,
        )

        # Open the circuit
        fail_func = AsyncMock(side_effect=Exception("fail"))
        with pytest.raises(Exception):
            await breaker.call(fail_func)

        # Wait for recovery
        await asyncio.sleep(0.1)
        assert breaker.state == CircuitState.HALF_OPEN

        # Successful calls should close the circuit
        success_func = AsyncMock(return_value="ok")
        await breaker.call(success_func)
        await breaker.call(success_func)

        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_reopens_on_half_open_failure(self):
        """Circuit reopens immediately on failure in HALF_OPEN state."""
        breaker = CircuitBreaker(
            name="test",
            failure_threshold=1,
            recovery_timeout=0.05,
            half_open_max_calls=3,
        )

        # Open the circuit
        fail_func = AsyncMock(side_effect=Exception("fail"))
        with pytest.raises(Exception):
            await breaker.call(fail_func)

        # Wait for recovery
        await asyncio.sleep(0.1)
        assert breaker.state == CircuitState.HALF_OPEN

        # Failure should reopen
        with pytest.raises(Exception):
            await breaker.call(fail_func)

        assert breaker._state == CircuitState.OPEN


class TestCircuitBreakerCalls:
    """Test circuit breaker call mechanics."""

    @pytest.mark.asyncio
    async def test_passes_args_to_function(self):
        """Arguments are passed through to the wrapped function."""
        breaker = CircuitBreaker(name="test")
        func = AsyncMock(return_value="result")

        result = await breaker.call(func, "arg1", "arg2", kwarg1="value")

        func.assert_called_once_with("arg1", "arg2", kwarg1="value")
        assert result == "result"

    @pytest.mark.asyncio
    async def test_works_with_sync_functions(self):
        """Circuit breaker works with synchronous functions."""
        breaker = CircuitBreaker(name="test")

        def sync_func(x: int) -> int:
            return x * 2

        result = await breaker.call(sync_func, 5)
        assert result == 10

    @pytest.mark.asyncio
    async def test_resets_failure_count_on_success(self):
        """Failure count resets after a successful call."""
        breaker = CircuitBreaker(name="test", failure_threshold=3)

        # Two failures
        fail_func = AsyncMock(side_effect=Exception("fail"))
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(fail_func)

        # One success resets count
        success_func = AsyncMock(return_value="ok")
        await breaker.call(success_func)

        # Two more failures shouldn't open (threshold is 3)
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(fail_func)

        assert breaker.state == CircuitState.CLOSED


class TestCircuitBreakerReset:
    """Test circuit breaker reset functionality."""

    @pytest.mark.asyncio
    async def test_manual_reset(self):
        """Manual reset closes the circuit."""
        breaker = CircuitBreaker(name="test", failure_threshold=1)

        # Open the circuit
        fail_func = AsyncMock(side_effect=Exception("fail"))
        with pytest.raises(Exception):
            await breaker.call(fail_func)

        assert breaker.is_open

        # Manual reset
        breaker.reset()

        assert breaker.is_closed
        assert breaker._failure_count == 0


class TestCircuitBreakerStats:
    """Test circuit breaker statistics."""

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Stats returns correct information."""
        breaker = CircuitBreaker(
            name="test_circuit",
            failure_threshold=5,
            recovery_timeout=120.0,
        )

        stats = breaker.get_stats()

        assert stats["name"] == "test_circuit"
        assert stats["state"] == "closed"
        assert stats["failure_count"] == 0
        assert stats["failure_threshold"] == 5
        assert stats["recovery_timeout"] == 120.0
