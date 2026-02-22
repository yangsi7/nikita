"""Tests for Gottman ratio tracker (Spec 057, T5).

Tests cover:
- Interaction recording (positive/negative)
- Ratio calculation (including edge cases)
- Target ratios (conflict vs normal)
- Below/above target detection
- Temperature delta calculation
- Window pruning
- Session reset
- History initialization
"""

import pytest
from datetime import UTC, datetime, timedelta

from nikita.conflicts.gottman import GottmanTracker
from nikita.conflicts.models import ConflictDetails, GottmanCounters


class TestRecordInteraction:
    """Test recording positive/negative interactions."""

    def test_record_positive(self):
        counters = GottmanCounters()
        result = GottmanTracker.record_interaction(counters, is_positive=True)
        assert result.positive_count == 1
        assert result.negative_count == 0
        assert result.session_positive == 1
        assert result.session_negative == 0

    def test_record_negative(self):
        counters = GottmanCounters()
        result = GottmanTracker.record_interaction(counters, is_positive=False)
        assert result.positive_count == 0
        assert result.negative_count == 1
        assert result.session_positive == 0
        assert result.session_negative == 1

    def test_accumulates(self):
        counters = GottmanCounters(positive_count=5, negative_count=1)
        result = GottmanTracker.record_interaction(counters, is_positive=True)
        assert result.positive_count == 6
        assert result.negative_count == 1


class TestGetRatio:
    """Test ratio calculation."""

    def test_normal_ratio(self):
        counters = GottmanCounters(positive_count=10, negative_count=2)
        assert GottmanTracker.get_ratio(counters) == 5.0

    def test_zero_negatives_with_positives(self):
        counters = GottmanCounters(positive_count=5, negative_count=0)
        assert GottmanTracker.get_ratio(counters) == float("inf")

    def test_zero_both(self):
        counters = GottmanCounters(positive_count=0, negative_count=0)
        assert GottmanTracker.get_ratio(counters) == 0.0

    def test_more_negatives(self):
        counters = GottmanCounters(positive_count=1, negative_count=5)
        assert GottmanTracker.get_ratio(counters) == 0.2


class TestGetTarget:
    """Test target ratio selection."""

    def test_conflict_target(self):
        assert GottmanTracker.get_target(is_in_conflict=True) == 5.0

    def test_normal_target(self):
        assert GottmanTracker.get_target(is_in_conflict=False) == 20.0


class TestIsBelowTarget:
    """Test below-target detection."""

    def test_below_conflict_target(self):
        counters = GottmanCounters(positive_count=3, negative_count=1)
        # Ratio = 3.0 < 5.0
        assert GottmanTracker.is_below_target(counters, is_in_conflict=True) is True

    def test_above_conflict_target(self):
        counters = GottmanCounters(positive_count=10, negative_count=1)
        # Ratio = 10.0 > 5.0
        assert GottmanTracker.is_below_target(counters, is_in_conflict=True) is False

    def test_below_normal_target(self):
        counters = GottmanCounters(positive_count=10, negative_count=1)
        # Ratio = 10.0 < 20.0
        assert GottmanTracker.is_below_target(counters, is_in_conflict=False) is True

    def test_infinity_always_above(self):
        counters = GottmanCounters(positive_count=5, negative_count=0)
        assert GottmanTracker.is_below_target(counters, is_in_conflict=True) is False
        assert GottmanTracker.is_below_target(counters, is_in_conflict=False) is False

    def test_empty_counters_not_below(self):
        counters = GottmanCounters()
        assert GottmanTracker.is_below_target(counters, is_in_conflict=False) is False


class TestTemperatureDelta:
    """Test temperature delta from Gottman ratio."""

    def test_below_target_positive_delta(self):
        counters = GottmanCounters(positive_count=2, negative_count=1)
        # Ratio = 2.0, target = 5.0 (conflict)
        delta = GottmanTracker.calculate_temperature_delta(counters, is_in_conflict=True)
        assert delta > 0
        assert 2.0 <= delta <= 5.0

    def test_above_target_negative_delta(self):
        counters = GottmanCounters(positive_count=30, negative_count=1)
        # Ratio = 30.0, target = 20.0 (normal)
        delta = GottmanTracker.calculate_temperature_delta(counters, is_in_conflict=False)
        assert delta < 0

    def test_empty_counters_zero_delta(self):
        counters = GottmanCounters()
        delta = GottmanTracker.calculate_temperature_delta(counters, is_in_conflict=False)
        assert delta == 0.0

    def test_infinity_ratio_negative_delta(self):
        counters = GottmanCounters(positive_count=5, negative_count=0)
        delta = GottmanTracker.calculate_temperature_delta(counters, is_in_conflict=True)
        assert delta < 0


class TestPruneWindow:
    """Test rolling window pruning."""

    def test_expired_window_resets_counters(self):
        old_start = datetime.now(UTC) - timedelta(days=10)
        counters = GottmanCounters(
            positive_count=10, negative_count=2,
            session_positive=3, session_negative=1,
            window_start=old_start,
        )
        pruned = GottmanTracker.prune_window(counters)
        assert pruned.positive_count == 0
        assert pruned.negative_count == 0
        # Session preserved
        assert pruned.session_positive == 3
        assert pruned.session_negative == 1

    def test_active_window_unchanged(self):
        recent_start = datetime.now(UTC) - timedelta(days=3)
        counters = GottmanCounters(
            positive_count=10, negative_count=2,
            window_start=recent_start,
        )
        pruned = GottmanTracker.prune_window(counters)
        assert pruned.positive_count == 10
        assert pruned.negative_count == 2

    def test_custom_window_days(self):
        old_start = datetime.now(UTC) - timedelta(days=4)
        counters = GottmanCounters(
            positive_count=5, negative_count=1,
            window_start=old_start,
        )
        # Default 7 days: not expired
        assert GottmanTracker.prune_window(counters, window_days=7).positive_count == 5
        # Custom 3 days: expired
        assert GottmanTracker.prune_window(counters, window_days=3).positive_count == 0


class TestResetSession:
    """Test session counter reset."""

    def test_reset_preserves_rolling(self):
        counters = GottmanCounters(
            positive_count=10, negative_count=2,
            session_positive=3, session_negative=1,
        )
        reset = GottmanTracker.reset_session(counters)
        assert reset.positive_count == 10
        assert reset.negative_count == 2
        assert reset.session_positive == 0
        assert reset.session_negative == 0


class TestInitializeFromHistory:
    """Test bootstrapping from score_history entries."""

    def test_positive_and_negative(self):
        entries = [
            {"delta": "2.5"},
            {"delta": "-1.0"},
            {"delta": "3.0"},
            {"delta": "-0.5"},
            {"delta": "1.0"},
        ]
        counters = GottmanTracker.initialize_from_history(entries)
        assert counters.positive_count == 3
        assert counters.negative_count == 2

    def test_empty_history(self):
        counters = GottmanTracker.initialize_from_history([])
        assert counters.positive_count == 0
        assert counters.negative_count == 0

    def test_invalid_entries_skipped(self):
        entries = [
            {"delta": "invalid"},
            {"delta": "2.0"},
            {"other": "field"},
        ]
        counters = GottmanTracker.initialize_from_history(entries)
        assert counters.positive_count == 1
        assert counters.negative_count == 0

    def test_zero_delta_ignored(self):
        entries = [{"delta": "0"}, {"delta": "0.0"}]
        counters = GottmanTracker.initialize_from_history(entries)
        assert counters.positive_count == 0
        assert counters.negative_count == 0


class TestUpdateConflictDetails:
    """Test updating conflict details with Gottman interaction."""

    def test_positive_interaction(self):
        details = ConflictDetails(positive_count=5, negative_count=1)
        updated = GottmanTracker.update_conflict_details(
            details, is_positive=True, is_in_conflict=False,
        )
        assert updated.positive_count == 6
        assert updated.negative_count == 1
        assert updated.gottman_target == 20.0

    def test_negative_interaction_in_conflict(self):
        details = ConflictDetails(positive_count=5, negative_count=1)
        updated = GottmanTracker.update_conflict_details(
            details, is_positive=False, is_in_conflict=True,
        )
        assert updated.positive_count == 5
        assert updated.negative_count == 2
        assert updated.gottman_target == 5.0

    def test_preserves_temperature(self):
        details = ConflictDetails(temperature=60.0, zone="hot")
        updated = GottmanTracker.update_conflict_details(
            details, is_positive=True, is_in_conflict=False,
        )
        assert updated.temperature == 60.0
        assert updated.zone == "hot"
