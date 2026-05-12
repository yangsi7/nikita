---
title: "Spec 218 Slice 8 — v1 Bulldoze + wizard_v2_enabled Flag Flip"
lifecycle: living
spec: 218
slice: 8
pr: PR-218-8
date: 2026-05-13
---

# Slice 218-8: Atomic v1 Bulldoze + Flag Flip

## Summary

Final slice of Spec 218. Atomically removes all v1 onboarding wizard code, flips
`wizard_v2_enabled` from `False` to `True`, supersedes Spec 217, and syncs ROADMAP.md.

## Acceptance Criteria

- AC1: All v1 backend modules deleted (conversation_agent.py, converse_contracts.py,
  answer_contracts.py, agent_emission_state.py, sidecar_persistence.py,
  conversation_prompts.py, conversation_persistence.py, state.py,
  state_reconstruction.py, validators.py, wiring.py, message_history.py,
  agent_runner.py, question_registry.py, archetypes.py, big5_judge.py,
  bare_token_fallback.py, cohort_chips.py, follow_up_registry.yaml).
- AC2: v1 route file deleted: `nikita/api/routes/portal_onboarding.py`.
- AC3: v1 schema file deleted: `nikita/api/schemas/onboarding.py`.
- AC4: All v1 test files deleted (tests/agents/onboarding/*.py excluding v2/,
  tests/onboarding/*, tests/services/test_portal_onboarding*.py,
  tests/api/routes/test_onboarding*.py excluding portal_onboarding_v2).
- AC5: All v1 portal files deleted (onboarding-wizard.tsx, schemas.ts,
  components/ dir, hooks/ dir, steps/ dir, types/ dir, __tests__/ dir,
  portal/src/__tests__/app/onboarding/*, portal/e2e/onboarding*.spec.ts).
- AC6: `HandlerHandoffAsk` removed from v2/envelope.py, decorator_agent.py,
  portal_onboarding_v2.py, envelope.ts, DynamicQuestion.tsx.
- AC7: `wizard_v2_enabled` default flipped to `True` in nikita/config/settings.py.
- AC8: v1 router registration removed from nikita/api/main.py.
- AC9: Spec 217 spec.md lifecycle changed to `superseded`, banner added.
- AC10: ROADMAP.md updated — Spec 218 status to COMPLETE, domain subtotal updated.
- AC11: `uv run pytest -q` passes (all remaining tests green).
- AC12: `(cd portal && npm run test -- --run)` passes.
- AC13: `(cd portal && npm run lint && npm run build)` passes.
- AC14: No import of deleted v1 modules survives in any non-deleted file.

## Files Modified (non-deleted)

- `nikita/config/settings.py` — `wizard_v2_enabled` default `False` → `True`
- `nikita/api/main.py` — v1 router block removed
- `nikita/agents/onboarding/__init__.py` — v1 imports removed; only cost_guard exports
- `nikita/agents/onboarding/v2/envelope.py` — `HandlerHandoffAsk` removed
- `nikita/agents/onboarding/v2/decorator_agent.py` — `HandlerHandoffAsk` fallback replaced with `ValueError`
- `nikita/agents/onboarding/cost_guard.py` — `ConverseDeps` TYPE_CHECKING import removed; `check_fetch_budget` retained with `deps: object`
- `nikita/agents/onboarding/tools/firecrawl_tools.py` — `ConverseDeps` TYPE_CHECKING import removed
- `nikita/agents/onboarding/handoff_greeting.py` — import fixed: `conversation_prompts.NIKITA_PERSONA` → `nikita.agents.text.persona.NIKITA_PERSONA`
- `nikita/api/routes/portal_onboarding_v2.py` — `HandlerHandoffAsk` import removed; `get_async_session` import redirected to `nikita.db.database`
- `portal/src/app/onboarding/v2/types/envelope.ts` — `HandlerHandoffAsk` removed
- `portal/src/app/onboarding/v2/DynamicQuestion.tsx` — v1 handler branch removed
- `specs/217-onboarding-wizard-deterministic-redesign/spec.md` — lifecycle superseded, banner added
- `ROADMAP.md` — Spec 218 → COMPLETE, domain subtotal updated

## Key Design Decisions

- `handoff_greeting.py` retained (not deleted): `telegram/commands.py` imports it via
  local import in `_dispatch_handoff_greeting`. Import path fixed after `conversation_prompts.py` deletion.
- `firecrawl_tools.py` retained: v2 `research_agent.py` depends on it. Its TYPE_CHECKING
  import of `ConverseDeps` removed.
- `cost_guard.check_fetch_budget` retained with `deps: object` duck type: `firecrawl_tools.py`
  calls it at runtime (line 252). Was previously typed as `"ConverseDeps"` string annotation.
- `portal_onboarding.py` deleted entirely: all non-v1 routes had been superseded/moved.
  v2 route file (`portal_onboarding_v2.py`) had a bad import of `get_async_session` from
  the deleted file; redirected to `nikita.db.database`.

## Atomicity

Single commit on branch `feat/218-8-bulldoze-v1-flag-flip`. All changes staged together.
No migration ceremony (solo-dev, zero retained prod users).
