"""User-related database models."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nikita.db.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from nikita.db.models.context import ConversationThread, NikitaThought
    from nikita.db.models.conversation import Conversation
    from nikita.db.models.engagement import EngagementHistory, EngagementState
    from nikita.db.models.game import DailySummary, ScoreHistory
    from nikita.db.models.generated_prompt import GeneratedPrompt
    from nikita.db.models.narrative_arc import UserNarrativeArc
    from nikita.db.models.profile import UserBackstory, UserProfile
    from nikita.db.models.scheduled_event import ScheduledEvent
    from nikita.db.models.scheduled_touchpoint import ScheduledTouchpoint
    from nikita.db.models.memory_fact import MemoryFact
    from nikita.db.models.ready_prompt import ReadyPrompt
    from nikita.db.models.social_circle import UserSocialCircle


class User(Base, TimestampMixin):
    """
    Core user state table.

    Links to Supabase Auth via id (auth.users.id).
    Stores game progress, relationship score, and settings.
    """

    __tablename__ = "users"

    # Primary key matches Supabase Auth user ID
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)

    # Platform identifiers (BigInteger for Telegram IDs > 2^31)
    telegram_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, nullable=True)
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
    # Spec 049 P8: Dedicated timestamp for boss fight start (replaces generic updated_at)
    boss_fight_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Neo4j Aura/Graphiti reference
    graphiti_group_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Voice prompt caching (FR-034: enables <100ms pre-call response)
    cached_voice_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    cached_voice_prompt_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    cached_voice_context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # User settings
    timezone: Mapped[str] = mapped_column(String(50), default="UTC", nullable=False)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Voice onboarding (Spec 028)
    onboarding_status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
    )
    onboarding_profile: Mapped[dict | None] = mapped_column(JSONB, default=dict, nullable=True)
    onboarded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    onboarding_call_id: Mapped[str | None] = mapped_column(Text, nullable=True)

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
    conversation_threads: Mapped[list["ConversationThread"]] = relationship(
        "ConversationThread",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    thoughts: Mapped[list["NikitaThought"]] = relationship(
        "NikitaThought",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    engagement_state: Mapped["EngagementState"] = relationship(
        "EngagementState",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    engagement_history: Mapped[list["EngagementHistory"]] = relationship(
        "EngagementHistory",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    generated_prompts: Mapped[list["GeneratedPrompt"]] = relationship(
        "GeneratedPrompt",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    profile: Mapped["UserProfile"] = relationship(
        "UserProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    backstory: Mapped["UserBackstory"] = relationship(
        "UserBackstory",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    scheduled_events: Mapped[list["ScheduledEvent"]] = relationship(
        "ScheduledEvent",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    scheduled_touchpoints: Mapped[list["ScheduledTouchpoint"]] = relationship(
        "ScheduledTouchpoint",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    # Spec 035: Social circle and narrative arcs
    social_circle: Mapped[list["UserSocialCircle"]] = relationship(
        "UserSocialCircle",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    narrative_arcs: Mapped[list["UserNarrativeArc"]] = relationship(
        "UserNarrativeArc",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    # Spec 042: Unified pipeline
    memory_facts: Mapped[list["MemoryFact"]] = relationship(
        "MemoryFact",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    ready_prompts: Mapped[list["ReadyPrompt"]] = relationship(
        "ReadyPrompt",
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
        CheckConstraint(
            "onboarding_status IN ('pending', 'in_progress', 'completed', 'skipped')",
            name="check_onboarding_status_values",
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
