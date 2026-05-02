"""Spec 216-B1+B2 conversational onboarding agent package.

The 13-slot agentic wizard. Houses:

- ``state.py`` — WizardSlots / FinalForm / SlotDelta (cumulative state +
  Pydantic completion gate; Hard Rules §1, §2, §4).
- ``question_registry.py`` — SlotKind StrEnum (B1.18) + ORDERED_QUESTIONS
  priority registry.
- ``conversation_agent.py`` — Pydantic AI agent with discriminated-union
  output_type [TurnOutput, TurnFailure] (B1.3); @output_validator
  + ModelRetry for mirror-echo / length (B1.5); CostGuard (B1.8).
- ``conversation_prompts.py`` — M1-M4 meta-prompt templates + cluster
  taxonomies (B1.6/B1.7) + inject_per_turn_context callable (Hard Rule §6).
- ``cost_guard.py`` — $0.05 LLM-budget circuit breaker (B1.8).
- ``follow_up_registry.yaml`` — paired static_fallback_question per
  (slot, cluster) for M1 fallback path (B1.9).
- ``state_reconstruction.py`` — JSONB → WizardSlots cumulative reload.
- ``conversation_persistence.py`` — JSONB write helpers (unchanged).
- ``message_history.py`` — wire-Turn → Pydantic AI ModelMessage.
- ``handoff_greeting.py`` — first-turn TG↔portal greeting templates.

Architecture reference: ``specs/216-onboarding-redesign-cinematic/`` and
the per-PR subspecs.
"""

from nikita.agents.onboarding.cost_guard import CostGuard
from nikita.agents.onboarding.question_registry import (
    ORDERED_QUESTIONS,
    SlotKind,
    next_question,
)
from nikita.agents.onboarding.state import (
    FinalForm,
    SlotDelta,
    TOTAL_SLOTS,
    WizardSlots,
    WizardState,
)

__all__ = [
    "CostGuard",
    "FinalForm",
    "ORDERED_QUESTIONS",
    "SlotDelta",
    "SlotKind",
    "TOTAL_SLOTS",
    "WizardSlots",
    "WizardState",
    "next_question",
]
