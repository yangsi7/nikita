# Architecture Validation Report

**Spec:** `specs/112-portal-e2e-hardening/spec.md`
**Status:** PASS
**Timestamp:** 2026-03-11T12:00:00Z
**Validator:** sdd-architecture-validator

## Summary

- CRITICAL: 0
- HIGH: 0
- MEDIUM: 3
- LOW: 2

## Findings

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| MEDIUM | Module Organization | `fixtures.ts` (flat file) to `fixtures/` (directory) migration needs explicit re-export strategy to avoid breaking existing imports in 10 spec files | `portal/e2e/fixtures.ts` -> `portal/e2e/fixtures/` | Spec mentions T2.5 (refactor fixtures.ts) but does not specify whether `fixtures.ts` becomes a re-export shim or is deleted. All 10 existing spec files import from `./fixtures`. Add explicit migration note: delete `fixtures.ts` after all spec files are updated to import from `./fixtures/index.ts`, OR keep `fixtures.ts` as a re-export shim during Phase A and delete in Phase B. |
| MEDIUM | Separation of Concerns | `auth.ts` file named in spec (AC-1.4) contains `mockApiRoutes(page)` which mixes API mocking (data concern) with auth setup (auth concern) | `portal/e2e/fixtures/auth.ts` | Rename to `portal/e2e/fixtures/mock-routes.ts` or `portal/e2e/fixtures/api-mocks.ts`. The file intercepts `/api/v1/*` routes with factory data -- this is API mocking, not auth. Auth bypass is handled server-side in middleware.ts. Alternatively, keep `auth.ts` but document that it handles "browser-side route mocking for authenticated pages" to justify the name. |
| MEDIUM | Import Patterns | Vitest meta-tests (US-6: T6.1, T6.2) for factories and assertion helpers will import from `portal/e2e/fixtures/`. Vitest config must include `e2e/fixtures/` in its module resolution but exclude `e2e/*.spec.ts` (Playwright files). No mention of vitest config changes in spec. | `portal/vitest.config.ts` (or `vite.config.ts`) | Add a task to verify vitest can resolve imports from `e2e/fixtures/` without pulling in Playwright test files. Likely needs a dedicated test file location like `portal/src/__tests__/e2e-fixtures.test.ts` that imports from `../e2e/fixtures/` or a vitest `include` pattern update. |
| LOW | Naming Conventions | Spec lists `portal/e2e/fixtures/auth.ts` but the auth bypass is in `portal/src/lib/supabase/middleware.ts`. Two files with "auth" semantics in different layers could confuse contributors. | `portal/e2e/fixtures/auth.ts` vs `portal/src/lib/supabase/middleware.ts` | Minor naming concern. A comment header in `e2e/fixtures/auth.ts` clarifying "browser-side auth/API mocking (server-side bypass is in src/lib/supabase/middleware.ts)" would suffice. |
| LOW | Scalability | Phase A PR estimated at ~575 lines exceeds the 400-line PR limit stated in CLAUDE.md Git Conventions. Phase B at ~460 lines also exceeds. | `specs/112-portal-e2e-hardening/plan.md` lines 88-91 | Consider splitting Phase A into two PRs: (A1) infra + CI = US-1 + US-2 + US-5 + US-6 (~365 lines), (A2) anti-pattern fixes + data-testid = US-3 + US-4 (~280 lines). This brings each PR under 400 lines. |

## Proposed Structure

```
portal/
  e2e/
    fixtures/
      factories.ts        # Mock data factory functions (mockUser, mockMetrics, etc.)
      auth.ts              # mockApiRoutes(page) - browser-side API interception
      assertions.ts        # expectTableRows, expectChartRendered, etc.
      index.ts             # Barrel re-exports
    .auth/
      player.json          # Empty storage state (existing)
      admin.json           # Empty storage state (existing)
    global-setup.ts        # Existing - creates .auth files
    dashboard.spec.ts      # Rewritten with mockApiRoutes
    data-viz.spec.ts       # Rewritten with mockApiRoutes
    admin.spec.ts          # Rewritten + extended (/admin/text, /admin/voice)
    admin-mutations.spec.ts # Rewritten with mockApiRoutes
    player.spec.ts         # Rewritten with mockApiRoutes
    transitions-export.spec.ts # Fixed anti-patterns
    mobile-nav.spec.ts     # Audited
    auth-flow.spec.ts      # Existing (unchanged)
    login.spec.ts          # Existing (unchanged)
    accessibility.spec.ts  # Existing (unchanged)
    nikita-pages.spec.ts   # NEW - 5 nikita sub-routes
    insights.spec.ts       # NEW - /dashboard/insights
    diary.spec.ts          # NEW - /dashboard/diary
    conversation-detail.spec.ts      # NEW - /dashboard/conversations/[id]
    admin-pipeline.spec.ts           # NEW - /admin/pipeline
    admin-jobs.spec.ts               # NEW - /admin/jobs
    admin-conversation-detail.spec.ts # NEW - /admin/conversations/[id]
    admin-user-detail.spec.ts        # NEW - /admin/users/[id]
  src/
    lib/supabase/
      middleware.ts        # MODIFIED - env-gated E2E bypass added
      client.ts            # Existing (unchanged)
      server.ts            # Existing (unchanged)
    components/            # ~20 files MODIFIED with data-testid attributes
  middleware.ts            # Existing (unchanged) - delegates to lib/supabase/middleware.ts
  playwright.config.ts     # MODIFIED - player/admin projects, two webServers
```

## Module Dependency Graph

```
playwright.config.ts
  |-- defines projects: player (port 3003), admin (port 3004)
  |-- webServer starts: npm run dev (with E2E_AUTH_BYPASS=true)
  |
  v
e2e/*.spec.ts
  |-- imports from: e2e/fixtures/index.ts (barrel)
  |                   |-- factories.ts (mock data)
  |                   |-- auth.ts (mockApiRoutes - page.route interceptors)
  |                   |-- assertions.ts (expectTableRows, etc.)
  |
  |-- uses: page.route() -> intercepts browser /api/v1/* calls
  |
  v
portal/src/ (Next.js app, served by dev server)
  |-- middleware.ts -> lib/supabase/middleware.ts
  |     |-- IF E2E_AUTH_BYPASS=true: returns mock user (no Supabase call)
  |     |-- ELSE: normal supabase.auth.getUser()
  |
  |-- components/*.tsx (with data-testid attributes)
  |-- app/**/*.tsx (pages)
```

**Key boundary**: E2E tests (portal/e2e/) NEVER import from portal/src/. The only cross-boundary interaction is:
1. Server-side: env var `E2E_AUTH_BYPASS` controls middleware behavior
2. Browser-side: `page.route()` intercepts HTTP requests to `/api/v1/*`
3. DOM-side: `data-testid` attributes on components serve as the test contract

This is a clean architectural boundary -- no source code coupling.

## Separation of Concerns Analysis

| Layer | Responsibility | Violations |
|-------|---------------|------------|
| `e2e/fixtures/factories.ts` | Mock data generation (typed objects matching API schemas) | None |
| `e2e/fixtures/auth.ts` | Browser-side API route interception via `page.route()` | Minor naming issue (see MEDIUM finding) |
| `e2e/fixtures/assertions.ts` | Reusable content validation helpers | None |
| `e2e/*.spec.ts` | Test orchestration (navigate, assert) | Will be cleaned up (anti-patterns removed) |
| `src/lib/supabase/middleware.ts` | Auth bypass (server-side, env-gated) | None -- clean production guard |
| `src/components/*.tsx` | `data-testid` instrumentation | None -- attributes are passive, no test logic in source |
| `.github/workflows/portal-ci.yml` | CI pipeline (Playwright job) | None |

## Import Pattern Checklist

- [x] `@/*` alias configured in `portal/tsconfig.json` (maps to `./src/*`) -- spec correctly references source files via this alias
- [x] E2E fixtures use relative imports within `e2e/` directory (no `@/` alias needed -- e2e/ is outside src/)
- [x] Barrel export via `fixtures/index.ts` prevents deep imports into fixture internals
- [x] No circular dependencies possible -- fixture files are pure (factories return objects, assertions use Playwright Page API, auth.ts registers routes)
- [x] Spec correctly avoids importing Playwright types in vitest tests (US-6 meta-tests test factory return types, not Playwright Page-dependent helpers)
- [ ] **Needs clarification**: How vitest resolves `e2e/fixtures/` imports -- see MEDIUM finding above

## Security Architecture

- [x] `E2E_AUTH_BYPASS` is server-side only (no `NEXT_PUBLIC_` prefix) -- cannot be read by browser JavaScript
- [x] Production guard: bypass wrapped in `process.env.NODE_ENV !== "production"` -- dead-code-eliminated by Next.js production builds
- [x] Double guard: both env var check AND NODE_ENV check required
- [x] Mock user IDs are deterministic test values (`e2e-player-id`, `e2e-admin-id`) -- clearly non-production
- [x] No real Supabase credentials needed in CI -- dummy env vars sufficient
- [x] `E2E_AUTH_BYPASS` not set in Vercel or Cloud Run environments
- [x] `data-testid` attributes kept in production (industry standard -- negligible performance impact, no security concern)

## Type Safety Assessment

- [x] TypeScript strict mode enabled (`"strict": true` in tsconfig.json)
- [x] Factories return typed objects matching API response schemas (AC-1.2)
- [x] Factory overrides use `Partial<T>` pattern (AC-1.3) -- type-safe partial application
- [x] No `any` types allowed in mock factories (NFR)
- [x] Assertion helpers accept typed `Page` parameter from Playwright

## Alignment with Existing Architecture

1. **Middleware modification is minimal and well-isolated**: The `updateSession()` function in `portal/src/lib/supabase/middleware.ts` (61 lines) gets a ~15-line bypass block at the top. The existing auth logic (lines 29-60) remains unchanged. Clean separation.

2. **Playwright config evolution is additive**: Current config has `setup` + `chromium` projects. Spec adds `player` + `admin` projects. The existing `global-setup.ts` already creates `player.json` and `admin.json` storage states -- this aligns with the two-project model.

3. **E2E directory structure follows existing convention**: All test files are flat in `e2e/` (matching existing pattern). Fixtures directory is a clean extraction of the existing `fixtures.ts` file. No deviation from established patterns.

4. **Anti-pattern count confirmed**: Spec claims 5 files have `.catch(() => false)`. Actual ripgrep finds 9 files (40 instances total). Spec correctly identifies the worst offenders but `auth-flow.spec.ts`, `mobile-nav.spec.ts`, `admin.spec.ts`, and `transitions-export.spec.ts` also have instances. T3.6 (audit mobile-nav) partially covers this, but `auth-flow.spec.ts` and `admin.spec.ts` are not explicitly listed for anti-pattern removal. **This is not an architecture concern** -- it is a scope completeness issue for the testing validator.

5. **24 page.tsx files found** (spec says 24 + 1 route handler = 25 routes): Confirmed alignment.

## Recommendations

1. **(MEDIUM - Action Required)** Clarify the `fixtures.ts` -> `fixtures/` migration strategy in plan.md. Either (a) keep `fixtures.ts` as a re-export shim during Phase A or (b) update all 10 spec files' imports in US-3 (which rewrites them anyway). Option (b) is cleaner since US-3 rewrites all files.

2. **(MEDIUM - Action Required)** Add a task to verify vitest can import from `e2e/fixtures/` for the US-6 meta-tests. Check if `portal/vitest.config.ts` includes the `e2e/` path or if the meta-tests should live elsewhere (e.g., `portal/src/__tests__/e2e-meta/`).

3. **(MEDIUM - Suggestion)** Consider renaming `e2e/fixtures/auth.ts` to `e2e/fixtures/api-mocks.ts` since its primary function is `mockApiRoutes(page)` (API interception), not auth. Auth bypass is handled server-side in middleware.ts.

4. **(LOW - Suggestion)** Split Phase A into two PRs to stay under the 400-line limit: (A1) infrastructure + CI, (A2) anti-pattern fixes + data-testid instrumentation.

5. **(LOW - Suggestion)** Add a comment header in the auth bypass block in `middleware.ts` pointing to `e2e/fixtures/` as the companion test infrastructure, for discoverability.
