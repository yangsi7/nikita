"""Game state and history models."""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nikita.db.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from nikita.db.models.user import User


class ScoreHistory(Base, UUIDMixin):
    """
    Score history for tracking and graphs.

    Records every score change with context about
    what caused the change.
    """

    __tablename__ = "score_history"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Score snapshot
    score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    chapter: Mapped[int] = mapped_column(Integer, nullable=False)

    # Event type and details
    event_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )  # 'conversation' | 'decay' | 'boss_pass' | 'boss_fail'
    event_details: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )  # Store deltas, reasons

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="score_history")


# Event types for score history
SCORE_EVENT_TYPES = [
    "conversation",  # Score changed from conversation
    "decay",  # Daily decay applied
    "boss_pass",  # Passed boss encounter
    "boss_fail",  # Failed boss encounter
    "chapter_advance",  # Advanced to new chapter
    "manual_adjustment",  # Admin adjustment
]


class DailySummary(Base, UUIDMixin):
    """
    Daily summary with Nikita's in-character recap.

    Generates a personalized daily summary in Nikita's voice
    recapping the day's interactions and score changes.
    """

    __tablename__ = "daily_summaries"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Date tracking
    date: Mapped[date] = mapped_column(Date, nullable=False)

    # Score tracking
    score_start: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    score_end: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    decay_applied: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)

    # Interaction stats
    conversations_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Nikita's in-character summary
    nikita_summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Key events of the day
    key_events: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="daily_summaries")

    @property
    def score_change(self) -> Decimal | None:
        """Calculate net score change for the day."""
        if self.score_start is not None and self.score_end is not None:
            return self.score_end - self.score_start
        return None
