"""Sidecar Pydantic model for transient agent emission state (Spec 217-3A AC-8.1).

``AgentEmissionState`` carries state that is NOT a wizard slot but lives
across turns — chiefly ``pending_followup`` which the agent emits when
it wants to insert a clarifying question before the deterministic flow
advances. This sidecar is persisted at
``users.onboarding_profile.pending_followup`` JSONB (sibling of ``slots``)
and cleared via the JSONB ``#-`` key-removal operator (NOT via a JSON
null literal — see Spec 217-3A AC-8.2 forbidden-shape rule).

Hard Rule §1 separation:
  ``WizardSlots`` (state.py) holds cumulative slot data — gate input.
  ``AgentEmissionState`` (this module) holds transient agent emission
  state — NEVER a slot, NEVER feeds ``FinalForm.model_validate``.

Persistence contract:
  - Set:    ``UPDATE users SET onboarding_profile = jsonb_set(
              onboarding_profile, '{pending_followup}', :followup_jsonb
            ) WHERE id = :uid``
  - Clear:  ``UPDATE users SET onboarding_profile = onboarding_profile #-
              '{pending_followup}' WHERE id = :uid``
  - Read:   ``SELECT onboarding_profile -> 'pending_followup' FROM users``

  Setting the value to a JSON null literal is FORBIDDEN — it leaves the
  key present and forces every downstream reader to disambiguate
  "absent" vs "null". The cleanup test (217-3A.2 scope) asserts
  ``onboarding_profile ? 'pending_followup'`` returns ``false`` after
  resolution.

Serialization invariant:
  ``model_dump(exclude_none=True)`` MUST omit ``pending_followup`` when
  ``None`` so the JSONB writer can round-trip cleanly with key absence.
  Verified by ``test_emission_state_sidecar.py``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from nikita.agents.onboarding.converse_contracts import FollowUpQuestion


class AgentEmissionState(BaseModel):
    """Transient agent emission state — sidecar to ``WizardSlots``.

    Currently carries only ``pending_followup``. New transient fields
    (e.g., last LLM cost record, last reaction streak) can be added here
    without touching ``WizardSlots`` or ``FinalForm`` — keeps Hard Rule §1
    cumulative-state purity intact.
    """

    model_config = ConfigDict(extra="forbid")

    pending_followup: FollowUpQuestion | None = None
    """Clarifying question the agent inserted on the prior turn.

    Set when the agent emits ``FollowUpQuestion``; cleared (key removed
    from JSONB) when the user's next answer resolves it OR when the
    deterministic flow advances past the followup's target slot.
    """


__all__ = ["AgentEmissionState"]
