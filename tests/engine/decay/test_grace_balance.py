"""Tests for Spec 101 FR-003: Ch1 decay rebalancing.

Verifies inverted grace periods: longest for new players, shortest for veterans.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

from nikita.engine.constants import GRACE_PERIODS
from nikita.engine.decay.calculator import DecayCalculator


def create_mock_user(*, chapter: int, hours_since: float) -> MagicMock:
    user = MagicMock()
    user.id = uuid4()
    user.chapter = chapter
    user.relationship_score = Decimal("50.0")
    user.last_interaction_at = datetime.now(UTC) - timedelta(hours=hours_since)
    user.game_status = "active"
    return user


class TestGraceBalanceSpec101:
    """Verify inverted grace periods favor new players."""

    def test_ch1_user_safe_at_70h(self):
        """Ch1 user with 70h inactivity is NOT overdue (within 72h grace)."""
        calc = DecayCalculator()
        user = create_mock_user(chapter=1, hours_since=70)
        assert calc.is_overdue(user) is False

    def test_ch5_user_overdue_at_9h(self):
        """Ch5 user with 9h inactivity IS overdue (past 8h grace)."""
        calc = DecayCalculator()
        user = create_mock_user(chapter=5, hours_since=9)
        assert calc.is_overdue(user) is True

    def test_grace_periods_inverted_order(self):
        """Grace periods should decrease from Ch1 to Ch5."""
        assert GRACE_PERIODS[1] > GRACE_PERIODS[2]
        assert GRACE_PERIODS[2] > GRACE_PERIODS[3]
        assert GRACE_PERIODS[3] > GRACE_PERIODS[4]
        assert GRACE_PERIODS[4] > GRACE_PERIODS[5]

    def test_ch1_grace_is_72_hours(self):
        """Ch1 should have 72h grace period."""
        assert GRACE_PERIODS[1] == timedelta(hours=72)

    def test_ch5_grace_is_8_hours(self):
        """Ch5 should have 8h grace period."""
        assert GRACE_PERIODS[5] == timedelta(hours=8)
