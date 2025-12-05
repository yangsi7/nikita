"""Tests for Engagement Detection Phase 2: Detectors.

TDD tests for spec 014 - T2.1 through T2.3.
Tests written FIRST, implementation follows.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest


# ==============================================================================
# T2.1: ClinginessDetector Tests
# ==============================================================================


class TestClinginessDetectorClass:
    """Tests for ClinginessDetector class structure (AC-2.1.1)."""

    def test_ac_2_1_1_class_exists_in_detection_module(self):
        """AC-2.1.1: ClinginessDetector class in detection.py."""
        from nikita.engine.engagement.detection import ClinginessDetector

        assert ClinginessDetector is not None

    def test_clinginess_detector_has_detect_method(self):
        """ClinginessDetector has detect() method."""
        from nikita.engine.engagement.detection import ClinginessDetector

        detector = ClinginessDetector()
        assert hasattr(detector, "detect")
        assert callable(detector.detect)


class TestClinginessFrequencySignal:
    """Tests for clinginess frequency signal (AC-2.1.2)."""

    def test_ac_2_1_2_frequency_signal_method_exists(self):
        """AC-2.1.2: _frequency_signal() compares to clinginess_threshold."""
        from nikita.engine.engagement.detection import ClinginessDetector

        detector = ClinginessDetector()
        assert hasattr(detector, "_frequency_signal")

    def test_frequency_signal_returns_decimal(self):
        """Frequency signal returns Decimal 0-1."""
        from nikita.engine.engagement.detection import ClinginessDetector

        detector = ClinginessDetector()
        # 30 messages per day is excessive (optimal is ~10-15 for chapter 1)
        result = detector._frequency_signal(
            messages_per_day=30,
            optimal_frequency=15,
            chapter=1,
        )
        assert isinstance(result, Decimal)
        assert Decimal("0") <= result <= Decimal("1")

    def test_frequency_signal_high_when_excessive(self):
        """High frequency (2x+ optimal) returns high signal."""
        from nikita.engine.engagement.detection import ClinginessDetector

        detector = ClinginessDetector()
        # 30 messages when optimal is 15 = 2x over
        result = detector._frequency_signal(
            messages_per_day=30,
            optimal_frequency=15,
            chapter=1,
        )
        assert result >= Decimal("0.5")

    def test_frequency_signal_low_when_normal(self):
        """Normal frequency returns low signal."""
        from nikita.engine.engagement.detection import ClinginessDetector

        detector = ClinginessDetector()
        # 15 messages when optimal is 15 = exactly right
        result = detector._frequency_signal(
            messages_per_day=15,
            optimal_frequency=15,
            chapter=1,
        )
        assert result <= Decimal("0.3")


class TestClinginessDoubleTextSignal:
    """Tests for double-text detection (AC-2.1.3)."""

    def test_ac_2_1_3_double_text_signal_method_exists(self):
        """AC-2.1.3: _double_text_signal() detects multiple messages before response."""
        from nikita.engine.engagement.detection import ClinginessDetector

        detector = ClinginessDetector()
        assert hasattr(detector, "_double_text_signal")

    def test_double_text_high_with_many_consecutive(self):
        """Many consecutive messages without response = high signal."""
        from nikita.engine.engagement.detection import ClinginessDetector

        detector = ClinginessDetector()
        # 5 messages before Nikita responded
        result = detector._double_text_signal(
            consecutive_messages=5,
            total_exchanges=10,
        )
        assert result >= Decimal("0.5")

    def test_double_text_low_with_normal_pattern(self):
        """Normal back-and-forth = low signal."""
        from nikita.engine.engagement.detection import ClinginessDetector

        detector = ClinginessDetector()
        # 1 message per exchange (normal)
        result = detector._double_text_signal(
            consecutive_messages=1,
            total_exchanges=10,
        )
        assert result <= Decimal("0.2")


class TestClinginessResponseTimeSignal:
    """Tests for response time signal (AC-2.1.4)."""

    def test_ac_2_1_4_response_time_signal_method_exists(self):
        """AC-2.1.4: _response_time_signal() flags < 30 second responses."""
        from nikita.engine.engagement.detection import ClinginessDetector

        detector = ClinginessDetector()
        assert hasattr(detector, "_response_time_signal")

    def test_response_time_high_when_instant(self):
        """Instant responses (< 30s) = high signal."""
        from nikita.engine.engagement.detection import ClinginessDetector

        detector = ClinginessDetector()
        # Average response time 15 seconds
        result = detector._response_time_signal(
            avg_response_seconds=15,
        )
        assert result >= Decimal("0.7")

    def test_response_time_low_when_normal(self):
        """Normal response times (5+ minutes) = low signal."""
        from nikita.engine.engagement.detection import ClinginessDetector

        detector = ClinginessDetector()
        # Average response time 5 minutes
        result = detector._response_time_signal(
            avg_response_seconds=300,
        )
        assert result <= Decimal("0.2")


class TestClinginessLengthRatioSignal:
    """Tests for message length ratio (AC-2.1.5)."""

    def test_ac_2_1_5_length_ratio_signal_method_exists(self):
        """AC-2.1.5: _length_ratio_signal() compares to Nikita's average."""
        from nikita.engine.engagement.detection import ClinginessDetector

        detector = ClinginessDetector()
        assert hasattr(detector, "_length_ratio_signal")

    def test_length_ratio_high_when_excessive(self):
        """Long messages compared to Nikita = high signal."""
        from nikita.engine.engagement.detection import ClinginessDetector

        detector = ClinginessDetector()
        # User writes 3x more than Nikita
        result = detector._length_ratio_signal(
            user_avg_length=300,
            nikita_avg_length=100,
        )
        assert result >= Decimal("0.5")

    def test_length_ratio_low_when_balanced(self):
        """Balanced message lengths = low signal."""
        from nikita.engine.engagement.detection import ClinginessDetector

        detector = ClinginessDetector()
        result = detector._length_ratio_signal(
            user_avg_length=100,
            nikita_avg_length=100,
        )
        assert result <= Decimal("0.2")


class TestClinginessDetectMethod:
    """Tests for composite detection (AC-2.1.6, AC-2.1.7, AC-2.1.8)."""

    def test_ac_2_1_6_detect_returns_clinginess_result(self):
        """AC-2.1.6: detect() returns ClinginessResult with score and signals."""
        from nikita.engine.engagement.detection import ClinginessDetector
        from nikita.engine.engagement.models import ClinginessResult

        detector = ClinginessDetector()
        result = detector.detect(
            messages_per_day=15,
            optimal_frequency=15,
            chapter=1,
            consecutive_messages=1,
            total_exchanges=10,
            avg_response_seconds=300,
            user_avg_length=100,
            nikita_avg_length=100,
            needy_score=Decimal("0.1"),
        )

        assert isinstance(result, ClinginessResult)
        assert hasattr(result, "score")
        assert hasattr(result, "signals")
        assert hasattr(result, "is_clingy")

    def test_ac_2_1_7_score_weights_applied(self):
        """AC-2.1.7: Score weights: frequency=0.35, double_text=0.20, response=0.15, length=0.10, needy=0.20."""
        from nikita.engine.engagement.detection import ClinginessDetector

        detector = ClinginessDetector()
        # All signals at 1.0 should give composite of 1.0
        result = detector.detect(
            messages_per_day=50,  # Very high frequency
            optimal_frequency=10,
            chapter=1,
            consecutive_messages=10,  # Many double-texts
            total_exchanges=10,
            avg_response_seconds=5,  # Instant responses
            user_avg_length=500,  # Very long messages
            nikita_avg_length=100,
            needy_score=Decimal("1.0"),  # Very needy
        )

        # Weights should sum to 1.0: 0.35 + 0.20 + 0.15 + 0.10 + 0.20 = 1.0
        assert "frequency" in result.signals
        assert "double_text" in result.signals
        assert "response_time" in result.signals
        assert "length_ratio" in result.signals
        assert "needy_language" in result.signals

    def test_ac_2_1_8_is_clingy_threshold_0_7(self):
        """AC-2.1.8: is_clingy = True when score > 0.7."""
        from nikita.engine.engagement.detection import ClinginessDetector

        detector = ClinginessDetector()

        # Low clinginess case
        low_result = detector.detect(
            messages_per_day=15,
            optimal_frequency=15,
            chapter=1,
            consecutive_messages=1,
            total_exchanges=10,
            avg_response_seconds=300,
            user_avg_length=100,
            nikita_avg_length=100,
            needy_score=Decimal("0.1"),
        )
        assert low_result.is_clingy is False

        # High clinginess case
        high_result = detector.detect(
            messages_per_day=50,
            optimal_frequency=10,
            chapter=1,
            consecutive_messages=8,
            total_exchanges=10,
            avg_response_seconds=10,
            user_avg_length=400,
            nikita_avg_length=100,
            needy_score=Decimal("0.9"),
        )
        assert high_result.is_clingy is True


# ==============================================================================
# T2.2: NeglectDetector Tests
# ==============================================================================


class TestNeglectDetectorClass:
    """Tests for NeglectDetector class structure (AC-2.2.1)."""

    def test_ac_2_2_1_class_exists_in_detection_module(self):
        """AC-2.2.1: NeglectDetector class in detection.py."""
        from nikita.engine.engagement.detection import NeglectDetector

        assert NeglectDetector is not None

    def test_neglect_detector_has_detect_method(self):
        """NeglectDetector has detect() method."""
        from nikita.engine.engagement.detection import NeglectDetector

        detector = NeglectDetector()
        assert hasattr(detector, "detect")
        assert callable(detector.detect)


class TestNeglectFrequencySignal:
    """Tests for neglect frequency signal (AC-2.2.2)."""

    def test_ac_2_2_2_frequency_signal_method_exists(self):
        """AC-2.2.2: _frequency_signal() compares to neglect_threshold."""
        from nikita.engine.engagement.detection import NeglectDetector

        detector = NeglectDetector()
        assert hasattr(detector, "_frequency_signal")

    def test_frequency_signal_high_when_too_low(self):
        """Low frequency (< half optimal) = high signal."""
        from nikita.engine.engagement.detection import NeglectDetector

        detector = NeglectDetector()
        # 3 messages when optimal is 15 = too few
        result = detector._frequency_signal(
            messages_per_day=3,
            optimal_frequency=15,
            chapter=1,
        )
        assert result >= Decimal("0.5")

    def test_frequency_signal_low_when_normal(self):
        """Normal frequency = low signal."""
        from nikita.engine.engagement.detection import NeglectDetector

        detector = NeglectDetector()
        result = detector._frequency_signal(
            messages_per_day=15,
            optimal_frequency=15,
            chapter=1,
        )
        assert result <= Decimal("0.3")


class TestNeglectResponseTimeSignal:
    """Tests for slow response detection (AC-2.2.3)."""

    def test_ac_2_2_3_response_time_signal_method_exists(self):
        """AC-2.2.3: _response_time_signal() flags > 4 hour responses."""
        from nikita.engine.engagement.detection import NeglectDetector

        detector = NeglectDetector()
        assert hasattr(detector, "_response_time_signal")

    def test_response_time_high_when_slow(self):
        """Slow responses (> 4 hours) = high signal."""
        from nikita.engine.engagement.detection import NeglectDetector

        detector = NeglectDetector()
        # Average response time 6 hours
        result = detector._response_time_signal(
            avg_response_seconds=6 * 3600,  # 6 hours
        )
        assert result >= Decimal("0.5")

    def test_response_time_low_when_normal(self):
        """Normal response times = low signal."""
        from nikita.engine.engagement.detection import NeglectDetector

        detector = NeglectDetector()
        result = detector._response_time_signal(
            avg_response_seconds=1800,  # 30 minutes
        )
        assert result <= Decimal("0.2")


class TestNeglectShortMessageSignal:
    """Tests for short message detection (AC-2.2.4)."""

    def test_ac_2_2_4_short_message_signal_method_exists(self):
        """AC-2.2.4: _short_message_signal() flags < 20 char average."""
        from nikita.engine.engagement.detection import NeglectDetector

        detector = NeglectDetector()
        assert hasattr(detector, "_short_message_signal")

    def test_short_message_high_when_terse(self):
        """Very short messages (< 20 chars) = high signal."""
        from nikita.engine.engagement.detection import NeglectDetector

        detector = NeglectDetector()
        result = detector._short_message_signal(
            avg_message_length=10,  # "ok", "k", "fine"
        )
        assert result >= Decimal("0.7")

    def test_short_message_low_when_normal(self):
        """Normal length messages = low signal."""
        from nikita.engine.engagement.detection import NeglectDetector

        detector = NeglectDetector()
        result = detector._short_message_signal(
            avg_message_length=80,  # Decent messages
        )
        assert result <= Decimal("0.2")


class TestNeglectAbruptEndingSignal:
    """Tests for abrupt ending detection (AC-2.2.5)."""

    def test_ac_2_2_5_abrupt_ending_signal_method_exists(self):
        """AC-2.2.5: _abrupt_ending_signal() detects conversation endings."""
        from nikita.engine.engagement.detection import NeglectDetector

        detector = NeglectDetector()
        assert hasattr(detector, "_abrupt_ending_signal")

    def test_abrupt_ending_high_with_many(self):
        """Many abrupt endings = high signal."""
        from nikita.engine.engagement.detection import NeglectDetector

        detector = NeglectDetector()
        # 5 abrupt endings in 10 conversations
        result = detector._abrupt_ending_signal(
            abrupt_endings=5,
            total_conversations=10,
        )
        assert result >= Decimal("0.5")

    def test_abrupt_ending_low_when_rare(self):
        """Few abrupt endings = low signal."""
        from nikita.engine.engagement.detection import NeglectDetector

        detector = NeglectDetector()
        result = detector._abrupt_ending_signal(
            abrupt_endings=1,
            total_conversations=20,
        )
        assert result <= Decimal("0.2")


class TestNeglectDetectMethod:
    """Tests for composite neglect detection (AC-2.2.6, AC-2.2.7, AC-2.2.8)."""

    def test_ac_2_2_6_detect_returns_neglect_result(self):
        """AC-2.2.6: detect() returns NeglectResult with score and signals."""
        from nikita.engine.engagement.detection import NeglectDetector
        from nikita.engine.engagement.models import NeglectResult

        detector = NeglectDetector()
        result = detector.detect(
            messages_per_day=15,
            optimal_frequency=15,
            chapter=1,
            avg_response_seconds=1800,
            avg_message_length=80,
            abrupt_endings=1,
            total_conversations=10,
            distracted_score=Decimal("0.1"),
        )

        assert isinstance(result, NeglectResult)
        assert hasattr(result, "score")
        assert hasattr(result, "signals")
        assert hasattr(result, "is_neglecting")

    def test_ac_2_2_7_score_weights_applied(self):
        """AC-2.2.7: Score weights: frequency=0.35, slow=0.20, short=0.15, endings=0.10, distracted=0.20."""
        from nikita.engine.engagement.detection import NeglectDetector

        detector = NeglectDetector()
        result = detector.detect(
            messages_per_day=1,  # Very low
            optimal_frequency=15,
            chapter=1,
            avg_response_seconds=10 * 3600,  # 10 hours
            avg_message_length=5,  # Very short
            abrupt_endings=8,  # Many
            total_conversations=10,
            distracted_score=Decimal("1.0"),  # Very distracted
        )

        # Weights should sum to 1.0: 0.35 + 0.20 + 0.15 + 0.10 + 0.20 = 1.0
        assert "frequency" in result.signals
        assert "response_time" in result.signals
        assert "short_messages" in result.signals
        assert "abrupt_endings" in result.signals
        assert "distracted_language" in result.signals

    def test_ac_2_2_8_is_neglecting_threshold_0_6(self):
        """AC-2.2.8: is_neglecting = True when score > 0.6."""
        from nikita.engine.engagement.detection import NeglectDetector

        detector = NeglectDetector()

        # Low neglect case
        low_result = detector.detect(
            messages_per_day=15,
            optimal_frequency=15,
            chapter=1,
            avg_response_seconds=1800,
            avg_message_length=80,
            abrupt_endings=1,
            total_conversations=10,
            distracted_score=Decimal("0.1"),
        )
        assert low_result.is_neglecting is False

        # High neglect case
        high_result = detector.detect(
            messages_per_day=2,
            optimal_frequency=15,
            chapter=1,
            avg_response_seconds=8 * 3600,  # 8 hours
            avg_message_length=10,
            abrupt_endings=7,
            total_conversations=10,
            distracted_score=Decimal("0.8"),
        )
        assert high_result.is_neglecting is True


# ==============================================================================
# T2.3: LLM Analysis Tests
# ==============================================================================


class TestLLMAnalysisFunctions:
    """Tests for LLM-based language analysis (AC-2.3.1 through AC-2.3.6)."""

    def test_ac_2_3_1_analyze_neediness_function_exists(self):
        """AC-2.3.1: analyze_neediness() function defined."""
        from nikita.engine.engagement.detection import analyze_neediness

        assert analyze_neediness is not None
        assert callable(analyze_neediness)

    def test_ac_2_3_2_uses_pydantic_ai_structured_output(self):
        """AC-2.3.2: Uses Pydantic AI structured output."""
        # This test verifies the function signature expects Pydantic AI usage
        from nikita.engine.engagement.detection import analyze_neediness

        # Function should be async (for LLM calls)
        import inspect

        assert inspect.iscoroutinefunction(analyze_neediness)

    @pytest.mark.asyncio
    async def test_ac_2_3_3_returns_score_0_to_1(self):
        """AC-2.3.3: Returns score 0-1 for needy language patterns."""
        from nikita.engine.engagement.detection import analyze_neediness

        # Mock the LLM call
        with patch(
            "nikita.engine.engagement.detection._call_neediness_llm"
        ) as mock_llm:
            mock_llm.return_value = Decimal("0.7")
            result = await analyze_neediness(
                messages=["Are you there?", "Hello??", "Why aren't you responding?"],
            )

        assert isinstance(result, Decimal)
        assert Decimal("0") <= result <= Decimal("1")

    def test_ac_2_3_4_analyze_distraction_function_exists(self):
        """AC-2.3.4: analyze_distraction() function defined."""
        from nikita.engine.engagement.detection import analyze_distraction

        assert analyze_distraction is not None
        assert callable(analyze_distraction)

    @pytest.mark.asyncio
    async def test_ac_2_3_5_distraction_returns_score_0_to_1(self):
        """AC-2.3.5: Returns score 0-1 for distracted patterns."""
        from nikita.engine.engagement.detection import analyze_distraction

        # Mock the LLM call
        with patch(
            "nikita.engine.engagement.detection._call_distraction_llm"
        ) as mock_llm:
            mock_llm.return_value = Decimal("0.3")
            result = await analyze_distraction(
                messages=["ok", "sure", "whatever"],
            )

        assert isinstance(result, Decimal)
        assert Decimal("0") <= result <= Decimal("1")

    @pytest.mark.asyncio
    async def test_ac_2_3_6_results_cached_per_session(self):
        """AC-2.3.6: Results cached per session to reduce API calls."""
        from nikita.engine.engagement.detection import (
            analyze_neediness,
            clear_analysis_cache,
        )

        # Clear cache first
        clear_analysis_cache()

        call_count = 0

        async def mock_llm(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return Decimal("0.5")

        with patch(
            "nikita.engine.engagement.detection._call_neediness_llm",
            side_effect=mock_llm,
        ):
            # First call - should hit LLM
            messages = ["Are you there?", "Hello??"]
            result1 = await analyze_neediness(messages=messages, session_id="test-123")

            # Second call with same session - should use cache
            result2 = await analyze_neediness(messages=messages, session_id="test-123")

            # Third call with different session - should hit LLM again
            result3 = await analyze_neediness(messages=messages, session_id="test-456")

        assert result1 == result2  # Cached
        assert call_count == 2  # Only 2 LLM calls (sessions 123 and 456)


class TestNeedyLanguagePatterns:
    """Tests for needy language detection patterns."""

    @pytest.mark.asyncio
    async def test_high_neediness_for_desperate_messages(self):
        """Desperate/clingy messages score high."""
        from nikita.engine.engagement.detection import analyze_neediness

        with patch(
            "nikita.engine.engagement.detection._call_neediness_llm"
        ) as mock_llm:
            # Simulate what LLM would return for desperate messages
            mock_llm.return_value = Decimal("0.85")
            result = await analyze_neediness(
                messages=[
                    "Please respond",
                    "I miss you so much",
                    "Why are you ignoring me?",
                    "I need to talk to you right now",
                ],
            )

        assert result >= Decimal("0.7")

    @pytest.mark.asyncio
    async def test_low_neediness_for_confident_messages(self):
        """Confident/casual messages score low."""
        from nikita.engine.engagement.detection import analyze_neediness

        with patch(
            "nikita.engine.engagement.detection._call_neediness_llm"
        ) as mock_llm:
            mock_llm.return_value = Decimal("0.15")
            result = await analyze_neediness(
                messages=[
                    "Hey, how's your day going?",
                    "That's interesting, tell me more",
                    "No worries, whenever you have time",
                ],
            )

        assert result <= Decimal("0.3")


class TestDistractedLanguagePatterns:
    """Tests for distracted language detection patterns."""

    @pytest.mark.asyncio
    async def test_high_distraction_for_dismissive_messages(self):
        """Dismissive/terse messages score high."""
        from nikita.engine.engagement.detection import analyze_distraction

        with patch(
            "nikita.engine.engagement.detection._call_distraction_llm"
        ) as mock_llm:
            mock_llm.return_value = Decimal("0.8")
            result = await analyze_distraction(
                messages=[
                    "k",
                    "fine",
                    "whatever",
                    "busy rn",
                ],
            )

        assert result >= Decimal("0.6")

    @pytest.mark.asyncio
    async def test_low_distraction_for_engaged_messages(self):
        """Engaged/thoughtful messages score low."""
        from nikita.engine.engagement.detection import analyze_distraction

        with patch(
            "nikita.engine.engagement.detection._call_distraction_llm"
        ) as mock_llm:
            mock_llm.return_value = Decimal("0.1")
            result = await analyze_distraction(
                messages=[
                    "That's a really good point about the project",
                    "I've been thinking about what you said earlier",
                    "Let me explain what I mean in more detail",
                ],
            )

        assert result <= Decimal("0.3")
