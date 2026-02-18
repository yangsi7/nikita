"""Adversarial tests for BreakupManager._check_temperature_threshold (DA-07).

Targets: nikita/conflicts/breakup.py — temperature-based breakup logic.

Edge cases tested:
- None timestamp with CRITICAL temperature (no crash)
- Future timestamp (negative hours_in_critical)
- Exact boundary values (>90.0 excludes ==90.0, >48h boundary)
- Non-CRITICAL zone short-circuits
- Warning threshold (24h-48h in CRITICAL)
- Breakup takes priority over warning when both conditions met
"""

import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from nikita.conflicts.breakup import BreakupManager, BreakupRisk, ThresholdResult
from nikita.conflicts.store import ConflictStore


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_store():
    """Create a mock ConflictStore."""
    store = MagicMock(spec=ConflictStore)
    store.count_consecutive_unresolved_crises.return_value = 0
    return store


@pytest.fixture
def manager(mock_store):
    """Create BreakupManager with mocked store."""
    return BreakupManager(store=mock_store)


def _make_conflict_details(temperature: float) -> dict:
    """Build a minimal conflict_details dict for a given temperature."""
    return {"temperature": temperature}


FIXED_NOW = datetime(2026, 2, 18, 12, 0, 0, tzinfo=UTC)


def _patch_now():
    """Patch datetime.now(UTC) inside breakup module to FIXED_NOW."""
    mock_dt = MagicMock(wraps=datetime)
    mock_dt.now.return_value = FIXED_NOW
    # Allow datetime(...) construction to work normally
    mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
    return patch("nikita.conflicts.breakup.datetime", mock_dt)


# =============================================================================
# TestBreakupNoneTimestamp
# =============================================================================


class TestBreakupNoneTimestamp:
    """last_conflict_at=None with CRITICAL temperature must return None, not crash."""

    def test_none_timestamp_returns_none(self, manager):
        """CRITICAL temp (95.0) + None timestamp -> None (no crash, no breakup)."""
        result = manager._check_temperature_threshold(
            user_id="user-1",
            relationship_score=50,
            conflict_details=_make_conflict_details(95.0),
            last_conflict_at=None,
            consecutive_crises=0,
        )
        assert result is None

    def test_none_timestamp_max_temperature(self, manager):
        """Temperature at absolute max (100.0) + None timestamp -> None."""
        result = manager._check_temperature_threshold(
            user_id="user-1",
            relationship_score=10,
            conflict_details=_make_conflict_details(100.0),
            last_conflict_at=None,
            consecutive_crises=5,
        )
        assert result is None

    def test_none_timestamp_threshold_boundary(self, manager):
        """Temperature exactly at CRITICAL boundary (75.0) + None timestamp -> None."""
        result = manager._check_temperature_threshold(
            user_id="user-1",
            relationship_score=50,
            conflict_details=_make_conflict_details(75.0),
            last_conflict_at=None,
            consecutive_crises=0,
        )
        assert result is None


# =============================================================================
# TestBreakupFutureTimestamp
# =============================================================================


class TestBreakupFutureTimestamp:
    """last_conflict_at in the future produces negative hours_in_critical.

    Must NOT false-positive a breakup or warning.
    """

    def test_future_timestamp_1h_ahead(self, manager):
        """Timestamp 1h in the future -> hours_in_critical ~ -1.0 -> None."""
        with _patch_now():
            future_ts = FIXED_NOW + timedelta(hours=1)
            result = manager._check_temperature_threshold(
                user_id="user-1",
                relationship_score=50,
                conflict_details=_make_conflict_details(95.0),
                last_conflict_at=future_ts,
                consecutive_crises=0,
            )
            # hours_in_critical is negative, so >48 and >24 checks both fail
            assert result is None

    def test_future_timestamp_100h_ahead(self, manager):
        """Timestamp 100h in the future -> hours_in_critical ~ -100 -> None."""
        with _patch_now():
            future_ts = FIXED_NOW + timedelta(hours=100)
            result = manager._check_temperature_threshold(
                user_id="user-1",
                relationship_score=50,
                conflict_details=_make_conflict_details(99.0),
                last_conflict_at=future_ts,
                consecutive_crises=0,
            )
            assert result is None

    def test_future_timestamp_1_second_ahead(self, manager):
        """Timestamp barely in the future (1s) -> still negative -> None."""
        with _patch_now():
            future_ts = FIXED_NOW + timedelta(seconds=1)
            result = manager._check_temperature_threshold(
                user_id="user-1",
                relationship_score=50,
                conflict_details=_make_conflict_details(95.0),
                last_conflict_at=future_ts,
                consecutive_crises=0,
            )
            assert result is None


# =============================================================================
# TestBreakupExactThresholds
# =============================================================================


class TestBreakupExactThresholds:
    """Exact boundary tests for temperature >90.0 AND hours >48.

    NOTE: The code uses `details.temperature > 90.0`, which means exactly
    90.0 does NOT trigger breakup. This is a potential off-by-one/boundary bug.
    """

    def test_temp_exactly_90_at_48h01m_no_breakup(self, manager):
        """temp=90.0 at 48h01m -> should_breakup=False.

        Code: `details.temperature > 90.0` — exactly 90.0 is NOT >90.0.
        NOTE: May fail if source changes to >= 90.0.
        """
        with _patch_now():
            ts = FIXED_NOW - timedelta(hours=48, minutes=1)
            result = manager._check_temperature_threshold(
                user_id="user-1",
                relationship_score=50,
                conflict_details=_make_conflict_details(90.0),
                last_conflict_at=ts,
                consecutive_crises=0,
            )
            # temp=90.0 is NOT >90.0, so breakup condition fails.
            # But hours >24, so it hits the warning branch.
            assert result is not None
            assert result.should_breakup is False
            assert result.should_warn is True

    def test_temp_90_1_at_48h01m_breakup(self, manager):
        """temp=90.1 at 48h01m -> should_breakup=True."""
        with _patch_now():
            ts = FIXED_NOW - timedelta(hours=48, minutes=1)
            result = manager._check_temperature_threshold(
                user_id="user-1",
                relationship_score=50,
                conflict_details=_make_conflict_details(90.1),
                last_conflict_at=ts,
                consecutive_crises=0,
            )
            assert result is not None
            assert result.should_breakup is True

    def test_temp_89_9_at_50h_no_breakup(self, manager):
        """temp=89.9 at 50h -> should_breakup=False (temp not >90).

        Even though hours >48, temperature is below 90 threshold.
        Should still warn (CRITICAL >24h).
        """
        with _patch_now():
            ts = FIXED_NOW - timedelta(hours=50)
            result = manager._check_temperature_threshold(
                user_id="user-1",
                relationship_score=50,
                conflict_details=_make_conflict_details(89.9),
                last_conflict_at=ts,
                consecutive_crises=0,
            )
            assert result is not None
            assert result.should_breakup is False
            assert result.should_warn is True

    def test_temp_95_at_47h59m_no_breakup(self, manager):
        """temp=95 at 47h59m -> should_breakup=False (hours not >48).

        Even though temp >90, duration hasn't hit 48h yet.
        Should still warn (CRITICAL >24h).
        """
        with _patch_now():
            ts = FIXED_NOW - timedelta(hours=47, minutes=59)
            result = manager._check_temperature_threshold(
                user_id="user-1",
                relationship_score=50,
                conflict_details=_make_conflict_details(95.0),
                last_conflict_at=ts,
                consecutive_crises=0,
            )
            assert result is not None
            assert result.should_breakup is False
            assert result.should_warn is True

    def test_temp_95_at_48h01m_breakup(self, manager):
        """temp=95 at 48h01m -> should_breakup=True (both conditions met)."""
        with _patch_now():
            ts = FIXED_NOW - timedelta(hours=48, minutes=1)
            result = manager._check_temperature_threshold(
                user_id="user-1",
                relationship_score=50,
                conflict_details=_make_conflict_details(95.0),
                last_conflict_at=ts,
                consecutive_crises=0,
            )
            assert result is not None
            assert result.should_breakup is True
            assert result.risk_level == BreakupRisk.TRIGGERED

    def test_temp_exactly_48h_no_breakup(self, manager):
        """temp=95 at exactly 48.0h -> should_breakup=False.

        Code: `hours_in_critical > 48` — exactly 48 is NOT >48.
        NOTE: May fail if source changes to >= 48.
        """
        with _patch_now():
            ts = FIXED_NOW - timedelta(hours=48)
            result = manager._check_temperature_threshold(
                user_id="user-1",
                relationship_score=50,
                conflict_details=_make_conflict_details(95.0),
                last_conflict_at=ts,
                consecutive_crises=0,
            )
            # hours_in_critical == 48.0, not > 48, so breakup doesn't trigger
            # But >24, so warning triggers
            assert result is not None
            assert result.should_breakup is False
            assert result.should_warn is True


# =============================================================================
# TestBreakupNonCriticalZoneSkips
# =============================================================================


class TestBreakupNonCriticalZoneSkips:
    """Non-CRITICAL zone temperatures must return None regardless of duration."""

    def test_hot_zone_74_9_returns_none(self, manager):
        """temp=74.9 (HOT zone, not CRITICAL) -> None even with long duration."""
        with _patch_now():
            ts = FIXED_NOW - timedelta(hours=100)
            result = manager._check_temperature_threshold(
                user_id="user-1",
                relationship_score=50,
                conflict_details=_make_conflict_details(74.9),
                last_conflict_at=ts,
                consecutive_crises=0,
            )
            assert result is None

    def test_warm_zone_returns_none(self, manager):
        """temp=49.9 (WARM zone) -> None."""
        with _patch_now():
            ts = FIXED_NOW - timedelta(hours=200)
            result = manager._check_temperature_threshold(
                user_id="user-1",
                relationship_score=5,
                conflict_details=_make_conflict_details(49.9),
                last_conflict_at=ts,
                consecutive_crises=10,
            )
            assert result is None

    def test_calm_zone_returns_none(self, manager):
        """temp=10.0 (CALM zone) -> None."""
        with _patch_now():
            ts = FIXED_NOW - timedelta(hours=500)
            result = manager._check_temperature_threshold(
                user_id="user-1",
                relationship_score=5,
                conflict_details=_make_conflict_details(10.0),
                last_conflict_at=ts,
                consecutive_crises=10,
            )
            assert result is None

    def test_exactly_75_is_critical(self, manager):
        """temp=75.0 is CRITICAL (>=75). Verify it does NOT return None.

        TemperatureEngine.get_zone: temp >= 75 -> CRITICAL.
        With >24h duration, should trigger warning.
        """
        with _patch_now():
            ts = FIXED_NOW - timedelta(hours=25)
            result = manager._check_temperature_threshold(
                user_id="user-1",
                relationship_score=50,
                conflict_details=_make_conflict_details(75.0),
                last_conflict_at=ts,
                consecutive_crises=0,
            )
            assert result is not None
            assert result.should_warn is True


# =============================================================================
# TestBreakupWarningThreshold
# =============================================================================


class TestBreakupWarningThreshold:
    """CRITICAL zone for >24h but <48h -> warning only, no breakup."""

    def test_critical_25h_warning(self, manager):
        """temp=80.0 for 25h -> should_warn=True, should_breakup=False."""
        with _patch_now():
            ts = FIXED_NOW - timedelta(hours=25)
            result = manager._check_temperature_threshold(
                user_id="user-1",
                relationship_score=50,
                conflict_details=_make_conflict_details(80.0),
                last_conflict_at=ts,
                consecutive_crises=0,
            )
            assert result is not None
            assert result.should_warn is True
            assert result.should_breakup is False
            assert result.risk_level == BreakupRisk.CRITICAL

    def test_critical_47h_warning_not_breakup(self, manager):
        """temp=80.0 for 47h -> warning (>24h), NOT breakup (<48h and temp not >90)."""
        with _patch_now():
            ts = FIXED_NOW - timedelta(hours=47)
            result = manager._check_temperature_threshold(
                user_id="user-1",
                relationship_score=50,
                conflict_details=_make_conflict_details(80.0),
                last_conflict_at=ts,
                consecutive_crises=0,
            )
            assert result is not None
            assert result.should_warn is True
            assert result.should_breakup is False

    def test_critical_exactly_24h_no_warning(self, manager):
        """temp=80.0 for exactly 24.0h -> hours_in_critical=24.0, NOT >24 -> None.

        NOTE: May fail if source changes to >= 24.
        """
        with _patch_now():
            ts = FIXED_NOW - timedelta(hours=24)
            result = manager._check_temperature_threshold(
                user_id="user-1",
                relationship_score=50,
                conflict_details=_make_conflict_details(80.0),
                last_conflict_at=ts,
                consecutive_crises=0,
            )
            # Exactly 24h is NOT >24h, so no warning triggers either
            assert result is None

    def test_critical_23h59m_no_warning(self, manager):
        """temp=80.0 for 23h59m -> hours_in_critical < 24 -> None."""
        with _patch_now():
            ts = FIXED_NOW - timedelta(hours=23, minutes=59)
            result = manager._check_temperature_threshold(
                user_id="user-1",
                relationship_score=50,
                conflict_details=_make_conflict_details(80.0),
                last_conflict_at=ts,
                consecutive_crises=0,
            )
            assert result is None


# =============================================================================
# TestBreakupBothConditionsMet
# =============================================================================


class TestBreakupBothConditionsMet:
    """When both breakup (temp>90, >48h) AND warning (>24h) conditions are met,
    breakup check comes FIRST in the code, so should_breakup=True wins."""

    def test_breakup_beats_warning(self, manager):
        """temp=95 for 49h -> breakup (not just warning)."""
        with _patch_now():
            ts = FIXED_NOW - timedelta(hours=49)
            result = manager._check_temperature_threshold(
                user_id="user-1",
                relationship_score=50,
                conflict_details=_make_conflict_details(95.0),
                last_conflict_at=ts,
                consecutive_crises=0,
            )
            assert result is not None
            assert result.should_breakup is True
            # When breakup triggers, should_warn is NOT set
            assert result.should_warn is False
            assert result.risk_level == BreakupRisk.TRIGGERED

    def test_breakup_at_100_temp_72h(self, manager):
        """temp=100 for 72h -> extreme case, breakup triggered."""
        with _patch_now():
            ts = FIXED_NOW - timedelta(hours=72)
            result = manager._check_temperature_threshold(
                user_id="user-1",
                relationship_score=50,
                conflict_details=_make_conflict_details(100.0),
                last_conflict_at=ts,
                consecutive_crises=3,
            )
            assert result is not None
            assert result.should_breakup is True
            assert result.consecutive_crises == 3
            assert result.score == 50

    def test_breakup_preserves_score_and_crises(self, manager):
        """Verify ThresholdResult carries through score and crises."""
        with _patch_now():
            ts = FIXED_NOW - timedelta(hours=50)
            result = manager._check_temperature_threshold(
                user_id="user-99",
                relationship_score=15,
                conflict_details=_make_conflict_details(91.0),
                last_conflict_at=ts,
                consecutive_crises=2,
            )
            assert result is not None
            assert result.should_breakup is True
            assert result.score == 15
            assert result.consecutive_crises == 2
            assert "91.0" in result.reason
            assert "50." in result.reason  # hours mentioned
