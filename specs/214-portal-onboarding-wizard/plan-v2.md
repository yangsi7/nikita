# Spec 214 — Plan v2 (FR-11d Slot-Filling Variant)

**Source:** `specs/214-portal-onboarding-wizard/spec.md` (FR-11d, AC-11d.1-10) at master commit `6119b26`
**Authority:** Plan v16 (`/Users/yangsim/.claude/plans/delightful-orbiting-ladybug.md`) + ADR-009 + `.claude/rules/agentic-design-patterns.md`
**Supersedes:** `plan.md` for the chat-first variant ONLY. Original `plan.md` (FR-1 step-wizard) remains valid behind `NEXT_PUBLIC_USE_LEGACY_FORM_WIZARD=true`.
**Created:** 2026-04-23

## 1. Scope

Implement the chat-first conversational onboarding redesigned around proper agentic patterns (cumulative state + Pydantic completion gate + dynamic instructions / consolidated tool + regex fallback + message_history primitive + additive wire-format extension for terminal handoff).

**Out of scope** (per spec §11): legacy step-wizard removal, multi-locale, voice-onboarding rewrite, pydantic-graph FSM adoption, broader Spec 214 audit.

## 2. Target Architecture

```
POST /api/v1/onboarding/converse  (handler in portal_onboarding.py)

  1. Load cumulative state
     state = WizardState.from_user(user, hydrator=build_state_from_conversation)
       └─ slots reconstructed from profile["conversation"][*].extracted ∪ profile["elided_extracted"]
          (option A; option B opt-in if AC-11d.9 perf bench fails)

  2. Run agent with dynamic instructions
     result = await agent.run(
       user_input,
       message_history=hydrate_message_history(profile["conversation"]),
       deps=ConverseDeps(state=state),
     )
       └─ Agent has:
          * output_type=[SlotDelta, str]   OR   retained 6+1 tools + Agent(instructions=callable)
          * @output_validator deserializes SlotDelta → state.merge()
          * raise ModelRetry on ValidationError → self-correct

  3. Deterministic post-processing (defense in depth)
     fallback = regex_phone_fallback(state, user_input)
     if fallback: state = state.merge(fallback)

  4. Compute completion via Pydantic
     try:   FinalForm.model_validate(state.slots_dict)
            complete = True
     except ValidationError:
            complete = False

  5. Mint link code on terminal turn (idempotent — see GET path)
     if complete and not previously_minted_active:
         link_code, link_expires_at = await TelegramLinkRepository.create_code(user.id)

  6. Persist + return
     await append_conversation_turn(user.id, ...)
     return ConverseResponse(
       progress_pct=state.slots.progress_pct,           # cumulative @computed_field
       conversation_complete=complete,                  # Pydantic gate
       extracted_fields=state.last_delta_dict,
       link_code=link_code,                             # NEW, terminal-turn only
       link_expires_at=link_expires_at,                 # NEW, terminal-turn only
       ...existing fields per converse_contracts.py:55
     )

GET /api/v1/onboarding/conversation  (handler in portal_onboarding.py:702)
  reads users.onboarding_profile + active telegram_link_codes row →
  returns ConversationProfileResponse(
    conversation, progress_pct, elided_extracted,
    link_code, link_expires_at, link_code_expired   # all NEW
  )
  MUST NEVER call create_code (grep gate per AC-11d.8)
```

## 3. File-by-File Refactor Map

### 3.1 New files (5)

| Path | Purpose | LOC est. |
|---|---|---|
| `nikita/agents/onboarding/state.py` | `WizardSlots`, `FinalForm`, `SlotDelta` Pydantic models + `WizardState` container; `TOTAL_SLOTS: Final[int] = 6` | ~120 |
| `nikita/agents/onboarding/state_reconstruction.py` | `build_state_from_conversation()` reducer (elided FIRST then live overrides per AC-11d.10); `RECONSTRUCTION_BUDGET_MS: Final[int] = 10` | ~60 |
| `nikita/agents/onboarding/regex_fallback.py` | `regex_phone_fallback()` for AC-11d.4; reuses `phonenumbers` parser via `PhoneExtraction._phone_format` | ~40 |
| `tests/agents/onboarding/test_wizard_state.py` | T1 RED-then-GREEN tests for state models + FinalForm + completion triplet | ~150 |
| `tests/agents/onboarding/test_state_reconstruction.py` | T9 RED-then-GREEN tests for AC-11d.1, AC-11d.10, repeated-slot-uses-live | ~120 |
| `tests/agents/onboarding/test_state_reconstruction_perf.py` | T10 RED-then-GREEN micro-bench for AC-11d.9 (100-turn fixture, p95 < 10 ms) | ~40 |
| `tests/agents/onboarding/test_regex_fallback.py` | T5 RED-then-GREEN tests for phone regex (E.164 happy path + reject malformed) | ~80 |
| `tests/agents/onboarding/test_dynamic_instructions.py` | T7 RED-then-GREEN tests for AC-11d.5 (call count >= turn count, missing non-empty, slot name in prompt) | ~100 |

### 3.2 Refactored files (4)

| Path | Change | LOC est. |
|---|---|---|
| `nikita/agents/onboarding/conversation_agent.py` | Either consolidate 6+1 tools → 1 `output_type=[SlotDelta, str]` agent, OR retain 6+1 tools + add `Agent(instructions=callable)` rendering `state.missing` per turn. ADD `@output_validator` with `raise ModelRetry`. | -180/+120 |
| `nikita/agents/onboarding/conversation_prompts.py` | Strip hardcoded slot-routing rules from `_WIZARD_FRAMING` (PR #395 patchwork). Provide `render_dynamic_instructions(ctx)` for Agent. | -60/+40 |
| `nikita/api/routes/portal_onboarding.py` | DELETE `_compute_progress` helper (AC-11d.3 grep gate). Replace `conversation_complete = ...` snapshot logic with cumulative state load → agent run → regex fallback → FinalForm gate. ADD link_code minting on terminal turn. EXTEND `ConversationProfileResponse` model with 3 new fields + `extra="forbid"` (AC-11d.8 grep gate). MINT code only inside POST /converse handler. | -80/+150 |
| `nikita/agents/onboarding/converse_contracts.py` | Add `link_code: str \| None = None` + `link_expires_at: datetime \| None = None` to `ConverseResponse`. Preserve `extra="forbid"` invariant. | +6 |
| `portal/src/app/onboarding/types/converse.ts` | Mirror BE additive fields. Remove the post-completion `api.linkTelegram()` workaround call. | +4/-30 |
| `portal/src/app/onboarding/onboarding-wizard.tsx` | Hydration block: branch on `link_code_expired === true` → re-call /converse with same conversation_history to re-mint. Read `link_code` from terminal /converse response (no separate POST). 429 fallback: preserve `state.isComplete` instead of clobbering. | +30/-20 |

### 3.3 Test additions (per `.claude/rules/testing.md` Agentic-Flow Test Requirements)

| Path | Test class | Driver AC |
|---|---|---|
| `tests/api/routes/test_converse_endpoint.py` | `TestConverseCumulativeCompletion` (empty/partial/full triplet) | AC-11d.3 |
| `tests/api/routes/test_converse_endpoint.py` | `TestConverseMonotonicProgress` (turn-by-turn progress never regresses) | AC-11d.2 |
| `tests/api/routes/test_converse_endpoint.py` | `test_converse_terminal_turn_includes_link_code` + `test_converse_non_terminal_turn_omits_link_code` | AC-11d.7 |
| `tests/api/routes/test_converse_endpoint.py` | `test_get_conversation_returns_link_after_completion` + `test_get_conversation_signals_link_expired_after_ttl` + `test_get_conversation_never_mints_code` | AC-11d.8 |
| `tests/agents/onboarding/test_conversation_agent.py` | `TestConsolidatedAgent` (mixed output_type, dynamic instructions, output_validator) | AC-11d.5, AC-11d.6 |
| `tests/agents/onboarding/test_conversation_agent.py` | `TestToolSelectionBiasRecovery` (mocked LLM emits `IdentityExtraction` for phone input → recovers via regex fallback OR ModelRetry) | AC-11d.4 |
| `tests/agents/onboarding/test_conversation_agent.py` | `test_agent_run_uses_message_history_primitive` | AC-11d.6 |

## 4. PR Splitting (≤400 lines per PR per pr-workflow.md)

Estimated total: ~600 LOC code + ~600 LOC tests = ~1200 LOC. SPLIT into 2 PRs:

### PR-A: State + cumulative completion + regex (T1-T6, T9-T11)
- New: `state.py`, `state_reconstruction.py`, `regex_fallback.py`
- New tests: `test_wizard_state.py`, `test_state_reconstruction.py`, `test_state_reconstruction_perf.py`, `test_regex_fallback.py`
- Refactor: `portal_onboarding.py` (cumulative state load + FinalForm gate + DELETE `_compute_progress` + ADD link_code mint + EXTEND `ConversationProfileResponse`)
- Refactor: `converse_contracts.py` (additive fields)
- Tests for converse cumulative + completion + regex paths
- Estimated: ~350-400 LOC

### PR-B: Agent refactor + dynamic instructions + FE wire-up (T7-T8, T12)
- Refactor: `conversation_agent.py` (consolidated tool OR retained tools + dynamic instructions + output_validator)
- Refactor: `conversation_prompts.py` (strip hardcoded routing)
- New tests: `test_dynamic_instructions.py`
- Tests for `TestConsolidatedAgent`, `TestToolSelectionBiasRecovery`, `test_agent_run_uses_message_history_primitive`
- FE TS type extension + re-mint code path + 429 fallback fix in same PR (driver: AC-11d.7 + AC-11d.8 Phase 3 Implementation Notes)
- Estimated: ~350-400 LOC

Both PRs MUST satisfy:
- Pre-push HARD GATE: `uv run pytest -q` AND `(cd portal && npm run test -- --run && npm run lint && npm run build)` PASS
- `/qa-review --pr N` to 0 findings across all severities (incl nitpicks)
- Agentic-Flow Test Requirements §1-3 included (cumulative-state monotonicity, completion-gate triplet, mock-LLM-emits-wrong-tool recovery)

## 5. Migration Strategy

**No DB schema migration required.** All persistence reuses existing `users.onboarding_profile JSONB` column (defined `nikita/db/models/user.py:117`). The cumulative state is reconstructed on each /converse request from existing JSONB content (option A in spec §FR-11d). Option B (denormalized `profile["slots"]` cache) is opt-in only if AC-11d.9 perf bench fails.

`telegram_link_codes` table is unchanged. The re-mint path (FE detects `link_code_expired=true` from GET) inserts a fresh row via existing `TelegramLinkRepository.create_code` — no UNIQUE(user_id) constraint exists per FR-11b, so no `ON CONFLICT` needed (spec clarification iter-2).

**Cutover behavior**: on first /converse request post-deploy, existing users with partial `onboarding_profile.conversation` content will see their cumulative state reconstructed correctly; the FE reducer simply mirrors `progress_pct` from BE so no FE state migration is needed.

## 6. Risk Register (lifted from Plan v16 §10)

| Risk | Mitigation |
|---|---|
| Pydantic AI `output_type=[X, str]` mode untested in this codebase | T7 integration test with mocked LLM responses before any /converse change |
| Dynamic `instructions=callable` signature change between Pydantic AI versions | Pin `pydantic-ai` version in pyproject; T7 asserts callable invoked per-turn |
| `WizardSlots.merge` returning new instance breaks deps mutation | `output_validator` reassigns `ctx.deps.state.slots = ctx.deps.state.slots.merge(...)` — explicit, tested |
| Regex fallback false-positive ("I'm 27 years old" → 27 → phone) | `phonenumbers` lib in `PhoneExtraction._phone_format` rejects non-E.164; fallback returns None on ValidationError; T5 covers |
| FE TS type drift breaks build after BE additive fields ship | Land BE + FE in PR-B together; CI Vercel build catches type errors |
| Reconstruction perf regression > 10 ms on 100-turn fixture | AC-11d.9 micro-bench in CI; if fails, ship option B in same PR |
| 100-turn elision interacts with cumulative state | AC-11d.10 covers; sibling test covers repeated-slot first-eviction-wins |
| GATE 2 finds new CRITICAL post-merge (FE C/H disposition) | FE C/H are tracked in spec Phase 3 Notes as PR-blockers; PR-B implementor cannot land without them |
| `_compute_progress` deletion breaks unrelated test that mocks it | T4 grep precedent: `grep -rn "_compute_progress" tests/` before deletion; update mocks |

## 7. Sequencing & Dependency Graph

```
PR-A (state + completion + regex) ──→ merge ──→ deploy ──→ smoke probe
                                            │
                                            └─→ /qa-review CLEAN
                                                    │
                                                    ▼
PR-B (agent + dynamic instructions + FE) ──→ merge ──→ deploy ──→ smoke probe
                                                  │
                                                  └─→ /qa-review CLEAN
                                                          │
                                                          ▼
                                                Phase 4: Walk W (live behavioral)
```

**Cap**: 3 walks (W → X → Y). After Y if not converged → escalate.

## 8. Tasks (T1-T12, owner: executor-agent, est. 3-6 h each)

### T1 — RED: failing tests for `WizardSlots`, `FinalForm`, `SlotDelta`
- **File:** `tests/agents/onboarding/test_wizard_state.py` (NEW)
- **ACs:**
  - AC-T1.1: `test_wizard_slots_starts_empty_with_progress_zero` asserts `WizardSlots().progress_pct == 0` AND `WizardSlots().missing == [<6 slot names>]`
  - AC-T1.2: `test_final_form_rejects_partial_state` asserts `FinalForm.model_validate({"location": ..., "scene": ..., ...3 of 6})` raises `ValidationError`
  - AC-T1.3: `test_final_form_age_under_18_rejects` asserts `identity.age = 17` triggers `@model_validator` failure
  - AC-T1.4: `test_slot_delta_discriminated_union` asserts a SlotDelta with `kind="phone"` + `value=PhoneExtraction(...)` round-trips through `model_dump_json`
- **Verify:** `uv run pytest tests/agents/onboarding/test_wizard_state.py -v` → ALL RED (file doesn't exist yet)

### T2 — GREEN: implement state models
- **File:** `nikita/agents/onboarding/state.py` (NEW)
- **ACs:**
  - AC-T2.1: `WizardSlots(BaseModel)` with 6 optional slot fields + `@computed_field missing` + `@computed_field progress_pct`
  - AC-T2.2: `FinalForm(BaseModel)` with 6 required slots + `@model_validator(mode="after") identity_age_18`
  - AC-T2.3: `TOTAL_SLOTS: Final[int] = 6` named constant per `.claude/rules/tuning-constants.md`
  - AC-T2.4: T1 tests GREEN

### T3 — RED: cumulative completion endpoint test
- **File:** `tests/api/routes/test_converse_endpoint.py::TestConverseCumulativeCompletion` (extend existing file)
- **ACs:**
  - AC-T3.1: `test_converse_empty_state_returns_complete_false` — no slots filled → `conversation_complete=False`, `progress_pct=0`
  - AC-T3.2: `test_converse_partial_state_returns_complete_false` — 3 of 6 slots filled → `conversation_complete=False`, `progress_pct≈50`
  - AC-T3.3: `test_converse_full_state_returns_complete_true_with_link_code` — all 6 slots → `conversation_complete=True`, `link_code != None`, `re.fullmatch("^[A-Z0-9]{6}$", link_code)`
  - AC-T3.4: tests RED (current /converse uses snapshot logic, not cumulative)

### T4 — GREEN: wire cumulative state into `/converse`
- **File:** `nikita/api/routes/portal_onboarding.py`
- **ACs:**
  - AC-T4.1: handler loads `WizardState.from_user(user, hydrator=build_state_from_conversation)` BEFORE agent.run
  - AC-T4.2: handler computes `complete = try: FinalForm.model_validate(state.slots_dict); except ValidationError: False`
  - AC-T4.3: `_compute_progress` helper DELETED (grep `rg "_compute_progress" nikita/api/routes/portal_onboarding.py` returns empty)
  - AC-T4.4: `conversation_complete = False` literal absent (grep gate from AC-11d.3)
  - AC-T4.5: terminal turn mints `link_code` via `TelegramLinkRepository.create_code` and returns it in `ConverseResponse`
  - AC-T4.6: T3 tests GREEN

### T5 — RED: regex phone fallback test
- **File:** `tests/agents/onboarding/test_regex_fallback.py` (NEW)
- **ACs:**
  - AC-T5.1: `test_regex_extracts_e164_phone_when_state_phone_unfilled` — input `"call me at +1 415 555 0234"` → returns `SlotDelta(kind="phone", value=PhoneExtraction(...))`
  - AC-T5.2: `test_regex_returns_none_for_age_substring` — input `"I'm 27 years old"` → returns `None` (phonenumbers rejects)
  - AC-T5.3: `test_regex_returns_none_when_state_phone_already_filled` — `state.phone` non-null → returns `None`
  - AC-T5.4: tests RED (file doesn't exist)

### T6 — GREEN: implement regex fallback
- **File:** `nikita/agents/onboarding/regex_fallback.py` (NEW)
- **ACs:**
  - AC-T6.1: `regex_phone_fallback(state, user_input) -> SlotDelta | None` defined
  - AC-T6.2: reuses `PhoneExtraction._phone_format` validator (no new phone-parser code)
  - AC-T6.3: T5 tests GREEN

### T7 — RED: state reconstruction tests (cumulative + elision boundary)
- **File:** `tests/agents/onboarding/test_state_reconstruction.py` (NEW)
- **ACs:**
  - AC-T7.1: `test_reconstruct_from_conversation_only_no_elided` — 3-turn fixture with extracted on each → `WizardSlots` reconstructed with all 3
  - AC-T7.2: `test_elision_boundary_preserves_slots` — `monkeypatch CONVERSATION_TURN_CAP=5`, 10-turn fixture with slots filled in turns 1-3 → all 3 slots survive
  - AC-T7.3: `test_repeated_slot_extraction_uses_live_conversation` — slot X set turn 1 (elided), refined turn 50 (live) → reconstruction returns turn-50 value
  - AC-T7.4: tests RED (no `state_reconstruction.py` yet)

### T8 — GREEN: implement state reconstruction reducer
- **File:** `nikita/agents/onboarding/state_reconstruction.py` (NEW)
- **ACs:**
  - AC-T8.1: `build_state_from_conversation(profile)` applies `elided_extracted` FIRST then iterates `conversation[*].extracted` (live overrides)
  - AC-T8.2: `RECONSTRUCTION_BUDGET_MS: Final[int] = 10` named constant
  - AC-T8.3: T7 tests GREEN

### T9 — RED: micro-bench perf test
- **File:** `tests/agents/onboarding/test_state_reconstruction_perf.py` (NEW)
- **ACs:**
  - AC-T9.1: `test_reconstruct_wizardslots_under_budget` — synthetic 100-turn `onboarding_profile`, p95 over 100 iterations
  - AC-T9.2: assertion `p95 < RECONSTRUCTION_BUDGET_MS` (imported from production module per tuning-constants.md single-source-of-truth)
  - AC-T9.3: test GREEN immediately (option A pure-Python reduction is fast)
  - AC-T9.4: if RED, option B opt-in profile["slots"] cache MUST land same PR (per spec FR-11d)

### T10 — RED: dynamic instructions + consolidated agent tests
- **File:** `tests/agents/onboarding/test_dynamic_instructions.py` + `test_conversation_agent.py::TestConsolidatedAgent`
- **ACs:**
  - AC-T10.1: `test_dynamic_instructions_callable_invoked_with_missing_slots` — wraps callable with MagicMock, asserts call count >= turn count, asserts at least one invocation had `state.missing` non-empty, asserts rendered prompt contains a slot name from `state.missing`
  - AC-T10.2: `TestConsolidatedAgent::test_output_type_mixed_mode` — mocked LLM emits `SlotDelta` → state merges; emits `str` → free-text reply
  - AC-T10.3: `TestToolSelectionBiasRecovery::test_llm_emits_wrong_tool_for_phone_input_recovers_via_regex_fallback` — mocked agent emits `IdentityExtraction` for `+1 415 555 0234`, asserts post-pipeline `state.phone` is filled
  - AC-T10.4: `test_agent_run_uses_message_history_primitive` — asserts `agent.run` called with `message_history=` non-empty on turn 2+
  - AC-T10.5: tests RED

### T11 — GREEN: refactor agent + integration smoke
- **Files:** `conversation_agent.py`, `conversation_prompts.py`, `portal_onboarding.py`
- **ACs:**
  - AC-T11.1: agent.run wired with `message_history=hydrate_message_history(...)` AND `deps=ConverseDeps(state=state)`
  - AC-T11.2: dynamic `instructions=callable` injects `state.missing` per turn (or output_type=[SlotDelta, str] consolidated mode)
  - AC-T11.3: `@output_validator` raises `ModelRetry` on ValidationError
  - AC-T11.4: regex fallback wired in step 3 of /converse handler (after agent.run, before completion gate)
  - AC-T11.5: T10 tests GREEN
  - AC-T11.6: full /converse flow integration smoke (mock LLM, real state machine, 6-turn fixture → `conversation_complete=True` + valid `link_code`)

### T12 — Pre-push HARD GATE + FE wire-up
- **Files:** `portal/src/app/onboarding/types/converse.ts`, `onboarding-wizard.tsx`
- **ACs:**
  - AC-T12.1: TS types extended with `link_code: string | null`, `link_expires_at: string | null`, `link_code_expired: boolean | undefined`
  - AC-T12.2: post-completion `api.linkTelegram()` workaround call REMOVED (FE reads `link_code` from terminal /converse response)
  - AC-T12.3: GET hydration branch on `link_code_expired===true` → re-call /converse to re-mint
  - AC-T12.4: 429 fallback preserves `state.isComplete` (no clobber)
  - AC-T12.5: `uv run pytest -q` PASS (full nikita suite)
  - AC-T12.6: `(cd portal && npm run test -- --run && npm run lint && npm run build)` PASS
  - AC-T12.7: pre-PR grep gates run (zero-assertion shells, PII format strings, raw cache_key, AC-11d.3 grep gate, AC-11d.8 grep gate) all empty

## 9. Verification per PR (mandatory before squash merge per pr-workflow.md)

- [ ] TDD evidence: 2 commits per task minimum (RED then GREEN)
- [ ] Pre-push HARD GATE output pasted in PR body under `## Local tests`
- [ ] Pre-PR grep gates (zero-assertion shells, PII format strings, raw cache_key, AC-11d.3, AC-11d.8) all empty
- [ ] Orchestrator grep-verify after implementor + before reviewer dispatch
- [ ] `/qa-review` fresh-context loop to 0 findings across blocking/important/nitpick. Every dispatch: `HARD CAP: 5 tool calls` + explicit changed-files list
- [ ] CI green
- [ ] Squash merge + commit-hash verification on `origin/master`
- [ ] Post-merge auto-dispatched smoke (curl probe + log sweep)

## 10. References

- Spec: `specs/214-portal-onboarding-wizard/spec.md` (FR-11d at master commit `6119b26`)
- Plan v16: `~/.claude/plans/delightful-orbiting-ladybug.md`
- Validation manifest: `specs/214-portal-onboarding-wizard/validation-findings.md`
- Rules: `.claude/rules/{agentic-design-patterns, testing, pr-workflow, tuning-constants}.md`
- ADR: `~/.claude/ecosystem-spec/decisions/ADR-009-agentic-design-patterns.md`
- Pydantic AI canonical: https://ai.pydantic.dev/{message-history,output,dependencies,graph}/
