"""Spec 216-E E1.3 / E1.7 — CostGuard cumulative + ceiling tests.

- Cumulative ``fetch_cost_cumulative`` increments correctly via
  ``check_fetch_budget``.
- Hard ceiling at $0.15 fetch-only refuses further calls.
- Soft warn at $0.10 returns True (does not block).
- Flow ceiling at $0.50 enforces NR-02 master cap.
"""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from nikita.agents.onboarding.conversation_agent import ConverseDeps
from nikita.agents.onboarding.cost_guard import (
    COST_CIRCUIT_THRESHOLD_USD,
    FETCH_BUDGET_HARD_USD,
    FETCH_BUDGET_WARN_USD,
    FLOW_HARD_CEILING_USD,
    CostGuard,
)
from nikita.agents.onboarding.state import WizardSlots


def _make_deps(**overrides) -> ConverseDeps:
    defaults = dict(
        user_id=uuid4(),
        conversation_id=uuid4(),
        state=WizardSlots(),
        state_summary="",
        last_slot_kind=None,
        last_value=None,
        next_slot_kind=None,
        next_slot_hint=None,
        cost_budget_remaining_usd=1.0,
        fetch_invocations_this_turn=0,
        fetch_cost_cumulative=0.0,
        cohort_cache={},
        big5_confidence={},
        traceparent="",
    )
    defaults.update(overrides)
    return ConverseDeps(**defaults)


class TestConstants:
    def test_threshold_is_5_cents(self):
        assert COST_CIRCUIT_THRESHOLD_USD == 0.05

    def test_fetch_hard_ceiling_is_15_cents(self):
        assert FETCH_BUDGET_HARD_USD == Decimal("0.15")

    def test_fetch_warn_is_10_cents(self):
        assert FETCH_BUDGET_WARN_USD == Decimal("0.10")

    def test_flow_ceiling_is_50_cents(self):
        assert FLOW_HARD_CEILING_USD == Decimal("0.50")


class TestFetchBudgetGuard:
    def test_first_call_permitted(self):
        deps = _make_deps(fetch_cost_cumulative=0.0)
        assert CostGuard.check_fetch_budget(deps) is True

    def test_under_warn_permitted(self):
        deps = _make_deps(fetch_cost_cumulative=0.05)
        assert CostGuard.check_fetch_budget(deps) is True
        assert CostGuard.is_fetch_warn(deps) is False

    def test_at_warn_threshold_warns_but_permits(self):
        deps = _make_deps(fetch_cost_cumulative=0.10)
        assert CostGuard.check_fetch_budget(deps) is True
        assert CostGuard.is_fetch_warn(deps) is True

    def test_at_hard_ceiling_permits_exact_match(self):
        # 0.125 + 0.025 = 0.150 → ==FETCH_BUDGET_HARD_USD → permitted (inclusive).
        deps = _make_deps(fetch_cost_cumulative=0.125)
        assert CostGuard.check_fetch_budget(deps) is True

    def test_over_hard_ceiling_rejects(self):
        deps = _make_deps(fetch_cost_cumulative=0.13)
        # 0.13 + 0.025 = 0.155 > 0.15 → rejected.
        assert CostGuard.check_fetch_budget(deps) is False


class TestFlowCeiling:
    def test_under_50_cents_permitted(self):
        assert CostGuard.check_flow_ceiling(0.49) is True

    def test_at_50_cents_permitted_exact(self):
        assert CostGuard.check_flow_ceiling(Decimal("0.50")) is True

    def test_over_50_cents_rejected(self):
        assert CostGuard.check_flow_ceiling(Decimal("0.51")) is False

    def test_handles_float_input(self):
        # E1.7 — cumulative cost arrives mixed-type (float from LLM
        # provider, Decimal from fetch tools). The guard MUST coerce both.
        assert CostGuard.check_flow_ceiling(0.49) is True
        assert CostGuard.check_flow_ceiling(0.51) is False


class TestLegacyLLMBudgetGuard:
    """B1.8 backward-compat — pre-existing LLM budget circuit still works."""

    def test_above_threshold_permits(self):
        deps = _make_deps(cost_budget_remaining_usd=0.50)
        assert CostGuard.check_budget(deps) is True

    def test_at_threshold_permits_inclusive(self):
        deps = _make_deps(cost_budget_remaining_usd=0.05)
        assert CostGuard.check_budget(deps) is True

    def test_below_threshold_rejects(self):
        deps = _make_deps(cost_budget_remaining_usd=0.04)
        assert CostGuard.check_budget(deps) is False
