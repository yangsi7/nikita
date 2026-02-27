"""LLM retry decorator with exponential backoff (Spec 109, FR-002).

Provides a tenacity-based async decorator for LLM API calls that retries
on transient errors (rate limits, server errors, timeouts) but fails
immediately on client errors (auth, bad request, validation).

Usage:
    from nikita.llm import llm_retry

    @llm_retry
    async def _call_llm(self, prompt: str) -> str:
        result = await agent.run(prompt)
        return result.data

Design notes:
    D1 — @llm_retry captures settings at *decoration time* (module import).
        Tests must patch get_settings() BEFORE the decorator fires, or use
        monkeypatch on the already-captured wrapper attributes.
    D3 — Worst-case latency per call site:
        max_attempts * call_timeout + backoff ≈ 3 min (3 × 60 s + ~7 s backoff).
        Background tasks insulate the Telegram webhook from this budget.
"""

import asyncio
import logging
from functools import wraps
from typing import Any, Callable

import httpx
from anthropic import (
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    RateLimitError,
)
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from nikita.config.settings import get_settings

logger = logging.getLogger(__name__)

# Transient errors that should be retried
RETRYABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    RateLimitError,
    InternalServerError,
    httpx.ReadTimeout,
    httpx.ConnectTimeout,
    asyncio.TimeoutError,
)

# Client errors that should NOT be retried
NON_RETRYABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    AuthenticationError,
    BadRequestError,
)

# Legacy re-export — now reads from settings at decoration time.
# Kept for backward compatibility (tests import LLM_CALL_TIMEOUT directly).
LLM_CALL_TIMEOUT = 60.0  # Default; actual value comes from settings in llm_retry()


def _log_retry_attempt(retry_state: RetryCallState) -> None:
    """Log WARNING on each retry attempt."""
    exception = retry_state.outcome.exception() if retry_state.outcome else None
    func_name = getattr(retry_state.fn, "__qualname__", str(retry_state.fn))
    logger.warning(
        "LLM call %s failed (attempt %d/%d): %s — retrying",
        func_name,
        retry_state.attempt_number,
        retry_state.retry_object.stop.max_attempt_number,  # type: ignore[union-attr]
        _sanitize_error(exception),
    )


def _log_final_failure(retry_state: RetryCallState) -> None:
    """Log ERROR after all retry attempts exhausted, then re-raise.

    Tenacity's retry_error_callback takes precedence over reraise=True.
    We must explicitly re-raise so callers see the exception.
    """
    exception = retry_state.outcome.exception() if retry_state.outcome else None
    func_name = getattr(retry_state.fn, "__qualname__", str(retry_state.fn))
    logger.error(
        "LLM call %s failed after %d attempts: %s",
        func_name,
        retry_state.attempt_number,
        _sanitize_error(exception),
    )
    if exception:
        raise exception


def _sanitize_error(exc: BaseException | None) -> str:
    """Sanitize error message — strip API keys and long payloads."""
    if exc is None:
        return "unknown error"
    msg = str(exc)
    # Truncate long error messages
    if len(msg) > 200:
        msg = msg[:200] + "..."
    return msg


def llm_retry(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator: retry async LLM calls with exponential backoff.

    Retries on: RateLimitError, InternalServerError, ReadTimeout, ConnectTimeout.
    Fails immediately on: AuthenticationError, BadRequestError, ValidationError.

    Reads settings at decoration time for max_attempts and base_wait.
    Wraps calls with asyncio.wait_for() for per-call timeout.

    Args:
        func: Async function making LLM API calls.

    Returns:
        Wrapped function with retry logic.
    """
    settings = get_settings()
    call_timeout = settings.llm_retry_call_timeout

    @retry(
        stop=stop_after_attempt(settings.llm_retry_max_attempts),
        wait=wait_exponential(
            multiplier=settings.llm_retry_base_wait,
            max=10,
        ),
        retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
        before_sleep=_log_retry_attempt,
        retry_error_callback=_log_final_failure,
        reraise=True,
    )
    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        return await asyncio.wait_for(
            func(*args, **kwargs),
            timeout=call_timeout,
        )

    return wrapper
