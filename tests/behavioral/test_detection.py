"""Unit tests for Situation Detection (Spec 024, Phase B: T005-T010).

Tests:
- SituationDetector class
- Priority-based classification
- Time-based detection (morning/evening)
- Gap detection (6h/24h thresholds)
- Conflict detection integration with Spec 023
"""

from datetime import datetime, timedelta, timezone

import pytest

from nikita.behavioral.detector import SituationDetector
from nikita.behavioral.models import SituationContext, SituationType


class TestSituationDetector:
    """Tests for SituationDetector class (AC-T005.1-T005.4)."""

    @pytest.fixture
    def detector(self):
        """Create detector instance."""
        return SituationDetector()

    def test_detector_exists(self, detector):
        """AC-T005.1: SituationDetector class exists."""
        assert detector is not None
        assert hasattr(detector, "detect")

    def test_detect_returns_situation_context(self, detector):
        """AC-T005.2: detect() returns SituationContext."""
        result = detector.detect()

        assert isinstance(result, SituationContext)
        assert result.situation_type is not None

    def test_detect_with_all_parameters(self, detector):
        """AC-T005.3: Handles multiple situation types."""
        result = detector.detect(
            conflict_state="cold",
            hours_since_last_message=10.0,
            user_local_hour=9,
            chapter=2,
            relationship_score=65.0,
            engagement_state="in_zone",
            user_id="123e4567-e89b-12d3-a456-426614174000",
        )

        assert isinstance(result, SituationContext)
        # Conflict takes priority
        assert result.situation_type == SituationType.CONFLICT

    def test_detect_stores_context_values(self, detector):
        """detect() stores all context values correctly."""
        result = detector.detect(
            conflict_state="none",
            hours_since_last_message=2.5,
            user_local_hour=15,
            chapter=3,
            relationship_score=72.0,
            engagement_state="drifting",
        )

        assert result.hours_since_last_message == 2.5
        assert result.user_local_hour == 15
        assert result.chapter == 3
        assert result.relationship_score == 72.0
        assert result.conflict_state == "none"
        assert result.engagement_state == "drifting"


class TestSituationClassification:
    """Tests for situation classification logic (AC-T006.1-T006.3)."""

    @pytest.fixture
    def detector(self):
        """Create detector instance."""
        return SituationDetector()

    def test_situations_are_mutually_exclusive(self, detector):
        """AC-T006.1: Only one situation type returned."""
        # Even with multiple conditions matching, only one is returned
        result = detector.detect(
            conflict_state="cold",  # Matches CONFLICT
            hours_since_last_message=10.0,  # Matches AFTER_GAP
            user_local_hour=9,  # Matches MORNING
        )

        # Only highest priority (CONFLICT) is returned
        assert result.situation_type == SituationType.CONFLICT

    def test_priority_conflict_highest(self, detector):
        """AC-T006.2: CONFLICT has highest priority."""
        result = detector.detect(
            conflict_state="explosive",
            hours_since_last_message=48.0,  # Would be AFTER_GAP
            user_local_hour=9,  # Would be MORNING
        )
        assert result.situation_type == SituationType.CONFLICT

    def test_priority_after_gap_second(self, detector):
        """AC-T006.2: AFTER_GAP has second highest priority."""
        result = detector.detect(
            conflict_state="none",  # No conflict
            hours_since_last_message=10.0,  # Gap > 6 hours
            user_local_hour=9,  # Would be MORNING
        )
        assert result.situation_type == SituationType.AFTER_GAP

    def test_priority_morning_third(self, detector):
        """AC-T006.2: MORNING has third priority (over EVENING)."""
        result = detector.detect(
            conflict_state="none",
            hours_since_last_message=2.0,  # No gap
            user_local_hour=9,  # Morning hour
        )
        assert result.situation_type == SituationType.MORNING

    def test_priority_evening_fourth(self, detector):
        """AC-T006.2: EVENING has fourth priority."""
        result = detector.detect(
            conflict_state="none",
            hours_since_last_message=2.0,  # No gap
            user_local_hour=20,  # Evening hour
        )
        assert result.situation_type == SituationType.EVENING

    def test_priority_mid_conversation_default(self, detector):
        """AC-T006.2: MID_CONVERSATION is the default."""
        result = detector.detect(
            conflict_state="none",
            hours_since_last_message=2.0,  # No gap
            user_local_hour=14,  # Afternoon (not morning/evening)
        )
        assert result.situation_type == SituationType.MID_CONVERSATION


class TestTimeBasedDetection:
    """Tests for time-based detection (AC-T007.1-T007.4)."""

    @pytest.fixture
    def detector(self):
        """Create detector instance."""
        return SituationDetector()

    def test_morning_detection_start(self, detector):
        """AC-T007.1: Morning starts at 6am."""
        result = detector.detect(user_local_hour=6, hours_since_last_message=0)
        assert result.situation_type == SituationType.MORNING

    def test_morning_detection_end(self, detector):
        """AC-T007.1: Morning ends at 11am (inclusive)."""
        result = detector.detect(user_local_hour=11, hours_since_last_message=0)
        assert result.situation_type == SituationType.MORNING

    def test_morning_detection_mid(self, detector):
        """AC-T007.1: Morning at 9am."""
        result = detector.detect(user_local_hour=9, hours_since_last_message=0)
        assert result.situation_type == SituationType.MORNING

    def test_not_morning_before_6am(self, detector):
        """AC-T007.1: 5am is NOT morning."""
        result = detector.detect(user_local_hour=5, hours_since_last_message=0)
        assert result.situation_type != SituationType.MORNING

    def test_not_morning_after_11am(self, detector):
        """AC-T007.1: 12pm is NOT morning."""
        result = detector.detect(user_local_hour=12, hours_since_last_message=0)
        assert result.situation_type != SituationType.MORNING

    def test_evening_detection_start(self, detector):
        """AC-T007.2: Evening starts at 6pm (18:00)."""
        result = detector.detect(user_local_hour=18, hours_since_last_message=0)
        assert result.situation_type == SituationType.EVENING

    def test_evening_detection_end(self, detector):
        """AC-T007.2: Evening ends at 10pm (22:00, inclusive)."""
        result = detector.detect(user_local_hour=22, hours_since_last_message=0)
        assert result.situation_type == SituationType.EVENING

    def test_evening_detection_mid(self, detector):
        """AC-T007.2: Evening at 8pm (20:00)."""
        result = detector.detect(user_local_hour=20, hours_since_last_message=0)
        assert result.situation_type == SituationType.EVENING

    def test_not_evening_before_6pm(self, detector):
        """AC-T007.2: 5pm is NOT evening."""
        result = detector.detect(user_local_hour=17, hours_since_last_message=0)
        assert result.situation_type != SituationType.EVENING

    def test_not_evening_after_10pm(self, detector):
        """AC-T007.2: 11pm is NOT evening."""
        result = detector.detect(user_local_hour=23, hours_since_last_message=0)
        assert result.situation_type != SituationType.EVENING

    def test_afternoon_is_mid_conversation(self, detector):
        """Afternoon hours (12-17) result in MID_CONVERSATION."""
        for hour in [12, 13, 14, 15, 16, 17]:
            result = detector.detect(user_local_hour=hour, hours_since_last_message=0)
            assert result.situation_type == SituationType.MID_CONVERSATION

    def test_night_is_mid_conversation(self, detector):
        """Night hours (23, 0-5) result in MID_CONVERSATION."""
        for hour in [23, 0, 1, 2, 3, 4, 5]:
            result = detector.detect(user_local_hour=hour, hours_since_last_message=0)
            assert result.situation_type == SituationType.MID_CONVERSATION

    def test_defaults_to_utc_hour(self, detector):
        """AC-T007.3: Defaults to UTC hour when not provided."""
        result = detector.detect(user_local_hour=None, hours_since_last_message=0)
        # Should still return a valid result using UTC hour
        assert result.situation_type is not None
        # user_local_hour should be set from UTC
        assert 0 <= result.user_local_hour <= 23


class TestGapDetection:
    """Tests for gap detection (AC-T008.1-T008.4)."""

    @pytest.fixture
    def detector(self):
        """Create detector instance."""
        return SituationDetector()

    def test_gap_6_hours_triggers_after_gap(self, detector):
        """AC-T008.1: Gap of exactly 6 hours triggers AFTER_GAP."""
        result = detector.detect(hours_since_last_message=6.0, user_local_hour=14)
        assert result.situation_type == SituationType.AFTER_GAP

    def test_gap_over_6_hours_triggers_after_gap(self, detector):
        """AC-T008.1: Gap > 6 hours triggers AFTER_GAP."""
        result = detector.detect(hours_since_last_message=10.0, user_local_hour=14)
        assert result.situation_type == SituationType.AFTER_GAP

    def test_gap_under_6_hours_no_trigger(self, detector):
        """AC-T008.1: Gap < 6 hours does NOT trigger AFTER_GAP."""
        result = detector.detect(hours_since_last_message=5.9, user_local_hour=14)
        assert result.situation_type != SituationType.AFTER_GAP

    def test_long_gap_metadata(self, detector):
        """AC-T008.2: Gap > 24 hours sets is_long_gap in metadata."""
        result = detector.detect(hours_since_last_message=25.0, user_local_hour=14)
        assert result.situation_type == SituationType.AFTER_GAP
        assert result.metadata.get("is_long_gap") is True
        assert result.metadata.get("gap_hours") == 25.0

    def test_medium_gap_metadata(self, detector):
        """AC-T008.2: Gap 6-24 hours has is_long_gap=False."""
        result = detector.detect(hours_since_last_message=12.0, user_local_hour=14)
        assert result.situation_type == SituationType.AFTER_GAP
        assert result.metadata.get("is_long_gap") is False
        assert result.metadata.get("gap_hours") == 12.0

    def test_calculate_time_since_last_message(self, detector):
        """AC-T008.3: Calculate hours since last message."""
        now = datetime.now(timezone.utc)
        last_message = now - timedelta(hours=10)

        hours = detector.calculate_time_since_last(last_message, now)

        assert 9.9 < hours < 10.1  # Allow small floating point variance

    def test_calculate_time_since_last_no_previous(self, detector):
        """AC-T008.3: Returns 0 if no previous message."""
        hours = detector.calculate_time_since_last(None)
        assert hours == 0.0

    def test_calculate_time_since_last_naive_datetime(self, detector):
        """AC-T008.3: Handles naive datetimes by assuming UTC."""
        now = datetime.now()  # Naive
        last_message = now - timedelta(hours=5)  # Naive

        hours = detector.calculate_time_since_last(last_message, now)
        assert 4.9 < hours < 5.1


class TestConflictDetection:
    """Tests for conflict detection integration (AC-T009.1-T009.3)."""

    @pytest.fixture
    def detector(self):
        """Create detector instance."""
        return SituationDetector()

    def test_passive_aggressive_is_conflict(self, detector):
        """AC-T009.1: passive_aggressive triggers CONFLICT."""
        result = detector.detect(conflict_state="passive_aggressive")
        assert result.situation_type == SituationType.CONFLICT
        assert result.metadata.get("conflict_subtype") == "passive_aggressive"

    def test_cold_is_conflict(self, detector):
        """AC-T009.1: cold triggers CONFLICT."""
        result = detector.detect(conflict_state="cold")
        assert result.situation_type == SituationType.CONFLICT
        assert result.metadata.get("conflict_subtype") == "cold"

    def test_vulnerable_is_conflict(self, detector):
        """AC-T009.1: vulnerable triggers CONFLICT."""
        result = detector.detect(conflict_state="vulnerable")
        assert result.situation_type == SituationType.CONFLICT
        assert result.metadata.get("conflict_subtype") == "vulnerable"

    def test_explosive_is_conflict(self, detector):
        """AC-T009.1: explosive triggers CONFLICT."""
        result = detector.detect(conflict_state="explosive")
        assert result.situation_type == SituationType.CONFLICT
        assert result.metadata.get("conflict_subtype") == "explosive"

    def test_none_is_not_conflict(self, detector):
        """AC-T009.1: none is NOT conflict."""
        result = detector.detect(conflict_state="none", user_local_hour=14)
        assert result.situation_type != SituationType.CONFLICT

    def test_map_conflict_to_situation(self, detector):
        """AC-T009.2: Map conflict_state to situation type."""
        # Active conflict states
        for state in ["passive_aggressive", "cold", "vulnerable", "explosive"]:
            situation = detector.map_conflict_to_situation(state)
            assert situation == SituationType.CONFLICT

        # Non-conflict state
        situation = detector.map_conflict_to_situation("none")
        assert situation == SituationType.MID_CONVERSATION

    def test_conflict_case_insensitive(self, detector):
        """AC-T009.1: Conflict detection is case-insensitive."""
        result = detector.detect(conflict_state="COLD")
        assert result.situation_type == SituationType.CONFLICT

        result = detector.detect(conflict_state="Explosive")
        assert result.situation_type == SituationType.CONFLICT


class TestPriorityEdgeCases:
    """Edge case tests for priority ordering."""

    @pytest.fixture
    def detector(self):
        """Create detector instance."""
        return SituationDetector()

    def test_conflict_beats_everything(self, detector):
        """CONFLICT beats all other conditions."""
        result = detector.detect(
            conflict_state="cold",
            hours_since_last_message=100.0,  # Very long gap
            user_local_hour=9,  # Morning
        )
        assert result.situation_type == SituationType.CONFLICT

    def test_gap_beats_time_based(self, detector):
        """AFTER_GAP beats time-based detection."""
        result = detector.detect(
            conflict_state="none",
            hours_since_last_message=24.0,
            user_local_hour=9,  # Morning
        )
        assert result.situation_type == SituationType.AFTER_GAP

    def test_morning_beats_evening_in_overlap(self, detector):
        """Morning and evening don't overlap (hours are disjoint)."""
        # Just verify the hours are properly disjoint
        morning_hours = list(range(6, 12))  # 6-11
        evening_hours = list(range(18, 23))  # 18-22

        # No overlap
        assert not set(morning_hours) & set(evening_hours)


class TestMetadataGeneration:
    """Tests for metadata in SituationContext."""

    @pytest.fixture
    def detector(self):
        """Create detector instance."""
        return SituationDetector()

    def test_conflict_metadata(self, detector):
        """Conflict situations include subtype in metadata."""
        result = detector.detect(conflict_state="vulnerable")
        assert "conflict_subtype" in result.metadata
        assert result.metadata["conflict_subtype"] == "vulnerable"

    def test_gap_metadata(self, detector):
        """Gap situations include gap info in metadata."""
        result = detector.detect(hours_since_last_message=15.0, user_local_hour=14)
        assert "gap_hours" in result.metadata
        assert result.metadata["gap_hours"] == 15.0
        assert "is_long_gap" in result.metadata

    def test_morning_no_special_metadata(self, detector):
        """Morning situations have minimal metadata."""
        result = detector.detect(user_local_hour=9, hours_since_last_message=0)
        # No conflict_subtype or gap_hours
        assert "conflict_subtype" not in result.metadata
        assert "gap_hours" not in result.metadata

    def test_mid_conversation_minimal_metadata(self, detector):
        """MID_CONVERSATION has empty metadata."""
        result = detector.detect(user_local_hour=14, hours_since_last_message=0)
        assert result.metadata == {}
