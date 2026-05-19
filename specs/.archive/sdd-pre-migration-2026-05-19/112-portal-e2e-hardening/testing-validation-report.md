## Testing Validation Report

**Spec:** `/Users/yangsim/Nanoleq/sideProjects/nikita/specs/112-portal-e2e-hardening/spec.md`
**Status:** PASS
**Timestamp:** 2026-03-11T12:00:00Z

### Summary
- CRITICAL: 0
- HIGH: 0
- MEDIUM: 4
- LOW: 3

### Findings

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| MEDIUM | Coverage Target | No numeric coverage percentage target specified (e.g., "80% line coverage"). Spec targets 25/25 route coverage but lacks vitest unit test coverage thresholds for portal components. | spec.md:188-194 (NFRs) | Add a measurable coverage target: e.g., "vitest coverage >= 70% lines for portal/src/lib/ and portal/src/hooks/; E2E: 25/25 routes with content assertions." |
| MEDIUM | Testing Pyramid | The spec is E2E-heavy by nature but the vitest "meta tests" (US-6) cover only factory and assertion helper functions (~60 lines). No vitest page-level component tests are defined despite Approach C being part of the hybrid selection. | spec.md:76-78 (Hybrid A+C), plan.md:37-39 (US-6) | Either (a) add explicit vitest component-level test tasks for key pages (dashboard, admin) validating render output with mocked data, or (b) remove the Approach C claim from the rationale and acknowledge this is an E2E-first spec. The hybrid claim without vitest page tests is misleading. |
| MEDIUM | Mock Drift | No strategy for detecting when mock factory data drifts from real API response schemas. Factories are typed in TS, but API schemas evolve on the Python backend side. | spec.md:93-101 (FR-001) | Add a contract validation mechanism: either (a) a CI step that exports backend OpenAPI schema and validates factory types against it, or (b) a documented manual review checklist for factory updates when API endpoints change. |
| MEDIUM | Test Isolation | `waitForPageSettled` in current fixtures.ts uses `catch {}` to swallow timeout errors (line 80). The spec identifies `.catch(() => false)` as an anti-pattern in test assertions but the existing fixture helper `waitForPageSettled` uses the same pattern. | portal/e2e/fixtures.ts:80 | AC-4.5 says "zero `.catch(() =>` patterns remain in portal/e2e/". The `waitForPageSettled` helper and `hasSidebarNav` helper (line 90) both use `.catch()`. Ensure T2.5 (fixture refactor) explicitly addresses these two instances. |
| LOW | CI Timing | AC-8.7 specifies "Total CI time increase < 5 minutes" but no mechanism to enforce or measure this is defined. | spec.md:186 | Add a CI step annotation or comment noting expected timing. Consider `timeout-minutes: 8` on the e2e job as a hard guard. |
| LOW | Error Scenario Coverage | Dynamic route tests (T7.4, T8.3, T8.4) include "invalid ID" error states, which is good. However, network failure scenarios (API timeout, 500 responses) are not explicitly tested for any route. | plan.md:46-52 (US-7, US-8) | Consider adding 1-2 tests that use `page.route()` to return 500 status for API calls, verifying error-state UI renders correctly. This would validate the error-state `data-testid` attributes from FR-007. |
| LOW | Browser Matrix | Only Chromium is specified (single project). No cross-browser requirement is documented or explicitly excluded. | spec.md:111 (AC-2.4), playwright.config.ts:29 | Acceptable for a hardening spec focused on assertion quality. Document the single-browser decision in a KDD or NFR so future readers know it was intentional. |

### Testing Pyramid Analysis

```
Target (standard):          Spec 112 (actual):
    /\                          /\
   / E2E\  10%                / E2E \  ~85%  (25 route specs)
  /------\                   /--------\
 / Integ  \ 20%             / Meta-unit \ ~15% (factory + assertion vitest)
/----------\                /------------\
/ Unit      \ 70%          (no component-level vitest tests)
```

**Assessment:** The pyramid is inverted, but this is **expected and acceptable** for a spec whose explicit purpose is E2E hardening. The spec correctly identifies this as a testing-infrastructure spec, not a feature spec. The meta-test layer (US-6: vitest tests for factories and helpers) provides the "unit" tier for the test infrastructure itself. The only concern is the hybrid A+C claim without substantial vitest page-level tests (see MEDIUM finding #2).

### AC Testability Analysis

| AC ID | AC Description | Testable | Test Type | Issue |
|-------|----------------|----------|-----------|-------|
| AC-1.1 | Factory functions exported | Yes | Unit (vitest) | None |
| AC-1.2 | Factories return typed objects | Yes | Unit (vitest) | None |
| AC-1.3 | Factories accept partial overrides | Yes | Unit (vitest) | None |
| AC-1.4 | mockApiRoutes helper | Yes | Integration (E2E) | None |
| AC-2.1 | Middleware env-gated bypass | Yes | Integration (E2E) | None |
| AC-2.2 | Mock player user shape | Yes | Unit (vitest) | None |
| AC-2.3 | Mock admin user shape | Yes | Unit (vitest) | None |
| AC-2.4 | Two Playwright projects | Yes | Config validation | None |
| AC-2.5 | No NEXT_PUBLIC_ prefix | Yes | Grep/lint | None |
| AC-2.6 | Production guard | Yes | Unit (vitest) | None |
| AC-2.7 | Role-based route visibility | Yes | E2E | None |
| AC-3.1 | Assertion helpers exported | Yes | Unit (vitest) | None |
| AC-3.2 | data-testid selectors only | Yes | Grep/lint | None |
| AC-3.3 | No .catch(() => false) in helpers | Yes | Grep | None |
| AC-3.4 | Explicit timeout + error messages | Yes | Unit (vitest) | None |
| AC-4.1 | Remove .catch patterns | Yes | Grep (rg) | None |
| AC-4.2 | Replace triple-OR | Yes | Grep (rg) | None |
| AC-4.3 | Replace >=0 | Yes | Grep (rg) | None |
| AC-4.4 | All rewritten tests use mockApiRoutes | Yes | Code review | None |
| AC-4.5 | Zero .catch patterns remain | Yes | Grep (rg) | Existing fixtures.ts also has .catch |
| AC-5.1-5.6 | Player route coverage | Yes | E2E | None |
| AC-6.1-6.6 | Admin route coverage | Yes | E2E | None |
| AC-7.1-7.8 | data-testid attributes | Yes | E2E + grep | None |
| AC-8.1-8.7 | CI integration | Yes | CI run | AC-8.7 timing target not enforceable |

### Test Scenario Inventory

**E2E Scenarios:**

| Scenario | Priority | User Flow | Status |
|----------|----------|-----------|--------|
| Dashboard content validation | P0 | Player views score ring, charts | Defined (T3.1 rewrite) |
| Data-viz chart content | P0 | Player views engagement charts | Defined (T3.2 rewrite) |
| Admin user table content | P0 | Admin views user list | Defined (T3.3 rewrite) |
| Player pages content | P0 | Player views vices, conversations, settings | Defined (T3.4 rewrite) |
| Nikita hub + sub-pages | P1 | Player navigates nikita/mind/circle/day/stories | Defined (T7.1) |
| Insights page | P1 | Player views insight cards | Defined (T7.2) |
| Diary page | P1 | Player views diary entries | Defined (T7.3) |
| Conversation detail | P1 | Player views message thread | Defined (T7.4) |
| Admin pipeline | P1 | Admin views stage timings | Defined (T8.1) |
| Admin jobs | P1 | Admin views job list | Defined (T8.2) |
| Admin conversation detail | P1 | Admin views pipeline events | Defined (T8.3) |
| Admin user detail | P1 | Admin views user metrics | Defined (T8.4) |
| Admin text/voice pages | P1 | Admin views text/voice sessions | Defined (T8.5) |
| Transitions export content | P1 | Player exports transitions | Defined (T3.5 fix) |
| Mobile nav | P2 | Mobile viewport navigation | Defined (T3.6 audit) |
| Auth flow (existing) | P0 | Login, callback, redirect | Existing (no changes) |
| Accessibility (existing) | P2 | ARIA, keyboard nav | Existing (no changes) |

**Integration Test Points:**

| Component | Integration Point | Mock Required |
|-----------|-------------------|---------------|
| Middleware auth bypass | E2E_AUTH_BYPASS env var | Env var injection (not mock) |
| API data rendering | page.route() interceptors | Yes - factory data via mockApiRoutes |
| Supabase auth endpoints | Browser-side auth API calls | Yes - page.route() for /auth/v1/* |
| Backend API responses | /api/v1/* routes | Yes - factory data |

**Unit Test Coverage (vitest meta-tests):**

| Module | Functions | Coverage Target |
|--------|-----------|-----------------|
| factories.ts | 12 factory functions | Type correctness, override merging |
| assertions.ts | 5 assertion helpers | Failure on missing elements, timeout behavior |

### TDD Readiness Checklist
- [x] ACs are specific — each AC has a concrete, verifiable condition
- [x] ACs are measurable — most ACs can be verified via grep, CI run, or test execution
- [x] Test types clear per AC — E2E, vitest, grep/lint all distinguished
- [x] Red-green-refactor path clear — US-6 (meta tests) explicitly ordered before US-2 (implementation) in dependency graph

### Coverage Requirements
- [ ] Overall target specified — No numeric line/branch coverage target (MEDIUM finding)
- [x] Critical path coverage — 25/25 routes with content validation
- [ ] Branch coverage — Not specified (acceptable for E2E-focused spec)
- [x] Exclusions documented — Python E2E suite explicitly out of scope; auth-flow tests unchanged

### Recommendations

1. **Address `.catch()` in existing fixtures.ts (MEDIUM):** AC-4.5 targets "zero `.catch(() =>` patterns in portal/e2e/" but the current `fixtures.ts` has two instances (lines 80 and 90). Task T2.5 (fixture refactor) should explicitly call out removing these. The `hasSidebarNav` helper should be rewritten to use `await expect(locator).toBeVisible()` with proper error handling, and `waitForPageSettled` should use a Playwright auto-waiting pattern instead of swallowing errors.

2. **Clarify hybrid A+C claim or add vitest page tests (MEDIUM):** The spec selects "Hybrid A+C" but the only vitest tests defined (US-6) are for test infrastructure (factories, assertion helpers). If the intent is truly hybrid, add 2-3 vitest page-level component tests for critical pages (e.g., dashboard, admin user list) that validate render output with mocked API data. Otherwise, rename the approach to "Approach A with meta-testing" to avoid confusion.

3. **Add mock-to-API drift detection (MEDIUM):** TypeScript types in factories.ts will catch compile-time mismatches within the portal codebase, but the API schemas live in the Python backend. Add a recommendation (even as a future task) for an OpenAPI-based contract test or a manual review trigger when backend API response shapes change.

4. **Add a numeric coverage target (MEDIUM):** Even for an E2E-focused spec, specify: "25/25 routes with content assertions (E2E), 100% of factory and assertion helper functions covered by vitest." This makes the "done" criteria unambiguous.

5. **Add API error state E2E tests (LOW):** Include 1-2 tests per route category (player, admin) that mock API responses with 500 status codes to verify error-state rendering. This validates the `data-testid="error-{name}"` attributes from FR-007 and ensures error UIs actually work.

6. **Add CI timeout guard (LOW):** Set `timeout-minutes: 8` on the e2e job in portal-ci.yml as a hard enforcement of AC-8.7's "< 5 minutes" target (with buffer).

7. **Document single-browser decision (LOW):** Add a note in the KDD table: "Browser matrix: Chromium only (WebKit/Firefox out of scope for hardening phase; re-evaluate if cross-browser bugs emerge)."
