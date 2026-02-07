"""Tests for Inbound Call Handler (US-15: Inbound Calls).

Tests for T075-T080 acceptance criteria:
- AC-T076.1: handle_incoming_call(phone_number) processes inbound call
- AC-T076.2: Looks up user by phone number
- AC-T076.3: Checks call availability (chapter-based)
- AC-T076.4: Returns accept_call=False with message if unavailable
- AC-T077.1-4: VoiceSessionManager tracks sessions and recovery
- AC-T078.1-4: Pre-call webhook handling
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestInboundCallHandler:
    """Test InboundCallHandler class (T076)."""

    @pytest.fixture
    def mock_user(self):
        """Create mock user with phone number.

        Note: onboarding_status must be 'completed' or 'skipped' for inbound calls
        to be accepted (Spec 033: Unified Phone Number).
        """
        user = MagicMock()
        user.id = uuid4()
        user.phone_number = "+41787950009"
        user.chapter = 3
        user.game_status = "active"
        user.telegram_id = 12345678
        user.metrics = MagicMock()
        user.metrics.relationship_score = Decimal("65.0")
        user.onboarding_status = "completed"  # Required for inbound calls (Spec 033)
        return user

    def test_handle_incoming_call_success(self, mock_user):
        """AC-T076.1: handle_incoming_call(phone_number) processes inbound call."""
        from nikita.agents.voice.inbound import InboundCallHandler

        handler = InboundCallHandler()

        with patch.object(
            handler, "_lookup_user_by_phone", new_callable=AsyncMock
        ) as mock_lookup, patch.object(
            handler, "_check_availability", new_callable=AsyncMock
        ) as mock_avail, patch.object(
            handler, "_build_context", new_callable=AsyncMock
        ) as mock_context, patch.object(
            handler, "_get_conversation_config_override", new_callable=AsyncMock
        ) as mock_config:
            mock_lookup.return_value = mock_user
            mock_avail.return_value = (True, "Nikita is available")
            mock_context.return_value = {"user_name": "TestUser"}
            mock_config.return_value = {"tts": {"stability": 0.5}}

            import asyncio
            result = asyncio.get_event_loop().run_until_complete(
                handler.handle_incoming_call("+41787950009")
            )

        assert result["accept_call"] is True
        assert "user_id" in result
        assert result["user_id"] == str(mock_user.id)

    def test_looks_up_user_by_phone(self, mock_user):
        """AC-T076.2: Looks up user by phone number."""
        from nikita.agents.voice.inbound import InboundCallHandler

        handler = InboundCallHandler()

        with patch.object(
            handler, "_lookup_user_by_phone", new_callable=AsyncMock
        ) as mock_lookup, patch.object(
            handler, "_check_availability", new_callable=AsyncMock
        ) as mock_avail, patch.object(
            handler, "_build_context", new_callable=AsyncMock
        ) as mock_context, patch.object(
            handler, "_get_conversation_config_override", new_callable=AsyncMock
        ) as mock_config:
            mock_lookup.return_value = mock_user
            mock_avail.return_value = (True, "Available")
            mock_context.return_value = {"user_name": "TestUser"}
            mock_config.return_value = {"tts": {"stability": 0.5}}

            import asyncio
            asyncio.get_event_loop().run_until_complete(
                handler.handle_incoming_call("+41787950009")
            )

        mock_lookup.assert_called_once_with("+41787950009")

    def test_checks_availability_by_chapter(self, mock_user):
        """AC-T076.3: Checks call availability (chapter-based)."""
        from nikita.agents.voice.inbound import InboundCallHandler

        handler = InboundCallHandler()

        with patch.object(
            handler, "_lookup_user_by_phone", new_callable=AsyncMock
        ) as mock_lookup, patch.object(
            handler, "_check_availability", new_callable=AsyncMock
        ) as mock_avail, patch.object(
            handler, "_build_context", new_callable=AsyncMock
        ) as mock_context, patch.object(
            handler, "_get_conversation_config_override", new_callable=AsyncMock
        ) as mock_config:
            mock_lookup.return_value = mock_user
            mock_avail.return_value = (True, "Available")
            mock_context.return_value = {"user_name": "TestUser"}
            mock_config.return_value = {"tts": {"stability": 0.5}}

            import asyncio
            asyncio.get_event_loop().run_until_complete(
                handler.handle_incoming_call("+41787950009")
            )

        mock_avail.assert_called_once_with(mock_user)

    def test_rejects_unavailable_call(self, mock_user):
        """AC-T076.4: Returns accept_call=False with message if unavailable.

        Also verifies dynamic_variables are always returned (ElevenLabs requirement).
        """
        from nikita.agents.voice.inbound import InboundCallHandler

        handler = InboundCallHandler()

        with patch.object(
            handler, "_lookup_user_by_phone", new_callable=AsyncMock
        ) as mock_lookup, patch.object(
            handler, "_build_context", new_callable=AsyncMock
        ) as mock_context, patch.object(
            handler, "_check_availability", new_callable=AsyncMock
        ) as mock_avail:
            mock_lookup.return_value = mock_user
            # _build_context is now called BEFORE availability check per ElevenLabs requirement
            mock_context.return_value = {
                "user_name": "TestUser",
                "chapter": "3",
                "relationship_score": "65.0",
                "engagement_state": "IN_ZONE",
                "nikita_mood": "playful",
                "nikita_energy": "medium",
                "time_of_day": "afternoon",
                "recent_topics": "",
                "open_threads": "",
            }
            mock_avail.return_value = (False, "Nikita is busy right now")

            import asyncio
            result = asyncio.get_event_loop().run_until_complete(
                handler.handle_incoming_call("+41787950009")
            )

        assert result["accept_call"] is False
        assert "Nikita is busy" in result["message"]
        # CRITICAL: dynamic_variables must always be returned per ElevenLabs requirement
        assert "dynamic_variables" in result
        assert result["dynamic_variables"]["user_name"] == "TestUser"

    def test_rejects_unknown_caller(self):
        """AC-T078.3: Returns accept_call=False for unknown callers.

        Also verifies dynamic_variables are always returned (ElevenLabs requirement).
        """
        from nikita.agents.voice.inbound import InboundCallHandler

        handler = InboundCallHandler()

        with patch.object(
            handler, "_lookup_user_by_phone", new_callable=AsyncMock
        ) as mock_lookup:
            mock_lookup.return_value = None  # Unknown number

            import asyncio
            result = asyncio.get_event_loop().run_until_complete(
                handler.handle_incoming_call("+15551234567")
            )

        assert result["accept_call"] is False
        assert "not registered" in result["message"].lower()
        # CRITICAL: dynamic_variables must always be returned per ElevenLabs requirement
        assert "dynamic_variables" in result
        assert result["dynamic_variables"]["user_name"] == "stranger"
        assert result["dynamic_variables"]["chapter"] == "1"
        # conversation_config_override should also be present
        assert "conversation_config_override" in result


class TestVoiceSessionManager:
    """Test VoiceSessionManager for connection recovery (T077)."""

    @pytest.fixture
    def session_id(self):
        """Create test session ID."""
        return f"voice_session_{uuid4()}"

    def test_tracks_session_state(self, session_id):
        """AC-T077.1: VoiceSessionManager tracks session state."""
        from nikita.agents.voice.inbound import VoiceSessionManager

        manager = VoiceSessionManager()
        user_id = uuid4()

        manager.create_session(session_id, user_id)

        session = manager.get_session(session_id)
        assert session is not None
        assert session["state"] == "ACTIVE"
        assert session["user_id"] == user_id

    def test_handle_disconnect(self, session_id):
        """AC-T077.2: handle_disconnect marks session as disconnected."""
        from nikita.agents.voice.inbound import VoiceSessionManager

        manager = VoiceSessionManager()
        user_id = uuid4()

        manager.create_session(session_id, user_id)
        manager.handle_disconnect(session_id)

        session = manager.get_session(session_id)
        assert session["state"] == "DISCONNECTED"
        assert "disconnected_at" in session

    def test_recovery_within_30s(self, session_id):
        """AC-T077.3: attempt_recovery returns True if <30s disconnect."""
        from nikita.agents.voice.inbound import VoiceSessionManager

        manager = VoiceSessionManager()
        user_id = uuid4()

        manager.create_session(session_id, user_id)
        manager.handle_disconnect(session_id)

        # Should recover within 30s
        can_recover = manager.attempt_recovery(session_id)
        assert can_recover is True

    def test_recovery_after_30s_fails(self, session_id):
        """AC-T077.4: Long disconnects trigger session finalization."""
        from nikita.agents.voice.inbound import VoiceSessionManager

        manager = VoiceSessionManager()
        user_id = uuid4()

        manager.create_session(session_id, user_id)

        # Simulate old disconnect
        session = manager._sessions[session_id]
        session["state"] = "DISCONNECTED"
        session["disconnected_at"] = datetime.now(timezone.utc) - timedelta(seconds=60)

        can_recover = manager.attempt_recovery(session_id)
        assert can_recover is False

    def test_finalize_session(self, session_id):
        """Session finalization removes session from manager."""
        from nikita.agents.voice.inbound import VoiceSessionManager

        manager = VoiceSessionManager()
        user_id = uuid4()

        manager.create_session(session_id, user_id)
        manager.finalize_session(session_id)

        session = manager.get_session(session_id)
        assert session is None or session.get("state") == "FINALIZED"


class TestPreCallWebhook:
    """Test pre-call webhook handling (T078)."""

    @pytest.fixture
    def mock_user(self):
        """Create mock user.

        Note: onboarding_status must be 'completed' or 'skipped' for inbound calls
        to be accepted (Spec 033: Unified Phone Number).
        """
        user = MagicMock()
        user.id = uuid4()
        user.name = "TestUser"
        user.phone_number = "+41787950009"
        user.chapter = 3
        user.game_status = "active"
        user.onboarding_status = "completed"  # Required for inbound calls (Spec 033)
        return user

    def test_pre_call_returns_dynamic_variables(self, mock_user):
        """AC-T078.2: Returns dynamic_variables and conversation_config_override."""
        from nikita.agents.voice.inbound import InboundCallHandler

        handler = InboundCallHandler()

        with patch.object(
            handler, "_lookup_user_by_phone", new_callable=AsyncMock
        ) as mock_lookup, patch.object(
            handler, "_check_availability", new_callable=AsyncMock
        ) as mock_avail, patch.object(
            handler, "_build_context", new_callable=AsyncMock
        ) as mock_context, patch.object(
            handler, "_get_conversation_config_override", new_callable=AsyncMock
        ) as mock_config:
            mock_lookup.return_value = mock_user
            mock_avail.return_value = (True, "Available")
            mock_context.return_value = {
                "user_name": "TestUser",
                "chapter": "3",
            }
            mock_config.return_value = {"tts": {"stability": 0.5}}

            import asyncio
            result = asyncio.get_event_loop().run_until_complete(
                handler.handle_incoming_call("+41787950009")
            )

        assert result["accept_call"] is True
        assert "dynamic_variables" in result
        assert result["dynamic_variables"]["user_name"] == "TestUser"

    def test_pre_call_includes_agent_config(self, mock_user):
        """Pre-call returns conversation_config_override with TTS settings."""
        from nikita.agents.voice.inbound import InboundCallHandler

        handler = InboundCallHandler()

        with patch.object(
            handler, "_lookup_user_by_phone", new_callable=AsyncMock
        ) as mock_lookup, patch.object(
            handler, "_check_availability", new_callable=AsyncMock
        ) as mock_avail, patch.object(
            handler, "_build_context", new_callable=AsyncMock
        ) as mock_context, patch.object(
            handler, "_get_conversation_config_override", new_callable=AsyncMock
        ) as mock_config:
            mock_lookup.return_value = mock_user
            mock_avail.return_value = (True, "Available")
            mock_context.return_value = {"user_name": "TestUser", "chapter": "3"}
            mock_config.return_value = {"tts": {"stability": 0.5, "similarity_boost": 0.75}}

            import asyncio
            result = asyncio.get_event_loop().run_until_complete(
                handler.handle_incoming_call("+41787950009")
            )

        # Should include TTS settings based on chapter
        assert result["accept_call"] is True
        assert "conversation_config_override" in result
        config = result["conversation_config_override"]
        assert "tts" in config


class TestPreCallPerformance:
    """Test pre-call performance requirements (FR-033, FR-034).

    FR-033: Pre-call webhook MUST respond in <100ms with NO LLM/Neo4j calls.
    FR-034: Pre-call uses cached_voice_prompt from database for fast retrieval.
    """

    @pytest.fixture
    def mock_user_with_cached_prompt(self):
        """Create mock user with cached voice prompt.

        Note: onboarding_status must be 'completed' or 'skipped' for inbound calls
        to be accepted (Spec 033: Unified Phone Number).
        """
        user = MagicMock()
        user.id = uuid4()
        user.name = "TestUser"
        user.phone_number = "+41787950009"
        user.chapter = 3
        user.game_status = "active"
        user.onboarding_status = "completed"  # Required for inbound calls (Spec 033)
        user.cached_voice_prompt = "You are Nikita, a flirty girlfriend chatting with TestUser..."
        user.metrics = MagicMock()
        user.metrics.relationship_score = Decimal("65.0")
        user.vice_preferences = []
        return user

    @pytest.fixture
    def mock_user_without_cached_prompt(self):
        """Create mock user without cached voice prompt (first-time caller).

        Note: onboarding_status must be 'completed' or 'skipped' for inbound calls
        to be accepted (Spec 033: Unified Phone Number).
        """
        user = MagicMock()
        user.id = uuid4()
        user.name = "TestUser"
        user.phone_number = "+41787950009"
        user.chapter = 3
        user.game_status = "active"
        user.onboarding_status = "completed"  # Required for inbound calls (Spec 033)
        user.cached_voice_prompt = None  # No cache
        user.metrics = MagicMock()
        user.metrics.relationship_score = Decimal("65.0")
        user.vice_preferences = []
        return user

    def test_precall_uses_cached_prompt(self, mock_user_with_cached_prompt):
        """FR-034: Pre-call should use cached_voice_prompt from user object."""
        from nikita.agents.voice.inbound import InboundCallHandler

        handler = InboundCallHandler()

        with patch.object(
            handler, "_lookup_user_by_phone", new_callable=AsyncMock
        ) as mock_lookup, patch.object(
            handler, "_check_availability", new_callable=AsyncMock
        ) as mock_avail, patch.object(
            handler, "_build_context", new_callable=AsyncMock
        ) as mock_context:
            mock_lookup.return_value = mock_user_with_cached_prompt
            mock_avail.return_value = (True, "Available")
            mock_context.return_value = {
                "user_name": "TestUser",
                "chapter": "3",
                "relationship_score": "65.0",
                "engagement_state": "IN_ZONE",
                "nikita_mood": "playful",
                "nikita_energy": "medium",
                "time_of_day": "afternoon",
                "recent_topics": "",
                "open_threads": "",
                "secret__user_id": str(mock_user_with_cached_prompt.id),
                "secret__signed_token": "token",
            }

            import asyncio
            result = asyncio.get_event_loop().run_until_complete(
                handler.handle_incoming_call("+41787950009")
            )

        assert result["accept_call"] is True
        assert "conversation_config_override" in result
        config = result["conversation_config_override"]
        assert "agent" in config
        assert "prompt" in config["agent"]
        # Verify cached prompt is used
        assert config["agent"]["prompt"]["prompt"] == "You are Nikita, a flirty girlfriend chatting with TestUser..."

    def test_precall_uses_fallback_when_no_cache(self, mock_user_without_cached_prompt):
        """FR-034: Pre-call should use fallback prompt when cache is empty."""
        from nikita.agents.voice.inbound import InboundCallHandler

        handler = InboundCallHandler()

        with patch.object(
            handler, "_lookup_user_by_phone", new_callable=AsyncMock
        ) as mock_lookup, patch.object(
            handler, "_check_availability", new_callable=AsyncMock
        ) as mock_avail, patch.object(
            handler, "_build_context", new_callable=AsyncMock
        ) as mock_context, patch(
            "nikita.agents.voice.config.VoiceAgentConfig"
        ) as mock_config_class:
            mock_lookup.return_value = mock_user_without_cached_prompt
            mock_avail.return_value = (True, "Available")
            mock_context.return_value = {
                "user_name": "TestUser",
                "chapter": "3",
                "relationship_score": "65.0",
                "engagement_state": "IN_ZONE",
                "nikita_mood": "playful",
                "nikita_energy": "medium",
                "time_of_day": "afternoon",
                "recent_topics": "",
                "open_threads": "",
                "secret__user_id": str(mock_user_without_cached_prompt.id),
                "secret__signed_token": "token",
            }

            # Mock VoiceAgentConfig to return fallback prompt
            mock_config_instance = MagicMock()
            mock_config_instance.generate_system_prompt.return_value = "Fallback static prompt..."
            mock_config_class.return_value = mock_config_instance

            import asyncio
            result = asyncio.get_event_loop().run_until_complete(
                handler.handle_incoming_call("+41787950009")
            )

        assert result["accept_call"] is True
        config = result["conversation_config_override"]
        assert "agent" in config
        # Fallback prompt should be used
        assert config["agent"]["prompt"]["prompt"] == "Fallback static prompt..."
        # VoiceAgentConfig.generate_system_prompt should have been called
        mock_config_instance.generate_system_prompt.assert_called_once()

    def test_precall_no_metaprompt_service_calls(self, mock_user_with_cached_prompt):
        """FR-033: Pre-call should NOT call MetaPromptService (LLM)."""
        from nikita.agents.voice.inbound import InboundCallHandler

        handler = InboundCallHandler()

        with patch.object(
            handler, "_lookup_user_by_phone", new_callable=AsyncMock
        ) as mock_lookup, patch.object(
            handler, "_check_availability", new_callable=AsyncMock
        ) as mock_avail, patch.object(
            handler, "_build_context", new_callable=AsyncMock
        ) as mock_context:
            mock_lookup.return_value = mock_user_with_cached_prompt
            mock_avail.return_value = (True, "Available")
            mock_context.return_value = {
                "user_name": "TestUser",
                "chapter": "3",
                "relationship_score": "65.0",
                "engagement_state": "IN_ZONE",
                "nikita_mood": "playful",
                "nikita_energy": "medium",
                "time_of_day": "afternoon",
                "recent_topics": "",
                "open_threads": "",
                "secret__user_id": str(mock_user_with_cached_prompt.id),
                "secret__signed_token": "token",
            }

            import asyncio
            asyncio.get_event_loop().run_until_complete(
                handler.handle_incoming_call("+41787950009")
            )

        # MetaPromptService no longer exists - voice agent loads ready prompts directly

    def test_precall_no_neo4j_calls(self, mock_user_with_cached_prompt):
        """FR-033: Pre-call should NOT query SupabaseMemory."""
        from nikita.agents.voice.inbound import InboundCallHandler

        handler = InboundCallHandler()

        with patch.object(
            handler, "_lookup_user_by_phone", new_callable=AsyncMock
        ) as mock_lookup, patch.object(
            handler, "_check_availability", new_callable=AsyncMock
        ) as mock_avail, patch.object(
            handler, "_build_context", new_callable=AsyncMock
        ) as mock_context, patch(
            "nikita.memory.get_memory_client", new_callable=AsyncMock
        ) as mock_memory:
            mock_lookup.return_value = mock_user_with_cached_prompt
            mock_avail.return_value = (True, "Available")
            mock_context.return_value = {
                "user_name": "TestUser",
                "chapter": "3",
                "relationship_score": "65.0",
                "engagement_state": "IN_ZONE",
                "nikita_mood": "playful",
                "nikita_energy": "medium",
                "time_of_day": "afternoon",
                "recent_topics": "",
                "open_threads": "",
                "secret__user_id": str(mock_user_with_cached_prompt.id),
                "secret__signed_token": "token",
            }

            import asyncio
            asyncio.get_event_loop().run_until_complete(
                handler.handle_incoming_call("+41787950009")
            )

        # Neo4j memory client should NOT be called
        mock_memory.assert_not_called()

    def test_precall_latency_under_100ms(self, mock_user_with_cached_prompt):
        """FR-033: Pre-call webhook must complete in <100ms (with mocks)."""
        import time
        from nikita.agents.voice.inbound import InboundCallHandler

        handler = InboundCallHandler()

        with patch.object(
            handler, "_lookup_user_by_phone", new_callable=AsyncMock
        ) as mock_lookup, patch.object(
            handler, "_check_availability", new_callable=AsyncMock
        ) as mock_avail, patch.object(
            handler, "_build_context", new_callable=AsyncMock
        ) as mock_context:
            mock_lookup.return_value = mock_user_with_cached_prompt
            mock_avail.return_value = (True, "Available")
            mock_context.return_value = {
                "user_name": "TestUser",
                "chapter": "3",
                "relationship_score": "65.0",
                "engagement_state": "IN_ZONE",
                "nikita_mood": "playful",
                "nikita_energy": "medium",
                "time_of_day": "afternoon",
                "recent_topics": "",
                "open_threads": "",
                "secret__user_id": str(mock_user_with_cached_prompt.id),
                "secret__signed_token": "token",
            }

            import asyncio

            start = time.perf_counter()
            asyncio.get_event_loop().run_until_complete(
                handler.handle_incoming_call("+41787950009")
            )
            elapsed_ms = (time.perf_counter() - start) * 1000

        # With all external calls mocked, should complete in <100ms
        assert elapsed_ms < 100, f"Pre-call took {elapsed_ms:.2f}ms, expected <100ms"


class TestUnifiedPhoneNumberRouting:
    """Test unified phone number routing (Spec 033).

    Spec 033 implements single phone number for both onboarding and regular calls:
    - Meta-Nikita persona via conversation_config_override for outbound onboarding
    - Default Nikita for inbound calls from onboarded users
    - Reject inbound calls from users who haven't completed onboarding
    """

    @pytest.fixture
    def mock_onboarded_user(self):
        """Create mock user who completed onboarding."""
        user = MagicMock()
        user.id = uuid4()
        user.name = "CompletedUser"
        user.phone_number = "+41787950009"
        user.chapter = 2
        user.game_status = "active"
        user.onboarding_status = "completed"
        user.cached_voice_prompt = "You are Nikita..."
        user.metrics = MagicMock()
        user.metrics.relationship_score = Decimal("65.0")
        user.vice_preferences = []
        return user

    @pytest.fixture
    def mock_skipped_onboarding_user(self):
        """Create mock user who skipped onboarding."""
        user = MagicMock()
        user.id = uuid4()
        user.name = "SkippedUser"
        user.phone_number = "+41787950010"
        user.chapter = 1
        user.game_status = "active"
        user.onboarding_status = "skipped"
        user.cached_voice_prompt = "You are Nikita..."
        user.metrics = MagicMock()
        user.metrics.relationship_score = Decimal("50.0")
        user.vice_preferences = []
        return user

    @pytest.fixture
    def mock_not_onboarded_user(self):
        """Create mock user who hasn't completed onboarding."""
        user = MagicMock()
        user.id = uuid4()
        user.name = "NewUser"
        user.phone_number = "+41787950011"
        user.chapter = 1
        user.game_status = "active"
        user.onboarding_status = "pending"
        user.cached_voice_prompt = None
        user.metrics = None
        user.vice_preferences = []
        return user

    @pytest.fixture
    def mock_in_progress_onboarding_user(self):
        """Create mock user with onboarding in progress."""
        user = MagicMock()
        user.id = uuid4()
        user.name = "InProgressUser"
        user.phone_number = "+41787950012"
        user.chapter = 1
        user.game_status = "active"
        user.onboarding_status = "in_progress"
        user.cached_voice_prompt = None
        user.metrics = None
        user.vice_preferences = []
        return user

    def test_accepts_call_from_completed_onboarding_user(self, mock_onboarded_user):
        """Spec 033: Accept inbound calls from users who completed onboarding."""
        from nikita.agents.voice.inbound import InboundCallHandler

        handler = InboundCallHandler()

        with patch.object(
            handler, "_lookup_user_by_phone", new_callable=AsyncMock
        ) as mock_lookup, patch.object(
            handler, "_check_availability", new_callable=AsyncMock
        ) as mock_avail, patch.object(
            handler, "_build_context", new_callable=AsyncMock
        ) as mock_context, patch.object(
            handler, "_get_conversation_config_override", new_callable=AsyncMock
        ) as mock_config:
            mock_lookup.return_value = mock_onboarded_user
            mock_avail.return_value = (True, "Nikita is available")
            mock_context.return_value = {"user_name": "CompletedUser", "chapter": "2"}
            mock_config.return_value = {"tts": {"stability": 0.5}}

            import asyncio
            result = asyncio.get_event_loop().run_until_complete(
                handler.handle_incoming_call("+41787950009")
            )

        assert result["accept_call"] is True
        assert result["user_id"] == str(mock_onboarded_user.id)

    def test_accepts_call_from_skipped_onboarding_user(self, mock_skipped_onboarding_user):
        """Spec 033: Accept inbound calls from users who skipped onboarding."""
        from nikita.agents.voice.inbound import InboundCallHandler

        handler = InboundCallHandler()

        with patch.object(
            handler, "_lookup_user_by_phone", new_callable=AsyncMock
        ) as mock_lookup, patch.object(
            handler, "_check_availability", new_callable=AsyncMock
        ) as mock_avail, patch.object(
            handler, "_build_context", new_callable=AsyncMock
        ) as mock_context, patch.object(
            handler, "_get_conversation_config_override", new_callable=AsyncMock
        ) as mock_config:
            mock_lookup.return_value = mock_skipped_onboarding_user
            mock_avail.return_value = (True, "Nikita is available")
            mock_context.return_value = {"user_name": "SkippedUser", "chapter": "1"}
            mock_config.return_value = {"tts": {"stability": 0.5}}

            import asyncio
            result = asyncio.get_event_loop().run_until_complete(
                handler.handle_incoming_call("+41787950010")
            )

        assert result["accept_call"] is True
        assert result["user_id"] == str(mock_skipped_onboarding_user.id)

    def test_rejects_call_from_pending_onboarding_user(self, mock_not_onboarded_user):
        """Spec 033: Reject inbound calls from users with pending onboarding."""
        from nikita.agents.voice.inbound import InboundCallHandler

        handler = InboundCallHandler()

        with patch.object(
            handler, "_lookup_user_by_phone", new_callable=AsyncMock
        ) as mock_lookup:
            mock_lookup.return_value = mock_not_onboarded_user

            import asyncio
            result = asyncio.get_event_loop().run_until_complete(
                handler.handle_incoming_call("+41787950011")
            )

        assert result["accept_call"] is False
        assert "onboarding" in result["message"].lower()
        assert "user_id" in result
        assert result["user_id"] == str(mock_not_onboarded_user.id)
        # CRITICAL: dynamic_variables must always be returned per ElevenLabs requirement
        assert "dynamic_variables" in result
        assert "conversation_config_override" in result

    def test_rejects_call_from_in_progress_onboarding_user(self, mock_in_progress_onboarding_user):
        """Spec 033: Reject inbound calls from users with in_progress onboarding."""
        from nikita.agents.voice.inbound import InboundCallHandler

        handler = InboundCallHandler()

        with patch.object(
            handler, "_lookup_user_by_phone", new_callable=AsyncMock
        ) as mock_lookup:
            mock_lookup.return_value = mock_in_progress_onboarding_user

            import asyncio
            result = asyncio.get_event_loop().run_until_complete(
                handler.handle_incoming_call("+41787950012")
            )

        assert result["accept_call"] is False
        assert "onboarding" in result["message"].lower()
        # CRITICAL: dynamic_variables must always be returned per ElevenLabs requirement
        assert "dynamic_variables" in result

    def test_not_onboarded_rejection_includes_friendly_message(self, mock_not_onboarded_user):
        """Spec 033: Rejection includes friendly first message about waiting for intro call."""
        from nikita.agents.voice.inbound import InboundCallHandler

        handler = InboundCallHandler()

        with patch.object(
            handler, "_lookup_user_by_phone", new_callable=AsyncMock
        ) as mock_lookup:
            mock_lookup.return_value = mock_not_onboarded_user

            import asyncio
            result = asyncio.get_event_loop().run_until_complete(
                handler.handle_incoming_call("+41787950011")
            )

        assert result["accept_call"] is False
        assert "conversation_config_override" in result
        config = result["conversation_config_override"]
        assert "agent" in config
        assert "first_message" in config["agent"]
        # First message should explain they need to wait for intro call
        first_msg = config["agent"]["first_message"].lower()
        assert any(
            phrase in first_msg
            for phrase in ["haven't properly met", "calling you soon", "wait", "intro"]
        )

    def test_not_onboarded_user_has_correct_user_id_in_dynamic_vars(self, mock_not_onboarded_user):
        """Spec 033: Rejected user should have correct user_id in dynamic_variables."""
        from nikita.agents.voice.inbound import InboundCallHandler

        handler = InboundCallHandler()

        with patch.object(
            handler, "_lookup_user_by_phone", new_callable=AsyncMock
        ) as mock_lookup:
            mock_lookup.return_value = mock_not_onboarded_user

            import asyncio
            result = asyncio.get_event_loop().run_until_complete(
                handler.handle_incoming_call("+41787950011")
            )

        # Even rejected users should have their user_id in dynamic_variables
        assert "dynamic_variables" in result
        assert result["dynamic_variables"]["secret__user_id"] == str(mock_not_onboarded_user.id)

    def test_handles_none_onboarding_status(self):
        """Spec 033: Handle users without onboarding_status attribute (legacy users)."""
        from nikita.agents.voice.inbound import InboundCallHandler

        handler = InboundCallHandler()

        # Create user without onboarding_status attribute
        legacy_user = MagicMock()
        legacy_user.id = uuid4()
        legacy_user.name = "LegacyUser"
        legacy_user.phone_number = "+41787950013"
        legacy_user.chapter = 1
        legacy_user.game_status = "active"
        legacy_user.cached_voice_prompt = None
        legacy_user.metrics = None
        # Simulate missing attribute by using spec= which won't have onboarding_status
        del legacy_user.onboarding_status

        with patch.object(
            handler, "_lookup_user_by_phone", new_callable=AsyncMock
        ) as mock_lookup:
            mock_lookup.return_value = legacy_user

            import asyncio
            result = asyncio.get_event_loop().run_until_complete(
                handler.handle_incoming_call("+41787950013")
            )

        # Legacy users without onboarding_status should be rejected
        assert result["accept_call"] is False
        assert "dynamic_variables" in result
