"""Tests for LLM retry utility (Spec 109, FR-002)."""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from anthropic import (
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    RateLimitError,
)
from pydantic import ValidationError
from tenacity import wait_none

from nikita.llm.retry import RETRYABLE_EXCEPTIONS, LLM_CALL_TIMEOUT, llm_retry


# ---------------------------------------------------------------------------
# Test 0: asyncio.TimeoutError is in RETRYABLE_EXCEPTIONS
# ---------------------------------------------------------------------------


def test_asyncio_timeout_in_retryable():
    """asyncio.TimeoutError should be in RETRYABLE_EXCEPTIONS (C2 fix)."""
    assert asyncio.TimeoutError in RETRYABLE_EXCEPTIONS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_rate_limit_error() -> RateLimitError:
    response = httpx.Response(
        429, request=httpx.Request("POST", "https://api.anthropic.com")
    )
    return RateLimitError(response=response, body=None, message="Rate limited")


def _make_internal_server_error() -> InternalServerError:
    response = httpx.Response(
        500, request=httpx.Request("POST", "https://api.anthropic.com")
    )
    return InternalServerError(response=response, body=None, message="Server error")


def _make_auth_error() -> AuthenticationError:
    response = httpx.Response(
        401, request=httpx.Request("POST", "https://api.anthropic.com")
    )
    return AuthenticationError(response=response, body=None, message="Invalid API key")


def _make_bad_request_error() -> BadRequestError:
    response = httpx.Response(
        400, request=httpx.Request("POST", "https://api.anthropic.com")
    )
    return BadRequestError(response=response, body=None, message="Bad request")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_settings() -> MagicMock:
    settings = MagicMock()
    settings.llm_retry_max_attempts = 3
    settings.llm_retry_base_wait = 1.0
    settings.llm_retry_call_timeout = 60.0  # Must be a real float for asyncio.wait_for
    return settings


def make_decorated(mock_func: AsyncMock, mock_settings: MagicMock):
    """Create a fresh llm_retry-decorated async function and skip real delays."""
    with patch("nikita.llm.retry.get_settings", return_value=mock_settings):

        @llm_retry
        async def _fn(*args, **kwargs):
            return await mock_func(*args, **kwargs)

    # Skip real backoff waits so tests run in <5 s
    _fn.retry.wait = wait_none()
    return _fn


# ---------------------------------------------------------------------------
# Test 1: retries on RateLimitError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retries_on_rate_limit_error(mock_settings):
    """Function should be called 3 times: fail, fail, succeed."""
    mock_func = AsyncMock(
        side_effect=[
            _make_rate_limit_error(),
            _make_rate_limit_error(),
            "ok",
        ]
    )
    fn = make_decorated(mock_func, mock_settings)

    result = await fn()

    assert result == "ok"
    assert mock_func.call_count == 3


# ---------------------------------------------------------------------------
# Test 2: retries on InternalServerError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retries_on_internal_server_error(mock_settings):
    """Function should be called 3 times: fail, fail, succeed."""
    mock_func = AsyncMock(
        side_effect=[
            _make_internal_server_error(),
            _make_internal_server_error(),
            "ok",
        ]
    )
    fn = make_decorated(mock_func, mock_settings)

    result = await fn()

    assert result == "ok"
    assert mock_func.call_count == 3


# ---------------------------------------------------------------------------
# Test 3: retries on httpx.ReadTimeout
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retries_on_read_timeout(mock_settings):
    """ReadTimeout is a transient error and should trigger retry."""
    mock_func = AsyncMock(
        side_effect=[
            httpx.ReadTimeout("Read timed out"),
            "ok",
        ]
    )
    fn = make_decorated(mock_func, mock_settings)

    result = await fn()

    assert result == "ok"
    assert mock_func.call_count == 2


# ---------------------------------------------------------------------------
# Test 4: no retry on AuthenticationError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_retry_on_authentication_error(mock_settings):
    """AuthenticationError is a client error — raise immediately after 1 call."""
    mock_func = AsyncMock(side_effect=_make_auth_error())
    fn = make_decorated(mock_func, mock_settings)

    with pytest.raises(AuthenticationError):
        await fn()

    assert mock_func.call_count == 1


# ---------------------------------------------------------------------------
# Test 5: no retry on BadRequestError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_retry_on_bad_request_error(mock_settings):
    """BadRequestError is a client error — raise immediately after 1 call."""
    mock_func = AsyncMock(side_effect=_make_bad_request_error())
    fn = make_decorated(mock_func, mock_settings)

    with pytest.raises(BadRequestError):
        await fn()

    assert mock_func.call_count == 1


# ---------------------------------------------------------------------------
# Test 6: no retry on pydantic.ValidationError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_retry_on_validation_error(mock_settings):
    """ValidationError is not retryable — raise immediately after 1 call."""
    validation_error = ValidationError.from_exception_data("test", [])
    mock_func = AsyncMock(side_effect=validation_error)
    fn = make_decorated(mock_func, mock_settings)

    with pytest.raises(ValidationError):
        await fn()

    assert mock_func.call_count == 1


# ---------------------------------------------------------------------------
# Test 7: exhausted retries — all attempts consumed, retry_error_callback fires
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_exhausted_retries_raises(mock_settings):
    """All 3 attempts fail — exception re-raised after exhaustion (C1 fix).

    _log_final_failure now re-raises the exception so callers can handle it.
    The important invariant is that all 3 attempts are made AND the exception propagates.
    """
    mock_func = AsyncMock(
        side_effect=[
            _make_rate_limit_error(),
            _make_rate_limit_error(),
            _make_rate_limit_error(),
        ]
    )
    fn = make_decorated(mock_func, mock_settings)

    with pytest.raises(RateLimitError):
        await fn()

    assert mock_func.call_count == 3


# ---------------------------------------------------------------------------
# Test 8: retry logs a WARNING with attempt number
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retry_logging_warning(mock_settings, caplog):
    """Each failed-then-retried attempt should produce a WARNING log."""
    mock_func = AsyncMock(
        side_effect=[
            _make_rate_limit_error(),
            "ok",
        ]
    )
    fn = make_decorated(mock_func, mock_settings)

    with caplog.at_level(logging.WARNING, logger="nikita.llm.retry"):
        result = await fn()

    assert result == "ok"
    warning_records = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warning_records) >= 1
    # The warning should mention the attempt number
    assert any("attempt" in r.message.lower() or "1" in r.message for r in warning_records)


# ---------------------------------------------------------------------------
# Test 9: final failure logs an ERROR
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_final_failure_logging_error(mock_settings, caplog):
    """After all retries exhausted, an ERROR should be logged and exception re-raised."""
    mock_func = AsyncMock(
        side_effect=[
            _make_rate_limit_error(),
            _make_rate_limit_error(),
            _make_rate_limit_error(),
        ]
    )
    fn = make_decorated(mock_func, mock_settings)

    with caplog.at_level(logging.ERROR, logger="nikita.llm.retry"):
        with pytest.raises(RateLimitError):
            await fn()

    error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(error_records) >= 1
    assert any("failed" in r.message.lower() for r in error_records)


# ---------------------------------------------------------------------------
# Test 10: backoff respects settings.llm_retry_max_attempts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_backoff_uses_settings(mock_settings):
    """Decorator reads max_attempts from settings — custom 2 means only 2 attempts."""
    mock_settings.llm_retry_max_attempts = 2

    mock_func = AsyncMock(
        side_effect=[
            _make_rate_limit_error(),
            _make_rate_limit_error(),
            "should_not_reach",
        ]
    )
    fn = make_decorated(mock_func, mock_settings)

    with pytest.raises(RateLimitError):
        await fn()

    # With max_attempts=2, only 2 calls should be made before giving up
    assert mock_func.call_count == 2


# ---------------------------------------------------------------------------
# Test 11: retries on asyncio.TimeoutError (C2)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retries_on_asyncio_timeout(mock_settings):
    """asyncio.TimeoutError from wait_for() should trigger retry and succeed."""
    mock_func = AsyncMock(
        side_effect=[
            asyncio.TimeoutError(),
            "ok",
        ]
    )
    fn = make_decorated(mock_func, mock_settings)

    result = await fn()

    assert result == "ok"
    assert mock_func.call_count == 2


# ---------------------------------------------------------------------------
# Test 12: LLM_CALL_TIMEOUT uses settings.llm_retry_call_timeout
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_call_timeout_from_settings():
    """Verify llm_retry reads call timeout from settings, not hardcoded constant."""
    mock_settings = MagicMock()
    mock_settings.llm_retry_max_attempts = 1
    mock_settings.llm_retry_base_wait = 0.1
    mock_settings.llm_retry_call_timeout = 15.5  # Non-default value

    mock_func = AsyncMock(return_value="ok")

    with patch("nikita.llm.retry.get_settings", return_value=mock_settings):
        with patch("nikita.llm.retry.asyncio.wait_for", wraps=asyncio.wait_for) as mock_wait_for:

            @llm_retry
            async def _fn():
                return await mock_func()

            result = await _fn()

    assert result == "ok"
    mock_wait_for.assert_called_once()
    # Verify the custom timeout from settings was actually used
    call_args = mock_wait_for.call_args
    assert call_args[1].get("timeout") == 15.5 or call_args[0][1] == 15.5
