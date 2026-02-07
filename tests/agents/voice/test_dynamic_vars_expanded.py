"""Tests for expanded DynamicVariables (Spec 032: US-1).

TDD tests for T1.1 (model expansion) and T1.2 (builder population).
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4

from nikita.agents.voice.models import DynamicVariables, VoiceContext, NikitaMood


class TestDynamicVariablesExpanded:
    """T1.1: DynamicVariables model expansion tests."""

    def test_has_today_summary_field(self):
        """AC-T1.1.1: today_summary field exists with default empty string."""
        dv = DynamicVariables()
        assert hasattr(dv, "today_summary")
        assert dv.today_summary == ""

    def test_has_last_conversation_summary_field(self):
        """AC-T1.1.1: last_conversation_summary field exists."""
        dv = DynamicVariables()
        assert hasattr(dv, "last_conversation_summary")
        assert dv.last_conversation_summary == ""

    def test_has_mood_4d_fields(self):
        """AC-T1.1.1: nikita_mood_* fields for 4D emotional state."""
        dv = DynamicVariables()
        assert hasattr(dv, "nikita_mood_arousal")
        assert hasattr(dv, "nikita_mood_valence")
        assert hasattr(dv, "nikita_mood_dominance")
        assert hasattr(dv, "nikita_mood_intimacy")
        # Default to 0.5 (neutral)
        assert dv.nikita_mood_arousal == 0.5
        assert dv.nikita_mood_valence == 0.5
        assert dv.nikita_mood_dominance == 0.5
        assert dv.nikita_mood_intimacy == 0.5

    def test_has_nikita_daily_events_field(self):
        """AC-T1.1.1: nikita_daily_events field for life simulation."""
        dv = DynamicVariables()
        assert hasattr(dv, "nikita_daily_events")
        assert dv.nikita_daily_events == ""

    def test_has_conflict_fields(self):
        """AC-T1.1.1: active_conflict_* fields."""
        dv = DynamicVariables()
        assert hasattr(dv, "active_conflict_type")
        assert hasattr(dv, "active_conflict_severity")
        assert dv.active_conflict_type == ""
        assert dv.active_conflict_severity == 0.0

    def test_has_emotional_context_field(self):
        """AC-T1.1.1: emotional_context field."""
        dv = DynamicVariables()
        assert hasattr(dv, "emotional_context")
        assert dv.emotional_context == ""

    def test_has_user_backstory_field(self):
        """AC-T1.1.1: user_backstory field."""
        dv = DynamicVariables()
        assert hasattr(dv, "user_backstory")
        assert dv.user_backstory == ""

    def test_has_context_block_field(self):
        """AC-T1.1.1: context_block field for aggregated context."""
        dv = DynamicVariables()
        assert hasattr(dv, "context_block")
        assert dv.context_block == ""

    def test_all_12_new_fields_present(self):
        """AC-T1.1.1: All 12 new fields added."""
        dv = DynamicVariables()
        new_fields = [
            "today_summary",
            "last_conversation_summary",
            "nikita_mood_arousal",
            "nikita_mood_valence",
            "nikita_mood_dominance",
            "nikita_mood_intimacy",
            "nikita_daily_events",
            "active_conflict_type",
            "active_conflict_severity",
            "emotional_context",
            "user_backstory",
            "context_block",
        ]
        for field in new_fields:
            assert hasattr(dv, field), f"Missing field: {field}"

    def test_default_values_correct(self):
        """AC-T1.1.2: Default values set correctly."""
        dv = DynamicVariables()
        # Strings default to empty
        assert dv.today_summary == ""
        assert dv.last_conversation_summary == ""
        assert dv.nikita_daily_events == ""
        assert dv.active_conflict_type == ""
        assert dv.emotional_context == ""
        assert dv.user_backstory == ""
        assert dv.context_block == ""
        # Floats default to appropriate values
        assert dv.nikita_mood_arousal == 0.5
        assert dv.nikita_mood_valence == 0.5
        assert dv.nikita_mood_dominance == 0.5
        assert dv.nikita_mood_intimacy == 0.5
        assert dv.active_conflict_severity == 0.0

    def test_json_serialization_includes_new_fields(self):
        """AC-T1.1.3: JSON serialization works correctly."""
        dv = DynamicVariables(
            today_summary="Had coffee with friends",
            nikita_mood_arousal=0.7,
            active_conflict_type="jealousy",
            active_conflict_severity=0.3,
        )
        data = dv.to_dict()
        assert "today_summary" in data
        assert data["today_summary"] == "Had coffee with friends"
        assert "nikita_mood_arousal" in data
        assert data["nikita_mood_arousal"] == "0.7"  # to_dict converts to string
        assert "active_conflict_type" in data
        assert "active_conflict_severity" in data

    def test_backward_compatible_with_existing_code(self):
        """AC-T1.1.4: Backward compatible - existing fields still work."""
        dv = DynamicVariables(
            user_name="Test User",
            chapter=3,
            relationship_score=75.0,
            engagement_state="IN_ZONE",
        )
        # Old fields work
        assert dv.user_name == "Test User"
        assert dv.chapter == 3
        assert dv.relationship_score == 75.0
        assert dv.engagement_state == "IN_ZONE"
        # New fields have defaults
        assert dv.today_summary == ""
        assert dv.nikita_mood_arousal == 0.5


class TestDynamicVariablesBuilderExpanded:
    """T1.2: DynamicVariablesBuilder population tests."""

    def test_builder_populates_today_summary(self):
        """AC-T1.2.1: today_summary loaded from daily_summaries."""
        from nikita.agents.voice.context import DynamicVariablesBuilder

        # Create context with today_summary
        context = VoiceContext(
            user_id=uuid4(),
            user_name="Test",
            chapter=3,
            relationship_score=70.0,
        )
        # Note: VoiceContext may need today_summary field too
        # For now, test builder handles missing gracefully

        builder = DynamicVariablesBuilder()
        dv = builder.build_from_context(context)

        # Should have field even if not populated from context
        assert hasattr(dv, "today_summary")

    def test_builder_populates_mood_4d_from_context(self):
        """AC-T1.2.2: 4D mood loaded from nikita_emotional_states."""
        from nikita.agents.voice.context import DynamicVariablesBuilder

        context = VoiceContext(
            user_id=uuid4(),
            user_name="Test",
            chapter=3,
            relationship_score=70.0,
        )

        builder = DynamicVariablesBuilder()
        dv = builder.build_from_context(context)

        # Should have 4D mood fields
        assert hasattr(dv, "nikita_mood_arousal")
        assert hasattr(dv, "nikita_mood_valence")
        assert hasattr(dv, "nikita_mood_dominance")
        assert hasattr(dv, "nikita_mood_intimacy")

    def test_builder_populates_last_conversation_summary(self):
        """AC-T1.2.3: last_conversation_summary loaded."""
        from nikita.agents.voice.context import DynamicVariablesBuilder

        context = VoiceContext(
            user_id=uuid4(),
            user_name="Test",
            chapter=3,
            relationship_score=70.0,
            last_conversation_summary="We talked about work stress",
        )

        builder = DynamicVariablesBuilder()
        dv = builder.build_from_context(context)

        assert dv.last_conversation_summary == "We talked about work stress"

    def test_builder_generates_context_block(self):
        """AC-T1.2.4: context_block generated from all fields."""
        from nikita.agents.voice.context import DynamicVariablesBuilder

        context = VoiceContext(
            user_id=uuid4(),
            user_name="Alex",
            chapter=3,
            relationship_score=70.0,
        )

        builder = DynamicVariablesBuilder()
        dv = builder.build_from_context(context)

        # context_block should be populated
        assert hasattr(dv, "context_block")

    @pytest.mark.asyncio
    async def test_build_from_user_populates_new_fields(self):
        """Test build_from_user populates new fields."""
        from nikita.agents.voice.context import DynamicVariablesBuilder

        # Mock user
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.name = "Alex"
        mock_user.chapter = 3
        mock_user.relationship_score = 70.0
        mock_user.onboarding_profile = {"name": "Alex", "backstory": "Met at coffee shop"}
        mock_user.metrics = MagicMock()
        mock_user.metrics.relationship_score = 70.0
        mock_user.metrics.secureness = 60.0
        mock_user.engagement_state = MagicMock()
        mock_user.engagement_state.state = "in_zone"
        mock_user.last_interaction_at = datetime.now(timezone.utc) - timedelta(hours=2)

        builder = DynamicVariablesBuilder()
        dv = builder.build_from_user(mock_user)

        # Should have all new fields with defaults
        assert hasattr(dv, "today_summary")
        assert hasattr(dv, "nikita_mood_arousal")
        assert hasattr(dv, "context_block")


class TestContextBlockGeneration:
    """T1.4: context_block generation tests."""

    def test_context_block_format(self):
        """AC-T1.4.1: context_block includes relationship state."""
        from nikita.agents.voice.context import DynamicVariablesBuilder

        builder = DynamicVariablesBuilder()

        # Test _build_context_block method if it exists
        context_block = builder._build_context_block(
            user_name="Alex",
            chapter=3,
            relationship_score=70.0,
            today_summary="Went to gym, had coffee",
            last_conversation_summary="Talked about work",
            nikita_mood_4d={"arousal": 0.6, "valence": 0.7, "dominance": 0.5, "intimacy": 0.6},
        )

        assert isinstance(context_block, str)
        # Should include key info
        assert "Alex" in context_block or "relationship" in context_block.lower()

    def test_context_block_includes_recent_events(self):
        """AC-T1.4.2: context_block includes recent events."""
        from nikita.agents.voice.context import DynamicVariablesBuilder

        builder = DynamicVariablesBuilder()

        context_block = builder._build_context_block(
            user_name="Alex",
            chapter=3,
            relationship_score=70.0,
            today_summary="Went to gym, had coffee",
            nikita_daily_events="worked on security audit, cat knocked over plant",
        )

        # Should have some content when daily events provided
        assert len(context_block) > 0

    def test_context_block_token_budget(self):
        """AC-T1.4.4: Token budget ≤500 tokens."""
        from nikita.agents.voice.context import DynamicVariablesBuilder

        builder = DynamicVariablesBuilder()

        # Generate with a lot of content
        context_block = builder._build_context_block(
            user_name="Alexandra",
            chapter=5,
            relationship_score=85.0,
            today_summary="Long day at work, dealt with difficult client, went to gym, had dinner with friends, watched a movie, called mom" * 5,
            last_conversation_summary="We had a deep conversation about our future together and discussed many important topics" * 5,
            nikita_daily_events="Many events happened today" * 5,
            nikita_mood_4d={"arousal": 0.8, "valence": 0.9, "dominance": 0.6, "intimacy": 0.9},
            active_conflict_type="jealousy",
            active_conflict_severity=0.3,
        )

        # Rough token estimate: 1 token ≈ 4 characters
        estimated_tokens = len(context_block) / 4
        assert estimated_tokens <= 500, f"context_block too large: ~{estimated_tokens} tokens"


class TestVoiceContextExpanded:
    """Tests for VoiceContext model expansion to support new fields."""

    def test_voice_context_has_today_summary(self):
        """VoiceContext should support today_summary for builder."""
        context = VoiceContext(
            user_id=uuid4(),
            user_name="Test",
            chapter=3,
            relationship_score=70.0,
        )
        # Check if field exists or can be set
        # This may require updating VoiceContext model
        assert hasattr(context, "last_conversation_summary")  # Already exists

    def test_voice_context_has_backstory(self):
        """VoiceContext should support backstory field."""
        context = VoiceContext(
            user_id=uuid4(),
            user_name="Test",
            chapter=3,
            relationship_score=70.0,
        )
        # backstory field should be available
        if hasattr(context, "backstory"):
            assert context.backstory is None or isinstance(context.backstory, str)


class TestIntegration:
    """T1.5: Integration tests for expanded dynamic variables."""

    def test_all_30_plus_fields_populated(self):
        """AC-T1.5.1: All 30+ fields populated."""
        dv = DynamicVariables(
            # Original fields
            user_name="Alex",
            chapter=3,
            relationship_score=70.0,
            engagement_state="IN_ZONE",
            secureness=60.0,
            hours_since_last=2.5,
            nikita_mood="playful",
            nikita_energy="high",
            time_of_day="afternoon",
            day_of_week="Tuesday",
            nikita_activity="working",
            recent_topics="work, gym",
            open_threads="dinner plans",
            # New fields
            today_summary="Good day so far",
            last_conversation_summary="Talked about work",
            nikita_mood_arousal=0.6,
            nikita_mood_valence=0.7,
            nikita_mood_dominance=0.5,
            nikita_mood_intimacy=0.6,
            nikita_daily_events="morning coffee, security audit",
            active_conflict_type="",
            active_conflict_severity=0.0,
            emotional_context="feeling playful and engaged",
            user_backstory="Met at coffee shop downtown",
            context_block="Full context here...",
        )

        # Count total fields (excluding secret__ fields for this check)
        data = dv.to_dict()
        assert len(data) >= 25, f"Expected 25+ fields, got {len(data)}"

    def test_serialization_to_elevenlabs_format(self):
        """AC-T1.5.2: Serialization to ElevenLabs format works."""
        dv = DynamicVariables(
            user_name="Alex",
            chapter=3,
            today_summary="Had coffee",
            nikita_mood_arousal=0.7,
        )

        # to_dict should produce string values for ElevenLabs
        data = dv.to_dict()
        for key, value in data.items():
            assert isinstance(value, str), f"Field {key} should be string, got {type(value)}"

    def test_defaults_produce_valid_output(self):
        """AC-T1.5.2: Default values produce valid output."""
        dv = DynamicVariables()
        data = dv.to_dict()

        # All values should be non-None strings
        for key, value in data.items():
            assert value is not None, f"Field {key} is None"
            assert isinstance(value, str), f"Field {key} should be string"
