"""Spec 218-8: v2 agent-driven onboarding wizard package.

v1 modules (conversation_agent, state, question_registry, wiring, validators,
archetypes, cohort_chips, big5_judge, bare_token_fallback, conversation_prompts,
message_history, agent_runner, handoff_greeting, sidecar_persistence,
state_reconstruction, answer_contracts, converse_contracts, agent_emission_state,
conversation_persistence, follow_up_registry.yaml) were deleted atomically in
PR-218-8 once all 11 Phase-1 slots were covered by the v2 surface.

Remaining: cost_guard.py (FETCH_BUDGET_HARD_USD, FLOW_HARD_CEILING_USD, CostGuard)
is used by nikita/agents/onboarding/v2/research_agent.py.

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
