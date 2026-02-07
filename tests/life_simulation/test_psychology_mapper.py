"""Tests for psychology mapper (Spec 035).

Tests for event → psychological response mapping.
"""

import pytest

from nikita.life_simulation.psychology_mapper import (
    CoreWound,
    DefenseMechanism,
    PsychologicalState,
    PsychologyMapper,
    TraumaTrigger,
    get_psychology_mapper,
)


class TestPsychologyMapperSingleton:
    """Tests for psychology mapper singleton."""

    def test_get_psychology_mapper_returns_instance(self):
        """Should return PsychologyMapper instance."""
        mapper = get_psychology_mapper()
        assert isinstance(mapper, PsychologyMapper)

    def test_get_psychology_mapper_returns_same_instance(self):
        """Should return same instance on subsequent calls."""
        mapper1 = get_psychology_mapper()
        mapper2 = get_psychology_mapper()
        assert mapper1 is mapper2


class TestCoreWoundEnum:
    """Tests for CoreWound enum."""

    def test_too_much_value(self):
        """Should have correct value."""
        assert CoreWound.TOO_MUCH.value == "too_much"

    def test_conditional_love_value(self):
        """Should have correct value."""
        assert CoreWound.CONDITIONAL_LOVE.value == "conditional_love"

    def test_vulnerability_punished_value(self):
        """Should have correct value."""
        assert CoreWound.VULNERABILITY_PUNISHED.value == "vulnerability_punished"

    def test_fundamentally_broken_value(self):
        """Should have correct value."""
        assert CoreWound.FUNDAMENTALLY_BROKEN.value == "fundamentally_broken"


class TestDefenseMechanismEnum:
    """Tests for DefenseMechanism enum."""

    def test_intellectualization_value(self):
        """Should have correct value."""
        assert DefenseMechanism.INTELLECTUALIZATION.value == "intellectualization"

    def test_humor_deflection_value(self):
        """Should have correct value."""
        assert DefenseMechanism.HUMOR_DEFLECTION.value == "humor_deflection"

    def test_testing_value(self):
        """Should have correct value."""
        assert DefenseMechanism.TESTING.value == "testing"

    def test_preemptive_withdrawal_value(self):
        """Should have correct value."""
        assert DefenseMechanism.PREEMPTIVE_WITHDRAWAL.value == "preemptive_withdrawal"


class TestTraumaTriggerEnum:
    """Tests for TraumaTrigger enum."""

    def test_raised_voice_value(self):
        """Should have correct value."""
        assert TraumaTrigger.RAISED_VOICE.value == "raised_voice"

    def test_possessiveness_value(self):
        """Should have correct value."""
        assert TraumaTrigger.POSSESSIVENESS.value == "possessiveness"

    def test_abandonment_value(self):
        """Should have correct value."""
        assert TraumaTrigger.ABANDONMENT.value == "abandonment"


class TestPsychologicalState:
    """Tests for PsychologicalState dataclass."""

    def test_to_dict(self):
        """Should convert to dictionary correctly."""
        state = PsychologicalState(
            active_wounds=[CoreWound.TOO_MUCH],
            triggered_defenses=[DefenseMechanism.HUMOR_DEFLECTION],
            active_triggers=[TraumaTrigger.ABANDONMENT],
            emotional_temperature=-0.3,
            vulnerability_willingness=0.4,
            attachment_mode="anxious",
        )
        result = state.to_dict()

        assert result["active_wounds"] == ["too_much"]
        assert result["triggered_defenses"] == ["humor_deflection"]
        assert result["active_triggers"] == ["abandonment"]
        assert result["emotional_temperature"] == -0.3
        assert result["vulnerability_willingness"] == 0.4
        assert result["attachment_mode"] == "anxious"

    def test_format_for_prompt_with_defenses(self):
        """Should format defenses correctly."""
        state = PsychologicalState(
            active_wounds=[],
            triggered_defenses=[DefenseMechanism.INTELLECTUALIZATION, DefenseMechanism.HUMOR_DEFLECTION],
            active_triggers=[],
            emotional_temperature=0.0,
            vulnerability_willingness=0.5,
            attachment_mode="secure-leaning",
        )
        result = state.format_for_prompt()

        assert "intellectualizing emotions" in result["active_defenses"]
        assert "using humor to deflect" in result["active_defenses"]

    def test_format_for_prompt_with_triggers(self):
        """Should format triggers correctly."""
        state = PsychologicalState(
            active_wounds=[],
            triggered_defenses=[],
            active_triggers=[TraumaTrigger.RAISED_VOICE, TraumaTrigger.CRITICISM],
            emotional_temperature=-0.5,
            vulnerability_willingness=0.2,
            attachment_mode="avoidant",
        )
        result = state.format_for_prompt()

        assert "raised voice" in result["recent_triggers"]
        assert "criticism" in result["recent_triggers"]

    def test_format_for_prompt_with_wounds(self):
        """Should format wounds correctly."""
        state = PsychologicalState(
            active_wounds=[CoreWound.CONDITIONAL_LOVE, CoreWound.FUNDAMENTALLY_BROKEN],
            triggered_defenses=[],
            active_triggers=[],
            emotional_temperature=0.0,
            vulnerability_willingness=0.5,
            attachment_mode="secure-leaning",
        )
        result = state.format_for_prompt()

        assert "'Love must be earned' wound" in result["current_wound_state"]
        assert "'I am fundamentally broken' wound" in result["current_wound_state"]


class TestPsychologyMapperAnalyzeEvent:
    """Tests for PsychologyMapper.analyze_event()."""

    def test_analyze_event_with_viktor(self):
        """Should activate fundamentally_broken wound for Viktor."""
        mapper = get_psychology_mapper()
        state = mapper.analyze_event(
            event_type="work",
            involved_characters=["Viktor"],
            event_description="Working on project with Viktor",
        )

        assert CoreWound.FUNDAMENTALLY_BROKEN in state.active_wounds
        assert DefenseMechanism.INTELLECTUALIZATION in state.triggered_defenses

    def test_analyze_event_with_alexei(self):
        """Should activate conditional love and trigger criticism for Alexei (father)."""
        mapper = get_psychology_mapper()
        state = mapper.analyze_event(
            event_type="family",
            involved_characters=["Alexei"],
            event_description="Father called unexpectedly",
        )

        assert CoreWound.CONDITIONAL_LOVE in state.active_wounds
        assert CoreWound.FUNDAMENTALLY_BROKEN in state.active_wounds
        assert TraumaTrigger.CRITICISM in state.active_triggers

    def test_analyze_event_with_max(self):
        """Should activate trauma triggers for Max (abusive ex)."""
        mapper = get_psychology_mapper()
        state = mapper.analyze_event(
            event_type="social",
            involved_characters=["Max"],
            event_description="Max texted me",
        )

        assert CoreWound.VULNERABILITY_PUNISHED in state.active_wounds
        assert TraumaTrigger.RAISED_VOICE in state.active_triggers
        assert TraumaTrigger.POSSESSIVENESS in state.active_triggers
        assert DefenseMechanism.TESTING in state.triggered_defenses

    def test_analyze_event_with_lena(self):
        """Should have positive mood impact for Lena (supportive friend)."""
        mapper = get_psychology_mapper()
        state = mapper.analyze_event(
            event_type="social",
            involved_characters=["Lena"],
            event_description="Had coffee with Lena",
        )

        assert len(state.active_wounds) == 0
        assert len(state.active_triggers) == 0
        assert state.emotional_temperature > 0.5  # Positive

    def test_analyze_event_setback_triggers_criticism(self):
        """Should trigger criticism for setback events."""
        mapper = get_psychology_mapper()
        state = mapper.analyze_event(
            event_type="setback",
            involved_characters=[],
            event_description="Project deadline missed",
        )

        assert TraumaTrigger.CRITICISM in state.active_triggers

    def test_analyze_event_plans_cancelled_triggers_abandonment(self):
        """Should trigger abandonment for cancelled plans."""
        mapper = get_psychology_mapper()
        state = mapper.analyze_event(
            event_type="plans_cancelled",
            involved_characters=[],
            event_description="Friend cancelled our plans",
        )

        assert TraumaTrigger.ABANDONMENT in state.active_triggers
        assert state.attachment_mode == "anxious"


class TestPsychologyMapperAnalyzeUserBehavior:
    """Tests for PsychologyMapper.analyze_user_behavior()."""

    def test_analyze_user_behavior_raised_voice(self):
        """Should trigger raised voice response."""
        mapper = get_psychology_mapper()
        state = mapper.analyze_user_behavior(
            behavior_type="raised_voice",
            intensity=0.8,
        )

        assert TraumaTrigger.RAISED_VOICE in state.active_triggers
        assert CoreWound.VULNERABILITY_PUNISHED in state.active_wounds
        assert state.attachment_mode == "avoidant"

    def test_analyze_user_behavior_jealousy(self):
        """Should trigger possessiveness response."""
        mapper = get_psychology_mapper()
        state = mapper.analyze_user_behavior(
            behavior_type="jealousy",
            intensity=0.6,
        )

        assert TraumaTrigger.POSSESSIVENESS in state.active_triggers
        assert state.attachment_mode == "avoidant"

    def test_analyze_user_behavior_went_silent(self):
        """Should trigger abandonment response."""
        mapper = get_psychology_mapper()
        state = mapper.analyze_user_behavior(
            behavior_type="went_silent",
            intensity=0.7,
        )

        assert TraumaTrigger.ABANDONMENT in state.active_triggers
        assert CoreWound.TOO_MUCH in state.active_wounds
        assert state.attachment_mode == "anxious"

    def test_analyze_user_behavior_high_intensity_activates_defenses(self):
        """Should activate more defenses at high intensity."""
        mapper = get_psychology_mapper()
        state = mapper.analyze_user_behavior(
            behavior_type="raised_voice",
            intensity=0.9,
        )

        assert len(state.triggered_defenses) >= 1
        assert DefenseMechanism.TESTING in state.triggered_defenses or DefenseMechanism.PREEMPTIVE_WITHDRAWAL in state.triggered_defenses

    def test_analyze_user_behavior_low_intensity(self):
        """Should have minimal defenses at low intensity."""
        mapper = get_psychology_mapper()
        state = mapper.analyze_user_behavior(
            behavior_type="criticism",
            intensity=0.3,
        )

        assert len(state.triggered_defenses) == 0


class TestPsychologyMapperGetHealingResponse:
    """Tests for PsychologyMapper.get_healing_response()."""

    def test_get_healing_response_raised_voice_handled_well(self):
        """Should return positive response when raised voice handled well."""
        mapper = get_psychology_mapper()
        response = mapper.get_healing_response(
            trigger=TraumaTrigger.RAISED_VOICE,
            user_handled_well=True,
        )

        assert response["mood_shift"] == "cautiously relieved"
        assert "Max" in response["behavior"]  # References past

    def test_get_healing_response_abandonment_handled_well(self):
        """Should return positive response when abandonment handled well."""
        mapper = get_psychology_mapper()
        response = mapper.get_healing_response(
            trigger=TraumaTrigger.ABANDONMENT,
            user_handled_well=True,
        )

        assert response["mood_shift"] == "relief with residual wariness"
        assert "data point" in response["behavior"]

    def test_get_healing_response_not_handled_well(self):
        """Should return guarded response when not handled well."""
        mapper = get_psychology_mapper()
        response = mapper.get_healing_response(
            trigger=TraumaTrigger.CRITICISM,
            user_handled_well=False,
        )

        assert response["mood_shift"] == "guarded"
        assert "shorter responses" in response["behavior"]
        assert "sarcasm" in response["behavior"]
