"""B1.8 — Cost circuit-breaker tests.

CostGuard.check_budget(deps) returns False when cost_budget_remaining_usd
falls below the COST_CIRCUIT_THRESHOLD_USD ($0.05). Below threshold →
the wizard falls back to the static follow_up_registry (B1.9).
"""

from __future__ import annotations

from uuid import uuid4

import pytest


def _imports():
    from nikita.agents.onboarding.conversation_agent import ConverseDeps  # noqa: PLC0415
    from nikita.agents.onboarding.cost_guard import (  # noqa: PLC0415
        COST_CIRCUIT_THRESHOLD_USD,
        CostGuard,
    )
    from nikita.agents.onboarding.state import WizardSlots  # noqa: PLC0415
    return ConverseDeps, COST_CIRCUIT_THRESHOLD_USD, CostGuard, WizardSlots


def _make_deps(ConverseDeps, slots, **overrides):
    defaults = {
        "state": slots,
        "state_summary": "",
        "last_slot_kind": None,
        "last_value": None,
        "next_slot_kind": None,
        "next_slot_hint": None,
        "cost_budget_remaining_usd": 1.0,
        "fetch_invocations_this_turn": 0,
        "fetch_cost_cumulative": 0.0,
        "cohort_cache": {},
        "big5_confidence": {},
        "traceparent": "",
        "user_id": uuid4(),
        "conversation_id": uuid4(),
    }
    defaults.update(overrides)
    return ConverseDeps(**defaults)


class TestCostGuardThreshold:
    def test_threshold_constant_is_5_cents(self):
        """COST_CIRCUIT_THRESHOLD_USD must equal 0.05 (B1.8)."""
        _, threshold, _, _ = _imports()
        assert threshold == 0.05

    def test_check_budget_returns_true_above_threshold(self):
        """Budget remaining > threshold → check_budget returns True."""
        ConverseDeps, _, CostGuard, WizardSlots = _imports()
        deps = _make_deps(ConverseDeps, WizardSlots(), cost_budget_remaining_usd=1.00)
        assert CostGuard.check_budget(deps) is True

    def test_check_budget_returns_false_below_threshold(self):
        """Budget remaining < threshold → check_budget returns False."""
        ConverseDeps, _, CostGuard, WizardSlots = _imports()
        deps = _make_deps(ConverseDeps, WizardSlots(), cost_budget_remaining_usd=0.01)
        assert CostGuard.check_budget(deps) is False

    def test_check_budget_returns_true_at_exact_threshold(self):
        """Budget remaining == threshold → check_budget returns True (>= boundary)."""
        ConverseDeps, threshold, CostGuard, WizardSlots = _imports()
        deps = _make_deps(
            ConverseDeps, WizardSlots(), cost_budget_remaining_usd=threshold
        )
        assert CostGuard.check_budget(deps) is True
