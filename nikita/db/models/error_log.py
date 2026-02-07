"""Error logging model for admin dashboard monitoring.

Created as part of Issue #19 - Error logging infrastructure.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from nikita.db.models.base import Base


class ErrorLevel(str, Enum):
    """Error severity levels."""

    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ErrorLog(Base):
    """
    Error log entry for system-wide error tracking.

    Used by the admin dashboard to display and filter errors,
    track resolution status, and analyze error patterns.
    """

    __tablename__ = "error_logs"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default="gen_random_uuid()",
    )

    level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ErrorLevel.ERROR.value,
        doc="Error severity: critical, error, warning, info",
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Human-readable error message",
    )

    source: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        doc="Module/function path where error occurred",
    )

    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="User associated with error (if applicable)",
    )

    conversation_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        nullable=True,
        doc="Conversation where error occurred (if applicable)",
    )

    stack_trace: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Full stack trace for debugging",
    )

    context: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        doc="Additional context (request data, state, etc.)",
    )

    resolved: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="Whether the error has been resolved",
    )

    resolution_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        doc="Notes about how the error was resolved",
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
        doc="When the error occurred",
    )

    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When the error was resolved",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
        doc="When this log entry was created",
    )

    def __repr__(self) -> str:
        return f"<ErrorLog {self.id} [{self.level}] {self.source}>"
