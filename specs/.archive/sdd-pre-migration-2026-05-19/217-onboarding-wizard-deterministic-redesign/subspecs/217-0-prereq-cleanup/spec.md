# Subspec 217-0 — Prereq Cleanup

**Parent**: `specs/217-onboarding-wizard-deterministic-redesign/spec.md` FR-14
**PR boundary**: 217-0 (lands first)
**Estimated**: ~150 LOC (e2e fix + delete + ROADMAP backfill)
**Status**: Draft (GATE 1)

---

## Scope

Pre-flight cleanup that must land before any of 217-1/2/3A/3B branches off master. Closes pre-existing CI noise + housekeeping that would otherwise pollute downstream PR reviews.

1. **Networkidle violations**: Replace 13 `waitUntil: "networkidle"` calls in `portal/e2e/onboarding.spec.ts` (L43, 56, 69, 81, 96, 112, 124, 152, 179, 192, 226, 242, 272 per ERRATA) with `waitUntil: "domcontentloaded"` + `expect(locator).toBeVisible({ timeout: 10000 })` polling. Reason: `networkidle` is brittle on Cloud Run cold-starts + framer-motion in-flight animations and consistently flakes the suite.
2. **Obsolete test.skip**: DELETE the `test.describe.skip` block at `portal/e2e/onboarding-wizard.spec.ts:24-26`. Close GH #364 with a comment pointing at PR 217-3B for replacement coverage (the 216-B/C architecture it tested is being superseded; fresh tests live in the 217-3B vitest suite).
3. **Hygiene check**: `git ls-files portal/src/app/onboarding/auth/` — if files are still tracked AND user confirms intent, `git rm -rf` them. NOTE: per ERRATA, the route currently survives intentionally as a 410 GONE stub per PR #538 with TODO `delete-after 2026-06-06` (CL-CODE C1). Verify intent against PR #538 before deletion; if user wants to keep the stub, this task is a no-op.
4. **ROADMAP backfill**: Add ROADMAP.md entries for PRs #537/#538/#539 under Spec 216 status block.

## Acceptance Criteria

| AC | Description | Severity |
|---|---|---|
| AC-0.1 | All 13 `networkidle` occurrences in `onboarding.spec.ts` replaced with `domcontentloaded` + locator polling | HIGH |
| AC-0.2 | `onboarding-wizard.spec.ts:24-26` test.describe.skip block deleted | HIGH |
| AC-0.3 | GH #364 closed with comment `Obsolete test removed in PR #<N>; replacement coverage planned in PR 217-3B` | MEDIUM |
| AC-0.4 | If `portal/src/app/onboarding/auth/` deletion is confirmed, `git ls-files portal/src/app/onboarding/auth/` returns empty post-merge | MEDIUM (conditional) |
| AC-0.5 | ROADMAP.md contains rows for #537, #538, #539 under Spec 216 (or near it) with merge dates | LOW |
| AC-0.6 | `(cd portal && npx playwright test --list onboarding.spec.ts)` lists 0 networkidle waits via inspection | HIGH |
| AC-0.7 | Pre-push HARD GATE green: `(cd portal && npm run test -- --run && npm run lint && npm run build)` + `uv run pytest -q` (no Python diff so suite should be untouched but still run per `pr-workflow.md`) | HIGH |
| AC-0.8 | `/qa-review --pr <N>` returns 0 findings across ALL severities via fresh-context loop | HIGH |

## Files Touched

- `portal/e2e/onboarding.spec.ts` (13 line edits)
- `portal/e2e/onboarding-wizard.spec.ts:24-26` (deletion)
- `portal/src/app/onboarding/auth/*` (conditional `git rm`)
- `ROADMAP.md` (3-row backfill)

## Test Inventory

- Existing `portal/e2e/onboarding.spec.ts` test cases — must continue to pass after networkidle replacement (proxy assertion: locator polling timeout 10s should be sufficient for cold-start Cloud Run target).
- New: NONE (cleanup-only sub-PR; no new behavior).

## Out of Scope

- Any wizard / interstitial / agent code changes — those live in 217-1/2/3A/3B.
- Refactoring of the existing onboarding e2e test suite beyond the networkidle fixes.
