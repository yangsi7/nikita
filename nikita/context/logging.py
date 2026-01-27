"""Structured logging configuration for pipeline.

This module configures structlog for JSON-formatted logging with
conversation correlation IDs.
"""

import logging
from typing import TYPE_CHECKING
from uuid import UUID

import structlog

if TYPE_CHECKING:
    from structlog.typing import EventDict


def configure_pipeline_logging(json_format: bool = True) -> None:
    """Configure structured logging for the pipeline.

    Args:
        json_format: If True, output logs as JSON. If False, use console format.
    """
    processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_pipeline_logger(
    conversation_id: UUID,
    stage: str | None = None,
) -> structlog.BoundLogger:
    """Get a logger with conversation context bound.

    Args:
        conversation_id: The conversation ID for correlation
        stage: Optional stage name to include

    Returns:
        A bound logger with context fields
    """
    logger = structlog.get_logger()
    bound_logger = logger.bind(
        conversation_id=str(conversation_id),
        pipeline="post_processing",
    )
    if stage:
        bound_logger = bound_logger.bind(stage=stage)
    return bound_logger


def log_stage_start(
    logger: structlog.BoundLogger,
    stage_name: str,
    is_critical: bool = False,
) -> None:
    """Log the start of a pipeline stage.

    Args:
        logger: The bound logger to use
        stage_name: Name of the stage
        is_critical: Whether this stage is critical
    """
    logger.info(
        "stage_started",
        stage=stage_name,
        is_critical=is_critical,
    )


def log_stage_complete(
    logger: structlog.BoundLogger,
    stage_name: str,
    duration_ms: float,
    success: bool = True,
    error: str | None = None,
) -> None:
    """Log the completion of a pipeline stage.

    Args:
        logger: The bound logger to use
        stage_name: Name of the stage
        duration_ms: How long the stage took
        success: Whether the stage succeeded
        error: Error message if failed
    """
    if success:
        logger.info(
            "stage_completed",
            stage=stage_name,
            duration_ms=round(duration_ms, 2),
            success=True,
        )
    else:
        logger.error(
            "stage_failed",
            stage=stage_name,
            duration_ms=round(duration_ms, 2),
            success=False,
            error=error,
        )
