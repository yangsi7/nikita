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

    @pytest.mark.asyncio
    async def test_update_onboarding_profile_key_stores_native_json_types(
        self, user_repo: UserRepository, test_telegram_id: int
    ):
        """GH #318 real-DB regression guard.

        Verifies `update_onboarding_profile_key` stores Python values as their
        native JSON types (number, string, object), NOT as JSON strings.

        Pre-fix (GH #318): stored `{"age":"28"}` (string) instead of
        `{"age":28}` (number), because `cast(json.dumps(value), JSONB)`
        double-encoded through asyncpg's JSONB codec. Downstream
        `_age_bucket(profile["age"])` then TypeError'd comparing str to int.
        All three prior bugs in the #313 -> #316 -> #318 chain evaded
        mock-only tests; this test hits asyncpg end-to-end.
        """
        user_id = uuid4()
        user = await user_repo.create_with_metrics(
            user_id=user_id,
            telegram_id=test_telegram_id,
        )

        # Integer value: must store as JSON number, not JSON string.
        await user_repo.update_onboarding_profile_key(user.id, "age", 28)
        await user_repo.session.commit()

        result = await user_repo.session.execute(
            text(
                "SELECT jsonb_typeof(onboarding_profile->'age') AS age_type, "
                "(onboarding_profile->>'age')::int AS age_int "
                "FROM users WHERE id = :uid"
            ),
            {"uid": user.id},
        )
        row = result.mappings().first()
        assert row is not None
        assert row["age_type"] == "number", (
            f"age should be JSON number, got {row['age_type']!r} "
            "(pre-fix bug stored as string)"
        )
        assert row["age_int"] == 28

        # String value: must store as JSON string (unescaped), not double-quoted.
        await user_repo.update_onboarding_profile_key(user.id, "name", "Simon")
        await user_repo.session.commit()

        result = await user_repo.session.execute(
            text(
                "SELECT jsonb_typeof(onboarding_profile->'name') AS name_type, "
                "onboarding_profile->>'name' AS name_val "
                "FROM users WHERE id = :uid"
            ),
            {"uid": user.id},
        )
        row = result.mappings().first()
        assert row is not None
        assert row["name_type"] == "string"
        assert row["name_val"] == "Simon", (
            f"name should be 'Simon', got {row['name_val']!r} "
            "(pre-fix bug stored as double-quoted JSON-encoded form)"
        )

        # Dict value: must store as JSON object, not JSON string blob.
        await user_repo.update_onboarding_profile_key(
            user.id, "meta", {"venues": ["Berghain"], "count": 3}
        )
        await user_repo.session.commit()

        result = await user_repo.session.execute(
            text(
                "SELECT jsonb_typeof(onboarding_profile->'meta') AS meta_type, "
                "(onboarding_profile->'meta'->>'count')::int AS meta_count "
                "FROM users WHERE id = :uid"
            ),
            {"uid": user.id},
        )
        row = result.mappings().first()
        assert row is not None
        assert row["meta_type"] == "object"
        assert row["meta_count"] == 3

    @pytest.mark.asyncio
    async def test_update_telegram_id_three_cases(
        self, user_repo: UserRepository, session: AsyncSession
    ):
        """Real-DB regression for GH #321 REQ-4 + REQ-5.

        Covers the three outcome branches of UserRepository.update_telegram_id
        against Postgres with asyncpg — catches the bug class that hit
        GH #316 + GH #318 (SQLAlchemy bind-processor + asyncpg wire-format
        regressions hidden by mock-only unit tests).

        1. Fresh bind: user's telegram_id starts NULL → becomes set →
           returns BindResult.BOUND. Real DB row reflects the new value.
        2. Idempotent re-bind: same user_id re-binds same telegram_id →
           returns BindResult.ALREADY_BOUND_SAME_USER, no state change.
        3. Cross-user conflict: second user tries to claim a telegram_id
           already held by the first user → raises
           TelegramIdAlreadyBoundByOtherUserError carrying the conflicting
           telegram_id.
        """
        from nikita.db.repositories.user_repository import (
            BindResult,
            TelegramIdAlreadyBoundByOtherUserError,
        )

        tid_a = 900_000_000_001  # well above any real Telegram user
        tid_b = 900_000_000_002

        # User A with no telegram_id yet (default None path).
        user_a_id = uuid4()
        user_a = await user_repo.create_with_metrics(user_id=user_a_id, telegram_id=None)
        assert user_a.telegram_id is None

        # Case 1: fresh bind.
        outcome_1 = await user_repo.update_telegram_id(user_a_id, tid_a)
        assert outcome_1 == BindResult.BOUND
        # Verify via a fresh SELECT that the row reflects the bind.
        result = await session.execute(
            text("SELECT telegram_id FROM users WHERE id = :uid"),
            {"uid": user_a_id},
        )
        row = result.mappings().first()
        assert row is not None and row["telegram_id"] == tid_a

        # Case 2: idempotent re-bind.
        outcome_2 = await user_repo.update_telegram_id(user_a_id, tid_a)
        assert outcome_2 == BindResult.ALREADY_BOUND_SAME_USER

        # User B, no telegram_id.
        user_b_id = uuid4()
        user_b = await user_repo.create_with_metrics(user_id=user_b_id, telegram_id=None)
        assert user_b.telegram_id is None

        # Case 3: conflict — User B tries to claim tid_a (held by A).
        with pytest.raises(TelegramIdAlreadyBoundByOtherUserError) as exc_info:
            await user_repo.update_telegram_id(user_b_id, tid_a)
        assert exc_info.value.telegram_id == tid_a

        # User B should be able to bind an unused telegram_id.
        outcome_3 = await user_repo.update_telegram_id(user_b_id, tid_b)
        assert outcome_3 == BindResult.BOUND


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
        assert summary.date == today

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
