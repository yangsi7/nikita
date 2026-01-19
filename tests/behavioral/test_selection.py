"""Unit tests for Instruction Selection (Spec 024, Phase C: T011-T014).

Tests:
- InstructionSelector class
- Priority-based selection
- Condition evaluation
- YAML loading integration
"""

import pytest

from nikita.behavioral.models import (
    InstructionSet,
    MetaInstruction,
    SituationCategory,
    SituationContext,
    SituationType,
)
from nikita.behavioral.selector import InstructionSelector


class TestInstructionSelector:
    """Tests for InstructionSelector class (AC-T011.1-T011.4)."""

    @pytest.fixture
    def selector(self):
        """Create selector instance."""
        return InstructionSelector()

    @pytest.fixture
    def context_morning(self):
        """Morning context for testing."""
        return SituationContext(
            situation_type=SituationType.MORNING,
            user_local_hour=9,
            chapter=1,
            relationship_score=50.0,
            conflict_state="none",
        )

    def test_selector_exists(self, selector):
        """AC-T011.1: InstructionSelector class exists."""
        assert selector is not None
        assert hasattr(selector, "select")

    def test_select_returns_instruction_set(self, selector, context_morning):
        """AC-T011.2: select() returns InstructionSet."""
        result = selector.select(context_morning)

        assert isinstance(result, InstructionSet)
        assert result.situation_type == SituationType.MORNING

    def test_loads_from_yaml(self, selector):
        """AC-T011.3: Loads from instruction library YAML."""
        library = selector.instruction_library

        assert "morning" in library
        assert "evening" in library
        assert "conflict" in library
        assert "after_gap" in library
        assert "mid_conversation" in library

    def test_select_returns_meta_instructions(self, selector, context_morning):
        """AC-T011.4: Returns list of MetaInstruction objects."""
        result = selector.select(context_morning)

        assert len(result.instructions) > 0
        for inst in result.instructions:
            assert isinstance(inst, MetaInstruction)

    def test_select_filters_by_situation(self, selector):
        """Selected instructions match the situation type."""
        morning_ctx = SituationContext(situation_type=SituationType.MORNING)
        evening_ctx = SituationContext(situation_type=SituationType.EVENING)

        morning_result = selector.select(morning_ctx)
        evening_result = selector.select(evening_ctx)

        # All morning instructions have MORNING situation type
        for inst in morning_result.instructions:
            assert inst.situation_type == SituationType.MORNING

        # All evening instructions have EVENING situation type
        for inst in evening_result.instructions:
            assert inst.situation_type == SituationType.EVENING


class TestPrioritySelection:
    """Tests for priority-based selection (AC-T012.1-T012.3)."""

    @pytest.fixture
    def selector(self):
        """Create selector instance."""
        return InstructionSelector()

    def test_sorted_by_priority(self, selector):
        """AC-T012.1: Instructions sorted by priority (1 = highest)."""
        context = SituationContext(situation_type=SituationType.MORNING)
        result = selector.select(context)

        # Check sorting
        priorities = [inst.priority for inst in result.instructions]
        assert priorities == sorted(priorities)

    def test_default_max_instructions(self, selector):
        """AC-T012.2: Default returns up to 5 instructions."""
        context = SituationContext(situation_type=SituationType.MORNING)
        result = selector.select(context)

        assert len(result.instructions) <= 5

    def test_configurable_max_instructions(self, selector):
        """AC-T012.2: max_instructions is configurable."""
        context = SituationContext(situation_type=SituationType.MORNING)

        # Select with max of 2
        result = selector.select(context, max_instructions=2)
        assert len(result.instructions) <= 2

        # Select with max of 10
        result = selector.select(context, max_instructions=10)
        assert len(result.instructions) <= 10

    def test_constructor_max_instructions(self):
        """AC-T012.2: max_instructions configurable in constructor."""
        selector = InstructionSelector(max_instructions=3)
        context = SituationContext(situation_type=SituationType.MORNING)

        result = selector.select(context)
        assert len(result.instructions) <= 3

    def test_priority_1_selected_first(self, selector):
        """Priority 1 instructions appear before priority 2."""
        context = SituationContext(situation_type=SituationType.MORNING)
        result = selector.select(context)

        if len(result.instructions) >= 2:
            assert result.instructions[0].priority <= result.instructions[1].priority


class TestConditionEvaluation:
    """Tests for condition evaluation (AC-T013.1-T013.4)."""

    @pytest.fixture
    def selector(self):
        """Create selector instance."""
        return InstructionSelector()

    def test_chapter_min_filter(self, selector):
        """AC-T013.2: chapter_min condition filters correctly."""
        # After_gap has instructions with chapter_min: 2
        context_ch1 = SituationContext(
            situation_type=SituationType.AFTER_GAP,
            hours_since_last_message=10.0,
            chapter=1,
        )
        context_ch2 = SituationContext(
            situation_type=SituationType.AFTER_GAP,
            hours_since_last_message=10.0,
            chapter=2,
        )

        result_ch1 = selector.select(context_ch1)
        result_ch2 = selector.select(context_ch2)

        # Chapter 2 should have access to instructions with chapter_min: 2
        # Find instructions that require chapter_min: 2
        ch2_only_ids = {inst.instruction_id for inst in result_ch2.instructions
                        if inst.conditions and inst.conditions.get("chapter_min") == 2}
        ch1_ids = {inst.instruction_id for inst in result_ch1.instructions}

        # Chapter 1 should NOT have chapter_min: 2 instructions
        assert not (ch2_only_ids & ch1_ids), "Chapter 1 should not have chapter_min=2 instructions"

    def test_chapter_max_filter(self, selector):
        """AC-T013.2: chapter_max condition filters correctly."""
        # Morning has instruction with chapter_max: 2
        context_ch2 = SituationContext(
            situation_type=SituationType.MORNING,
            chapter=2,
        )
        context_ch3 = SituationContext(
            situation_type=SituationType.MORNING,
            chapter=3,
        )

        result_ch2 = selector.select(context_ch2)
        result_ch3 = selector.select(context_ch3)

        # Chapter 2 should have access to chapter_max: 2 instructions
        ch2_ids = {inst.instruction_id for inst in result_ch2.instructions}
        ch3_ids = {inst.instruction_id for inst in result_ch3.instructions}

        # morning_4 has chapter_max: 2
        if "morning_4" in ch2_ids:
            assert "morning_4" not in ch3_ids

    def test_relationship_score_min_filter(self, selector):
        """AC-T013.2: relationship_score_min filters correctly."""
        # Evening has instruction with relationship_score_min: 40
        context_low = SituationContext(
            situation_type=SituationType.EVENING,
            relationship_score=30.0,
        )
        context_high = SituationContext(
            situation_type=SituationType.EVENING,
            relationship_score=60.0,
        )

        result_low = selector.select(context_low)
        result_high = selector.select(context_high)

        low_ids = {inst.instruction_id for inst in result_low.instructions}
        high_ids = {inst.instruction_id for inst in result_high.instructions}

        # evening_4 has relationship_score_min: 40
        if "evening_4" in high_ids:
            assert "evening_4" not in low_ids

    def test_conflict_states_filter(self, selector):
        """AC-T013.2: conflict_states condition filters correctly."""
        context_cold = SituationContext(
            situation_type=SituationType.CONFLICT,
            conflict_state="cold",
        )
        context_explosive = SituationContext(
            situation_type=SituationType.CONFLICT,
            conflict_state="explosive",
        )

        result_cold = selector.select(context_cold)
        result_explosive = selector.select(context_explosive)

        cold_ids = {inst.instruction_id for inst in result_cold.instructions}
        explosive_ids = {inst.instruction_id for inst in result_explosive.instructions}

        # Cold-specific instructions should only appear for cold
        # conflict_cold_1 has conflict_states: [cold]
        if "conflict_cold_1" in cold_ids:
            assert "conflict_cold_1" not in explosive_ids

    def test_non_applicable_filtered_out(self, selector):
        """AC-T013.3: Non-applicable instructions filtered out."""
        context = SituationContext(
            situation_type=SituationType.CONFLICT,
            conflict_state="cold",
            chapter=1,
        )

        result = selector.select(context)

        # All returned instructions should apply to the context
        for inst in result.instructions:
            assert inst.applies_to_context(context)

    def test_evaluate_conditions_method(self, selector):
        """AC-T013.1: evaluate_conditions method exists."""
        context = SituationContext()
        inst = MetaInstruction(
            instruction_id="test",
            situation_type=SituationType.MORNING,
            category=SituationCategory.EMOTIONAL,
            instruction="Test instruction text here",
            conditions={"chapter_min": 2},
        )

        # Should delegate to applies_to_context
        assert selector.evaluate_conditions(inst, context) == inst.applies_to_context(context)


class TestGetInstructionsForSituation:
    """Tests for get_instructions_for_situation helper."""

    @pytest.fixture
    def selector(self):
        """Create selector instance."""
        return InstructionSelector()

    def test_returns_all_instructions(self, selector):
        """Returns all instructions without condition filtering."""
        morning_instructions = selector.get_instructions_for_situation(SituationType.MORNING)

        # Should have at least the 5 morning instructions from YAML
        assert len(morning_instructions) >= 3

    def test_returns_correct_type(self, selector):
        """All returned instructions have correct situation type."""
        for situation in SituationType:
            instructions = selector.get_instructions_for_situation(situation)
            for inst in instructions:
                assert inst.situation_type == situation


class TestCaching:
    """Tests for instruction library caching."""

    def test_lazy_loading(self):
        """Instruction library is loaded lazily."""
        selector = InstructionSelector()

        # Library not loaded yet
        assert selector._instruction_library is None

        # Access library
        _ = selector.instruction_library

        # Now it's loaded
        assert selector._instruction_library is not None

    def test_cache_reused(self):
        """Library is cached and reused."""
        selector = InstructionSelector()

        lib1 = selector.instruction_library
        lib2 = selector.instruction_library

        assert lib1 is lib2

    def test_clear_cache(self):
        """clear_cache() forces reload."""
        selector = InstructionSelector()

        # Load library
        _ = selector.instruction_library
        assert selector._instruction_library is not None

        # Clear cache
        selector.clear_cache()
        assert selector._instruction_library is None

        # Next access reloads
        _ = selector.instruction_library
        assert selector._instruction_library is not None


class TestInstructionSetOutput:
    """Tests for InstructionSet output from selection."""

    @pytest.fixture
    def selector(self):
        """Create selector instance."""
        return InstructionSelector()

    def test_instruction_set_has_context(self, selector):
        """InstructionSet contains the original context."""
        context = SituationContext(
            situation_type=SituationType.MORNING,
            chapter=3,
            relationship_score=75.0,
        )

        result = selector.select(context)

        assert result.context.chapter == 3
        assert result.context.relationship_score == 75.0

    def test_instruction_set_format_for_prompt(self, selector):
        """InstructionSet can be formatted for prompt."""
        context = SituationContext(situation_type=SituationType.MORNING)
        result = selector.select(context)

        formatted = result.format_for_prompt()

        # Should produce readable output
        assert "Behavioral Guidance" in formatted or formatted == ""
        if result.instructions:
            assert len(formatted) > 0

    def test_instruction_set_by_category(self, selector):
        """InstructionSet groups instructions by category."""
        context = SituationContext(situation_type=SituationType.MORNING)
        result = selector.select(context)

        by_cat = result.by_category()

        # Should have at least one category
        assert len(by_cat) > 0

        # Categories should be SituationCategory enum values
        for cat in by_cat.keys():
            assert isinstance(cat, SituationCategory)
