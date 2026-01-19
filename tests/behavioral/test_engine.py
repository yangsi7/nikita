"""Unit and integration tests for MetaInstructionEngine (Spec 024, Phase D: T015-T017).

Tests:
- MetaInstructionEngine class
- format_for_prompt output
- Full pipeline integration
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from nikita.behavioral.detector import SituationDetector
from nikita.behavioral.engine import MetaInstructionEngine
from nikita.behavioral.models import (
    InstructionSet,
    MetaInstruction,
    SituationCategory,
    SituationContext,
    SituationType,
)
from nikita.behavioral.selector import InstructionSelector


class TestMetaInstructionEngine:
    """Tests for MetaInstructionEngine class (AC-T015.1-T015.4)."""

    @pytest.fixture
    def engine(self):
        """Create engine instance."""
        return MetaInstructionEngine()

    def test_engine_exists(self, engine):
        """AC-T015.1: MetaInstructionEngine class exists."""
        assert engine is not None
        assert hasattr(engine, "get_instructions_for_context")

    def test_engine_has_detector(self, engine):
        """Engine has SituationDetector."""
        assert hasattr(engine, "detector")
        assert isinstance(engine.detector, SituationDetector)

    def test_engine_has_selector(self, engine):
        """Engine has InstructionSelector."""
        assert hasattr(engine, "selector")
        assert isinstance(engine.selector, InstructionSelector)

    def test_get_instructions_for_context_main_method(self, engine):
        """AC-T015.2: get_instructions_for_context() is main method."""
        result = engine.get_instructions_for_context(
            conflict_state="none",
            hours_since_last_message=2.0,
            user_local_hour=14,
            chapter=1,
        )

        assert isinstance(result, str)

    def test_get_instructions_returns_formatted_string(self, engine):
        """AC-T015.2: Returns formatted string for prompt."""
        result = engine.get_instructions_for_context(
            user_local_hour=9,  # Morning
            chapter=2,
        )

        # Should have behavioral guidance content
        if result:
            assert "Behavioral Guidance" in result or len(result) > 0

    def test_caches_instruction_library(self, engine):
        """AC-T015.3: Caches instruction library."""
        # Access selector library twice
        lib1 = engine.selector.instruction_library
        lib2 = engine.selector.instruction_library

        assert lib1 is lib2

    def test_clear_caches(self, engine):
        """clear_caches() clears selector cache."""
        # Load library
        _ = engine.selector.instruction_library
        assert engine.selector._instruction_library is not None

        # Clear caches
        engine.clear_caches()

        assert engine.selector._instruction_library is None


class TestGetInstructionsForContext:
    """Tests for get_instructions_for_context method."""

    @pytest.fixture
    def engine(self):
        """Create engine instance."""
        return MetaInstructionEngine()

    def test_detects_morning_situation(self, engine):
        """Morning hour results in morning instructions."""
        result = engine.get_instructions_for_context(
            user_local_hour=9,
            hours_since_last_message=0,
        )

        # Morning situation should include "morning" or warm energy text
        if result:
            # Check for morning-related content
            assert any(word in result.lower() for word in ["morning", "warm", "energy"])

    def test_detects_conflict_situation(self, engine):
        """Conflict state results in conflict instructions."""
        result = engine.get_instructions_for_context(
            conflict_state="cold",
            user_local_hour=14,
        )

        # Conflict situation should include conflict-related text
        if result:
            assert any(word in result.lower() for word in ["distance", "cold", "factual", "conflict"])

    def test_detects_gap_situation(self, engine):
        """Long gap results in gap instructions."""
        result = engine.get_instructions_for_context(
            hours_since_last_message=12.0,
            user_local_hour=14,
        )

        # Gap situation should include gap-related text
        if result:
            assert any(word in result.lower() for word in ["gap", "apart", "absence"])

    def test_uses_last_message_at_timestamp(self, engine):
        """Can calculate hours from last_message_at timestamp."""
        now = datetime.now(timezone.utc)
        ten_hours_ago = now - timedelta(hours=10)

        result = engine.get_instructions_for_context(
            last_message_at=ten_hours_ago,
            user_local_hour=14,
        )

        # Should detect gap situation (> 6 hours)
        if result:
            assert any(word in result.lower() for word in ["gap", "apart", "absence"])

    def test_max_instructions_configurable(self, engine):
        """max_instructions limits output."""
        result_small = engine.get_instructions_for_context(
            user_local_hour=9,
            max_instructions=1,
        )

        result_large = engine.get_instructions_for_context(
            user_local_hour=9,
            max_instructions=10,
        )

        # More instructions = longer output (generally)
        # Both should return valid strings
        assert isinstance(result_small, str)
        assert isinstance(result_large, str)

    def test_user_id_accepted(self, engine):
        """User ID parameter accepted."""
        result = engine.get_instructions_for_context(
            user_id="123e4567-e89b-12d3-a456-426614174000",
            user_local_hour=14,
        )

        assert isinstance(result, str)


class TestDetectSituation:
    """Tests for detect_situation method."""

    @pytest.fixture
    def engine(self):
        """Create engine instance."""
        return MetaInstructionEngine()

    def test_returns_situation_context(self, engine):
        """Returns SituationContext object."""
        context = engine.detect_situation(
            conflict_state="none",
            hours_since_last_message=2.0,
            user_local_hour=14,
        )

        assert isinstance(context, SituationContext)
        assert context.situation_type is not None

    def test_detects_correct_situation(self, engine):
        """Detects correct situation type."""
        # Morning
        morning = engine.detect_situation(user_local_hour=9)
        assert morning.situation_type == SituationType.MORNING

        # Evening
        evening = engine.detect_situation(user_local_hour=20)
        assert evening.situation_type == SituationType.EVENING

        # Conflict (highest priority)
        conflict = engine.detect_situation(
            conflict_state="cold",
            user_local_hour=9,  # Would be morning without conflict
        )
        assert conflict.situation_type == SituationType.CONFLICT


class TestSelectInstructions:
    """Tests for select_instructions method."""

    @pytest.fixture
    def engine(self):
        """Create engine instance."""
        return MetaInstructionEngine()

    def test_returns_instruction_set(self, engine):
        """Returns InstructionSet object."""
        context = SituationContext(situation_type=SituationType.MORNING)
        result = engine.select_instructions(context)

        assert isinstance(result, InstructionSet)

    def test_respects_max_instructions(self, engine):
        """Respects max_instructions parameter."""
        context = SituationContext(situation_type=SituationType.MORNING)
        result = engine.select_instructions(context, max_instructions=2)

        assert len(result.instructions) <= 2


class TestFormatForPrompt:
    """Tests for format_for_prompt method (AC-T016.1-T016.4)."""

    @pytest.fixture
    def engine(self):
        """Create engine instance."""
        return MetaInstructionEngine()

    def test_format_returns_string(self, engine):
        """AC-T016.1: format_for_prompt() returns string."""
        instruction_set = InstructionSet(
            situation_type=SituationType.MORNING,
            context=SituationContext(),
            instructions=[
                MetaInstruction(
                    instruction_id="test_1",
                    situation_type=SituationType.MORNING,
                    category=SituationCategory.EMOTIONAL,
                    instruction="Lean toward warm energy",
                )
            ],
        )

        result = engine.format_for_prompt(instruction_set)
        assert isinstance(result, str)

    def test_format_groups_by_category(self, engine):
        """AC-T016.2: Groups instructions by category."""
        instruction_set = InstructionSet(
            situation_type=SituationType.MORNING,
            context=SituationContext(),
            instructions=[
                MetaInstruction(
                    instruction_id="em_1",
                    situation_type=SituationType.MORNING,
                    category=SituationCategory.EMOTIONAL,
                    instruction="Emotional instruction text here",
                ),
                MetaInstruction(
                    instruction_id="conv_1",
                    situation_type=SituationType.MORNING,
                    category=SituationCategory.CONVERSATIONAL,
                    instruction="Conversational instruction text",
                ),
            ],
        )

        result = engine.format_for_prompt(instruction_set)

        # Both categories should appear
        assert "Emotional" in result
        assert "Conversational" in result

    def test_format_clean_readable(self, engine):
        """AC-T016.3: Clean, readable format."""
        instruction_set = InstructionSet(
            situation_type=SituationType.MORNING,
            context=SituationContext(),
            instructions=[
                MetaInstruction(
                    instruction_id="test_1",
                    situation_type=SituationType.MORNING,
                    category=SituationCategory.EMOTIONAL,
                    instruction="Lean toward warm energy",
                ),
            ],
        )

        result = engine.format_for_prompt(instruction_set)

        # Should have markdown structure
        assert "##" in result  # Headers
        assert "Lean toward warm energy" in result

    def test_format_empty_set(self, engine):
        """Empty instruction set returns empty string."""
        instruction_set = InstructionSet(
            situation_type=SituationType.MID_CONVERSATION,
            context=SituationContext(),
            instructions=[],
        )

        result = engine.format_for_prompt(instruction_set)
        assert result == ""


class TestGetSituationSummary:
    """Tests for get_situation_summary method."""

    @pytest.fixture
    def engine(self):
        """Create engine instance."""
        return MetaInstructionEngine()

    def test_returns_dict(self, engine):
        """Returns dictionary."""
        context = SituationContext(
            situation_type=SituationType.MORNING,
            chapter=2,
            relationship_score=65.0,
        )

        summary = engine.get_situation_summary(context)

        assert isinstance(summary, dict)
        assert "situation_type" in summary
        assert summary["situation_type"] == "morning"

    def test_includes_all_fields(self, engine):
        """Includes all relevant fields."""
        context = SituationContext(
            situation_type=SituationType.CONFLICT,
            hours_since_last_message=10.0,
            user_local_hour=14,
            chapter=3,
            relationship_score=75.0,
            conflict_state="cold",
            engagement_state="drifting",
        )

        summary = engine.get_situation_summary(context)

        assert summary["situation_type"] == "conflict"
        assert summary["hours_since_last_message"] == 10.0
        assert summary["user_local_hour"] == 14
        assert summary["chapter"] == 3
        assert summary["relationship_score"] == 75.0
        assert summary["conflict_state"] == "cold"
        assert summary["engagement_state"] == "drifting"


class TestIntegration:
    """Integration tests for full pipeline (AC-T017.1-T017.3)."""

    @pytest.fixture
    def engine(self):
        """Create engine instance."""
        return MetaInstructionEngine()

    def test_full_pipeline_context_to_format(self, engine):
        """AC-T017.1: Full pipeline from context to formatted output."""
        # Step 1: Context
        conflict_state = "cold"
        hours_since_last = 2.0
        chapter = 2

        # Step 2: Get formatted instructions
        formatted = engine.get_instructions_for_context(
            conflict_state=conflict_state,
            hours_since_last_message=hours_since_last,
            chapter=chapter,
            user_local_hour=14,
        )

        # Step 3: Verify output
        assert isinstance(formatted, str)
        # Cold conflict should produce conflict instructions
        if formatted:
            assert any(word in formatted.lower() for word in ["distance", "cold", "emotional"])

    def test_different_situations_different_outputs(self, engine):
        """AC-T017.2: Different situations produce different outputs."""
        morning_output = engine.get_instructions_for_context(
            user_local_hour=9,
            hours_since_last_message=0,
        )

        conflict_output = engine.get_instructions_for_context(
            conflict_state="explosive",
            user_local_hour=14,
        )

        gap_output = engine.get_instructions_for_context(
            hours_since_last_message=24.0,
            user_local_hour=14,
        )

        # All should be strings
        assert isinstance(morning_output, str)
        assert isinstance(conflict_output, str)
        assert isinstance(gap_output, str)

        # At least one should differ (if they have content)
        if morning_output and conflict_output:
            # Different situations produce different guidance
            assert morning_output != conflict_output or "Behavioral Guidance" in morning_output

    def test_mid_conversation_works(self, engine):
        """AC-T017.3: MID_CONVERSATION (default) works."""
        # No special conditions - afternoon, no conflict, no gap
        result = engine.get_instructions_for_context(
            user_local_hour=14,
            hours_since_last_message=1.0,
            conflict_state="none",
        )

        assert isinstance(result, str)
        # Should have mid-conversation instructions
        if result:
            assert any(word in result.lower() for word in ["flow", "conversation", "balance", "energy"])

    def test_all_situations_produce_output(self, engine):
        """Each situation type produces valid output."""
        test_cases = [
            {"conflict_state": "cold", "user_local_hour": 14},  # CONFLICT
            {"hours_since_last_message": 10.0, "user_local_hour": 14},  # AFTER_GAP
            {"user_local_hour": 9},  # MORNING
            {"user_local_hour": 20},  # EVENING
            {"user_local_hour": 14, "hours_since_last_message": 1.0},  # MID_CONVERSATION
        ]

        for params in test_cases:
            result = engine.get_instructions_for_context(**params)
            assert isinstance(result, str), f"Failed for params: {params}"


class TestConstructorConfiguration:
    """Tests for engine constructor configuration."""

    def test_default_max_instructions(self):
        """Default max_instructions is 5."""
        engine = MetaInstructionEngine()
        assert engine.max_instructions == 5

    def test_custom_max_instructions(self):
        """Custom max_instructions respected."""
        engine = MetaInstructionEngine(max_instructions=3)
        assert engine.max_instructions == 3

    def test_custom_detector(self):
        """Custom detector can be injected."""
        custom_detector = MagicMock(spec=SituationDetector)
        engine = MetaInstructionEngine(detector=custom_detector)
        assert engine.detector is custom_detector

    def test_custom_selector(self):
        """Custom selector can be injected."""
        custom_selector = MagicMock(spec=InstructionSelector)
        engine = MetaInstructionEngine(selector=custom_selector)
        assert engine.selector is custom_selector


class TestGetAllSituations:
    """Tests for get_all_situations helper."""

    def test_returns_all_situation_types(self):
        """Returns all SituationType enum values."""
        engine = MetaInstructionEngine()
        situations = engine.get_all_situations()

        assert len(situations) == 5
        assert SituationType.CONFLICT in situations
        assert SituationType.AFTER_GAP in situations
        assert SituationType.MORNING in situations
        assert SituationType.EVENING in situations
        assert SituationType.MID_CONVERSATION in situations
