"""Tests for Spec 058 warmth bonus — vulnerability exchange + trust bonus.

Tests apply_warmth_bonus() in ScoreCalculator: diminishing returns
(+2, +1, +0), trust cap at 10, and interaction with scoring service.

AC refs: AC-6.1, AC-6.2, AC-6.3, AC-6.4, AC-7.1, AC-7.2, AC-7.3, AC-7.4, AC-7.5
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from nikita.engine.scoring.calculator import ScoreCalculator
from nikita.engine.scoring.models import MetricDeltas


# ============================================================================
# ScoreCalculator.apply_warmth_bonus
# ============================================================================


class TestApplyWarmthBonus:
    """apply_warmth_bonus: diminishing returns on trust."""

    @pytest.fixture
    def calc(self):
        return ScoreCalculator()

    @pytest.fixture
    def base_deltas(self):
        return MetricDeltas(
            intimacy=Decimal("1"),
            passion=Decimal("1"),
            trust=Decimal("3"),
            secureness=Decimal("1"),
        )

    def test_first_exchange_adds_2_trust(self, calc, base_deltas):
        """v_exchange_count=0 -> +2 trust."""
        result = calc.apply_warmth_bonus(base_deltas, v_exchange_count=0)
        assert result.trust == Decimal("5")  # 3 + 2

    def test_second_exchange_adds_1_trust(self, calc, base_deltas):
        """v_exchange_count=1 -> +1 trust."""
        result = calc.apply_warmth_bonus(base_deltas, v_exchange_count=1)
        assert result.trust == Decimal("4")  # 3 + 1

    def test_third_exchange_adds_0_trust(self, calc, base_deltas):
        """v_exchange_count=2 -> +0 trust (diminishing returns)."""
        result = calc.apply_warmth_bonus(base_deltas, v_exchange_count=2)
        assert result.trust == Decimal("3")  # unchanged

    def test_fourth_exchange_adds_0_trust(self, calc, base_deltas):
        """v_exchange_count=3 -> +0 trust."""
        result = calc.apply_warmth_bonus(base_deltas, v_exchange_count=3)
        assert result.trust == Decimal("3")  # unchanged

    def test_trust_capped_at_10(self, calc):
        """Trust delta cannot exceed 10."""
        high_trust = MetricDeltas(
            intimacy=Decimal("0"),
            passion=Decimal("0"),
            trust=Decimal("9"),
            secureness=Decimal("0"),
        )
        result = calc.apply_warmth_bonus(high_trust, v_exchange_count=0)
        assert result.trust == Decimal("10")  # 9 + 2 = 11, capped to 10

    def test_trust_at_10_stays_at_10(self, calc):
        """Trust at 10 stays at 10 with bonus."""
        max_trust = MetricDeltas(
            intimacy=Decimal("0"),
            passion=Decimal("0"),
            trust=Decimal("10"),
            secureness=Decimal("0"),
        )
        result = calc.apply_warmth_bonus(max_trust, v_exchange_count=0)
        assert result.trust == Decimal("10")

    def test_other_deltas_unchanged(self, calc, base_deltas):
        """Only trust changes, other deltas preserved."""
        result = calc.apply_warmth_bonus(base_deltas, v_exchange_count=0)
        assert result.intimacy == Decimal("1")
        assert result.passion == Decimal("1")
        assert result.secureness == Decimal("1")

    def test_returns_metric_deltas_type(self, calc, base_deltas):
        result = calc.apply_warmth_bonus(base_deltas, v_exchange_count=0)
        assert isinstance(result, MetricDeltas)

    def test_no_bonus_returns_same_object(self, calc, base_deltas):
        """When no bonus applied (count>=2), returns same deltas."""
        result = calc.apply_warmth_bonus(base_deltas, v_exchange_count=5)
        assert result.trust == base_deltas.trust


# ============================================================================
# Vulnerability exchange prompt in analyzer (AC-6.1, AC-6.2)
# ============================================================================


class TestVulnerabilityExchangePrompt:
    """Analyzer prompt includes vulnerability_exchange detection."""

    def test_analyzer_prompt_contains_vulnerability_exchange(self):
        from nikita.engine.scoring.analyzer import ANALYSIS_SYSTEM_PROMPT

        assert "vulnerability_exchange" in ANALYSIS_SYSTEM_PROMPT

    def test_analyzer_prompt_mentions_both_conditions(self):
        from nikita.engine.scoring.analyzer import ANALYSIS_SYSTEM_PROMPT

        assert "nikita" in ANALYSIS_SYSTEM_PROMPT.lower()
        assert "player" in ANALYSIS_SYSTEM_PROMPT.lower() or "user" in ANALYSIS_SYSTEM_PROMPT.lower()
        assert "empathy" in ANALYSIS_SYSTEM_PROMPT.lower()
