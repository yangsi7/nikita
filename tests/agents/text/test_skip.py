"""Tests for SkipDecision - TDD for T5.1.

Acceptance Criteria:
- AC-5.1.1: SKIP_RATES dict maps chapter to (min_rate, max_rate)
- AC-5.1.2: Ch1 rate: 25-40% skip
- AC-5.1.3: Ch5 rate: 0-5% skip
- AC-5.1.4: `should_skip(chapter)` returns bool
- AC-5.1.5: Skip probability randomized within range each call
"""

import pytest
import statistics


class TestSkipRates:
    """Tests for SKIP_RATES constant."""

    def test_skip_module_importable(self):
        """Skip module should be importable."""
        from nikita.agents.text import skip

        assert hasattr(skip, "SKIP_RATES")
        assert hasattr(skip, "SkipDecision")

    def test_ac_5_1_1_skip_rates_is_dict(self):
        """AC-5.1.1: SKIP_RATES should be a dict mapping chapter to (min, max)."""
        from nikita.agents.text.skip import SKIP_RATES

        assert isinstance(SKIP_RATES, dict)

        # Should have entries for chapters 1-5
        for chapter in [1, 2, 3, 4, 5]:
            assert chapter in SKIP_RATES, f"Chapter {chapter} missing from SKIP_RATES"

        # Each entry should be a tuple of (min, max) rates (0-1)
        for chapter, rate_range in SKIP_RATES.items():
            assert isinstance(rate_range, tuple)
            assert len(rate_range) == 2
            min_rate, max_rate = rate_range
            assert 0 <= min_rate <= 1
            assert 0 <= max_rate <= 1
            assert min_rate <= max_rate

    def test_ac_5_1_2_ch1_skip_rate(self):
        """AC-5.1.2: Ch1 rate should be 25-40% skip."""
        from nikita.agents.text.skip import SKIP_RATES

        min_rate, max_rate = SKIP_RATES[1]

        # 25% = 0.25, 40% = 0.40
        assert min_rate == 0.25
        assert max_rate == 0.40

    def test_ac_5_1_3_ch5_skip_rate(self):
        """AC-5.1.3: Ch5 rate should be 0-5% skip."""
        from nikita.agents.text.skip import SKIP_RATES

        min_rate, max_rate = SKIP_RATES[5]

        # 0% = 0.0, 5% = 0.05
        assert min_rate == 0.0
        assert max_rate == 0.05

    def test_skip_rates_decrease_through_chapters(self):
        """Skip rates should generally decrease as chapters progress."""
        from nikita.agents.text.skip import SKIP_RATES

        # Average skip rates should decrease
        ch1_avg = (SKIP_RATES[1][0] + SKIP_RATES[1][1]) / 2
        ch3_avg = (SKIP_RATES[3][0] + SKIP_RATES[3][1]) / 2
        ch5_avg = (SKIP_RATES[5][0] + SKIP_RATES[5][1]) / 2

        assert ch1_avg > ch3_avg > ch5_avg


class TestSkipDecision:
    """Tests for SkipDecision class."""

    def test_skip_decision_class_exists(self):
        """SkipDecision class should exist."""
        from nikita.agents.text.skip import SkipDecision

        assert callable(SkipDecision)

    def test_ac_5_1_4_should_skip_returns_bool(self):
        """AC-5.1.4: should_skip(chapter) should return bool."""
        from nikita.agents.text.skip import SkipDecision

        decision = SkipDecision()
        result = decision.should_skip(chapter=1)

        assert isinstance(result, bool)

    def test_should_skip_accepts_chapter_parameter(self):
        """should_skip should accept chapter parameter."""
        from nikita.agents.text.skip import SkipDecision
        import inspect

        decision = SkipDecision()
        sig = inspect.signature(decision.should_skip)

        assert "chapter" in sig.parameters

    def test_ac_5_1_5_skip_is_randomized(self):
        """AC-5.1.5: Skip probability should be randomized within range."""
        from nikita.agents.text.skip import SkipDecision

        decision = SkipDecision()

        # Generate many samples
        samples = [decision.should_skip(chapter=1) for _ in range(1000)]

        # Should have both True and False (not deterministic)
        assert True in samples
        assert False in samples

    def test_ch1_skip_rate_within_expected_range(self):
        """Ch1 should skip 25-40% of messages."""
        from nikita.agents.text.skip import SkipDecision

        decision = SkipDecision()

        # Generate 1000 samples
        samples = [decision.should_skip(chapter=1) for _ in range(1000)]
        skip_rate = sum(samples) / len(samples)

        # Should be within 25-40% range (with some tolerance for randomness)
        assert 0.20 <= skip_rate <= 0.45, f"Ch1 skip rate {skip_rate:.2%} outside expected range"

    def test_ch5_skip_rate_within_expected_range(self):
        """Ch5 should skip 0-5% of messages."""
        from nikita.agents.text.skip import SkipDecision

        decision = SkipDecision()

        # Generate 1000 samples
        samples = [decision.should_skip(chapter=5) for _ in range(1000)]
        skip_rate = sum(samples) / len(samples)

        # Should be within 0-5% range (with some tolerance for randomness)
        assert 0.0 <= skip_rate <= 0.10, f"Ch5 skip rate {skip_rate:.2%} outside expected range"

    def test_skip_rate_varies_by_chapter(self):
        """Skip rates should vary significantly between chapters."""
        from nikita.agents.text.skip import SkipDecision

        decision = SkipDecision()

        # Generate samples for different chapters
        ch1_samples = [decision.should_skip(chapter=1) for _ in range(500)]
        ch5_samples = [decision.should_skip(chapter=5) for _ in range(500)]

        ch1_rate = sum(ch1_samples) / len(ch1_samples)
        ch5_rate = sum(ch5_samples) / len(ch5_samples)

        # Ch1 should have significantly higher skip rate than Ch5
        assert ch1_rate > ch5_rate + 0.10, "Ch1 should skip more than Ch5"

    def test_invalid_chapter_uses_default(self):
        """Invalid chapter should use a default skip rate."""
        from nikita.agents.text.skip import SkipDecision

        decision = SkipDecision()

        # Should not crash with invalid chapter
        result = decision.should_skip(chapter=0)
        assert isinstance(result, bool)

        result = decision.should_skip(chapter=6)
        assert isinstance(result, bool)


class TestSkipRatesByChapter:
    """Tests verifying specific skip rates for each chapter."""

    def test_ch2_skip_rate(self):
        """Ch2 should have rate 15-25%."""
        from nikita.agents.text.skip import SKIP_RATES

        min_rate, max_rate = SKIP_RATES[2]
        assert min_rate == 0.15
        assert max_rate == 0.25

    def test_ch3_skip_rate(self):
        """Ch3 should have rate 5-15%."""
        from nikita.agents.text.skip import SKIP_RATES

        min_rate, max_rate = SKIP_RATES[3]
        assert min_rate == 0.05
        assert max_rate == 0.15

    def test_ch4_skip_rate(self):
        """Ch4 should have rate 2-10%."""
        from nikita.agents.text.skip import SKIP_RATES

        min_rate, max_rate = SKIP_RATES[4]
        assert min_rate == 0.02
        assert max_rate == 0.10


class TestSkipConsecutiveMessages:
    """Tests for consecutive message handling."""

    def test_skip_decision_tracks_last_skip(self):
        """SkipDecision should track if last message was skipped."""
        from nikita.agents.text.skip import SkipDecision

        decision = SkipDecision()

        # Should have a way to track last skip status
        assert hasattr(decision, "last_was_skipped") or hasattr(decision, "_last_skip")

    def test_consecutive_skips_less_likely(self):
        """After a skip, next message should be less likely to skip."""
        from nikita.agents.text.skip import SkipDecision

        decision = SkipDecision()

        # Track consecutive skip patterns
        consecutive_skips = 0
        total_skips = 0
        previous_was_skip = False

        for _ in range(1000):
            result = decision.should_skip(chapter=1)
            if result:
                total_skips += 1
                # Check if previous was also a skip
                if previous_was_skip:
                    consecutive_skips += 1
            previous_was_skip = result

        # Consecutive skips should be relatively rare
        if total_skips > 0:
            consecutive_rate = consecutive_skips / total_skips
            # Should be less than normal skip rate (reduced chance after skip)
            assert consecutive_rate < 0.30, f"Consecutive skip rate {consecutive_rate:.2%} too high"
