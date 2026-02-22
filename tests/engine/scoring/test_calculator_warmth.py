"""Tests for Spec 058 warmth bonus in ScoreCalculator."""

from __future__ import annotations

from decimal import Decimal

from nikita.engine.scoring.calculator import ScoreCalculator
from nikita.engine.scoring.models import MetricDeltas


class TestApplyWarmthBonus:
    """AC-7.1, AC-7.2, AC-7.3, AC-7.4: Warmth bonus with diminishing returns."""

    def setup_method(self):
        self.calc = ScoreCalculator()
        self.base_deltas = MetricDeltas(
            intimacy=Decimal("2"), passion=Decimal("1"),
            trust=Decimal("3"), secureness=Decimal("1"),
        )

    def test_first_exchange_plus_2_trust(self):
        """AC-7.1: First V-exchange -> +2 trust bonus."""
        result = self.calc.apply_warmth_bonus(self.base_deltas, v_exchange_count=0)
        assert result.trust == Decimal("5")  # 3 + 2

    def test_second_exchange_plus_1_trust(self):
        """AC-7.2: Second V-exchange -> +1 trust bonus."""
        result = self.calc.apply_warmth_bonus(self.base_deltas, v_exchange_count=1)
        assert result.trust == Decimal("4")  # 3 + 1

    def test_third_exchange_plus_0(self):
        """AC-7.3: Third+ V-exchange -> +0 (diminishing returns)."""
        result = self.calc.apply_warmth_bonus(self.base_deltas, v_exchange_count=2)
        assert result.trust == Decimal("3")  # unchanged

    def test_fourth_exchange_plus_0(self):
        result = self.calc.apply_warmth_bonus(self.base_deltas, v_exchange_count=5)
        assert result.trust == Decimal("3")

    def test_trust_capped_at_10(self):
        """AC-7.4: Trust capped at 10."""
        high_trust = MetricDeltas(
            intimacy=Decimal("0"), passion=Decimal("0"),
            trust=Decimal("9"), secureness=Decimal("0"),
        )
        result = self.calc.apply_warmth_bonus(high_trust, v_exchange_count=0)
        assert result.trust == Decimal("10")  # 9 + 2 capped at 10

    def test_no_bonus_preserves_other_metrics(self):
        result = self.calc.apply_warmth_bonus(self.base_deltas, v_exchange_count=0)
        assert result.intimacy == self.base_deltas.intimacy
        assert result.passion == self.base_deltas.passion
        assert result.secureness == self.base_deltas.secureness
