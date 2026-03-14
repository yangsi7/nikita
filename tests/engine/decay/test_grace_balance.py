"""Tests for grace period ordering and values from YAML config (Spec 117).

Verifies grace periods increase with chapter: Ch1 shortest, Ch5 longest.
This is the natural order (veterans get more grace), superseding the
old inverted pattern from engine.constants (Spec 101 FR-003).
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

from nikita.config import get_config
from nikita.engine.decay.calculator import DecayCalculator


def create_mock_user(*, chapter: int, hours_since: float) -> MagicMock:
    user = MagicMock()
    user.id = uuid4()
    user.chapter = chapter
    user.relationship_score = Decimal("50.0")
    user.last_interaction_at = datetime.now(UTC) - timedelta(hours=hours_since)
    user.game_status = "active"
    return user


class TestGraceBalanceSpec117:
    """Verify grace periods from YAML config (Ch1=8h, Ch5=72h)."""

    def test_ch1_user_overdue_at_9h(self):
        """Ch1 user with 9h inactivity IS overdue (Ch1 grace=8h per YAML)."""
        calc = DecayCalculator()
        user = create_mock_user(chapter=1, hours_since=9)
        assert calc.is_overdue(user) is True

    def test_ch1_user_safe_at_7h(self):
        """Ch1 user with 7h inactivity is NOT overdue (within 8h grace)."""
        calc = DecayCalculator()
        user = create_mock_user(chapter=1, hours_since=7)
        assert calc.is_overdue(user) is False

    def test_ch5_user_safe_at_70h(self):
        """Ch5 user with 70h inactivity is NOT overdue (Ch5 grace=72h per YAML)."""
        calc = DecayCalculator()
        user = create_mock_user(chapter=5, hours_since=70)
        assert calc.is_overdue(user) is False

    def test_ch5_user_overdue_at_73h(self):
        """Ch5 user with 73h inactivity IS overdue (past 72h grace)."""
        calc = DecayCalculator()
        user = create_mock_user(chapter=5, hours_since=73)
        assert calc.is_overdue(user) is True

    def test_grace_periods_natural_order(self):
        """Grace periods increase from Ch1 to Ch5 (veterans get more grace)."""
        cfg = get_config()
        assert cfg.get_grace_period(1) < cfg.get_grace_period(2)
        assert cfg.get_grace_period(2) < cfg.get_grace_period(3)
        assert cfg.get_grace_period(3) < cfg.get_grace_period(4)
        assert cfg.get_grace_period(4) < cfg.get_grace_period(5)

    def test_ch1_grace_is_8_hours(self):
        """Ch1 should have 8h grace period (YAML)."""
        assert get_config().get_grace_period(1) == timedelta(hours=8)

    def test_ch5_grace_is_72_hours(self):
        """Ch5 should have 72h grace period (YAML)."""
        assert get_config().get_grace_period(5) == timedelta(hours=72)
