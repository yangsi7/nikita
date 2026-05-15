"""Spec 218-8: v2 agent-driven onboarding wizard package.

Active module: cost_guard.py (FETCH_BUDGET_HARD_USD, FLOW_HARD_CEILING_USD, CostGuard)
used by nikita/agents/onboarding/v2/research_agent.py.

v2 sub-package: nikita.agents.onboarding.v2
"""

from nikita.agents.onboarding.cost_guard import (
    FETCH_BUDGET_HARD_USD,
    FLOW_HARD_CEILING_USD,
    CostGuard,
)

__all__ = [
    "CostGuard",
    "FETCH_BUDGET_HARD_USD",
    "FLOW_HARD_CEILING_USD",
]
