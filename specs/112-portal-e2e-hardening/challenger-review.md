# Challenger Review: Spec 112 — Portal E2E Hardening

**Reviewer**: challenger
**Date**: 2026-03-11
**Verdict**: PASS with 1 CRITICAL fix, 4 IMPORTANT notes

---

## CRITICAL Findings

### C1: `page.route()` Cannot Intercept Server-Side Middleware Calls

**Spec reference**: FR-002, Auth Mock Infrastructure
**Spec says**: "Middleware's `getUser()` calls Supabase REST — intercept via `page.route("**/auth/v1/user", ...)` to return a mock user object."
**Problem**: Playwright's `page.route()` intercepts browser-side HTTP requests only. Next.js middleware runs on the server (Node.js edge runtime). When middleware calls `createServerClient()` → `getUser()`, that HTTP request goes from the Next.js server process directly to Supabase — it never passes through the browser's network stack where `page.route()` operates.

**Evidence**: The spec's own Approach A evaluation (line 44) flags this: "Server-side `getUser()` in middleware calls Supabase directly — `page.route()` only intercepts browser-side fetches. Middleware auth bypass needed." But the selected approach (Hybrid A+C, line 78) claims `page.route()` can solve it, contradicting the devil's advocate note.

**Fix options**:
1. **Environment variable bypass**: Add `NEXT_PUBLIC_E2E_MODE=true` env var. In middleware, skip auth check when `E2E_MODE` is set. This is the simplest but weakens security testing.
2. **Test-only middleware override**: Create `middleware.test.ts` that exports a no-auth middleware, swap via Next.js config in test mode.
3. **Dev server with auth disabled**: Run `npm run dev` with env vars that make `getUser()` return a mock user. The `@supabase/ssr` `createServerClient` accepts custom `cookies()` — pre-set valid-looking cookies that the mock auth endpoint will validate.
4. **Accept the limitation**: Run E2E tests against the dev server with real Supabase auth (Approach B for auth only). Auth is already tested in `auth-flow.spec.ts` — the new tests focus on content validation, not auth.

**Recommendation**: Option 3 or 4. The spec must explicitly address how server-side middleware auth is bypassed, not hand-wave it with `page.route()`.

---

## IMPORTANT Findings

### I1: Route Count Discrepancy — 24 vs 25

**Spec reference**: Problem Statement says "24 portal routes exist" but Route Coverage Matrix lists 25 rows (1-25). Coverage summary says "10/25 current -> 25/25 target."
**Fix**: Reconcile — either 24 or 25 routes. Count the actual `page.tsx` files.

### I2: Existing E2E Tests Location Confusion

**Spec reference**: Files to Modify section
**Observation**: The spec references `portal/e2e/dashboard.spec.ts` etc. But the project also has `tests/e2e/portal/` (Python Playwright tests in `test_dashboard.py`, `test_conversations.py`, `test_login_flow.py` at `tests/e2e/portal/`). These are two separate E2E test suites — one TypeScript (portal-native Playwright), one Python (pytest-playwright).

The spec only addresses the TypeScript suite. The Python suite (`tests/e2e/portal/`) has its own page objects, conftest, and fixtures. Are these being deprecated? If both suites continue to exist, there's maintenance duplication.

**Recommendation**: Add a note in Out of Scope or Key Decisions: "Python E2E tests in `tests/e2e/portal/` are [deprecated/complementary/out-of-scope]. This spec targets only `portal/e2e/*.spec.ts`."

### I3: `data-testid` Quota is Arbitrary

**Spec reference**: AC-7.8 "Minimum 60 `data-testid` attributes across portal components"
**Problem**: 60 is an arbitrary number. Currently there are 0 `data-testid` attributes in the portal (verified via `rg 'data-testid' portal/src/` returning empty). The spec should derive the number from actual component count, not pick a round number.

**Recommendation**: Replace AC-7.8 with "Every component referenced by an E2E assertion has a corresponding `data-testid` attribute." This is verifiable and scales with the test suite rather than being a magic number.

### I4: CI Time Budget May Be Unrealistic

**Spec reference**: AC-8.7 "Total CI time increase < 3 minutes"
**Observation**: Playwright install (`npx playwright install --with-deps chromium`) alone takes 30-60s. Starting a Next.js dev server takes 10-20s. Running 25+ spec files with content assertions, network interception, and page rendering can easily exceed 2 minutes on GitHub Actions runners.

Current E2E tests (12 spec files) likely take 60-90s already. Adding 12 new spec files + rewriting 5 existing ones roughly doubles the test count.

**Recommendation**: Either increase the budget to 5 minutes or add "Playwright install time excluded from budget" clarification.

---

## MINOR Findings

### M1: GH Issue #103 Scope Mismatch

GH #103 body mentions "stale docs" but the spec only addresses route coverage and testing. The docs cleanup aspect of #103 is not addressed. Should be noted as out of scope.

### M2: `transitions-export.spec.ts` Not Listed

The existing file `portal/e2e/transitions-export.spec.ts` has the `body?.length > 0` anti-pattern (noted in Problem Statement) but is not listed in Files to Modify. Should be included in FR-004 rewrites.

### M3: No Mention of `mobile-nav.spec.ts`

`portal/e2e/mobile-nav.spec.ts` exists but is not mentioned in the spec. Is it covered? Does it have anti-patterns? Should be audited.

---

## Over-Engineering Check

**Verdict: Borderline.** 12 new test files + 3 fixture files + modifying ~20 portal components + CI changes is a large scope for "test hardening." However, the problem is genuine (0 content validation across 25 routes), and the fix requires this breadth.

**Suggestion**: Consider phasing — Phase A: fixture infrastructure + fix anti-patterns in existing 5 files. Phase B: new route coverage (14 routes). This reduces blast radius per PR and keeps under the 400-line PR limit (CLAUDE.md).

---

## Edge Cases Not Covered

1. **Dynamic routes with invalid IDs**: `/dashboard/conversations/[id]` and `/admin/users/[id]` — what happens when `[id]` is a non-existent UUID? Tests should assert error state rendering, not just happy path.
2. **Empty state rendering**: Many routes may render differently with zero data (no conversations, no vices, no diary entries). The spec mentions `expectNoEmptyState(page)` helper but doesn't specify tests for the empty state path itself.
3. **Auth token expiry during test**: If mock auth tokens have a short TTL and tests are slow, some assertions may fail due to expired sessions. Mock tokens should have long expiry.

---

## Cross-Spec Conflicts with Spec 111

**None.** Spec 112 is portal-only (TypeScript/Next.js). Spec 111 is backend-only (Python/FastAPI). Zero file overlap.

---

## Testability Assessment

All acceptance criteria are testable:
- Factory functions: verify return types via vitest
- Auth mocks: verify cookie setting + route interception
- Content assertions: verify they fail on empty pages
- Anti-pattern removal: `rg ".catch\(\(\) =>"` returns 0
- Route coverage: script audit against `page.tsx` files
- CI: verify GitHub Actions workflow runs

**Strong testability overall.**

---

## Summary

| Priority | Count | Items |
|----------|-------|-------|
| CRITICAL | 1 | C1 (server-side auth not interceptable by `page.route()`) |
| IMPORTANT | 4 | I1 (route count), I2 (two E2E suites), I3 (arbitrary quota), I4 (CI time) |
| MINOR | 3 | M1 (docs scope), M2 (transitions-export missing), M3 (mobile-nav missing) |
| Edge Cases | 3 | Invalid IDs, empty states, token expiry |
