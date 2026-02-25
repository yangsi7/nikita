"""Tests for decay calculator (spec 005).

TDD: These tests define the expected behavior for DecayCalculator.
Tests written FIRST before implementation.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from nikita.engine.constants import DECAY_RATES, GRACE_PERIODS
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
        # Ch1 grace = 72h (Spec 101 FR-003: inverted), so 5h ago is within grace
        last_interaction = datetime.now(UTC) - timedelta(hours=5)
        user = create_mock_user(chapter=1, last_interaction_at=last_interaction)

        assert calculator.is_overdue(user) is False

    def test_is_overdue_past_grace_returns_true(self):
        """User past grace period IS overdue."""
        calculator = DecayCalculator()
        # Ch5 grace = 8h (Spec 101 FR-003: inverted), so 10h ago is past grace
        last_interaction = datetime.now(UTC) - timedelta(hours=10)
        user = create_mock_user(chapter=5, last_interaction_at=last_interaction)

        assert calculator.is_overdue(user) is True

    def test_is_overdue_just_inside_grace_returns_false(self):
        """User just inside grace period is NOT overdue."""
        calculator = DecayCalculator()
        # Ch5 grace = 8h (Spec 101 FR-003: inverted), so 7:59:59 should still be safe
        last_interaction = datetime.now(UTC) - timedelta(hours=7, minutes=59, seconds=59)
        user = create_mock_user(chapter=5, last_interaction_at=last_interaction)

        assert calculator.is_overdue(user) is False

    @pytest.mark.parametrize(
        "chapter,grace_hours",
        [
            (1, 72),
            (2, 48),
            (3, 24),
            (4, 16),
            (5, 8),
        ],
    )
    def test_is_overdue_respects_chapter_grace_periods(self, chapter: int, grace_hours: int):
        """Each chapter has correct grace period from GRACE_PERIODS."""
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
        # Ch5: grace=8h (Spec 101 FR-003), rate=0.2/h
        # 10 hours ago = 2 hours overdue
        last_interaction = datetime.now(UTC) - timedelta(hours=10)
        user = create_mock_user(
            chapter=5,
            relationship_score=Decimal("50.0"),
            last_interaction_at=last_interaction,
        )

        result = calculator.calculate_decay(user)

        assert result is not None
        assert isinstance(result, DecayResult)
        assert result.user_id == user.id

    def test_calculate_decay_correct_amount_ch1(self):
        """Ch1: 2h overdue × 0.8%/h = 1.6% decay (Spec 101 FR-003: Ch1 grace=72h)."""
        calculator = DecayCalculator()
        # Ch1: grace=72h, rate=0.8/h
        # 74 hours ago = 2 hours overdue
        last_interaction = datetime.now(UTC) - timedelta(hours=74)
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
        """Ch1: 10h overdue × 0.8%/h = 8.0% decay (Spec 101 FR-003: Ch1 grace=72h)."""
        calculator = DecayCalculator()
        # Ch1: grace=72h, rate=0.8/h
        # 82 hours ago = 10 hours overdue
        last_interaction = datetime.now(UTC) - timedelta(hours=82)
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
        """Each chapter uses correct decay rate from DECAY_RATES."""
        calculator = DecayCalculator()
        grace = GRACE_PERIODS[chapter]

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

        # Ch1: grace=72h (Spec 101 FR-003), rate=0.8/h
        # 50 hours overdue would be 40% decay without cap
        last_interaction = datetime.now(UTC) - timedelta(hours=122)  # 122 - 72 = 50h overdue
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

        # Ch1: grace=72h (Spec 101 FR-003), rate=0.8/h
        # 30 hours overdue would be 24% decay without cap
        last_interaction = datetime.now(UTC) - timedelta(hours=102)  # 102 - 72 = 30h overdue
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

        # Ch5: grace=8h (Spec 101 FR-003), rate=0.2/h; 10h overdue = 8% decay
        last_interaction = datetime.now(UTC) - timedelta(hours=18)
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

        # Ch5: grace=8h (Spec 101 FR-003), rate=0.2/h; 5h overdue = 1% decay
        last_interaction = datetime.now(UTC) - timedelta(hours=13)
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

        # Ch5: grace=8h (Spec 101 FR-003), 2h overdue × 0.2/h = 0.4% decay
        last_interaction = datetime.now(UTC) - timedelta(hours=10)
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

        # Ch5: grace=8h (Spec 101 FR-003), 12h since interaction = 4h overdue
        last_interaction = datetime.now(UTC) - timedelta(hours=12)
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

        # Ch5: grace=8h (Spec 101 FR-003), 10h ago = 2h overdue
        last_interaction = datetime.now(UTC) - timedelta(hours=10)
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

        # Ch5: grace=8h (Spec 101 FR-003), 10h ago = 2h overdue
        last_interaction = datetime.now(UTC) - timedelta(hours=10)
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
