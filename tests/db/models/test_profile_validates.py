"""Tests for OnboardingState.collected_answers ORM-level validator.

T026: @validates collected_answers — Spec 212 PR D, FR-014.

Note: validate_city enforces structural rules (junk-word blocklist, length,
control chars, purely-numeric). Chat-like free text ("hey what's up?") that
passes those structural rules will be accepted here; semantic filtering is the
API layer's job. These tests verify that the ORM validator fires and delegates
to validate_city correctly.
"""

import pytest
from sqlalchemy.orm import configure_mappers

from nikita.db.models.profile import OnboardingState


@pytest.fixture(autouse=True)
def ensure_mappers():
    """Ensure SQLAlchemy mapper instrumentation is fully configured.

    configure_mappers() is normally called at app startup (engine creation).
    In unit tests that instantiate models without touching the engine, calling
    it explicitly ensures @validates event listeners are wired to the
    instrumented attributes.
    """
    configure_mappers()


class TestCollectedAnswersValidation:
    def test_rejects_blocklisted_city(self):
        """ORM validator rejects junk-word city names via validate_city."""
        state = OnboardingState()
        with pytest.raises(ValueError, match="city"):
            # "n/a" is in validate_city's _JUNK_WORDS blocklist
            state.collected_answers = {"location_city": "n/a"}

    def test_rejects_single_char_city(self):
        """ORM validator rejects too-short city names (< 2 chars)."""
        state = OnboardingState()
        with pytest.raises(ValueError, match="(?i)city"):
            state.collected_answers = {"location_city": "x"}

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
