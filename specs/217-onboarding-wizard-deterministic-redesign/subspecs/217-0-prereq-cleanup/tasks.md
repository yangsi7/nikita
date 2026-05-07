# Tasks — Subspec 217-0 Prereq Cleanup

**Parent**: `subspecs/217-0-prereq-cleanup/{spec,plan}.md`
**Phase**: 6
**Date**: 2026-05-07

## TDD Ordering

Cleanup-only PR; no new behavior to TDD. Existing e2e suite IS the regression guard.

## Tasks

- [ ] T-0-1: `git checkout -b chore/217-0-prereq-cleanup` from master HEAD.
- [ ] T-0-2: Run `(cd portal && npm run test -- --run)` BEFORE edits to capture baseline pass.
- [ ] T-0-3: Edit `portal/e2e/onboarding.spec.ts` — replace each of the 13 `waitUntil: "networkidle"` occurrences with `waitUntil: "domcontentloaded"` and add a follow-on locator polling assertion `await expect(<expected-locator>).toBeVisible({ timeout: 10000 })`.
- [ ] T-0-4: Re-run `(cd portal && npx playwright test onboarding.spec.ts)` to verify no regressions; if cold-start flakes, bump timeout to 15s and record in PR body.
- [ ] T-0-5: Edit `portal/e2e/onboarding-wizard.spec.ts:24-26` — delete the `test.describe.skip` block (3 lines).
- [ ] T-0-6: Run `git ls-files portal/src/app/onboarding/auth/`. If non-empty, verify against PR #538 intent + user; if delete confirmed, `git rm -rf portal/src/app/onboarding/auth/`.
- [ ] T-0-7: Append 3 rows to ROADMAP.md for PRs #537, #538, #539 (under Spec 216 status block, with merge dates and PR titles).
- [ ] T-0-8: Pre-push HARD GATE — `(cd portal && npm run test -- --run && npm run lint && npm run build)` + `uv run pytest -q`.
- [ ] T-0-9: `git push -u origin chore/217-0-prereq-cleanup`.
- [ ] T-0-10: `gh pr create --title "chore(217,0): prereq cleanup — networkidle / test.skip / ROADMAP backfill" --body "..."` (body cites this subspec + ACs).
- [ ] T-0-11: `/qa-review --pr <N>` zero-tolerance fresh-context loop until 0 findings ALL severities.
- [ ] T-0-12: Squash merge.
- [ ] T-0-13: `gh issue close 364 --comment "Obsolete test removed in PR #<N>; replacement coverage planned in PR 217-3B (Spec 217 wizard refactor)."`
- [ ] T-0-14: Post-merge verification — re-run `(cd portal && npx playwright test --list onboarding.spec.ts)` against `origin/master`; assert 0 networkidle remain; commit-hash check per `pr-workflow.md` step 9.

## Done Criteria

All 8 ACs from spec.md satisfied. PR merged to master with green CI + 0-finding `/qa-review`.
