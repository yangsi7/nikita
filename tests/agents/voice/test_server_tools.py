"""Tests for Server Tool Handler (US-2: Natural Conversation).

Tests for T012, T013 acceptance criteria:
- AC-T012.1: handle(request) routes to appropriate tool handler
- AC-T012.2: Validates signed token for user_id
- AC-T012.3: Returns structured response for ElevenLabs
- AC-T013.1: POST /api/v1/voice/server-tool handles tool calls
- AC-T013.2: Validates ElevenLabs webhook signature
- AC-T013.3: Returns JSON response for tool result
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.agents.voice.models import ServerToolName, ServerToolRequest


class TestServerToolHandler:
    """Test ServerToolHandler - T012."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.elevenlabs_api_key = "test_api_key"
        settings.elevenlabs_default_agent_id = "test_agent_id"
        settings.elevenlabs_webhook_secret = "test_secret_key"
        return settings

    @pytest.fixture
    def test_user_id(self):
        """Create test user ID."""
        return str(uuid4())

    @pytest.fixture
    def test_session_id(self):
        """Create test session ID."""
        return "voice_test_session"

    @pytest.mark.asyncio
    async def test_handle_routes_to_get_context(
        self, mock_settings, test_user_id, test_session_id
    ):
        """AC-T012.1: handle(request) routes to appropriate tool handler."""
        from nikita.agents.voice.server_tools import ServerToolHandler

        handler = ServerToolHandler(settings=mock_settings)

        request = ServerToolRequest(
            tool_name=ServerToolName.GET_CONTEXT,
            user_id=test_user_id,
            session_id=test_session_id,
            data={},
        )

        with patch.object(
            handler, "_get_context", new_callable=AsyncMock
        ) as mock_get_context:
            mock_get_context.return_value = {"chapter": 3, "vices": []}
            response = await handler.handle(request)

        mock_get_context.assert_called_once()
        assert response.success is True

    @pytest.mark.asyncio
    async def test_handle_routes_to_get_memory(
        self, mock_settings, test_user_id, test_session_id
    ):
        """AC-T012.1: Routes to get_memory handler."""
        from nikita.agents.voice.server_tools import ServerToolHandler

        handler = ServerToolHandler(settings=mock_settings)

        request = ServerToolRequest(
            tool_name=ServerToolName.GET_MEMORY,
            user_id=test_user_id,
            session_id=test_session_id,
            data={"query": "recent topics"},
        )

        with patch.object(
            handler, "_get_memory", new_callable=AsyncMock
        ) as mock_get_memory:
            mock_get_memory.return_value = {"facts": [], "threads": []}
            response = await handler.handle(request)

        mock_get_memory.assert_called_once()
        assert response.success is True

    @pytest.mark.asyncio
    async def test_handle_returns_structured_response(
        self, mock_settings, test_user_id, test_session_id
    ):
        """AC-T012.3: Returns structured response for ElevenLabs."""
        from nikita.agents.voice.server_tools import ServerToolHandler

        handler = ServerToolHandler(settings=mock_settings)

        request = ServerToolRequest(
            tool_name=ServerToolName.GET_CONTEXT,
            user_id=test_user_id,
            session_id=test_session_id,
            data={},
        )

        with patch.object(
            handler, "_get_context", new_callable=AsyncMock
        ) as mock_get_context:
            mock_get_context.return_value = {"chapter": 3}
            response = await handler.handle(request)

        # Response should have required fields
        assert hasattr(response, "success")
        assert hasattr(response, "data")
        assert hasattr(response, "tool_name")
        assert response.tool_name == ServerToolName.GET_CONTEXT

    @pytest.mark.asyncio
    async def test_handle_score_turn_tool(
        self, mock_settings, test_user_id, test_session_id
    ):
        """AC-T012.1: Routes to score_turn handler."""
        from nikita.agents.voice.server_tools import ServerToolHandler

        handler = ServerToolHandler(settings=mock_settings)

        request = ServerToolRequest(
            tool_name=ServerToolName.SCORE_TURN,
            user_id=test_user_id,
            session_id=test_session_id,
            data={
                "user_message": "I love talking to you",
                "nikita_response": "Aww, you're sweet",
            },
        )

        with patch.object(
            handler, "_score_turn", new_callable=AsyncMock
        ) as mock_score:
            mock_score.return_value = {"intimacy_delta": 2.0, "trust_delta": 1.0}
            response = await handler.handle(request)

        mock_score.assert_called_once()
        assert response.success is True

    @pytest.mark.asyncio
    async def test_handle_update_memory_tool(
        self, mock_settings, test_user_id, test_session_id
    ):
        """AC-T012.1: Routes to update_memory handler."""
        from nikita.agents.voice.server_tools import ServerToolHandler

        handler = ServerToolHandler(settings=mock_settings)

        request = ServerToolRequest(
            tool_name=ServerToolName.UPDATE_MEMORY,
            user_id=test_user_id,
            session_id=test_session_id,
            data={
                "fact": "User mentioned they work in finance",
                "category": "career",
            },
        )

        with patch.object(
            handler, "_update_memory", new_callable=AsyncMock
        ) as mock_update:
            mock_update.return_value = {"stored": True}
            response = await handler.handle(request)

        mock_update.assert_called_once()
        assert response.success is True

    @pytest.mark.asyncio
    async def test_handle_unknown_tool_returns_error(
        self, mock_settings, test_user_id, test_session_id
    ):
        """Unknown tool should return error response."""
        from nikita.agents.voice.server_tools import ServerToolHandler

        handler = ServerToolHandler(settings=mock_settings)

        # Manually create request with invalid tool (bypass enum validation)
        request = MagicMock()
        request.tool_name = "unknown_tool"
        request.user_id = test_user_id
        request.session_id = test_session_id
        request.data = {}

        response = await handler.handle(request)

        assert response.success is False
        assert "unknown" in response.error.lower()


class TestSignedTokenValidation:
    """Test signed token validation for API endpoint."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.elevenlabs_webhook_secret = "test_secret_key"
        return settings

    def test_validate_token_success(self, mock_settings):
        """Valid token should be validated successfully."""
        from nikita.agents.voice.server_tools import ServerToolHandler
        import hashlib
        import hmac
        import time

        handler = ServerToolHandler(settings=mock_settings)

        user_id = str(uuid4())
        session_id = "voice_session_123"
        timestamp = int(time.time())
        payload = f"{user_id}:{session_id}:{timestamp}"
        secret = mock_settings.elevenlabs_webhook_secret
        signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        token = f"{payload}:{signature}"

        extracted_user_id, extracted_session_id = handler._validate_token(token)

        assert extracted_user_id == user_id
        assert extracted_session_id == session_id

    def test_validate_token_invalid_format(self, mock_settings):
        """Invalid token format should raise ValueError."""
        from nikita.agents.voice.server_tools import ServerToolHandler

        handler = ServerToolHandler(settings=mock_settings)

        with pytest.raises(ValueError, match="Invalid token format"):
            handler._validate_token("invalid:format")

    def test_validate_token_expired(self, mock_settings):
        """Expired token should raise ValueError."""
        from nikita.agents.voice.server_tools import ServerToolHandler
        import hashlib
        import hmac

        handler = ServerToolHandler(settings=mock_settings)

        user_id = str(uuid4())
        session_id = "voice_session_123"
        old_timestamp = 1000000  # Way in the past
        payload = f"{user_id}:{session_id}:{old_timestamp}"
        secret = mock_settings.elevenlabs_webhook_secret
        signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        token = f"{payload}:{signature}"

        with pytest.raises(ValueError, match="[Ee]xpired"):
            handler._validate_token(token)

    def test_validate_token_invalid_signature(self, mock_settings):
        """Invalid signature should raise ValueError."""
        from nikita.agents.voice.server_tools import ServerToolHandler
        import time

        handler = ServerToolHandler(settings=mock_settings)

        user_id = str(uuid4())
        session_id = "voice_session_123"
        timestamp = int(time.time())
        payload = f"{user_id}:{session_id}:{timestamp}"
        bad_signature = "invalid_signature_hash"
        token = f"{payload}:{bad_signature}"

        with pytest.raises(ValueError, match="[Ii]nvalid signature"):
            handler._validate_token(token)


class TestTimeoutFallback:
    """Test timeout fallback decorator (T072, US-14)."""

    @pytest.mark.asyncio
    async def test_timeout_decorator_returns_fallback_on_timeout(self):
        """AC-T072.1: Decorator with configurable timeout returns fallback."""
        import asyncio
        from nikita.agents.voice.server_tools import with_timeout_fallback

        @with_timeout_fallback(timeout_seconds=0.1, fallback_data={"default": "value"})
        async def slow_function():
            await asyncio.sleep(1.0)  # Will timeout
            return {"should": "never_return"}

        result = await slow_function()

        assert result.get("timeout") is True
        assert result.get("default") == "value"

    @pytest.mark.asyncio
    async def test_timeout_decorator_returns_normal_on_success(self):
        """Decorator returns normal response when function completes in time."""
        from nikita.agents.voice.server_tools import with_timeout_fallback

        @with_timeout_fallback(timeout_seconds=1.0, fallback_data={"default": "value"})
        async def fast_function():
            return {"success": True, "data": "actual"}

        result = await fast_function()

        assert result.get("success") is True
        assert result.get("data") == "actual"
        assert result.get("timeout") is None

    @pytest.mark.asyncio
    async def test_timeout_fallback_includes_cache_friendly(self):
        """AC-T072.4: Fallback includes cache_friendly=True."""
        import asyncio
        from nikita.agents.voice.server_tools import with_timeout_fallback

        @with_timeout_fallback(timeout_seconds=0.05)
        async def timeout_function():
            await asyncio.sleep(1.0)
            return {}

        result = await timeout_function()

        assert result.get("cache_friendly") is True

    @pytest.mark.asyncio
    async def test_timeout_fallback_includes_error_message(self):
        """AC-T072.2: Returns fallback response with error message."""
        import asyncio
        from nikita.agents.voice.server_tools import with_timeout_fallback

        @with_timeout_fallback(timeout_seconds=0.05)
        async def timeout_function():
            await asyncio.sleep(1.0)
            return {}

        result = await timeout_function()

        assert "error" in result
        assert "timed out" in result["error"].lower()

    def test_timeout_decorator_configurable_seconds(self):
        """Timeout should be configurable."""
        from nikita.agents.voice.server_tools import with_timeout_fallback

        # Test that different timeout values work
        @with_timeout_fallback(timeout_seconds=5.0)
        async def five_second_timeout():
            pass

        @with_timeout_fallback(timeout_seconds=0.5)
        async def half_second_timeout():
            pass

        # Just verify decorators apply without error
        assert callable(five_second_timeout)
        assert callable(half_second_timeout)


class TestServerToolResilience:
    """Test server tool resilience for Neo4j cold starts (US-14)."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.elevenlabs_webhook_secret = "test_secret"
        return settings

    @pytest.mark.asyncio
    async def test_get_memory_graceful_degradation(self, mock_settings):
        """AC-FR022-001: Graceful degradation when Neo4j unavailable."""
        from nikita.agents.voice.server_tools import ServerToolHandler

        handler = ServerToolHandler(settings=mock_settings)

        # Mock memory client that fails
        with patch(
            "nikita.agents.voice.server_tools.get_memory_client",
            side_effect=Exception("Neo4j connection failed"),
        ):
            result = await handler._get_memory(
                user_id=str(uuid4()),
                session_id="test_session",
                data={"query": "recent"},
            )

        # Should return empty results, not raise exception
        assert result.get("facts") == []
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update_memory_graceful_degradation(self, mock_settings):
        """Memory updates fail gracefully when Neo4j unavailable."""
        from nikita.agents.voice.server_tools import ServerToolHandler

        handler = ServerToolHandler(settings=mock_settings)

        with patch(
            "nikita.agents.voice.server_tools.get_memory_client",
            side_effect=Exception("Neo4j connection failed"),
        ):
            result = await handler._update_memory(
                user_id=str(uuid4()),
                session_id="test_session",
                data={"fact": "Test fact"},
            )

        # Should return error but not crash
        assert result.get("stored") is False
        assert "error" in result
