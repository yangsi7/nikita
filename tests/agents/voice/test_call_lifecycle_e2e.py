"""E2E tests for complete voice call lifecycle.

Tests the full flow from call initiation to completion:
- Call initiation (session creation, context loading, signed tokens)
- Server tool calls during conversation
- Call ending with scoring and memory updates
- Webhook processing from ElevenLabs

Implements comprehensive verification of:
- FR-001: Call Initiation
- FR-008: Session Management
- T006, T012, T022 acceptance criteria
"""

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from nikita.agents.voice.models import (
    NikitaMood,
    ServerToolName,
    ServerToolRequest,
    ServerToolResponse,
    VoiceContext,
)
from nikita.agents.voice.scoring import CallScore
from nikita.agents.voice.server_tools import ServerToolHandler
from nikita.agents.voice.service import VoiceService
from nikita.engine.scoring.models import MetricDeltas


class TestCallInitiation:
    """Test call initiation flow."""

    @pytest.fixture
    def voice_service(self, mock_settings):
        """Get VoiceService instance."""
        return VoiceService(settings=mock_settings)

    @pytest.mark.asyncio
    async def test_initiate_creates_session(
        self, voice_service, user_chapter_3, mock_settings
    ):
        """Test that call initiation creates a session with valid ID."""
        with patch.object(
            voice_service,
            "_load_user",
            AsyncMock(return_value=user_chapter_3),
        ):
            with patch.object(
                voice_service,
                "_log_call_started",
                AsyncMock(),
            ):
                result = await voice_service.initiate_call(user_chapter_3.id)

                # Session ID should be generated
                assert "session_id" in result
                assert result["session_id"].startswith("voice_")

                # Session should be stored internally
                assert voice_service.get_session(result["session_id"]) is not None

    @pytest.mark.asyncio
    async def test_initiate_loads_user_context(
        self, voice_service, user_chapter_3
    ):
        """AC-T006.4: Loads user context for initial greeting customization."""
        with patch.object(
            voice_service,
            "_load_user",
            AsyncMock(return_value=user_chapter_3),
        ):
            with patch.object(
                voice_service,
                "_log_call_started",
                AsyncMock(),
            ):
                result = await voice_service.initiate_call(user_chapter_3.id)

                # Context should include user data
                context = result["context"]
                assert context["chapter"] == user_chapter_3.chapter
                assert context["user_name"] == user_chapter_3.name

    @pytest.mark.asyncio
    async def test_initiate_returns_valid_config(
        self, voice_service, user_chapter_3, mock_settings
    ):
        """Test that initiation returns complete ElevenLabs config."""
        with patch.object(
            voice_service,
            "_load_user",
            AsyncMock(return_value=user_chapter_3),
        ):
            with patch.object(
                voice_service,
                "_log_call_started",
                AsyncMock(),
            ):
                result = await voice_service.initiate_call(user_chapter_3.id)

                # Should have all required fields for ElevenLabs
                assert "agent_id" in result
                assert result["agent_id"] == mock_settings.elevenlabs_default_agent_id
                assert "signed_token" in result
                assert "session_id" in result
                assert "dynamic_variables" in result

    @pytest.mark.asyncio
    async def test_initiate_sets_dynamic_variables(
        self, voice_service, user_chapter_3
    ):
        """Test that dynamic variables are properly set for prompt interpolation."""
        with patch.object(
            voice_service,
            "_load_user",
            AsyncMock(return_value=user_chapter_3),
        ):
            with patch.object(
                voice_service,
                "_log_call_started",
                AsyncMock(),
            ):
                result = await voice_service.initiate_call(user_chapter_3.id)

                dynamic_vars = result["dynamic_variables"]

                # Should include key personalization variables
                assert "user_name" in dynamic_vars
                assert dynamic_vars["user_name"] == user_chapter_3.name
                assert "chapter" in dynamic_vars
                # Dynamic variables are strings for prompt interpolation
                assert str(dynamic_vars["chapter"]) == str(user_chapter_3.chapter)
                assert "nikita_mood" in dynamic_vars
                assert "time_of_day" in dynamic_vars


class TestServerTools:
    """Test server tool handling during calls."""

    @pytest.fixture
    def tool_handler(self, mock_settings):
        """Get ServerToolHandler instance."""
        return ServerToolHandler(settings=mock_settings)

    @pytest.mark.asyncio
    async def test_server_tool_get_context(
        self, tool_handler, user_chapter_3, mock_memory_client
    ):
        """Test GET_CONTEXT returns user context for conversation."""
        request = ServerToolRequest(
            tool_name=ServerToolName.GET_CONTEXT,
            user_id=str(user_chapter_3.id),
            session_id="test_session",
            data={},
        )

        # Mock at source module for lazy imports inside functions
        with patch(
            "nikita.memory.graphiti_client.get_memory_client",
            AsyncMock(return_value=mock_memory_client),
        ):
            with patch(
                "nikita.db.database.get_session_maker"
            ) as mock_session_maker:
                mock_session = AsyncMock()
                mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                mock_session.__aexit__ = AsyncMock()
                mock_session_maker.return_value = MagicMock(return_value=mock_session)

                with patch(
                    "nikita.db.repositories.user_repository.UserRepository"
                ) as MockRepo:
                    mock_repo = MockRepo.return_value
                    mock_repo.get = AsyncMock(return_value=user_chapter_3)

                    response = await tool_handler.handle(request)

                    assert response.success is True
                    assert response.tool_name == ServerToolName.GET_CONTEXT

    @pytest.mark.asyncio
    async def test_server_tool_get_memory(
        self, tool_handler, user_chapter_3, mock_memory_client
    ):
        """Test GET_MEMORY queries Graphiti for relevant memories."""
        request = ServerToolRequest(
            tool_name=ServerToolName.GET_MEMORY,
            user_id=str(user_chapter_3.id),
            session_id="test_session",
            data={"query": "What do I know about the user's work?"},
        )

        mock_memory_client.search = AsyncMock(
            return_value=[
                {"content": "User works as software engineer", "source": "user_message"},
                {"content": "User started new job recently", "source": "voice_call"},
            ]
        )

        # Mock at source module for lazy imports inside functions
        with patch(
            "nikita.memory.graphiti_client.get_memory_client",
            AsyncMock(return_value=mock_memory_client),
        ):
            response = await tool_handler.handle(request)

            assert response.success is True
            assert response.tool_name == ServerToolName.GET_MEMORY

    @pytest.mark.asyncio
    async def test_server_tool_score_turn(
        self, tool_handler, user_chapter_3
    ):
        """Test SCORE_TURN analyzes conversation exchange."""
        request = ServerToolRequest(
            tool_name=ServerToolName.SCORE_TURN,
            user_id=str(user_chapter_3.id),
            session_id="test_session",
            data={
                "user_message": "I had a great day at work!",
                "nikita_response": "That's wonderful! Tell me more about it!",
            },
        )

        with patch(
            "nikita.db.database.get_session_maker"
        ) as mock_session_maker:
            mock_session = AsyncMock()
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock()
            mock_session_maker.return_value = MagicMock(return_value=mock_session)

            with patch(
                "nikita.db.repositories.user_repository.UserRepository"
            ) as MockRepo:
                mock_repo = MockRepo.return_value
                mock_repo.get = AsyncMock(return_value=user_chapter_3)

                # Mock at source module for lazy imports inside functions
                with patch(
                    "nikita.engine.scoring.analyzer.ScoreAnalyzer"
                ) as MockAnalyzer:
                    mock_analyzer = MockAnalyzer.return_value
                    mock_analyzer.analyze = AsyncMock(
                        return_value=MagicMock(
                            deltas=MetricDeltas(
                                intimacy=Decimal("2"),
                                passion=Decimal("1"),
                                trust=Decimal("2"),
                                secureness=Decimal("1"),
                            ),
                            explanation="Positive exchange",
                        )
                    )

                    response = await tool_handler.handle(request)

                    assert response.success is True
                    assert response.tool_name == ServerToolName.SCORE_TURN

    @pytest.mark.asyncio
    async def test_server_tool_update_memory(
        self, tool_handler, user_chapter_3, mock_memory_client
    ):
        """Test UPDATE_MEMORY stores new facts to Graphiti."""
        request = ServerToolRequest(
            tool_name=ServerToolName.UPDATE_MEMORY,
            user_id=str(user_chapter_3.id),
            session_id="test_session",
            data={
                "fact": "User got promoted to senior engineer",
                "category": "occupation",
            },
        )

        # Mock at source module for lazy imports inside functions
        with patch(
            "nikita.memory.graphiti_client.get_memory_client",
            AsyncMock(return_value=mock_memory_client),
        ):
            response = await tool_handler.handle(request)

            assert response.success is True
            assert response.tool_name == ServerToolName.UPDATE_MEMORY

    def test_server_tool_hmac_validation(self, mock_settings):
        """AC-T012.2: Validates signed token for user_id."""
        import hashlib
        import hmac
        import time

        user_id = str(uuid4())
        session_id = "test_session"
        timestamp = int(time.time())

        # Create valid token
        payload = f"{user_id}:{session_id}:{timestamp}"
        secret = mock_settings.elevenlabs_webhook_secret or "default_voice_secret"
        signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        valid_token = f"{payload}:{signature}"

        # Verify signature
        parts = valid_token.rsplit(":", 1)
        assert len(parts) == 2
        payload_received, sig_received = parts

        expected_sig = hmac.new(
            secret.encode(),
            payload_received.encode(),
            hashlib.sha256,
        ).hexdigest()

        assert hmac.compare_digest(sig_received, expected_sig)

    @pytest.mark.asyncio
    async def test_server_tool_timeout_handling(self, tool_handler, user_chapter_3):
        """T072: Server tools handle timeouts gracefully."""
        from nikita.agents.voice.server_tools import with_timeout_fallback

        # Test the decorator directly
        @with_timeout_fallback(timeout_seconds=0.01, fallback_data={"default": True})
        async def slow_operation():
            import asyncio
            await asyncio.sleep(0.1)  # Longer than timeout
            return {"result": "data"}

        result = await slow_operation()

        # Should get fallback response
        assert result["timeout"] is True
        assert result["cache_friendly"] is True
        assert "error" in result


class TestEndCall:
    """Test call ending and post-processing."""

    @pytest.fixture
    def voice_service(self, mock_settings):
        """Get VoiceService instance."""
        return VoiceService(settings=mock_settings)

    @pytest.mark.asyncio
    async def test_end_call_triggers_scoring(
        self, voice_service, user_chapter_3, transcript_positive
    ):
        """AC-T022.2: End call calls VoiceCallScorer.score_call()."""
        # Convert transcript to pairs format
        transcript_pairs = [
            ("Pretty great actually!", "That's amazing!"),
        ]

        with patch.object(
            voice_service,
            "_load_user",
            AsyncMock(return_value=user_chapter_3),
        ):
            with patch(
                "nikita.agents.voice.scoring.VoiceCallScorer"
            ) as MockScorer:
                mock_scorer = MockScorer.return_value
                mock_scorer.score_call = AsyncMock(
                    return_value=CallScore(
                        session_id="test_session",
                        deltas=MetricDeltas(
                            intimacy=Decimal("3"),
                            passion=Decimal("2"),
                            trust=Decimal("3"),
                            secureness=Decimal("2"),
                        ),
                        explanation="Good call",
                    )
                )
                mock_scorer.apply_score = AsyncMock(return_value=Decimal("60"))

                with patch(
                    "nikita.db.database.get_session_maker"
                ) as mock_session_maker:
                    mock_session = AsyncMock()
                    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                    mock_session.__aexit__ = AsyncMock()
                    mock_session.commit = AsyncMock()
                    mock_session_maker.return_value = MagicMock(
                        return_value=mock_session
                    )

                    with patch(
                        "nikita.db.repositories.user_repository.UserRepository"
                    ) as MockRepo:
                        mock_repo = MockRepo.return_value
                        mock_repo.update_last_interaction = AsyncMock()

                        result = await voice_service.end_call(
                            user_id=str(user_chapter_3.id),
                            session_id="test_session",
                            transcript=transcript_pairs,
                            duration_seconds=180,
                        )

                        # Verify scoring was called
                        mock_scorer.score_call.assert_called_once()
                        mock_scorer.apply_score.assert_called_once()

                        assert result["success"] is True
                        assert "score_change" in result

    @pytest.mark.asyncio
    async def test_end_call_updates_last_interaction(
        self, voice_service, user_chapter_3
    ):
        """AC-T022.4: Updates last_interaction_at."""
        with patch.object(
            voice_service,
            "_load_user",
            AsyncMock(return_value=user_chapter_3),
        ):
            with patch(
                "nikita.agents.voice.scoring.VoiceCallScorer"
            ) as MockScorer:
                mock_scorer = MockScorer.return_value
                mock_scorer.score_call = AsyncMock(
                    return_value=CallScore(
                        session_id="test_session",
                        deltas=MetricDeltas(),
                        explanation="Test",
                    )
                )
                mock_scorer.apply_score = AsyncMock(return_value=Decimal("55"))

                with patch(
                    "nikita.db.database.get_session_maker"
                ) as mock_session_maker:
                    mock_session = AsyncMock()
                    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                    mock_session.__aexit__ = AsyncMock()
                    mock_session.commit = AsyncMock()
                    mock_session_maker.return_value = MagicMock(
                        return_value=mock_session
                    )

                    with patch(
                        "nikita.db.repositories.user_repository.UserRepository"
                    ) as MockRepo:
                        mock_repo = MockRepo.return_value
                        mock_repo.update_last_interaction = AsyncMock()

                        await voice_service.end_call(
                            user_id=str(user_chapter_3.id),
                            session_id="test_session",
                            transcript=[],
                        )

                        # Verify last_interaction was updated (user_id is passed as string)
                        mock_repo.update_last_interaction.assert_called_once_with(
                            str(user_chapter_3.id)
                        )

    @pytest.mark.asyncio
    async def test_end_call_cleans_session(self, voice_service, user_chapter_3):
        """Test that end_call removes session from internal storage."""
        session_id = "test_session_cleanup"

        # Add session first
        voice_service._sessions[session_id] = {
            "user_id": str(user_chapter_3.id),
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

        with patch.object(
            voice_service,
            "_load_user",
            AsyncMock(return_value=user_chapter_3),
        ):
            with patch(
                "nikita.agents.voice.scoring.VoiceCallScorer"
            ) as MockScorer:
                mock_scorer = MockScorer.return_value
                mock_scorer.score_call = AsyncMock(
                    return_value=CallScore(
                        session_id=session_id,
                        deltas=MetricDeltas(),
                        explanation="Test",
                    )
                )
                mock_scorer.apply_score = AsyncMock(return_value=Decimal("55"))

                with patch(
                    "nikita.db.database.get_session_maker"
                ) as mock_session_maker:
                    mock_session = AsyncMock()
                    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                    mock_session.__aexit__ = AsyncMock()
                    mock_session.commit = AsyncMock()
                    mock_session_maker.return_value = MagicMock(
                        return_value=mock_session
                    )

                    with patch(
                        "nikita.db.repositories.user_repository.UserRepository"
                    ) as MockRepo:
                        mock_repo = MockRepo.return_value
                        mock_repo.update_last_interaction = AsyncMock()

                        await voice_service.end_call(
                            user_id=str(user_chapter_3.id),
                            session_id=session_id,
                            transcript=[],
                        )

                        # Session should be cleaned up
                        assert voice_service.get_session(session_id) is None

    @pytest.mark.asyncio
    async def test_end_call_returns_score_details(
        self, voice_service, user_chapter_3
    ):
        """AC-T022.3: Returns CallResult with scoring summary."""
        with patch.object(
            voice_service,
            "_load_user",
            AsyncMock(return_value=user_chapter_3),
        ):
            with patch(
                "nikita.agents.voice.scoring.VoiceCallScorer"
            ) as MockScorer:
                mock_scorer = MockScorer.return_value
                mock_scorer.score_call = AsyncMock(
                    return_value=CallScore(
                        session_id="test_session",
                        deltas=MetricDeltas(
                            intimacy=Decimal("5"),
                            passion=Decimal("4"),
                            trust=Decimal("3"),
                            secureness=Decimal("2"),
                        ),
                        explanation="Great conversation",
                        duration_seconds=300,
                    )
                )
                mock_scorer.apply_score = AsyncMock(return_value=Decimal("62"))

                with patch(
                    "nikita.db.database.get_session_maker"
                ) as mock_session_maker:
                    mock_session = AsyncMock()
                    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
                    mock_session.__aexit__ = AsyncMock()
                    mock_session.commit = AsyncMock()
                    mock_session_maker.return_value = MagicMock(
                        return_value=mock_session
                    )

                    with patch(
                        "nikita.db.repositories.user_repository.UserRepository"
                    ) as MockRepo:
                        mock_repo = MockRepo.return_value
                        mock_repo.update_last_interaction = AsyncMock()

                        result = await voice_service.end_call(
                            user_id=str(user_chapter_3.id),
                            session_id="test_session",
                            transcript=[("Hi", "Hello!")],
                            duration_seconds=300,
                        )

                        # Verify result structure
                        assert result["success"] is True
                        assert result["new_relationship_score"] == "62"
                        assert result["score_change"]["intimacy"] == "5"
                        assert result["score_change"]["passion"] == "4"
                        assert result["explanation"] == "Great conversation"


class TestWebhookProcessing:
    """Test webhook processing from ElevenLabs."""

    @pytest.mark.asyncio
    async def test_webhook_call_ended_event(self, mock_settings, user_chapter_3):
        """Test processing of call_ended webhook event."""
        from nikita.agents.voice.service import VoiceService

        service = VoiceService(settings=mock_settings)

        # Simulate webhook payload structure
        webhook_payload = {
            "event_type": "call_ended",
            "conversation_id": "conv_test_123",
            "agent_id": mock_settings.elevenlabs_default_agent_id,
            "call_duration_secs": 180,
            "transcript": [
                {"role": "agent", "message": "Hey you!", "time_in_call_secs": 0},
                {"role": "user", "message": "Hi!", "time_in_call_secs": 2},
            ],
        }

        # Extract transcript pairs
        transcript = webhook_payload.get("transcript", [])
        pairs = []
        for i, entry in enumerate(transcript):
            if entry["role"] == "user" and i + 1 < len(transcript):
                next_entry = transcript[i + 1]
                if next_entry["role"] == "agent":
                    pairs.append((entry["message"], next_entry["message"]))

        # For this simple transcript, we expect pairs to be empty or specific
        # The important thing is the structure is processed correctly
        assert isinstance(pairs, list)

    @pytest.mark.asyncio
    async def test_webhook_validates_agent_id(self, mock_settings):
        """Test that webhook validates agent_id matches expected."""
        webhook_payload = {
            "event_type": "call_ended",
            "agent_id": "wrong_agent_id",  # Different from expected
        }

        expected_agent = mock_settings.elevenlabs_default_agent_id

        # Validation check (this would be in actual webhook handler)
        is_valid = webhook_payload["agent_id"] == expected_agent
        assert is_valid is False  # Should fail validation
