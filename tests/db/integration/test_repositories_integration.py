"""Integration tests for repository operations.

T14: Integration Tests
- AC-T14.1: Integration tests use test Supabase project
- AC-T14.3: Transaction tests verify atomic operations
"""

from . import conftest as db_conftest
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.conversation import Conversation
from nikita.db.models.game import DailySummary, ScoreHistory
from nikita.db.models.user import User, UserMetrics, UserVicePreference
from nikita.db.repositories.conversation_repository import ConversationRepository
from nikita.db.repositories.metrics_repository import UserMetricsRepository
from nikita.db.repositories.score_history_repository import ScoreHistoryRepository
from nikita.db.repositories.summary_repository import DailySummaryRepository
from nikita.db.repositories.user_repository import UserRepository
from nikita.db.repositories.vice_repository import VicePreferenceRepository

# Skip all tests if Database unreachable
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not db_conftest._SUPABASE_REACHABLE,
        reason="Database unreachable - skipping integration tests",
    ),
]


class TestUserRepositoryIntegration:
    """Integration tests for UserRepository."""

    @pytest_asyncio.fixture
    async def user_repo(self, session: AsyncSession) -> UserRepository:
        """Create UserRepository with test session."""
        return UserRepository(session)

    @pytest.mark.asyncio
    async def test_create_user_with_metrics(
        self, user_repo: UserRepository, test_telegram_id: int
    ):
        """AC-T14.1: Create user with metrics using real database."""
        user_id = uuid4()
        user = await user_repo.create_with_metrics(
            user_id=user_id,
            telegram_id=test_telegram_id,
        )

        assert user is not None
        assert user.id == user_id
        assert user.telegram_id == test_telegram_id
        assert user.relationship_score == Decimal("50.00")
        assert user.chapter == 1
        assert user.game_status == "active"

    @pytest.mark.asyncio
    async def test_get_by_telegram_id(
        self, user_repo: UserRepository, test_telegram_id: int
    ):
        """AC-T14.1: Get user by Telegram ID."""
        # Create user first
        user_id = uuid4()
        created = await user_repo.create_with_metrics(
            user_id=user_id,
            telegram_id=test_telegram_id,
        )

        # Retrieve by Telegram ID
        retrieved = await user_repo.get_by_telegram_id(test_telegram_id)

        assert retrieved is not None
        assert retrieved.id == created.id

    @pytest.mark.asyncio
    async def test_update_score_atomically(
        self, user_repo: UserRepository, test_telegram_id: int
    ):
        """AC-T14.3: Update score is atomic."""
        user_id = uuid4()
        user = await user_repo.create_with_metrics(
            user_id=user_id,
            telegram_id=test_telegram_id,
        )

        # Update score
        updated = await user_repo.update_score(
            user.id,
            Decimal("5.00"),
            "conversation",
        )

        assert updated.relationship_score == Decimal("55.00")

        # Verify score history was logged
        result = await user_repo.session.execute(
            select(ScoreHistory).where(ScoreHistory.user_id == user.id)
        )
        history = result.scalars().first()
        assert history is not None
        assert history.event_type == "conversation"


class TestConversationRepositoryIntegration:
    """Integration tests for ConversationRepository."""

    @pytest_asyncio.fixture
    async def user(self, session: AsyncSession) -> User:
        """Create a test user."""
        repo = UserRepository(session)
        user_id = uuid4()
        return await repo.create_with_metrics(
            user_id=user_id,
            telegram_id=int(uuid4().int % 1000000000),
        )

    @pytest_asyncio.fixture
    async def conv_repo(self, session: AsyncSession) -> ConversationRepository:
        """Create ConversationRepository with test session."""
        return ConversationRepository(session)

    @pytest.mark.asyncio
    async def test_create_conversation(
        self, conv_repo: ConversationRepository, user: User
    ):
        """AC-T14.1: Create conversation with real database."""
        conv = await conv_repo.create_conversation(
            user_id=user.id,
            platform="telegram",
        )

        assert conv is not None
        assert conv.id is not None
        assert conv.user_id == user.id
        assert conv.platform == "telegram"
        assert conv.messages == []

    @pytest.mark.asyncio
    async def test_append_message_to_jsonb(
        self, conv_repo: ConversationRepository, user: User
    ):
        """AC-T14.1: Append message updates JSONB array."""
        conv = await conv_repo.create_conversation(
            user_id=user.id,
            platform="telegram",
        )

        updated = await conv_repo.append_message(
            conversation_id=conv.id,
            role="user",
            content="Hello Nikita!",
            analysis={"sentiment": "positive"},
        )

        assert len(updated.messages) == 1
        assert updated.messages[0]["role"] == "user"
        assert updated.messages[0]["content"] == "Hello Nikita!"

    @pytest.mark.asyncio
    async def test_get_recent_conversations(
        self, conv_repo: ConversationRepository, user: User
    ):
        """AC-T14.1: Get recent conversations ordered by time."""
        # Create multiple conversations
        for i in range(3):
            await conv_repo.create_conversation(
                user_id=user.id,
                platform="telegram",
            )

        recent = await conv_repo.get_recent(user.id, limit=10)

        assert len(recent) == 3


class TestTransactionAtomicity:
    """Test transaction atomicity across repositories.

    AC-T14.3: Transaction tests verify atomic operations.
    """

    @pytest.mark.asyncio
    async def test_rollback_on_error(self, session: AsyncSession, test_telegram_id: int):
        """Verify transaction rollback on error."""
        user_repo = UserRepository(session)

        # Create user successfully
        user_id = uuid4()
        user = await user_repo.create_with_metrics(
            user_id=user_id,
            telegram_id=test_telegram_id,
        )

        # Try to update with invalid user ID (should fail)
        with pytest.raises(ValueError):
            await user_repo.update_score(
                uuid4(),  # Non-existent user
                Decimal("10.00"),
                "invalid",
            )

        # Original user should still exist (session not corrupted)
        retrieved = await user_repo.get(user.id)
        assert retrieved is not None

    @pytest.mark.asyncio
    async def test_multiple_operations_in_transaction(
        self, session: AsyncSession, test_telegram_id: int
    ):
        """Verify multiple operations are atomic."""
        user_repo = UserRepository(session)
        conv_repo = ConversationRepository(session)
        history_repo = ScoreHistoryRepository(session)

        # Create user
        user_id = uuid4()
        user = await user_repo.create_with_metrics(
            user_id=user_id,
            telegram_id=test_telegram_id,
        )

        # Create conversation
        conv = await conv_repo.create_conversation(
            user_id=user.id,
            platform="telegram",
        )

        # Log score event
        history = await history_repo.log_event(
            user_id=user.id,
            score=Decimal("50.00"),
            chapter=1,
            event_type="conversation",
        )

        # All should be in same transaction
        assert user.id is not None
        assert conv.id is not None
        assert history is not None


class TestMetricsIntegration:
    """Integration tests for UserMetricsRepository."""

    @pytest_asyncio.fixture
    async def user(self, session: AsyncSession) -> User:
        """Create a test user with metrics."""
        repo = UserRepository(session)
        user_id = uuid4()
        return await repo.create_with_metrics(
            user_id=user_id,
            telegram_id=int(uuid4().int % 1000000000),
        )

    @pytest.mark.asyncio
    async def test_update_metrics_with_clamping(
        self, session: AsyncSession, user: User
    ):
        """AC-T14.3: Metrics updates are atomic with clamping."""
        metrics_repo = UserMetricsRepository(session)

        # Get initial metrics
        metrics = await metrics_repo.get_by_user_id(user.id)
        assert metrics is not None

        # Update with clamping
        updated = await metrics_repo.update_metrics(
            user.id,
            intimacy_delta=Decimal("60.00"),  # Would exceed 100
        )

        assert updated.intimacy == Decimal("100.00")  # Clamped

    @pytest.mark.asyncio
    async def test_calculate_composite_score(
        self, session: AsyncSession, user: User
    ):
        """AC-T14.3: Composite score calculation."""
        metrics_repo = UserMetricsRepository(session)

        composite = await metrics_repo.calculate_composite(user.id)

        # Default values: 50, 50, 50, 50
        # Composite = 50*0.30 + 50*0.25 + 50*0.25 + 50*0.20 = 50.00
        assert composite == Decimal("50.00")


class TestVicePreferenceIntegration:
    """Integration tests for VicePreferenceRepository."""

    @pytest_asyncio.fixture
    async def user(self, session: AsyncSession) -> User:
        """Create a test user."""
        repo = UserRepository(session)
        user_id = uuid4()
        return await repo.create_with_metrics(
            user_id=user_id,
            telegram_id=int(uuid4().int % 1000000000),
        )

    @pytest.mark.asyncio
    async def test_discover_and_update_intensity(
        self, session: AsyncSession, user: User
    ):
        """AC-T14.3: Vice discovery and update are atomic."""
        vice_repo = VicePreferenceRepository(session)

        # Discover new vice
        pref = await vice_repo.discover(
            user_id=user.id,
            category="jealousy_triggers",
        )

        assert pref is not None
        assert pref.intensity_level == 1

        # Update intensity
        updated = await vice_repo.update_intensity(pref.id, delta=2)

        assert updated.intensity_level == 3


class TestDailySummaryIntegration:
    """Integration tests for DailySummaryRepository."""

    @pytest_asyncio.fixture
    async def user(self, session: AsyncSession) -> User:
        """Create a test user."""
        repo = UserRepository(session)
        user_id = uuid4()
        return await repo.create_with_metrics(
            user_id=user_id,
            telegram_id=int(uuid4().int % 1000000000),
        )

    @pytest.mark.asyncio
    async def test_create_and_get_summary(
        self, session: AsyncSession, user: User
    ):
        """AC-T14.1: Create and retrieve daily summary."""
        summary_repo = DailySummaryRepository(session)
        today = date.today()

        summary = await summary_repo.create_summary(
            user_id=user.id,
            summary_date=today,
            score_start=Decimal("50.00"),
            score_end=Decimal("55.00"),
            conversations_count=3,
        )

        assert summary is not None
        assert summary.user_id == user.id
        assert summary.summary_date == today

        # Retrieve by date
        retrieved = await summary_repo.get_by_date(user.id, today)
        assert retrieved is not None
        assert retrieved.id == summary.id

    @pytest.mark.asyncio
    async def test_get_range(self, session: AsyncSession, user: User):
        """AC-T14.1: Get summaries in date range."""
        summary_repo = DailySummaryRepository(session)
        today = date.today()

        # Create summaries for 3 days
        for i in range(3):
            await summary_repo.create_summary(
                user_id=user.id,
                summary_date=today - timedelta(days=i),
                score_start=Decimal("50.00"),
                score_end=Decimal("55.00"),
                conversations_count=i + 1,
            )

        # Get range
        summaries = await summary_repo.get_range(
            user.id,
            start_date=today - timedelta(days=2),
            end_date=today,
        )

        assert len(summaries) == 3
