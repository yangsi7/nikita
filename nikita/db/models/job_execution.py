"""Job execution tracking model for admin debug portal.

Tracks execution history of scheduled jobs (decay, deliver, summary, cleanup,
process-conversations) for monitoring and debugging.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from nikita.db.models.base import Base, TimestampMixin, UUIDMixin


class JobName(str, Enum):
    """Scheduled job types tracked in the system."""

    DECAY = "decay"
    DELIVER = "deliver"
    SUMMARY = "summary"
    CLEANUP = "cleanup"
    PROCESS_CONVERSATIONS = "process-conversations"
    POST_PROCESSING = "post_processing"  # Spec 031: Individual conversation processing
    PSYCHE_BATCH = "psyche_batch"  # Spec 056: Daily psyche state generation


class JobStatus(str, Enum):
    """Job execution status."""

    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class JobExecution(Base, UUIDMixin, TimestampMixin):
    """
    Tracks execution history of scheduled jobs.

    Used by admin debug portal to monitor job status and identify issues.
    Each row represents a single job execution attempt.
    """

    __tablename__ = "job_executions"

    # Job identification
    job_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    # Execution timing
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=JobStatus.RUNNING.value,
    )

    # Results and metrics
    result: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
    )
    duration_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<JobExecution {self.job_name} {self.status} @ {self.started_at}>"
