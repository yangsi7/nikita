# Plan — Subspec 217-0 Prereq Cleanup

**Parent**: `subspecs/217-0-prereq-cleanup/spec.md`
**Phase**: 5
**Date**: 2026-05-07

## Architecture

No architectural change. This is a mechanical edit + housekeeping PR.

## Task Breakdown (high-level; full TDD ordering in tasks.md)

1. Read `portal/e2e/onboarding.spec.ts`; replace 13 `waitUntil: "networkidle"` occurrences. Verify e2e suite green locally.
2. Read `portal/e2e/onboarding-wizard.spec.ts:24-26`; delete `test.describe.skip` block.
3. Verify `portal/src/app/onboarding/auth/` state via `git ls-files`; confirm with user if delete intended (or keep as 410 stub per PR #538).
4. Append 3 rows to ROADMAP.md for #537/#538/#539.
5. Pre-push HARD GATE.
6. `gh pr create` → `/qa-review` zero-tolerance loop → squash merge.
7. `gh issue close 364 --comment "..."`.

## Verification

- e2e suite green (warm + cold-start scenarios).
- No regressions in unrelated portal tests.
- ROADMAP.md renders cleanly.

## Risks

| Risk | Mitigation |
|---|---|
| Locator polling timeout (10s) too tight for Cloud Run cold-start | Bump to 15s if first CI run flakes; record in PR body |
| `git rm portal/src/app/onboarding/auth/` accidentally deletes intentional 410 stub | Read PR #538 + ask user before delete |

## Dependencies

None (lands first).
