"""Tests for voice context block consistency (Spec 032: US-4).

TDD tests for T4.1-T4.3: Personality consistency between voice and text agents.
"""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

from nikita.agents.voice.context import DynamicVariablesBuilder
from nikita.agents.voice.models import DynamicVariables
from nikita.db.models.user import User, UserMetrics


class TestContextBlockFormat:
    """T4.1: Context block format matches text agent."""

    def test_context_block_includes_relationship_state(self):
        """AC-T4.1.1: Context block includes relationship state."""
        vars = DynamicVariables(
            user_name="Alex",
            chapter=3,
            relationship_score=Decimal("72.5"),
            context_block="",  # Will test builder generates this
        )
        builder = DynamicVariablesBuilder()
        context_block = builder._build_context_block(
            user_name="Alex",
            chapter=3,
            relationship_score=Decimal("72.5"),
        )

        assert "Alex" in context_block
        assert "chapter" in context_block.lower() or "building trust" in context_block.lower()
        assert "72" in context_block  # Score

    def test_context_block_includes_mood_summary(self):
        """AC-T4.1.2: Context block includes mood summary."""
        builder = DynamicVariablesBuilder()
        context_block = builder._build_context_block(
            nikita_mood_4d={
                "arousal": 0.8,
                "valence": 0.7,
                "dominance": 0.6,
                "intimacy": 0.5,
            }
        )

        # Should have mood descriptors
        mood_words = ["energetic", "relaxed", "happy", "moody", "confident",
                      "vulnerable", "affectionate", "guarded", "calm", "excited"]
        assert any(word in context_block.lower() for word in mood_words)

    def test_context_block_includes_today_summary(self):
        """AC-T4.1.3: Context block includes today summary when available."""
        builder = DynamicVariablesBuilder()
        context_block = builder._build_context_block(
            user_name="Alex",
            today_summary="Had coffee together this morning and discussed work stress.",
        )

        assert "coffee" in context_block.lower() or "today" in context_block.lower()

    def test_context_block_includes_conflict_when_active(self):
        """AC-T4.1.4: Context block includes conflict info when active."""
        builder = DynamicVariablesBuilder()
        context_block = builder._build_context_block(
            active_conflict_type="jealousy",
            active_conflict_severity=0.6,
        )

        assert "jealousy" in context_block.lower() or "conflict" in context_block.lower()

    def test_context_block_respects_token_limit(self):
        """AC-T4.1.5: Context block stays within token limit (~500 tokens, ~2000 chars)."""
        builder = DynamicVariablesBuilder()
        context_block = builder._build_context_block(
            user_name="Alexandra",
            chapter=5,
            relationship_score=Decimal("95.0"),
            today_summary="A" * 500,  # Long summary
            last_conversation_summary="B" * 500,  # Long summary
            user_backstory="C" * 500,  # Long backstory
            nikita_mood_4d={
                "arousal": 0.9,
                "valence": 0.9,
                "dominance": 0.9,
                "intimacy": 0.9,
            },
        )

        # Should be truncated to ~2000 chars max
        assert len(context_block) <= 2100  # Allow small buffer


class TestContextBlockContent:
    """T4.3: Tests for context block content correctness."""

    def test_chapter_names_mapped_correctly(self):
        """Test chapter numbers map to correct names."""
        builder = DynamicVariablesBuilder()

        chapter_map = {
            1: "just met",
            2: "getting acquainted",
            3: "building trust",
            4: "growing close",
            5: "deeply connected",
        }

        for chapter_num, expected_name in chapter_map.items():
            context_block = builder._build_context_block(
                chapter=chapter_num,
            )
            assert expected_name in context_block.lower(), f"Chapter {chapter_num} should map to '{expected_name}'"

    def test_empty_fields_handled_gracefully(self):
        """Test context block handles empty fields without errors."""
        builder = DynamicVariablesBuilder()
        context_block = builder._build_context_block()

        assert context_block is not None
        assert isinstance(context_block, str)

    def test_emotional_context_computed_correctly(self):
        """Test 4D mood maps to correct descriptors."""
        builder = DynamicVariablesBuilder()

        # High arousal + positive valence = energetic + happy
        emotional = builder._compute_emotional_context(
            arousal=0.9,
            valence=0.9,
            dominance=0.5,
            intimacy=0.5,
        )
        assert "energetic" in emotional.lower()
        assert "happy" in emotional.lower()

        # Low arousal + negative valence = relaxed + moody
        emotional = builder._compute_emotional_context(
            arousal=0.1,
            valence=0.1,
            dominance=0.5,
            intimacy=0.5,
        )
        assert "relaxed" in emotional.lower() or "calm" in emotional.lower()
        assert "moody" in emotional.lower()

    def test_high_dominance_shows_confident(self):
        """Test high dominance shows confident descriptor."""
        builder = DynamicVariablesBuilder()
        emotional = builder._compute_emotional_context(
            arousal=0.5,
            valence=0.5,
            dominance=0.9,
            intimacy=0.5,
        )
        assert "confident" in emotional.lower()

    def test_high_intimacy_shows_affectionate(self):
        """Test high intimacy shows affectionate descriptor."""
        builder = DynamicVariablesBuilder()
        emotional = builder._compute_emotional_context(
            arousal=0.5,
            valence=0.5,
            dominance=0.5,
            intimacy=0.9,
        )
        assert "affectionate" in emotional.lower()


class TestVoiceTextParity:
    """T4.1 continued: Voice-text parity tests."""

    def test_dynamic_vars_has_all_text_agent_fields(self):
        """Verify DynamicVariables has same fields as text agent context."""
        # These fields should exist in DynamicVariables
        required_fields = [
            "user_name",
            "chapter",
            "relationship_score",
            "engagement_state",
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

        vars = DynamicVariables()
        for field in required_fields:
            assert hasattr(vars, field), f"DynamicVariables missing field: {field}"

    def test_builder_populates_all_fields(self):
        """Verify builder populates all context fields."""
        from nikita.agents.voice.models import NikitaMood
        from types import SimpleNamespace

        builder = DynamicVariablesBuilder()

        # Build from mock context object (VoiceContext + Spec 032 attrs)
        context = SimpleNamespace(
            user_id=uuid4(),
            user_name="TestUser",
            chapter=3,
            relationship_score=65.0,
            engagement_state="IN_ZONE",
            nikita_mood=NikitaMood.PLAYFUL,
            nikita_energy="high",
            time_of_day="afternoon",
            last_conversation_summary="Discussed plans",
            recent_topics=["work", "movies"],
            open_threads=["weekend plans"],
            # Spec 032 attrs
            today_summary="Had a nice chat",
            nikita_mood_4d={
                "arousal": 0.7,
                "valence": 0.8,
                "dominance": 0.5,
                "intimacy": 0.6,
            },
            nikita_daily_events="Went to yoga class",
            active_conflict={"type": "none", "severity": 0.0},
            user_backstory="Met at a coffee shop",
            secureness=50.0,
            hours_since_last=2.5,
        )

        vars = builder.build_from_context(context)

        assert vars.user_name == "TestUser"
        assert vars.chapter == 3
        assert vars.today_summary == "Had a nice chat"
        assert vars.emotional_context  # Should be computed
        assert vars.context_block  # Should be generated


class TestBuilderIntegration:
    """Integration tests for DynamicVariablesBuilder."""

    def test_build_from_user_populates_context_block(self):
        """Test build_from_user generates complete context block."""
        from types import SimpleNamespace

        # Create mock user without using spec=User to avoid MagicMock issues
        user = SimpleNamespace(
            id=uuid4(),
            name="TestUser",
            onboarding_profile={"name": "TestUser", "backstory": "Met at gym"},
            chapter=2,
            relationship_score=Decimal("45.0"),
            game_status="active",
            last_interaction_at=datetime.now(timezone.utc),
            metrics=SimpleNamespace(
                intimacy=Decimal("50.0"),
                passion=Decimal("50.0"),
                trust=Decimal("50.0"),
                secureness=Decimal("50.0"),
                relationship_score=Decimal("45.0"),
            ),
            engagement_state=None,  # Test fallback to "IN_ZONE"
            vice_preferences=[],
        )

        builder = DynamicVariablesBuilder()
        vars = builder.build_from_user(user)

        assert vars.user_name == "TestUser"
        assert vars.chapter == 2
        assert vars.context_block  # Should be generated
        assert len(vars.context_block) > 0

    def test_context_block_suitable_for_elevenlabs_injection(self):
        """Test context block format works with ElevenLabs dynamic variables."""
        builder = DynamicVariablesBuilder()
        context_block = builder._build_context_block(
            user_name="Alex",
            chapter=3,
            relationship_score=Decimal("72.5"),
            nikita_mood_4d={"arousal": 0.7, "valence": 0.8, "dominance": 0.5, "intimacy": 0.5},
        )

        # Should not contain special characters that break injection
        assert "{{" not in context_block
        assert "}}" not in context_block
        assert "\n" not in context_block or context_block.count("\n") < 5  # Minimal newlines
