"""Tests for conversation rhythm helpers (Spec 210 v2).

Covers `compute_momentum` and `compute_user_gaps` — pure functions that
produce the momentum coefficient M used as a multiplier in the response
timing delay formula.

Model (see docs/models/response-timing.md):
    M = clip(EWMA_alpha(gaps) / B_ch, M_LO, M_HI)

Where B_ch is the chapter baseline and EWMA is seeded at B_ch (Bayesian
prior equivalence).
"""

from datetime import datetime, timedelta

import pytest

from nikita.agents.text.conversation_rhythm import (
    CHAPTER_BASELINES_SECONDS,
    MOMENTUM_ALPHA,
    MOMENTUM_HI,
    MOMENTUM_LO,
    SESSION_BREAK_SECONDS,
    compute_momentum,
    compute_user_gaps,
)


# --------------------------------------------------------------------------- #
# compute_momentum                                                            #
# --------------------------------------------------------------------------- #


class TestComputeMomentumCoreBehavior:
    """Contract: pure function, output in [M_LO, M_HI], direction correct."""

    def test_empty_history_is_neutral(self):
        """No gap data -> M=1.0 (no adjustment)."""
        assert compute_momentum([], chapter=1) == pytest.approx(1.0)
        assert compute_momentum([], chapter=3) == pytest.approx(1.0)
        assert compute_momentum([], chapter=5) == pytest.approx(1.0)

    def test_fast_user_produces_low_momentum_ch1(self):
        """User replying in ~5-10s on Ch1 (baseline 300s) -> M < 0.5."""
        m = compute_momentum([5.0, 8.0, 6.0, 7.0, 9.0, 6.0, 8.0], chapter=1)
        assert m < 0.5, f"Expected M < 0.5 for fast user, got {m}"
        assert m >= MOMENTUM_LO

    def test_slow_user_produces_high_momentum_ch1(self):
        """User gaps all above baseline -> M > 1.5."""
        # Ch1 baseline 300; use gaps well above to push EWMA up
        m = compute_momentum([600.0, 720.0, 540.0, 800.0, 660.0], chapter=1)
        assert m > 1.5, f"Expected M > 1.5 for slow user, got {m}"
        assert m <= MOMENTUM_HI

    def test_neutral_gaps_at_baseline_give_M_near_one(self):
        """User gaps equal to baseline -> M ~= 1.0."""
        baseline = CHAPTER_BASELINES_SECONDS[3]
        gaps = [float(baseline)] * 10
        m = compute_momentum(gaps, chapter=3)
        assert 0.95 <= m <= 1.05, f"Expected M near 1.0, got {m}"

    def test_bounded_below(self):
        """Even absurdly fast gaps cannot push M below M_LO."""
        m = compute_momentum([0.01] * 20, chapter=5)
        assert m >= MOMENTUM_LO
        # And the bound should actually be approached
        assert m <= MOMENTUM_LO + 0.01

    def test_bounded_above(self):
        """Even very slow gaps cannot push M above M_HI."""
        # Use gaps at the session-break boundary to avoid being filtered
        # (filter runs in compute_user_gaps, not compute_momentum).
        m = compute_momentum([899.0] * 20, chapter=1)
        assert m <= MOMENTUM_HI


class TestComputeMomentumColdStart:
    """Short histories should behave gracefully via the prior-seeded EWMA."""

    def test_single_observation_pulls_toward_it(self):
        """One gap of 10s on Ch1 (B=300) -> M noticeably below 1, not extreme."""
        m = compute_momentum([10.0], chapter=1)
        baseline = CHAPTER_BASELINES_SECONDS[1]
        # After one obs, EWMA = alpha*10 + (1-alpha)*B ≈ 0.35*10 + 0.65*300 = 198.5
        # M = 198.5 / 300 ≈ 0.662
        expected = (MOMENTUM_ALPHA * 10 + (1 - MOMENTUM_ALPHA) * baseline) / baseline
        assert m == pytest.approx(expected, rel=1e-3)

    def test_two_observations(self):
        """Two gaps -> EWMA contracts further but still respects prior."""
        m = compute_momentum([10.0, 10.0], chapter=1)
        # Two-step EWMA seeded at 300:
        s1 = MOMENTUM_ALPHA * 10 + (1 - MOMENTUM_ALPHA) * 300
        s2 = MOMENTUM_ALPHA * 10 + (1 - MOMENTUM_ALPHA) * s1
        assert m == pytest.approx(s2 / 300, rel=1e-3)


class TestComputeMomentumDirection:
    """Monotone direction tests."""

    def test_accelerating_trace_lowers_final_M(self):
        """Gaps decreasing over time -> final M significantly lower than initial M."""
        trace = [400.0, 300.0, 200.0, 100.0, 30.0, 20.0]
        values = [compute_momentum(trace[: i + 1], chapter=3) for i in range(len(trace))]
        # End-to-end: last M must be well below first M
        assert values[-1] < values[0] - 0.3
        # Once below the prior, momentum should trend down (last three monotone)
        tail = values[-3:]
        assert tail[0] > tail[1] > tail[2]

    def test_decelerating_trace_raises_final_M(self):
        """Gaps increasing over time -> final M significantly higher than initial M."""
        trace = [20.0, 30.0, 100.0, 200.0, 400.0, 600.0]
        values = [compute_momentum(trace[: i + 1], chapter=3) for i in range(len(trace))]
        assert values[-1] > values[0] + 0.5
        # Once above the prior, momentum should trend up (last three monotone)
        tail = values[-3:]
        assert tail[0] < tail[1] < tail[2]


class TestComputeMomentumChapterDifferentiation:
    """Same gaps on different chapters produce different M because B_ch differs."""

    def test_same_gaps_produce_higher_M_on_higher_chapter(self):
        """Baseline shrinks with chapter, so a fixed gap is relatively slower at Ch5."""
        gaps = [120.0] * 5  # 2 minutes
        # Ch5 baseline 90s: gaps above baseline -> M > 1
        m_ch5 = compute_momentum(gaps, chapter=5)
        # Ch1 baseline 300s: gaps below baseline -> M < 1
        m_ch1 = compute_momentum(gaps, chapter=1)
        assert m_ch5 > 1.0
        assert m_ch1 < 1.0


class TestComputeMomentumInvalidChapter:
    """Invalid chapter should fall back to a sensible default (Ch1)."""

    def test_chapter_0_falls_back(self):
        m = compute_momentum([5.0], chapter=0)
        # Should not raise; should produce a finite M in bounds
        assert MOMENTUM_LO <= m <= MOMENTUM_HI

    def test_chapter_99_falls_back(self):
        m = compute_momentum([5.0], chapter=99)
        assert MOMENTUM_LO <= m <= MOMENTUM_HI


# --------------------------------------------------------------------------- #
# compute_user_gaps                                                          #
# --------------------------------------------------------------------------- #


def _msg(role: str, ts: datetime, content: str = "x") -> dict:
    return {"role": role, "content": content, "timestamp": ts.isoformat()}


class TestComputeUserGapsBasics:
    """Extract user-turn inter-message deltas in seconds."""

    def test_empty_messages(self):
        assert compute_user_gaps([]) == []

    def test_single_message(self):
        now = datetime(2026, 4, 13, 12, 0, 0)
        assert compute_user_gaps([_msg("user", now)]) == []

    def test_user_only_gaps(self):
        """Pairs of consecutive user turns produce one gap each."""
        t0 = datetime(2026, 4, 13, 12, 0, 0)
        msgs = [
            _msg("user", t0),
            _msg("user", t0 + timedelta(seconds=5)),
            _msg("user", t0 + timedelta(seconds=12)),
        ]
        gaps = compute_user_gaps(msgs)
        assert gaps == [5.0, 7.0]

    def test_nikita_turns_ignored(self):
        """Gaps are user-to-user; Nikita turns between are skipped."""
        t0 = datetime(2026, 4, 13, 12, 0, 0)
        msgs = [
            _msg("user", t0),
            _msg("nikita", t0 + timedelta(seconds=3)),
            _msg("user", t0 + timedelta(seconds=10)),  # 10s after first user
            _msg("nikita", t0 + timedelta(seconds=12)),
            _msg("user", t0 + timedelta(seconds=25)),  # 15s after prev user
        ]
        gaps = compute_user_gaps(msgs)
        assert gaps == [10.0, 15.0]


class TestComputeUserGapsSessionFilter:
    """Gaps greater than SESSION_BREAK_SECONDS (900s / 15min) are dropped."""

    def test_session_break_filtered_out(self):
        t0 = datetime(2026, 4, 13, 12, 0, 0)
        msgs = [
            _msg("user", t0),
            _msg("user", t0 + timedelta(seconds=5)),
            _msg("user", t0 + timedelta(seconds=5 + 1500)),  # 25min gap
            _msg("user", t0 + timedelta(seconds=5 + 1500 + 8)),
        ]
        gaps = compute_user_gaps(msgs)
        assert gaps == [5.0, 8.0]  # 1500s dropped

    def test_exactly_at_session_boundary(self):
        """Gap exactly equal to SESSION_BREAK_SECONDS is treated as a break (dropped)."""
        t0 = datetime(2026, 4, 13, 12, 0, 0)
        msgs = [
            _msg("user", t0),
            _msg("user", t0 + timedelta(seconds=SESSION_BREAK_SECONDS)),
        ]
        gaps = compute_user_gaps(msgs)
        assert gaps == []


class TestComputeUserGapsFloorAndWindow:
    def test_zero_gap_floored_to_one(self):
        """Same-timestamp messages yield delta 1.0, not 0, to avoid log(0)."""
        t0 = datetime(2026, 4, 13, 12, 0, 0)
        msgs = [_msg("user", t0), _msg("user", t0)]
        gaps = compute_user_gaps(msgs)
        assert gaps == [1.0]

    def test_returns_last_10_only(self):
        """With >10 user-gap pairs, only the last 10 deltas are returned."""
        t0 = datetime(2026, 4, 13, 12, 0, 0)
        # 15 user messages -> 14 gaps
        msgs = [_msg("user", t0 + timedelta(seconds=i * 5)) for i in range(15)]
        gaps = compute_user_gaps(msgs)
        assert len(gaps) == 10
        # Each gap is 5s
        assert all(g == 5.0 for g in gaps)


class TestComputeUserGapsMalformed:
    """Defensive behavior for malformed inputs."""

    def test_missing_timestamp_skipped(self):
        t0 = datetime(2026, 4, 13, 12, 0, 0)
        msgs = [
            _msg("user", t0),
            {"role": "user", "content": "x"},  # no timestamp
            _msg("user", t0 + timedelta(seconds=7)),
        ]
        gaps = compute_user_gaps(msgs)
        # Invalid entry skipped, gap computed between remaining user turns
        assert gaps == [7.0]

    def test_unparseable_timestamp_skipped(self):
        t0 = datetime(2026, 4, 13, 12, 0, 0)
        msgs = [
            _msg("user", t0),
            {"role": "user", "content": "x", "timestamp": "not-a-date"},
            _msg("user", t0 + timedelta(seconds=9)),
        ]
        gaps = compute_user_gaps(msgs)
        assert gaps == [9.0]
