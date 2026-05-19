## Architecture Validation Report — FR-11d Amendment

**Spec:** `specs/214-portal-onboarding-wizard/spec.md` (FR-11d, lines 654-753)
**Branch:** `spec/214-fr11d-slot-filling-amendment` (commit b4180e1)
**Status:** PASS (with 2 MEDIUM + 3 LOW findings to address pre-implementation)
**Timestamp:** 2026-04-22T00:00:00Z
**Validator:** sdd-architecture-validator (FR-11d v2 re-validation)

### Summary

- CRITICAL: 0
- HIGH: 0
- MEDIUM: 2
- LOW: 3

PASS criteria met (0 CRITICAL + 0 HIGH). Amendment is architecturally sound; the slot-filling redesign correctly encodes the 6 hard rules from `.claude/rules/agentic-design-patterns.md` and remediates the Walk V anti-patterns. Two MEDIUM items relate to module-boundary clarity and naming-migration scope; three LOW items are stylistic.

---

### Findings

| # | Severity | Category | Issue | Location | Recommendation |
|---|----------|----------|-------|----------|----------------|
| A1 | MEDIUM | Module Organization | `state.py` (the new `WizardSlots` / `FinalForm` / `SlotDelta` home) is referenced as living in `nikita/agents/onboarding/` but is never explicitly named in the spec. The spec implies it but never declares the file path. Implementor risk: split between `nikita/agents/onboarding/state.py` (agent-coupled) vs `nikita/onboarding/state.py` (domain-layer). The two existing modules have a real boundary (`nikita/onboarding/` is shipped-to-portal contracts + tuning + handoff + validation; `nikita/agents/onboarding/` is the Pydantic AI agent + extraction schemas + persistence). | spec.md L660-674 ("State Model" subsection) | Add an explicit "**File location**: `nikita/agents/onboarding/state.py`" line under the "State Model — Cumulative Server-Side Slots" heading. Justification: `WizardSlots` is the agent's runtime state model and depends on `extraction_schemas.py` (same dir); `FinalForm` is the agent's completion gate. Both belong with the agent, not in the contracts layer. The contracts layer (`nikita/onboarding/contracts.py`) stays request/response-shaped only. |
| A2 | MEDIUM | Naming Consistency / Migration Path | `SlotDelta` (new, FR-11d) and `ConverseResult` (existing in `nikita/agents/onboarding/converse_contracts.py`) coexist without an explicit mapping. Spec says `output_type=[SlotDelta, str]` is the "default target shape" and the 6+1-tool registration is "transitional," but never states whether `SlotDelta` REPLACES the per-tool `*Extraction` outputs or wraps them, and never says what happens to `ConverseResult` in the transitional vs. target shape. | spec.md L702-708 ("Tool Architecture") + missing explicit reference to `converse_contracts.py:ConverseResult` | Add a one-paragraph "Migration path" under FR-11d's Tool Architecture subsection: (a) Transitional shape: `ConverseResult` unchanged; per-tool `*Extraction` outputs feed into the `WizardSlots.model_copy(update=...)` merge inside the converse handler. (b) Target shape: single tool returns `SlotDelta` (a Pydantic model with one optional field per slot) which is then merged via `model_copy`. `ConverseResult` (the wire response) is unchanged in both shapes — only the agent's internal output_type changes. This makes the migration non-breaking for the FE contract. |
| A3 | LOW | Backward-Compat Documentation | FR-1's supersession header (L52) cleanly states the env-flag-gated split, but FR-2 through FR-10 do not have any per-FR markers indicating which apply to (a) legacy step-wizard only, (b) chat-first only, (c) both. FR-2 (Dossier Styling), FR-7 (POST profile), FR-10 (backend extension) clearly apply to both; FR-4 (preview-backstory step 8), FR-8 (step order), FR-9 (BackstoryChooser step UI) apply to legacy only. | spec.md FR-2 through FR-10 (no per-FR scope markers) | Add a one-line scope marker under each FR-2…FR-10 heading: `**Scope**: legacy-wizard only` / `chat-first only` / `both variants`. Reduces implementor confusion when the env flag is later flipped to "chat-first only" and dead FRs need to be archived. |
| A4 | LOW | Import Patterns / Circular-Dep Risk | "Cumulative state reconstruction" (L722-724) reduces over `profile["conversation"][*].extracted ∪ profile["elided_extracted"]`. The handler in `nikita/api/routes/portal_onboarding.py` will need to import `WizardSlots` from `nikita/agents/onboarding/state.py` AND continue importing `conversation_persistence.load_profile` (existing). This is a clean linear dep: `routes → agents/onboarding/state → agents/onboarding/extraction_schemas` and `routes → agents/onboarding/conversation_persistence`. No cycle. BUT: if `state.py` itself ever imports `conversation_persistence` (e.g., to add a `WizardSlots.from_profile(profile_dict)` constructor), the cycle becomes routes → state → persistence → routes (via shared session). | spec.md L722-727 ("Conversation Persistence") | Add a constraint sentence: "`state.py` imports ONLY from `extraction_schemas.py` and stdlib. The reconstruction reducer (`build_state_from_conversation`) lives in the route handler OR a dedicated `state_reconstruction.py`, never inside `state.py` itself, to keep `WizardSlots` import-cycle-safe." |
| A5 | LOW | Single Source of Truth | AC-11d.2 says "BE serves cumulative; FE mirrors verbatim, never recomputes." This is correct and matches the Hard Rules anti-pattern table (`progress = response.progress_pct` overwrite is the fix). However, the spec also mentions (NR-FR-something earlier) `localStorage` wizard-state persistence (US-3, AC-US3.1-3) keyed by user_id. There is no explicit statement that `localStorage` for the chat-first variant stores ONLY UI state (current input draft, scroll position) and NEVER the cumulative slots — slots come from the BE on every /converse call. Without this clarification, an implementor could reintroduce the FE-side "source of truth" anti-pattern via `localStorage` instead of via the reducer. | spec.md FR-11d L735 vs US-3 AC-US3.1-3 (L789-792) | Add to FR-11d: "**localStorage scope**: under the chat-first variant (default), `localStorage` MUST NOT cache `WizardSlots`, `progress_pct`, or `complete`. Only ephemeral UI state (current input buffer, last-rendered turn id) is permitted in localStorage. Cumulative slots are reconstructed BE-side on every /converse call. This preserves AC-11d.1's invariant. The `nikita_wizard_{user_id}` localStorage key from US-3 applies to legacy-wizard only." |

---

### Proposed Module Organization (Confirmed)

```
nikita/
├── agents/
│   └── onboarding/                            # Pydantic AI agent + runtime state
│       ├── conversation_agent.py              # MODIFIED — Agent(instructions=callable)
│       ├── conversation_persistence.py        # UNCHANGED — JSONB load/save
│       ├── conversation_prompts.py            # MODIFIED — callable-rendered, no static routing
│       ├── converse_contracts.py              # UNCHANGED — wire ConverseResult
│       ├── extraction_schemas.py              # UNCHANGED — *Extraction schemas (slot sources)
│       ├── message_history.py                 # UNCHANGED — hydrate_message_history
│       ├── state.py                           # NEW — WizardSlots, FinalForm, SlotDelta, TOTAL_SLOTS
│       ├── state_reconstruction.py            # NEW (recommended A4) — build_state_from_conversation
│       └── validators.py                      # POSSIBLY MODIFIED — add output_validator(ModelRetry)
├── onboarding/                                 # Domain layer (contracts + tuning + handoff)
│   ├── contracts.py                            # UNCHANGED — request/response wire types
│   ├── tuning.py                               # UNCHANGED for FR-11d
│   ├── handoff.py                              # UNCHANGED — OnboardingProfileWriter path
│   └── ... (other existing files)
└── api/
    └── routes/
        └── portal_onboarding.py                # MODIFIED — /converse handler + cumulative reconstruction
```

The boundary between `nikita/agents/onboarding/` (agent runtime) and `nikita/onboarding/` (domain contracts) is preserved and reinforced by FR-11d. The new `state.py` correctly belongs in `agents/onboarding/` because:
1. It holds the agent's runtime state model (mutating across turns)
2. It depends on `extraction_schemas.py` (sibling)
3. It is consumed by the agent loop, not the wire contract
4. `nikita/onboarding/` already has `validation.py` (a different concern: portal-facing field validation)

### Module Dependency Graph

```
routes/portal_onboarding.py
  ├─→ agents/onboarding/state.py            (WizardSlots, FinalForm)
  ├─→ agents/onboarding/state_reconstruction.py  (build_state_from_conversation)
  ├─→ agents/onboarding/conversation_agent.py  (Agent + tools + dynamic instructions callable)
  ├─→ agents/onboarding/conversation_persistence.py  (load/save JSONB)
  ├─→ agents/onboarding/message_history.py   (hydrate_message_history)
  ├─→ agents/onboarding/converse_contracts.py  (ConverseResult wire type)
  └─→ onboarding/handoff.py                   (OnboardingProfileWriter)
       └─→ db/repositories/telegram_link_repository.py  (FR-11b atomic verify_code)

agents/onboarding/state.py
  ├─→ agents/onboarding/extraction_schemas.py  (LocationExtraction, SceneExtraction, ...)
  └─→ pydantic, stdlib only                    (NO conversation_persistence import — anti-cycle)

agents/onboarding/conversation_agent.py
  ├─→ agents/onboarding/state.py
  ├─→ agents/onboarding/extraction_schemas.py
  ├─→ agents/onboarding/conversation_prompts.py  (callable that renders state.missing)
  └─→ pydantic_ai
```

No cycles. Acyclic linear dep chain. (Risk noted in A4 if `state.py` ever imports `conversation_persistence`.)

### Separation of Concerns Analysis

| Layer | Responsibility | FR-11d compliance |
|-------|---------------|-------------------|
| Wire (contracts) | `OnboardingV2ProfileRequest/Response`, `ConverseResult`, `BackstoryOption` — request/response shapes only | PASS — unchanged. `SlotDelta` is internal-to-agent, not wire. |
| Domain state (`state.py`) | Cumulative `WizardSlots`, `FinalForm` validator-as-gate, `progress_pct` derivation | PASS — Pydantic-pure, no I/O, no DB |
| Agent (`conversation_agent.py`) | Pydantic AI `Agent` definition, tool registrations, dynamic instructions callable, output_validator | PASS — single agent, mixed output target shape declared |
| Persistence (`conversation_persistence.py`) | JSONB load/save with `SELECT FOR UPDATE` + `MutableDict.as_mutable` | PASS — unchanged per spec L722 |
| Reconstruction (NEW recommended `state_reconstruction.py`) | Reduce `conversation[*].extracted ∪ elided_extracted` → `WizardSlots` | RECOMMEND — pull this out of route handler so it's unit-testable in isolation |
| Route handler (`portal_onboarding.py`) | HTTP plumbing: load profile → reconstruct state → run agent → merge → validate → persist → respond | PASS — handler stays thin; gate is `try: FinalForm.model_validate(...)` not a literal |
| FE reducer (`useConversationState.ts`) | Mirror BE `progress_pct` and `complete` verbatim; never recompute | PASS — explicit at AC-11d.2 |

No layer violations. The "FinalForm IS the gate" pattern correctly pushes business invariants (age ≥ 18, voice-requires-phone) into the model layer where they belong, away from handler conditionals.

### Type Safety

- `WizardSlots(BaseModel)`: declared, all 6 slots optional, `@computed_field` for `missing` / `progress_pct` — correct shape per Hard Rule §1.
- `FinalForm(BaseModel)`: declared, all 6 slots **non-optional**, `@model_validator(mode="after")` for cross-field rules — correct shape per Hard Rule §2.
- `SlotDelta(BaseModel)`: declared as the discriminated-union output_type element — needs explicit field schema in spec OR a forward-ref to "one optional field per slot, mirroring `WizardSlots`" (currently implied; clarify per A2).
- `ConverseDeps`: declared as the `RunContext[ConverseDeps]` payload carrying cumulative state to the dynamic-instructions callable. Spec mentions `deps=ConverseDeps(...)` at L730 but does not enumerate fields. Implementor must define: at minimum `state: WizardSlots`, `user_id: UUID`, possibly `conversation_id: UUID`. Recommend adding a one-line schema sketch.
- `PhoneExtraction(phone_preference="voice", phone=parsed, confidence=1.0)`: `confidence` field referenced at L711 — verify it exists on the existing `extraction_schemas.PhoneExtraction` or note the additive field. (Stretch goal; not blocking.)

### Import Pattern Checklist

- [x] `state.py` imports only `extraction_schemas` + stdlib + pydantic — no cycle risk if A4 constraint added
- [x] Route handler imports `state.py` AND `conversation_persistence.py` separately (no transitive cycle)
- [x] FE imports `progress_pct` from BE response only; never computes locally (AC-11d.2 enforces)
- [x] No new import alias changes required; existing `nikita.*` and portal `@/*` aliases unchanged
- [x] Conditional import unnecessary (env flag `NEXT_PUBLIC_USE_LEGACY_FORM_WIZARD` is FE-only; BE serves both variants from the same /converse endpoint)

### Error Handling Architecture

- **Pre-tool (Pydantic on tool args)**: existing `extraction_schemas.*` Pydantic models — unchanged.
- **Post-tool (`@agent.output_validator` raising `ModelRetry`)**: NEW per FR-11d L707, goes in `validators.py` or `conversation_agent.py`. Self-correcting loop with `retries=4`. Aligns with Hard Rule §5.
- **Deterministic post-processing (regex phone fallback)**: NEW per FR-11d L709-711, lives in route handler post-agent-run. Single permitted post-processing path. Defense-in-depth for the highest-stakes slot.
- **Completion gate**: `try: FinalForm.model_validate(...) ; except ValidationError` — no boolean literals in handler. Aligns with project-wide pattern of pushing invariants into Pydantic models (existing in `nikita/onboarding/contracts.py`).

Broader exception strategy is consistent with existing patterns (per `memory/backend.md` repository pattern + `engine/` Pydantic validation throughout). No new exception hierarchy needed.

### Single Source of Truth (AC-11d.2 + FE Mirror)

- **BE serves cumulative `progress_pct`**: handler computes once via `state.progress_pct` (computed field), serializes into `ConverseResult` response.
- **FE mirrors verbatim**: `useConversationState.ts:169` reducer assigns `state.progress_pct = response.progress_pct` (already correct post-PR #392 IFF BE serves cumulative — anti-pattern table acknowledges this).
- **No conflict with existing FRs**: FR-5 (pipeline poll) tracks a separate `PipelineReadyResponse.state` (pending/ready/degraded/failed) — orthogonal axis. FR-7 (POST profile) is a one-shot terminal write triggered by `complete=True`. FR-11 / FR-11b (link minting) is triggered AFTER `FinalForm.model_validate` succeeds — clean handoff per L713-718.
- **localStorage caveat (A5)**: needs explicit clarification that the chat-first variant does NOT cache cumulative slots client-side.

### Backward Compatibility

| FR | Status under FR-11d |
|----|---------------------|
| FR-1 (11-step click-wizard) | SUPERSEDED — retained behind `NEXT_PUBLIC_USE_LEGACY_FORM_WIZARD` flag (legacy-only). Per-FR scope markers needed (A3). |
| FR-2 (dossier styling) | UNCHANGED — applies to both variants (chat bubbles + legacy steps both use the same theme tokens) |
| FR-3 through FR-9 | LEGACY-ONLY — UI-step-specific; chat-first variant collects same slots through conversation, not stepped UIs |
| FR-10 (backend: PUT chosen-option + PipelineReady extension) | APPLIES TO BOTH — chat-first still calls `PUT /chosen-option` when backstory slot fills; `PipelineReadyResponse.wizard_step` becomes optional under chat-first (slot count, not step number) |
| FR-11 (handoff) | UNCHANGED — terminal handoff is the same in both variants |
| FR-11b (Telegram deep-link binding) | UNCHANGED — FR-11d L716-718 explicitly reuses FR-11b's `TelegramLinkRepository.create_code` and `?start=<code>` href. Clean integration. |

No backward-compat conflicts. The env flag cleanly bisects the FE rendering surface; the BE /converse endpoint, contracts, and persistence are shared.

### Naming Consistency: SlotDelta vs ConverseResult

- `ConverseResult` (existing wire type in `converse_contracts.py`): the HTTP response body for `/converse`. Carries `progress_pct`, `complete`, `link_code`, conversation turn metadata. UNCHANGED.
- `SlotDelta` (NEW, internal): the agent's per-turn structured output (one of the `output_type=[SlotDelta, str]` union members). NEVER appears on the wire.
- Migration path: Transitional shape uses 6 `*Extraction` outputs; target shape uses single `SlotDelta`. Both merge into `WizardSlots` via `model_copy(update=...)`. The wire `ConverseResult` is unchanged in both — making the FE/BE contract migration zero-risk.

This is correct, but spec should make the migration explicit per A2.

### Recommendations (Priority Order)

1. **A1 (MEDIUM)** — Add explicit file path declaration: `nikita/agents/onboarding/state.py`. One-line addition under the State Model heading.
2. **A2 (MEDIUM)** — Add a "Migration path" paragraph clarifying `SlotDelta` vs existing `*Extraction` outputs vs unchanged wire `ConverseResult`. Removes implementor ambiguity about the transitional → target trajectory.
3. **A4 (LOW)** — Add a one-sentence import constraint on `state.py` (no `conversation_persistence` import). Recommend extracting reconstruction logic to `state_reconstruction.py`.
4. **A5 (LOW)** — Add a localStorage scope clarifier: under chat-first, localStorage holds UI state only, never cumulative slots.
5. **A3 (LOW)** — Add per-FR scope markers (`legacy-only` / `chat-first only` / `both`) to FR-2 through FR-10 to disambiguate which legacy FRs are eventually archivable.

All five are documentation-only adjustments. No structural redesign required.

---

### Conclusion

**PASS**. The FR-11d amendment is architecturally sound. It correctly:

1. Preserves the existing `nikita/agents/onboarding/` ↔ `nikita/onboarding/` boundary
2. Encodes the 6 hard rules from `.claude/rules/agentic-design-patterns.md` as testable acceptance criteria (AC-11d.1 through AC-11d.6)
3. Reuses existing infrastructure (`conversation_persistence.py`, `extraction_schemas.py`, `hydrate_message_history`, `OnboardingProfileWriter`, `TelegramLinkRepository`) without re-implementation
4. Maintains backward compatibility with FR-2 (styling), FR-10 (backend extensions), FR-11/FR-11b (handoff) by env-flag-gating only the FE rendering surface
5. Avoids circular dependencies through the proposed module layout

The 5 findings are all clarifications that strengthen implementation guardrails; none block planning. With A1 and A2 addressed (15-min spec edits), the spec is ready to proceed to GATE 3 / planning.
