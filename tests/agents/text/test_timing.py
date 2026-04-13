"""Tests for ResponseTimer — Spec 210 v2 (log-normal × chapter × momentum).

Covers:
- Per-chapter coefficients and caps (`CHAPTER_COEFFICIENTS`, `CHAPTER_CAPS_SECONDS`)
- New-conversation gate (`is_new_conversation=False` -> 0)
- Momentum scaling and bounds
- Dev-mode bypass
- Log-normal base distribution shape (direction tests only — MC validator
  covers quantitative shape at scale)

Superseded v1 tests:
- TIMING_RANGES (0, 28800) etc. -> now (0, CHAPTER_CAPS_SECONDS[ch])
- random.gauss mean-clustering tests -> replaced by log-normal shape checks
"""

from unittest.mock import MagicMock, patch

import pytest


def _production_settings() -> MagicMock:
    s = MagicMock()
    s.environment = "production"
    s.debug = False
    return s


def _development_settings() -> MagicMock:
    s = MagicMock()
    s.environment = "development"
    s.debug = False
    return s


# --------------------------------------------------------------------------- #
# Module structure                                                            #
# --------------------------------------------------------------------------- #


class TestModuleStructure:
    def test_module_importable(self):
        from nikita.agents.text import timing

        assert hasattr(timing, "ResponseTimer")
        assert hasattr(timing, "CHAPTER_COEFFICIENTS")
        assert hasattr(timing, "CHAPTER_CAPS_SECONDS")
        assert hasattr(timing, "LOGNORMAL_MU")
        assert hasattr(timing, "LOGNORMAL_SIGMA")

    def test_chapter_coefficients_increase(self):
        """Coefficients monotone-increase with chapter (excitement fades)."""
        from nikita.agents.text.timing import CHAPTER_COEFFICIENTS

        for ch in range(1, 5):
            assert CHAPTER_COEFFICIENTS[ch] < CHAPTER_COEFFICIENTS[ch + 1]

    def test_chapter_caps_increase(self):
        """Caps grow with chapter (Ch1 tightest, Ch5 loosest)."""
        from nikita.agents.text.timing import CHAPTER_CAPS_SECONDS

        assert CHAPTER_CAPS_SECONDS[1] <= 15
        assert CHAPTER_CAPS_SECONDS[5] >= 600
        for ch in range(1, 5):
            assert CHAPTER_CAPS_SECONDS[ch] < CHAPTER_CAPS_SECONDS[ch + 1]


# --------------------------------------------------------------------------- #
# ResponseTimer.calculate_delay                                               #
# --------------------------------------------------------------------------- #


class TestCalculateDelayBypasses:
    """Early returns: dev mode, ongoing conversations."""

    def test_development_mode_returns_zero(self):
        from nikita.agents.text.timing import ResponseTimer

        with patch(
            "nikita.agents.text.timing.get_settings",
            return_value=_development_settings(),
        ):
            timer = ResponseTimer()
            for ch in range(1, 6):
                assert timer.calculate_delay(chapter=ch) == 0

    def test_debug_mode_returns_zero(self):
        from nikita.agents.text.timing import ResponseTimer

        s = _production_settings()
        s.debug = True
        with patch("nikita.agents.text.timing.get_settings", return_value=s):
            timer = ResponseTimer()
            assert timer.calculate_delay(chapter=3) == 0

    def test_ongoing_conversation_returns_zero(self):
        """is_new_conversation=False short-circuits regardless of chapter/momentum."""
        from nikita.agents.text.timing import ResponseTimer

        with patch(
            "nikita.agents.text.timing.get_settings",
            return_value=_production_settings(),
        ):
            timer = ResponseTimer()
            for ch in range(1, 6):
                for m in (0.1, 1.0, 5.0):
                    assert (
                        timer.calculate_delay(
                            chapter=ch, is_new_conversation=False, momentum=m
                        )
                        == 0
                    )


class TestCalculateDelayCaps:
    """Per-chapter caps enforced even with adversarial Z and momentum."""

    def test_ch1_cap_enforced_with_high_z(self):
        """Very large Z value should still be clamped to Ch1 cap."""
        from nikita.agents.text.timing import CHAPTER_CAPS_SECONDS, ResponseTimer

        with patch(
            "nikita.agents.text.timing.get_settings",
            return_value=_production_settings(),
        ), patch("random.Random.gauss", return_value=10.0):
            timer = ResponseTimer()
            delay = timer.calculate_delay(
                chapter=1, is_new_conversation=True, momentum=5.0
            )
            assert 1 <= delay <= CHAPTER_CAPS_SECONDS[1]

    def test_ch5_cap_enforced_with_high_z(self):
        from nikita.agents.text.timing import CHAPTER_CAPS_SECONDS, ResponseTimer

        with patch(
            "nikita.agents.text.timing.get_settings",
            return_value=_production_settings(),
        ), patch("random.Random.gauss", return_value=10.0):
            timer = ResponseTimer()
            delay = timer.calculate_delay(
                chapter=5, is_new_conversation=True, momentum=5.0
            )
            assert 1 <= delay <= CHAPTER_CAPS_SECONDS[5]

    def test_ch1_delay_rarely_above_cap_in_sampling(self):
        """100 samples at Ch1, all must be ≤ 10s."""
        from nikita.agents.text.timing import CHAPTER_CAPS_SECONDS, ResponseTimer

        with patch(
            "nikita.agents.text.timing.get_settings",
            return_value=_production_settings(),
        ):
            timer = ResponseTimer()
            samples = [
                timer.calculate_delay(chapter=1, is_new_conversation=True)
                for _ in range(100)
            ]
            assert all(s <= CHAPTER_CAPS_SECONDS[1] for s in samples)
            assert all(s >= 1 for s in samples)  # floor at 1s for new conversations


class TestCalculateDelayMomentum:
    """Momentum multiplicatively scales the sample (pre-cap)."""

    def test_doubled_momentum_doubles_raw_delay_pre_cap(self):
        """With fixed Z, M=2 yields ~2x the delay of M=1 (below the cap)."""
        from nikita.agents.text.timing import ResponseTimer

        with patch(
            "nikita.agents.text.timing.get_settings",
            return_value=_production_settings(),
        ), patch("random.Random.gauss", return_value=0.0):
            # Z=0 -> exp(mu) ≈ 20s; coeff_ch3 = 0.5 -> base ~10s (well below cap 300)
            timer = ResponseTimer()
            d1 = timer.calculate_delay(chapter=3, is_new_conversation=True, momentum=1.0)
            d2 = timer.calculate_delay(chapter=3, is_new_conversation=True, momentum=2.0)
            assert d2 >= 2 * d1 - 1  # allow int truncation of 1s

    def test_momentum_out_of_bounds_is_clamped(self):
        """Caller passes M=100 or M=-5; timer must clamp internally, no crash."""
        from nikita.agents.text.timing import ResponseTimer

        with patch(
            "nikita.agents.text.timing.get_settings",
            return_value=_production_settings(),
        ):
            timer = ResponseTimer()
            # Should not raise and should produce a valid cap-bounded int
            d_hi = timer.calculate_delay(chapter=3, is_new_conversation=True, momentum=100.0)
            d_lo = timer.calculate_delay(chapter=3, is_new_conversation=True, momentum=-5.0)
            assert 1 <= d_hi <= 300  # floor at 1s for new conversations
            assert 1 <= d_lo <= 300


class TestCalculateDelayInvalidChapter:
    def test_invalid_chapter_falls_back(self):
        from nikita.agents.text.timing import ResponseTimer

        with patch(
            "nikita.agents.text.timing.get_settings",
            return_value=_production_settings(),
        ):
            timer = ResponseTimer()
            delay = timer.calculate_delay(chapter=0, is_new_conversation=True)
            assert isinstance(delay, int)
            assert delay >= 1  # new-conversation floor
            delay = timer.calculate_delay(chapter=99, is_new_conversation=True)
            assert isinstance(delay, int)
            assert delay >= 1  # new-conversation floor


class TestCalculateDelayProgression:
    """Expected ordering: Ch1 median << Ch5 median (excitement fades)."""

    def test_ch1_samples_are_much_smaller_than_ch5(self):
        from nikita.agents.text.timing import ResponseTimer

        with patch(
            "nikita.agents.text.timing.get_settings",
            return_value=_production_settings(),
        ):
            timer = ResponseTimer()
            ch1 = [timer.calculate_delay(chapter=1, is_new_conversation=True) for _ in range(200)]
            ch5 = [timer.calculate_delay(chapter=5, is_new_conversation=True) for _ in range(200)]
            # Ch5 sampled delays should generally exceed Ch1 caps (10s)
            assert max(ch1) <= 10
            # Average Ch5 should be materially higher than Ch1
            assert sum(ch5) / len(ch5) > sum(ch1) / len(ch1)


# --------------------------------------------------------------------------- #
# Human-readable formatter                                                    #
# --------------------------------------------------------------------------- #


class TestCalculateDelayHumanReadable:
    def test_returns_string(self):
        from nikita.agents.text.timing import ResponseTimer

        with patch(
            "nikita.agents.text.timing.get_settings",
            return_value=_development_settings(),
        ):
            timer = ResponseTimer()
            assert isinstance(
                timer.calculate_delay_human_readable(chapter=1), str
            )

    def test_zero_seconds_dev_mode(self):
        from nikita.agents.text.timing import ResponseTimer

        with patch(
            "nikita.agents.text.timing.get_settings",
            return_value=_development_settings(),
        ):
            timer = ResponseTimer()
            assert timer.calculate_delay_human_readable(chapter=1) == "0 seconds"

    def test_ongoing_returns_zero(self):
        from nikita.agents.text.timing import ResponseTimer

        with patch(
            "nikita.agents.text.timing.get_settings",
            return_value=_production_settings(),
        ):
            timer = ResponseTimer()
            assert (
                timer.calculate_delay_human_readable(
                    chapter=3, is_new_conversation=False
                )
                == "0 seconds"
            )

    def test_positive_delay_formats_correctly(self):
        """Non-zero delay includes seconds even when minutes are present."""
        from nikita.agents.text.timing import ResponseTimer

        with patch(
            "nikita.agents.text.timing.get_settings",
            return_value=_production_settings(),
        ), patch("random.Random.gauss", return_value=0.0):
            timer = ResponseTimer()
            # Z=0 → exp(2.996)≈20 × coeff_ch5=1.0 → delay≈20s
            result = timer.calculate_delay_human_readable(
                chapter=5, is_new_conversation=True
            )
            assert "second" in result


# --------------------------------------------------------------------------- #
# Legacy compatibility (a few integration tests import TIMING_RANGES)         #
# --------------------------------------------------------------------------- #


class TestLegacyCompat:
    def test_timing_ranges_still_exported(self):
        """TIMING_RANGES preserved as (0, cap) for downstream legacy imports."""
        from nikita.agents.text.timing import TIMING_RANGES, CHAPTER_CAPS_SECONDS

        for ch in range(1, 6):
            lo, hi = TIMING_RANGES[ch]
            assert lo == 0
            assert hi == CHAPTER_CAPS_SECONDS[ch]
