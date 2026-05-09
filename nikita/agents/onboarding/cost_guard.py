"""Cost circuit-breaker for the agentic wizard (Spec 216-B1+B2 / B1.8 + Spec 216-E).

Two layers:

1. Per-turn LLM circuit breaker (B1.8): when
   ``ConverseDeps.cost_budget_remaining_usd`` falls below
   ``COST_CIRCUIT_THRESHOLD_USD`` ($0.05), the M1 generate-follow-up path
   switches to the static fallback registry (``follow_up_registry.yaml``).

2. Cumulative-flow ceilings (216-E): the wizard tracks total cost across
   LLM + fetch_* tools (firecrawl) via ``CostGuard.check_budget``. Spec 218
   PR-218-PREREQ-A removed the WebSearchTool builtin.
   Hard ceilings:
     - ``FETCH_BUDGET_HARD_USD``  ($0.15) — fetch-tool-only cap per flow
     - ``FLOW_HARD_CEILING_USD``   ($0.50) — total cost cap per flow
     - ``FETCH_BUDGET_WARN_USD``   ($0.10) — soft warn for fetch tools

Both layers expose pure predicates; consumers (route handler, fetch tool)
own the action (fall back, abort, log).

Per ``.claude/rules/tuning-constants.md``: every threshold is a named,
documented, regression-guarded constant.
"""

from __future__ import annotations

from decimal import Decimal
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


FETCH_BUDGET_HARD_USD: Final[Decimal] = Decimal("0.15")
"""Fetch-tool-only cumulative budget ceiling, in USD per onboarding flow.

Current value: $0.15 (Spec 216-E, E1.3 lock-in).
Prior values: N/A — introduced here.

Rationale: spec E1.3 caps cumulative fetch_* tool spend at $0.15/flow.
Each firecrawl call is approximately $0.025; 6 calls (~p99) = $0.15.
The hard ceiling abort-fires before issuing a 7th call.

Changing this requires updating
``tests/agents/onboarding/test_cost_guard.py``.
"""


FETCH_BUDGET_WARN_USD: Final[Decimal] = Decimal("0.10")
"""Fetch-tool soft-warn threshold, in USD per onboarding flow.

Current value: $0.10 (Spec 216-E, E1.3).
Rationale: warn at 2/3 of hard ceiling so observability can flag flows
trending hot before the hard abort fires.
"""


FLOW_HARD_CEILING_USD: Final[Decimal] = Decimal("0.50")
"""Total per-flow cost ceiling across LLM + fetch (firecrawl), in USD.

Current value: $0.50 (Spec 216-E, E1.7 + master spec NR-02).
Prior values: N/A — introduced here.

Rationale: master spec NR-02 caps onboarding cost at <$0.50/flow.
Composition (p99): ~$0.30 LLM + $0.15 firecrawl fetch (~$0.05 reserve).
Spec 218 PR-218-PREREQ-A removed the WebSearchTool builtin; reserve
absorbed into LLM/fetch headroom.
Changing this requires updating the regression test.
"""


class CostGuard:
    """Cost circuit breaker — predicate + cumulative budget tracking.

    Stateless. ``check_budget(deps)`` returns whether the LLM path is
    permitted on the current turn (B1.8 layer).

    ``check_fetch_budget(deps, additional_cost)`` returns whether another
    fetch tool call is permitted (216-E layer). The caller is responsible
    for incrementing ``deps.fetch_cost_cumulative`` AFTER a successful
    call and consulting this predicate BEFORE the next call.

    ``check_flow_ceiling(total_cost)`` returns whether the cumulative
    LLM + fetch (firecrawl) total is still under the $0.50 hard ceiling.
    """

    @staticmethod
    def check_budget(deps: "ConverseDeps") -> bool:
        """Return True iff sufficient budget remains for an LLM call.

        Boundary: ``cost_budget_remaining_usd >= COST_CIRCUIT_THRESHOLD_USD``
        (inclusive). At exactly $0.05 remaining, the call is permitted.
        """
        return deps.cost_budget_remaining_usd >= COST_CIRCUIT_THRESHOLD_USD

    @staticmethod
    def check_fetch_budget(
        deps: "ConverseDeps", additional_cost: Decimal | float = Decimal("0.025")
    ) -> bool:
        """Return True iff another fetch tool call would stay under the
        $0.15 fetch-only ceiling.

        ``additional_cost`` is the projected cost of the next call (default
        $0.025, the firecrawl per-call estimate). The predicate returns
        ``True`` iff
        ``fetch_cost_cumulative + additional_cost <= FETCH_BUDGET_HARD_USD``.
        """
        current = _as_decimal(getattr(deps, "fetch_cost_cumulative", 0))
        projected = current + _as_decimal(additional_cost)
        return projected <= FETCH_BUDGET_HARD_USD

    @staticmethod
    def is_fetch_warn(deps: "ConverseDeps") -> bool:
        """Return True iff fetch cumulative cost has crossed the soft warn
        threshold ($0.10). Used for observability only; does NOT block."""
        current = _as_decimal(getattr(deps, "fetch_cost_cumulative", 0))
        return current >= FETCH_BUDGET_WARN_USD

    @staticmethod
    def check_flow_ceiling(total_cost: Decimal | float) -> bool:
        """Return True iff total per-flow cost is under the $0.50 ceiling.

        Caller passes the cumulative LLM + fetch (firecrawl) USD spend
        for this flow.
        """
        return _as_decimal(total_cost) <= FLOW_HARD_CEILING_USD


def _as_decimal(value: Decimal | float | int | str) -> Decimal:
    """Best-effort conversion to Decimal without losing precision via float.

    Accepts already-Decimal, int, str, or float (latter coerced through str
    to avoid binary-float artifacts).
    """
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(str(value))
    return Decimal(str(value))


__all__ = [
    "COST_CIRCUIT_THRESHOLD_USD",
    "FETCH_BUDGET_HARD_USD",
    "FETCH_BUDGET_WARN_USD",
    "FLOW_HARD_CEILING_USD",
    "CostGuard",
]
