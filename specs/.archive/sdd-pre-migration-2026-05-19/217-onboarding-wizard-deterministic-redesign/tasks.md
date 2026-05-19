# Tasks — Spec 217 Master Coordination

**Spec ID**: 217-onboarding-wizard-deterministic-redesign
**Phase**: 6 (Tasks)
**Date**: 2026-05-07

This master tasks file is a **coordination index**. Per-sub-PR task lists with TDD ordering live in subspec `tasks.md`. Master tasks below are cross-cutting / orchestrator-owned.

---

## Phase 0 — Pre-flight (orchestrator owns)

- [x] T-M-0.1: ROADMAP-217 entry registered (added during spec authoring 2026-05-07).
- [ ] T-M-0.2: GATE 2 validator dispatch — 6 parallel `Task(subagent_type=sdd-*-validator)` from orchestrator main thread; consume reports into `validation-findings.md`.
- [ ] T-M-0.3: User reviews `validation-findings.md`; resolve CRITICAL/HIGH (max 3 iterations) before any `/implement`.
- [x] T-M-0.4: Verify spike artifact `docs-to-process/20260507-spec217-2-backstory-diagnosis.md` exists with named root cause C5 (already verified).

## Phase 1 — sub-PR 217-0 (prereq cleanup)

See `subspecs/217-0-prereq-cleanup/tasks.md`. Summary:
- 13 `networkidle` → `domcontentloaded` + locator polling.
- DELETE `onboarding-wizard.spec.ts:24-26` test.describe.skip block; close GH #364.
- `git rm -rf portal/src/app/onboarding/auth/` IF still tracked AND user confirms (verify against PR #538 410-GONE intentional sunset).
- ROADMAP backfill for #537/#538/#539.
- Pre-push gate + `/qa-review` zero-tolerance + squash merge.

## Phase 2 — sub-PR 217-1 (cold-start CTA + interstitial reskin + loading flash)

See `subspecs/217-1-cold-start-cta-interstitial/tasks.md`. Summary:
- Append `?start=welcome` to landing CTAs via `URLSearchParams`.
- Reskin `InterstitialClient.tsx` (Spec 208 brand veil + UA-default-safe auto-advance + `router.prefetch`).
- Diagnose + remediate loading flash (Skeleton + brand veil).
- Add UA fixture `portal/e2e/auth-interstitial-pwa.spec.ts` (3 UA cases).
- Walk B1 + DB cleanup post-walk.

## Phase 3 — sub-PR 217-2 (backstory fallback)

See `subspecs/217-2-backstory-fallback/tasks.md`. Summary:
- `WizardShell.tsx` `case "archetype":` deterministic fallback per spike root cause C5.
- BE 5-LOC `asyncio.wait_for` defense-in-depth at `portal_onboarding.py:1367`.
- Structured log emission on fallback fire.
- New vitest `_components/__tests__/WizardShell.archetype-fallback.test.tsx`.
- Walk B2 + DB cleanup.

## Phase 4 — sub-PR 217-3A (BE emission union)

See `subspecs/217-3A-be-emission-union/tasks.md`. Summary:
- Define `ReactionOnly`, `FollowUpQuestion`, `TurnFailure` (refactor) in `converse_contracts.py`.
- Wire `Agent(output_type=[ToolOutput(...), ...])`.
- `instructions=callable` decision rule.
- `@output_validator` mirror-of-next + mirror-echo via `difflib.SequenceMatcher >0.85`.
- Sidecar `AgentEmissionState` + `users.onboarding_profile.pending_followup` JSONB persistence.
- `/answer` dispatch on emission kind.
- IdentityPair contract (BE side).
- Calibration fixture `tests/agents/onboarding/fixtures/similarity_calibration.py`.
- Pre-flight LOC check; split into 217-3A.1 if >350.
- Pre-push gate + `/qa-review`.

## Phase 5 — sub-PR 217-3B (FE wizard refactor)

See `subspecs/217-3B-fe-wizard-refactor/tasks.md`. Summary:
- Sibling-DOM `<DeterministicTrack>` + `<AgentSubspace>` components.
- Remove overlay rendering at `WizardShell.tsx:467,542,760-789`.
- Interaction-locking (deterministic enabled during reaction, locked during followup).
- `IdentityPair.tsx` compound control + `screen-config.ts` extension.
- `useConversationState.ts:175` discriminated-union dispatch.
- vitest `WizardShell.test.tsx` sibling-DOM assertion.
- Walk B3 + DB cleanup.

## Phase 6 — Post-final-merge integration

- [ ] T-M-6.1: Walk B4 — full chain end-to-end from `simon.yang.ch+walkB4@gmail.com`. Report at `audits/2026/{YYYYMMDD}-walk-B4-spec217-integration.md`.
- [ ] T-M-6.2: ROADMAP sync — mark 217 status COMPLETE; mark 216-B/216-C SUPERSEDED-BY-217.
- [ ] T-M-6.3: `specs/INDEX.md` update.

---

## Task ID Convention

- `T-M-N.M` — master coordination task
- `T-{0|1|2|3A|3B}-N.M` — subspec-specific task (in subspec tasks.md)
