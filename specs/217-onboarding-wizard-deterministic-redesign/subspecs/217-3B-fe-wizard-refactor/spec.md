# Subspec 217-3B — FE Wizard Refactor (Sibling DOM + IdentityPair + Reducer)

**Parent**: `specs/217-onboarding-wizard-deterministic-redesign/spec.md` FR-10b, FR-11, FR-12, FR-13
**PR boundary**: 217-3B (depends on 217-3A merged — consumes the BE emission contract)
**Estimated**: 250-300 LOC (≤400 cap)
**Status**: Draft (GATE 1)

---

## Scope

Refactors the wizard FE to consume the new BE emission contract from 217-3A:

1. **Sibling DOM regions** `<DeterministicTrack>` + `<AgentSubspace>` — REMOVE the overlay rendering at `WizardShell.tsx:467,542,760-789` (root cause of user-reported failure #4).
2. **Interaction-locking** semantics: deterministic input REMAINS ENABLED during `state.kind === "reaction"` (preserves momentum); `disabled` during `state.kind === "followup"` (preserves "never two active inputs" rule).
3. **IdentityPair compound control** — name+age in one card; honors BE `field_error` partial-validation contract from 217-3A FR-10a.
4. **Reducer discriminated-union dispatch** — `useConversationState.ts:175 case "server_response"` branches on `response.kind ∈ {deterministic_advance, reaction, followup, field_error}`. NO `setTimeout` auto-advance on reaction state.

## Acceptance Criteria

### Sibling DOM (FR-11)

| AC | Description | Severity |
|---|---|---|
| AC-11.1 | New components: `portal/src/app/onboarding/_components/DeterministicTrack.tsx`, `AgentSubspace.tsx` | HIGH |
| AC-11.2 | `WizardShell.tsx` overlay rendering at L467 (`reactionText`), L542 (`<NikitaReaction>`), L760-789 (control rendering) REMOVED; replaced with sibling DOM per master plan.md §3.2 | CRITICAL |
| AC-11.3 | `[data-testid="deterministic-card"]` and `[data-testid="agent-subspace"]` are SIBLING DOM nodes — verified by vitest assertion `el.parentNode === other.parentNode` | CRITICAL |
| AC-11.4 | Both regions use shadcn/ui `Card` + framer-motion `AnimatePresence` (opacity+y+blur) per Spec 208 design system | HIGH |

### Interaction locking (FR-12)

| AC | Description | Severity |
|---|---|---|
| AC-12.1 | `state.kind === "reaction"` → `<DeterministicTrack disabled={false}>` (input REMAINS ENABLED); typing fades the reaction; "Got it" CTA in `AgentSubspace` as alternative dismissal; NO `setTimeout` auto-timer | HIGH |
| AC-12.2 | `state.kind === "followup"` → `<DeterministicTrack disabled={true} aria-disabled="true">`; followup card is the active input region | HIGH |
| AC-12.3 | `state.kind === "deterministic"` → `<AgentSubspace>` empty (or shows last reaction as a faded chronological log entry, NEVER as an active input) | MEDIUM |
| AC-12.4 | At most ONE input is focusable at any time across both regions — verified by vitest assertion enumerating `:focusable` and counting | HIGH |

### IdentityPair (FR-10b)

| AC | Description | Severity |
|---|---|---|
| AC-10b.1 | `screen-config.ts` declares `IdentityPair` control type | HIGH |
| AC-10b.2 | New `portal/src/app/onboarding/_components/IdentityPair.tsx` — single shadcn/ui `Card` with two inputs (name `text`, age `number`) + one submit button | HIGH |
| AC-10b.3 | Submit POSTs `/api/v1/onboarding/answer` with `{slot: "identity_pair", value: {name, age}}` | HIGH |
| AC-10b.4 | On `field_error` response (per 217-3A AC-10a.2), inline error renders next to the offending field; valid name input value preserved | HIGH |

### Reducer (FR-13)

| AC | Description | Severity |
|---|---|---|
| AC-13.1 | `useConversationState.ts:175 case "server_response"` (per ERRATA L175, NOT brief's L169-173) merges by union-of-extractions pattern (cumulative state) — `agentic-design-patterns.md` Hard Rule #1 | HIGH |
| AC-13.2 | Discriminated-union dispatch on `response.kind ∈ {deterministic_advance, reaction, followup, field_error}` produces correct `state.kind` transition | HIGH |
| AC-13.3 | NO `setTimeout` invoked on reaction state (assert via vitest `vi.spyOn(global, "setTimeout")` count == baseline) | HIGH |

### Test coverage

| AC | Description | Severity |
|---|---|---|
| AC-T-B.1 | New vitest `portal/src/app/onboarding/_components/__tests__/WizardShell.test.tsx` — sibling-DOM assertion + at-most-one-focusable + interaction-locking transitions | CRITICAL |
| AC-T-B.2 | New vitest `portal/src/app/onboarding/hooks/__tests__/useConversationState.test.ts` — discriminated-union dispatch test cases per AC-13.2 + no-auto-advance assertion per AC-13.3 | HIGH |
| AC-T-B.3 | New vitest `portal/src/app/onboarding/_components/__tests__/IdentityPair.test.tsx` — full-valid + partial-error rendering | HIGH |

### Verification

| AC | Description | Severity |
|---|---|---|
| AC-V-B.1 | Pre-push HARD GATE — full portal vitest + lint + build green | HIGH |
| AC-V-B.2 | `/qa-review --pr <N>` zero-tolerance fresh-context loop | HIGH |
| AC-V-B.3 | Live Walk B3 from `simon.yang.ch+walkB3@gmail.com` per `live-testing-protocol.md` 12-step protocol — full chain incl. new emission UI; anti-fabrication discipline; DB cleanup post-walk | HIGH |

## Files Touched (Reuse Map)

| File | Action |
|---|---|
| `portal/src/app/onboarding/_components/WizardShell.tsx` | REMOVE overlay; mount sibling DOM |
| `portal/src/app/onboarding/_components/DeterministicTrack.tsx` | NEW |
| `portal/src/app/onboarding/_components/AgentSubspace.tsx` | NEW |
| `portal/src/app/onboarding/_components/IdentityPair.tsx` | NEW |
| `portal/src/app/onboarding/_components/screen-config.ts` | Add `IdentityPair` control type |
| `portal/src/app/onboarding/hooks/useConversationState.ts:175` | Discriminated-union dispatch on `response.kind` |
| `portal/src/app/onboarding/types/{ControlSelection,answer,contracts,converse,wizard}.ts` | Mirror BE emission contract from 217-3A |
| `portal/src/app/onboarding/_components/__tests__/WizardShell.test.tsx` | NEW |
| `portal/src/app/onboarding/hooks/__tests__/useConversationState.test.ts` | NEW |
| `portal/src/app/onboarding/_components/__tests__/IdentityPair.test.tsx` | NEW |
| `portal/e2e/fixtures/index.ts` | Update walk-protocol step 9 to recognize new data-testids |

## Out of Scope

- BE emission contract definition (217-3A — already merged before this PR).
- Cold-start CTA / interstitial / loading flash (217-1).
- Backstory hang (217-2).
- Voice agent.
