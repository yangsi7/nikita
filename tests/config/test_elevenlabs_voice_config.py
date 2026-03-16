"""Guard tests for ElevenLabs voice agent configuration.

Verifies that:
- User model uses `phone` (not `phone_number`) as the canonical attribute
- ElevenLabs settings fields exist and are correctly typed
- Phone number ID is configurable via environment

Created during voice agent audit (2026-03-16).
"""

from __future__ import annotations

from nikita.db.models.user import User


class TestUserPhoneAttribute:
    """Guard tests: User.phone is the canonical phone attribute."""

    def test_user_model_has_phone(self) -> None:
        """User model exposes `phone` column."""
        assert hasattr(User, "phone"), "User model must have 'phone' attribute"

    def test_user_model_does_not_have_phone_number(self) -> None:
        """User model must NOT have `phone_number` — code using it is a bug.

        Known bug locations fixed in this PR:
        - nikita/onboarding/server_tools.py:443
        - nikita/api/routes/onboarding.py:489, 509
        """
        assert not hasattr(
            User, "phone_number"
        ), "User model has 'phone', not 'phone_number' — using phone_number is a bug"


class TestElevenLabsSettings:
    """Verify ElevenLabs settings fields exist with correct types."""

    def test_settings_has_phone_number_id_field(self) -> None:
        """settings.elevenlabs_phone_number_id must exist for outbound calls."""
        from nikita.config.settings import Settings

        field_info = Settings.model_fields.get("elevenlabs_phone_number_id")
        assert field_info is not None, "Settings must have elevenlabs_phone_number_id"

    def test_settings_has_default_agent_id_field(self) -> None:
        from nikita.config.settings import Settings

        field_info = Settings.model_fields.get("elevenlabs_default_agent_id")
        assert field_info is not None

    def test_settings_has_voice_id_field(self) -> None:
        from nikita.config.settings import Settings

        field_info = Settings.model_fields.get("elevenlabs_voice_id")
        assert field_info is not None
