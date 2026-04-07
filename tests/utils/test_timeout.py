"""Tests for timeout fallback decorator (DEBT-001).

Tests:
- Decorator returns fallback value on timeout
- Decorator returns normal result on success
- Timeout duration is respected
"""

import asyncio

import pytest

from nikita.agents.voice.server_tools import with_timeout_fallback


class TestWithTimeoutFallback:
    """Test with_timeout_fallback decorator."""

    @pytest.mark.asyncio
    async def test_returns_result_on_success(self):
        """Decorator passes through normal return value."""

        @with_timeout_fallback(timeout_seconds=2.0)
        async def fast_func():
            return {"data": "hello"}

        result = await fast_func()
        assert result == {"data": "hello"}

    @pytest.mark.asyncio
    async def test_returns_fallback_on_timeout(self):
        """Decorator returns fallback dict when function times out."""

        @with_timeout_fallback(timeout_seconds=0.05, fallback_data={"cached": True})
        async def slow_func():
            await asyncio.sleep(5)
            return {"data": "never_reached"}

        result = await slow_func()
        assert result["timeout"] is True
        assert result["cache_friendly"] is True
        assert result["cached"] is True
        assert "timed out" in result["error"]

    @pytest.mark.asyncio
    async def test_fallback_with_no_fallback_data(self):
        """Decorator returns minimal fallback when no fallback_data provided."""

        @with_timeout_fallback(timeout_seconds=0.05)
        async def slow_func():
            await asyncio.sleep(5)

        result = await slow_func()
        assert result["timeout"] is True
        assert result["cache_friendly"] is True
        assert "cached" not in result

    @pytest.mark.asyncio
    async def test_preserves_function_args(self):
        """Decorator correctly passes through args and kwargs."""

        @with_timeout_fallback(timeout_seconds=2.0)
        async def func_with_args(a, b, key="default"):
            return {"a": a, "b": b, "key": key}

        result = await func_with_args(1, 2, key="custom")
        assert result == {"a": 1, "b": 2, "key": "custom"}

    @pytest.mark.asyncio
    async def test_works_as_instance_method_decorator(self):
        """Decorator works on instance methods (self passed as first arg)."""

        class MyHandler:
            @with_timeout_fallback(timeout_seconds=2.0)
            async def get_data(self, user_id: str) -> dict:
                return {"user_id": user_id, "data": "found"}

        handler = MyHandler()
        result = await handler.get_data("abc-123")
        assert result == {"user_id": "abc-123", "data": "found"}
