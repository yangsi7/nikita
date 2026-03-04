"""PipelineEvent model for pipeline observability (Spec 110).

Single table for all typed pipeline events. JSONB data field holds
event-specific payloads. 30-day retention via pg_cron.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from nikita.db.models.base import Base


class PipelineEvent(Base):
    """Pipeline observability event.

    Emitted by the orchestrator after each stage completes.
    Buffered in memory, bulk-inserted on pipeline completion.
    """

    __tablename__ = "pipeline_events"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        server_default="gen_random_uuid()",
    )

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    conversation_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
    )

    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Typed event string (e.g., 'extraction.complete')",
    )

    stage: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        doc="Pipeline stage name (nullable for non-pipeline events)",
    )

    data: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        doc="Event-specific payload (max 16KB)",
    )

    duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        doc="Stage execution time in milliseconds",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
    )

    def __repr__(self) -> str:
        return f"<PipelineEvent {self.event_type} user={self.user_id}>"
