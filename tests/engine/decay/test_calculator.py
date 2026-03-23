"""Tests for decay calculator (spec 005).

TDD: These tests define the expected behavior for DecayCalculator.
Tests written FIRST before implementation.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from nikita.config import get_config
from nikita.engine.decay.calculator import DecayCalculator
from nikita.engine.decay.models import DecayResult


def create_mock_user(
    *,
    chapter: int = 1,
    relationship_score: Decimal = Decimal("50.0"),
    last_interaction_at: datetime | None = None,
    game_status: str = "active",
) -> MagicMock:
    """Create a mock user with specified attributes."""
    user = MagicMock()
    user.id = uuid4()
    user.chapter = chapter
    user.relationship_score = relationship_score
    user.last_interaction_at = last_interaction_at
    user.game_status = game_status
    return user


class TestDecayCalculatorIsOverdue:
    """Test is_overdue() method."""

    def test_is_overdue_no_interaction_returns_true(self):
        """User with no last_interaction_at is considered overdue."""
        calculator = DecayCalculator()
        user = create_mock_user(chapter=1, last_interaction_at=None)

        assert calculator.is_overdue(user) is True

    def test_is_overdue_within_grace_returns_false(self):
        """User within grace period is NOT overdue."""
        calculator = DecayCalculator()
        # Ch1 grace = 8h (YAML config), so 5h ago is still within grace
        last_interaction = datetime.now(UTC) - timedelta(hours=5)
        user = create_mock_user(chapter=1, last_interaction_at=last_interaction)

        assert calculator.is_overdue(user) is False

    def test_is_overdue_past_grace_returns_true(self):
        """User past grace period IS overdue."""
        calculator = DecayCalculator()
        # Ch1 grace = 8h (YAML config), so 10h ago is past grace
        last_interaction = datetime.now(UTC) - timedelta(hours=10)
        user = create_mock_user(chapter=1, last_interaction_at=last_interaction)

        assert calculator.is_overdue(user) is True

    def test_is_overdue_just_inside_grace_returns_false(self):
        """User just inside grace period is NOT overdue."""
        calculator = DecayCalculator()
        # Ch1 grace = 8h (YAML config), so 7:59:59 should still be safe
        last_interaction = datetime.now(UTC) - timedelta(hours=7, minutes=59, seconds=59)
        user = create_mock_user(chapter=1, last_interaction_at=last_interaction)

        assert calculator.is_overdue(user) is False

    @pytest.mark.parametrize(
        "chapter,grace_hours",
        [
            (1, 8),
            (2, 16),
            (3, 24),
            (4, 48),
            (5, 72),
        ],
    )
    def test_is_overdue_respects_chapter_grace_periods(self, chapter: int, grace_hours: int):
        """Each chapter has correct grace period from YAML config (Spec 117)."""
        calculator = DecayCalculator()

        # Just within grace (1 hour less than grace period)
        within_grace = datetime.now(UTC) - timedelta(hours=grace_hours - 1)
        user_within = create_mock_user(chapter=chapter, last_interaction_at=within_grace)
        assert calculator.is_overdue(user_within) is False

        # Just past grace (1 hour more than grace period)
        past_grace = datetime.now(UTC) - timedelta(hours=grace_hours + 1)
        user_past = create_mock_user(chapter=chapter, last_interaction_at=past_grace)
        assert calculator.is_overdue(user_past) is True


class TestDecayCalculatorCalculateDecay:
    """Test calculate_decay() method."""

    def test_calculate_decay_within_grace_returns_none(self):
        """No decay if user is within grace period."""
        calculator = DecayCalculator()
        # Ch1 grace = 72h (Spec 101 FR-003), so 5h ago is within grace
        last_interaction = datetime.now(UTC) - timedelta(hours=5)
        user = create_mock_user(
            chapter=1,
            relationship_score=Decimal("50.0"),
            last_interaction_at=last_interaction,
        )

        result = calculator.calculate_decay(user)
        assert result is None

    def test_calculate_decay_past_grace_returns_decay_result(self):
        """Returns DecayResult when user is past grace."""
        calculator = DecayCalculator()
        # Ch1: grace=8h (YAML), rate=0.8/h; 10 hours ago = 2 hours overdue
        last_interaction = datetime.now(UTC) - timedelta(hours=10)
        user = create_mock_user(
            chapter=1,
            relationship_score=Decimal("50.0"),
            last_interaction_at=last_interaction,
        )

        result = calculator.calculate_decay(user)

        assert result is not None
        assert isinstance(result, DecayResult)
        assert result.user_id == user.id

    def test_calculate_decay_correct_amount_ch1(self):
        """Ch1: 2h overdue × 0.8%/h = 1.6% decay (YAML: Ch1 grace=8h)."""
        calculator = DecayCalculator()
        # Ch1: grace=8h, rate=0.8/h; 10 hours ago = 2 hours overdue
        last_interaction = datetime.now(UTC) - timedelta(hours=10)
        user = create_mock_user(
            chapter=1,
            relationship_score=Decimal("50.0"),
            last_interaction_at=last_interaction,
        )

        result = calculator.calculate_decay(user)

        assert result is not None
        # 2 hours × 0.8 ≈ 1.6 (allow small timing variance)
        assert float(result.decay_amount) == pytest.approx(1.6, abs=0.01)
        assert result.score_before == Decimal("50.0")
        assert float(result.score_after) == pytest.approx(48.4, abs=0.01)
        assert result.chapter == 1

    def test_calculate_decay_correct_amount_ch1_10h_overdue(self):
        """Ch1: 10h overdue × 0.8%/h = 8.0% decay (YAML: Ch1 grace=8h)."""
        calculator = DecayCalculator()
        # Ch1: grace=8h, rate=0.8/h; 18 hours ago = 10 hours overdue
        last_interaction = datetime.now(UTC) - timedelta(hours=18)
        user = create_mock_user(
            chapter=1,
            relationship_score=Decimal("65.0"),
            last_interaction_at=last_interaction,
        )

        result = calculator.calculate_decay(user)

        assert result is not None
        # 10 hours × 0.8 ≈ 8.0 (allow small timing variance)
        assert float(result.decay_amount) == pytest.approx(8.0, abs=0.01)
        assert result.score_before == Decimal("65.0")
        assert float(result.score_after) == pytest.approx(57.0, abs=0.01)

    @pytest.mark.parametrize(
        "chapter,rate",
        [
            (1, Decimal("0.8")),
            (2, Decimal("0.6")),
            (3, Decimal("0.4")),
            (4, Decimal("0.3")),
            (5, Decimal("0.2")),
        ],
    )
    def test_calculate_decay_uses_chapter_specific_rates(self, chapter: int, rate: Decimal):
        """Each chapter uses correct decay rate from YAML config (Spec 117)."""
        calculator = DecayCalculator()
        grace = get_config().get_grace_period(chapter)

        # 5 hours past grace
        last_interaction = datetime.now(UTC) - (grace + timedelta(hours=5))
        user = create_mock_user(
            chapter=chapter,
            relationship_score=Decimal("60.0"),
            last_interaction_at=last_interaction,
        )

        result = calculator.calculate_decay(user)

        assert result is not None
        expected_decay = float(5 * rate)  # 5 hours × chapter rate
        # Allow small timing variance
        assert float(result.decay_amount) == pytest.approx(expected_decay, abs=0.01)
        assert float(result.score_after) == pytest.approx(60.0 - expected_decay, abs=0.01)

    def test_calculate_decay_capped_at_max(self):
        """Decay capped at MAX_DECAY_PER_CYCLE (default 20%)."""
        calculator = DecayCalculator(max_decay_per_cycle=Decimal("20.0"))

        # Ch1: grace=8h (YAML), rate=0.8/h; 50 hours overdue = 40% decay without cap
        last_interaction = datetime.now(UTC) - timedelta(hours=58)  # 58 - 8 = 50h overdue
        user = create_mock_user(
            chapter=1,
            relationship_score=Decimal("100.0"),
            last_interaction_at=last_interaction,
        )

        result = calculator.calculate_decay(user)

        assert result is not None
        # Should cap at 20%, not 40%
        assert result.decay_amount == Decimal("20.0")
        assert result.score_after == Decimal("80.0")

    def test_calculate_decay_configurable_max(self):
        """Max decay can be configured."""
        calculator = DecayCalculator(max_decay_per_cycle=Decimal("15.0"))

        # Ch1: grace=8h (YAML), rate=0.8/h; 30 hours overdue = 24% decay without cap
        last_interaction = datetime.now(UTC) - timedelta(hours=38)  # 38 - 8 = 30h overdue
        user = create_mock_user(
            chapter=1,
            relationship_score=Decimal("100.0"),
            last_interaction_at=last_interaction,
        )

        result = calculator.calculate_decay(user)

        assert result is not None
        # Should cap at 15%, not 24%
        assert result.decay_amount == Decimal("15.0")
        assert result.score_after == Decimal("85.0")

    def test_calculate_decay_floor_at_zero(self):
        """Score floors at 0 when decay exceeds score."""
        calculator = DecayCalculator()

        # Ch5: grace=72h (YAML), rate=0.2/h; 10h overdue = 2% decay
        last_interaction = datetime.now(UTC) - timedelta(hours=82)  # 82 - 72 = 10h overdue
        user = create_mock_user(
            chapter=5,
            relationship_score=Decimal("1.0"),  # Only 1%, less than 2% decay (10h*0.2)
            last_interaction_at=last_interaction,
        )

        result = calculator.calculate_decay(user)

        assert result is not None
        # Floor at 0
        assert result.score_after == Decimal("0.0")
        # Actual decay applied is limited to what was available
        assert result.decay_amount == Decimal("1.0")
        assert result.game_over_triggered is True

    def test_calculate_decay_game_over_triggered_at_zero(self):
        """game_over_triggered is True when score reaches 0."""
        calculator = DecayCalculator()

        # Ch5: grace=72h (YAML), rate=0.2/h; 5h overdue = 1% decay
        last_interaction = datetime.now(UTC) - timedelta(hours=77)  # 77 - 72 = 5h overdue
        user = create_mock_user(
            chapter=5,
            relationship_score=Decimal("0.5"),  # Less than 1% decay
            last_interaction_at=last_interaction,
        )

        result = calculator.calculate_decay(user)

        assert result is not None
        assert result.score_after == Decimal("0.0")
        assert result.game_over_triggered is True

    def test_calculate_decay_no_game_over_when_score_above_zero(self):
        """game_over_triggered is False when score remains above 0."""
        calculator = DecayCalculator()

        # Ch5: grace=72h (YAML), 2h overdue × 0.2/h = 0.4% decay
        last_interaction = datetime.now(UTC) - timedelta(hours=74)  # 74 - 72 = 2h overdue
        user = create_mock_user(
            chapter=5,
            relationship_score=Decimal("50.0"),
            last_interaction_at=last_interaction,
        )

        result = calculator.calculate_decay(user)

        assert result is not None
        # 2h * 0.2 = 0.4 decay; 50.0 - 0.4 = 49.6
        assert float(result.score_after) == pytest.approx(49.6, abs=0.01)
        assert result.game_over_triggered is False

    def test_calculate_decay_includes_hours_overdue(self):
        """DecayResult includes hours_overdue for audit trail."""
        calculator = DecayCalculator()

        # Ch5: grace=72h (YAML), 76h since interaction = 4h overdue
        last_interaction = datetime.now(UTC) - timedelta(hours=76)
        user = create_mock_user(
            chapter=5,
            relationship_score=Decimal("50.0"),
            last_interaction_at=last_interaction,
        )

        result = calculator.calculate_decay(user)

        assert result is not None
        # Should be approximately 4 hours (allow small timing tolerance)
        assert 3.9 <= result.hours_overdue <= 4.1

    def test_calculate_decay_includes_timestamp(self):
        """DecayResult includes calculation timestamp."""
        calculator = DecayCalculator()

        before = datetime.now(UTC)

        # Ch5: grace=72h (YAML), 74h ago = 2h overdue
        last_interaction = datetime.now(UTC) - timedelta(hours=74)
        user = create_mock_user(
            chapter=5,
            relationship_score=Decimal("50.0"),
            last_interaction_at=last_interaction,
        )

        result = calculator.calculate_decay(user)

        after = datetime.now(UTC)

        assert result is not None
        assert before <= result.timestamp <= after

    def test_calculate_decay_sets_decay_reason(self):
        """DecayResult includes decay_reason='inactivity'."""
        calculator = DecayCalculator()

        # Ch5: grace=72h (YAML), 74h ago = 2h overdue
        last_interaction = datetime.now(UTC) - timedelta(hours=74)
        user = create_mock_user(
            chapter=5,
            relationship_score=Decimal("50.0"),
            last_interaction_at=last_interaction,
        )

        result = calculator.calculate_decay(user)

        assert result is not None
        assert result.decay_reason == "inactivity"


class TestDecayCalculatorDefaultMaxDecay:
    """Test default max_decay_per_cycle behavior."""

    def test_default_max_decay_is_20(self):
        """Default MAX_DECAY_PER_CYCLE is 20%."""
        calculator = DecayCalculator()

        assert calculator.max_decay_per_cycle == Decimal("20.0")

    def test_custom_max_decay_accepted(self):
        """Custom max_decay_per_cycle is accepted."""
        calculator = DecayCalculator(max_decay_per_cycle=Decimal("10.0"))

        assert calculator.max_decay_per_cycle == Decimal("10.0")


class TestDecayAllChaptersRateApplication:
    """GH #148: Verify decay rate application for ALL 5 chapters.

    Each test case specifies: chapter, hours_overdue past grace, starting score,
    and expected decay = hours_overdue * chapter_rate.
    """

    @pytest.mark.parametrize(
        "chapter,grace_hours,rate,hours_overdue,start_score,expected_decay",
        [
            # Ch1: 0.8%/hr, 8h grace — 3h overdue => 2.4
            (1, 8, Decimal("0.8"), 3, Decimal("50.0"), 2.4),
            # Ch2: 0.6%/hr, 16h grace — 4h overdue => 2.4
            (2, 16, Decimal("0.6"), 4, Decimal("50.0"), 2.4),
            # Ch3: 0.4%/hr, 24h grace — 6h overdue => 2.4
            (3, 24, Decimal("0.4"), 6, Decimal("50.0"), 2.4),
            # Ch4: 0.3%/hr, 48h grace — 8h overdue => 2.4
            (4, 48, Decimal("0.3"), 8, Decimal("50.0"), 2.4),
            # Ch5: 0.2%/hr, 72h grace — 12h overdue => 2.4
            (5, 72, Decimal("0.2"), 12, Decimal("50.0"), 2.4),
        ],
        ids=["ch1-0.8/hr", "ch2-0.6/hr", "ch3-0.4/hr", "ch4-0.3/hr", "ch5-0.2/hr"],
    )
    def test_decay_amount_matches_chapter_rate(
        self,
        chapter: int,
        grace_hours: int,
        rate: Decimal,
        hours_overdue: int,
        start_score: Decimal,
        expected_decay: float,
    ):
        """Decay amount = hours_overdue * chapter rate for each chapter."""
        calculator = DecayCalculator()

        total_hours = grace_hours + hours_overdue
        last_interaction = datetime.now(UTC) - timedelta(hours=total_hours)
        user = create_mock_user(
            chapter=chapter,
            relationship_score=start_score,
            last_interaction_at=last_interaction,
        )

        result = calculator.calculate_decay(user)

        assert result is not None
        assert float(result.decay_amount) == pytest.approx(expected_decay, abs=0.02)
        expected_after = float(start_score) - expected_decay
        assert float(result.score_after) == pytest.approx(expected_after, abs=0.02)
        assert result.chapter == chapter

    @pytest.mark.parametrize(
        "chapter,grace_hours,rate,hours_overdue",
        [
            (1, 8, Decimal("0.8"), 10),   # Ch1: 10h * 0.8 = 8.0
            (2, 16, Decimal("0.6"), 10),   # Ch2: 10h * 0.6 = 6.0
            (3, 24, Decimal("0.4"), 10),   # Ch3: 10h * 0.4 = 4.0
            (4, 48, Decimal("0.3"), 10),   # Ch4: 10h * 0.3 = 3.0
            (5, 72, Decimal("0.2"), 10),   # Ch5: 10h * 0.2 = 2.0
        ],
        ids=["ch1-10h", "ch2-10h", "ch3-10h", "ch4-10h", "ch5-10h"],
    )
    def test_decay_10h_overdue_all_chapters(
        self,
        chapter: int,
        grace_hours: int,
        rate: Decimal,
        hours_overdue: int,
    ):
        """10 hours overdue for each chapter produces distinct decay amounts."""
        calculator = DecayCalculator()

        total_hours = grace_hours + hours_overdue
        last_interaction = datetime.now(UTC) - timedelta(hours=total_hours)
        user = create_mock_user(
            chapter=chapter,
            relationship_score=Decimal("70.0"),
            last_interaction_at=last_interaction,
        )

        result = calculator.calculate_decay(user)

        assert result is not None
        expected_decay = float(hours_overdue * rate)
        assert float(result.decay_amount) == pytest.approx(expected_decay, abs=0.02)
        assert result.score_before == Decimal("70.0")
        assert float(result.score_after) == pytest.approx(70.0 - expected_decay, abs=0.02)
        assert result.hours_overdue == pytest.approx(hours_overdue, abs=0.1)


class TestDecayAllChaptersGracePeriod:
    """GH #148: Verify grace periods for ALL 5 chapters.

    Grace periods (from decay.yaml):
      Ch1=8h, Ch2=16h, Ch3=24h, Ch4=48h, Ch5=72h
    """

    @pytest.mark.parametrize(
        "chapter,grace_hours",
        [
            (1, 8),
            (2, 16),
            (3, 24),
            (4, 48),
            (5, 72),
        ],
        ids=["ch1-8h", "ch2-16h", "ch3-24h", "ch4-48h", "ch5-72h"],
    )
    def test_no_decay_within_grace_period(self, chapter: int, grace_hours: int):
        """No decay when interaction is within grace period for each chapter."""
        calculator = DecayCalculator()

        # Interaction at half the grace period ago — well within grace
        last_interaction = datetime.now(UTC) - timedelta(hours=grace_hours // 2)
        user = create_mock_user(
            chapter=chapter,
            relationship_score=Decimal("60.0"),
            last_interaction_at=last_interaction,
        )

        result = calculator.calculate_decay(user)
        assert result is None, f"Ch{chapter}: expected no decay within {grace_hours}h grace"

    @pytest.mark.parametrize(
        "chapter,grace_hours",
        [
            (1, 8),
            (2, 16),
            (3, 24),
            (4, 48),
            (5, 72),
        ],
        ids=["ch1-boundary", "ch2-boundary", "ch3-boundary", "ch4-boundary", "ch5-boundary"],
    )
    def test_no_decay_at_exact_grace_boundary(self, chapter: int, grace_hours: int):
        """At exact grace boundary, user is still safe (strictly greater than required)."""
        calculator = DecayCalculator()

        # Just inside grace boundary (1 second buffer to account for test execution time)
        last_interaction = datetime.now(UTC) - timedelta(hours=grace_hours) + timedelta(seconds=1)
        user = create_mock_user(
            chapter=chapter,
            relationship_score=Decimal("55.0"),
            last_interaction_at=last_interaction,
        )

        # At boundary is safe (calculator uses strictly-greater-than)
        assert calculator.is_overdue(user) is False
        result = calculator.calculate_decay(user)
        assert result is None, f"Ch{chapter}: expected no decay at exact {grace_hours}h boundary"

    @pytest.mark.parametrize(
        "chapter,grace_hours",
        [
            (1, 8),
            (2, 16),
            (3, 24),
            (4, 48),
            (5, 72),
        ],
        ids=["ch1-just-past", "ch2-just-past", "ch3-just-past", "ch4-just-past", "ch5-just-past"],
    )
    def test_decay_starts_just_past_grace(self, chapter: int, grace_hours: int):
        """Decay begins immediately once strictly past grace period."""
        calculator = DecayCalculator()

        # 1 minute past grace — should trigger decay
        last_interaction = datetime.now(UTC) - timedelta(hours=grace_hours, minutes=1)
        user = create_mock_user(
            chapter=chapter,
            relationship_score=Decimal("55.0"),
            last_interaction_at=last_interaction,
        )

        assert calculator.is_overdue(user) is True
        result = calculator.calculate_decay(user)
        assert result is not None, f"Ch{chapter}: expected decay just past {grace_hours}h grace"
        # Decay should be small (only ~1 minute overdue)
        assert result.decay_amount > Decimal("0")
        assert result.score_after < Decimal("55.0")

    @pytest.mark.parametrize(
        "chapter,grace_hours,rate",
        [
            (1, 8, Decimal("0.8")),
            (2, 16, Decimal("0.6")),
            (3, 24, Decimal("0.4")),
            (4, 48, Decimal("0.3")),
            (5, 72, Decimal("0.2")),
        ],
        ids=["ch1-verify", "ch2-verify", "ch3-verify", "ch4-verify", "ch5-verify"],
    )
    def test_grace_and_rate_from_config_match_yaml(
        self, chapter: int, grace_hours: int, rate: Decimal
    ):
        """Config values match decay.yaml for each chapter."""
        config = get_config()

        actual_grace = config.get_grace_period(chapter)
        assert actual_grace == timedelta(hours=grace_hours), (
            f"Ch{chapter}: expected grace={grace_hours}h, got {actual_grace}"
        )

        actual_rate = config.get_decay_rate(chapter)
        assert actual_rate == rate, (
            f"Ch{chapter}: expected rate={rate}, got {actual_rate}"
        )
