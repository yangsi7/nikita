"""Tests for ResponseTimer - TDD for T4.1.

Acceptance Criteria:
- AC-4.1.1: TIMING_RANGES dict maps chapter to (min_seconds, max_seconds)
- AC-4.1.2: Ch1 range: 600-28800s (10min-8h)
- AC-4.1.3: Ch5 range: 300-1800s (5min-30min)
- AC-4.1.4: `calculate_delay(chapter)` returns int seconds
- AC-4.1.5: Distribution is gaussian, not uniform (natural feel)
- AC-4.1.6: Random jitter added to prevent exact patterns
"""

import pytest
import statistics
from unittest.mock import patch, MagicMock


class TestTimingRanges:
    """Tests for TIMING_RANGES constant."""

    def test_timing_module_importable(self):
        """Timing module should be importable."""
        from nikita.agents.text import timing

        assert hasattr(timing, "TIMING_RANGES")
        assert hasattr(timing, "ResponseTimer")

    def test_ac_4_1_1_timing_ranges_is_dict(self):
        """AC-4.1.1: TIMING_RANGES should be a dict mapping chapter to (min, max)."""
        from nikita.agents.text.timing import TIMING_RANGES

        assert isinstance(TIMING_RANGES, dict)

        # Should have entries for chapters 1-5
        assert 1 in TIMING_RANGES
        assert 5 in TIMING_RANGES

        # Each entry should be a tuple of (min, max)
        for chapter, timing_range in TIMING_RANGES.items():
            assert isinstance(timing_range, tuple)
            assert len(timing_range) == 2
            min_sec, max_sec = timing_range
            assert isinstance(min_sec, (int, float))
            assert isinstance(max_sec, (int, float))
            assert min_sec < max_sec

    def test_ac_4_1_2_ch1_range(self):
        """AC-4.1.2: Ch1 range should be 600-28800s (10min-8h)."""
        from nikita.agents.text.timing import TIMING_RANGES

        min_sec, max_sec = TIMING_RANGES[1]

        # 10 minutes = 600 seconds
        assert min_sec == 600
        # 8 hours = 28800 seconds
        assert max_sec == 28800

    def test_ac_4_1_3_ch5_range(self):
        """AC-4.1.3: Ch5 range should be 300-1800s (5min-30min)."""
        from nikita.agents.text.timing import TIMING_RANGES

        min_sec, max_sec = TIMING_RANGES[5]

        # 5 minutes = 300 seconds
        assert min_sec == 300
        # 30 minutes = 1800 seconds
        assert max_sec == 1800

    def test_ranges_for_all_chapters(self):
        """All 5 chapters should have timing ranges defined."""
        from nikita.agents.text.timing import TIMING_RANGES

        for chapter in [1, 2, 3, 4, 5]:
            assert chapter in TIMING_RANGES, f"Chapter {chapter} missing from TIMING_RANGES"


def mock_production_settings():
    """Create mock settings that simulate production mode."""
    mock_settings = MagicMock()
    mock_settings.environment = "production"
    mock_settings.debug = False
    return mock_settings


def mock_development_settings():
    """Create mock settings that simulate development mode."""
    mock_settings = MagicMock()
    mock_settings.environment = "development"
    mock_settings.debug = False
    return mock_settings


class TestResponseTimer:
    """Tests for ResponseTimer class."""

    def test_response_timer_class_exists(self):
        """ResponseTimer class should exist."""
        from nikita.agents.text.timing import ResponseTimer

        assert callable(ResponseTimer)

    def test_ac_4_1_4_calculate_delay_returns_int(self):
        """AC-4.1.4: calculate_delay(chapter) should return int seconds in production."""
        from nikita.agents.text.timing import ResponseTimer

        with patch('nikita.agents.text.timing.get_settings', return_value=mock_production_settings()):
            timer = ResponseTimer()
            delay = timer.calculate_delay(chapter=1)

            assert isinstance(delay, int)
            assert delay > 0

    def test_calculate_delay_within_chapter_range(self):
        """calculate_delay should return values within the chapter's range in production."""
        from nikita.agents.text.timing import ResponseTimer, TIMING_RANGES

        with patch('nikita.agents.text.timing.get_settings', return_value=mock_production_settings()):
            timer = ResponseTimer()

            for chapter in [1, 3, 5]:
                min_sec, max_sec = TIMING_RANGES[chapter]

                # Test multiple times to check range compliance
                for _ in range(20):
                    delay = timer.calculate_delay(chapter=chapter)
                    assert min_sec <= delay <= max_sec, \
                        f"Ch{chapter} delay {delay} not in range [{min_sec}, {max_sec}]"

    def test_ac_4_1_5_distribution_not_uniform(self):
        """AC-4.1.5: Distribution should be gaussian (clustered around mean) in production."""
        from nikita.agents.text.timing import ResponseTimer, TIMING_RANGES

        with patch('nikita.agents.text.timing.get_settings', return_value=mock_production_settings()):
            timer = ResponseTimer()

            # Generate many samples
            samples = [timer.calculate_delay(chapter=3) for _ in range(500)]

            min_sec, max_sec = TIMING_RANGES[3]

            # Count samples in thirds
            range_size = max_sec - min_sec
            third = range_size / 3

            lower_third = sum(1 for s in samples if s < min_sec + third)
            middle_third = sum(1 for s in samples if min_sec + third <= s < min_sec + 2 * third)
            upper_third = sum(1 for s in samples if s >= min_sec + 2 * third)

            # For gaussian, middle third should have more samples than edges
            # This is a probabilistic test, but with 500 samples should be very reliable
            assert middle_third > lower_third, "Middle should be denser than lower (gaussian)"
            assert middle_third > upper_third, "Middle should be denser than upper (gaussian)"

    def test_ac_4_1_6_jitter_prevents_exact_patterns(self):
        """AC-4.1.6: Random jitter should prevent exact repetition in production."""
        from nikita.agents.text.timing import ResponseTimer

        with patch('nikita.agents.text.timing.get_settings', return_value=mock_production_settings()):
            timer = ResponseTimer()

            # Generate samples
            samples = [timer.calculate_delay(chapter=2) for _ in range(100)]

            # Should have many unique values (high variance)
            unique_values = set(samples)
            assert len(unique_values) >= 50, f"Only {len(unique_values)} unique values, expected more variance"

    def test_invalid_chapter_uses_default(self):
        """Invalid chapter should fall back to a default range in production."""
        from nikita.agents.text.timing import ResponseTimer

        with patch('nikita.agents.text.timing.get_settings', return_value=mock_production_settings()):
            timer = ResponseTimer()

            # Chapter 0 or 6 should not crash
            delay = timer.calculate_delay(chapter=0)
            assert isinstance(delay, int)
            assert delay > 0

            delay = timer.calculate_delay(chapter=6)
            assert isinstance(delay, int)
            assert delay > 0

    def test_development_mode_returns_zero(self):
        """Development mode should bypass delays and return 0."""
        from nikita.agents.text.timing import ResponseTimer

        with patch('nikita.agents.text.timing.get_settings', return_value=mock_development_settings()):
            timer = ResponseTimer()

            for chapter in [1, 2, 3, 4, 5]:
                delay = timer.calculate_delay(chapter=chapter)
                assert delay == 0, f"Development mode should return 0, got {delay}"

    def test_debug_mode_returns_zero(self):
        """Debug mode should bypass delays and return 0."""
        from nikita.agents.text.timing import ResponseTimer

        mock_settings = MagicMock()
        mock_settings.environment = "production"  # Even production...
        mock_settings.debug = True  # ...with debug=True should return 0

        with patch('nikita.agents.text.timing.get_settings', return_value=mock_settings):
            timer = ResponseTimer()
            delay = timer.calculate_delay(chapter=3)
            assert delay == 0, f"Debug mode should return 0, got {delay}"


class TestTimingProgression:
    """Tests verifying timing gets faster through chapters."""

    def test_timing_reduces_through_chapters(self):
        """Response timing ranges should reduce as chapters progress."""
        from nikita.agents.text.timing import TIMING_RANGES

        # Ch1 should have longest delays
        ch1_max = TIMING_RANGES[1][1]
        ch3_max = TIMING_RANGES[3][1]
        ch5_max = TIMING_RANGES[5][1]

        assert ch1_max > ch3_max > ch5_max

    def test_average_delay_decreases_through_chapters(self):
        """Average delays should decrease through chapters in production."""
        from nikita.agents.text.timing import ResponseTimer

        with patch('nikita.agents.text.timing.get_settings', return_value=mock_production_settings()):
            timer = ResponseTimer()

            # Calculate average delays for chapters 1, 3, 5
            ch1_delays = [timer.calculate_delay(1) for _ in range(50)]
            ch3_delays = [timer.calculate_delay(3) for _ in range(50)]
            ch5_delays = [timer.calculate_delay(5) for _ in range(50)]

            ch1_avg = statistics.mean(ch1_delays)
            ch3_avg = statistics.mean(ch3_delays)
            ch5_avg = statistics.mean(ch5_delays)

            assert ch1_avg > ch3_avg > ch5_avg


class TestTimingRangesByChapter:
    """Tests verifying specific timing ranges for each chapter."""

    def test_ch2_timing_range(self):
        """Ch2 should have range 300-14400s (5min-4h)."""
        from nikita.agents.text.timing import TIMING_RANGES

        min_sec, max_sec = TIMING_RANGES[2]

        # 5 minutes = 300 seconds
        assert min_sec == 300
        # 4 hours = 14400 seconds
        assert max_sec == 14400

    def test_ch3_timing_range(self):
        """Ch3 should have range 300-7200s (5min-2h)."""
        from nikita.agents.text.timing import TIMING_RANGES

        min_sec, max_sec = TIMING_RANGES[3]

        # 5 minutes = 300 seconds
        assert min_sec == 300
        # 2 hours = 7200 seconds
        assert max_sec == 7200

    def test_ch4_timing_range(self):
        """Ch4 should have range 300-3600s (5min-1h)."""
        from nikita.agents.text.timing import TIMING_RANGES

        min_sec, max_sec = TIMING_RANGES[4]

        # 5 minutes = 300 seconds
        assert min_sec == 300
        # 1 hour = 3600 seconds
        assert max_sec == 3600
