"""Adversarial tests for GottmanTracker (Spec 057).

Targets zero/zero ratio, infinity handling, large counters,
session vs rolling mismatch, malformed history, window pruning
edge cases, and temperature delta calculations at extremes.
"""

import math
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from nikita.conflicts.gottman import GottmanTracker
from nikita.conflicts.models import ConflictDetails, GottmanCounters


# ---------------------------------------------------------------------------
# 1. Zero/zero ratio (the "nothing happened" case)
# ---------------------------------------------------------------------------


class TestGottmanZeroZeroAdversarial:
    """0 positive + 0 negative: the degenerate base case."""

    def test_ratio_is_zero(self):
        """0/0 ratio should be 0.0 (not NaN, not infinity)."""
        counters = GottmanCounters(positive_count=0, negative_count=0)
        ratio = GottmanTracker.get_ratio(counters)
        assert ratio == 0.0
        assert not math.isnan(ratio)

    def test_not_below_target_conflict(self):
        """0/0 should NOT be considered below target (it's neutral)."""
        counters = GottmanCounters(positive_count=0, negative_count=0)
        assert GottmanTracker.is_below_target(counters, is_in_conflict=True) is False

    def test_not_below_target_normal(self):
        """0/0 should NOT be considered below target in normal mode either."""
        counters = GottmanCounters(positive_count=0, negative_count=0)
        assert GottmanTracker.is_below_target(counters, is_in_conflict=False) is False

    def test_temperature_delta_is_zero(self):
        """0/0 should produce 0.0 temperature delta (no data = no signal)."""
        counters = GottmanCounters(positive_count=0, negative_count=0)
        delta = GottmanTracker.calculate_temperature_delta(counters, is_in_conflict=True)
        assert delta == 0.0

    def test_temperature_delta_normal_is_zero(self):
        """0/0 in normal mode should also produce 0.0."""
        counters = GottmanCounters(positive_count=0, negative_count=0)
        delta = GottmanTracker.calculate_temperature_delta(counters, is_in_conflict=False)
        assert delta == 0.0


# ---------------------------------------------------------------------------
# 2. Infinity ratio (all positive, no negative)
# ---------------------------------------------------------------------------


class TestGottmanInfinityAdversarial:
    """N positive + 0 negative: ratio = infinity."""

    def test_ratio_is_inf(self):
        """N/0 should be float('inf')."""
        counters = GottmanCounters(positive_count=10, negative_count=0)
        ratio = GottmanTracker.get_ratio(counters)
        assert ratio == float("inf")

    def test_1_pos_0_neg_is_inf(self):
        """Even 1/0 should be inf."""
        counters = GottmanCounters(positive_count=1, negative_count=0)
        assert GottmanTracker.get_ratio(counters) == float("inf")

    def test_inf_not_below_target_conflict(self):
        """Infinity is always above any target."""
        counters = GottmanCounters(positive_count=5, negative_count=0)
        assert GottmanTracker.is_below_target(counters, is_in_conflict=True) is False

    def test_inf_not_below_target_normal(self):
        """Infinity above 20.0 target too."""
        counters = GottmanCounters(positive_count=5, negative_count=0)
        assert GottmanTracker.is_below_target(counters, is_in_conflict=False) is False

    def test_inf_temperature_delta(self):
        """Infinity ratio should produce -1.0 delta (ABOVE_TARGET_DELTA_MIN)."""
        counters = GottmanCounters(positive_count=5, negative_count=0)
        delta = GottmanTracker.calculate_temperature_delta(counters, is_in_conflict=True)
        assert delta == -1.0

    def test_update_conflict_details_inf_stored_as_999(self):
        """When ratio is inf, update_conflict_details should store 999.0 (not 'inf' string).
        This is critical for JSONB serialization."""
        details = ConflictDetails(
            temperature=50.0,
            zone="warm",
            positive_count=9,
            negative_count=0,
        )
        # Adding another positive: 10/0 = inf → stored as 999.0
        result = GottmanTracker.update_conflict_details(details, is_positive=True, is_in_conflict=True)
        assert result.gottman_ratio == 999.0
        assert not math.isinf(result.gottman_ratio), "inf leaked into stored ratio"

    def test_update_conflict_details_inf_negative_interaction(self):
        """Adding negative to 10/0 makes it 10/1 = 10.0 (no longer inf)."""
        details = ConflictDetails(
            temperature=50.0,
            zone="warm",
            positive_count=10,
            negative_count=0,
        )
        result = GottmanTracker.update_conflict_details(details, is_positive=False, is_in_conflict=True)
        assert result.gottman_ratio == 10.0
        assert result.negative_count == 1


# ---------------------------------------------------------------------------
# 3. Large counters
# ---------------------------------------------------------------------------


class TestGottmanLargeCountersAdversarial:
    """Very large counter values — potential overflow or precision issues."""

    def test_million_positive_one_negative(self):
        """1,000,000 / 1 = 1,000,000.0"""
        counters = GottmanCounters(positive_count=1_000_000, negative_count=1)
        ratio = GottmanTracker.get_ratio(counters)
        assert ratio == 1_000_000.0

    def test_million_million(self):
        """1,000,000 / 1,000,000 = 1.0"""
        counters = GottmanCounters(positive_count=1_000_000, negative_count=1_000_000)
        ratio = GottmanTracker.get_ratio(counters)
        assert ratio == 1.0

    def test_one_positive_million_negative(self):
        """1 / 1,000,000 = 0.000001 — far below any target."""
        counters = GottmanCounters(positive_count=1, negative_count=1_000_000)
        ratio = GottmanTracker.get_ratio(counters)
        assert ratio == pytest.approx(1e-6)
        assert GottmanTracker.is_below_target(counters, is_in_conflict=True) is True

    def test_large_counters_temperature_delta_bounded(self):
        """Even with extreme ratio, delta should be in [-2, 5] range."""
        counters = GottmanCounters(positive_count=1_000_000, negative_count=1)
        delta = GottmanTracker.calculate_temperature_delta(counters, is_in_conflict=True)
        # Ratio = 1M >> 5.0 target, so surplus capped at 1.0
        # delta = -1.0 + (-2.0 - (-1.0)) * min(1.0, ...) = -1.0 + (-1.0)*1.0 = -2.0
        assert -2.0 <= delta <= 5.0, f"Delta out of expected range: {delta}"


# ---------------------------------------------------------------------------
# 4. Session vs rolling mismatch
# ---------------------------------------------------------------------------


class TestGottmanSessionRollingMismatch:
    """Session counters can diverge significantly from rolling counters."""

    def test_high_session_low_rolling(self):
        """Session has many positives but rolling is nearly empty."""
        counters = GottmanCounters(
            positive_count=2,
            negative_count=1,
            session_positive=100,
            session_negative=0,
        )
        # Ratio uses rolling counts (positive_count / negative_count)
        ratio = GottmanTracker.get_ratio(counters)
        assert ratio == 2.0  # Based on rolling, not session

    def test_reset_session_preserves_rolling(self):
        """reset_session should zero session but keep rolling counters intact."""
        counters = GottmanCounters(
            positive_count=50,
            negative_count=10,
            session_positive=20,
            session_negative=5,
        )
        result = GottmanTracker.reset_session(counters)
        assert result.positive_count == 50
        assert result.negative_count == 10
        assert result.session_positive == 0
        assert result.session_negative == 0

    def test_record_interaction_increments_both(self):
        """record_interaction should increment both rolling and session."""
        counters = GottmanCounters(
            positive_count=5,
            negative_count=2,
            session_positive=1,
            session_negative=0,
        )
        result = GottmanTracker.record_interaction(counters, is_positive=True)
        assert result.positive_count == 6
        assert result.session_positive == 2
        # Negatives unchanged
        assert result.negative_count == 2
        assert result.session_negative == 0

    def test_update_conflict_details_updates_session_and_rolling(self):
        """update_conflict_details should update both session and rolling counters."""
        details = ConflictDetails(
            temperature=50.0,
            zone="warm",
            positive_count=10,
            negative_count=2,
            session_positive=3,
            session_negative=1,
        )
        result = GottmanTracker.update_conflict_details(details, is_positive=True, is_in_conflict=False)
        assert result.positive_count == 11
        assert result.session_positive == 4
        assert result.negative_count == 2  # unchanged
        assert result.session_negative == 1  # unchanged


# ---------------------------------------------------------------------------
# 5. initialize_from_history adversarial
# ---------------------------------------------------------------------------


class TestGottmanInitializeFromHistoryAdversarial:
    """Malformed and edge-case score_entries for initialize_from_history."""

    def test_empty_list(self):
        """Empty history should produce zero counters."""
        counters = GottmanTracker.initialize_from_history([])
        assert counters.positive_count == 0
        assert counters.negative_count == 0

    def test_missing_delta_key(self):
        """Entry without 'delta' key should be treated as delta=0 (skipped)."""
        entries = [{"score": 10}, {"points": -5}]
        counters = GottmanTracker.initialize_from_history(entries)
        # get("delta", 0) returns 0, float(0) = 0.0, which is neither >0 nor <0
        assert counters.positive_count == 0
        assert counters.negative_count == 0

    def test_delta_is_string_not_a_number(self):
        """String delta that can't be parsed should be skipped (not crash)."""
        entries = [{"delta": "not_a_number"}, {"delta": "abc"}]
        counters = GottmanTracker.initialize_from_history(entries)
        assert counters.positive_count == 0
        assert counters.negative_count == 0

    def test_delta_is_none(self):
        """None delta should be skipped (TypeError in float(None)).
        NOTE: May fail if implementation doesn't catch TypeError."""
        entries = [{"delta": None}]
        counters = GottmanTracker.initialize_from_history(entries)
        assert counters.positive_count == 0
        assert counters.negative_count == 0

    def test_delta_is_decimal(self):
        """Decimal delta should be convertible to float."""
        entries = [{"delta": Decimal("3.5")}, {"delta": Decimal("-2.0")}]
        counters = GottmanTracker.initialize_from_history(entries)
        assert counters.positive_count == 1
        assert counters.negative_count == 1

    def test_delta_zero_counted_as_neither(self):
        """Delta=0 should count as neither positive nor negative."""
        entries = [{"delta": 0}, {"delta": 0.0}, {"delta": -0.0}]
        counters = GottmanTracker.initialize_from_history(entries)
        assert counters.positive_count == 0
        assert counters.negative_count == 0

    def test_mixed_valid_and_invalid(self):
        """Mix of valid and invalid entries: only valid ones counted."""
        entries = [
            {"delta": 5.0},       # positive
            {"delta": "bad"},     # skipped
            {"delta": -3.0},      # negative
            {"delta": None},      # skipped
            {"delta": 0.0},       # neither
            {"delta": 1.0},       # positive
            {"no_delta": True},   # delta=0 from .get default → neither
        ]
        counters = GottmanTracker.initialize_from_history(entries)
        assert counters.positive_count == 2
        assert counters.negative_count == 1

    def test_session_counters_are_zero(self):
        """initialize_from_history should set session counters to 0."""
        entries = [{"delta": 5.0}, {"delta": -1.0}]
        counters = GottmanTracker.initialize_from_history(entries)
        assert counters.session_positive == 0
        assert counters.session_negative == 0

    def test_delta_is_bool(self):
        """bool is a subclass of int in Python. True=1 (positive), False=0 (neither).
        NOTE: May fail if implementation doesn't handle bool-as-number correctly."""
        entries = [{"delta": True}, {"delta": False}]
        counters = GottmanTracker.initialize_from_history(entries)
        # float(True) = 1.0 > 0 → positive; float(False) = 0.0 → neither
        assert counters.positive_count == 1
        assert counters.negative_count == 0

    def test_delta_is_negative_zero(self):
        """Negative zero: -0.0 == 0.0 in Python, so neither positive nor negative."""
        entries = [{"delta": -0.0}]
        counters = GottmanTracker.initialize_from_history(entries)
        assert counters.positive_count == 0
        assert counters.negative_count == 0

    def test_delta_is_inf(self):
        """float('inf') delta: inf > 0, so should be counted as positive.
        NOTE: May fail if implementation doesn't expect infinity."""
        entries = [{"delta": float("inf")}]
        counters = GottmanTracker.initialize_from_history(entries)
        assert counters.positive_count == 1

    def test_delta_is_neg_inf(self):
        """float('-inf') delta: -inf < 0, so should be counted as negative."""
        entries = [{"delta": float("-inf")}]
        counters = GottmanTracker.initialize_from_history(entries)
        assert counters.negative_count == 1


# ---------------------------------------------------------------------------
# 6. prune_window adversarial
# ---------------------------------------------------------------------------


class TestGottmanPruneWindowAdversarial:
    """Edge cases for prune_window: far past, future, exactly at cutoff."""

    def test_window_start_far_in_past(self):
        """Window start 100 days ago: should be pruned (reset)."""
        now = datetime(2025, 6, 1, tzinfo=UTC)
        counters = GottmanCounters(
            positive_count=50,
            negative_count=10,
            session_positive=5,
            session_negative=2,
            window_start=now - timedelta(days=100),
        )
        result = GottmanTracker.prune_window(counters, now=now)
        assert result.positive_count == 0
        assert result.negative_count == 0
        # Session counters should be preserved
        assert result.session_positive == 5
        assert result.session_negative == 2
        assert result.window_start == now

    def test_window_start_in_future(self):
        """Window start in future: NOT expired, should keep counters.
        Because window_start > (now - 7 days), so window_start >= window_cutoff."""
        now = datetime(2025, 6, 1, tzinfo=UTC)
        future_start = now + timedelta(days=1)
        counters = GottmanCounters(
            positive_count=50,
            negative_count=10,
            window_start=future_start,
        )
        result = GottmanTracker.prune_window(counters, now=now)
        assert result.positive_count == 50
        assert result.negative_count == 10

    def test_window_start_exactly_at_cutoff(self):
        """Window start exactly at cutoff boundary (now - 7 days).
        The check is `window_start < window_cutoff`, so exactly-at should NOT prune."""
        now = datetime(2025, 6, 8, tzinfo=UTC)
        cutoff = now - timedelta(days=7)  # June 1
        counters = GottmanCounters(
            positive_count=50,
            negative_count=10,
            window_start=cutoff,
        )
        result = GottmanTracker.prune_window(counters, now=now)
        # window_start == cutoff means NOT < cutoff, so should keep
        assert result.positive_count == 50
        assert result.negative_count == 10

    def test_window_start_one_second_before_cutoff(self):
        """Window start 1 second before cutoff: should be pruned."""
        now = datetime(2025, 6, 8, tzinfo=UTC)
        cutoff = now - timedelta(days=7)
        just_before = cutoff - timedelta(seconds=1)
        counters = GottmanCounters(
            positive_count=50,
            negative_count=10,
            window_start=just_before,
        )
        result = GottmanTracker.prune_window(counters, now=now)
        assert result.positive_count == 0
        assert result.negative_count == 0

    def test_custom_window_days(self):
        """Custom window of 1 day: should prune anything older than 1 day."""
        now = datetime(2025, 6, 8, tzinfo=UTC)
        counters = GottmanCounters(
            positive_count=50,
            negative_count=10,
            window_start=now - timedelta(days=2),
        )
        result = GottmanTracker.prune_window(counters, window_days=1, now=now)
        assert result.positive_count == 0
        assert result.negative_count == 0

    def test_zero_window_days(self):
        """Window of 0 days: cutoff = now, so anything before now is expired.
        NOTE: May fail if window_days=0 causes unexpected behavior."""
        now = datetime(2025, 6, 8, 12, 0, 0, tzinfo=UTC)
        counters = GottmanCounters(
            positive_count=50,
            negative_count=10,
            window_start=now - timedelta(hours=1),
        )
        result = GottmanTracker.prune_window(counters, window_days=0, now=now)
        # window_start < now (cutoff = now - 0 days = now), so should prune
        assert result.positive_count == 0


# ---------------------------------------------------------------------------
# 7. Temperature delta edge cases
# ---------------------------------------------------------------------------


class TestGottmanTemperatureDeltaEdges:
    """Edge cases in calculate_temperature_delta."""

    def test_exact_conflict_target_ratio(self):
        """Ratio exactly at conflict target (5.0): should produce negative delta (above target).
        ratio=5.0, target=5.0, ratio >= target → above target path.
        surplus = (5.0 - 5.0) / 5.0 = 0.0
        delta = -1.0 + (-2.0 - (-1.0)) * 0.0 = -1.0"""
        counters = GottmanCounters(positive_count=5, negative_count=1)
        delta = GottmanTracker.calculate_temperature_delta(counters, is_in_conflict=True)
        assert delta == pytest.approx(-1.0)

    def test_exact_normal_target_ratio(self):
        """Ratio exactly at normal target (20.0): above target.
        surplus = 0.0, delta = -1.0."""
        counters = GottmanCounters(positive_count=20, negative_count=1)
        delta = GottmanTracker.calculate_temperature_delta(counters, is_in_conflict=False)
        assert delta == pytest.approx(-1.0)

    def test_ratio_zero_with_negatives_only(self):
        """0 positive, N negative: ratio=0.0, far below target.
        shortfall = min(1.0, (5.0 - 0.0) / 5.0) = min(1.0, 1.0) = 1.0
        delta = 2.0 + (5.0 - 2.0) * 1.0 = 5.0"""
        counters = GottmanCounters(positive_count=0, negative_count=5)
        delta = GottmanTracker.calculate_temperature_delta(counters, is_in_conflict=True)
        assert delta == pytest.approx(5.0)

    def test_ratio_zero_normal_mode(self):
        """0/N in normal mode: target=20.0.
        shortfall = min(1.0, 20.0 / 20.0) = 1.0
        delta = 2.0 + 3.0 * 1.0 = 5.0"""
        counters = GottmanCounters(positive_count=0, negative_count=5)
        delta = GottmanTracker.calculate_temperature_delta(counters, is_in_conflict=False)
        assert delta == pytest.approx(5.0)

    def test_huge_ratio_above_target(self):
        """Very high ratio (1000:1): surplus capped at 1.0.
        surplus = min(1.0, (1000 - 5) / 5) = 1.0
        delta = -1.0 + (-1.0) * 1.0 = -2.0"""
        counters = GottmanCounters(positive_count=1000, negative_count=1)
        delta = GottmanTracker.calculate_temperature_delta(counters, is_in_conflict=True)
        assert delta == pytest.approx(-2.0)

    def test_just_below_conflict_target(self):
        """Ratio = 4.0 (below 5.0 target).
        shortfall = min(1.0, (5.0 - 4.0) / 5.0) = 0.2
        delta = 2.0 + 3.0 * 0.2 = 2.6"""
        counters = GottmanCounters(positive_count=4, negative_count=1)
        delta = GottmanTracker.calculate_temperature_delta(counters, is_in_conflict=True)
        assert delta == pytest.approx(2.6)

    def test_just_above_conflict_target(self):
        """Ratio = 6.0 (above 5.0 target).
        surplus = min(1.0, (6.0 - 5.0) / 5.0) = 0.2
        delta = -1.0 + (-1.0) * 0.2 = -1.2"""
        counters = GottmanCounters(positive_count=6, negative_count=1)
        delta = GottmanTracker.calculate_temperature_delta(counters, is_in_conflict=True)
        assert delta == pytest.approx(-1.2)

    def test_delta_always_in_expected_range(self):
        """For any valid counters, delta should be in [-2.0, 5.0]."""
        test_cases = [
            (0, 1),
            (1, 0),
            (1, 1),
            (5, 1),
            (20, 1),
            (100, 1),
            (1, 100),
            (0, 100),
        ]
        for pos, neg in test_cases:
            counters = GottmanCounters(positive_count=pos, negative_count=neg)
            for conflict in [True, False]:
                delta = GottmanTracker.calculate_temperature_delta(counters, conflict)
                assert -2.0 <= delta <= 5.0, (
                    f"pos={pos}, neg={neg}, conflict={conflict}: delta={delta}"
                )

    def test_single_negative_no_positive(self):
        """1 negative, 0 positive: ratio=0.0, below target.
        shortfall = 1.0 (max)
        delta = 5.0 (max positive delta)."""
        counters = GottmanCounters(positive_count=0, negative_count=1)
        delta = GottmanTracker.calculate_temperature_delta(counters, is_in_conflict=True)
        assert delta == pytest.approx(5.0)

    def test_single_positive_single_negative(self):
        """1/1 = 1.0, below both targets (5.0 and 20.0)."""
        counters = GottmanCounters(positive_count=1, negative_count=1)
        # Conflict mode: shortfall = (5.0 - 1.0) / 5.0 = 0.8
        # delta = 2.0 + 3.0 * 0.8 = 4.4
        delta = GottmanTracker.calculate_temperature_delta(counters, is_in_conflict=True)
        assert delta == pytest.approx(4.4)
