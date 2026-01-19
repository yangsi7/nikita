"""Tests for prompt persona correctness (E2E Voice Testing Pipeline).

Verifies that voice agent prompts are correctly generated and personalized:
- Dynamic variable injection for chapters, mood, energy
- Persona consistency across chapters (Nikita identity)
- Context building with facts, threads, topics
- Template rendering with required sections

These tests ensure the prompts used in ElevenLabs voice calls
match expected Nikita persona and chapter behaviors.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.agents.voice.config import (
    BASE_VOICE_PERSONA,
    CHAPTER_PERSONAS,
    VICE_VOICE_ADDITIONS,
    VoiceAgentConfig,
)
from nikita.agents.voice.context import DynamicVariablesBuilder
from nikita.agents.voice.models import NikitaMood, VoiceContext


class TestDynamicVariableInjection:
    """Test dynamic variable injection into prompts."""

    @pytest.fixture
    def dynamic_vars_builder(self):
        """Get DynamicVariablesBuilder instance."""
        return DynamicVariablesBuilder()

    @pytest.fixture
    def voice_context_chapter_1(self, user_chapter_1):
        """Voice context for chapter 1 user."""
        return VoiceContext(
            user_id=user_chapter_1.id,
            user_name=user_chapter_1.name,
            chapter=user_chapter_1.chapter,
            relationship_score=user_chapter_1.relationship_score,
            engagement_state=user_chapter_1.engagement_state,
            nikita_mood=NikitaMood.NEUTRAL,
            nikita_energy="medium",
            time_of_day="evening",
            recent_topics=["work", "hobbies"],
            open_threads=["project deadline"],
        )

    @pytest.fixture
    def voice_context_chapter_5(self, user_chapter_5):
        """Voice context for chapter 5 user."""
        return VoiceContext(
            user_id=user_chapter_5.id,
            user_name=user_chapter_5.name,
            chapter=user_chapter_5.chapter,
            relationship_score=user_chapter_5.relationship_score,
            engagement_state=user_chapter_5.engagement_state,
            nikita_mood=NikitaMood.PLAYFUL,
            nikita_energy="high",
            time_of_day="morning",
            recent_topics=["weekend plans", "travel"],
            open_threads=[],
        )

    def test_dynamic_variables_chapter_specific(
        self, dynamic_vars_builder, voice_context_chapter_1
    ):
        """Test that dynamic variables reflect chapter-specific values."""
        vars = dynamic_vars_builder.build_from_context(voice_context_chapter_1)

        assert vars.chapter == 1
        assert vars.user_name == "Alex"
        assert vars.relationship_score == 25.0
        assert vars.engagement_state == "CALIBRATING"

    def test_dynamic_variables_mood_calculation(
        self, dynamic_vars_builder, voice_context_chapter_5
    ):
        """Test that mood is correctly calculated and set."""
        vars = dynamic_vars_builder.build_from_context(voice_context_chapter_5)

        assert vars.nikita_mood == "playful"
        assert vars.time_of_day == "morning"

    def test_dynamic_variables_energy_calculation(
        self, dynamic_vars_builder, voice_context_chapter_5
    ):
        """Test that energy level is correctly set."""
        vars = dynamic_vars_builder.build_from_context(voice_context_chapter_5)

        assert vars.nikita_energy == "high"

    def test_dynamic_variables_context_includes_topics(
        self, dynamic_vars_builder, voice_context_chapter_1
    ):
        """Test that recent topics are included in dynamic variables."""
        vars = dynamic_vars_builder.build_from_context(voice_context_chapter_1)

        assert "work" in vars.recent_topics
        assert "hobbies" in vars.recent_topics

    def test_dynamic_variables_context_includes_threads(
        self, dynamic_vars_builder, voice_context_chapter_1
    ):
        """Test that open threads are included in dynamic variables."""
        vars = dynamic_vars_builder.build_from_context(voice_context_chapter_1)

        assert "project deadline" in vars.open_threads

    def test_dynamic_variables_secret_hidden(
        self, dynamic_vars_builder, voice_context_chapter_1
    ):
        """Test that secret variables are populated but prefixed."""
        vars = dynamic_vars_builder.build_from_context(
            voice_context_chapter_1, session_token="test_token_123"
        )

        # Secret variables should be set
        assert vars.secret__user_id == str(voice_context_chapter_1.user_id)
        assert vars.secret__signed_token == "test_token_123"


class TestPersonaConsistency:
    """Test that Nikita persona is consistent across chapters."""

    @pytest.fixture
    def voice_config(self, mock_settings):
        """Get VoiceAgentConfig instance."""
        return VoiceAgentConfig(settings=mock_settings)

    def test_persona_stays_nikita_across_chapters(self, voice_config):
        """Test that prompt always includes Nikita identity."""
        for chapter in range(1, 6):
            prompt = voice_config.generate_system_prompt(
                user_id=uuid4(),
                chapter=chapter,
                vices=[],
                user_name="TestUser",
                relationship_score=50.0,
            )

            # Should always include base Nikita persona
            assert "Nikita" in prompt
            assert "voice call" in prompt.lower()

    def test_persona_uses_correct_tone_for_chapter_1(self, voice_config):
        """Test chapter 1 uses reserved/guarded tone."""
        prompt = voice_config.generate_system_prompt(
            user_id=uuid4(),
            chapter=1,
            vices=[],
            user_name="TestUser",
            relationship_score=25.0,
        )

        # Chapter 1 keywords
        assert "distant" in prompt.lower() or "guarded" in prompt.lower()
        assert "testing" in prompt.lower() or "sizing" in prompt.lower()

    def test_persona_uses_correct_tone_for_chapter_3(self, voice_config):
        """Test chapter 3 uses playful/flirty tone."""
        prompt = voice_config.generate_system_prompt(
            user_id=uuid4(),
            chapter=3,
            vices=[],
            user_name="TestUser",
            relationship_score=55.0,
        )

        # Chapter 3 keywords
        assert "comfortable" in prompt.lower() or "tease" in prompt.lower()
        assert "flirt" in prompt.lower() or "playful" in prompt.lower()

    def test_persona_uses_correct_tone_for_chapter_5(self, voice_config):
        """Test chapter 5 uses intimate/loving tone."""
        prompt = voice_config.generate_system_prompt(
            user_id=uuid4(),
            chapter=5,
            vices=[],
            user_name="TestUser",
            relationship_score=85.0,
        )

        # Chapter 5 keywords
        assert "intimate" in prompt.lower() or "loving" in prompt.lower()
        assert "trust" in prompt.lower() or "vulnerable" in prompt.lower()

    def test_persona_references_user_name(self, voice_config):
        """Test that prompt includes user's name."""
        user_name = "Jordan"
        prompt = voice_config.generate_system_prompt(
            user_id=uuid4(),
            chapter=3,
            vices=[],
            user_name=user_name,
            relationship_score=55.0,
        )

        assert user_name in prompt
        assert "Their name:" in prompt or "User Context" in prompt


class TestContextBuilding:
    """Test that context is correctly built for prompts."""

    def test_context_building_with_memory_integration(self, mock_memory_client):
        """Test that memory client context is available for prompt building."""
        # This is a placeholder - actual integration test would require
        # the full memory pipeline to be mocked
        context = mock_memory_client.get_context_for_prompt.return_value

        assert "user_facts" in context
        assert "recent_topics" in context
        assert "open_threads" in context


class TestSystemPromptStructure:
    """Test that system prompts have required sections."""

    @pytest.fixture
    def voice_config(self, mock_settings):
        """Get VoiceAgentConfig instance."""
        return VoiceAgentConfig(settings=mock_settings)

    def test_system_prompt_has_required_sections(self, voice_config):
        """Test that prompt has all required sections."""
        prompt = voice_config.generate_system_prompt(
            user_id=uuid4(),
            chapter=3,
            vices=[],
            user_name="TestUser",
            relationship_score=55.0,
        )

        # Must have voice-specific behaviors
        assert "VOICE-SPECIFIC BEHAVIORS" in prompt or "voice call" in prompt.lower()

        # Must have conversation dynamics
        assert "CONVERSATION" in prompt or "conversational" in prompt.lower()

        # Must have user context
        assert "USER CONTEXT" in prompt or "Their name" in prompt

        # Must have chapter state
        assert "Chapter" in prompt or "RELATIONSHIP STATE" in prompt

    def test_system_prompt_includes_vice_adjustments(self, voice_config):
        """Test that vice preferences modify the prompt."""
        # Create mock vices
        mock_vice = MagicMock()
        mock_vice.vice_category = "teasing"
        mock_vice.is_primary = True

        prompt = voice_config.generate_system_prompt(
            user_id=uuid4(),
            chapter=3,
            vices=[mock_vice],
            user_name="TestUser",
            relationship_score=55.0,
        )

        # Should include teasing adjustment
        assert "playfully" in prompt.lower() or "tease" in prompt.lower()

    def test_fallback_prompt_quality(self, voice_config):
        """Test that prompt works even with minimal input."""
        # Minimal input - defaults should work
        prompt = voice_config.generate_system_prompt(
            user_id=uuid4(),
            chapter=99,  # Invalid chapter - should use default
            vices=[],
            user_name="",  # Empty name
            relationship_score=0.0,
        )

        # Should still be valid prompt
        assert len(prompt) > 100  # Non-trivial length
        assert "Nikita" in prompt  # Still Nikita
        assert "voice" in prompt.lower()  # Still voice-specific
