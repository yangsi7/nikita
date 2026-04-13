"""Tests for OnboardingState.collected_answers ORM-level validator.

T026: @validates collected_answers — Spec 212 PR D, FR-014.
"""

import pytest
from nikita.db.models.profile import OnboardingState


class TestCollectedAnswersValidation:
    def test_rejects_free_text_city(self):
        """ORM validator rejects chat text stored as location_city."""
        state = OnboardingState()
        with pytest.raises(ValueError, match="city"):
            state.collected_answers = {"location_city": "hey, so what's your deal?"}

    def test_accepts_valid_city(self):
        """ORM validator passes valid city names."""
        state = OnboardingState()
        state.collected_answers = {"location_city": "Zurich"}
        assert state.collected_answers["location_city"] == "Zurich"

    def test_accepts_empty_answers(self):
        """Empty dict passes (no keys to validate)."""
        state = OnboardingState()
        state.collected_answers = {}
        assert state.collected_answers == {}

    def test_accepts_unknown_keys(self):
        """Unknown keys pass through (validator only checks known keys)."""
        state = OnboardingState()
        state.collected_answers = {"favorite_color": "blue"}
        assert state.collected_answers["favorite_color"] == "blue"
