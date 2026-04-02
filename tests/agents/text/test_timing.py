"""Tests for ResponseTimer — Spec 204: Engagement-Aware Timing.

Original TDD for T4.1, updated for Spec 204 T1+T2:
- T1: Recalibrated timing ranges + first-message path
- T2: Engagement-aware timing multiplier + feature flag + clamping

Acceptance Criteria:
- AC-T1.1: TIMING_RANGES Ch1=(5,45), Ch2=(15,180), Ch3=(30,600), Ch4=(60,1800), Ch5=(120,3600)
- AC-T1.2: FIRST_MESSAGE_DELAY = (5, 30)
- AC-T1.3: calculate_delay() backward-compatible signature
- AC-T1.4: is_first_message=True returns delay in (5, 30)
- AC-T1.5: Dev mode bypass preserved
- AC-T1.6: Gaussian distribution preserved
- AC-T1.7: 5 range assertion tests pass
- AC-T1.8: First-message test passes (seeded random)
- AC-T2.1: ENGAGEMENT_TIMING_MULTIPLIERS dict with 6 states
- AC-T2.2: engagement_state applied as multiplier
- AC-T2.3: None defaults to 1.0
- AC-T2.4: Clamped to [0, chapter_max * 2]
- AC-T2.5: Feature flag gates multiplier
- AC-T2.6: settings.py has engagement_aware_timing field
- AC-T2.7: 30 parametrized tests pass (5x6 matrix)
- AC-T2.8: Clamping boundary tests pass
- AC-T2.9: [TIMING] log emitted
"""

import random
import statistics

import pytest
from unittest.mock import patch, MagicMock


def mock_production_settings(**overrides):
    """Create mock settings that simulate production mode."""
    mock_settings = MagicMock()
    mock_settings.environment = "production"
    mock_settings.debug = False
    mock_settings.engagement_aware_timing = True
    for k, v in overrides.items():
        setattr(mock_settings, k, v)
    return mock_settings


def mock_development_settings():
    """Create mock settings that simulate development mode."""
    mock_settings = MagicMock()
    mock_settings.environment = "development"
    mock_settings.debug = False
    mock_settings.engagement_aware_timing = True
    return mock_settings


# ==============================================================================
# T1: Timing Ranges + First-Message Path
# ==============================================================================


class TestTimingRanges:
    """AC-T1.1: TIMING_RANGES recalibrated for Spec 204."""

    def test_timing_module_importable(self):
        """Timing module should be importable."""
        from nikita.agents.text import timing

        assert hasattr(timing, "TIMING_RANGES")
        assert hasattr(timing, "ResponseTimer")

    def test_ac_t1_1_ch1_range(self):
        """AC-T1.1/T1.7: Ch1 range = (5, 45)."""
        from nikita.agents.text.timing import TIMING_RANGES

        assert TIMING_RANGES[1] == (5, 45)

    def test_ac_t1_1_ch2_range(self):
        """AC-T1.1/T1.7: Ch2 range = (15, 180)."""
        from nikita.agents.text.timing import TIMING_RANGES

        assert TIMING_RANGES[2] == (15, 180)

    def test_ac_t1_1_ch3_range(self):
        """AC-T1.1/T1.7: Ch3 range = (30, 600)."""
        from nikita.agents.text.timing import TIMING_RANGES

        assert TIMING_RANGES[3] == (30, 600)

    def test_ac_t1_1_ch4_range(self):
        """AC-T1.1/T1.7: Ch4 range = (60, 1800)."""
        from nikita.agents.text.timing import TIMING_RANGES

        assert TIMING_RANGES[4] == (60, 1800)

    def test_ac_t1_1_ch5_range(self):
        """AC-T1.1/T1.7: Ch5 range = (120, 3600)."""
        from nikita.agents.text.timing import TIMING_RANGES

        assert TIMING_RANGES[5] == (120, 3600)

    def test_timing_ranges_is_dict_with_5_chapters(self):
        """TIMING_RANGES should have exactly chapters 1-5."""
        from nikita.agents.text.timing import TIMING_RANGES

        assert isinstance(TIMING_RANGES, dict)
        assert set(TIMING_RANGES.keys()) == {1, 2, 3, 4, 5}

    def test_all_ranges_min_less_than_max(self):
        """Every range should have min < max."""
        from nikita.agents.text.timing import TIMING_RANGES

        for ch, (min_sec, max_sec) in TIMING_RANGES.items():
            assert min_sec < max_sec, f"Ch{ch}: min={min_sec} >= max={max_sec}"


class TestFirstMessageDelay:
    """AC-T1.2, AC-T1.4, AC-T1.8: First-message path."""

    def test_ac_t1_2_first_message_delay_constant(self):
        """AC-T1.2: FIRST_MESSAGE_DELAY = (5, 30)."""
        from nikita.agents.text.timing import FIRST_MESSAGE_DELAY

        assert FIRST_MESSAGE_DELAY == (5, 30)

    def test_ac_t1_4_first_message_returns_fast_delay(self):
        """AC-T1.4: is_first_message=True returns delay in (5, 30)."""
        from nikita.agents.text.timing import ResponseTimer

        with patch('nikita.agents.text.timing.get_settings', return_value=mock_production_settings()):
            timer = ResponseTimer()
            for _ in range(50):
                delay = timer.calculate_delay(chapter=5, is_first_message=True)
                assert 5 <= delay <= 30, f"First-message delay {delay} not in [5, 30]"

    def test_ac_t1_8_first_message_seeded_random(self):
        """AC-T1.8: First-message test with seeded random."""
        from nikita.agents.text.timing import ResponseTimer

        with patch('nikita.agents.text.timing.get_settings', return_value=mock_production_settings()):
            random.seed(42)
            timer = ResponseTimer()
            delay = timer.calculate_delay(chapter=1, is_first_message=True)
            assert 5 <= delay <= 30
            assert isinstance(delay, int)

    def test_first_message_ignores_chapter(self):
        """First-message delay should be the same range regardless of chapter."""
        from nikita.agents.text.timing import ResponseTimer

        with patch('nikita.agents.text.timing.get_settings', return_value=mock_production_settings()):
            timer = ResponseTimer()
            for ch in [1, 2, 3, 4, 5]:
                for _ in range(20):
                    delay = timer.calculate_delay(chapter=ch, is_first_message=True)
                    assert 5 <= delay <= 30, f"Ch{ch} first-message delay {delay} not in [5, 30]"

    def test_first_message_ignores_engagement_state(self):
        """First-message delay should not be affected by engagement multiplier."""
        from nikita.agents.text.timing import ResponseTimer

        with patch('nikita.agents.text.timing.get_settings', return_value=mock_production_settings()):
            timer = ResponseTimer()
            for _ in range(20):
                delay = timer.calculate_delay(
                    chapter=3, engagement_state="clingy", is_first_message=True
                )
                assert 5 <= delay <= 30


class TestCalculateDelaySignature:
    """AC-T1.3: Backward-compatible signature."""

    def test_ac_t1_3_old_signature_works(self):
        """AC-T1.3: calculate_delay(chapter) still works (backward-compatible)."""
        from nikita.agents.text.timing import ResponseTimer

        with patch('nikita.agents.text.timing.get_settings', return_value=mock_production_settings()):
            timer = ResponseTimer()
            delay = timer.calculate_delay(chapter=1)
            assert isinstance(delay, int)

    def test_ac_t1_3_new_params_are_optional(self):
        """AC-T1.3: engagement_state and is_first_message are optional."""
        from nikita.agents.text.timing import ResponseTimer

        with patch('nikita.agents.text.timing.get_settings', return_value=mock_production_settings()):
            timer = ResponseTimer()
            # All three call forms should work
            timer.calculate_delay(chapter=1)
            timer.calculate_delay(chapter=1, engagement_state="in_zone")
            timer.calculate_delay(chapter=1, is_first_message=True)
            timer.calculate_delay(chapter=1, engagement_state="drifting", is_first_message=False)


class TestDevModeBypass:
    """AC-T1.5: Dev mode bypass preserved."""

    def test_ac_t1_5_development_mode_returns_zero(self):
        """Dev mode should return 0 for all chapters."""
        from nikita.agents.text.timing import ResponseTimer

        with patch('nikita.agents.text.timing.get_settings', return_value=mock_development_settings()):
            timer = ResponseTimer()
            for ch in [1, 2, 3, 4, 5]:
                assert timer.calculate_delay(chapter=ch) == 0

    def test_debug_mode_returns_zero(self):
        """Debug mode should return 0."""
        from nikita.agents.text.timing import ResponseTimer

        settings = mock_production_settings(debug=True)
        with patch('nikita.agents.text.timing.get_settings', return_value=settings):
            timer = ResponseTimer()
            assert timer.calculate_delay(chapter=3) == 0

    def test_dev_mode_first_message_returns_zero(self):
        """Dev mode + first message should still return 0."""
        from nikita.agents.text.timing import ResponseTimer

        with patch('nikita.agents.text.timing.get_settings', return_value=mock_development_settings()):
            timer = ResponseTimer()
            assert timer.calculate_delay(chapter=1, is_first_message=True) == 0


class TestGaussianDistribution:
    """AC-T1.6: Gaussian distribution preserved."""

    def test_ac_t1_6_distribution_not_uniform(self):
        """Middle third should have more samples than edges (gaussian)."""
        from nikita.agents.text.timing import ResponseTimer, TIMING_RANGES

        with patch('nikita.agents.text.timing.get_settings', return_value=mock_production_settings()):
            timer = ResponseTimer()
            samples = [timer.calculate_delay(chapter=3) for _ in range(500)]

            min_sec, max_sec = TIMING_RANGES[3]
            range_size = max_sec - min_sec
            third = range_size / 3

            lower = sum(1 for s in samples if s < min_sec + third)
            middle = sum(1 for s in samples if min_sec + third <= s < min_sec + 2 * third)
            upper = sum(1 for s in samples if s >= min_sec + 2 * third)

            assert middle > lower, "Middle should be denser than lower"
            assert middle > upper, "Middle should be denser than upper"

    def test_jitter_prevents_patterns(self):
        """Jitter should produce many unique values."""
        from nikita.agents.text.timing import ResponseTimer

        with patch('nikita.agents.text.timing.get_settings', return_value=mock_production_settings()):
            timer = ResponseTimer()
            samples = [timer.calculate_delay(chapter=2) for _ in range(100)]
            unique = set(samples)
            assert len(unique) >= 30, f"Only {len(unique)} unique, expected more"

    def test_delays_within_range(self):
        """All delays should be within chapter range."""
        from nikita.agents.text.timing import ResponseTimer, TIMING_RANGES

        with patch('nikita.agents.text.timing.get_settings', return_value=mock_production_settings()):
            timer = ResponseTimer()
            for ch in [1, 2, 3, 4, 5]:
                min_sec, max_sec = TIMING_RANGES[ch]
                for _ in range(50):
                    delay = timer.calculate_delay(chapter=ch)
                    assert min_sec <= delay <= max_sec, \
                        f"Ch{ch} delay {delay} not in [{min_sec}, {max_sec}]"


class TestTimingProgression:
    """Timing ranges should increase through chapters (engagement-aware model)."""

    def test_timing_increases_through_chapters(self):
        """Later chapters should have longer max delays."""
        from nikita.agents.text.timing import TIMING_RANGES

        ch1_max = TIMING_RANGES[1][1]
        ch3_max = TIMING_RANGES[3][1]
        ch5_max = TIMING_RANGES[5][1]

        assert ch1_max < ch3_max < ch5_max

    def test_average_delay_increases_through_chapters(self):
        """Average delays should increase through chapters."""
        from nikita.agents.text.timing import ResponseTimer

        with patch('nikita.agents.text.timing.get_settings', return_value=mock_production_settings()):
            timer = ResponseTimer()
            ch1_avg = statistics.mean([timer.calculate_delay(1) for _ in range(50)])
            ch3_avg = statistics.mean([timer.calculate_delay(3) for _ in range(50)])
            ch5_avg = statistics.mean([timer.calculate_delay(5) for _ in range(50)])

            assert ch1_avg < ch3_avg < ch5_avg


# ==============================================================================
# T2: Engagement-Aware Timing Multiplier
# ==============================================================================

ENGAGEMENT_STATES = ["calibrating", "in_zone", "drifting", "clingy", "distant", "out_of_zone"]
EXPECTED_MULTIPLIERS = {
    "calibrating": 0.5,
    "in_zone": 1.0,
    "drifting": 0.3,
    "clingy": 1.5,
    "distant": 0.1,
    "out_of_zone": 0.2,
}


class TestEngagementTimingMultipliers:
    """AC-T2.1: ENGAGEMENT_TIMING_MULTIPLIERS dict."""

    def test_ac_t2_1_multipliers_dict_exists(self):
        """AC-T2.1: ENGAGEMENT_TIMING_MULTIPLIERS should exist with 6 states."""
        from nikita.agents.text.timing import ENGAGEMENT_TIMING_MULTIPLIERS

        assert isinstance(ENGAGEMENT_TIMING_MULTIPLIERS, dict)
        assert len(ENGAGEMENT_TIMING_MULTIPLIERS) == 6

    @pytest.mark.parametrize("state,expected", list(EXPECTED_MULTIPLIERS.items()))
    def test_ac_t2_1_multiplier_values(self, state, expected):
        """AC-T2.1: Each state should have the correct multiplier."""
        from nikita.agents.text.timing import ENGAGEMENT_TIMING_MULTIPLIERS

        assert ENGAGEMENT_TIMING_MULTIPLIERS[state] == expected


class TestEngagementMultiplierApplication:
    """AC-T2.2, AC-T2.3: Multiplier applied to base delay."""

    def test_ac_t2_3_none_defaults_to_1_0(self):
        """AC-T2.3: None engagement_state defaults to multiplier 1.0."""
        from nikita.agents.text.timing import ResponseTimer, TIMING_RANGES

        with patch('nikita.agents.text.timing.get_settings', return_value=mock_production_settings()):
            random.seed(42)
            timer = ResponseTimer()
            delay_none = timer.calculate_delay(chapter=3, engagement_state=None)

            random.seed(42)
            delay_in_zone = timer.calculate_delay(chapter=3, engagement_state="in_zone")

            # Both should be equal since in_zone=1.0 and None defaults to 1.0
            assert delay_none == delay_in_zone

    def test_ac_t2_2_clingy_increases_delay(self):
        """AC-T2.2: clingy (1.5x) should produce longer delays than in_zone (1.0x)."""
        from nikita.agents.text.timing import ResponseTimer

        with patch('nikita.agents.text.timing.get_settings', return_value=mock_production_settings()):
            timer = ResponseTimer()
            clingy_delays = []
            in_zone_delays = []
            for _ in range(100):
                clingy_delays.append(timer.calculate_delay(chapter=3, engagement_state="clingy"))
                in_zone_delays.append(timer.calculate_delay(chapter=3, engagement_state="in_zone"))

            assert statistics.mean(clingy_delays) > statistics.mean(in_zone_delays)

    def test_ac_t2_2_distant_decreases_delay(self):
        """AC-T2.2: distant (0.1x) should produce shorter delays than in_zone (1.0x)."""
        from nikita.agents.text.timing import ResponseTimer

        with patch('nikita.agents.text.timing.get_settings', return_value=mock_production_settings()):
            timer = ResponseTimer()
            distant_delays = []
            in_zone_delays = []
            for _ in range(100):
                distant_delays.append(timer.calculate_delay(chapter=3, engagement_state="distant"))
                in_zone_delays.append(timer.calculate_delay(chapter=3, engagement_state="in_zone"))

            assert statistics.mean(distant_delays) < statistics.mean(in_zone_delays)


class TestEngagementClamping:
    """AC-T2.4: Final delay clamped to [0, chapter_max * 2]."""

    def test_ac_t2_4_delay_never_negative(self):
        """Delay should never be negative."""
        from nikita.agents.text.timing import ResponseTimer

        with patch('nikita.agents.text.timing.get_settings', return_value=mock_production_settings()):
            timer = ResponseTimer()
            for _ in range(100):
                delay = timer.calculate_delay(chapter=1, engagement_state="distant")
                assert delay >= 0, f"Delay should not be negative: {delay}"

    def test_ac_t2_4_delay_clamped_to_2x_max(self):
        """Delay should never exceed chapter_max * 2."""
        from nikita.agents.text.timing import ResponseTimer, TIMING_RANGES

        with patch('nikita.agents.text.timing.get_settings', return_value=mock_production_settings()):
            timer = ResponseTimer()
            for ch in [1, 2, 3, 4, 5]:
                _, max_sec = TIMING_RANGES[ch]
                upper_bound = max_sec * 2
                for _ in range(50):
                    delay = timer.calculate_delay(chapter=ch, engagement_state="clingy")
                    assert delay <= upper_bound, \
                        f"Ch{ch} delay {delay} exceeds 2x max {upper_bound}"


class TestEngagementFeatureFlag:
    """AC-T2.5, AC-T2.6: Feature flag gates multiplier."""

    def test_ac_t2_6_settings_has_flag(self):
        """AC-T2.6: settings.py should have engagement_aware_timing field."""
        from nikita.config.settings import Settings

        s = Settings(engagement_aware_timing=True)
        assert s.engagement_aware_timing is True

        s2 = Settings(engagement_aware_timing=False)
        assert s2.engagement_aware_timing is False

    def test_ac_t2_5_flag_false_ignores_multiplier(self):
        """AC-T2.5: When engagement_aware_timing=False, multiplier=1.0."""
        from nikita.agents.text.timing import ResponseTimer

        settings_off = mock_production_settings(engagement_aware_timing=False)
        settings_on = mock_production_settings(engagement_aware_timing=True)

        with patch('nikita.agents.text.timing.get_settings', return_value=settings_off):
            random.seed(42)
            timer = ResponseTimer()
            delay_off = timer.calculate_delay(chapter=3, engagement_state="distant")

        with patch('nikita.agents.text.timing.get_settings', return_value=settings_on):
            random.seed(42)
            timer2 = ResponseTimer()
            delay_on = timer2.calculate_delay(chapter=3, engagement_state="distant")

        # With flag off, distant multiplier (0.1x) should NOT apply
        # So delay_off should be larger (normal timing)
        # delay_on should be much smaller (0.1x multiplier)
        assert delay_off > delay_on


class TestEngagementParametrized:
    """AC-T2.7: 30 parametrized tests (5 chapters x 6 states)."""

    @pytest.mark.parametrize("chapter", [1, 2, 3, 4, 5])
    @pytest.mark.parametrize("state", ENGAGEMENT_STATES)
    def test_ac_t2_7_chapter_state_matrix(self, chapter, state):
        """AC-T2.7: Each chapter+state combo produces valid delay."""
        from nikita.agents.text.timing import ResponseTimer, TIMING_RANGES

        with patch('nikita.agents.text.timing.get_settings', return_value=mock_production_settings()):
            random.seed(42)
            timer = ResponseTimer()
            delay = timer.calculate_delay(chapter=chapter, engagement_state=state)

            _, max_sec = TIMING_RANGES[chapter]
            assert isinstance(delay, int)
            assert 0 <= delay <= max_sec * 2, \
                f"Ch{chapter}/{state}: delay={delay} out of bounds [0, {max_sec * 2}]"


class TestTimingLog:
    """AC-T2.9: [TIMING] log emitted."""

    def test_ac_t2_9_timing_log_emitted(self):
        """AC-T2.9: [TIMING] log emitted with chapter, engagement, base, final."""
        from nikita.agents.text.timing import ResponseTimer
        import logging

        with patch('nikita.agents.text.timing.get_settings', return_value=mock_production_settings()):
            timer = ResponseTimer()
            with patch('nikita.agents.text.timing.logger') as mock_logger:
                timer.calculate_delay(chapter=3, engagement_state="drifting")
                # Should have logged at least one info message containing [TIMING]
                log_calls = mock_logger.info.call_args_list
                log_messages = [str(call) for call in log_calls]
                assert any("[TIMING]" in msg for msg in log_messages), \
                    f"No [TIMING] log found in: {log_messages}"
