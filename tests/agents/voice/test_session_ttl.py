"""Tests for session TTL eviction (REL-001-004).

Tests:
- VoiceService._sessions evicts stale entries
- VoiceSessionManager._sessions evicts stale entries
- OnboardingServerToolHandler._profiles evicts stale entries
"""

import time
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest


class TestVoiceServiceSessionTTL:
    """Test VoiceService._sessions TTL eviction."""

    def test_evicts_stale_sessions(self):
        """Sessions older than TTL are removed."""
        from nikita.agents.voice.service import SESSION_TTL_SECONDS, VoiceService

        settings = MagicMock()
        service = VoiceService(settings=settings)

        # Add a session with old timestamp
        service._sessions["old_session"] = {
            "user_id": "abc",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "_created_ts": time.time() - SESSION_TTL_SECONDS - 100,
        }
        # Add a fresh session
        service._sessions["fresh_session"] = {
            "user_id": "def",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "_created_ts": time.time(),
        }

        service._evict_stale_sessions()

        assert "old_session" not in service._sessions
        assert "fresh_session" in service._sessions

    def test_keeps_all_sessions_when_fresh(self):
        """No sessions evicted when all are within TTL."""
        from nikita.agents.voice.service import VoiceService

        settings = MagicMock()
        service = VoiceService(settings=settings)

        service._sessions["s1"] = {"_created_ts": time.time()}
        service._sessions["s2"] = {"_created_ts": time.time()}

        service._evict_stale_sessions()

        assert len(service._sessions) == 2


class TestVoiceSessionManagerTTL:
    """Test VoiceSessionManager._sessions TTL eviction."""

    def test_evicts_stale_sessions(self):
        """Sessions older than TTL are removed."""
        from nikita.agents.voice.inbound import (
            SESSION_TTL_SECONDS,
            VoiceSessionManager,
        )

        mgr = VoiceSessionManager()

        # Add old session
        old_id = uuid4()
        mgr._sessions["old"] = {
            "session_id": "old",
            "user_id": old_id,
            "state": "ACTIVE",
            "created_at": datetime.now(timezone.utc),
            "_created_ts": time.time() - SESSION_TTL_SECONDS - 100,
        }
        # Add fresh session
        fresh_id = uuid4()
        mgr._sessions["fresh"] = {
            "session_id": "fresh",
            "user_id": fresh_id,
            "state": "ACTIVE",
            "created_at": datetime.now(timezone.utc),
            "_created_ts": time.time(),
        }

        mgr._evict_stale_sessions()

        assert "old" not in mgr._sessions
        assert "fresh" in mgr._sessions


class TestOnboardingProfileTTL:
    """Test OnboardingServerToolHandler._profiles TTL eviction."""

    def test_evicts_stale_profiles(self):
        """Profiles older than TTL are removed."""
        from nikita.onboarding.server_tools import (
            PROFILE_TTL_SECONDS,
            OnboardingServerToolHandler,
        )

        handler = OnboardingServerToolHandler()

        # Add old profile entry
        handler._profiles["old_user"] = MagicMock()
        handler._profile_timestamps["old_user"] = time.time() - PROFILE_TTL_SECONDS - 100

        # Add fresh profile entry
        handler._profiles["fresh_user"] = MagicMock()
        handler._profile_timestamps["fresh_user"] = time.time()

        handler._evict_stale_profiles()

        assert "old_user" not in handler._profiles
        assert "old_user" not in handler._profile_timestamps
        assert "fresh_user" in handler._profiles
