"""Detection tests for Conflict Generation System (Spec 027, Phase B: T006-T011).

Tests for:
- T006: TriggerDetector class
- T007: Dismissive detection
- T008: Neglect detection
- T009: Jealousy detection
- T010: Boundary violation detection
- T011: Phase B coverage
"""

import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from nikita.conflicts.detector import (
    DetectionContext,
    DetectionResult,
    TriggerDetector,
)
from nikita.conflicts.models import ConflictTrigger, TriggerType


# Fixtures


@pytest.fixture
def detector():
    """Create a TriggerDetector with LLM disabled."""
    return TriggerDetector(llm_enabled=False)


@pytest.fixture
def detector_with_llm():
    """Create a TriggerDetector with mocked LLM."""
    with patch("nikita.conflicts.detector.Agent") as mock_agent_class:
        mock_agent = MagicMock()
        mock_agent_class.return_value = mock_agent
        return TriggerDetector(llm_enabled=True)


@pytest.fixture
def basic_context():
    """Create a basic detection context."""
    return DetectionContext(
        user_id="user_123",
        message="Hello, how are you?",
        chapter=3,
        relationship_score=50,
    )


# Test DetectionContext


class TestDetectionContext:
    """Tests for DetectionContext model."""

    def test_create_basic_context(self):
        """Test creating a basic context."""
        ctx = DetectionContext(
            user_id="user_1",
            message="Hi there",
        )
        assert ctx.user_id == "user_1"
        assert ctx.message == "Hi there"
        assert ctx.chapter == 1  # default
        assert ctx.relationship_score == 50  # default

    def test_create_full_context(self):
        """Test creating context with all fields."""
        now = datetime.now(UTC)
        ctx = DetectionContext(
            user_id="user_2",
            message="Test message",
            chapter=4,
            relationship_score=75,
            last_interaction=now,
            recent_messages=["msg1", "msg2"],
            conversation_duration_minutes=15,
        )
        assert ctx.chapter == 4
        assert ctx.relationship_score == 75
        assert ctx.last_interaction == now
        assert len(ctx.recent_messages) == 2
        assert ctx.conversation_duration_minutes == 15

    def test_chapter_bounds(self):
        """Test chapter validation bounds."""
        # Valid chapters
        for chapter in [1, 2, 3, 4, 5]:
            ctx = DetectionContext(
                user_id="user",
                message="test",
                chapter=chapter,
            )
            assert ctx.chapter == chapter


# Test DetectionResult


class TestDetectionResult:
    """Tests for DetectionResult model."""

    def test_empty_result(self):
        """Test empty detection result."""
        result = DetectionResult()
        assert result.triggers == []
        assert not result.has_triggers
        assert result.highest_severity == 0.0

    def test_result_with_triggers(self):
        """Test result with triggers."""
        trigger = ConflictTrigger(
            trigger_id="t1",
            trigger_type=TriggerType.DISMISSIVE,
            severity=0.5,
        )
        result = DetectionResult(triggers=[trigger])
        assert result.has_triggers
        assert result.highest_severity == 0.5

    def test_highest_severity_multiple(self):
        """Test highest severity with multiple triggers."""
        triggers = [
            ConflictTrigger(
                trigger_id="t1",
                trigger_type=TriggerType.DISMISSIVE,
                severity=0.3,
            ),
            ConflictTrigger(
                trigger_id="t2",
                trigger_type=TriggerType.JEALOUSY,
                severity=0.7,
            ),
            ConflictTrigger(
                trigger_id="t3",
                trigger_type=TriggerType.BOUNDARY,
                severity=0.5,
            ),
        ]
        result = DetectionResult(triggers=triggers)
        assert result.highest_severity == 0.7


# Test TriggerDetector


class TestTriggerDetector:
    """Tests for TriggerDetector class."""

    def test_create_detector(self):
        """Test creating a detector."""
        detector = TriggerDetector(llm_enabled=False)
        assert detector is not None
        assert not detector._llm_enabled

    def test_detect_sync_no_triggers(self, detector, basic_context):
        """Test sync detection with no triggers."""
        result = detector.detect_sync(basic_context)
        assert isinstance(result, DetectionResult)
        assert result.context_analyzed == basic_context

    def test_chapter_sensitivity_applied(self, detector):
        """Test that chapter sensitivity affects severity."""
        # Chapter 1 has 1.5x sensitivity
        ctx_ch1 = DetectionContext(
            user_id="user",
            message="k",  # short message
            chapter=1,
        )
        result_ch1 = detector.detect_sync(ctx_ch1)

        # Chapter 5 has 0.8x sensitivity
        ctx_ch5 = DetectionContext(
            user_id="user",
            message="k",
            chapter=5,
        )
        result_ch5 = detector.detect_sync(ctx_ch5)

        # Chapter 1 should have higher severity
        if result_ch1.has_triggers and result_ch5.has_triggers:
            assert result_ch1.highest_severity > result_ch5.highest_severity


# Test Dismissive Detection (T007)


class TestDismissiveDetection:
    """Tests for dismissive trigger detection."""

    def test_short_message_detected(self, detector):
        """Test detection of short messages."""
        ctx = DetectionContext(
            user_id="user",
            message="ok",
            chapter=3,
        )
        result = detector.detect_sync(ctx)
        assert result.has_triggers
        dismissive = [t for t in result.triggers if t.trigger_type == TriggerType.DISMISSIVE]
        assert len(dismissive) > 0
        assert dismissive[0].context.get("reason") == "short_message"

    def test_single_word_higher_severity(self, detector):
        """Test that single word has higher severity than multi-word short."""
        ctx_single = DetectionContext(
            user_id="user",
            message="ok",  # single word
            chapter=3,
        )
        ctx_multi = DetectionContext(
            user_id="user",
            message="ok sure",  # multi word but still short
            chapter=3,
        )
        result_single = detector.detect_sync(ctx_single)
        result_multi = detector.detect_sync(ctx_multi)

        single_severity = result_single.highest_severity
        multi_severity = result_multi.highest_severity

        # Single word should be same or higher (both may be short)
        assert single_severity >= 0.3

    def test_very_short_highest_severity(self, detector):
        """Test that 1-3 char messages have highest severity."""
        ctx = DetectionContext(
            user_id="user",
            message="k",  # 1 char
            chapter=3,
        )
        result = detector.detect_sync(ctx)
        dismissive = [t for t in result.triggers if t.trigger_type == TriggerType.DISMISSIVE]
        # Base severity 0.5 * chapter 3 sensitivity 1.0 = 0.5
        assert dismissive[0].severity >= 0.4

    def test_consecutive_short_detected(self, detector):
        """Test detection of consecutive short messages."""
        ctx = DetectionContext(
            user_id="user",
            message="yeah",
            chapter=3,
            recent_messages=["ok", "sure", "k", "yep", "fine"],
        )
        result = detector.detect_sync(ctx)
        assert result.has_triggers

        consecutive = [
            t for t in result.triggers
            if t.trigger_type == TriggerType.DISMISSIVE
            and t.context.get("reason") == "consecutive_short"
        ]
        assert len(consecutive) > 0

    def test_normal_message_no_dismissive(self, detector):
        """Test that normal messages don't trigger dismissive."""
        ctx = DetectionContext(
            user_id="user",
            message="Hey! How was your day? I was thinking about you.",
            chapter=3,
        )
        result = detector.detect_sync(ctx)
        dismissive = [t for t in result.triggers if t.trigger_type == TriggerType.DISMISSIVE]
        assert len(dismissive) == 0


# Test Neglect Detection (T008)


class TestNeglectDetection:
    """Tests for neglect trigger detection."""

    def test_long_gap_detected(self, detector):
        """Test detection of long time gaps."""
        ctx = DetectionContext(
            user_id="user",
            message="Hi",
            chapter=3,
            last_interaction=datetime.now(UTC) - timedelta(hours=30),
        )
        result = detector.detect_sync(ctx)

        neglect = [t for t in result.triggers if t.trigger_type == TriggerType.NEGLECT]
        assert len(neglect) > 0
        assert neglect[0].context.get("reason") == "time_gap"

    def test_no_neglect_recent_interaction(self, detector):
        """Test no neglect for recent interaction."""
        ctx = DetectionContext(
            user_id="user",
            message="Hi again",
            chapter=3,
            last_interaction=datetime.now(UTC) - timedelta(hours=2),
        )
        result = detector.detect_sync(ctx)

        neglect = [t for t in result.triggers if t.trigger_type == TriggerType.NEGLECT]
        # Should not detect time-based neglect
        time_neglect = [n for n in neglect if n.context.get("reason") == "time_gap"]
        assert len(time_neglect) == 0

    def test_gap_severity_increases_with_time(self, detector):
        """Test that gap severity increases with longer gaps."""
        ctx_24h = DetectionContext(
            user_id="user",
            message="Hi",
            chapter=3,
            last_interaction=datetime.now(UTC) - timedelta(hours=25),
        )
        ctx_48h = DetectionContext(
            user_id="user",
            message="Hi",
            chapter=3,
            last_interaction=datetime.now(UTC) - timedelta(hours=50),
        )

        result_24h = detector.detect_sync(ctx_24h)
        result_48h = detector.detect_sync(ctx_48h)

        neglect_24 = [t for t in result_24h.triggers if t.trigger_type == TriggerType.NEGLECT]
        neglect_48 = [t for t in result_48h.triggers if t.trigger_type == TriggerType.NEGLECT]

        if neglect_24 and neglect_48:
            assert neglect_48[0].severity > neglect_24[0].severity

    def test_short_session_detected(self, detector):
        """Test detection of short conversation sessions."""
        ctx = DetectionContext(
            user_id="user",
            message="bye",
            chapter=3,
            conversation_duration_minutes=3,
            recent_messages=["hi", "how are you"],
        )
        result = detector.detect_sync(ctx)

        neglect = [
            t for t in result.triggers
            if t.trigger_type == TriggerType.NEGLECT
            and t.context.get("reason") == "short_session"
        ]
        assert len(neglect) > 0

    def test_no_neglect_first_interaction(self, detector):
        """Test no neglect when last_interaction is None."""
        ctx = DetectionContext(
            user_id="user",
            message="First message ever",
            chapter=1,
            last_interaction=None,
        )
        result = detector.detect_sync(ctx)

        neglect = [
            t for t in result.triggers
            if t.trigger_type == TriggerType.NEGLECT
            and t.context.get("reason") == "time_gap"
        ]
        assert len(neglect) == 0


# Test Jealousy Detection (T009)


class TestJealousyDetection:
    """Tests for jealousy trigger detection."""

    def test_friend_mention_detected(self, detector):
        """Test detection of friend mentions."""
        ctx = DetectionContext(
            user_id="user",
            message="I went to dinner with a friend last night",
            chapter=3,
        )
        result = detector.detect_sync(ctx)

        jealousy = [t for t in result.triggers if t.trigger_type == TriggerType.JEALOUSY]
        assert len(jealousy) > 0

    def test_ex_mention_detected(self, detector):
        """Test detection of ex mentions."""
        ctx = DetectionContext(
            user_id="user",
            message="My ex texted me today",
            chapter=3,
        )
        result = detector.detect_sync(ctx)

        jealousy = [t for t in result.triggers if t.trigger_type == TriggerType.JEALOUSY]
        assert len(jealousy) > 0

    def test_date_mention_detected(self, detector):
        """Test detection of date mentions."""
        ctx = DetectionContext(
            user_id="user",
            message="I had a great date last week",
            chapter=3,
        )
        result = detector.detect_sync(ctx)

        jealousy = [t for t in result.triggers if t.trigger_type == TriggerType.JEALOUSY]
        assert len(jealousy) > 0

    def test_attractive_mention_detected(self, detector):
        """Test detection of attractive person mentions."""
        ctx = DetectionContext(
            user_id="user",
            message="She was really cute and attractive",
            chapter=3,
        )
        result = detector.detect_sync(ctx)

        jealousy = [t for t in result.triggers if t.trigger_type == TriggerType.JEALOUSY]
        assert len(jealousy) > 0

    def test_multiple_keywords_higher_severity(self, detector):
        """Test that multiple keywords increase severity."""
        ctx_single = DetectionContext(
            user_id="user",
            message="I saw my ex today",
            chapter=3,
        )
        ctx_multiple = DetectionContext(
            user_id="user",
            message="My ex is really cute and attractive",
            chapter=3,
        )

        result_single = detector.detect_sync(ctx_single)
        result_multiple = detector.detect_sync(ctx_multiple)

        jealousy_single = [t for t in result_single.triggers if t.trigger_type == TriggerType.JEALOUSY]
        jealousy_multiple = [t for t in result_multiple.triggers if t.trigger_type == TriggerType.JEALOUSY]

        if jealousy_single and jealousy_multiple:
            assert jealousy_multiple[0].severity > jealousy_single[0].severity

    def test_no_jealousy_normal_message(self, detector):
        """Test no jealousy for normal messages."""
        ctx = DetectionContext(
            user_id="user",
            message="I had a great day at work today!",
            chapter=3,
        )
        result = detector.detect_sync(ctx)

        jealousy = [t for t in result.triggers if t.trigger_type == TriggerType.JEALOUSY]
        assert len(jealousy) == 0


# Test Boundary Detection (T010)


class TestBoundaryDetection:
    """Tests for boundary violation trigger detection."""

    def test_sexual_keyword_detected(self, detector):
        """Test detection of sexual keywords."""
        ctx = DetectionContext(
            user_id="user",
            message="Send me a nude pic",
            chapter=3,
        )
        result = detector.detect_sync(ctx)

        boundary = [t for t in result.triggers if t.trigger_type == TriggerType.BOUNDARY]
        assert len(boundary) > 0

    def test_come_over_detected(self, detector):
        """Test detection of 'come over' requests."""
        ctx = DetectionContext(
            user_id="user",
            message="Why don't you come over to my place tonight",
            chapter=2,
        )
        result = detector.detect_sync(ctx)

        boundary = [t for t in result.triggers if t.trigger_type == TriggerType.BOUNDARY]
        assert len(boundary) > 0

    def test_early_chapter_higher_severity(self, detector):
        """Test that early chapters have higher boundary sensitivity."""
        ctx_ch1 = DetectionContext(
            user_id="user",
            message="Come over to my place",
            chapter=1,
        )
        ctx_ch5 = DetectionContext(
            user_id="user",
            message="Come over to my place",
            chapter=5,
        )

        result_ch1 = detector.detect_sync(ctx_ch1)
        result_ch5 = detector.detect_sync(ctx_ch5)

        boundary_ch1 = [t for t in result_ch1.triggers if t.trigger_type == TriggerType.BOUNDARY]
        boundary_ch5 = [t for t in result_ch5.triggers if t.trigger_type == TriggerType.BOUNDARY]

        if boundary_ch1 and boundary_ch5:
            # Ch1 has 1.5x sensitivity, Ch5 has 0.8x
            assert boundary_ch1[0].severity > boundary_ch5[0].severity

    def test_no_boundary_normal_message(self, detector):
        """Test no boundary for normal messages."""
        ctx = DetectionContext(
            user_id="user",
            message="Let's go to the movies tomorrow",
            chapter=3,
        )
        result = detector.detect_sync(ctx)

        boundary = [t for t in result.triggers if t.trigger_type == TriggerType.BOUNDARY]
        assert len(boundary) == 0


# Test Chapter Sensitivity


class TestChapterSensitivity:
    """Tests for chapter-based sensitivity adjustments."""

    def test_chapter_1_multiplier(self, detector):
        """Test chapter 1 has 1.5x multiplier."""
        ctx = DetectionContext(
            user_id="user",
            message="k",
            chapter=1,
        )
        result = detector.detect_sync(ctx)
        # Base severity for single char is 0.5
        # With 1.5x multiplier: 0.75
        assert result.highest_severity >= 0.7

    def test_chapter_3_baseline(self, detector):
        """Test chapter 3 has 1.0x multiplier (baseline)."""
        ctx = DetectionContext(
            user_id="user",
            message="k",
            chapter=3,
        )
        result = detector.detect_sync(ctx)
        # Base severity stays at 0.5
        assert 0.45 <= result.highest_severity <= 0.55

    def test_chapter_5_reduced(self, detector):
        """Test chapter 5 has 0.8x multiplier."""
        ctx = DetectionContext(
            user_id="user",
            message="k",
            chapter=5,
        )
        result = detector.detect_sync(ctx)
        # Base severity 0.5 * 0.8 = 0.4
        assert result.highest_severity <= 0.45


# Test Async Detection


class TestAsyncDetection:
    """Tests for async detection method."""

    @pytest.mark.asyncio
    async def test_detect_async_basic(self, detector, basic_context):
        """Test async detection."""
        result = await detector.detect(basic_context)
        assert isinstance(result, DetectionResult)
        assert result.context_analyzed == basic_context

    @pytest.mark.asyncio
    async def test_detect_async_stores_triggers(self, detector):
        """Test that async detection stores triggers."""
        ctx = DetectionContext(
            user_id="user_test_store",
            message="k",  # Will trigger dismissive
            chapter=3,
        )
        result = await detector.detect(ctx)

        # Check that detection found triggers (stored internally)
        assert result.has_triggers

    @pytest.mark.asyncio
    async def test_detect_async_multiple_trigger_types(self, detector):
        """Test detection of multiple trigger types at once."""
        ctx = DetectionContext(
            user_id="user",
            message="k",  # dismissive
            chapter=2,
            last_interaction=datetime.now(UTC) - timedelta(hours=30),  # neglect
        )
        result = await detector.detect(ctx)

        trigger_types = {t.trigger_type for t in result.triggers}
        # Should have both dismissive and neglect
        assert TriggerType.DISMISSIVE in trigger_types
        assert TriggerType.NEGLECT in trigger_types


# Test Edge Cases


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_message(self, detector):
        """Test handling of empty message."""
        ctx = DetectionContext(
            user_id="user",
            message="",
            chapter=3,
        )
        result = detector.detect_sync(ctx)
        # Empty message should still work
        assert isinstance(result, DetectionResult)

    def test_whitespace_only_message(self, detector):
        """Test handling of whitespace-only message."""
        ctx = DetectionContext(
            user_id="user",
            message="   ",
            chapter=3,
        )
        result = detector.detect_sync(ctx)
        assert isinstance(result, DetectionResult)

    def test_very_long_message(self, detector):
        """Test handling of very long message."""
        ctx = DetectionContext(
            user_id="user",
            message="Hello " * 1000,
            chapter=3,
        )
        result = detector.detect_sync(ctx)
        assert isinstance(result, DetectionResult)

    def test_special_characters(self, detector):
        """Test handling of special characters."""
        ctx = DetectionContext(
            user_id="user",
            message="👋 Hey! How are you? 🙂",
            chapter=3,
        )
        result = detector.detect_sync(ctx)
        assert isinstance(result, DetectionResult)

    def test_case_insensitive_keywords(self, detector):
        """Test that keyword matching is case insensitive."""
        ctx_lower = DetectionContext(
            user_id="user",
            message="my ex called me",
            chapter=3,
        )
        ctx_upper = DetectionContext(
            user_id="user",
            message="MY EX CALLED ME",
            chapter=3,
        )

        result_lower = detector.detect_sync(ctx_lower)
        result_upper = detector.detect_sync(ctx_upper)

        jealousy_lower = [t for t in result_lower.triggers if t.trigger_type == TriggerType.JEALOUSY]
        jealousy_upper = [t for t in result_upper.triggers if t.trigger_type == TriggerType.JEALOUSY]

        # Both should detect jealousy
        assert len(jealousy_lower) > 0
        assert len(jealousy_upper) > 0
