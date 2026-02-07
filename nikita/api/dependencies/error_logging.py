"""Error logging utility for system-wide error tracking.

Created as part of Issue #19 - Error logging infrastructure.
Provides a centralized way to log errors to the database for admin monitoring.
"""

import logging
import traceback
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.error_log import ErrorLevel, ErrorLog

logger = logging.getLogger(__name__)


async def log_error(
    session: AsyncSession,
    message: str,
    source: str,
    level: ErrorLevel = ErrorLevel.ERROR,
    user_id: UUID | None = None,
    conversation_id: UUID | None = None,
    exception: Exception | None = None,
    context: dict[str, Any] | None = None,
    commit: bool = True,
) -> ErrorLog:
    """
    Log an error to the database for admin dashboard monitoring.

    Args:
        session: Database session
        message: Human-readable error message
        source: Module/function path (e.g., "nikita.api.routes.voice:webhook")
        level: Error severity level
        user_id: User associated with error (if applicable)
        conversation_id: Conversation where error occurred (if applicable)
        exception: Exception object for stack trace extraction
        context: Additional context dictionary
        commit: Whether to commit the transaction (default True)

    Returns:
        The created ErrorLog entry
    """
    stack_trace = None
    if exception:
        stack_trace = "".join(
            traceback.format_exception(type(exception), exception, exception.__traceback__)
        )

    error_log = ErrorLog(
        level=level.value,
        message=message,
        source=source,
        user_id=user_id,
        conversation_id=conversation_id,
        stack_trace=stack_trace,
        context=context or {},
        occurred_at=datetime.now(timezone.utc),
    )

    session.add(error_log)

    if commit:
        await session.commit()
        await session.refresh(error_log)

    # Also log to standard logger for immediate visibility
    log_method = getattr(logger, level.value, logger.error)
    log_method(f"[{source}] {message}", exc_info=exception is not None)

    return error_log


async def log_critical(
    session: AsyncSession,
    message: str,
    source: str,
    **kwargs: Any,
) -> ErrorLog:
    """Log a critical error. Shorthand for log_error with CRITICAL level."""
    return await log_error(session, message, source, level=ErrorLevel.CRITICAL, **kwargs)


async def log_warning(
    session: AsyncSession,
    message: str,
    source: str,
    **kwargs: Any,
) -> ErrorLog:
    """Log a warning. Shorthand for log_error with WARNING level."""
    return await log_error(session, message, source, level=ErrorLevel.WARNING, **kwargs)


async def get_recent_errors(
    session: AsyncSession,
    limit: int = 50,
    level: ErrorLevel | None = None,
    source_filter: str | None = None,
    user_id: UUID | None = None,
    include_resolved: bool = False,
) -> list[ErrorLog]:
    """
    Get recent errors for admin dashboard display.

    Args:
        session: Database session
        limit: Maximum number of errors to return
        level: Filter by error level
        source_filter: Filter by source (partial match)
        user_id: Filter by user ID
        include_resolved: Whether to include resolved errors

    Returns:
        List of ErrorLog entries, ordered by occurred_at DESC
    """
    from sqlalchemy import desc, select

    query = select(ErrorLog)

    if not include_resolved:
        query = query.where(ErrorLog.resolved == False)  # noqa: E712

    if level:
        query = query.where(ErrorLog.level == level.value)

    if source_filter:
        query = query.where(ErrorLog.source.ilike(f"%{source_filter}%"))

    if user_id:
        query = query.where(ErrorLog.user_id == user_id)

    query = query.order_by(desc(ErrorLog.occurred_at)).limit(limit)

    result = await session.execute(query)
    return list(result.scalars().all())


async def resolve_error(
    session: AsyncSession,
    error_id: UUID,
    resolution_notes: str | None = None,
    commit: bool = True,
) -> ErrorLog | None:
    """
    Mark an error as resolved.

    Args:
        session: Database session
        error_id: ID of the error to resolve
        resolution_notes: Optional notes about how it was resolved
        commit: Whether to commit the transaction

    Returns:
        The updated ErrorLog entry, or None if not found
    """
    from sqlalchemy import select

    result = await session.execute(select(ErrorLog).where(ErrorLog.id == error_id))
    error_log = result.scalar_one_or_none()

    if error_log:
        error_log.resolved = True
        error_log.resolved_at = datetime.now(timezone.utc)
        if resolution_notes:
            error_log.resolution_notes = resolution_notes

        if commit:
            await session.commit()

    return error_log


async def get_error_stats(session: AsyncSession, hours: int = 24) -> dict[str, Any]:
    """
    Get error statistics for admin dashboard overview.

    Args:
        session: Database session
        hours: Time window for statistics

    Returns:
        Dictionary with error counts by level and source
    """
    from datetime import timedelta

    from sqlalchemy import func, select

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

    # Count by level
    level_query = (
        select(ErrorLog.level, func.count(ErrorLog.id))
        .where(ErrorLog.occurred_at >= cutoff)
        .group_by(ErrorLog.level)
    )
    level_result = await session.execute(level_query)
    level_counts = {row[0]: row[1] for row in level_result.fetchall()}

    # Count by source (top 5)
    source_query = (
        select(ErrorLog.source, func.count(ErrorLog.id))
        .where(ErrorLog.occurred_at >= cutoff)
        .group_by(ErrorLog.source)
        .order_by(func.count(ErrorLog.id).desc())
        .limit(5)
    )
    source_result = await session.execute(source_query)
    top_sources = [{"source": row[0], "count": row[1]} for row in source_result.fetchall()]

    # Total and unresolved counts
    total_query = select(func.count(ErrorLog.id)).where(ErrorLog.occurred_at >= cutoff)
    total_result = await session.execute(total_query)
    total_count = total_result.scalar() or 0

    unresolved_query = (
        select(func.count(ErrorLog.id))
        .where(ErrorLog.occurred_at >= cutoff)
        .where(ErrorLog.resolved == False)  # noqa: E712
    )
    unresolved_result = await session.execute(unresolved_query)
    unresolved_count = unresolved_result.scalar() or 0

    return {
        "total": total_count,
        "unresolved": unresolved_count,
        "by_level": level_counts,
        "top_sources": top_sources,
        "time_window_hours": hours,
    }
