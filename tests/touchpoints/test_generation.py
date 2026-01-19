"""Message generation tests for Proactive Touchpoint System (Spec 025, Phase C: T012-T016).

Tests:
- T012: MessageGenerator class
- T013: MetaPromptService integration
- T014: Life event context
- T015: Emotional state context
- T016: Phase C coverage
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nikita.touchpoints.generator import PROACTIVE_TEMPLATE
from nikita.touchpoints.models import TriggerContext, TriggerType


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_session():
    """Create mock AsyncSession."""
    return AsyncMock()


@pytest.fixture
def mock_user():
    """Create mock user."""
    user = MagicMock()
    user.id = uuid4()
    user.chapter = 2
    return user


@pytest.fixture
def mock_agent_class():
    """Mock the Pydantic AI Agent class."""
    with patch("nikita.touchpoints.generator.Agent") as mock_class:
        mock_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.output = "hey there :)"
        mock_instance.run = AsyncMock(return_value=mock_result)
        mock_class.return_value = mock_instance
        yield mock_class


@pytest.fixture
def generator(mock_session, mock_agent_class):
    """Create MessageGenerator with mocked agent."""
    from nikita.touchpoints.generator import MessageGenerator

    gen = MessageGenerator(mock_session)
    return gen


# =============================================================================
# T012: MessageGenerator Class Tests (AC-T012.1 - AC-T012.4)
# =============================================================================


class TestMessageGeneratorClass:
    """Test MessageGenerator class structure."""

    def test_generator_exists(self, generator):
        """AC-T012.1: MessageGenerator class exists."""
        assert generator is not None

    def test_generator_has_session(self, generator, mock_session):
        """Generator stores session."""
        assert generator.session is mock_session

    def test_generator_has_agent(self, generator):
        """Generator has Haiku agent."""
        assert generator._agent is not None

    def test_generator_loads_template(self, generator):
        """Generator loads template."""
        assert generator._template is not None
        assert len(generator._template) > 0


class TestGenerateMethod:
    """Test generate() method (AC-T012.2)."""

    @pytest.mark.asyncio
    async def test_generate_returns_string(self, generator, mock_user):
        """AC-T012.2: generate() returns string content."""
        trigger_context = TriggerContext(
            trigger_type=TriggerType.TIME,
            time_slot="morning",
            chapter=2,
        )

        with patch(
            "nikita.db.repositories.user_repository.UserRepository"
        ) as mock_repo_class:
            mock_repo = mock_repo_class.return_value
            mock_repo.get_by_id = AsyncMock(return_value=mock_user)

            result = await generator.generate(
                user_id=mock_user.id,
                trigger_context=trigger_context,
            )

        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_generate_with_life_event(self, generator, mock_user):
        """Generate with life event context."""
        trigger_context = TriggerContext(
            trigger_type=TriggerType.EVENT,
            event_id="evt_123",
            event_type="work_drama",
            event_description="Boss was difficult",
            chapter=3,
        )

        with patch(
            "nikita.db.repositories.user_repository.UserRepository"
        ) as mock_repo_class:
            mock_repo = mock_repo_class.return_value
            mock_repo.get_by_id = AsyncMock(return_value=mock_user)

            result = await generator.generate(
                user_id=mock_user.id,
                trigger_context=trigger_context,
                life_event_description="Boss criticized her project publicly",
            )

        assert isinstance(result, str)


# =============================================================================
# T013: MetaPromptService Integration Tests (AC-T013.1 - AC-T013.4)
# =============================================================================


class TestMetaPromptIntegration:
    """Test integration with MetaPromptService patterns."""

    def test_uses_haiku_agent(self, generator):
        """AC-T013.1: Uses Haiku agent like MetaPromptService."""
        # Generator has an agent
        assert generator._agent is not None

    @pytest.mark.asyncio
    async def test_passes_trigger_context(self, generator, mock_user):
        """AC-T013.2: Passes trigger context for personalization."""
        trigger_context = TriggerContext(
            trigger_type=TriggerType.GAP,
            hours_since_contact=30.0,
            chapter=2,
        )

        with patch(
            "nikita.db.repositories.user_repository.UserRepository"
        ) as mock_repo_class:
            mock_repo = mock_repo_class.return_value
            mock_repo.get_by_id = AsyncMock(return_value=mock_user)

            await generator.generate(
                user_id=mock_user.id,
                trigger_context=trigger_context,
            )

        # Verify agent was called
        generator._agent.run.assert_called_once()
        # Check the prompt includes trigger info
        call_args = generator._agent.run.call_args[0][0]
        assert "gap" in call_args.lower()

    def test_uses_proactive_template(self, generator):
        """AC-T013.3: Uses proactive message template."""
        template = generator._template
        assert "trigger" in template.lower() or "{{trigger_type}}" in template


# =============================================================================
# T014: Life Event Context Tests (AC-T014.1 - AC-T014.4)
# =============================================================================


class TestLifeEventContext:
    """Test life event context integration."""

    @pytest.mark.asyncio
    async def test_loads_life_event(self, generator, mock_user):
        """AC-T014.1: Loads relevant life event from trigger_context."""
        trigger_context = TriggerContext(
            trigger_type=TriggerType.EVENT,
            event_id="evt_456",
            event_type="social_drama",
            event_description="Friend cancelled plans last minute",
            chapter=3,
        )

        with patch(
            "nikita.db.repositories.user_repository.UserRepository"
        ) as mock_repo_class:
            mock_repo = mock_repo_class.return_value
            mock_repo.get_by_id = AsyncMock(return_value=mock_user)

            await generator.generate(
                user_id=mock_user.id,
                trigger_context=trigger_context,
                life_event_description="Her friend cancelled plans last minute",
            )

        # Verify life event was passed to agent
        call_args = generator._agent.run.call_args[0][0]
        assert "friend" in call_args.lower() or "cancelled" in call_args.lower()

    @pytest.mark.asyncio
    async def test_includes_event_in_prompt(self, generator, mock_user):
        """AC-T014.2: Includes event description in prompt."""
        trigger_context = TriggerContext(
            trigger_type=TriggerType.EVENT,
            event_id="evt_789",
            event_type="work_success",
            event_description="Got a new photography client",
            chapter=2,
        )

        with patch(
            "nikita.db.repositories.user_repository.UserRepository"
        ) as mock_repo_class:
            mock_repo = mock_repo_class.return_value
            mock_repo.get_by_id = AsyncMock(return_value=mock_user)

            await generator.generate(
                user_id=mock_user.id,
                trigger_context=trigger_context,
                life_event_description="Got a new photography client",
            )

        call_args = generator._agent.run.call_args[0][0]
        assert "client" in call_args.lower() or "photography" in call_args.lower()


# =============================================================================
# T015: Emotional State Context Tests (AC-T015.1 - AC-T015.4)
# =============================================================================


class TestEmotionalStateContext:
    """Test emotional state context integration."""

    def test_format_emotional_state_positive(self, generator):
        """AC-T015.2: High valence affects message tone."""
        emotional_state = {
            "valence": 0.8,
            "arousal": 0.8,  # > 0.7 threshold for "high energy"
            "dominance": 0.6,
        }

        formatted = generator._format_emotional_state(emotional_state)

        assert "positive" in formatted.lower()
        assert "high energy" in formatted.lower()

    def test_format_emotional_state_negative(self, generator):
        """AC-T015.2: Low valence affects message tone."""
        emotional_state = {
            "valence": 0.2,
            "arousal": 0.3,
            "dominance": 0.2,
        }

        formatted = generator._format_emotional_state(emotional_state)

        assert "negative" in formatted.lower()
        assert "vulnerable" in formatted.lower()

    def test_format_emotional_state_neutral(self, generator):
        """Neutral emotional state."""
        emotional_state = {
            "valence": 0.5,
            "arousal": 0.5,
            "dominance": 0.5,
        }

        formatted = generator._format_emotional_state(emotional_state)

        assert "neutral" in formatted.lower()

    @pytest.mark.asyncio
    async def test_emotional_state_in_prompt(self, generator, mock_user):
        """AC-T015.3: Emotional state included in generation prompt."""
        trigger_context = TriggerContext(
            trigger_type=TriggerType.TIME,
            time_slot="evening",
            chapter=3,
        )
        emotional_state = {
            "valence": 0.3,
            "arousal": 0.6,
        }

        with patch(
            "nikita.db.repositories.user_repository.UserRepository"
        ) as mock_repo_class:
            mock_repo = mock_repo_class.return_value
            mock_repo.get_by_id = AsyncMock(return_value=mock_user)

            await generator.generate(
                user_id=mock_user.id,
                trigger_context=trigger_context,
                emotional_state=emotional_state,
            )

        call_args = generator._agent.run.call_args[0][0]
        # Should include emotional state info
        assert "negative" in call_args.lower() or "feeling" in call_args.lower()


# =============================================================================
# Mood and Energy Computation Tests
# =============================================================================


class TestMoodComputation:
    """Test mood and energy computation."""

    def test_compute_mood_gap_trigger(self, generator):
        """Gap trigger has specific mood."""
        trigger_context = TriggerContext(
            trigger_type=TriggerType.GAP,
            hours_since_contact=30.0,
        )

        mood = generator._compute_mood(trigger_context)

        assert "thinking" in mood.lower() or "concerned" in mood.lower()

    def test_compute_mood_morning(self, generator):
        """Morning slot has optimistic mood."""
        trigger_context = TriggerContext(
            trigger_type=TriggerType.TIME,
            time_slot="morning",
        )

        mood = generator._compute_mood(trigger_context)

        assert "fresh" in mood.lower() or "optimistic" in mood.lower()

    def test_compute_mood_evening(self, generator):
        """Evening slot has relaxed mood."""
        trigger_context = TriggerContext(
            trigger_type=TriggerType.TIME,
            time_slot="evening",
        )

        mood = generator._compute_mood(trigger_context)

        assert "relaxed" in mood.lower() or "reflective" in mood.lower()

    def test_compute_mood_from_emotional_state(self, generator):
        """Mood from emotional state overrides defaults."""
        trigger_context = TriggerContext(
            trigger_type=TriggerType.TIME,
            time_slot="morning",
            emotional_state={
                "valence": 0.2,
                "arousal": 0.7,
            },
        )

        mood = generator._compute_mood(trigger_context)

        # Should use emotional state, not morning default
        assert "upset" in mood.lower() or "agitated" in mood.lower()

    def test_compute_energy_morning(self, generator):
        """Morning has waking up energy."""
        trigger_context = TriggerContext(
            trigger_type=TriggerType.TIME,
            time_slot="morning",
        )

        energy = generator._compute_energy(trigger_context)

        assert "woke up" in energy.lower() or "medium" in energy.lower()

    def test_compute_energy_evening(self, generator):
        """Evening has winding down energy."""
        trigger_context = TriggerContext(
            trigger_type=TriggerType.TIME,
            time_slot="evening",
        )

        energy = generator._compute_energy(trigger_context)

        assert "winding" in energy.lower()

    def test_compute_energy_event(self, generator):
        """Event trigger has high energy."""
        trigger_context = TriggerContext(
            trigger_type=TriggerType.EVENT,
            event_id="evt_test",
            event_type="test",
            event_description="test",
        )

        energy = generator._compute_energy(trigger_context)

        assert "high" in energy.lower()


# =============================================================================
# Template Tests
# =============================================================================


class TestTemplate:
    """Test template loading and formatting."""

    def test_template_file_exists(self):
        """Template file should exist."""
        assert PROACTIVE_TEMPLATE.exists()

    def test_template_has_placeholders(self, generator):
        """Template has required placeholders."""
        template = generator._template

        # Check for key content patterns
        assert "trigger" in template.lower()
        assert "chapter" in template.lower()

    def test_format_template(self, generator):
        """Template formatting replaces placeholders."""
        context = {
            "trigger_type": "time",
            "time_slot": "morning",
            "hours_since_contact": 0,
            "chapter": 2,
            "chapter_description": "Dating",
            "mood": "happy",
            "energy": "high",
            "event_context": "No event",
            "emotional_state": "Positive",
            "recent_summary": "Had a nice chat yesterday",
        }

        formatted = generator._format_template(context)

        # Placeholders should be replaced
        assert "{{trigger_type}}" not in formatted
        assert "time" in formatted.lower()
        assert "morning" in formatted.lower()


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestConvenienceFunction:
    """Test generate_touchpoint_message convenience function."""

    def test_convenience_function_exists(self):
        """Convenience function is importable."""
        from nikita.touchpoints.generator import generate_touchpoint_message

        assert generate_touchpoint_message is not None
        assert callable(generate_touchpoint_message)


# =============================================================================
# T016: Phase C Coverage Tests (AC-T016.1, AC-T016.2)
# =============================================================================


class TestPhaseCCoverage:
    """Ensure Phase C has comprehensive test coverage."""

    def test_generator_module_importable(self, mock_agent_class):
        """AC-T016.1: Generator module importable."""
        from nikita.touchpoints.generator import (
            MessageGenerator,
            generate_touchpoint_message,
        )

        assert MessageGenerator is not None
        assert generate_touchpoint_message is not None

    def test_generator_in_package_exports(self, mock_agent_class):
        """Generator exported from package."""
        from nikita.touchpoints import MessageGenerator, generate_touchpoint_message

        assert MessageGenerator is not None
        assert generate_touchpoint_message is not None

    def test_template_exists(self):
        """Template file exists."""
        assert PROACTIVE_TEMPLATE.exists()
        content = PROACTIVE_TEMPLATE.read_text()
        assert len(content) > 0

    def test_all_trigger_types_handled(self, generator):
        """All trigger types handled in mood/energy computation."""
        for trigger_type in TriggerType:
            if trigger_type == TriggerType.TIME:
                context = TriggerContext(
                    trigger_type=trigger_type,
                    time_slot="morning",
                )
            elif trigger_type == TriggerType.EVENT:
                context = TriggerContext(
                    trigger_type=trigger_type,
                    event_id="test",
                    event_type="test",
                    event_description="test",
                )
            else:  # GAP
                context = TriggerContext(
                    trigger_type=trigger_type,
                    hours_since_contact=30.0,
                )

            mood = generator._compute_mood(context)
            energy = generator._compute_energy(context)

            assert mood is not None
            assert energy is not None
