"""User-related database models."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nikita.db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from nikita.db.models.conversation import Conversation
    from nikita.db.models.game import DailySummary, ScoreHistory


class User(Base, TimestampMixin):
    """
    Core user state table.

    Links to Supabase Auth via id (auth.users.id).
    Stores game progress, relationship score, and settings.
    """

    __tablename__ = "users"

    # Primary key matches Supabase Auth user ID
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)

    # Platform identifiers
    telegram_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Game state
    relationship_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("50.00"),
        nullable=False,
    )
    chapter: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    boss_attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    days_played: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    last_interaction_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    game_status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        nullable=False,
    )

    # FalkorDB/Graphiti reference
    graphiti_group_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    # User settings
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    metrics: Mapped["UserMetrics"] = relationship(
        "UserMetrics",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    vice_preferences: Mapped[list["UserVicePreference"]] = relationship(
        "UserVicePreference",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        "Conversation",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    score_history: Mapped[list["ScoreHistory"]] = relationship(
        "ScoreHistory",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    daily_summaries: Mapped[list["DailySummary"]] = relationship(
        "DailySummary",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint("chapter BETWEEN 1 AND 5", name="check_chapter_range"),
        CheckConstraint("boss_attempts BETWEEN 0 AND 3", name="check_boss_attempts_range"),
        CheckConstraint(
            "game_status IN ('active', 'boss_fight', 'game_over', 'won')",
            name="check_game_status_values",
        ),
    )


class UserMetrics(Base, TimestampMixin):
    """
    Hidden sub-metrics for relationship scoring.

    These metrics are not shown to the player but influence
    the composite relationship_score.
    """

    __tablename__ = "user_metrics"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # Hidden metrics (0-100 scale)
    intimacy: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("50.00"),
        nullable=False,
    )
    passion: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("50.00"),
        nullable=False,
    )
    trust: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("50.00"),
        nullable=False,
    )
    secureness: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("50.00"),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="metrics")

    def calculate_composite_score(self) -> Decimal:
        """
        Calculate composite relationship score from sub-metrics.

        Formula: intimacy * 0.30 + passion * 0.25 + trust * 0.25 + secureness * 0.20
        """
        return (
            self.intimacy * Decimal("0.30")
            + self.passion * Decimal("0.25")
            + self.trust * Decimal("0.25")
            + self.secureness * Decimal("0.20")
        )


class UserVicePreference(Base, TimestampMixin):
    """
    Vice preference tracking for personalization.

    Tracks player engagement with 8 vice categories
    to customize Nikita's behavior and conversations.
    """

    __tablename__ = "user_vice_preferences"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Vice category (one of 8)
    category: Mapped[str] = mapped_column(String(50), nullable=False)

    # Tracking
    intensity_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    engagement_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="vice_preferences")

    __table_args__ = (
        CheckConstraint("intensity_level BETWEEN 1 AND 5", name="check_intensity_level_range"),
    )


# Vice categories (8 total, no moderation)
VICE_CATEGORIES = [
    "intellectual_dominance",  # Enjoys being challenged intellectually
    "risk_taking",  # Attracted to danger, risk-taking behavior
    "substances",  # Open discussion of drugs, alcohol
    "sexuality",  # Sexual content and innuendo
    "emotional_intensity",  # Deep emotional exchanges
    "rule_breaking",  # Anti-authority, breaking norms
    "dark_humor",  # Morbid, dark jokes
    "vulnerability",  # Emotional openness, sharing fears
]
