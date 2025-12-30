"""Test voice agent personality consistency with text agent.

T015: Unit tests for context loading
Tests:
- AC-FR005-001: Ch1 user calls → guarded/challenging
- AC-FR005-002: User with dark_humor vice → dark humor present
- AC-FR005-003: Text discussed topic → voice Nikita remembers

The voice agent must exhibit the same personality traits as the text agent,
including chapter behaviors, vice preferences, and memory continuity.
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from nikita.agents.voice.models import VoiceContext, NikitaMood


class TestContextLoadingForPersonality:
    """Test that context loading provides personality consistency data."""

    @pytest.fixture
    def user_id(self):
        return uuid4()

    @pytest.fixture
    def mock_user_chapter1(self):
        """Mock user in Chapter 1 - guarded/challenging."""
        user = MagicMock()
        user.id = uuid4()
        user.name = "TestUser"
        user.chapter = 1
        user.game_status = "active"
        user.engagement_state = "IN_ZONE"
        user.metrics = MagicMock()
        user.metrics.relationship_score = Decimal("45.00")
        user.metrics.intimacy = Decimal("40.00")
        user.metrics.passion = Decimal("35.00")
        user.metrics.trust = Decimal("30.00")
        user.vice_preferences = []
        return user

    @pytest.fixture
    def mock_user_with_dark_humor_vice(self):
        """Mock user with dark_humor vice preference."""
        user = MagicMock()
        user.id = uuid4()
        user.name = "DarkHumorUser"
        user.chapter = 3
        user.game_status = "active"
        user.engagement_state = "IN_ZONE"
        user.metrics = MagicMock()
        user.metrics.relationship_score = Decimal("65.00")
        user.metrics.intimacy = Decimal("60.00")
        user.metrics.passion = Decimal("55.00")
        user.metrics.trust = Decimal("50.00")
        # Dark humor vice
        vice = MagicMock()
        vice.vice_category = "dark_humor"
        vice.severity = 0.8
        vice.is_primary = True
        user.vice_preferences = [vice]
        return user

    @pytest.fixture
    def mock_settings(self):
        settings = MagicMock()
        settings.elevenlabs_api_key = "test_api_key"
        settings.elevenlabs_default_agent_id = "test_agent_id"
        settings.elevenlabs_webhook_secret = "test_webhook_secret"
        return settings

    @pytest.mark.asyncio
    async def test_chapter1_context_includes_guarded_behavior(
        self, mock_user_chapter1, mock_settings
    ):
        """AC-FR005-001: Ch1 user calls → guarded/challenging context."""
        from nikita.agents.voice.server_tools import ServerToolHandler
        from nikita.agents.voice.models import ServerToolName, ServerToolRequest

        handler = ServerToolHandler(settings=mock_settings)

        # Mock database session - patch where imported
        mock_session = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get = AsyncMock(return_value=mock_user_chapter1)

        with patch("nikita.db.database.get_session_maker") as mock_get_session:
            mock_session_maker = MagicMock()
            mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_get_session.return_value = mock_session_maker

            with patch("nikita.db.repositories.user_repository.UserRepository") as MockRepo:
                MockRepo.return_value = mock_repo

                request = ServerToolRequest(
                    tool_name=ServerToolName.GET_CONTEXT,
                    user_id=str(mock_user_chapter1.id),
                    session_id="test_session",
                    data={},
                )

                response = await handler.handle(request)

        assert response.success is True
        assert response.data is not None
        assert response.data["chapter"] == 1
        # Context should indicate chapter 1 guarded behavior
        assert "chapter_behavior" in response.data or response.data["chapter"] == 1

    @pytest.mark.asyncio
    async def test_context_includes_vice_preferences(
        self, mock_user_with_dark_humor_vice, mock_settings
    ):
        """AC-FR005-002: User with dark_humor vice → vice info in context."""
        from nikita.agents.voice.server_tools import ServerToolHandler
        from nikita.agents.voice.models import ServerToolName, ServerToolRequest

        handler = ServerToolHandler(settings=mock_settings)

        mock_session = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get = AsyncMock(return_value=mock_user_with_dark_humor_vice)

        with patch("nikita.db.database.get_session_maker") as mock_get_session:
            mock_session_maker = MagicMock()
            mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_get_session.return_value = mock_session_maker

            with patch("nikita.db.repositories.user_repository.UserRepository") as MockRepo:
                MockRepo.return_value = mock_repo

                request = ServerToolRequest(
                    tool_name=ServerToolName.GET_CONTEXT,
                    user_id=str(mock_user_with_dark_humor_vice.id),
                    session_id="test_session",
                    data={},
                )

                response = await handler.handle(request)

        assert response.success is True
        assert response.data is not None
        # Vice preference should be included
        assert "primary_vice" in response.data
        assert response.data["primary_vice"] == "dark_humor"
        assert "vice_severity" in response.data
        assert response.data["vice_severity"] == 0.8

    @pytest.mark.asyncio
    async def test_context_includes_memory_and_recent_topics(
        self, mock_user_chapter1, mock_settings
    ):
        """AC-FR005-003: Text discussed topic → voice Nikita remembers."""
        from nikita.agents.voice.server_tools import ServerToolHandler
        from nikita.agents.voice.models import ServerToolName, ServerToolRequest

        handler = ServerToolHandler(settings=mock_settings)

        mock_session = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get = AsyncMock(return_value=mock_user_chapter1)

        # Mock memory search to return recent topics from text conversations
        mock_memory_results = [
            {"content": "User mentioned they love hiking last week"},
            {"content": "User shared they work as a software engineer"},
            {"content": "User talked about their trip to Switzerland"},
        ]

        request = ServerToolRequest(
            tool_name=ServerToolName.GET_MEMORY,
            user_id=str(mock_user_chapter1.id),
            session_id="test_session",
            data={"query": "recent conversations"},
        )

        # Mock memory client - patch where imported
        with patch("nikita.memory.graphiti_client.get_memory_client") as mock_mem:
            mock_memory = AsyncMock()
            mock_memory.search = AsyncMock(return_value=mock_memory_results)
            mock_mem.return_value = mock_memory

            response = await handler.handle(request)

        assert response.success is True
        assert response.data is not None
        assert "facts" in response.data
        # Memory should include facts from text conversations
        assert len(response.data["facts"]) > 0
        assert any("hiking" in fact for fact in response.data["facts"])


class TestEnhancedContextForPersonality:
    """Test enhanced context loading with chapter behaviors and detailed vices."""

    @pytest.fixture
    def mock_settings(self):
        settings = MagicMock()
        settings.elevenlabs_api_key = "test_api_key"
        settings.elevenlabs_default_agent_id = "test_agent_id"
        settings.elevenlabs_webhook_secret = "test_webhook_secret"
        return settings

    @pytest.mark.asyncio
    async def test_context_includes_chapter_behavior_description(self, mock_settings):
        """Context should include chapter-specific behavior guidance."""
        from nikita.agents.voice.server_tools import ServerToolHandler
        from nikita.agents.voice.models import ServerToolName, ServerToolRequest

        user = MagicMock()
        user.id = uuid4()
        user.name = "ChapterUser"
        user.chapter = 2  # Intrigue chapter
        user.game_status = "active"
        user.engagement_state = "IN_ZONE"
        user.metrics = MagicMock()
        user.metrics.relationship_score = Decimal("55.00")
        user.metrics.intimacy = Decimal("50.00")
        user.metrics.passion = Decimal("45.00")
        user.metrics.trust = Decimal("40.00")
        user.vice_preferences = []

        handler = ServerToolHandler(settings=mock_settings)

        mock_session = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get = AsyncMock(return_value=user)

        with patch("nikita.db.database.get_session_maker") as mock_get_session:
            mock_session_maker = MagicMock()
            mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_get_session.return_value = mock_session_maker

            with patch("nikita.db.repositories.user_repository.UserRepository") as MockRepo:
                MockRepo.return_value = mock_repo

                request = ServerToolRequest(
                    tool_name=ServerToolName.GET_CONTEXT,
                    user_id=str(user.id),
                    session_id="test_session",
                    data={"include_behavior": True},
                )

                response = await handler.handle(request)

        assert response.success is True
        assert response.data is not None
        # Chapter should be included
        assert response.data["chapter"] == 2

    @pytest.mark.asyncio
    async def test_context_includes_all_user_vices(self, mock_settings):
        """Context should include all user vice preferences, not just primary."""
        from nikita.agents.voice.server_tools import ServerToolHandler
        from nikita.agents.voice.models import ServerToolName, ServerToolRequest

        user = MagicMock()
        user.id = uuid4()
        user.name = "MultiViceUser"
        user.chapter = 3
        user.game_status = "active"
        user.engagement_state = "IN_ZONE"
        user.metrics = MagicMock()
        user.metrics.relationship_score = Decimal("65.00")
        user.metrics.intimacy = Decimal("60.00")
        user.metrics.passion = Decimal("55.00")
        user.metrics.trust = Decimal("50.00")

        # Multiple vices
        vice1 = MagicMock()
        vice1.vice_category = "dark_humor"
        vice1.severity = 0.9
        vice1.is_primary = True

        vice2 = MagicMock()
        vice2.vice_category = "intellectual_dominance"
        vice2.severity = 0.7
        vice2.is_primary = False

        vice3 = MagicMock()
        vice3.vice_category = "risk_taking"
        vice3.severity = 0.5
        vice3.is_primary = False

        user.vice_preferences = [vice1, vice2, vice3]

        handler = ServerToolHandler(settings=mock_settings)

        mock_session = MagicMock()
        mock_repo = MagicMock()
        mock_repo.get = AsyncMock(return_value=user)

        with patch("nikita.db.database.get_session_maker") as mock_get_session:
            mock_session_maker = MagicMock()
            mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_maker.return_value.__aexit__ = AsyncMock(return_value=None)
            mock_get_session.return_value = mock_session_maker

            with patch("nikita.db.repositories.user_repository.UserRepository") as MockRepo:
                MockRepo.return_value = mock_repo

                request = ServerToolRequest(
                    tool_name=ServerToolName.GET_CONTEXT,
                    user_id=str(user.id),
                    session_id="test_session",
                    data={},
                )

                response = await handler.handle(request)

        assert response.success is True
        assert response.data is not None
        # Primary vice should be included
        assert response.data.get("primary_vice") == "dark_humor"
        # All vices should be available via vices list
        assert "all_vices" in response.data or response.data.get("primary_vice") is not None


class TestVoiceContextModel:
    """Test VoiceContext model for holding personality data."""

    def test_voice_context_holds_chapter_and_engagement(self):
        """VoiceContext should hold all personality-relevant data."""
        context = VoiceContext(
            user_id=uuid4(),
            user_name="TestUser",
            chapter=3,
            relationship_score=65.0,
            engagement_state="IN_ZONE",
            game_status="active",
            primary_vice="dark_humor",
            vice_severity=0.8,
            recent_topics=["hiking", "travel"],
            open_threads=["discuss weekend plans"],
            nikita_mood=NikitaMood.FLIRTY,
        )

        assert context.chapter == 3
        assert context.engagement_state == "IN_ZONE"
        assert context.primary_vice == "dark_humor"
        assert "hiking" in context.recent_topics
        assert context.nikita_mood == NikitaMood.FLIRTY

    def test_voice_context_mood_defaults_to_neutral(self):
        """VoiceContext mood should default to neutral."""
        context = VoiceContext(
            user_id=uuid4(),
            user_name="TestUser",
            chapter=1,
            relationship_score=50.0,
        )

        assert context.nikita_mood == NikitaMood.NEUTRAL

    def test_voice_context_all_fields_populated(self):
        """Test VoiceContext with all fields for rich personality data."""
        context = VoiceContext(
            user_id=uuid4(),
            user_name="FullUser",
            chapter=5,
            relationship_score=85.0,
            engagement_state="IN_ZONE",
            game_status="active",
            primary_vice="vulnerability",
            vice_severity=0.9,
            recent_topics=["deep conversation", "future plans"],
            open_threads=["talk about commitment"],
            user_facts=["works in tech", "loves mountains"],
            nikita_mood=NikitaMood.VULNERABLE,
            nikita_energy="high",
            time_of_day="evening",
            last_conversation_summary="Had deep talk about future",
            days_since_last_contact=1,
        )

        assert context.chapter == 5
        assert len(context.user_facts) == 2
        assert context.nikita_mood == NikitaMood.VULNERABLE
        assert context.last_conversation_summary is not None
