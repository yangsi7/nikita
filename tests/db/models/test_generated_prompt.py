"""Tests for GeneratedPrompt model (Spec 035 T4.1)."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from nikita.db.models.generated_prompt import GeneratedPrompt


class TestGeneratedPromptPlatformField:
    """Tests for platform field (T4.1)."""

    def test_generated_prompt_has_platform_field(self):
        """Test that GeneratedPrompt has platform field (AC-T4.1.1)."""
        # Verify field exists in model columns
        assert hasattr(GeneratedPrompt, "platform")

        # Verify it's a mapped column
        column = GeneratedPrompt.__table__.columns.get("platform")
        assert column is not None
        assert str(column.type) == "VARCHAR(10)"

    def test_generated_prompt_platform_default(self):
        """Test that platform field has default 'text' (AC-T4.1.2)."""
        # Check the column default is set
        column = GeneratedPrompt.__table__.columns.get("platform")
        assert column is not None
        # The default is set on the column
        assert column.default is not None
        assert column.default.arg == "text"

    def test_generated_prompt_platform_not_nullable(self):
        """Test that platform field is not nullable (AC-T4.1.3)."""
        column = GeneratedPrompt.__table__.columns.get("platform")
        assert column is not None
        assert column.nullable is False

    def test_generated_prompt_platform_voice(self):
        """Test that platform can be set to 'voice'."""
        prompt = GeneratedPrompt(
            id=uuid4(),
            user_id=uuid4(),
            prompt_content="Voice prompt",
            token_count=150,
            generation_time_ms=75.0,
            meta_prompt_template="system_prompt",
            platform="voice",
            created_at=datetime.now(UTC),
        )

        assert prompt.platform == "voice"
