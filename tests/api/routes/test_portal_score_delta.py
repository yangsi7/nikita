"""Tests for _compute_score_delta helper in portal routes (GH #153)."""

import pytest

from nikita.api.routes.portal import _compute_score_delta


class FakeEntry:
    """Minimal stand-in for a score_history row."""

    def __init__(self, score: float):
        self.score = score


class TestComputeScoreDelta:
    """Unit tests for the _compute_score_delta helper."""

    def test_direct_delta(self):
        """Conversation scoring stores delta directly."""
        entry = FakeEntry(55.0)
        assert _compute_score_delta(entry, {"delta": "2.5"}) == 2.5

    def test_delta_from_score_before(self):
        """Boss events store score_before."""
        entry = FakeEntry(55.0)
        assert _compute_score_delta(entry, {"score_before": "50.0"}) == 5.0

    def test_delta_from_old_score(self):
        """Voice scoring stores old_score."""
        entry = FakeEntry(60.0)
        assert _compute_score_delta(entry, {"old_score": "55.0"}) == 5.0

    def test_delta_from_decay_amount(self):
        """Decay events store decay_amount (positive value, delta is negative)."""
        entry = FakeEntry(49.5)
        assert _compute_score_delta(entry, {"decay_amount": "0.5"}) == -0.5

    def test_empty_details_returns_none(self):
        """No recognizable keys → None."""
        entry = FakeEntry(50.0)
        assert _compute_score_delta(entry, {}) is None

    def test_direct_delta_zero(self):
        """Zero delta should return 0.0, not None."""
        entry = FakeEntry(50.0)
        assert _compute_score_delta(entry, {"delta": "0"}) == 0.0

    def test_direct_delta_negative(self):
        """Negative delta from conversation scoring."""
        entry = FakeEntry(48.0)
        assert _compute_score_delta(entry, {"delta": "-1.5"}) == -1.5

    def test_decay_amount_zero(self):
        """Zero decay should return -0.0 (or 0.0)."""
        entry = FakeEntry(50.0)
        result = _compute_score_delta(entry, {"decay_amount": "0"})
        assert result == 0.0

    def test_invalid_delta_string(self):
        """Non-numeric delta string returns None."""
        entry = FakeEntry(50.0)
        assert _compute_score_delta(entry, {"delta": "not-a-number"}) is None

    def test_priority_delta_over_score_before(self):
        """Direct delta takes priority when both delta and score_before present."""
        entry = FakeEntry(55.0)
        result = _compute_score_delta(entry, {"delta": "3.0", "score_before": "50.0"})
        assert result == 3.0
