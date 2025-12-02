"""Tests for ConversationRepository class.

TDD Tests for T4: Create ConversationRepository

Acceptance Criteria:
- AC-T4.1: create(user_id, platform, started_at) creates new conversation
- AC-T4.2: append_message(conv_id, role, content, analysis) adds message to JSONB
- AC-T4.3: get_recent(user_id, limit=10) returns last N conversations
- AC-T4.4: search(user_id, query) performs full-text search on search_vector
- AC-T4.5: close_conversation(conv_id, score_delta) sets ended_at and score_delta
"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from nikita.db.models.conversation import Conversation
from nikita.db.repositories.conversation_repository import ConversationRepository


class TestConversationRepository:
    """Test suite for ConversationRepository - T4 ACs."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        session = AsyncMock(spec=AsyncSession)
        session.add = MagicMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.get = AsyncMock()
        return session

    @pytest.fixture
    def sample_conversation(self) -> Conversation:
        """Create a sample Conversation entity."""
        conv = MagicMock(spec=Conversation)
        conv.id = uuid4()
        conv.user_id = uuid4()
        conv.platform = "telegram"
        conv.messages = []
        conv.started_at = datetime.now(UTC)
        conv.ended_at = None
        conv.score_delta = None
        conv.is_boss_fight = False
        conv.chapter_at_time = 1
        conv.add_message = MagicMock()
        return conv

    # ========================================
    # AC-T4.1: create(user_id, platform, started_at) creates new conversation
    # ========================================
    @pytest.mark.asyncio
    async def test_create_conversation_basic(self, mock_session: AsyncMock):
        """AC-T4.1: create_conversation creates a new conversation."""
        user_id = uuid4()
        started_at = datetime.now(UTC)

        repo = ConversationRepository(mock_session)

        # Mock the create method from BaseRepository
        mock_session.refresh = AsyncMock()

        result = await repo.create_conversation(
            user_id=user_id,
            platform="telegram",
            started_at=started_at,
        )

        # Verify session operations
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_conversation_with_boss_fight(self, mock_session: AsyncMock):
        """AC-T4.1: create_conversation with boss_fight flag."""
        user_id = uuid4()

        repo = ConversationRepository(mock_session)

        result = await repo.create_conversation(
            user_id=user_id,
            platform="voice",
            is_boss_fight=True,
            chapter_at_time=3,
        )

        # Verify the conversation was added
        mock_session.add.assert_called_once()
        # Get the conversation that was passed to add
        call_args = mock_session.add.call_args[0][0]
        assert call_args.is_boss_fight is True
        assert call_args.chapter_at_time == 3
        assert call_args.platform == "voice"

    @pytest.mark.asyncio
    async def test_create_conversation_defaults_started_at(self, mock_session: AsyncMock):
        """AC-T4.1: create_conversation defaults started_at to now."""
        user_id = uuid4()

        repo = ConversationRepository(mock_session)

        before = datetime.now(UTC)
        result = await repo.create_conversation(
            user_id=user_id,
            platform="telegram",
        )
        after = datetime.now(UTC)

        # Verify started_at was set
        call_args = mock_session.add.call_args[0][0]
        assert before <= call_args.started_at <= after

    # ========================================
    # AC-T4.2: append_message adds message to JSONB
    # ========================================
    @pytest.mark.asyncio
    async def test_append_message_adds_to_messages(
        self, mock_session: AsyncMock, sample_conversation: Conversation
    ):
        """AC-T4.2: append_message adds message to JSONB messages array."""
        mock_session.get.return_value = sample_conversation

        repo = ConversationRepository(mock_session)
        result = await repo.append_message(
            conversation_id=sample_conversation.id,
            role="user",
            content="Hello Nikita!",
            analysis={"sentiment": "positive"},
        )

        # Verify add_message was called on conversation
        sample_conversation.add_message.assert_called_once_with(
            "user", "Hello Nikita!", {"sentiment": "positive"}
        )
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_append_message_without_analysis(
        self, mock_session: AsyncMock, sample_conversation: Conversation
    ):
        """AC-T4.2: append_message works without analysis parameter."""
        mock_session.get.return_value = sample_conversation

        repo = ConversationRepository(mock_session)
        await repo.append_message(
            conversation_id=sample_conversation.id,
            role="nikita",
            content="Hey! How's it going?",
        )

        sample_conversation.add_message.assert_called_once_with(
            "nikita", "Hey! How's it going?", None
        )

    @pytest.mark.asyncio
    async def test_append_message_raises_if_not_found(self, mock_session: AsyncMock):
        """AC-T4.2: append_message raises ValueError if conversation not found."""
        mock_session.get.return_value = None

        repo = ConversationRepository(mock_session)

        with pytest.raises(ValueError, match="not found"):
            await repo.append_message(
                conversation_id=uuid4(),
                role="user",
                content="Hello",
            )

    # ========================================
    # AC-T4.3: get_recent returns last N conversations
    # ========================================
    @pytest.mark.asyncio
    async def test_get_recent_returns_conversations(
        self, mock_session: AsyncMock
    ):
        """AC-T4.3: get_recent returns list of recent conversations."""
        user_id = uuid4()
        conversations = [MagicMock(spec=Conversation) for _ in range(3)]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = conversations
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = ConversationRepository(mock_session)
        result = await repo.get_recent(user_id, limit=10)

        assert len(result) == 3
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_recent_respects_limit(self, mock_session: AsyncMock):
        """AC-T4.3: get_recent respects the limit parameter."""
        user_id = uuid4()

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = ConversationRepository(mock_session)
        await repo.get_recent(user_id, limit=5)

        # Verify limit was included in query
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_recent_default_limit(self, mock_session: AsyncMock):
        """AC-T4.3: get_recent uses default limit of 10."""
        user_id = uuid4()

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = ConversationRepository(mock_session)
        await repo.get_recent(user_id)  # No limit specified

        mock_session.execute.assert_called_once()

    # ========================================
    # AC-T4.4: search performs full-text search
    # ========================================
    @pytest.mark.asyncio
    async def test_search_finds_conversations(self, mock_session: AsyncMock):
        """AC-T4.4: search finds conversations matching query."""
        user_id = uuid4()
        conversations = [MagicMock(spec=Conversation)]

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = conversations
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = ConversationRepository(mock_session)
        result = await repo.search(user_id, "coffee")

        assert len(result) == 1
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_returns_empty_for_no_match(self, mock_session: AsyncMock):
        """AC-T4.4: search returns empty list for no matches."""
        user_id = uuid4()

        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result

        repo = ConversationRepository(mock_session)
        result = await repo.search(user_id, "nonexistent")

        assert result == []

    # ========================================
    # AC-T4.5: close_conversation sets ended_at and score_delta
    # ========================================
    @pytest.mark.asyncio
    async def test_close_conversation_sets_ended_at(
        self, mock_session: AsyncMock, sample_conversation: Conversation
    ):
        """AC-T4.5: close_conversation sets ended_at timestamp."""
        mock_session.get.return_value = sample_conversation

        repo = ConversationRepository(mock_session)

        before = datetime.now(UTC)
        result = await repo.close_conversation(sample_conversation.id)
        after = datetime.now(UTC)

        assert sample_conversation.ended_at is not None
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_conversation_with_score_delta(
        self, mock_session: AsyncMock, sample_conversation: Conversation
    ):
        """AC-T4.5: close_conversation sets score_delta when provided."""
        mock_session.get.return_value = sample_conversation

        repo = ConversationRepository(mock_session)
        await repo.close_conversation(
            sample_conversation.id,
            score_delta=Decimal("3.50"),
        )

        assert sample_conversation.score_delta == Decimal("3.50")

    @pytest.mark.asyncio
    async def test_close_conversation_raises_if_not_found(
        self, mock_session: AsyncMock
    ):
        """AC-T4.5: close_conversation raises ValueError if not found."""
        mock_session.get.return_value = None

        repo = ConversationRepository(mock_session)

        with pytest.raises(ValueError, match="not found"):
            await repo.close_conversation(uuid4())


class TestConversationRepositoryJSONB:
    """Test JSONB operations specific to ConversationRepository."""

    @pytest.fixture
    def mock_session(self) -> AsyncMock:
        """Create a mock AsyncSession."""
        session = AsyncMock(spec=AsyncSession)
        session.add = MagicMock()
        session.get = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_messages_start_as_empty_list(self, mock_session: AsyncMock):
        """Verify new conversations have empty messages array."""
        repo = ConversationRepository(mock_session)

        await repo.create_conversation(
            user_id=uuid4(),
            platform="telegram",
        )

        call_args = mock_session.add.call_args[0][0]
        assert call_args.messages == []

    @pytest.mark.asyncio
    async def test_multiple_messages_can_be_appended(self, mock_session: AsyncMock):
        """Verify multiple messages can be appended sequentially."""
        conv = MagicMock(spec=Conversation)
        conv.id = uuid4()
        conv.add_message = MagicMock()
        mock_session.get.return_value = conv

        repo = ConversationRepository(mock_session)

        await repo.append_message(conv.id, "user", "Hi!")
        await repo.append_message(conv.id, "nikita", "Hey there!")
        await repo.append_message(conv.id, "user", "How are you?")

        assert conv.add_message.call_count == 3
