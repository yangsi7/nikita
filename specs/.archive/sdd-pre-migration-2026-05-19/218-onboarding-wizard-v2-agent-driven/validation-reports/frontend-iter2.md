# GATE 2 ITER 2: Frontend Re-Validation — Spec 218

**Spec**: `specs/218-onboarding-wizard-v2-agent-driven/spec.md` (1008 lines, post-iter-1 amendment)
**Timestamp**: 2026-05-09
**Iter-1 verdict**: FAIL (0C / 2H / 4M / 3L)

## Verdict
PASS

## Iter-1 Finding Disposition

| ID | iter-1 finding | iter-2 status | Evidence |
|---|---|---|---|
| HIGH-1 | FR-005 lacked explicit shadcn primitive map for the 8 component shapes | RESOLVED | spec.md:75-84 — table maps each of 8 shapes (`Input+Button`, `Textarea`, `RadioGroup`, `Button[]` toggles, `Slider`, `Calendar+Popover`, `Input+libphonenumber`, reuse `QRHandoff+ClearanceGrantedCeremony`). Includes registry-add command for Textarea. Anti-pattern clause forbids custom-styled `<input>`/`<button>` divs. |
| HIGH-2 | Reusable wizard shells unnamed (single-thread DOM invariant prose-only) | RESOLVED | FR-020 (spec.md:229-245) declares all 7 named components in a table with shadcn primitive mapping: `TurnContainer`, `PhoneOptInModal` (`AlertDialog`), `PhoneDemoTakeover`, `CallingWaveform`, `BackEditConfirmDialog` (`AlertDialog`), `WizardThread`, `DynamicQuestion`. Auditability clause: `WizardThread` MUST render exactly one `TurnContainer` at a time. |
| MEDIUM-1 | FR-010 missing focus-trap + aria-live for full-screen takeover | RESOLVED | spec.md:127-131 — explicit "Trap keyboard focus inside the takeover region" + `aria-live="polite"` announcement + accessible "End early" button with 5s minimum delay. NFR Accessibility (spec.md:284) reinforces. |
| MEDIUM-2 | FR-007 modal text hardcoded for one anchor; AlertDialog primitive unspecified | RESOLVED | spec.md:99 declares shadcn `AlertDialog` primitive. spec.md:105 declares modal text MUST be parameterised by edited slot name + affected downstream slots (NOT hard-coded). |
| MEDIUM-3 | US-5 missing FE scrollback ACs for refreshed multi-turn conversation | RESOLVED | AC-005-004 (spec.md:371) + AC-005-005 (spec.md:372) added — covers N prior turns re-rendered as scrollback in narrator-led layout, plus Phase 1 + Phase 2 mid-turn refresh case. |
| MEDIUM-4 | FR-014 silent on permission-denied path | RESOLVED | spec.md:156-158 — three-branch coverage: API unavailable → toggle hidden; permission denied → inline error + revert to text-only (non-blocking submission); permission later granted → re-engage on next click without page reload. |
| LOW-3 | FR-010 silent on `prefers-reduced-motion` | RESOLVED | spec.md:130 — explicit `prefers-reduced-motion` honour: animated waveform replaced with static phone-icon + "Calling…" text. FR-020 `CallingWaveform` row reinforces. |

## Net-New Findings

None. Spot-checked the amendment scope:
- FR-005 table addition is internally consistent with FR-020 named-shells table (no shape orphaned, no shell maps to a shape outside FR-005).
- FR-007 AlertDialog usage matches FR-020 `BackEditConfirmDialog` primitive declaration.
- FR-010 focus-trap requirement is structurally enforceable via `PhoneDemoTakeover` (FR-020 declares "layout div + focus-trap utility").
- US-5 ACs do not contradict FR-001 single-thread invariant (scrollback is read-only history; only one active `TurnContainer` per FR-020:242).
- LOW-1 (auth FR) and LOW-2 (CORS) from iter-1 were already addressed by FR-019 (spec.md:223-227) and NFR Security (spec.md:265) — no regression.

## Severity Counts (NET)

CRITICAL=0 HIGH=0 MEDIUM=0 LOW=0

## Pass/Fail Criteria

PASS — 0 CRITICAL + 0 HIGH. All iter-1 MEDIUM and LOW findings also resolved. Spec is ready to proceed to Phase 5 (Planning).
