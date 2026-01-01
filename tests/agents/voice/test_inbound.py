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
        """Create mock user with phone number."""
        user = MagicMock()
        user.id = uuid4()
        user.phone_number = "+41787950009"
        user.chapter = 3
        user.game_status = "active"
        user.telegram_id = 12345678
        user.metrics = MagicMock()
        user.metrics.relationship_score = Decimal("65.0")
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
            handler, "_get_tts_config"
        ) as mock_tts:
            mock_lookup.return_value = mock_user
            mock_avail.return_value = (True, "Nikita is available")
            mock_context.return_value = {"user_name": "TestUser"}
            mock_tts.return_value = {"tts": {"stability": 0.5}}

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
            handler, "_get_tts_config"
        ) as mock_tts:
            mock_lookup.return_value = mock_user
            mock_avail.return_value = (True, "Available")
            mock_context.return_value = {"user_name": "TestUser"}
            mock_tts.return_value = {"tts": {"stability": 0.5}}

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
            handler, "_get_tts_config"
        ) as mock_tts:
            mock_lookup.return_value = mock_user
            mock_avail.return_value = (True, "Available")
            mock_context.return_value = {"user_name": "TestUser"}
            mock_tts.return_value = {"tts": {"stability": 0.5}}

            import asyncio
            asyncio.get_event_loop().run_until_complete(
                handler.handle_incoming_call("+41787950009")
            )

        mock_avail.assert_called_once_with(mock_user)

    def test_rejects_unavailable_call(self, mock_user):
        """AC-T076.4: Returns accept_call=False with message if unavailable."""
        from nikita.agents.voice.inbound import InboundCallHandler

        handler = InboundCallHandler()

        with patch.object(
            handler, "_lookup_user_by_phone", new_callable=AsyncMock
        ) as mock_lookup, patch.object(
            handler, "_check_availability", new_callable=AsyncMock
        ) as mock_avail:
            mock_lookup.return_value = mock_user
            mock_avail.return_value = (False, "Nikita is busy right now")

            import asyncio
            result = asyncio.get_event_loop().run_until_complete(
                handler.handle_incoming_call("+41787950009")
            )

        assert result["accept_call"] is False
        assert "Nikita is busy" in result["message"]

    def test_rejects_unknown_caller(self):
        """AC-T078.3: Returns accept_call=False for unknown callers."""
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
        """Create mock user."""
        user = MagicMock()
        user.id = uuid4()
        user.name = "TestUser"
        user.phone_number = "+41787950009"
        user.chapter = 3
        user.game_status = "active"
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
            handler, "_get_tts_config"
        ) as mock_tts:
            mock_lookup.return_value = mock_user
            mock_avail.return_value = (True, "Available")
            mock_context.return_value = {
                "user_name": "TestUser",
                "chapter": 3,
            }
            mock_tts.return_value = {"tts": {"stability": 0.5}}

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
            handler, "_get_tts_config"
        ) as mock_tts:
            mock_lookup.return_value = mock_user
            mock_avail.return_value = (True, "Available")
            mock_context.return_value = {"user_name": "TestUser", "chapter": 3}
            mock_tts.return_value = {"tts": {"stability": 0.5, "similarity_boost": 0.75}}

            import asyncio
            result = asyncio.get_event_loop().run_until_complete(
                handler.handle_incoming_call("+41787950009")
            )

        # Should include TTS settings based on chapter
        assert result["accept_call"] is True
        assert "conversation_config_override" in result
        config = result["conversation_config_override"]
        assert "tts" in config
