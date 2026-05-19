# Challenger Plan Review: Spec 112

**Reviewer**: challenger
**Date**: 2026-03-11
**Verdict**: PASS with 2 IMPORTANT items

---

## Spec Fix Verification

Critical finding from spec review was addressed:
- C1: Auth strategy reworked from `page.route()` to env-gated middleware bypass (`E2E_AUTH_BYPASS` + `E2E_AUTH_ROLE`). Verified in spec.md lines 84-87. The middleware at `portal/src/lib/supabase/middleware.ts:29` calls `supabase.auth.getUser()` server-side — the bypass must insert an early return before this call.

---

## Plan Quality Assessment

### Strengths

1. **Two-phase split is smart**: Phase A (575 lines) and Phase B (460 lines) both stay under the 400-line PR limit mentioned in CLAUDE.md. Wait — Phase A is 575 lines, which exceeds 400. See IMPORTANT finding below.
2. **Auth bypass is clean**: Server-side env var (`E2E_AUTH_BYPASS`, not `NEXT_PUBLIC_`) prevents accidental browser-side exposure. Two Playwright projects with separate ports/roles is idiomatic.
3. **Anti-pattern fixes are comprehensive**: All 15 `.catch(() => false)` instances (verified in codebase), both `toBeGreaterThanOrEqual(0)` instances, and the `transitions-export` body length check are listed.
4. **TDD for meta-tests**: US-6 (vitest tests for factories/assertions) is listed as "written BEFORE US-2" — correct TDD ordering.
5. **Dependency graph is logical**: US-1 → US-2 → US-3 makes sense. US-4 before US-3 is correct (need `data-testid` before assertions reference them).

### IMPORTANT Findings

**I1: Phase A Exceeds 400-Line PR Limit**

Phase A estimates 575 lines. CLAUDE.md says "Max 400 lines per PR." Either:
1. Split Phase A into two PRs (A1: infrastructure US-1/2/4/5/6, A2: anti-pattern rewrites US-3)
2. Accept the overage since test-only changes have lower review risk

**Recommendation**: Split into A1 (infrastructure: ~385 lines) and A2 (rewrites: ~200 lines). This also de-risks the approach — infrastructure lands first, rewrites can be validated independently.

**I2: Two webServers May Cause CI Port Conflicts**

Plan says: "player (port 3003) + admin (port 3004) projects with separate webServers."
Current Playwright config uses a single `webServer`. Running two simultaneous Next.js dev servers on different ports in CI may:
- Double memory usage on GitHub Actions runners (Next.js dev server ~500MB each)
- Cause startup race conditions if both try to compile simultaneously

**Alternative**: Use a single webServer. Switch auth role per test file by restarting with different env vars, OR use `test.use({ storageState: ... })` per project without separate servers. The middleware bypass reads `E2E_AUTH_ROLE` at request time — could this be a request header instead of an env var? E.g., `x-e2e-role: admin` header intercepted by middleware.

**Recommendation**: Consider the header approach — single server, role set per request via `page.setExtraHTTPHeaders()`. This is simpler than two servers.

---

### MINOR Findings

**M1: US-6 TDD Ordering Contradiction**

Dependencies say "US-6 written BEFORE US-2 (TDD — tests first)" but US-6 tests factory functions and assertion helpers that are defined in US-2. You can't write tests for functions that don't have TypeScript signatures yet. Options:
- Write interface/type definitions first (T2.1 types only), then US-6 tests, then US-2 implementations
- Write stub implementations that throw `not implemented`, then US-6 tests, then real implementations
- Accept that for infrastructure code, writing tests after stubs is pragmatic

This is a minor process point, not a blocker.

**M2: `mobile-nav.spec.ts` Audit Scope Unclear**

T3.6 says "Audit + fix `mobile-nav.spec.ts`" without specifying known anti-patterns. If no anti-patterns exist, this task may produce zero changes. Add "if no anti-patterns found, mark as no-op" to avoid wasted effort.

**M3: Phase B Invalid ID Tests Missing from Task Count**

T7.4, T8.3, T8.4 mention "(happy + error)" or "(happy path + invalid ID error state)" but the task count in the plan summary says "27 tasks." The error-state variants should be explicit sub-tasks or at minimum noted as test cases within the task.

---

## Alternative Approach: Single Server + Header-Based Role

```
Current plan:                     Alternative:
┌─────────────────┐               ┌─────────────────┐
│ Server A :3003  │               │ Server :3003    │
│ ROLE=player     │               │ ROLE from header│
├─────────────────┤               │                 │
│ Server B :3004  │               │ x-e2e-role:     │
│ ROLE=admin      │               │ player | admin  │
└─────────────────┘               └─────────────────┘

Pro: Simpler CI, half memory     Con: Header leak risk (mitigated
Pro: No port conflicts            by gating on E2E_AUTH_BYPASS env)
Pro: Faster startup
```

---

## TDD Correctness

| Story | Tests First? | Implementation After? | Notes |
|-------|-------------|----------------------|-------|
| US-1 (Auth) | No explicit tests | Config change | Acceptable — config tested implicitly by all E2E tests |
| US-2 (Fixtures) | US-6 first (sort of) | Yes | See M1 ordering note |
| US-3 (Rewrites) | Rewriting tests = tests first | Yes | Tests ARE the deliverable |
| US-4 (data-testid) | No tests needed | N/A | Instrumenting components, tested by US-3/7/8 |
| US-5 (CI) | No tests | Config change | Tested by CI run itself |
| US-6 (Meta) | N/A | N/A | These ARE the tests |
| US-7-8 (Routes) | Tests ARE the deliverable | N/A | Writing new E2E tests |
| US-9 (data-testid) | No tests needed | N/A | Tested by US-7/8 |

TDD is less applicable to a testing spec — the deliverables are tests themselves.

---

## Summary

| Priority | Count | Items |
|----------|-------|-------|
| CRITICAL | 0 | — |
| IMPORTANT | 2 | I1 (Phase A exceeds 400-line limit), I2 (two webServers in CI) |
| MINOR | 3 | M1 (US-6 TDD ordering), M2 (mobile-nav scope), M3 (error test sub-tasks) |
