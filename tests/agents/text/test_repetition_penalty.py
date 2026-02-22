"""Tests for semantic repetition penalty in SkipDecision (Spec 101 FR-005).

AC-T5.1: REPETITION_SIMILARITY_THRESHOLD constant = 0.7
AC-T5.2: has_repetition() method detects similar messages
AC-T5.3: should_skip() applies penalty boost when repetition detected
"""

import pytest

from nikita.agents.text.skip import (
    REPETITION_SIMILARITY_THRESHOLD,
    SkipDecision,
)


class TestRepetitionConstants:
    """Test repetition penalty constants."""

    def test_similarity_threshold_is_0_7(self):
        """AC-T5.1: Threshold is 0.7."""
        assert REPETITION_SIMILARITY_THRESHOLD == 0.7


class TestHasRepetition:
    """Test has_repetition() method."""

    def test_identical_message_detected(self):
        """AC-T5.2: Identical message = repetition."""
        decision = SkipDecision()
        recent = ["Hello, how are you?", "What's up?", "Tell me more"]

        assert decision.has_repetition("Hello, how are you?", recent) is True

    def test_very_similar_message_detected(self):
        """AC-T5.2: Very similar message (>0.7) = repetition."""
        decision = SkipDecision()
        recent = ["Hello, how are you doing today?"]

        # "Hello, how are you doing?" is very similar
        assert decision.has_repetition("Hello, how are you doing?", recent) is True

    def test_different_message_not_flagged(self):
        """AC-T5.2: Different message (<0.7 similarity) = no repetition."""
        decision = SkipDecision()
        recent = ["Hello, how are you?"]

        assert decision.has_repetition("What's for dinner tonight?", recent) is False

    def test_empty_recent_messages_no_repetition(self):
        """AC-T5.2: Empty recent list = no repetition."""
        decision = SkipDecision()

        assert decision.has_repetition("Hello", []) is False

    def test_case_insensitive_comparison(self):
        """AC-T5.2: Comparison is case-insensitive."""
        decision = SkipDecision()
        recent = ["hello how are you"]

        assert decision.has_repetition("Hello How Are You", recent) is True

    def test_checks_all_recent_messages(self):
        """AC-T5.2: Checks against all messages in recent list."""
        decision = SkipDecision()
        recent = [
            "Something completely different",
            "Another different thing",
            "Hello, how are you doing today?",  # Similar to input
        ]

        assert decision.has_repetition("Hello, how are you doing?", recent) is True


class TestRepetitionPenaltyIntegration:
    """Test that repetition boosts skip probability."""

    def test_repetition_increases_skip_rate(self):
        """AC-T5.3: With repetition, skip probability is boosted."""
        from unittest.mock import MagicMock, patch

        mock_settings = MagicMock()
        mock_settings.skip_rates_enabled = True

        skip_count_with_rep = 0
        skip_count_without_rep = 0
        trials = 1000

        # Enable skip rates for this test
        with patch(
            "nikita.config.settings.get_settings", return_value=mock_settings,
        ):
            # Trials without repetition
            for _ in range(trials):
                decision = SkipDecision()
                result = decision.should_skip(chapter=3, recent_messages=[])
                if result:
                    skip_count_without_rep += 1

            # Trials with repetition (identical recent message)
            for _ in range(trials):
                decision = SkipDecision()
                result = decision.should_skip(
                    chapter=3,
                    recent_messages=["Hello there"],
                    current_message="Hello there",
                )
                if result:
                    skip_count_with_rep += 1

        # Repetition should cause more skips (statistically)
        # This is a probabilistic test; use generous margin
        assert skip_count_with_rep > skip_count_without_rep

    def test_should_skip_accepts_optional_params(self):
        """should_skip() works with and without new params (backward compat)."""
        from unittest.mock import MagicMock, patch

        mock_settings = MagicMock()
        mock_settings.skip_rates_enabled = False

        with patch(
            "nikita.config.settings.get_settings", return_value=mock_settings,
        ):
            decision = SkipDecision()

            # Old signature: just chapter
            result1 = decision.should_skip(chapter=1)
            assert isinstance(result1, bool)

            # New signature: with optional params
            result2 = decision.should_skip(
                chapter=1,
                recent_messages=["Hi"],
                current_message="Hi",
            )
            assert isinstance(result2, bool)
