---
title: Spec 217 — Onboarding Wizard Deterministic-Track Redesign + Bug-Fix Bundle
lifecycle: living
predecessors: [216-B, 216-C]
successor: null
---

# Feature Specification: Onboarding Wizard Deterministic-Track Redesign (Spec 217)

**Spec ID**: 217-onboarding-wizard-deterministic-redesign
**Status**: Draft (GATE 1 → pending GATE 2 validators)
**Supersedes**: Spec 216-B (agentic-wizard-core) + Spec 216-C (cinematic-frontend). Master Spec 216 master spec.md remains partly consumed (216-A/D/E/F/G/H preserved).
**Date**: 2026-05-07
**Author**: SDD spec-author subagent (worktree-isolated)
**Authoritative inputs**: `docs-to-process/20260507-spec217-onboarding-redesign-planning-brief.md` (with ERRATA), `docs-to-process/20260507-spec217-2-backstory-diagnosis.md` (frozen spike artifact)

---

## Overview

### Problem Statement

User tested onboarding post-Walk-A1 (PRs #537/#538/#539 shipped 2026-05-06) and reported 5 catastrophic UX failures:

1. **Cold-start CTA**: tapping the landing CTA opens Telegram chat with no `/start` prefill (Telegram only renders the "START" button when the chat is empty; users with prior chat history get a frozen chat).
2. **Intermediate "access portal" interstitial copy** breaks the cinematic landing.
3. **Loading-state flash** ("in development / in progress") between magic-link click and first wizard frame.
4. **Deterministic question + agent reaction overlaid** in the same wizard card (per user screenshots) — violates 216-C's intended "clean wizard with sibling agent voice" model.
5. **Backstory generation hangs indefinitely** at `"preparing the three of us…"` with no retry, timeout, or fallback.

Underlying causes are documented in the planning brief (Phase-1 codebase verification against master `81aa0f5`) and in `docs-to-process/20260507-spec217-2-backstory-diagnosis.md` (root cause C5: FE has no fallback when `archetype_cards === null` in the `archetype` screen branch at `WizardShell.tsx:771-776`).

The 216-B / 216-C agentic-wizard architecture is sound at the BE level but the FE shipped with overlay rendering (L467 `reactionText` + L542 `<NikitaReaction>` + L760-789 control rendering) that breaks the "clean deterministic track + sibling agent subspace" UX contract; the agent emission contract from 216-B (`output_type=[TurnOutput, TurnFailure]`) is too coarse to express the "react-OR-followup, never-both" rule cleanly. Spec 217 redesigns the contract + FE while preserving 216-A (TG canonical routing), 216-D (Big Five + 12 archetypes), 216-E (firecrawl tools + cost-guard), 216-F (testing infrastructure), 216-G (TG-first landing CTA — only narrow extension), 216-H (autobind hardening).

### Proposed Solution

A 5-sub-PR bundle (each ≤400 LOC per `pr-workflow.md`) that:

1. **217-0** — Prereq cleanup: `networkidle` violations in onboarding.spec.ts (13 occurrences per ERRATA), test.skip resolution, `git rm` of `portal/src/app/onboarding/auth/` if still tracked, ROADMAP backfill for #537/#538/#539.
2. **217-1** — Cold-start CTA payload (`?start=welcome` via `URLSearchParams`) + interstitial reskin (Spec 208 brand veil + UA-default-safe auto-advance) + loading-flash remediation.
3. **217-2** — Backstory hang FE-side fallback per spike root cause C5 (FR-4a/4b/4c).
4. **217-3A** — BE emission union refactor: `[ReactionOnly, FollowUpQuestion, TurnFailure]` discriminated `output_type` with `ToolOutput(name=…)` per Pydantic AI 1.71.0; `@output_validator` mirror-of-next + mirror-echo guards via `difflib.SequenceMatcher`; sidecar `AgentEmissionState` for transient followup state (NOT in `WizardSlots`); `/answer` dispatch by emission kind.
5. **217-3B** — FE wizard refactor: sibling DOM regions `<DeterministicTrack>` + `<AgentSubspace>` (no overlay), interaction-locking semantics (deterministic stays enabled during reaction; locked during followup), IdentityPair compound control (name+age in one card), cumulative-state reducer.

Each sub-PR ships with TDD coverage + `/qa-review` zero-tolerance loop + live-walk verification per `live-testing-protocol.md`.

### Success Criteria

- **No overlay** in wizard: `data-testid="deterministic-card"` and `data-testid="agent-subspace"` are sibling DOM nodes (not nested) verified by vitest.
- **Cold-start CTA**: tapping landing CTA opens Telegram with `/start welcome` prefilled regardless of prior chat history; Nikita responds within 5s (216-A AC A1.4).
- **Interstitial**: brand veil renders on iOS PWA + Telegram IAB; tap-anywhere advances + persists JWT cookie; desktop Chrome + Firefox auto-advance ≤100ms.
- **Loading flash**: time-to-first-deterministic-card ≤200ms p95 warm-cache, ≤500ms p95 cold-start.
- **Backstory**: never hangs >5s on `archetype_cards === null`; FE deterministic fallback or retry CTA always presents an escape; BE 20s `wait_for` timeout on `pick_three_archetypes`.
- **Agent emission**: agent emits exactly one of {ReactionOnly, FollowUpQuestion, TurnFailure} per turn; `@output_validator` rejects mirror-of-next + mirror-echo via `ModelRetry`; cumulative `progress_pct` monotonic.
- **All 12-step live walks** (B1, B2, B3, B4) PASS per `live-testing-protocol.md`.

---

## Functional Requirements

### FR-1: Cold-start CTA static payload (sub-PR 217-1)
**Priority**: P1
**Description**: Append `?start=welcome` to TG CTA hrefs in `portal/src/components/landing/{hero-section,cta-section}.tsx` and `portal/src/app/login/page-client.tsx` (unauthenticated branch only) using `URLSearchParams` API. BE behavior unchanged — bare `/start` and `/start welcome` both route to `SignupHandler.handle_welcome` per 216-A AC A1.1+A1.2.

### FR-2: Interstitial reskin with default-safe UA strategy (sub-PR 217-1)
**Priority**: P1
**Description**: Replace `InterstitialClient.tsx` content with Spec 208 brand veil (bg-void + AuroraOrbs + Geist Sans heading). ALWAYS render the brand veil + tap surface. Layer programmatic `router.push` auto-advance ONLY on confirmed-non-iOS + non-IAB UAs (positive detection: Chrome desktop, Firefox, Edge). Preserve Spec 215 FR-6 iOS PWA + IAB user-gesture requirement (real touch event needed for cookie commit). `router.prefetch('/onboarding')` in a `useEffect` for instant transition.

### FR-3: Loading flash diagnosis + remediation (sub-PR 217-1)
**Priority**: P2
**Description**: Identify which of `loading.tsx`, `PipelineGate.tsx:69-73`, or `WizardShell.tsx:773` is the user-visible "in development" flash via `mcp__claude-in-chrome__*` MCP tools (network/Performance trace per `.claude/rules/dev-server-monitoring.md`); replace with Spec 208 brand veil + shadcn/ui `Skeleton` matching the wizard card silhouette. Visible duration ≤200ms p95 warm-cache.

### FR-4a: FE deterministic fallback + screen-advance guard (sub-PR 217-2)
**Priority**: P0 (blocks 90%+ of users from completing onboarding)
**Description**: In `WizardShell.tsx` `case "archetype":`, render shadcn/ui `Alert` with retry CTA after 3-5s if `archetype_cards === null`. Retry click POSTs `/answer` with last user input (idempotent on `(user_id, turn_id)` per existing cache). Alternative: refuse to advance `screenIndex` to `archetype` until `archetype_cards` is non-null in `state.lastResponse`. MUST emit a structured log line on fallback fire so production trigger is observable.

### FR-4b: BE defense-in-depth timeout (sub-PR 217-2)
**Priority**: P1
**Description**: Wrap `pick_three_archetypes(...)` in `asyncio.wait_for(..., timeout=20.0)` at `nikita/api/routes/portal_onboarding.py:1367`; existing `except Exception` already returns `default_archetype_cards`. ~5 LOC.

### FR-4c: Cross-device resume robustness (DEFERRED, OPTIONAL within 217-2)
**Priority**: P3 (deferrable to separate spec if FR-4a sufficient)
**Description**: Add `archetype_cards` to `/state` response shape so page-reload rehydrates them. Defer if FR-4a + FR-4b close the user-visible hang.

### FR-5: Agent emission union (sub-PR 217-3A)
**Priority**: P1
**Description**: Replace `Agent(output_type=[TurnOutput, TurnFailure])` at `conversation_agent.py:266` with `Agent(output_type=[ToolOutput(ReactionOnly, name='emit_reaction'), ToolOutput(FollowUpQuestion, name='ask_followup'), ToolOutput(TurnFailure, name='turn_failure')])`. Each becomes a separate `final_result_*` tool; LLM commits to exactly one per turn. `result.output` is `ReactionOnly | FollowUpQuestion | TurnFailure`; route handler branches via `isinstance`.

### FR-6: `instructions=callable` decision rule (sub-PR 217-3A)
**Priority**: P1
**Description**: Per-turn callable injects (a) the next deterministic question text, (b) `state.missing` slots, (c) decision rule: "If reacting is sufficient (last answer was clear, no signal gap), emit `ReactionOnly`. If a follow-up Q would add meaningful signal AND the next deterministic question is not duplicative, emit `FollowUpQuestion`. NEVER emit a `FollowUpQuestion` whose `question_text` duplicates the next deterministic question."

### FR-7: `@output_validator` mirror guards (sub-PR 217-3A)
**Priority**: P1
**Description**: Validator rejects (a) `FollowUpQuestion.question_text` similar to next deterministic question text per `difflib.SequenceMatcher(None, q1, q2).ratio() > 0.85`, (b) reaction containing user's last answer verbatim (case-insensitive substring). Use `raise ModelRetry(...)` for self-correction. Threshold 0.85 calibrated against 5 hand-crafted near-duplicate + 5 distinct question pairs in `tests/agents/onboarding/fixtures/similarity_calibration.py`.

### FR-8: Sidecar AgentEmissionState (sub-PR 217-3A)
**Priority**: P1
**Description**: New `nikita/agents/onboarding/agent_emission_state.py`: `class AgentEmissionState(BaseModel): pending_followup: FollowUpQuestion | None`. Persisted at `users.onboarding_profile.pending_followup` JSONB column (NOT inside `users.onboarding_profile.slots`). Cleared by setting `null` on followup resolution. `WizardSlots` remains monotonic (`agentic-design-patterns.md` Hard Rule #1).

### FR-9: `/answer` emission dispatch (sub-PR 217-3A)
**Priority**: P1
**Description**: `nikita/api/routes/portal_onboarding.py /answer` dispatches on emission type:
- `ReactionOnly` → `{kind: "reaction", reaction_text}`; do NOT advance slot; clear sidecar.
- `FollowUpQuestion` → `{kind: "followup", payload: ...}`; persist sidecar.
- `TurnFailure` → existing failure path.
- Deterministic answer (no agent emission) → existing slot-advance path.
- `FinalForm.model_validate(state.slots_dict)` completion gate UNCHANGED.

### FR-10a: BE IdentityPair contract (sub-PR 217-3A)
**Priority**: P2
**Description**: `/answer` accepts `{slot: "identity_pair", value: {name: str, age: int}}`. BE applies partial validation: if name valid + age invalid → persist name to `WizardSlots.name`, return `{kind: "field_error", errors: {age: "..."}}` for FE field-level re-prompt.

### FR-10b: FE IdentityPair control (sub-PR 217-3B)
**Priority**: P2
**Description**: `screen-config.ts` declares `IdentityPair` control type. New `IdentityPair.tsx` component renders one shadcn/ui `Card` with two inputs (name `text`, age `number`); single submit button. POSTs to `/answer` per FR-10a. On `field_error` response, show inline error; preserve valid name input value.

### FR-11: Sibling DOM wizard refactor (sub-PR 217-3B)
**Priority**: P0
**Description**: Remove overlay rendering at `WizardShell.tsx:467,542,760-789`. Introduce sibling DOM:
```tsx
<main>
  <DeterministicTrack data-testid="deterministic-card" disabled={state.kind !== "deterministic"}>
    <QuestionCard slot={current} />
  </DeterministicTrack>
  <AgentSubspace data-testid="agent-subspace">
    {state.kind === "reaction" && <ReactionBubble text={state.reaction_text} onDismiss={...} />}
    {state.kind === "followup" && <FollowupCard payload={state.payload} onAnswer={...} />}
  </AgentSubspace>
</main>
```
Both regions use shadcn/ui `Card` + framer-motion `AnimatePresence` + Spec 208 tokens.

### FR-12: Interaction-locking semantics (sub-PR 217-3B)
**Priority**: P1
**Description**:
- `state.kind === "reaction"` → deterministic input REMAINS ENABLED (typing fades the reaction; "Got it" CTA in AgentSubspace as alternative dismissal). NO auto-advance timer.
- `state.kind === "followup"` → deterministic input is `disabled` + `aria-disabled`; followup card is the active input region.
- `state.kind === "deterministic"` → AgentSubspace empty (or shows last reaction as a faded chronological log entry, NEVER as an active input).

### FR-13: FE reducer cumulative-state merge (sub-PR 217-3B)
**Priority**: P1
**Description**: `useConversationState.ts:175 case "server_response"` (per ERRATA) merges by union-of-extractions pattern (`agentic-design-patterns.md` Hard Rule #1). Add discriminated-union dispatch on `response.kind ∈ {deterministic_advance, reaction, followup, field_error}`. NO `setTimeout` auto-advance on reaction state.

### FR-14: 217-0 Prereq cleanup
**Priority**: P2
**Description**:
- 0a: Replace 13 `waitUntil: "networkidle"` calls in `portal/e2e/onboarding.spec.ts` (L43, 56, 69, 81, 96, 112, 124, 152, 179, 192, 226, 242, 272 per ERRATA) with `waitUntil: "domcontentloaded"` + locator polling.
- 0b: DELETE the `test.describe.skip` block at `portal/e2e/onboarding-wizard.spec.ts:24-26`; close GH #364 with comment pointing at PR 217-3B for replacement coverage.
- 0c: `git ls-files portal/src/app/onboarding/auth/` — `git rm -rf` if still tracked. Note per ERRATA: route survives intentionally as 410 GONE stub per PR #538 with TODO `delete-after 2026-06-06` (CL-CODE C1) — verify if delete is truly desired or keep stub.
- 0d: Backfill ROADMAP.md entries for PRs #537/#538/#539 under Spec 216 status.

### FR-15: Pydantic AI `ReinjectSystemPrompt` advisory (sub-PR 217-3A)
**Priority**: P3 (advisory)
**Description**: If 217-3A loads conversation history from DB rather than passing `result.new_messages()` between turns, use `ReinjectSystemPrompt` capability per Phase-2 doc verification (live scrape 2026-05-07 of https://ai.pydantic.dev/message-history/).

---

## User Stories

### US-1: Cold-start tapper (covers FR-1)
**As a** new user with prior Telegram chat history
**I want to** tap a landing CTA and land in Nikita's chat with `/start` already prefilled
**So that** I'm not stuck with a frozen chat and confused
**Acceptance Criteria**:
- AC-1.1: Landing CTA href contains `?start=welcome` query string (verified by URL parse).
- AC-1.2: Telegram chat opens with the "START" button rendered at chat bottom; tap auto-sends `/start welcome`.
- AC-1.3: Nikita's first reply appears within 5s.
- AC-1.4: Append uses `URLSearchParams` API and survives pre-existing UTM tags.
**Priority**: P1

### US-2: iOS PWA gesture survivor (covers FR-2)
**As a** user on iOS Safari standalone PWA + Telegram IAB
**I want to** see a branded interstitial that requires one tap to enter
**So that** my JWT cookie commits and I land in onboarding without a redirect loop
**Acceptance Criteria**:
- AC-2.1: Brand veil (Spec 208 bg-void + AuroraOrbs + "tap to enter") renders on iOS UA.
- AC-2.2: Tap on the surface fires real `click` handler → `router.push(searchParams.get('next') || '/onboarding')`.
- AC-2.3: JWT cookie persists post-advance (verified via `Set-Cookie` parse).
- AC-2.4: On confirmed-non-iOS-non-IAB UA (Chrome desktop), auto-advance fires within ≤100ms.
- AC-2.5: Spoofed/unknown UAs degrade to brand-veil + tap (default-safe).
**Priority**: P1

### US-3: Wizard mounter (covers FR-3, FR-11, FR-12)
**As a** user landing on `/onboarding` after magic-link auth
**I want to** see the wizard card immediately without any "in development" copy flash
**And** see a clean deterministic track + sibling agent subspace (no overlay)
**Acceptance Criteria**:
- AC-3.1: Time-to-first-deterministic-card ≤200ms p95 warm-cache, ≤500ms p95 cold-start (Playwright `performance.getEntriesByType('navigation')[0].domContentLoadedEventEnd`).
- AC-3.2: `expect(page).not.toContainText(/in development|in progress/i)`.
- AC-3.3: `[data-testid="deterministic-card"]` and `[data-testid="agent-subspace"]` are SIBLING DOM nodes.
- AC-3.4: At most one input is focusable at any time across both regions.
- AC-3.5: When `state.kind === "reaction"`, deterministic input is enabled; "Got it" CTA dismisses; no auto-timer.
- AC-3.6: When `state.kind === "followup"`, deterministic input is `disabled` + `aria-disabled`.
**Priority**: P0

### US-4: Backstory escapee (covers FR-4a, FR-4b)
**As a** user reaching the archetype-pick screen
**I want to** never see an indefinite "preparing the three of us…" hang
**So that** I can complete onboarding even when the BE is slow or returns null cards
**Acceptance Criteria**:
- AC-4.1: After 3-5s with `archetype_cards === null`, FE renders `Alert` with retry CTA.
- AC-4.2: Retry click triggers a fresh POST and resolves on cached `(user_id, turn_id)` envelope.
- AC-4.3: BE `pick_three_archetypes` wrapped in `asyncio.wait_for(..., timeout=20.0)`; on timeout `default_archetype_cards` returned.
- AC-4.4: Structured log emitted when fallback fires (`backstory_fallback_fired user_id=<hash> reason=<null_cards|timeout> ...`).
**Priority**: P0

### US-5: Agent emission consumer (covers FR-5, FR-6, FR-7, FR-8, FR-9)
**As an** orchestrator of the wizard
**I want to** receive exactly one of {ReactionOnly, FollowUpQuestion, TurnFailure} per turn
**So that** the FE never has to render a question + reaction overlay
**Acceptance Criteria**:
- AC-5.1: Agent's `output_type=[ToolOutput(ReactionOnly,...), ToolOutput(FollowUpQuestion,...), ToolOutput(TurnFailure,...)]`.
- AC-5.2: `@output_validator` rejects mirror-of-next via `difflib.SequenceMatcher >0.85` and raises `ModelRetry`.
- AC-5.3: `pending_followup` lives in sidecar `AgentEmissionState`, NOT in `WizardSlots`.
- AC-5.4: `WizardSlots.progress_pct` monotonic across followup pending+resolved transitions.
- AC-5.5: `/answer` returns `{kind: "reaction"|"followup"|"deterministic_advance"|"field_error"}` per emission type.
**Priority**: P1

### US-6: Identity-pair filler (covers FR-10a, FR-10b)
**As a** user filling the opener question
**I want to** enter name and age in one card
**So that** I don't have two separate screens for canonical-pair fields
**Acceptance Criteria**:
- AC-6.1: Single `<Card>` renders both inputs + one submit button.
- AC-6.2: BE accepts `{slot: "identity_pair", value: {name, age}}`.
- AC-6.3: Partial valid (name OK, age invalid) → BE persists name + returns `field_error` for age.
- AC-6.4: FE preserves valid name input value on field_error response.
**Priority**: P2

### US-7: Pre-existing test maintainer (covers FR-14)
**As a** developer
**I want to** see networkidle violations + obsolete test.skip blocks removed before new code lands
**So that** subsequent sub-PRs aren't blocked by pre-existing CI noise
**Acceptance Criteria**:
- AC-7.1: All 13 `networkidle` calls replaced with `domcontentloaded` + locator polling.
- AC-7.2: `onboarding-wizard.spec.ts:24-26` test.describe.skip block deleted; GH #364 closed with PR-217-3B reference.
- AC-7.3: ROADMAP.md backfilled for #537/#538/#539.
- AC-7.4: e2e CI green post-cleanup.
**Priority**: P2

---

## Non-Functional Requirements

### NFR-1: Performance
- Time-to-first-deterministic-card ≤200ms p95 warm-cache, ≤500ms p95 cold-start (FR-3 / AC-3.1).
- Backstory pipeline p99 ≤30s OR user-visible failure with retry (FR-4a / AC-4.x).
- Each `/answer` POST p99 ≤25s including the agent run.

### NFR-2: PR-size budget
Each sub-PR ≤400 LOC per `pr-workflow.md`. 217-3A pre-flight check at `git diff --stat origin/master...HEAD` mid-implementation; if >350 LOC, split `@output_validator` (FR-7) and sidecar (FR-8) into 217-3A.1.

### NFR-3: Agentic-design-patterns conformance (HARD GATE)
All 6 hard rules of `.claude/rules/agentic-design-patterns.md` apply to 217-3A:
1. Cumulative server-side state (`WizardSlots` + sidecar `AgentEmissionState`).
2. Pydantic completion gate (`FinalForm.model_validate`, NEVER literal).
3. Tool consolidation (3-tool discriminated union, not N-tool fan-out).
4. Monotonic progress as `@computed_field` of cumulative state.
5. Three-layer validation (pre-tool / `@output_validator` ModelRetry / deterministic post-processing).
6. Official `message_history=` primitive.

### NFR-4: Pydantic AI 1.71.0 syntax
Use `output_type=[A, B]` with `ToolOutput(name=…)` per Phase-2 verified canonical. Do NOT use `result_type=Union[…]` (pre-1.0). Do NOT use `system_prompt=` (reused across `message_history` calls); use `instructions=callable` (re-evaluated per turn).

### NFR-5: Cost / observability
- Backstory pipeline: structured log `backstory_pipeline_timeout user_id=<hash> run_id=<id> stage=<archetype|firecrawl|opus_persona> elapsed_ms=<n>`.
- Backstory fallback fire: `backstory_fallback_fired user_id=<hash> reason=<null_cards|timeout>`.

### NFR-6: Design system (Spec 208)
- bg-void `oklch(0.08 0 0)`, rose `oklch(0.75 0.15 350)`, Geist Sans/Mono, glass-card surfaces, AuroraOrbs, GlowButton, EASE_OUT_QUART, framer-motion `AnimatePresence` opacity+y+blur.
- All new UI built from shadcn/ui primitives: Card, Button, Skeleton, Alert, Input. Wrap landing CTAs with project's `GlowButton`.

### NFR-7: Live testing
12-step canonical walk per `live-testing-protocol.md`: Walk B1 (217-1), Walk B2 (217-2), Walk B3 (217-3 final), Walk B4 (post-final-merge end-to-end). Plus-aliases `simon.yang.ch+walkB{1,2,3,4}@gmail.com`. Anti-fabrication discipline applies.

---

## Constraints & Assumptions

- Solo-dev pre-launch project, zero retained users → NO migration ceremony / cohort-flag clauses (per memory `feedback_no_real_users_no_migration_ceremony.md`).
- 216-A/D/E/F/G/H preserved unchanged. Only 216-B + 216-C superseded.
- Spec 215 FR-6 (iOS PWA gesture) preserved — interstitial route stays, only content reskinned.
- pydantic-graph FSM rejected (`agentic-design-patterns.md` "NOT for linear flows").
- Subagent dispatch caps mandatory: every Agent-tool call MUST include HARD CAP + scope + exit criterion (`parallel-agents.md`).
- Pre-push HARD GATE: `uv run pytest -q` + `(cd portal && npm run test -- --run && npm run lint && npm run build)` before any push (per-sub-PR).
- `/qa-review` zero-tolerance: each sub-PR must pass a fresh-context review returning 0 findings across ALL severities before merge.

---

## Out of Scope

- 216-A (TG canonical routing), 216-D (Big5 + 12 archetypes), 216-E (firecrawl), 216-F (testing infra), 216-G (TG-first landing CTA — except `?start=welcome` payload extension), 216-H (autobind hardening) — preserved.
- Spec 215 FR-6 — preserved.
- Migration / cohort-flag / fallback-flag machinery.
- pydantic-graph FSM.
- Voice agent (`nikita/agents/voice/*`).
- Aggressive slot grouping beyond name+age (city+timezone deferred unless walk-fatigue evidence).
- Spec 216 audit-report.md backlog (4 CRIT + 8 HIGH + 5 MED) **except** items absorbed via the cross-spec audit-backlog overlap pre-check (see spike artifact).

---

## Open Questions

None blocking. All Q1-Q4 user clarifications already resolved per planning brief Operator Handoff section. Slot grouping depth is the sole deferrable (default = name+age; flag in plan phase via `AskUserQuestion` if walk-fatigue evidence emerges).

---

## Subspec Index

| Sub-PR | Slug | FRs | Estimated LOC | Dependency |
|---|---|---|---|---|
| 217-0 | prereq-cleanup | FR-14 | ~150 | (none) — lands first |
| 217-1 | cold-start-cta-interstitial | FR-1, FR-2, FR-3 | ~150 | 217-0 merged |
| 217-2 | backstory-fallback | FR-4a, FR-4b, FR-4c (deferred) | 80-150 (FE-only) | 217-1 merged |
| 217-3A | be-emission-union | FR-5, FR-6, FR-7, FR-8, FR-9, FR-10a, FR-15 | ~250-300 (≤350 cap) | 217-2 merged |
| 217-3B | fe-wizard-refactor | FR-10b, FR-11, FR-12, FR-13 | ~250-300 | 217-3A merged |

Each subspec carries its own `spec.md`, `plan.md`, `tasks.md`, `audit-report.md` at `subspecs/217-<X>-<slug>/`.

---

## Verification Strategy (cross-cutting)

R-series verifications are inherited from the planning brief (R1-R13). Per-sub-PR verifications live in subspec spec.md / tasks.md. Master cross-cutting:

- **R-master-1**: After all 5 sub-PRs merge, run **Walk B4** end-to-end live walk per `live-testing-protocol.md` from `simon.yang.ch+walkB4@gmail.com` exercising the full chain: cold-start CTA → TG `/start welcome` → magic-link → interstitial → wizard with new emission union UI → backstory pipeline → handoff to `/dashboard`. DB cleanup SQL post-walk per protocol template.
- **R-master-2**: GATE 2 validators (`sdd-*-validator` ×6 parallel) MUST pass before any sub-PR `/implement` invocation. See `validation-findings.md`.
- **R-master-3**: ROADMAP-217 entry registered (this spec authoring added it).
