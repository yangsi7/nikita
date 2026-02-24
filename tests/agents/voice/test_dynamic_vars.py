"""Tests for dynamic variables builder (US-13: Dynamic Variables and Overrides).

Tests for T067-T070 acceptance criteria:
- AC-FR018-001: Call initiates → user_name, chapter, mood available in prompts
- AC-FR018-002: Secret variables set → user_id hidden from LLM response generation
- AC-FR025-001: Config override passed → custom system prompt used
- AC-FR025-002: First_message override → Nikita uses custom greeting
"""

from datetime import datetime
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from nikita.agents.voice.models import DynamicVariables, NikitaMood, VoiceContext


class TestDynamicVariablesBuilder:
    """Test dynamic variables builder (FR-018)."""

    @pytest.fixture
    def mock_user(self):
        """Create a mock user for testing."""
        user = MagicMock()
        user.id = uuid4()
        user.name = "TestUser"
        user.chapter = 3
        user.game_status = "active"
        user.engagement_state = "IN_ZONE"
        user.metrics = MagicMock()
        user.metrics.relationship_score = 65.0
        return user

    @pytest.fixture
    def voice_context(self, mock_user):
        """Create a voice context for testing."""
        return VoiceContext(
            user_id=mock_user.id,
            user_name=mock_user.name,
            chapter=mock_user.chapter,
            relationship_score=65.0,
            engagement_state="IN_ZONE",
            game_status="active",
            nikita_mood=NikitaMood.PLAYFUL,
            nikita_energy="high",
            time_of_day="evening",
            recent_topics=["work", "weekend plans"],
            open_threads=["meeting next week"],
        )

    def test_build_from_context_includes_user_info(self, voice_context):
        """AC-FR018-001: Dynamic variables include user_name, chapter, mood."""
        from nikita.agents.voice.context import DynamicVariablesBuilder

        builder = DynamicVariablesBuilder()
        variables = builder.build_from_context(voice_context)

        assert variables.user_name == "TestUser"
        assert variables.chapter == 3
        assert variables.relationship_score == 65.0
        assert variables.nikita_mood == "playful"
        assert variables.nikita_energy == "high"
        assert variables.time_of_day == "evening"

    def test_build_from_context_includes_conversation_context(self, voice_context):
        """Variables include recent_topics and open_threads."""
        from nikita.agents.voice.context import DynamicVariablesBuilder

        builder = DynamicVariablesBuilder()
        variables = builder.build_from_context(voice_context)

        assert "work" in variables.recent_topics
        assert "weekend plans" in variables.recent_topics
        assert "meeting next week" in variables.open_threads

    def test_build_from_context_sets_secret_variables(self, voice_context):
        """AC-FR018-002: Secret variables set with user_id."""
        from nikita.agents.voice.context import DynamicVariablesBuilder

        builder = DynamicVariablesBuilder()
        session_token = "test_session_token_123"
        variables = builder.build_from_context(
            voice_context, session_token=session_token
        )

        # Secret variables should be set
        assert variables.secret__user_id == str(voice_context.user_id)
        assert variables.secret__signed_token == session_token

    def test_to_dict_excludes_secrets(self, voice_context):
        """to_dict() should exclude secret__ prefixed variables."""
        from nikita.agents.voice.context import DynamicVariablesBuilder

        builder = DynamicVariablesBuilder()
        variables = builder.build_from_context(
            voice_context, session_token="secret_token"
        )

        # Public dict should not contain secrets
        public_dict = variables.to_dict()

        assert "secret__user_id" not in public_dict
        assert "secret__signed_token" not in public_dict
        assert "user_name" in public_dict
        assert "chapter" in public_dict

    def test_to_dict_with_secrets_includes_all(self, voice_context):
        """to_dict_with_secrets() should include all variables."""
        from nikita.agents.voice.context import DynamicVariablesBuilder

        builder = DynamicVariablesBuilder()
        variables = builder.build_from_context(
            voice_context, session_token="secret_token"
        )

        # Full dict should contain everything
        full_dict = variables.to_dict_with_secrets()

        assert "secret__user_id" in full_dict
        assert "secret__signed_token" in full_dict
        assert "user_name" in full_dict

    def test_build_from_user_model(self, mock_user):
        """Build variables directly from user model."""
        from nikita.agents.voice.context import DynamicVariablesBuilder

        builder = DynamicVariablesBuilder()
        variables = builder.build_from_user(mock_user)

        assert variables.user_name == "TestUser"
        assert variables.chapter == 3
        assert variables.relationship_score == 65.0

    def test_empty_topics_formatted_correctly(self):
        """Empty topics should produce empty strings."""
        from nikita.agents.voice.context import DynamicVariablesBuilder

        context = VoiceContext(
            user_id=uuid4(),
            user_name="Test",
            chapter=1,
            relationship_score=50.0,
            recent_topics=[],
            open_threads=[],
        )

        builder = DynamicVariablesBuilder()
        variables = builder.build_from_context(context)

        assert variables.recent_topics == ""
        assert variables.open_threads == ""


class TestConversationConfigBuilder:
    """Test conversation config builder (FR-025)."""

    @pytest.fixture
    def mock_user(self):
        """Create a mock user for testing."""
        user = MagicMock()
        user.id = uuid4()
        user.name = "TestUser"
        user.chapter = 3
        user.game_status = "active"
        user.engagement_state = "IN_ZONE"
        user.metrics = MagicMock()
        user.metrics.relationship_score = 65.0
        user.vice_preferences = []
        return user

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.elevenlabs_api_key = "test_api_key"
        settings.elevenlabs_default_agent_id = "test_agent_id"
        return settings

    @pytest.mark.asyncio
    async def test_build_config_includes_system_prompt_override(
        self, mock_user, mock_settings
    ):
        """AC-FR025-001: Config includes custom system prompt."""
        from unittest.mock import AsyncMock, patch

        from nikita.agents.voice.context import ConversationConfigBuilder

        # Voice agent bypasses ContextEngine and loads ready prompts directly
        # Mock the ready prompt loading
        with patch("nikita.db.database.get_session_maker") as mock_session:
            mock_session_ctx = AsyncMock()
            mock_session.return_value = mock_session_ctx
            mock_session_ctx.__aenter__.return_value = MagicMock()

            builder = ConversationConfigBuilder(settings=mock_settings)
            config = await builder.build_config(user=mock_user)

            assert config.system_prompt is not None
            assert len(config.system_prompt) > 0
            assert "Nikita" in config.system_prompt

    @pytest.mark.asyncio
    async def test_build_config_includes_first_message_override(
        self, mock_user, mock_settings
    ):
        """AC-FR025-002: Config includes custom first message."""
        from unittest.mock import AsyncMock, patch

        from nikita.agents.voice.context import ConversationConfigBuilder

        with patch("nikita.db.database.get_session_maker") as mock_session:
            mock_session_ctx = AsyncMock()
            mock_session.return_value = mock_session_ctx
            mock_session_ctx.__aenter__.return_value = MagicMock()

            builder = ConversationConfigBuilder(settings=mock_settings)
            config = await builder.build_config(user=mock_user)

            assert config.first_message is not None
            assert len(config.first_message) > 0
            # First message should reference user name
            assert "TestUser" in config.first_message or "you" in config.first_message

    @pytest.mark.asyncio
    async def test_build_config_includes_tts_settings(self, mock_user, mock_settings):
        """Config includes TTS settings from chapter."""
        from unittest.mock import AsyncMock, patch

        from nikita.agents.voice.context import ConversationConfigBuilder

        with patch("nikita.db.database.get_session_maker") as mock_session:
            mock_session_ctx = AsyncMock()
            mock_session.return_value = mock_session_ctx
            mock_session_ctx.__aenter__.return_value = MagicMock()

            builder = ConversationConfigBuilder(settings=mock_settings)
            config = await builder.build_config(user=mock_user)

            assert config.tts is not None
            assert 0.0 <= config.tts.stability <= 1.0
            assert 0.0 <= config.tts.similarity_boost <= 1.0

    @pytest.mark.asyncio
    async def test_build_config_includes_dynamic_variables(self, mock_user, mock_settings):
        """Config includes dynamic variables."""
        from unittest.mock import AsyncMock, patch

        from nikita.agents.voice.context import ConversationConfigBuilder

        with patch("nikita.db.database.get_session_maker") as mock_session:
            mock_session_ctx = AsyncMock()
            mock_session.return_value = mock_session_ctx
            mock_session_ctx.__aenter__.return_value = MagicMock()

            builder = ConversationConfigBuilder(settings=mock_settings)
            config = await builder.build_config(user=mock_user)

            assert config.dynamic_variables is not None
            assert config.dynamic_variables.user_name == "TestUser"
            assert config.dynamic_variables.chapter == 3

    @pytest.mark.asyncio
    async def test_build_config_with_mood_override(self, mock_user, mock_settings):
        """Config respects mood override for TTS."""
        from unittest.mock import AsyncMock, patch

        from nikita.agents.voice.context import ConversationConfigBuilder

        with patch("nikita.db.database.get_session_maker") as mock_session:
            mock_session_ctx = AsyncMock()
            mock_session.return_value = mock_session_ctx
            mock_session_ctx.__aenter__.return_value = MagicMock()

            builder = ConversationConfigBuilder(settings=mock_settings)
            config = await builder.build_config(
                user=mock_user, mood=NikitaMood.ANNOYED
            )

            # Annoyed mood should affect TTS
            assert config.tts is not None
            # Annoyed: speed=1.1, stability=0.4
            assert config.tts.speed == 1.1 or config.tts.stability == 0.4

    @pytest.mark.asyncio
    async def test_to_elevenlabs_format(self, mock_user, mock_settings):
        """Convert config to ElevenLabs API format."""
        from unittest.mock import AsyncMock, patch

        from nikita.agents.voice.context import ConversationConfigBuilder

        with patch("nikita.db.database.get_session_maker") as mock_session:
            mock_session_ctx = AsyncMock()
            mock_session.return_value = mock_session_ctx
            mock_session_ctx.__aenter__.return_value = MagicMock()

            builder = ConversationConfigBuilder(settings=mock_settings)
            config = await builder.build_config(user=mock_user)
            elevenlabs_config = builder.to_elevenlabs_format(config)

            # Should have agent_id
            assert "agent_id" in elevenlabs_config
            # Should have conversation_config_override
            assert "conversation_config_override" in elevenlabs_config
            # Override should have agent section
            override = elevenlabs_config["conversation_config_override"]
            assert "agent" in override or "tts" in override

    @pytest.mark.asyncio
    async def test_to_elevenlabs_format_includes_voice_id(
        self, mock_user, mock_settings
    ):
        """Spec 108: TTS section includes voice_id when setting is configured."""
        from unittest.mock import AsyncMock, patch

        from nikita.agents.voice.context import ConversationConfigBuilder

        mock_settings.elevenlabs_voice_id = "xDh1Ib47SaVb2H8RXsJf"

        with patch("nikita.db.database.get_session_maker") as mock_session:
            mock_session_ctx = AsyncMock()
            mock_session.return_value = mock_session_ctx
            mock_session_ctx.__aenter__.return_value = MagicMock()

            builder = ConversationConfigBuilder(settings=mock_settings)
            config = await builder.build_config(user=mock_user)
            elevenlabs_config = builder.to_elevenlabs_format(config)

            override = elevenlabs_config["conversation_config_override"]
            assert "tts" in override
            assert override["tts"]["voice_id"] == "xDh1Ib47SaVb2H8RXsJf"

    @pytest.mark.asyncio
    async def test_to_elevenlabs_format_omits_voice_id_when_not_set(
        self, mock_user, mock_settings
    ):
        """Spec 108: TTS section omits voice_id when setting is None."""
        from unittest.mock import AsyncMock, patch

        from nikita.agents.voice.context import ConversationConfigBuilder

        mock_settings.elevenlabs_voice_id = None

        with patch("nikita.db.database.get_session_maker") as mock_session:
            mock_session_ctx = AsyncMock()
            mock_session.return_value = mock_session_ctx
            mock_session_ctx.__aenter__.return_value = MagicMock()

            builder = ConversationConfigBuilder(settings=mock_settings)
            config = await builder.build_config(user=mock_user)
            elevenlabs_config = builder.to_elevenlabs_format(config)

            override = elevenlabs_config["conversation_config_override"]
            assert "tts" in override
            assert "voice_id" not in override["tts"]

    @pytest.mark.asyncio
    async def test_to_elevenlabs_format_includes_expressive_mode(
        self, mock_user, mock_settings
    ):
        """Spec 108: TTS section always includes expressive_mode: True."""
        from unittest.mock import AsyncMock, patch

        from nikita.agents.voice.context import ConversationConfigBuilder

        with patch("nikita.db.database.get_session_maker") as mock_session:
            mock_session_ctx = AsyncMock()
            mock_session.return_value = mock_session_ctx
            mock_session_ctx.__aenter__.return_value = MagicMock()

            builder = ConversationConfigBuilder(settings=mock_settings)
            config = await builder.build_config(user=mock_user)
            elevenlabs_config = builder.to_elevenlabs_format(config)

            override = elevenlabs_config["conversation_config_override"]
            assert override["tts"]["expressive_mode"] is True


class TestTimeOfDayCalculation:
    """Test time of day calculation for dynamic variables."""

    def test_morning_hours(self):
        """5am-11am should be morning."""
        from nikita.agents.voice.context import DynamicVariablesBuilder

        builder = DynamicVariablesBuilder()

        for hour in [5, 6, 7, 8, 9, 10, 11]:
            result = builder._get_time_of_day(hour)
            assert result == "morning"

    def test_afternoon_hours(self):
        """12pm-4pm should be afternoon (Spec 029: matches meta_prompts/service.py)."""
        from nikita.agents.voice.context import DynamicVariablesBuilder

        builder = DynamicVariablesBuilder()

        for hour in [12, 13, 14, 15, 16]:
            result = builder._get_time_of_day(hour)
            assert result == "afternoon"

    def test_evening_hours(self):
        """5pm-8pm should be evening (Spec 029: matches meta_prompts/service.py)."""
        from nikita.agents.voice.context import DynamicVariablesBuilder

        builder = DynamicVariablesBuilder()

        for hour in [17, 18, 19, 20]:
            result = builder._get_time_of_day(hour)
            assert result == "evening"

    def test_night_hours(self):
        """9pm-11pm should be night (Spec 029: matches meta_prompts/service.py)."""
        from nikita.agents.voice.context import DynamicVariablesBuilder

        builder = DynamicVariablesBuilder()

        for hour in [21, 22, 23]:
            result = builder._get_time_of_day(hour)
            assert result == "night"

    def test_late_night_hours(self):
        """12am-4am should be late_night (Spec 029: matches meta_prompts/service.py)."""
        from nikita.agents.voice.context import DynamicVariablesBuilder

        builder = DynamicVariablesBuilder()

        for hour in [0, 1, 2, 3, 4]:
            result = builder._get_time_of_day(hour)
            assert result == "late_night"
