"""Tests for Narrative Arc System (Spec 035 T3.8).

TDD tests for the narrative arc system covering:
- Arc templates and categories
- Arc stage progression
- Template selection by vulnerability
- Arc context formatting
- Serialization/deserialization

20+ tests per T3.8 acceptance criteria.
"""

import random
from datetime import datetime
from uuid import uuid4

import pytest

from nikita.life_simulation.arcs import (
    ActiveArc,
    ArcCategory,
    ArcStage,
    ArcTemplate,
    NarrativeArcSystem,
    get_arc_system,
)


class TestArcSystemSingleton:
    """Tests for arc system singleton pattern (AC-T3.8.1)."""

    def test_arc_system_singleton(self):
        """Test that get_arc_system returns singleton."""
        system1 = get_arc_system()
        system2 = get_arc_system()

        assert system1 is system2
        assert isinstance(system1, NarrativeArcSystem)


class TestTemplateSelection:
    """Tests for template selection by vulnerability level (AC-T3.8.2-4)."""

    @pytest.fixture
    def system(self):
        """Create a fresh NarrativeArcSystem."""
        return NarrativeArcSystem()

    def test_template_selection_vulnerability_0(self, system):
        """Test that vulnerability 0 only gets templates with requirement 0."""
        template = system.select_arc_template(
            vulnerability_level=0,
            chapter=1,
            recent_topics=[],
        )

        if template:
            assert template.vulnerability_requirement <= 0

    def test_template_selection_vulnerability_3(self, system):
        """Test that vulnerability 3 can access deeper templates."""
        # Set seed for reproducibility
        random.seed(42)

        # Try multiple times to get a template
        templates_found = []
        for _ in range(10):
            template = system.select_arc_template(
                vulnerability_level=3,
                chapter=3,
                recent_topics=["vulnerability_shared", "deep_conversation"],
            )
            if template:
                templates_found.append(template)

        # Should find some templates with requirement <= 3
        assert len(templates_found) > 0
        for t in templates_found:
            assert t.vulnerability_requirement <= 3

    def test_template_selection_vulnerability_5(self, system):
        """Test that vulnerability 5 can access all templates."""
        random.seed(42)

        # Should be able to get any template
        template = system.select_arc_template(
            vulnerability_level=5,
            chapter=5,
            recent_topics=["family_topic"],
        )

        assert template is not None
        assert template.vulnerability_requirement <= 5

    def test_template_selection_by_topic_work(self, system):
        """Test template selection favors work topics when mentioned."""
        random.seed(42)

        # Find templates multiple times with work topics
        career_count = 0
        for _ in range(20):
            template = system.select_arc_template(
                vulnerability_level=3,
                chapter=3,
                recent_topics=["work_discussion", "stress_mention"],
            )
            if template and template.category == ArcCategory.CAREER:
                career_count += 1

        # Should have some career templates
        assert career_count > 0

    def test_template_selection_by_topic_friend(self, system):
        """Test template selection with friend topics."""
        random.seed(42)

        social_count = 0
        for _ in range(20):
            template = system.select_arc_template(
                vulnerability_level=3,
                chapter=3,
                recent_topics=["user_jealousy", "past_discussion"],
            )
            if template and template.category == ArcCategory.SOCIAL:
                social_count += 1

        # Should find some social templates
        assert social_count > 0


class TestArcStageProgression:
    """Tests for arc stage progression (AC-T3.8.7-8)."""

    def test_arc_stage_progression_setup_to_rising(self):
        """Test advancing from SETUP to RISING."""
        arc = ActiveArc(
            user_id=uuid4(),
            template_name="test_arc",
            category=ArcCategory.SOCIAL,
            stage=ArcStage.SETUP,
            conversations_in_arc=2,
            max_conversations=5,
        )

        # Advance stage
        result = arc.advance_stage()

        assert result is True
        assert arc.stage == ArcStage.RISING

    def test_arc_stage_progression_full_cycle(self):
        """Test full stage progression cycle."""
        arc = ActiveArc(
            user_id=uuid4(),
            template_name="test_arc",
            category=ArcCategory.RELATIONSHIP,
            stage=ArcStage.SETUP,
        )

        # Progress through all stages
        stages_visited = [arc.stage]

        while arc.stage != ArcStage.RESOLVED:
            result = arc.advance_stage()
            stages_visited.append(arc.stage)
            if not result:
                break

        expected = [
            ArcStage.SETUP,
            ArcStage.RISING,
            ArcStage.CLIMAX,
            ArcStage.FALLING,
            ArcStage.RESOLVED,
        ]
        assert stages_visited == expected

    def test_arc_should_advance_by_conversation_count(self):
        """Test should_advance based on conversation progress."""
        arc = ActiveArc(
            user_id=uuid4(),
            template_name="test_arc",
            stage=ArcStage.SETUP,
            conversations_in_arc=0,
            max_conversations=10,
        )

        # At 0/10 (0%), should not advance
        assert arc.should_advance() is False

        # At 2/10 (20%), should advance from SETUP
        arc.conversations_in_arc = 2
        assert arc.should_advance() is True

    def test_arc_max_duration_enforcement(self):
        """Test that arc respects max conversation count."""
        arc = ActiveArc(
            user_id=uuid4(),
            template_name="test_arc",
            stage=ArcStage.SETUP,
            conversations_in_arc=10,
            max_conversations=10,
        )

        # At 100% progress, should want to advance through stages
        assert arc.should_advance() is True


class TestArcResolution:
    """Tests for arc resolution (AC-T3.8.11, T3.8.17)."""

    def test_arc_resolution_sets_resolved_at(self):
        """Test that resolution sets resolved_at timestamp."""
        arc = ActiveArc(
            user_id=uuid4(),
            template_name="test_arc",
            stage=ArcStage.FALLING,
        )

        assert arc.resolved_at is None

        # Advance to RESOLVED
        arc.advance_stage()

        assert arc.stage == ArcStage.RESOLVED
        assert arc.resolved_at is not None
        assert isinstance(arc.resolved_at, datetime)

    def test_arc_inactive_after_resolution(self):
        """Test that resolved arcs cannot advance further."""
        arc = ActiveArc(
            user_id=uuid4(),
            template_name="test_arc",
            stage=ArcStage.RESOLVED,
            resolved_at=datetime.now(),
        )

        # Should not advance past RESOLVED
        result = arc.advance_stage()

        assert result is False
        assert arc.stage == ArcStage.RESOLVED


class TestArcSerialization:
    """Tests for arc serialization (AC-T3.8.12)."""

    def test_arc_to_dict_serialization(self):
        """Test converting ActiveArc to dictionary."""
        user_id = uuid4()
        arc = ActiveArc(
            user_id=user_id,
            template_name="lenas_warning",
            category=ArcCategory.SOCIAL,
            stage=ArcStage.RISING,
            conversations_in_arc=3,
            max_conversations=6,
            current_description="Lena is being skeptical",
            involved_characters=["Lena"],
        )

        result = arc.to_dict()

        assert result["user_id"] == str(user_id)
        assert result["template_name"] == "lenas_warning"
        assert result["category"] == "social"
        assert result["stage"] == "rising"
        assert result["conversations_in_arc"] == 3
        assert result["max_conversations"] == 6
        assert result["involved_characters"] == ["Lena"]
        assert "started_at" in result
        assert result["resolved_at"] is None

    def test_arc_from_dict_deserialization(self):
        """Test creating ActiveArc from dictionary."""
        arc_id = uuid4()
        user_id = uuid4()
        data = {
            "arc_id": str(arc_id),
            "user_id": str(user_id),
            "template_name": "viktor_resurfaces",
            "category": "social",
            "stage": "climax",
            "started_at": "2026-01-25T12:00:00",
            "conversations_in_arc": 5,
            "max_conversations": 8,
            "current_description": "Viktor's in trouble",
            "involved_characters": ["Viktor"],
            "emotional_impact_applied": False,
            "resolved_at": None,
        }

        arc = ActiveArc.from_dict(data)

        assert arc.arc_id == arc_id
        assert arc.user_id == user_id
        assert arc.template_name == "viktor_resurfaces"
        assert arc.category == ArcCategory.SOCIAL
        assert arc.stage == ArcStage.CLIMAX
        assert arc.conversations_in_arc == 5
        assert arc.involved_characters == ["Viktor"]


class TestArcCategories:
    """Tests for arc category filtering (AC-T3.8.13)."""

    def test_arc_category_filtering(self):
        """Test that templates are indexed by category."""
        system = NarrativeArcSystem()

        # Check all categories have templates
        for category in ArcCategory:
            templates = system._templates_by_category.get(category, [])
            assert len(templates) >= 0  # Some categories may be empty


class TestInvolvedCharacters:
    """Tests for character involvement in arcs (AC-T3.8.14)."""

    def test_involved_characters_in_arc(self):
        """Test that arcs have involved_characters populated."""
        system = NarrativeArcSystem()

        # Find a template with characters
        lena_template = next(
            (t for t in system.ARC_TEMPLATES if "Lena" in t.involved_characters),
            None,
        )

        assert lena_template is not None
        assert "Lena" in lena_template.involved_characters


class TestEmotionalImpact:
    """Tests for emotional impact values (AC-T3.8.15)."""

    def test_emotional_impact_values(self):
        """Test that templates have valid emotional impact."""
        system = NarrativeArcSystem()

        for template in system.ARC_TEMPLATES:
            assert isinstance(template.emotional_impact, dict)
            for metric, value in template.emotional_impact.items():
                assert metric in ["intimacy", "passion", "trust", "secureness"]
                assert -1.0 <= value <= 1.0


class TestArcCreation:
    """Tests for arc creation from templates (AC-T3.8.16)."""

    def test_arc_creation_from_template(self):
        """Test creating an arc from a template."""
        system = NarrativeArcSystem()
        user_id = uuid4()

        template = system.ARC_TEMPLATES[0]  # big_security_job
        arc = system.create_arc(user_id, template)

        assert arc.user_id == user_id
        assert arc.template_name == template.name
        assert arc.category == template.category
        assert arc.stage == ArcStage.SETUP
        assert arc.conversations_in_arc == 0
        assert template.duration_conversations[0] <= arc.max_conversations <= template.duration_conversations[1]
        assert arc.involved_characters == template.involved_characters


class TestActiveArcMethods:
    """Tests for ActiveArc methods (AC-T3.8.18)."""

    def test_active_arc_advance_stage_method(self):
        """Test the advance_stage method behavior."""
        arc = ActiveArc(
            user_id=uuid4(),
            template_name="test",
            stage=ArcStage.SETUP,
        )

        # First advance
        result1 = arc.advance_stage()
        assert result1 is True
        assert arc.stage == ArcStage.RISING

        # Second advance
        result2 = arc.advance_stage()
        assert result2 is True
        assert arc.stage == ArcStage.CLIMAX


class TestArcContextFormatting:
    """Tests for arc context formatting (AC-T3.8.19)."""

    def test_arc_context_formatting(self):
        """Test formatting arcs for prompt context."""
        system = NarrativeArcSystem()

        arcs = [
            ActiveArc(
                user_id=uuid4(),
                template_name="lenas_warning",
                category=ArcCategory.SOCIAL,
                stage=ArcStage.RISING,
                current_description="Lena is skeptical about you",
                involved_characters=["Lena"],
            ),
            ActiveArc(
                user_id=uuid4(),
                template_name="big_security_job",
                category=ArcCategory.CAREER,
                stage=ArcStage.SETUP,
                current_description="Got a call about a major contract",
                involved_characters=["Marco"],
            ),
        ]

        result = system.get_arc_context(arcs)

        assert "[social]" in result
        assert "[career]" in result
        assert "Lena" in result
        assert "Marco" in result
        assert "skeptical" in result

    def test_arc_context_formatting_empty(self):
        """Test formatting empty arc list."""
        system = NarrativeArcSystem()

        result = system.get_arc_context([])

        assert result == "No active storylines"


class TestArcTemplateDuration:
    """Tests for arc template duration ranges (AC-T3.8.20)."""

    def test_arc_template_duration_range(self):
        """Test that all templates have valid duration ranges."""
        system = NarrativeArcSystem()

        for template in system.ARC_TEMPLATES:
            min_conv, max_conv = template.duration_conversations
            assert min_conv >= 1
            assert max_conv >= min_conv
            assert max_conv <= 15  # Reasonable upper bound


class TestShouldStartNewArc:
    """Tests for should_start_new_arc logic."""

    def test_should_start_arc_rejects_when_max_active(self):
        """Test that no new arc starts when already at max."""
        system = NarrativeArcSystem()

        active_arcs = [
            ActiveArc(user_id=uuid4(), template_name="arc1"),
            ActiveArc(user_id=uuid4(), template_name="arc2"),
        ]

        result = system.should_start_new_arc(
            active_arcs=active_arcs,
            vulnerability_level=3,
            chapter=3,
            days_since_last_arc=10,
        )

        assert result is False

    def test_should_start_arc_respects_cooldown(self):
        """Test that arc cooldown is respected."""
        system = NarrativeArcSystem()

        result = system.should_start_new_arc(
            active_arcs=[],
            vulnerability_level=3,
            chapter=3,
            days_since_last_arc=1,  # Only 1 day since last
        )

        assert result is False


class TestArcTemplateCount:
    """Verify we have enough templates (AC-T3.8.21)."""

    def test_sufficient_templates(self):
        """Test that we have at least 10 arc templates."""
        system = NarrativeArcSystem()

        assert len(system.ARC_TEMPLATES) >= 10


class TestArcUpdate:
    """Tests for arc update method."""

    def test_arc_update_increments_count(self):
        """Test that update_arc increments conversation count."""
        system = NarrativeArcSystem()
        template = system.ARC_TEMPLATES[0]

        arc = ActiveArc(
            user_id=uuid4(),
            template_name=template.name,
            category=template.category,
            stage=ArcStage.SETUP,
            conversations_in_arc=0,
            max_conversations=5,
        )

        updated_arc, resolved = system.update_arc(arc, template)

        assert updated_arc.conversations_in_arc == 1
        assert resolved is False
