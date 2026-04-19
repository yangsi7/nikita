"""Job execution tracking model for admin debug portal.

Tracks execution history of scheduled jobs (decay, deliver, summary, cleanup,
process-conversations) for monitoring and debugging.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from sqlalchemy import DateTime, Integer, Numeric, String
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
    REFRESH_VOICE_PROMPTS = "refresh_voice_prompts"  # Spec 209: Voice prompt refresh cron
    HEARTBEAT = "heartbeat"  # Spec 215 PR 215-D: Hourly heartbeat tick (FR-005 safety net)
    GENERATE_DAILY_ARCS = "generate_daily_arcs"  # Spec 215 PR 215-D: Daily-arc generation cron
    HANDOFF_GREETING_BACKSTOP = "handoff_greeting_backstop"  # Spec 214 T4.4: FR-11e backstop cron


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

    # Spec 215 B2 (GH #336): cost ledger for FR-014 daily cost circuit breaker.
    # Populated by jobs that incur LLM spend (e.g. generate_daily_arcs); summed
    # by JobExecutionRepository.get_today_cost_usd().
    cost_usd: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<JobExecution {self.job_name} {self.status} @ {self.started_at}>"
