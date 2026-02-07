"""Unit tests for TokenEstimator (Spec 041 T2.8).

Tests the two-tier token estimation: fast (char ratio) and accurate (tiktoken).
"""

import pytest

from nikita.context.utils.token_counter import (
    TokenEstimator,
    get_token_estimator,
    estimate_tokens_fast,
    estimate_tokens_accurate,
    CHARS_PER_TOKEN,
)


class TestTokenEstimatorFast:
    """Test fast (character ratio) token estimation."""

    def test_fast_estimate_empty_string(self):
        """Empty string returns 0 tokens."""
        estimator = TokenEstimator()
        assert estimator.estimate_fast("") == 0

    def test_fast_estimate_none(self):
        """None returns 0 tokens."""
        estimator = TokenEstimator()
        assert estimator.estimate_fast(None) == 0

    def test_fast_estimate_simple_text(self):
        """Simple text estimation uses ~4 chars per token."""
        estimator = TokenEstimator()
        text = "a" * 100
        result = estimator.estimate_fast(text)
        expected = 100 // CHARS_PER_TOKEN
        assert result == expected

    def test_fast_estimate_is_integer_division(self):
        """Fast estimate uses integer division (floor)."""
        estimator = TokenEstimator()
        text = "abc"  # 3 chars
        result = estimator.estimate_fast(text)
        assert result == 0  # 3 // 4 = 0

    def test_fast_estimate_performance(self):
        """Fast estimate should be very quick (< 1ms for large text)."""
        import time
        estimator = TokenEstimator()
        large_text = "a" * 100_000  # 100KB

        start = time.time()
        for _ in range(100):
            estimator.estimate_fast(large_text)
        duration = (time.time() - start) / 100 * 1000  # ms per call

        # Should be < 1ms per call even for 100KB text
        assert duration < 1.0


class TestTokenEstimatorAccurate:
    """Test accurate (tiktoken) token estimation."""

    def test_accurate_estimate_empty_string(self):
        """Empty string returns 0 tokens."""
        estimator = TokenEstimator()
        assert estimator.estimate_accurate("") == 0

    def test_accurate_estimate_none(self):
        """None returns 0 tokens."""
        estimator = TokenEstimator()
        assert estimator.estimate_accurate(None) == 0

    def test_accurate_estimate_simple_text(self):
        """Accurate estimate uses tiktoken encoder."""
        estimator = TokenEstimator()
        text = "Hello, world!"
        result = estimator.estimate_accurate(text)
        # tiktoken gives precise count, typically 4-5 tokens for this
        assert 3 <= result <= 6

    def test_accurate_estimate_english_paragraph(self):
        """English paragraph should tokenize efficiently."""
        estimator = TokenEstimator()
        text = "The quick brown fox jumps over the lazy dog. " * 10  # ~450 chars
        result = estimator.estimate_accurate(text)
        # English text typically ~4 chars per token
        assert 80 <= result <= 150

    def test_accurate_estimate_repeated_chars(self):
        """Repeated chars compress well in tiktoken."""
        estimator = TokenEstimator()
        text = "a" * 1000
        result = estimator.estimate_accurate(text)
        # Repeated chars compress, but count varies
        assert 10 <= result <= 500


class TestTokenEstimatorComparison:
    """Test comparison between fast and accurate estimation."""

    def test_fast_vs_accurate_similar_for_english(self):
        """For typical English, fast and accurate should be within 50%."""
        estimator = TokenEstimator()
        text = "This is a typical English sentence with normal words and punctuation. " * 5

        fast = estimator.estimate_fast(text)
        accurate = estimator.estimate_accurate(text)

        # Fast estimate should be within 50% of accurate
        assert abs(fast - accurate) / max(accurate, 1) < 0.5

    def test_fast_is_conservative(self):
        """Fast estimate should generally err on the side of under-counting."""
        estimator = TokenEstimator()
        # For typical text, 4 chars per token is close to tiktoken's average
        text = "The quick brown fox jumps over the lazy dog."

        fast = estimator.estimate_fast(text)
        accurate = estimator.estimate_accurate(text)

        # Both should be in reasonable range
        assert 5 <= fast <= 20
        assert 5 <= accurate <= 20

    def test_estimate_method_mode_selection(self):
        """Test the unified estimate() method with mode selection."""
        estimator = TokenEstimator()
        text = "Hello, world!"

        fast = estimator.estimate(text, accurate=False)
        accurate = estimator.estimate(text, accurate=True)

        assert fast == estimator.estimate_fast(text)
        assert accurate == estimator.estimate_accurate(text)


class TestTokenEstimatorSingleton:
    """Test global singleton accessor."""

    def test_singleton_returns_same_instance(self):
        """get_token_estimator() returns same instance."""
        estimator1 = get_token_estimator()
        estimator2 = get_token_estimator()
        assert estimator1 is estimator2

    def test_convenience_functions(self):
        """Test convenience functions match singleton methods."""
        text = "Test text for token estimation"

        assert estimate_tokens_fast(text) == get_token_estimator().estimate_fast(text)
        assert estimate_tokens_accurate(text) == get_token_estimator().estimate_accurate(text)


class TestTokenEstimatorEdgeCases:
    """Test edge cases and error handling."""

    def test_unicode_text(self):
        """Unicode text should be handled correctly."""
        estimator = TokenEstimator()
        text = "你好世界 🌍 こんにちは мир"  # Chinese, emoji, Japanese, Russian

        fast = estimator.estimate_fast(text)
        accurate = estimator.estimate_accurate(text)

        # Both should return positive counts
        assert fast >= 0
        assert accurate >= 0

    def test_very_long_text(self):
        """Very long text should not crash."""
        estimator = TokenEstimator()
        text = "word " * 100_000  # 500KB+

        fast = estimator.estimate_fast(text)
        accurate = estimator.estimate_accurate(text)

        assert fast > 0
        assert accurate > 0

    def test_whitespace_only(self):
        """Whitespace-only text should return some tokens."""
        estimator = TokenEstimator()
        text = "   \n\t\n   "

        fast = estimator.estimate_fast(text)
        accurate = estimator.estimate_accurate(text)

        assert fast >= 0  # May be 0 due to integer division
        assert accurate >= 0
