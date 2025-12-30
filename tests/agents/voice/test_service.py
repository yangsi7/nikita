"""Tests for VoiceService (US-1: Start Voice Call).

Tests for T005, T006 acceptance criteria:
- AC-FR001-001: Call initiation returns connection params
- AC-FR008-001: Session creation logs start time
- AC-T006.1: initiate_call returns signed connection params
- AC-T006.2: Generates signed token
- AC-T006.3: Logs call_started event
- AC-T006.4: Loads user context
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.agents.voice.models import CallResult, VoiceContext


class TestVoiceServiceInitiateCall:
    """Test VoiceService.initiate_call() - T005, T006."""

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
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.elevenlabs_api_key = "test_api_key"
        settings.elevenlabs_default_agent_id = "test_agent_id"
        settings.elevenlabs_webhook_secret = "test_webhook_secret"
        settings.neo4j_uri = "neo4j+s://test.db"
        return settings

    @pytest.mark.asyncio
    async def test_initiate_call_returns_connection_params(
        self, mock_user, mock_settings
    ):
        """AC-T006.1: initiate_call returns signed ElevenLabs connection params."""
        from nikita.agents.voice.service import VoiceService

        service = VoiceService(settings=mock_settings)

        with patch.object(
            service, "_load_user", new_callable=AsyncMock, return_value=mock_user
        ):
            with patch.object(
                service, "_generate_signed_token", return_value="signed_token_123"
            ):
                with patch.object(
                    service, "_load_context", new_callable=AsyncMock
                ) as mock_context:
                    mock_context.return_value = VoiceContext(
                        user_id=mock_user.id,
                        user_name="TestUser",
                        chapter=3,
                        relationship_score=65.0,
                    )

                    result = await service.initiate_call(mock_user.id)

        assert result is not None
        assert "agent_id" in result
        assert "signed_token" in result
        assert result["signed_token"] == "signed_token_123"

    @pytest.mark.asyncio
    async def test_initiate_call_generates_signed_token(
        self, mock_user, mock_settings
    ):
        """AC-T006.2: Generates signed token with user_id for server tool auth."""
        from nikita.agents.voice.service import VoiceService

        service = VoiceService(settings=mock_settings)

        with patch.object(
            service, "_load_user", new_callable=AsyncMock, return_value=mock_user
        ):
            with patch.object(
                service, "_load_context", new_callable=AsyncMock
            ) as mock_context:
                mock_context.return_value = VoiceContext(
                    user_id=mock_user.id,
                    user_name="TestUser",
                    chapter=3,
                    relationship_score=65.0,
                )

                result = await service.initiate_call(mock_user.id)

        # Token should be generated
        assert "signed_token" in result
        assert result["signed_token"] is not None

    @pytest.mark.asyncio
    async def test_initiate_call_logs_call_started(self, mock_user, mock_settings):
        """AC-T006.3: Logs call_started event with timestamp."""
        from nikita.agents.voice.service import VoiceService

        service = VoiceService(settings=mock_settings)

        with patch.object(
            service, "_load_user", new_callable=AsyncMock, return_value=mock_user
        ):
            with patch.object(
                service, "_generate_signed_token", return_value="token"
            ):
                with patch.object(
                    service, "_load_context", new_callable=AsyncMock
                ) as mock_context:
                    mock_context.return_value = VoiceContext(
                        user_id=mock_user.id,
                        user_name="TestUser",
                        chapter=3,
                        relationship_score=65.0,
                    )
                    with patch.object(
                        service, "_log_call_started", new_callable=AsyncMock
                    ) as mock_log:
                        await service.initiate_call(mock_user.id)

                        # Should have logged the call start
                        mock_log.assert_called_once()

    @pytest.mark.asyncio
    async def test_initiate_call_loads_user_context(self, mock_user, mock_settings):
        """AC-T006.4: Loads user context for initial greeting customization."""
        from nikita.agents.voice.service import VoiceService

        service = VoiceService(settings=mock_settings)

        with patch.object(
            service, "_load_user", new_callable=AsyncMock, return_value=mock_user
        ):
            with patch.object(
                service, "_generate_signed_token", return_value="token"
            ):
                with patch.object(
                    service, "_load_context", new_callable=AsyncMock
                ) as mock_context:
                    expected_context = VoiceContext(
                        user_id=mock_user.id,
                        user_name="TestUser",
                        chapter=3,
                        relationship_score=65.0,
                    )
                    mock_context.return_value = expected_context

                    result = await service.initiate_call(mock_user.id)

                    # Context should be loaded
                    mock_context.assert_called_once()
                    assert "context" in result

    @pytest.mark.asyncio
    async def test_initiate_call_fails_for_game_over(self, mock_user, mock_settings):
        """Call should fail if user is in game_over state."""
        from nikita.agents.voice.service import VoiceService

        mock_user.game_status = "game_over"
        service = VoiceService(settings=mock_settings)

        with patch.object(
            service, "_load_user", new_callable=AsyncMock, return_value=mock_user
        ):
            with pytest.raises(ValueError, match="not available"):
                await service.initiate_call(mock_user.id)

    @pytest.mark.asyncio
    async def test_initiate_call_returns_session_id(self, mock_user, mock_settings):
        """AC-FR008-001: Session ID should be returned for tracking."""
        from nikita.agents.voice.service import VoiceService

        service = VoiceService(settings=mock_settings)

        with patch.object(
            service, "_load_user", new_callable=AsyncMock, return_value=mock_user
        ):
            with patch.object(
                service, "_generate_signed_token", return_value="token"
            ):
                with patch.object(
                    service, "_load_context", new_callable=AsyncMock
                ) as mock_context:
                    mock_context.return_value = VoiceContext(
                        user_id=mock_user.id,
                        user_name="TestUser",
                        chapter=3,
                        relationship_score=65.0,
                    )

                    result = await service.initiate_call(mock_user.id)

        assert "session_id" in result
        assert result["session_id"] is not None
