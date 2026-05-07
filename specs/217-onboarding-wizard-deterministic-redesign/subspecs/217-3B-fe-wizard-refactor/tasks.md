# Tasks — Subspec 217-3B FE Wizard Refactor

**Parent**: `subspecs/217-3B-fe-wizard-refactor/{spec,plan}.md`
**Phase**: 6
**Date**: 2026-05-07

## TDD Ordering

Strict RED-GREEN-REFACTOR. 217-3A merged before T-3B-1.

## Tasks

- [ ] T-3B-1: `git checkout -b feat/217-3B-fe-wizard-refactor` from master HEAD (post-217-3A merge).
- [ ] T-3B-2 (TEST-RED, AC-T-B.1): Write `portal/src/app/onboarding/_components/__tests__/WizardShell.test.tsx`. Cases: (a) `[data-testid="deterministic-card"].parentNode === [data-testid="agent-subspace"].parentNode`, (b) at-most-one focusable, (c) interaction-locking transitions across `state.kind` values. Run; FAIL.
- [ ] T-3B-3 (TEST-RED, AC-T-B.2): Write `portal/src/app/onboarding/hooks/__tests__/useConversationState.test.ts`. Cases per AC-13.2 (4 dispatch branches) + AC-13.3 (no-setTimeout-on-reaction via `vi.spyOn`). Run; FAIL.
- [ ] T-3B-4 (TEST-RED, AC-T-B.3): Write `portal/src/app/onboarding/_components/__tests__/IdentityPair.test.tsx`. Cases: full-valid POST shape, field_error rendering, valid-name preservation. Run; FAIL.
- [ ] T-3B-5 (IMPL-GREEN, FR-13): Edit `portal/src/app/onboarding/hooks/useConversationState.ts:175` per plan.md sketch. Update `portal/src/app/onboarding/types/{answer,contracts,converse,wizard}.ts` to mirror BE emission union. Run T-3B-3; PASS.
- [ ] T-3B-6 (IMPL-GREEN, FR-11): Create `DeterministicTrack.tsx` + `AgentSubspace.tsx`. Refactor `WizardShell.tsx` — remove overlay (L467, L542, L760-789); mount sibling DOM per plan.md sketch. Run T-3B-2; PASS.
- [ ] T-3B-7 (IMPL-GREEN, FR-12): Add interaction-locking semantics to `<DeterministicTrack disabled>` toggle; "Got it" CTA in `<AgentSubspace>`. Run T-3B-2 again to confirm interaction-locking ACs PASS.
- [ ] T-3B-8 (IMPL-GREEN, FR-10b): Add `IdentityPair` control type to `screen-config.ts`; create `IdentityPair.tsx` per plan.md sketch. Run T-3B-4; PASS.
- [ ] T-3B-9 (FIXTURE UPDATE): Edit `portal/e2e/fixtures/index.ts` to recognize `data-testid="deterministic-card"` + `data-testid="agent-subspace"` + new IdentityPair control in walk-protocol step 9.
- [ ] T-3B-10 (REGRESSION): Run all the failing tests from T-3B-2..4 + full portal vitest suite — all green.
- [ ] T-3B-11 (PRE-PUSH HARD GATE): `(cd portal && npm run test -- --run && npm run lint && npm run build)` + `uv run pytest -q` (no nikita changes; suite still required per `pr-workflow.md`). Record in PR body.
- [ ] T-3B-12: `git push -u origin feat/217-3B-fe-wizard-refactor`.
- [ ] T-3B-13: `gh pr create --title "feat(217,3B): FE wizard refactor — sibling DOM + IdentityPair + reducer" --body "..."`. PR body cites:
   - Spec 217 master + 217-3B subspec
   - Sibling-DOM rationale (resolves user-reported failure #4 overlay bug)
   - 217-3A emission contract consumption
- [ ] T-3B-14: `/qa-review --pr <N>` zero-tolerance fresh-context loop.
- [ ] T-3B-15: Squash merge after CI green + 0-finding fresh review.
- [ ] T-3B-16 (LIVE WALK B3): Per `live-testing-protocol.md` 12-step protocol from `simon.yang.ch+walkB3@gmail.com`. Anti-fabrication discipline mandatory. Capture screenshots of sibling-DOM rendering. DB cleanup SQL post-walk.
- [ ] T-3B-17: Commit-hash verification per `pr-workflow.md` step 9.

## Done Criteria

All 17 ACs from spec.md satisfied; PR merged; Walk B3 PASS with no overlay confirmed.
