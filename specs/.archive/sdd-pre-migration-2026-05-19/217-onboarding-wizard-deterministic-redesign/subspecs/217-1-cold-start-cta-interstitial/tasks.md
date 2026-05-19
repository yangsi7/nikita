# Tasks — Subspec 217-1 Cold-Start CTA + Interstitial + Loading Flash

**Parent**: `subspecs/217-1-cold-start-cta-interstitial/{spec,plan}.md`
**Phase**: 6
**Date**: 2026-05-07

## TDD Ordering (per `pr-workflow.md` + project TDD)

1. Write failing test FIRST → fails for the right reason.
2. Minimal implementation → green.
3. Commit tests separately from impl per CLAUDE.md SDD Enforcement #4.

## Tasks

- [ ] T-1-1: `git checkout -b feat/217-1-cold-start-cta-interstitial` from master HEAD (post-217-0 merge).
- [ ] T-1-2 (TEST-RED): Write `portal/e2e/auth-interstitial-pwa.spec.ts` — 3 UA cases (desktop Chrome auto-advance ≤100ms, iOS Safari brand-veil + tap, Telegram IAB UA brand-veil + tap). Run; ALL must FAIL (interstitial currently has different copy).
- [ ] T-1-3 (TEST-RED): Write `portal/src/app/onboarding/_components/__tests__/loading-flash.test.tsx` vitest asserting `expect(<onboarding loading state>).not.toContainText(/in development|in progress/i)` AND `<Skeleton>` is rendered. Run; FAIL.
- [ ] T-1-4 (TEST-RED): Write `portal/src/components/landing/__tests__/cta-href.test.tsx` vitest asserting `hero-section`, `cta-section`, `login/page-client` (unauth) ctaHrefs all contain `?start=welcome` via URL parse. Run; FAIL.
- [ ] T-1-5 (IMPL-GREEN — FR-1): Edit `portal/src/components/landing/hero-section.tsx:24`, `portal/src/components/landing/cta-section.tsx:17`, `portal/src/app/login/page-client.tsx:31` per plan.md sketch. Run T-1-4; PASS.
- [ ] T-1-6 (IMPL-GREEN — FR-2): Edit `portal/src/app/auth/interstitial/page.tsx` (server UA via `userAgent()`); rewrite `portal/src/app/auth/interstitial/InterstitialClient.tsx` per plan.md sketch. Run T-1-2; PASS for all 3 UA cases.
- [ ] T-1-7 (IMPL-GREEN — FR-3): Identify loading-flash source via Chrome MCP DevTools cold-`/onboarding` trace; replace flash surface with `<Skeleton>` + brand veil. Document trace findings in PR body. Run T-1-3; PASS.
- [ ] T-1-8 (REGRESSION): Re-run existing portal vitest + e2e suites — all green.
- [ ] T-1-9 (PRE-PUSH HARD GATE): `(cd portal && npm run test -- --run && npm run lint && npm run build)`. Record in PR body `## Local tests` section.
- [ ] T-1-10: `git push -u origin feat/217-1-cold-start-cta-interstitial`.
- [ ] T-1-11: `gh pr create --title "feat(217,1): cold-start CTA + interstitial reskin + loading-flash fix" --body "..."` (body cites this subspec + ACs + flash trace findings).
- [ ] T-1-12: `/qa-review --pr <N>` zero-tolerance fresh-context loop.
- [ ] T-1-13: Squash merge after CI green + 0-finding fresh review.
- [ ] T-1-14 (LIVE WALK B1): Per `live-testing-protocol.md` 12-step protocol from `simon.yang.ch+walkB1@gmail.com`. Anti-fabrication discipline applies (NEVER `INSERT INTO auth.users`, NEVER `signInWithPassword`, NEVER `E2E_AUTH_BYPASS`). Capture artifacts. DB cleanup SQL post-walk.
- [ ] T-1-15: Commit-hash verification per `pr-workflow.md` step 9.

## Done Criteria

All 18 ACs from spec.md satisfied; PR merged; Walk B1 PASS.
