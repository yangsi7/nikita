"""Unit tests for Behavioral Meta-Instructions models (Spec 024, T004).

Tests:
- MetaInstruction model validation
- SituationContext model validation
- InstructionSet formatting
- YAML loading tests
- Condition evaluation tests
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
import yaml

from nikita.behavioral.models import (
    InstructionSet,
    MetaInstruction,
    SituationCategory,
    SituationContext,
    SituationType,
)


class TestSituationType:
    """Tests for SituationType enum."""

    def test_all_situation_types_exist(self):
        """All expected situation types should exist."""
        assert SituationType.CONFLICT == "conflict"
        assert SituationType.AFTER_GAP == "after_gap"
        assert SituationType.MORNING == "morning"
        assert SituationType.EVENING == "evening"
        assert SituationType.MID_CONVERSATION == "mid_conversation"

    def test_situation_type_count(self):
        """Should have exactly 5 situation types."""
        assert len(SituationType) == 5


class TestSituationCategory:
    """Tests for SituationCategory enum."""

    def test_all_categories_exist(self):
        """All expected categories should exist."""
        assert SituationCategory.EMOTIONAL == "emotional"
        assert SituationCategory.CONVERSATIONAL == "conversational"
        assert SituationCategory.RELATIONAL == "relational"
        assert SituationCategory.TACTICAL == "tactical"

    def test_category_count(self):
        """Should have exactly 4 categories."""
        assert len(SituationCategory) == 4


class TestSituationContext:
    """Tests for SituationContext model (AC-T002.2)."""

    def test_default_context(self):
        """Default context should have reasonable defaults."""
        ctx = SituationContext()

        assert ctx.situation_type == SituationType.MID_CONVERSATION
        assert ctx.hours_since_last_message == 0.0
        assert ctx.user_local_hour == 12
        assert ctx.chapter == 1
        assert ctx.relationship_score == 50.0
        assert ctx.conflict_state == "none"
        assert ctx.engagement_state == "in_zone"

    def test_context_with_values(self):
        """Context should accept custom values."""
        user_id = uuid4()
        ctx = SituationContext(
            user_id=user_id,
            situation_type=SituationType.CONFLICT,
            hours_since_last_message=24.5,
            user_local_hour=9,
            chapter=3,
            relationship_score=75.5,
            conflict_state="cold",
            engagement_state="drifting",
        )

        assert ctx.user_id == user_id
        assert ctx.situation_type == SituationType.CONFLICT
        assert ctx.hours_since_last_message == 24.5
        assert ctx.user_local_hour == 9
        assert ctx.chapter == 3
        assert ctx.relationship_score == 75.5
        assert ctx.conflict_state == "cold"

    def test_context_validates_hours(self):
        """Hours since last message cannot be negative."""
        with pytest.raises(ValueError):
            SituationContext(hours_since_last_message=-1.0)

    def test_context_validates_hour_range(self):
        """User local hour must be 0-23."""
        with pytest.raises(ValueError):
            SituationContext(user_local_hour=25)

        with pytest.raises(ValueError):
            SituationContext(user_local_hour=-1)

    def test_context_validates_chapter_range(self):
        """Chapter must be 1-5."""
        with pytest.raises(ValueError):
            SituationContext(chapter=0)

        with pytest.raises(ValueError):
            SituationContext(chapter=6)

    def test_context_validates_relationship_score(self):
        """Relationship score must be 0-100."""
        with pytest.raises(ValueError):
            SituationContext(relationship_score=-1.0)

        with pytest.raises(ValueError):
            SituationContext(relationship_score=101.0)

    def test_context_detected_at_auto_set(self):
        """detected_at should be automatically set."""
        ctx = SituationContext()
        assert ctx.detected_at is not None
        assert ctx.detected_at.tzinfo == timezone.utc


class TestMetaInstruction:
    """Tests for MetaInstruction model (AC-T002.1)."""

    def test_basic_instruction(self):
        """Basic instruction should be created."""
        inst = MetaInstruction(
            instruction_id="test_1",
            situation_type=SituationType.MORNING,
            category=SituationCategory.EMOTIONAL,
            instruction="Lean toward warm energy in the morning",
        )

        assert inst.instruction_id == "test_1"
        assert inst.situation_type == SituationType.MORNING
        assert inst.category == SituationCategory.EMOTIONAL
        assert inst.priority == 5  # default
        assert inst.weight == 1.0  # default

    def test_instruction_with_conditions(self):
        """Instruction with conditions should be created."""
        inst = MetaInstruction(
            instruction_id="test_2",
            situation_type=SituationType.CONFLICT,
            category=SituationCategory.TACTICAL,
            priority=1,
            instruction="Lean toward expressing displeasure subtly",
            conditions={
                "chapter_min": 2,
                "conflict_states": ["passive_aggressive"],
            },
        )

        assert inst.conditions == {
            "chapter_min": 2,
            "conflict_states": ["passive_aggressive"],
        }

    def test_instruction_validates_priority(self):
        """Priority must be 1-10."""
        with pytest.raises(ValueError):
            MetaInstruction(
                instruction_id="test",
                situation_type=SituationType.MORNING,
                category=SituationCategory.EMOTIONAL,
                instruction="Test instruction here",
                priority=0,
            )

        with pytest.raises(ValueError):
            MetaInstruction(
                instruction_id="test",
                situation_type=SituationType.MORNING,
                category=SituationCategory.EMOTIONAL,
                instruction="Test instruction here",
                priority=11,
            )

    def test_instruction_validates_min_length(self):
        """Instruction text must be at least 10 characters."""
        with pytest.raises(ValueError):
            MetaInstruction(
                instruction_id="test",
                situation_type=SituationType.MORNING,
                category=SituationCategory.EMOTIONAL,
                instruction="Short",  # Too short
            )

    def test_instruction_validates_weight(self):
        """Weight must be 0.0-2.0."""
        with pytest.raises(ValueError):
            MetaInstruction(
                instruction_id="test",
                situation_type=SituationType.MORNING,
                category=SituationCategory.EMOTIONAL,
                instruction="Valid instruction text here",
                weight=-0.5,
            )


class TestMetaInstructionConditions:
    """Tests for MetaInstruction.applies_to_context() (AC-T002.3)."""

    @pytest.fixture
    def base_context(self):
        """Base context for condition testing."""
        return SituationContext(
            chapter=2,
            relationship_score=60.0,
            conflict_state="cold",
            engagement_state="in_zone",
        )

    def test_no_conditions_applies(self, base_context):
        """Instruction with no conditions should apply."""
        inst = MetaInstruction(
            instruction_id="test",
            situation_type=SituationType.MORNING,
            category=SituationCategory.EMOTIONAL,
            instruction="Always applicable instruction",
        )

        assert inst.applies_to_context(base_context) is True

    def test_chapter_min_applies(self, base_context):
        """chapter_min condition should work."""
        inst = MetaInstruction(
            instruction_id="test",
            situation_type=SituationType.MORNING,
            category=SituationCategory.EMOTIONAL,
            instruction="Chapter 2+ instruction here",
            conditions={"chapter_min": 2},
        )

        assert inst.applies_to_context(base_context) is True  # chapter=2

        base_context.chapter = 1
        assert inst.applies_to_context(base_context) is False

    def test_chapter_max_applies(self, base_context):
        """chapter_max condition should work."""
        inst = MetaInstruction(
            instruction_id="test",
            situation_type=SituationType.MORNING,
            category=SituationCategory.EMOTIONAL,
            instruction="Early chapter instruction",
            conditions={"chapter_max": 2},
        )

        assert inst.applies_to_context(base_context) is True  # chapter=2

        base_context.chapter = 3
        assert inst.applies_to_context(base_context) is False

    def test_relationship_score_min_applies(self, base_context):
        """relationship_score_min condition should work."""
        inst = MetaInstruction(
            instruction_id="test",
            situation_type=SituationType.EVENING,
            category=SituationCategory.RELATIONAL,
            instruction="High relationship instruction",
            conditions={"relationship_score_min": 50.0},
        )

        assert inst.applies_to_context(base_context) is True  # score=60

        base_context.relationship_score = 40.0
        assert inst.applies_to_context(base_context) is False

    def test_conflict_states_applies(self, base_context):
        """conflict_states condition should work."""
        inst = MetaInstruction(
            instruction_id="test",
            situation_type=SituationType.CONFLICT,
            category=SituationCategory.EMOTIONAL,
            instruction="Cold conflict instruction",
            conditions={"conflict_states": ["cold", "vulnerable"]},
        )

        assert inst.applies_to_context(base_context) is True  # conflict_state="cold"

        base_context.conflict_state = "explosive"
        assert inst.applies_to_context(base_context) is False

    def test_engagement_states_applies(self, base_context):
        """engagement_states condition should work."""
        inst = MetaInstruction(
            instruction_id="test",
            situation_type=SituationType.MID_CONVERSATION,
            category=SituationCategory.TACTICAL,
            instruction="In-zone engagement instruction",
            conditions={"engagement_states": ["in_zone", "engaged"]},
        )

        assert inst.applies_to_context(base_context) is True  # engagement_state="in_zone"

        base_context.engagement_state = "drifting"
        assert inst.applies_to_context(base_context) is False

    def test_multiple_conditions_all_must_pass(self, base_context):
        """Multiple conditions must all pass."""
        inst = MetaInstruction(
            instruction_id="test",
            situation_type=SituationType.CONFLICT,
            category=SituationCategory.EMOTIONAL,
            instruction="Multiple condition instruction",
            conditions={
                "chapter_min": 2,
                "relationship_score_min": 50.0,
                "conflict_states": ["cold"],
            },
        )

        assert inst.applies_to_context(base_context) is True

        # Fail one condition
        base_context.chapter = 1
        assert inst.applies_to_context(base_context) is False


class TestInstructionSet:
    """Tests for InstructionSet model."""

    @pytest.fixture
    def sample_instructions(self):
        """Sample instructions for testing."""
        return [
            MetaInstruction(
                instruction_id="em_1",
                situation_type=SituationType.MORNING,
                category=SituationCategory.EMOTIONAL,
                priority=1,
                instruction="Lean toward warm energy",
            ),
            MetaInstruction(
                instruction_id="conv_1",
                situation_type=SituationType.MORNING,
                category=SituationCategory.CONVERSATIONAL,
                priority=2,
                instruction="Consider sharing morning plans",
            ),
            MetaInstruction(
                instruction_id="em_2",
                situation_type=SituationType.MORNING,
                category=SituationCategory.EMOTIONAL,
                priority=3,
                instruction="Balance enthusiasm with calmness",
            ),
        ]

    def test_by_category_groups_correctly(self, sample_instructions):
        """by_category() should group instructions."""
        inst_set = InstructionSet(
            situation_type=SituationType.MORNING,
            context=SituationContext(),
            instructions=sample_instructions,
        )

        by_cat = inst_set.by_category()

        assert SituationCategory.EMOTIONAL in by_cat
        assert len(by_cat[SituationCategory.EMOTIONAL]) == 2
        assert SituationCategory.CONVERSATIONAL in by_cat
        assert len(by_cat[SituationCategory.CONVERSATIONAL]) == 1

    def test_format_for_prompt(self, sample_instructions):
        """format_for_prompt() should produce readable output."""
        inst_set = InstructionSet(
            situation_type=SituationType.MORNING,
            context=SituationContext(),
            instructions=sample_instructions,
        )

        formatted = inst_set.format_for_prompt()

        assert "## Behavioral Guidance" in formatted
        assert "Morning" in formatted
        assert "### Emotional" in formatted
        assert "Lean toward warm energy" in formatted
        assert "Consider sharing morning plans" in formatted

    def test_format_empty_set(self):
        """Empty instruction set should return empty string."""
        inst_set = InstructionSet(
            situation_type=SituationType.MORNING,
            context=SituationContext(),
            instructions=[],
        )

        assert inst_set.format_for_prompt() == ""


class TestYAMLLoading:
    """Tests for YAML configuration loading (AC-T004.2)."""

    def test_situations_yaml_loads(self):
        """situations.yaml should load correctly."""
        with open("nikita/config_data/behavioral/situations.yaml") as f:
            data = yaml.safe_load(f)

        assert "situations" in data
        assert "conflict" in data["situations"]
        assert "after_gap" in data["situations"]
        assert "morning" in data["situations"]
        assert "evening" in data["situations"]
        assert "mid_conversation" in data["situations"]

    def test_situations_have_priorities(self):
        """Each situation should have a priority."""
        with open("nikita/config_data/behavioral/situations.yaml") as f:
            data = yaml.safe_load(f)

        for name, config in data["situations"].items():
            assert "priority" in config, f"Situation {name} missing priority"
            assert isinstance(config["priority"], int)

    def test_instructions_yaml_loads(self):
        """instructions.yaml should load correctly."""
        with open("nikita/config_data/behavioral/instructions.yaml") as f:
            data = yaml.safe_load(f)

        assert "conflict" in data
        assert "after_gap" in data
        assert "morning" in data
        assert "evening" in data
        assert "mid_conversation" in data

    def test_instructions_have_required_fields(self):
        """Each instruction should have required fields."""
        with open("nikita/config_data/behavioral/instructions.yaml") as f:
            data = yaml.safe_load(f)

        for situation, instructions in data.items():
            for inst in instructions:
                assert "id" in inst, f"Instruction in {situation} missing id"
                assert "category" in inst, f"Instruction in {situation} missing category"
                assert "instruction" in inst, f"Instruction in {situation} missing instruction"

    def test_instructions_use_directional_language(self):
        """Instructions should use directional language."""
        directional_phrases = [
            "lean toward",
            "consider",
            "tend to",
            "balance",
            "avoid",
        ]

        with open("nikita/config_data/behavioral/instructions.yaml") as f:
            data = yaml.safe_load(f)

        total_instructions = 0
        directional_count = 0

        for instructions in data.values():
            for inst in instructions:
                total_instructions += 1
                text = inst["instruction"].lower()
                if any(phrase in text for phrase in directional_phrases):
                    directional_count += 1

        # At least 80% should use directional language
        assert directional_count / total_instructions >= 0.8

    def test_each_situation_has_minimum_instructions(self):
        """Each situation should have 3-5 instructions."""
        with open("nikita/config_data/behavioral/instructions.yaml") as f:
            data = yaml.safe_load(f)

        for situation, instructions in data.items():
            # Filter to base instructions (not conflict sub-states)
            if situation == "conflict":
                # Conflict has sub-states, check total
                assert len(instructions) >= 10, f"Conflict has too few instructions"
            else:
                assert len(instructions) >= 3, f"{situation} has too few instructions"
                assert len(instructions) <= 8, f"{situation} has too many instructions"
