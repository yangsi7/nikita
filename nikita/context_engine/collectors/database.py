"""Database collector for Context Engine (Spec 039).

Collects user, metrics, and vice data from Supabase PostgreSQL.
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from nikita.context_engine.collectors.base import BaseCollector, CollectorContext
from nikita.context_engine.models import ViceProfile
from nikita.db.models.user import User, UserMetrics, UserVicePreference
from nikita.db.repositories.engagement_repository import EngagementStateRepository
from nikita.db.repositories.metrics_repository import UserMetricsRepository
from nikita.db.repositories.user_repository import UserRepository
from nikita.db.repositories.vice_repository import VicePreferenceRepository


class UserData(BaseModel):
    """User data from database."""

    # Core game state
    chapter: int = Field(default=1, ge=1, le=5)
    chapter_name: str = Field(default="Curiosity")
    relationship_score: Decimal = Field(default=Decimal("50.00"))
    boss_attempts: int = Field(default=0, ge=0)
    game_status: str = Field(default="active")
    days_played: int = Field(default=0, ge=0)

    # Timestamps
    created_at: datetime | None = None
    last_interaction_at: datetime | None = None
    onboarded_at: datetime | None = None

    # Settings
    timezone: str = Field(default="UTC")
    notifications_enabled: bool = Field(default=True)

    # Onboarding
    onboarding_status: str = Field(default="pending")
    onboarding_profile: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_model(cls, user: User) -> "UserData":
        """Create UserData from SQLAlchemy model."""
        chapter_names = {
            1: "Curiosity",
            2: "Testing",
            3: "Depth",
            4: "Authenticity",
            5: "Commitment",
        }
        return cls(
            chapter=user.chapter,
            chapter_name=chapter_names.get(user.chapter, "Curiosity"),
            relationship_score=user.relationship_score,
            boss_attempts=user.boss_attempts,
            game_status=user.game_status,
            days_played=user.days_played,
            created_at=user.created_at,
            last_interaction_at=user.last_interaction_at,
            onboarded_at=user.onboarded_at,
            timezone=user.timezone or "UTC",
            notifications_enabled=user.notifications_enabled if user.notifications_enabled is not None else True,
            onboarding_status=user.onboarding_status or "pending",
            onboarding_profile=user.onboarding_profile or {},
        )


class MetricsData(BaseModel):
    """User metrics from database."""

    intimacy: Decimal = Field(default=Decimal("50.00"))
    passion: Decimal = Field(default=Decimal("50.00"))
    trust: Decimal = Field(default=Decimal("50.00"))
    secureness: Decimal = Field(default=Decimal("50.00"))

    @classmethod
    def from_model(cls, metrics: UserMetrics | None) -> "MetricsData":
        """Create MetricsData from SQLAlchemy model."""
        if metrics is None:
            return cls()
        return cls(
            intimacy=metrics.intimacy,
            passion=metrics.passion,
            trust=metrics.trust,
            secureness=metrics.secureness,
        )


class EngagementData(BaseModel):
    """Engagement state from database."""

    state: str = Field(default="calibrating")
    calibration_score: Decimal = Field(default=Decimal("0.50"))
    multiplier: Decimal = Field(default=Decimal("0.90"))
    consecutive_in_zone: int = Field(default=0)
    last_transition: datetime | None = None


class DatabaseCollectorOutput(BaseModel):
    """Output from DatabaseCollector."""

    user: UserData
    metrics: MetricsData
    vice_profile: ViceProfile
    engagement: EngagementData
    total_conversations: int = Field(default=0)
    total_words_exchanged: int = Field(default=0)


class DatabaseCollector(BaseCollector[DatabaseCollectorOutput]):
    """Collector that gathers user data from Supabase.

    Collects:
    - User entity (chapter, score, status)
    - UserMetrics (4 metrics)
    - VicePreferences (8 categories)
    - EngagementState (FSM state)
    """

    name = "database"
    timeout_seconds = 5.0
    max_retries = 2

    async def collect(self, ctx: CollectorContext) -> DatabaseCollectorOutput:
        """Collect user, metrics, and vices from database.

        Args:
            ctx: Collector context with session and user_id.

        Returns:
            DatabaseCollectorOutput with all user data.

        Raises:
            ValueError: If user not found.
        """
        # Initialize repositories
        user_repo = UserRepository(ctx.session)
        metrics_repo = UserMetricsRepository(ctx.session)
        vice_repo = VicePreferenceRepository(ctx.session)
        engagement_repo = EngagementStateRepository(ctx.session)

        # Get user with eager-loaded relationships
        user = await user_repo.get(ctx.user_id)
        if user is None:
            raise ValueError(f"User {ctx.user_id} not found")

        # Convert to data models
        user_data = UserData.from_model(user)
        metrics_data = MetricsData.from_model(user.metrics)

        # Build vice profile from preferences
        vice_profile = await self._build_vice_profile(vice_repo, ctx.user_id)

        # Get engagement state
        engagement_data = await self._get_engagement_data(engagement_repo, ctx.user_id)

        # Count conversations and words (simple estimate)
        total_conversations = await self._count_conversations(ctx)
        total_words = await self._estimate_words(ctx)

        return DatabaseCollectorOutput(
            user=user_data,
            metrics=metrics_data,
            vice_profile=vice_profile,
            engagement=engagement_data,
            total_conversations=total_conversations,
            total_words_exchanged=total_words,
        )

    async def _build_vice_profile(
        self,
        vice_repo: VicePreferenceRepository,
        user_id,
    ) -> ViceProfile:
        """Build ViceProfile from user preferences."""
        preferences = await vice_repo.get_active(user_id)

        # Map category -> intensity
        profile_data = {
            "intellectual_dominance": 0,
            "risk_taking": 0,
            "substances": 0,
            "sexuality": 0,
            "emotional_intensity": 0,
            "rule_breaking": 0,
            "dark_humor": 0,
            "vulnerability": 0,
        }

        for pref in preferences:
            if pref.category in profile_data:
                profile_data[pref.category] = pref.intensity_level

        return ViceProfile(**profile_data)

    async def _get_engagement_data(
        self,
        engagement_repo: EngagementStateRepository,
        user_id,
    ) -> EngagementData:
        """Get engagement state for user."""
        state = await engagement_repo.get_by_user_id(user_id)
        if state is None:
            return EngagementData()

        return EngagementData(
            state=state.state,
            calibration_score=state.calibration_score,
            multiplier=state.multiplier,
            consecutive_in_zone=state.consecutive_in_zone,
            last_transition=state.last_calculated_at,
        )

    async def _count_conversations(self, ctx: CollectorContext) -> int:
        """Count total conversations for user."""
        from sqlalchemy import func, select

        from nikita.db.models.conversation import Conversation

        stmt = select(func.count()).select_from(Conversation).where(Conversation.user_id == ctx.user_id)
        result = await ctx.session.execute(stmt)
        return result.scalar() or 0

    async def _estimate_words(self, ctx: CollectorContext) -> int:
        """Estimate total words exchanged (simplified)."""
        # This is a simplified estimate - could query message_embeddings for accuracy
        from sqlalchemy import func, select

        from nikita.db.models.conversation import Conversation

        # Count conversations and multiply by average message count
        count = await self._count_conversations(ctx)
        return count * 50  # Rough estimate: 50 words per conversation

    def get_fallback(self) -> DatabaseCollectorOutput:
        """Return safe default data if collection fails."""
        return DatabaseCollectorOutput(
            user=UserData(),
            metrics=MetricsData(),
            vice_profile=ViceProfile(),
            engagement=EngagementData(),
            total_conversations=0,
            total_words_exchanged=0,
        )
