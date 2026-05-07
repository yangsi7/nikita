# Subspec 217-3A — BE Emission Union (Discriminated `output_type`)

**Parent**: `specs/217-onboarding-wizard-deterministic-redesign/spec.md` FR-5, FR-6, FR-7, FR-8, FR-9, FR-10a, FR-15
**PR boundary**: 217-3A (depends on 217-2 merged; lands BEFORE 217-3B)
**Estimated**: 250-300 LOC (≤350 cap; pre-flight `git diff --stat` mid-implementation)
**Status**: Draft (GATE 1)

---

## Scope

Refactors the onboarding agent's emission contract from coarse `output_type=[TurnOutput, TurnFailure]` (216-B baseline) to a 3-tool discriminated union `[ReactionOnly, FollowUpQuestion, TurnFailure]` per Pydantic AI 1.71.0. Each becomes a `ToolOutput(name=…)`-named final tool; the LLM commits to exactly one per turn. Adds an `@output_validator` mirror-of-next + mirror-echo guard, a sidecar `AgentEmissionState` for transient followup state, and refactors `/answer` route dispatch on emission type. Includes the BE side of the IdentityPair (FR-10a) contract — name+age compound slot — leaving FE work to 217-3B.

This sub-PR lands BEFORE 217-3B so the FE has a stable BE contract to consume.

## Acceptance Criteria

### Emission union (FR-5)

| AC | Description | Severity |
|---|---|---|
| AC-5.1 | New file `nikita/agents/onboarding/converse_contracts.py` (or `agent_emission.py`) defines `ReactionOnly`, `FollowUpQuestion`, refactored `TurnFailure` per master plan.md §3.1 | HIGH |
| AC-5.2 | `nikita/agents/onboarding/conversation_agent.py:266` Agent constructor: `output_type=[ToolOutput(ReactionOnly, name='emit_reaction'), ToolOutput(FollowUpQuestion, name='ask_followup'), ToolOutput(TurnFailure, name='turn_failure')]` | HIGH |
| AC-5.3 | `result.output` is `ReactionOnly | FollowUpQuestion | TurnFailure`; route handler branches via `isinstance` — verified by pytest | HIGH |

### Decision rule (FR-6)

| AC | Description | Severity |
|---|---|---|
| AC-6.1 | `Agent(instructions=callable)` callable invoked per-turn; injects (a) next deterministic question text, (b) `state.missing` slots, (c) decision rule (ReactionOnly vs FollowUpQuestion vs duplicate guard) | HIGH |
| AC-6.2 | Callable receives current `WizardSlots` via `RunContext.deps`; verified by `MagicMock` wrapper assertion (`agentic-design-patterns.md` Required Test #2) | HIGH |

### Output validator (FR-7)

| AC | Description | Severity |
|---|---|---|
| AC-7.1 | `@agent.output_validator` rejects `FollowUpQuestion.question_text` if `difflib.SequenceMatcher(None, q1, q2).ratio() > 0.85` against next deterministic question text | HIGH |
| AC-7.2 | Validator rejects `ReactionOnly.reaction_text` containing user's last answer verbatim (case-insensitive substring) | HIGH |
| AC-7.3 | Both rejections call `raise ModelRetry(...)` (Pydantic AI self-correction) | HIGH |
| AC-7.4 | Calibration fixture at `tests/agents/onboarding/fixtures/similarity_calibration.py` containing 5 hand-crafted near-duplicate question pairs (ratio expected >0.85) + 5 distinct pairs (ratio expected <0.85). Threshold 0.85 LOCKED only after this fixture verifies separation. | HIGH |

### Sidecar state (FR-8)

| AC | Description | Severity |
|---|---|---|
| AC-8.1 | New `nikita/agents/onboarding/agent_emission_state.py` — `class AgentEmissionState(BaseModel): pending_followup: FollowUpQuestion | None` | HIGH |
| AC-8.2 | Persistence at `users.onboarding_profile.pending_followup` JSONB column (separate from `users.onboarding_profile.slots`); cleared by setting `null` on followup resolution | HIGH |
| AC-8.3 | `WizardSlots.progress_pct` monotonic across followup pending+resolved transitions — verified by 3-turn fixture asserting `progress_pct[t+1] >= progress_pct[t]` (`testing.md` agentic-flow test #1) | CRITICAL |

### `/answer` dispatch (FR-9)

| AC | Description | Severity |
|---|---|---|
| AC-9.1 | `nikita/api/routes/portal_onboarding.py /answer` dispatches via `isinstance(result.output, ...)` branches — `ReactionOnly` → `{kind:"reaction", reaction_text}` (slot NOT advanced; sidecar cleared); `FollowUpQuestion` → `{kind:"followup", payload}` (sidecar persisted); `TurnFailure` → existing failure path; deterministic answer (no agent emission) → existing slot-advance path | HIGH |
| AC-9.2 | Completion gate `FinalForm.model_validate(state.slots_dict)` UNCHANGED (Hard Rule #2 preserved) | CRITICAL |
| AC-9.3 | New pytest at `tests/api/routes/test_emission_dispatch.py` — one test per emission kind asserts response shape | HIGH |

### IdentityPair BE contract (FR-10a)

| AC | Description | Severity |
|---|---|---|
| AC-10a.1 | `/answer` accepts `{slot: "identity_pair", value: {name: str, age: int}}` | HIGH |
| AC-10a.2 | Partial-validation: name valid + age invalid → persist name to `WizardSlots.name`, return `{kind: "field_error", errors: {age: "..."}}`; FE preserves valid name input value (217-3B side) | HIGH |
| AC-10a.3 | New pytest `tests/api/routes/test_identity_pair.py` covers full-valid, partial-valid (name OK age bad), partial-valid (name bad age OK), full-invalid cases | HIGH |

### Pydantic AI advisory (FR-15)

| AC | Description | Severity |
|---|---|---|
| AC-15.1 | If implementation reconstructs message_history from DB (rather than `result.new_messages()` chaining), use `ReinjectSystemPrompt` capability per Phase-2 doc verification (https://ai.pydantic.dev/message-history/, scraped 2026-05-07) | MEDIUM (advisory) |

### Test coverage (`agentic-design-patterns.md` + `testing.md`)

| AC | Description | Severity |
|---|---|---|
| AC-T-1 | Cumulative-state monotonicity test — 3+ turn fixture asserts `progress_pct[t+1] >= progress_pct[t]` even with followup pending+resolved transitions | CRITICAL (Walk V precedent) |
| AC-T-2 | Completion-gate triplet test — empty/partial/full state → False/0%, False/<100%, True/100% via `FinalForm.model_validate` | CRITICAL |
| AC-T-3 | Mock-LLM-emits-wrong-tool recovery test — agent emits `FollowUpQuestion` when ReactionOnly was correct → `@output_validator` ModelRetry self-corrects OR deterministic fallback | CRITICAL |
| AC-T-4 | Agent invocation contract test — `agent.run(...)` called with `message_history=` AND `deps=` containing cumulative state | HIGH |
| AC-T-5 | Dynamic-instructions invocation test — callable invoked per-turn, references `state.missing` | HIGH |

### Verification

| AC | Description | Severity |
|---|---|---|
| AC-V.1 | Pre-push HARD GATE — full nikita + portal suites green | HIGH |
| AC-V.2 | `/qa-review --pr <N>` zero-tolerance fresh-context loop | HIGH |
| AC-V.3 | LOC pre-flight at mid-implementation: `git diff --stat origin/master...HEAD`. If >350 LOC, split `@output_validator` (FR-7) and sidecar (FR-8) into 217-3A.1 prerequisite PR | HIGH |
| AC-V.4 | NO live walk for 217-3A in isolation (BE contract change, FE not yet consuming). Walk B3 in 217-3B covers integration. | NOTE |

## Files Touched (Reuse Map)

| File | Action |
|---|---|
| `nikita/agents/onboarding/converse_contracts.py` | Add `ReactionOnly`, `FollowUpQuestion`; refactor `TurnFailure` |
| `nikita/agents/onboarding/conversation_agent.py:266` | Update `output_type=[ToolOutput(...), ...]`; update `instructions=callable` |
| `nikita/agents/onboarding/validators.py` | Add `mirror_of_next_validator` + `mirror_echo_validator` decorators |
| `nikita/agents/onboarding/agent_emission_state.py` | NEW (sidecar BaseModel) |
| `nikita/agents/onboarding/prompts.py` | Update prompt templates for new emission contract |
| `nikita/agents/onboarding/state.py` | Unchanged (`WizardSlots` invariants preserved) |
| `nikita/api/routes/portal_onboarding.py` | Refactor `/answer` dispatch on emission type; add IdentityPair contract |
| `nikita/db/models/user.py` | Document `onboarding_profile.pending_followup` JSONB field semantics (no schema migration; JSONB is permissive) |
| `tests/agents/onboarding/test_emission_union.py` | NEW |
| `tests/agents/onboarding/test_emission_state_sidecar.py` | NEW |
| `tests/agents/onboarding/test_output_validator_mirrors.py` | NEW |
| `tests/agents/onboarding/fixtures/similarity_calibration.py` | NEW (10 hand-crafted pairs) |
| `tests/api/routes/test_emission_dispatch.py` | NEW |
| `tests/api/routes/test_identity_pair.py` | NEW |

## Agentic-Design-Patterns 6-Rule Compliance

Per `.claude/rules/agentic-design-patterns.md`:

| Hard Rule | How 217-3A complies |
|---|---|
| 1. Cumulative server-side state | `WizardSlots` unchanged; sidecar `AgentEmissionState` is SEPARATE (transient state, not slot data); persistence in JSONB column off the user row |
| 2. Pydantic completion gates | `FinalForm.model_validate(state.slots_dict)` UNCHANGED (AC-9.2) — never literal |
| 3. Tool consolidation | 3-tool discriminated union (NOT 7-tool fan-out); each has `ToolOutput(name=…)` per Pydantic AI 1.71.0 |
| 4. Monotonic progress | `WizardSlots.progress_pct` `@computed_field` UNCHANGED; AC-T-1 verifies monotonicity through followup transitions |
| 5. Three-layer validation | Pre-tool (Pydantic types on `ReactionOnly`/`FollowUpQuestion` fields) + post-tool (`@output_validator` ModelRetry per FR-7) + deterministic post-processing (existing regex phone fallback preserved) |
| 6. Official `message_history=` primitive | `agent.run(..., message_history=state.messages, deps=deps)` UNCHANGED; FR-15 ReinjectSystemPrompt advisory if DB rehydration is added |

## Pydantic AI Primitives Used

| Primitive | Use here | Doc |
|---|---|---|
| `Agent(output_type=[A, B, C])` discriminated list | Three emission tools | https://ai.pydantic.dev/output/ |
| `ToolOutput(Cls, name=...)` wrapper | Each emission becomes a named `final_result_*` tool | https://ai.pydantic.dev/output/ |
| `Agent(instructions=callable)` | Per-turn dynamic system prompt | https://ai.pydantic.dev/output/ |
| `agent.run(..., message_history=, deps=)` | Multi-turn conversation context + DI | https://ai.pydantic.dev/message-history/ |
| `Agent(deps_type=X)` + `RunContext[X]` | Inject `WizardSlots` + sidecar into instructions/tools | https://ai.pydantic.dev/dependencies/ |
| `@agent.output_validator` + `raise ModelRetry` | Mirror-of-next + mirror-echo self-correction | https://ai.pydantic.dev/output/#output-validator-functions |
| `ReinjectSystemPrompt` | (FR-15 advisory) preserve system prompt across DB-rehydrated message_history | https://ai.pydantic.dev/message-history/ |

## Out of Scope

- FE wizard refactor (217-3B).
- Backstory hang fix (217-2 — already merged before this lands).
- pydantic-graph FSM (rejected per master constraints).
