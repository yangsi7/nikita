"""Tests for Spec 056 PsycheState Pydantic model (Phase 1: T1, T5).

TDD: Write failing tests FIRST. These test the PsycheState model with
8 validated fields, default state, JSON round-trip, and feature flag.

AC refs: AC-2.1, AC-2.2, AC-2.3, AC-2.4, AC-6.6
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from nikita.agents.psyche.models import PsycheState


# ============================================================================
# AC-2.1: Model fields - 8 fields with correct types
# ============================================================================


class TestPsycheStateFields:
    """AC-2.1: PsycheState has 8 validated fields."""

    def test_valid_state_all_fields(self):
        """Valid PsycheState with all 8 fields populated."""
        state = PsycheState(
            attachment_activation="secure",
            defense_mode="open",
            behavioral_guidance="Be warm and encouraging with this user.",
            internal_monologue="I feel safe with this person.",
            vulnerability_level=0.7,
            emotional_tone="warm",
            topics_to_encourage=["family", "dreams"],
            topics_to_avoid=["ex"],
        )
        assert state.attachment_activation == "secure"
        assert state.defense_mode == "open"
        assert state.behavioral_guidance == "Be warm and encouraging with this user."
        assert state.internal_monologue == "I feel safe with this person."
        assert state.vulnerability_level == 0.7
        assert state.emotional_tone == "warm"
        assert state.topics_to_encourage == ["family", "dreams"]
        assert state.topics_to_avoid == ["ex"]

    def test_has_exactly_eight_fields(self):
        """PsycheState model has exactly 8 fields."""
        assert len(PsycheState.model_fields) == 8

    def test_field_names(self):
        """All 8 expected field names present."""
        expected = {
            "attachment_activation",
            "defense_mode",
            "behavioral_guidance",
            "internal_monologue",
            "vulnerability_level",
            "emotional_tone",
            "topics_to_encourage",
            "topics_to_avoid",
        }
        assert set(PsycheState.model_fields.keys()) == expected


# ============================================================================
# AC-2.2: Field validation
# ============================================================================


class TestAttachmentActivation:
    """Attachment activation: Literal enum validation."""

    @pytest.mark.parametrize(
        "value",
        ["secure", "anxious", "avoidant", "disorganized"],
    )
    def test_valid_values(self, value: str):
        state = PsycheState(
            attachment_activation=value,
            defense_mode="open",
            behavioral_guidance="guidance",
            internal_monologue="thoughts",
            vulnerability_level=0.5,
            emotional_tone="warm",
            topics_to_encourage=[],
            topics_to_avoid=[],
        )
        assert state.attachment_activation == value

    def test_invalid_value_rejected(self):
        with pytest.raises(ValidationError):
            PsycheState(
                attachment_activation="invalid",
                defense_mode="open",
                behavioral_guidance="guidance",
                internal_monologue="thoughts",
                vulnerability_level=0.5,
                emotional_tone="warm",
                topics_to_encourage=[],
                topics_to_avoid=[],
            )


class TestDefenseMode:
    """Defense mode: Literal enum validation."""

    @pytest.mark.parametrize(
        "value",
        ["open", "guarded", "deflecting", "withdrawing"],
    )
    def test_valid_values(self, value: str):
        state = PsycheState(
            attachment_activation="secure",
            defense_mode=value,
            behavioral_guidance="guidance",
            internal_monologue="thoughts",
            vulnerability_level=0.5,
            emotional_tone="warm",
            topics_to_encourage=[],
            topics_to_avoid=[],
        )
        assert state.defense_mode == value

    def test_invalid_value_rejected(self):
        with pytest.raises(ValidationError):
            PsycheState(
                attachment_activation="secure",
                defense_mode="aggressive",
                behavioral_guidance="guidance",
                internal_monologue="thoughts",
                vulnerability_level=0.5,
                emotional_tone="warm",
                topics_to_encourage=[],
                topics_to_avoid=[],
            )


class TestEmotionalTone:
    """Emotional tone: Literal enum validation."""

    @pytest.mark.parametrize(
        "value",
        ["playful", "serious", "warm", "distant", "volatile"],
    )
    def test_valid_values(self, value: str):
        state = PsycheState(
            attachment_activation="secure",
            defense_mode="open",
            behavioral_guidance="guidance",
            internal_monologue="thoughts",
            vulnerability_level=0.5,
            emotional_tone=value,
            topics_to_encourage=[],
            topics_to_avoid=[],
        )
        assert state.emotional_tone == value

    def test_invalid_value_rejected(self):
        with pytest.raises(ValidationError):
            PsycheState(
                attachment_activation="secure",
                defense_mode="open",
                behavioral_guidance="guidance",
                internal_monologue="thoughts",
                vulnerability_level=0.5,
                emotional_tone="angry",
                topics_to_encourage=[],
                topics_to_avoid=[],
            )


class TestVulnerabilityLevel:
    """Vulnerability level: float bounded 0.0-1.0."""

    def test_minimum_bound(self):
        state = PsycheState(
            attachment_activation="secure",
            defense_mode="open",
            behavioral_guidance="guidance",
            internal_monologue="thoughts",
            vulnerability_level=0.0,
            emotional_tone="warm",
            topics_to_encourage=[],
            topics_to_avoid=[],
        )
        assert state.vulnerability_level == 0.0

    def test_maximum_bound(self):
        state = PsycheState(
            attachment_activation="secure",
            defense_mode="open",
            behavioral_guidance="guidance",
            internal_monologue="thoughts",
            vulnerability_level=1.0,
            emotional_tone="warm",
            topics_to_encourage=[],
            topics_to_avoid=[],
        )
        assert state.vulnerability_level == 1.0

    def test_below_minimum_rejected(self):
        with pytest.raises(ValidationError):
            PsycheState(
                attachment_activation="secure",
                defense_mode="open",
                behavioral_guidance="guidance",
                internal_monologue="thoughts",
                vulnerability_level=-0.1,
                emotional_tone="warm",
                topics_to_encourage=[],
                topics_to_avoid=[],
            )

    def test_above_maximum_rejected(self):
        with pytest.raises(ValidationError):
            PsycheState(
                attachment_activation="secure",
                defense_mode="open",
                behavioral_guidance="guidance",
                internal_monologue="thoughts",
                vulnerability_level=1.1,
                emotional_tone="warm",
                topics_to_encourage=[],
                topics_to_avoid=[],
            )

    def test_midrange_value(self):
        state = PsycheState(
            attachment_activation="secure",
            defense_mode="open",
            behavioral_guidance="guidance",
            internal_monologue="thoughts",
            vulnerability_level=0.42,
            emotional_tone="warm",
            topics_to_encourage=[],
            topics_to_avoid=[],
        )
        assert state.vulnerability_level == pytest.approx(0.42)


class TestTopicLists:
    """Topics lists: max_length=3 validation."""

    def test_empty_lists_valid(self):
        state = PsycheState(
            attachment_activation="secure",
            defense_mode="open",
            behavioral_guidance="guidance",
            internal_monologue="thoughts",
            vulnerability_level=0.5,
            emotional_tone="warm",
            topics_to_encourage=[],
            topics_to_avoid=[],
        )
        assert state.topics_to_encourage == []
        assert state.topics_to_avoid == []

    def test_max_three_encourage(self):
        state = PsycheState(
            attachment_activation="secure",
            defense_mode="open",
            behavioral_guidance="guidance",
            internal_monologue="thoughts",
            vulnerability_level=0.5,
            emotional_tone="warm",
            topics_to_encourage=["a", "b", "c"],
            topics_to_avoid=[],
        )
        assert len(state.topics_to_encourage) == 3

    def test_more_than_three_encourage_rejected(self):
        with pytest.raises(ValidationError):
            PsycheState(
                attachment_activation="secure",
                defense_mode="open",
                behavioral_guidance="guidance",
                internal_monologue="thoughts",
                vulnerability_level=0.5,
                emotional_tone="warm",
                topics_to_encourage=["a", "b", "c", "d"],
                topics_to_avoid=[],
            )

    def test_more_than_three_avoid_rejected(self):
        with pytest.raises(ValidationError):
            PsycheState(
                attachment_activation="secure",
                defense_mode="open",
                behavioral_guidance="guidance",
                internal_monologue="thoughts",
                vulnerability_level=0.5,
                emotional_tone="warm",
                topics_to_encourage=[],
                topics_to_avoid=["a", "b", "c", "d"],
            )


class TestBehavioralGuidanceAndMonologue:
    """String fields must be non-empty."""

    def test_empty_behavioral_guidance_rejected(self):
        with pytest.raises(ValidationError):
            PsycheState(
                attachment_activation="secure",
                defense_mode="open",
                behavioral_guidance="",
                internal_monologue="thoughts",
                vulnerability_level=0.5,
                emotional_tone="warm",
                topics_to_encourage=[],
                topics_to_avoid=[],
            )

    def test_empty_internal_monologue_rejected(self):
        with pytest.raises(ValidationError):
            PsycheState(
                attachment_activation="secure",
                defense_mode="open",
                behavioral_guidance="guidance",
                internal_monologue="",
                vulnerability_level=0.5,
                emotional_tone="warm",
                topics_to_encourage=[],
                topics_to_avoid=[],
            )


# ============================================================================
# AC-2.3: JSON round-trip (JSONB serialization)
# ============================================================================


class TestJsonRoundTrip:
    """AC-2.3: PsycheState serializes to/from JSONB cleanly."""

    def test_model_dump_json_roundtrip(self):
        state = PsycheState(
            attachment_activation="anxious",
            defense_mode="guarded",
            behavioral_guidance="Tread carefully, user is testing boundaries.",
            internal_monologue="I am not sure if I trust them yet.",
            vulnerability_level=0.3,
            emotional_tone="distant",
            topics_to_encourage=["career"],
            topics_to_avoid=["past relationships", "money"],
        )
        json_str = state.model_dump_json()
        restored = PsycheState.model_validate_json(json_str)
        assert restored == state

    def test_model_dump_dict_roundtrip(self):
        state = PsycheState(
            attachment_activation="secure",
            defense_mode="open",
            behavioral_guidance="Be open and warm.",
            internal_monologue="This feels nice.",
            vulnerability_level=0.8,
            emotional_tone="playful",
            topics_to_encourage=["travel", "music"],
            topics_to_avoid=[],
        )
        d = state.model_dump()
        restored = PsycheState.model_validate(d)
        assert restored == state

    def test_serialized_dict_is_json_safe(self):
        """model_dump(mode='json') produces JSON-serializable dict."""
        state = PsycheState(
            attachment_activation="disorganized",
            defense_mode="withdrawing",
            behavioral_guidance="Allow space but stay present.",
            internal_monologue="Everything feels chaotic.",
            vulnerability_level=0.1,
            emotional_tone="volatile",
            topics_to_encourage=["self-care"],
            topics_to_avoid=["family drama"],
        )
        d = state.model_dump(mode="json")
        # Should be JSON-serializable without errors
        json_str = json.dumps(d)
        assert isinstance(json_str, str)
        # And parseable back
        parsed = json.loads(json_str)
        restored = PsycheState.model_validate(parsed)
        assert restored == state


# ============================================================================
# AC-2.4: Default state for first-time users
# ============================================================================


class TestDefaultState:
    """AC-2.4: Default state exists for first-time users."""

    def test_default_classmethod_exists(self):
        assert hasattr(PsycheState, "default")
        assert callable(PsycheState.default)

    def test_default_returns_valid_state(self):
        state = PsycheState.default()
        assert isinstance(state, PsycheState)

    def test_default_has_all_fields_populated(self):
        state = PsycheState.default()
        assert state.attachment_activation in ("secure", "anxious", "avoidant", "disorganized")
        assert state.defense_mode in ("open", "guarded", "deflecting", "withdrawing")
        assert len(state.behavioral_guidance) > 0
        assert len(state.internal_monologue) > 0
        assert 0.0 <= state.vulnerability_level <= 1.0
        assert state.emotional_tone in ("playful", "serious", "warm", "distant", "volatile")
        assert isinstance(state.topics_to_encourage, list)
        assert isinstance(state.topics_to_avoid, list)

    def test_default_is_safe_neutral_state(self):
        """Default state should be neutral/safe for first-time user."""
        state = PsycheState.default()
        # First-time user: secure attachment, open disposition
        assert state.attachment_activation == "secure"
        assert state.defense_mode == "open"
        # Vulnerability should be low-medium for new user
        assert state.vulnerability_level <= 0.5

    def test_default_json_roundtrip(self):
        state = PsycheState.default()
        json_str = state.model_dump_json()
        restored = PsycheState.model_validate_json(json_str)
        assert restored == state


# ============================================================================
# AC-6.6: Feature flag convenience function
# ============================================================================


class TestFeatureFlag:
    """AC-6.6: is_psyche_agent_enabled gate."""

    def test_convenience_function_exists(self):
        from nikita.agents.psyche import is_psyche_agent_enabled

        assert callable(is_psyche_agent_enabled)

    def test_flag_defaults_off(self):
        from unittest.mock import patch

        from nikita.agents.psyche import is_psyche_agent_enabled

        with patch("nikita.config.settings.get_settings") as mock_settings:
            mock_settings.return_value.psyche_agent_enabled = False
            assert is_psyche_agent_enabled() is False

    def test_flag_respects_on(self):
        from unittest.mock import patch

        from nikita.agents.psyche import is_psyche_agent_enabled

        with patch("nikita.config.settings.get_settings") as mock_settings:
            mock_settings.return_value.psyche_agent_enabled = True
            assert is_psyche_agent_enabled() is True
