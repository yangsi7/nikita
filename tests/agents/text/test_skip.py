"""Tests for SkipDecision - TDD for T5.1.

Acceptance Criteria:
- AC-5.1.1: SKIP_RATES dict maps chapter to (min_rate, max_rate)
- AC-5.1.4: `should_skip(chapter)` returns bool

NOTE: Skip functionality is currently DISABLED (all rates = 0).
Future: Message scheduling engine via pg_cron will handle response timing.
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

    def test_skip_rates_have_correct_values(self):
        """Skip rates should decrease by chapter (R-3)."""
        from nikita.agents.text.skip import SKIP_RATES

        # Ch1 has highest skip rates, Ch5 lowest
        assert SKIP_RATES[1] == (0.25, 0.40)
        assert SKIP_RATES[2] == (0.15, 0.25)
        assert SKIP_RATES[3] == (0.05, 0.15)
        assert SKIP_RATES[4] == (0.02, 0.10)
        assert SKIP_RATES[5] == (0.00, 0.05)

        # Rates decrease monotonically
        for ch in range(1, 5):
            assert SKIP_RATES[ch][0] >= SKIP_RATES[ch + 1][0]
            assert SKIP_RATES[ch][1] >= SKIP_RATES[ch + 1][1]

    def test_skip_rates_disabled_dict_is_all_zero(self):
        """SKIP_RATES_DISABLED should all be 0 (used when flag OFF)."""
        from nikita.agents.text.skip import SKIP_RATES_DISABLED

        for chapter in [1, 2, 3, 4, 5]:
            min_rate, max_rate = SKIP_RATES_DISABLED[chapter]
            assert min_rate == 0.0, f"Chapter {chapter} min_rate should be 0"
            assert max_rate == 0.0, f"Chapter {chapter} max_rate should be 0"


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

    def test_skip_never_triggered_when_disabled(self):
        """With 0% skip rates, should_skip should always return False."""
        from nikita.agents.text.skip import SkipDecision

        decision = SkipDecision()

        # Test all chapters - none should skip
        for chapter in [1, 2, 3, 4, 5]:
            samples = [decision.should_skip(chapter=chapter) for _ in range(100)]
            skip_count = sum(samples)
            assert skip_count == 0, f"Chapter {chapter} should never skip (got {skip_count}/100)"

    def test_invalid_chapter_uses_default(self):
        """Invalid chapter should use a default skip rate (also 0)."""
        from nikita.agents.text.skip import SkipDecision

        decision = SkipDecision()

        # Should not crash with invalid chapter
        result = decision.should_skip(chapter=0)
        assert isinstance(result, bool)
        assert result is False  # Default is also disabled

        result = decision.should_skip(chapter=6)
        assert isinstance(result, bool)
        assert result is False  # Default is also disabled


class TestSkipConsecutiveMessages:
    """Tests for consecutive message handling."""

    def test_skip_decision_tracks_last_skip(self):
        """SkipDecision should track if last message was skipped."""
        from nikita.agents.text.skip import SkipDecision

        decision = SkipDecision()

        # Should have a way to track last skip status
        assert hasattr(decision, "last_was_skipped") or hasattr(decision, "_last_skip")

    def test_no_skips_when_disabled(self):
        """With disabled skip rates, no messages should be skipped."""
        from nikita.agents.text.skip import SkipDecision

        decision = SkipDecision()

        # Run 100 times for chapter 1 (previously highest skip rate)
        skips = 0
        for _ in range(100):
            if decision.should_skip(chapter=1):
                skips += 1

        assert skips == 0, f"Should have 0 skips when disabled, got {skips}"
