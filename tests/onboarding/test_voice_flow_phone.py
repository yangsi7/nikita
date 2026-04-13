"""Tests for voice_flow.py phone refactoring (Spec 212 PR B, T013).

Verifies:
- normalize_phone delegates to shared validation module (raises ValueError on bad input)
- _save_phone_number DB failure propagates instead of being swallowed

Failing until T018 (voice_flow refactor) is committed.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError


class TestNormalizePhoneRefactored:
    """normalize_phone must delegate to the shared validate_phone module."""

    def test_normalize_phone_raises_on_invalid(self):
        """normalize_phone('abc') must raise ValueError (delegates to validate_phone).

        Before refactor: US-biased fallback returned a mangled string.
        After refactor: validate_phone raises ValueError for non-numeric junk.
        """
        from nikita.onboarding.voice_flow import VoiceOnboardingFlow

        flow = VoiceOnboardingFlow()

        with pytest.raises(ValueError):
            flow.normalize_phone("abc")

    def test_normalize_phone_valid_swiss_number(self):
        """normalize_phone passes valid Swiss E.164 through unchanged."""
        from nikita.onboarding.voice_flow import VoiceOnboardingFlow

        flow = VoiceOnboardingFlow()
        result = flow.normalize_phone("+41791234567")
        assert result == "+41791234567"


class TestSavePhoneNumberPropagatesErrors:
    """_save_phone_number must NOT swallow DB exceptions."""

    @pytest.mark.asyncio
    async def test_save_phone_number_propagates_integrity_error(self):
        """_save_phone_number propagates IntegrityError — no silent except.

        Before refactor: bare `except Exception as e: logger.error(...)` swallowed
        the error, making duplicate-phone inserts invisible to the caller.
        After refactor: the exception propagates to the caller for proper handling.
        """
        from nikita.onboarding.voice_flow import VoiceOnboardingFlow

        user_id = uuid4()

        # Build a mock session where flush raises IntegrityError
        mock_session = AsyncMock()
        mock_user = MagicMock()
        mock_user.phone = None

        # Simulate repo.get returning the user, then flush raising
        with patch(
            "nikita.db.repositories.user_repository.UserRepository.get",
            new_callable=AsyncMock,
            return_value=mock_user,
        ), patch.object(
            mock_session,
            "flush",
            new_callable=AsyncMock,
            side_effect=IntegrityError("unique violation", {}, Exception()),
        ):
            flow = VoiceOnboardingFlow(session=mock_session)

            # Must propagate — not swallow
            with pytest.raises(IntegrityError):
                await flow._save_phone_number(user_id, "+41791234567")

    @pytest.mark.asyncio
    async def test_save_phone_number_no_session_returns_without_error(self):
        """_save_phone_number with None session returns silently (no-op path)."""
        from nikita.onboarding.voice_flow import VoiceOnboardingFlow

        flow = VoiceOnboardingFlow(session=None)
        user_id = uuid4()

        # Should not raise — the no-session guard should return early
        await flow._save_phone_number(user_id, "+41791234567")
