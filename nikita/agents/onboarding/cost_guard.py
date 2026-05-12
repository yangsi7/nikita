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
from typing import Final


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

    PR-218-8: check_budget / is_fetch_warn removed (only referenced ConverseDeps,
    deleted with v1 agent). check_fetch_budget retained: used by
    ``tools/firecrawl_tools.py`` which is shared with v2 research_agent.
    """

    @staticmethod
    def check_fetch_budget(
        deps: object, additional_cost: Decimal | float = Decimal("0.025")
    ) -> bool:
        """Return True iff another fetch tool call would stay under the
        $0.15 fetch-only ceiling.

        ``additional_cost`` is the projected cost of the next call (default
        $0.025, the firecrawl per-call estimate). The predicate returns
        ``True`` iff
        ``fetch_cost_cumulative + additional_cost <= FETCH_BUDGET_HARD_USD``.

        PR-218-8: parameter typed as ``object`` (duck-typed via getattr) since
        ConverseDeps was removed with v1. V2ResearchDeps carries the same
        ``fetch_cost_cumulative`` attribute.
        """
        current = _as_decimal(getattr(deps, "fetch_cost_cumulative", 0))
        projected = current + _as_decimal(additional_cost)
        return projected <= FETCH_BUDGET_HARD_USD

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
    "CostGuard",
    "FETCH_BUDGET_HARD_USD",
    "FLOW_HARD_CEILING_USD",
]
