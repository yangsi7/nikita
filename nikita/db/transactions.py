"""Transaction utilities for atomic database operations.

T12: Transaction Management
- @atomic decorator for transaction wrapping
- Nested transaction support via SAVEPOINTs
- Deadlock detection with exponential backoff retry
- Configurable isolation levels
"""

import asyncio
import functools
import logging
from collections.abc import Callable
from enum import Enum
from typing import Any, ParamSpec, TypeVar

from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


class IsolationLevel(str, Enum):
    """Database transaction isolation levels."""

    READ_COMMITTED = "READ COMMITTED"
    REPEATABLE_READ = "REPEATABLE READ"
    SERIALIZABLE = "SERIALIZABLE"


# Default configuration
DEFAULT_ISOLATION_LEVEL = IsolationLevel.READ_COMMITTED
DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 0.1  # 100ms


def is_deadlock_error(error: Exception) -> bool:
    """Check if an error is a deadlock or serialization failure.

    Args:
        error: The exception to check.

    Returns:
        True if error indicates deadlock/serialization failure.
    """
    if isinstance(error, OperationalError):
        # PostgreSQL deadlock detected
        error_code = getattr(error.orig, "pgcode", None)
        if error_code in ("40001", "40P01"):  # serialization_failure, deadlock_detected
            return True

        # Check message for deadlock indicators
        error_msg = str(error).lower()
        if "deadlock" in error_msg or "serialization" in error_msg:
            return True

    return False


def atomic(
    isolation_level: IsolationLevel = DEFAULT_ISOLATION_LEVEL,
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator to wrap function in a transaction with retry logic.

    AC-T12.1: Wraps function in transaction
    AC-T12.2: Nested transactions use SAVEPOINTs
    AC-T12.3: Failed transactions rollback completely
    AC-T12.4: Deadlock detection with exponential backoff retry
    AC-T12.5: Transaction isolation level configurable

    Args:
        isolation_level: Transaction isolation level (default: READ COMMITTED).
        max_retries: Maximum retry attempts for deadlocks (default: 3).
        base_delay: Base delay for exponential backoff in seconds.

    Returns:
        Decorated function that executes within a transaction.

    Example:
        @atomic(isolation_level=IsolationLevel.SERIALIZABLE)
        async def transfer_funds(
            session: AsyncSession, from_id: UUID, to_id: UUID, amount: Decimal
        ):
            # This entire function runs in a transaction
            # If a deadlock occurs, it will retry up to 3 times
            ...
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Find session in args or kwargs
            session: AsyncSession | None = None
            for arg in args:
                if isinstance(arg, AsyncSession):
                    session = arg
                    break
            if session is None:
                session = kwargs.get("session")
            if session is None:
                raise ValueError(
                    "atomic decorator requires AsyncSession as first arg or 'session' kwarg"
                )

            # Retry loop for deadlock handling
            last_error: Exception | None = None
            for attempt in range(max_retries + 1):
                try:
                    # Check if we're already in a transaction (nested)
                    if session.in_transaction():
                        # AC-T12.2: Use SAVEPOINT for nested transactions
                        async with session.begin_nested():
                            return await func(*args, **kwargs)
                    else:
                        # Start new transaction with isolation level
                        async with session.begin():
                            # Set isolation level if not default
                            if isolation_level != IsolationLevel.READ_COMMITTED:
                                await session.execute(
                                    f"SET TRANSACTION ISOLATION LEVEL {isolation_level.value}"
                                )
                            return await func(*args, **kwargs)

                except Exception as e:
                    # AC-T12.3: Rollback happens automatically via context manager
                    last_error = e

                    # AC-T12.4: Retry on deadlock with exponential backoff
                    if is_deadlock_error(e) and attempt < max_retries:
                        delay = base_delay * (2**attempt)
                        logger.warning(
                            f"Deadlock detected (attempt {attempt + 1}/{max_retries + 1}), "
                            f"retrying in {delay:.2f}s: {e}"
                        )
                        await asyncio.sleep(delay)
                        continue

                    # Non-deadlock error or max retries exceeded
                    raise

            # Should not reach here, but just in case
            if last_error:
                raise last_error
            raise RuntimeError("Unexpected state in atomic decorator")

        return wrapper  # type: ignore

    return decorator


async def run_in_transaction(
    session: AsyncSession,
    func: Callable[..., Any],
    *args: Any,
    isolation_level: IsolationLevel = DEFAULT_ISOLATION_LEVEL,
    **kwargs: Any,
) -> Any:
    """Run a function within a transaction.

    Alternative to @atomic decorator for dynamic transaction control.

    Args:
        session: The async session to use.
        func: Async function to execute.
        *args: Arguments to pass to function.
        isolation_level: Transaction isolation level.
        **kwargs: Keyword arguments to pass to function.

    Returns:
        Result of the function.
    """

    @atomic(isolation_level=isolation_level)
    async def _wrapped(session: AsyncSession) -> Any:
        return await func(session, *args, **kwargs)

    return await _wrapped(session)
