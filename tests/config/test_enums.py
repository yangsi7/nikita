"""Tests for nikita.config.enums module.

TDD: These tests define expected behavior BEFORE implementation.
"""

import pytest


class TestChapterEnum:
    """Tests for Chapter enum."""

    def test_chapter_has_five_values(self):
        """Chapter enum should have exactly 5 chapters."""
        from nikita.config.enums import Chapter

        assert len(Chapter) == 5

    def test_chapter_values_are_1_to_5(self):
        """Chapter values should be integers 1-5."""
        from nikita.config.enums import Chapter

        assert Chapter.CURIOSITY == 1
        assert Chapter.INTRIGUE == 2
        assert Chapter.INVESTMENT == 3
        assert Chapter.INTIMACY == 4
        assert Chapter.ESTABLISHED == 5

    def test_chapter_is_int_enum(self):
        """Chapter should be an IntEnum for numeric operations."""
        from nikita.config.enums import Chapter

        # Should be usable as int
        assert Chapter.CURIOSITY + 1 == 2
        assert Chapter.ESTABLISHED > Chapter.CURIOSITY

    def test_chapter_name_display(self):
        """Chapter should have display name property."""
        from nikita.config.enums import Chapter

        assert Chapter.CURIOSITY.name_display == "Curiosity"
        assert Chapter.ESTABLISHED.name_display == "Established"


class TestGameStatusEnum:
    """Tests for GameStatus enum."""

    def test_game_status_has_four_values(self):
        """GameStatus enum should have 4 states."""
        from nikita.config.enums import GameStatus

        assert len(GameStatus) == 4

    def test_game_status_values(self):
        """GameStatus should have expected string values."""
        from nikita.config.enums import GameStatus

        assert GameStatus.ACTIVE.value == "active"
        assert GameStatus.BOSS_FIGHT.value == "boss_fight"
        assert GameStatus.GAME_OVER.value == "game_over"
        assert GameStatus.WON.value == "won"

    def test_game_status_is_playable(self):
        """GameStatus should have is_playable property."""
        from nikita.config.enums import GameStatus

        assert GameStatus.ACTIVE.is_playable is True
        assert GameStatus.BOSS_FIGHT.is_playable is True
        assert GameStatus.GAME_OVER.is_playable is False
        assert GameStatus.WON.is_playable is False


class TestEngagementStateEnum:
    """Tests for EngagementState enum (6-state model from spec 014)."""

    def test_engagement_state_has_six_values(self):
        """EngagementState should have exactly 6 states."""
        from nikita.config.enums import EngagementState

        assert len(EngagementState) == 6

    def test_engagement_state_values(self):
        """EngagementState should have expected values (6-state model from spec 014)."""
        from nikita.config.enums import EngagementState

        expected = {
            "calibrating",
            "in_zone",
            "drifting",
            "clingy",
            "distant",
            "out_of_zone",
        }
        actual = {state.value for state in EngagementState}
        assert actual == expected

    def test_engagement_state_is_healthy(self):
        """EngagementState should have is_healthy property."""
        from nikita.config.enums import EngagementState

        # Healthy states
        assert EngagementState.CALIBRATING.is_healthy is True
        assert EngagementState.IN_ZONE.is_healthy is True

        # Unhealthy states
        assert EngagementState.DRIFTING.is_healthy is False
        assert EngagementState.CLINGY.is_healthy is False
        assert EngagementState.DISTANT.is_healthy is False
        assert EngagementState.OUT_OF_ZONE.is_healthy is False


class TestMoodEnum:
    """Tests for Mood enum."""

    def test_mood_has_values(self):
        """Mood enum should have mood states."""
        from nikita.config.enums import Mood

        assert len(Mood) >= 5
        assert hasattr(Mood, "PLAYFUL")
        assert hasattr(Mood, "FLIRTY")
        assert hasattr(Mood, "VULNERABLE")


class TestTimeOfDayEnum:
    """Tests for TimeOfDay enum."""

    def test_time_of_day_has_five_periods(self):
        """TimeOfDay should have 5 periods."""
        from nikita.config.enums import TimeOfDay

        assert len(TimeOfDay) == 5

    def test_time_of_day_values(self):
        """TimeOfDay should have expected values."""
        from nikita.config.enums import TimeOfDay

        assert TimeOfDay.MORNING.value == "morning"
        assert TimeOfDay.AFTERNOON.value == "afternoon"
        assert TimeOfDay.EVENING.value == "evening"
        assert TimeOfDay.NIGHT.value == "night"
        assert TimeOfDay.SLEEP.value == "sleep"


class TestViceCategoryEnum:
    """Tests for ViceCategory enum (8 categories from spec 006)."""

    def test_vice_category_has_eight_values(self):
        """ViceCategory should have exactly 8 categories."""
        from nikita.config.enums import ViceCategory

        assert len(ViceCategory) == 8

    def test_vice_category_values(self):
        """ViceCategory should have all 8 categories."""
        from nikita.config.enums import ViceCategory

        expected = {
            "intellectual_dominance",
            "risk_taking",
            "substances",
            "sexuality",
            "emotional_intensity",
            "rule_breaking",
            "dark_humor",
            "vulnerability",
        }
        actual = {cat.value for cat in ViceCategory}
        assert actual == expected


class TestViceIntensityEnum:
    """Tests for ViceIntensity enum."""

    def test_vice_intensity_has_three_levels(self):
        """ViceIntensity should have 3 levels."""
        from nikita.config.enums import ViceIntensity

        assert len(ViceIntensity) == 3

    def test_vice_intensity_values(self):
        """ViceIntensity should have low/medium/high."""
        from nikita.config.enums import ViceIntensity

        assert ViceIntensity.LOW.value == "low"
        assert ViceIntensity.MEDIUM.value == "medium"
        assert ViceIntensity.HIGH.value == "high"


class TestMetricEnum:
    """Tests for Metric enum (4 relationship metrics)."""

    def test_metric_has_four_values(self):
        """Metric should have exactly 4 metrics."""
        from nikita.config.enums import Metric

        assert len(Metric) == 4

    def test_metric_values(self):
        """Metric should have the 4 relationship metrics."""
        from nikita.config.enums import Metric

        expected = {"intimacy", "passion", "trust", "secureness"}
        actual = {m.value for m in Metric}
        assert actual == expected
