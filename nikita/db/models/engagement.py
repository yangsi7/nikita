"""Engagement state and history models (spec 014)."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nikita.db.models.base import Base, UUIDMixin

if TYPE_CHECKING:
    from nikita.db.models.user import User


# Engagement state enum values (spec 014)
ENGAGEMENT_STATES = [
    "calibrating",  # Initial state (days 1-3)
    "in_zone",  # Optimal engagement (multiplier: 1.0)
    "drifting",  # Suboptimal but recoverable (multiplier: 0.9)
    "clingy",  # User too frequent (multiplier: 0.8, 3 days → out_of_zone)
    "distant",  # User too infrequent (multiplier: 0.7, 3 days → out_of_zone)
    "out_of_zone",  # Critical state (multiplier: 0.5)
]


class EngagementState(Base, UUIDMixin):
    """
    User's current engagement state (spec 014).

    Tracks optimal engagement patterns and applies score multipliers
    based on user behavior (message frequency, timing patterns).
    """

    __tablename__ = "engagement_state"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # Current state
    state: Mapped[str] = mapped_column(
        Enum(*ENGAGEMENT_STATES, name="engagement_state_enum"),
        nullable=False,
        default="calibrating",
    )

    # Calibration score (0-1, tracks learning about user's patterns)
    calibration_score: Mapped[Decimal] = mapped_column(
        Numeric(3, 2),
        nullable=False,
        default=Decimal("0.5"),
    )

    # State tracking counters
    consecutive_in_zone: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    consecutive_clingy_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    consecutive_distant_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Score multiplier (0-1, applied to relationship_score changes)
    multiplier: Mapped[Decimal] = mapped_column(
        Numeric(3, 2),
        nullable=False,
        default=Decimal("0.9"),
    )

    # Timestamps
    last_calculated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="engagement_state")


class EngagementHistory(Base, UUIDMixin):
    """
    Historical record of engagement state transitions (spec 014).

    Logs every state change with reason and metrics snapshot
    for analytics and debugging.
    """

    __tablename__ = "engagement_history"

    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # State transition
    from_state: Mapped[str | None] = mapped_column(
        Enum(*ENGAGEMENT_STATES, name="engagement_state_enum"),
        nullable=True,
    )
    to_state: Mapped[str] = mapped_column(
        Enum(*ENGAGEMENT_STATES, name="engagement_state_enum"),
        nullable=False,
    )

    # Reason for transition
    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Metrics snapshot at transition time
    calibration_score: Mapped[Decimal | None] = mapped_column(
        Numeric(3, 2),
        nullable=True,
    )
    clinginess_score: Mapped[Decimal | None] = mapped_column(
        Numeric(3, 2),
        nullable=True,
    )
    neglect_score: Mapped[Decimal | None] = mapped_column(
        Numeric(3, 2),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="engagement_history")


# State multipliers (spec 014-engagement-model)
ENGAGEMENT_MULTIPLIERS = {
    "calibrating": Decimal("0.9"),  # Learning phase
    "in_zone": Decimal("1.0"),  # Optimal
    "drifting": Decimal("0.9"),  # Suboptimal
    "clingy": Decimal("0.8"),  # Too frequent
    "distant": Decimal("0.7"),  # Too infrequent
    "out_of_zone": Decimal("0.5"),  # Critical
}
