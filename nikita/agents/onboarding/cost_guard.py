"""Cost circuit-breaker for the agentic wizard (Spec 216-B1+B2 / B1.8).

When ``ConverseDeps.cost_budget_remaining_usd`` falls below
``COST_CIRCUIT_THRESHOLD_USD`` ($0.05), the wizard switches the M1
generate-follow-up path to the static fallback registry
(``follow_up_registry.yaml``).

This module exposes ONLY the predicate. Actual budget tracking is wired
in 216-D-code; for 216-B1+B2 the value is set to a 1.00 default in
``ConverseDeps`` and the predicate consequently returns True.

Per ``.claude/rules/tuning-constants.md``: the threshold is a named,
documented, regression-guarded constant.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from nikita.agents.onboarding.conversation_agent import ConverseDeps


COST_CIRCUIT_THRESHOLD_USD: Final[float] = 0.05
"""Minimum LLM-budget headroom before the M1 dynamic-follow-up path is
disabled in favor of the static fallback registry.

Current value: $0.05 (Spec 216-B1+B2, B1.8 lock-in).
Prior values: N/A — introduced here.

Rationale: $0.05 is approximately the cost of one Anthropic Claude Sonnet
call at p99 input/output sizes for the wizard. When less than $0.05 is
left in the per-user daily budget, attempting another live LLM call is
likely to crash the budget — fall back to the static registry.

Changing this requires updating the regression test in
test_cost_circuit_integration.py.
"""


class CostGuard:
    """Predicate-only cost circuit breaker.

    Stateless. ``check_budget(deps)`` returns whether the LLM path is
    permitted on the current turn. Higher-level orchestration layers
    (216-B3 endpoint, 216-D-code wiring) consume the predicate to choose
    between the live M1 generate-follow-up path and the static fallback.
    """

    @staticmethod
    def check_budget(deps: "ConverseDeps") -> bool:
        """Return True iff sufficient budget remains for an LLM call.

        Boundary: ``cost_budget_remaining_usd >= COST_CIRCUIT_THRESHOLD_USD``
        (inclusive). At exactly $0.05 remaining, the call is permitted.
        """
        return deps.cost_budget_remaining_usd >= COST_CIRCUIT_THRESHOLD_USD


__all__ = ["COST_CIRCUIT_THRESHOLD_USD", "CostGuard"]
