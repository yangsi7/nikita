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


class TestGetContextEnhancements:
    """Test enhanced get_context with thoughts, summaries, and backstory (Phase 1)."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.elevenlabs_webhook_secret = "test_secret"
        return settings

    @pytest.fixture
    def test_user_id(self):
        """Create test user ID."""
        return str(uuid4())

    @pytest.mark.asyncio
    async def test_get_context_includes_active_thoughts(
        self, mock_settings, test_user_id
    ):
        """Phase 1: get_context returns active_thoughts by type."""
        from nikita.agents.voice.server_tools import ServerToolHandler

        handler = ServerToolHandler(settings=mock_settings)

        # Create mock user with metrics and engagement
        mock_user = MagicMock()
        mock_user.name = "Test User"
        mock_user.chapter = 3
        mock_user.game_status = "active"
        mock_user.metrics = MagicMock(
            relationship_score=65.0,
            intimacy=60.0,
            passion=55.0,
            trust=70.0,
        )
        mock_user.engagement_state = MagicMock(state="in_zone")
        mock_user.vice_preferences = []

        # Mock thought with content attribute
        mock_thought = MagicMock()
        mock_thought.content = "I wonder what he's up to today"

        # Mock thoughts dict from repository
        mock_thoughts = {"wondering": [mock_thought]}

        # Mock all repositories
        with patch(
            "nikita.db.database.get_session_maker"
        ) as mock_session_maker, patch(
            "nikita.db.repositories.thought_repository.NikitaThoughtRepository"
        ) as mock_thought_repo_class, patch(
            "nikita.db.repositories.summary_repository.DailySummaryRepository"
        ) as mock_summary_repo_class, patch(
            "nikita.db.repositories.profile_repository.BackstoryRepository"
        ) as mock_backstory_repo_class:
            # Setup session context manager
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session_maker.return_value = MagicMock(return_value=mock_session)

            # Setup user repository
            with patch(
                "nikita.db.repositories.user_repository.UserRepository"
            ) as mock_user_repo_class:
                mock_user_repo = MagicMock()
                mock_user_repo.get = AsyncMock(return_value=mock_user)
                mock_user_repo_class.return_value = mock_user_repo

                # Setup thought repository
                mock_thought_repo = MagicMock()
                mock_thought_repo.get_thoughts_for_prompt = AsyncMock(
                    return_value=mock_thoughts
                )
                mock_thought_repo_class.return_value = mock_thought_repo

                # Setup summary repository (empty)
                mock_summary_repo = MagicMock()
                mock_summary_repo.get_by_date = AsyncMock(return_value=None)
                mock_summary_repo.get_range = AsyncMock(return_value=[])
                mock_summary_repo_class.return_value = mock_summary_repo

                # Setup backstory repository (empty)
                mock_backstory_repo = MagicMock()
                mock_backstory_repo.get_by_user_id = AsyncMock(return_value=None)
                mock_backstory_repo_class.return_value = mock_backstory_repo

                result = await handler._get_context(
                    user_id=test_user_id,
                    session_id="test_session",
                    data={},
                )

        assert "active_thoughts" in result
        assert "wondering" in result["active_thoughts"]
        assert result["active_thoughts"]["wondering"][0]["content"] == (
            "I wonder what he's up to today"
        )

    @pytest.mark.asyncio
    async def test_get_context_includes_today_summary(
        self, mock_settings, test_user_id
    ):
        """Phase 1: get_context returns today_summary."""
        from nikita.agents.voice.server_tools import ServerToolHandler

        handler = ServerToolHandler(settings=mock_settings)

        # Create mock user
        mock_user = MagicMock()
        mock_user.name = "Test User"
        mock_user.chapter = 3
        mock_user.game_status = "active"
        mock_user.metrics = MagicMock(
            relationship_score=65.0, intimacy=60.0, passion=55.0, trust=70.0
        )
        mock_user.engagement_state = MagicMock(state="in_zone")
        mock_user.vice_preferences = []

        # Mock today's summary
        # Spec 031 T2.2: Explicitly set summary_text=None so fallback to nikita_summary_text works
        mock_summary = MagicMock()
        mock_summary.summary_text = None  # New preferred column
        mock_summary.nikita_summary_text = "We had a great conversation about his work"

        with patch(
            "nikita.db.database.get_session_maker"
        ) as mock_session_maker, patch(
            "nikita.db.repositories.thought_repository.NikitaThoughtRepository"
        ) as mock_thought_repo_class, patch(
            "nikita.db.repositories.summary_repository.DailySummaryRepository"
        ) as mock_summary_repo_class, patch(
            "nikita.db.repositories.profile_repository.BackstoryRepository"
        ) as mock_backstory_repo_class:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session_maker.return_value = MagicMock(return_value=mock_session)

            with patch(
                "nikita.db.repositories.user_repository.UserRepository"
            ) as mock_user_repo_class:
                mock_user_repo = MagicMock()
                mock_user_repo.get = AsyncMock(return_value=mock_user)
                mock_user_repo_class.return_value = mock_user_repo

                mock_thought_repo = MagicMock()
                mock_thought_repo.get_thoughts_for_prompt = AsyncMock(return_value={})
                mock_thought_repo_class.return_value = mock_thought_repo

                mock_summary_repo = MagicMock()
                mock_summary_repo.get_by_date = AsyncMock(return_value=mock_summary)
                mock_summary_repo.get_range = AsyncMock(return_value=[])
                mock_summary_repo_class.return_value = mock_summary_repo

                mock_backstory_repo = MagicMock()
                mock_backstory_repo.get_by_user_id = AsyncMock(return_value=None)
                mock_backstory_repo_class.return_value = mock_backstory_repo

                result = await handler._get_context(
                    user_id=test_user_id,
                    session_id="test_session",
                    data={},
                )

        assert "today_summary" in result
        assert result["today_summary"] == "We had a great conversation about his work"

    @pytest.mark.asyncio
    async def test_get_context_includes_week_summaries(
        self, mock_settings, test_user_id
    ):
        """Phase 1: get_context returns week_summaries dict."""
        from datetime import date
        from nikita.agents.voice.server_tools import ServerToolHandler

        handler = ServerToolHandler(settings=mock_settings)

        mock_user = MagicMock()
        mock_user.name = "Test User"
        mock_user.chapter = 3
        mock_user.game_status = "active"
        mock_user.metrics = MagicMock(
            relationship_score=65.0, intimacy=60.0, passion=55.0, trust=70.0
        )
        mock_user.engagement_state = MagicMock(state="in_zone")
        mock_user.vice_preferences = []

        # Mock week summaries
        # Spec 031 T2.2: Explicitly set summary_text=None so fallback to nikita_summary_text works
        mock_summary_1 = MagicMock()
        mock_summary_1.date = date(2026, 1, 10)
        mock_summary_1.summary_text = None  # New preferred column
        mock_summary_1.nikita_summary_text = "Monday was fun"

        mock_summary_2 = MagicMock()
        mock_summary_2.date = date(2026, 1, 9)
        mock_summary_2.summary_text = None  # New preferred column
        mock_summary_2.nikita_summary_text = "Sunday was quiet"

        with patch(
            "nikita.db.database.get_session_maker"
        ) as mock_session_maker, patch(
            "nikita.db.repositories.thought_repository.NikitaThoughtRepository"
        ) as mock_thought_repo_class, patch(
            "nikita.db.repositories.summary_repository.DailySummaryRepository"
        ) as mock_summary_repo_class, patch(
            "nikita.db.repositories.profile_repository.BackstoryRepository"
        ) as mock_backstory_repo_class:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session_maker.return_value = MagicMock(return_value=mock_session)

            with patch(
                "nikita.db.repositories.user_repository.UserRepository"
            ) as mock_user_repo_class:
                mock_user_repo = MagicMock()
                mock_user_repo.get = AsyncMock(return_value=mock_user)
                mock_user_repo_class.return_value = mock_user_repo

                mock_thought_repo = MagicMock()
                mock_thought_repo.get_thoughts_for_prompt = AsyncMock(return_value={})
                mock_thought_repo_class.return_value = mock_thought_repo

                mock_summary_repo = MagicMock()
                mock_summary_repo.get_by_date = AsyncMock(return_value=None)
                mock_summary_repo.get_range = AsyncMock(
                    return_value=[mock_summary_1, mock_summary_2]
                )
                mock_summary_repo_class.return_value = mock_summary_repo

                mock_backstory_repo = MagicMock()
                mock_backstory_repo.get_by_user_id = AsyncMock(return_value=None)
                mock_backstory_repo_class.return_value = mock_backstory_repo

                result = await handler._get_context(
                    user_id=test_user_id,
                    session_id="test_session",
                    data={},
                )

        assert "week_summaries" in result
        assert len(result["week_summaries"]) == 2
        assert "2026-01-10" in result["week_summaries"]
        assert result["week_summaries"]["2026-01-10"] == "Monday was fun"

    @pytest.mark.asyncio
    async def test_get_context_includes_backstory(self, mock_settings, test_user_id):
        """Phase 1: get_context returns backstory with venue and scenario."""
        from nikita.agents.voice.server_tools import ServerToolHandler

        handler = ServerToolHandler(settings=mock_settings)

        mock_user = MagicMock()
        mock_user.name = "Test User"
        mock_user.chapter = 3
        mock_user.game_status = "active"
        mock_user.metrics = MagicMock(
            relationship_score=65.0, intimacy=60.0, passion=55.0, trust=70.0
        )
        mock_user.engagement_state = MagicMock(state="in_zone")
        mock_user.vice_preferences = []

        # Mock backstory
        mock_backstory = MagicMock()
        mock_backstory.venue_name = "Berghain"
        mock_backstory.venue_city = "Berlin"
        mock_backstory.scenario_type = "chaotic"
        mock_backstory.how_we_met = "We met on the dance floor at 4am"
        mock_backstory.the_moment = "You made me laugh when the music stopped"
        mock_backstory.unresolved_hook = "You never told me your real name"

        with patch(
            "nikita.db.database.get_session_maker"
        ) as mock_session_maker, patch(
            "nikita.db.repositories.thought_repository.NikitaThoughtRepository"
        ) as mock_thought_repo_class, patch(
            "nikita.db.repositories.summary_repository.DailySummaryRepository"
        ) as mock_summary_repo_class, patch(
            "nikita.db.repositories.profile_repository.BackstoryRepository"
        ) as mock_backstory_repo_class:
            mock_session = MagicMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session_maker.return_value = MagicMock(return_value=mock_session)

            with patch(
                "nikita.db.repositories.user_repository.UserRepository"
            ) as mock_user_repo_class:
                mock_user_repo = MagicMock()
                mock_user_repo.get = AsyncMock(return_value=mock_user)
                mock_user_repo_class.return_value = mock_user_repo

                mock_thought_repo = MagicMock()
                mock_thought_repo.get_thoughts_for_prompt = AsyncMock(return_value={})
                mock_thought_repo_class.return_value = mock_thought_repo

                mock_summary_repo = MagicMock()
                mock_summary_repo.get_by_date = AsyncMock(return_value=None)
                mock_summary_repo.get_range = AsyncMock(return_value=[])
                mock_summary_repo_class.return_value = mock_summary_repo

                mock_backstory_repo = MagicMock()
                mock_backstory_repo.get_by_user_id = AsyncMock(
                    return_value=mock_backstory
                )
                mock_backstory_repo_class.return_value = mock_backstory_repo

                result = await handler._get_context(
                    user_id=test_user_id,
                    session_id="test_session",
                    data={},
                )

        assert "backstory" in result
        assert result["backstory"]["venue_name"] == "Berghain"
        assert result["backstory"]["venue_city"] == "Berlin"
        assert result["backstory"]["scenario_type"] == "chaotic"
        assert result["backstory"]["how_we_met"] == "We met on the dance floor at 4am"
        assert result["backstory"]["the_moment"] == (
            "You made me laugh when the music stopped"
        )
        assert result["backstory"]["unresolved_hook"] == (
            "You never told me your real name"
        )


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
        """AC-FR022-001: Graceful degradation when Memory unavailable."""
        from nikita.agents.voice.server_tools import ServerToolHandler

        handler = ServerToolHandler(settings=mock_settings)

        # Mock memory client that fails (patch at source module)
        # Also mock the DB session maker since we don't want real DB calls
        with patch(
            "nikita.memory.get_memory_client",
            side_effect=Exception("Memory connection failed"),
        ), patch(
            "nikita.db.database.get_session_maker",
            side_effect=Exception("DB unavailable"),
        ):
            result = await handler._get_memory(
                user_id=str(uuid4()),
                session_id="test_session",
                data={"query": "recent"},
            )

        # Should return empty results, not raise exception
        assert result.get("facts") == []
        assert result.get("threads") == []
        assert "error" in result

    @pytest.mark.asyncio
    async def test_update_memory_graceful_degradation(self, mock_settings):
        """Memory updates fail gracefully when Memory unavailable."""
        from nikita.agents.voice.server_tools import ServerToolHandler

        handler = ServerToolHandler(settings=mock_settings)

        # Patch at source module, not where used
        with patch(
            "nikita.memory.get_memory_client",
            side_effect=Exception("Memory connection failed"),
        ):
            result = await handler._update_memory(
                user_id=str(uuid4()),
                session_id="test_session",
                data={"fact": "Test fact"},
            )

        # Should return error but not crash
        assert result.get("stored") is False
        assert "error" in result
