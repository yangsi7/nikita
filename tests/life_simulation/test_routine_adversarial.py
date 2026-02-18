"""Adversarial tests for WeeklyRoutine and DayRoutine models (DA-09).

Targets: nikita/life_simulation/models.py — Spec 055 routine models.

Edge cases tested:
- DayRoutine: empty fields, invalid day_of_week, invalid enums
- WeeklyRoutine: default(), get_day_for_date() with various dates, invalid keys
- DayRoutine.format_for_prompt(): empty activities, many activities (100+)
- WeeklyRoutine.from_yaml(): missing file, invalid YAML content
"""

import pytest
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import patch

from pydantic import ValidationError

from nikita.life_simulation.models import (
    DayRoutine,
    WeeklyRoutine,
    VALID_DAYS,
    VALID_WORK_SCHEDULES,
    VALID_ENERGY_PATTERNS,
    VALID_SOCIAL_AVAILABILITY,
)


# =============================================================================
# TestDayRoutineAdversarial
# =============================================================================


class TestDayRoutineAdversarial:
    """Edge cases for DayRoutine model."""

    def test_valid_minimal(self):
        """Minimal valid DayRoutine with just day_of_week."""
        dr = DayRoutine(day_of_week="monday")
        assert dr.day_of_week == "monday"
        assert dr.activities == []
        assert dr.work_schedule == "office"

    def test_empty_activities_list(self):
        """Empty activities list is valid."""
        dr = DayRoutine(day_of_week="tuesday", activities=[])
        assert dr.activities == []

    def test_invalid_day_of_week_number(self):
        """Numeric day_of_week should fail validation."""
        with pytest.raises(ValidationError):
            DayRoutine(day_of_week="8")

    def test_invalid_day_of_week_misspelled(self):
        """Misspelled day should fail validation."""
        with pytest.raises(ValidationError):
            DayRoutine(day_of_week="monnday")

    def test_invalid_day_of_week_empty(self):
        """Empty string day_of_week should fail validation."""
        with pytest.raises(ValidationError):
            DayRoutine(day_of_week="")

    def test_day_of_week_case_insensitive(self):
        """day_of_week validator lowercases input."""
        dr = DayRoutine(day_of_week="MONDAY")
        assert dr.day_of_week == "monday"

    def test_day_of_week_mixed_case(self):
        """Mixed case day_of_week is normalized."""
        dr = DayRoutine(day_of_week="Wednesday")
        assert dr.day_of_week == "wednesday"

    def test_invalid_work_schedule(self):
        """Invalid work_schedule should fail validation."""
        with pytest.raises(ValidationError):
            DayRoutine(day_of_week="monday", work_schedule="hybrid")

    def test_invalid_energy_pattern(self):
        """Invalid energy_pattern should fail validation."""
        with pytest.raises(ValidationError):
            DayRoutine(day_of_week="monday", energy_pattern="extreme")

    def test_invalid_social_availability(self):
        """Invalid social_availability should fail validation."""
        with pytest.raises(ValidationError):
            DayRoutine(day_of_week="monday", social_availability="very_high")

    def test_all_valid_days(self):
        """Every valid day name should be accepted."""
        for day in VALID_DAYS:
            dr = DayRoutine(day_of_week=day)
            assert dr.day_of_week == day

    def test_all_valid_work_schedules(self):
        """Every valid work_schedule should be accepted."""
        for ws in VALID_WORK_SCHEDULES:
            dr = DayRoutine(day_of_week="monday", work_schedule=ws)
            assert dr.work_schedule == ws

    def test_all_valid_energy_patterns(self):
        """Every valid energy_pattern should be accepted."""
        for ep in VALID_ENERGY_PATTERNS:
            dr = DayRoutine(day_of_week="monday", energy_pattern=ep)
            assert dr.energy_pattern == ep

    def test_all_valid_social_availabilities(self):
        """Every valid social_availability should be accepted."""
        for sa in VALID_SOCIAL_AVAILABILITY:
            dr = DayRoutine(day_of_week="monday", social_availability=sa)
            assert dr.social_availability == sa

    def test_enum_values_case_insensitive(self):
        """Enum validators lowercase input."""
        dr = DayRoutine(
            day_of_week="FRIDAY",
            work_schedule="REMOTE",
            energy_pattern="HIGH",
            social_availability="LOW",
        )
        assert dr.day_of_week == "friday"
        assert dr.work_schedule == "remote"
        assert dr.energy_pattern == "high"
        assert dr.social_availability == "low"


# =============================================================================
# TestWeeklyRoutineAdversarial
# =============================================================================


class TestWeeklyRoutineAdversarial:
    """Edge cases for WeeklyRoutine model."""

    def test_default_returns_weeklyRoutine(self):
        """WeeklyRoutine.default() returns a valid WeeklyRoutine."""
        wr = WeeklyRoutine.default()
        assert isinstance(wr, WeeklyRoutine)
        # Should have at least some days defined
        assert len(wr.days) > 0

    def test_default_has_all_seven_days(self):
        """Default routine should define all 7 days (from fallback or YAML)."""
        wr = WeeklyRoutine.default()
        assert len(wr.days) == 7
        for day in VALID_DAYS:
            assert day in wr.days

    def test_empty_days(self):
        """WeeklyRoutine with empty days dict is valid."""
        wr = WeeklyRoutine(days={})
        assert wr.days == {}

    def test_invalid_day_key(self):
        """Invalid day key in days dict should fail validation."""
        with pytest.raises(ValidationError):
            WeeklyRoutine(days={"invalidday": DayRoutine(day_of_week="monday")})

    def test_get_day_existing(self):
        """get_day() for existing day returns DayRoutine."""
        wr = WeeklyRoutine.default()
        result = wr.get_day("monday")
        assert isinstance(result, DayRoutine)

    def test_get_day_nonexistent(self):
        """get_day() for non-existent day returns None."""
        wr = WeeklyRoutine(days={})
        result = wr.get_day("monday")
        assert result is None

    def test_get_day_case_insensitive(self):
        """get_day() lowercases the input."""
        wr = WeeklyRoutine.default()
        result_lower = wr.get_day("monday")
        result_upper = wr.get_day("MONDAY")
        result_mixed = wr.get_day("Monday")
        assert result_lower == result_upper == result_mixed

    def test_get_day_for_date_known_day(self):
        """get_day_for_date() for a specific date returns correct day's routine."""
        wr = WeeklyRoutine.default()
        # 2026-02-18 is a Wednesday
        target = date(2026, 2, 18)
        result = wr.get_day_for_date(target)
        assert result is not None
        assert result.day_of_week == "wednesday"

    def test_get_day_for_date_all_week(self):
        """get_day_for_date() for each day of a full week matches expected day."""
        wr = WeeklyRoutine.default()
        # 2026-02-16 is Monday through 2026-02-22 is Sunday
        expected_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for i, expected in enumerate(expected_days):
            target = date(2026, 2, 16 + i)
            result = wr.get_day_for_date(target)
            assert result is not None, f"No routine for {target} ({expected})"
            assert result.day_of_week == expected, f"Expected {expected} for {target}, got {result.day_of_week}"

    def test_get_day_for_date_empty_routine(self):
        """get_day_for_date() on empty routine returns None."""
        wr = WeeklyRoutine(days={})
        result = wr.get_day_for_date(date(2026, 2, 18))
        assert result is None

    def test_get_day_for_date_partial_routine(self):
        """get_day_for_date() on partial routine returns None for missing days."""
        wr = WeeklyRoutine(days={
            "monday": DayRoutine(day_of_week="monday"),
        })
        # 2026-02-18 is Wednesday
        assert wr.get_day_for_date(date(2026, 2, 18)) is None
        # 2026-02-16 is Monday
        result = wr.get_day_for_date(date(2026, 2, 16))
        assert result is not None
        assert result.day_of_week == "monday"

    def test_from_yaml_missing_file(self):
        """from_yaml() with nonexistent path raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            WeeklyRoutine.from_yaml(Path("/nonexistent/routine.yaml"))

    def test_from_yaml_empty_file(self):
        """from_yaml() with empty YAML raises ValueError."""
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            f.flush()
            with pytest.raises(ValueError, match="missing 'days' key"):
                WeeklyRoutine.from_yaml(Path(f.name))

    def test_from_yaml_no_days_key(self):
        """from_yaml() with YAML missing 'days' key raises ValueError."""
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("timezone: Europe/Berlin\n")
            f.flush()
            with pytest.raises(ValueError, match="missing 'days' key"):
                WeeklyRoutine.from_yaml(Path(f.name))

    def test_from_yaml_valid_minimal(self):
        """from_yaml() with minimal valid YAML works."""
        yaml_content = """
days:
  monday:
    wake_time: "07:00"
    work_schedule: office
    energy_pattern: high
    social_availability: moderate
"""
        with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()
            wr = WeeklyRoutine.from_yaml(Path(f.name))
            assert "monday" in wr.days
            assert wr.days["monday"].wake_time == "07:00"

    def test_default_fallback_on_corrupt_yaml(self):
        """default() falls back to hardcoded routine if YAML is corrupt."""
        with patch("nikita.life_simulation.models.Path") as mock_path_cls:
            # Make the config path point to a nonexistent file
            mock_path = mock_path_cls.return_value.__truediv__.return_value.__truediv__.return_value
            mock_path.exists.return_value = False

            # default() uses from_yaml which catches FileNotFoundError
            # and returns hardcoded fallback
            wr = WeeklyRoutine.default()
            assert isinstance(wr, WeeklyRoutine)
            # Fallback should have 7 days
            assert len(wr.days) == 7


# =============================================================================
# TestFormatForPromptAdversarial
# =============================================================================


class TestFormatForPromptAdversarial:
    """Edge cases for DayRoutine.format_for_prompt()."""

    def test_empty_activities(self):
        """Empty activities -> 'no specific plans' in output."""
        dr = DayRoutine(day_of_week="monday", activities=[])
        prompt = dr.format_for_prompt()
        assert "no specific plans" in prompt
        assert "Monday" in prompt

    def test_single_activity(self):
        """Single activity listed."""
        dr = DayRoutine(day_of_week="tuesday", activities=["gym"])
        prompt = dr.format_for_prompt()
        assert "gym" in prompt
        assert "Tuesday" in prompt

    def test_many_activities_100(self):
        """100 activities should render without error (stress test)."""
        activities = [f"activity_{i}" for i in range(100)]
        dr = DayRoutine(day_of_week="friday", activities=activities)
        prompt = dr.format_for_prompt()
        # Should contain all activities joined by comma
        assert "activity_0" in prompt
        assert "activity_99" in prompt
        # Verify comma separation
        assert ", " in prompt
        # Output should be non-trivially long
        assert len(prompt) > 500

    def test_many_activities_1000(self):
        """1000 activities should still work (no truncation in model)."""
        activities = [f"task_{i}" for i in range(1000)]
        dr = DayRoutine(day_of_week="saturday", activities=activities)
        prompt = dr.format_for_prompt()
        assert "task_999" in prompt

    def test_activities_with_special_chars(self):
        """Activities with special characters render correctly."""
        dr = DayRoutine(
            day_of_week="wednesday",
            activities=["gym @ 7am", "meeting (zoom)", "lunch: sushi", "read 'book'"],
        )
        prompt = dr.format_for_prompt()
        assert "gym @ 7am" in prompt
        assert "meeting (zoom)" in prompt

    def test_format_includes_all_fields(self):
        """format_for_prompt() includes day, wake_time, work, energy, social."""
        dr = DayRoutine(
            day_of_week="thursday",
            wake_time="06:30",
            work_schedule="remote",
            energy_pattern="high",
            social_availability="low",
            activities=["yoga"],
        )
        prompt = dr.format_for_prompt()
        assert "Thursday" in prompt
        assert "06:30" in prompt
        assert "remote" in prompt
        assert "high" in prompt
        assert "low" in prompt
        assert "yoga" in prompt

    def test_format_day_capitalized(self):
        """Day name is capitalized in output."""
        dr = DayRoutine(day_of_week="sunday")
        prompt = dr.format_for_prompt()
        assert "Sunday" in prompt

    def test_activities_with_empty_strings(self):
        """Activities list with empty strings -> comma-joined includes empties."""
        dr = DayRoutine(day_of_week="monday", activities=["", "real_activity", ""])
        prompt = dr.format_for_prompt()
        # Empty strings still get joined: ", real_activity, "
        assert "real_activity" in prompt

    def test_activities_with_newlines(self):
        """Activities with newline characters -> embedded in output."""
        dr = DayRoutine(day_of_week="monday", activities=["line1\nline2"])
        prompt = dr.format_for_prompt()
        assert "line1\nline2" in prompt


# =============================================================================
# TestWeeklyRoutineDateMapping
# =============================================================================


class TestWeeklyRoutineDateMapping:
    """Exhaustive date-to-day mapping tests."""

    def test_leap_year_date(self):
        """Feb 29 on leap year maps correctly."""
        wr = WeeklyRoutine.default()
        # 2028-02-29 is a Tuesday
        result = wr.get_day_for_date(date(2028, 2, 29))
        assert result is not None
        assert result.day_of_week == "tuesday"

    def test_new_years_day(self):
        """Jan 1 maps correctly."""
        wr = WeeklyRoutine.default()
        # 2026-01-01 is a Thursday
        result = wr.get_day_for_date(date(2026, 1, 1))
        assert result is not None
        assert result.day_of_week == "thursday"

    def test_dec_31(self):
        """Dec 31 maps correctly."""
        wr = WeeklyRoutine.default()
        # 2026-12-31 is a Thursday
        result = wr.get_day_for_date(date(2026, 12, 31))
        assert result is not None
        assert result.day_of_week == "thursday"

    def test_far_future_date(self):
        """Date far in the future still works."""
        wr = WeeklyRoutine.default()
        result = wr.get_day_for_date(date(2099, 12, 25))
        assert result is not None
        assert result.day_of_week in VALID_DAYS

    def test_past_date(self):
        """Historical date still works."""
        wr = WeeklyRoutine.default()
        result = wr.get_day_for_date(date(2000, 1, 1))
        assert result is not None
        # 2000-01-01 is Saturday
        assert result.day_of_week == "saturday"
