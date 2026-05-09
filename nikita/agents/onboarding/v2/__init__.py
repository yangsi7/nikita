"""Spec 218 onboarding wizard v2 package.

Hybrid agent-driven dynamic-UI flow. Replaces Spec 217 emission-union wizard.

Modules:
- ``state``: ``WizardSlotsV2`` cumulative accumulator + ``FinalForm`` Pydantic
  completion gate + ``Phase`` enum + ``state_hash`` SHA-256 digest.
- ``router``: deterministic ``pick_next_target(state)`` -> next ``SlotKind``
  or ``DONE``; ``REQUIRED_ORDER`` constant; ``dag_invalidate(state, edited)``
  helper.
- ``envelope``: 8-shape ``AskUnion`` discriminated-union envelope per FR-005.

PR-218-1 ships these foundations only. Decorator agent (PR-218-2),
route handler bulldoze + wire-up (PR-218-3), FE components (PR-218-4),
Phase 2 open-bounce (PR-218-5), phone-demo wow (PR-218-6), and
supersession (PR-218-7) follow per ``specs/218-*/plan.md`` §23.10.
"""
