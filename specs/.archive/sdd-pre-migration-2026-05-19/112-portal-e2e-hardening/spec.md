# Spec 112: Portal E2E Hardening

**Status**: DRAFT (post-challenger-review)
**Domain**: Portal & Testing (Domain 6)
**GH Issues**: #101 (shallow assertions), #103 (missing route coverage; stale docs aspect is out of scope)
**Depends on**: Spec 044 (portal), Spec 063 (data-viz)

## Problem Statement

### GH #101: Shallow Assertions
Current Playwright E2E tests check selector existence (`.isVisible()`) but never validate content. A page can render zero data rows and still pass. Anti-patterns found in 5 of 10 test files:

| Anti-Pattern | Files | Example |
|---|---|---|
| `.catch(() => false)` swallowing | dashboard, data-viz, admin-mutations, player | `page.locator("svg").first().isVisible().catch(() => false)` |
| Triple-fallback OR assertions | dashboard, data-viz | `expect(hasScoreRing \|\| hasSkeleton \|\| hasError).toBe(true)` |
| `toBeGreaterThanOrEqual(0)` | dashboard | `expect(skeletonCount).toBeGreaterThanOrEqual(0)` |
| Body length > 0 (always true) | transitions-export | `body?.length > 0` |

These assertions can never fail, providing zero regression protection.

### GH #103: Missing Route Coverage
25 portal routes exist (24 `page.tsx` files + `/auth/callback` route handler). Only 10 are touched by E2E tests. 0 routes have content validation.

**Uncovered routes (15):**
- `/dashboard/nikita` (hub), `/dashboard/nikita/mind`, `/dashboard/nikita/circle`, `/dashboard/nikita/day`, `/dashboard/nikita/stories`
- `/dashboard/insights`, `/dashboard/diary`, `/dashboard/conversations/[id]`
- `/admin/conversations/[id]`, `/admin/pipeline`, `/admin/jobs`
- `/admin/users/[id]`, `/admin/text`, `/admin/voice`

**CI gap**: `portal-ci.yml` runs vitest only — no Playwright step.

**Out of scope**: GH #103 also mentions stale docs — documentation cleanup is not addressed by this spec. Python E2E tests in `tests/e2e/portal/` are out of scope; this spec targets only the TypeScript Playwright suite in `portal/e2e/`.

## Approach Evaluation

### Approach A: API Route Mocking via `page.route()`

Intercept all `/api/v1/*` and Supabase REST calls at network layer with deterministic fixture data. Auth solved by intercepting Supabase auth endpoints + injecting session cookies via `context.addCookies()`.

| Perspective | Score | Notes |
|---|---|---|
| QA Lead | 4/5 | Full route coverage, deterministic data, but network mocks can drift from real API |
| Frontend Engineer | 4/5 | Fast test authoring, TypeScript fixture types, but mock maintenance burden |
| DevOps Engineer | 4/5 | No external deps in CI, but need dev server + Chromium in portal-ci.yml |
| Devil's Advocate | 3/5 | Server-side `getUser()` in middleware calls Supabase directly — `page.route()` only intercepts browser-side fetches. Middleware auth bypass needed. |

**Total: 15/20**

### Approach B: Seeded Supabase Test User + Mocked API

Real Supabase auth with `service_role` key creating ephemeral test sessions. Backend API still mocked via `page.route()`.

| Perspective | Score | Notes |
|---|---|---|
| QA Lead | 4/5 | Real auth flow tested, good coverage |
| Frontend Engineer | 3/5 | Complex setup, `service_role` key management, user cleanup |
| DevOps Engineer | 2/5 | Requires Supabase secrets in CI, network dependency, flaky on cold starts |
| Devil's Advocate | 3/5 | Auth is already tested in `auth-flow.spec.ts` — re-testing adds cost without new signal |

**Total: 12/20**

### Approach C: Component-Heavy Pyramid (Vitest Shift)

Invest in vitest page-level component tests for content validation. Keep E2E thin (navigation + smoke).

| Perspective | Score | Notes |
|---|---|---|
| QA Lead | 3/5 | Strong unit coverage but misses integration issues (middleware, routing, hydration) |
| Frontend Engineer | 5/5 | Fast, isolated, easy to debug, no browser needed |
| DevOps Engineer | 5/5 | Already in CI, no new infra |
| Devil's Advocate | 2/5 | Component tests can't catch SSR hydration bugs, middleware redirects, or cookie-based auth |

**Total: 15/20**

### Selected: Hybrid A+C

**Rationale**: `page.route()` mocking (Approach A) for browser-side API content validation on all 25 routes + vitest page-level tests (Approach C) for fixture/assertion unit tests.

**Auth strategy — E2E auth bypass via env-gated middleware** (addresses C1: `page.route()` cannot intercept server-side middleware):

Next.js middleware calls `createServerClient().auth.getUser()` which makes a server-side HTTP request to Supabase — this is invisible to Playwright's `page.route()`. The solution:

1. **Middleware bypass**: Add env-gated bypass in `portal/src/lib/supabase/middleware.ts`. When `E2E_AUTH_BYPASS=true` (server-side only, NOT `NEXT_PUBLIC_`), middleware returns a mock user from `E2E_AUTH_ROLE` env var (`"player"` or `"admin"`) without calling Supabase. The bypass is server-side only and cannot be triggered from the browser.
2. **Dev server launch**: Playwright's `webServer` config starts `npm run dev` with `E2E_AUTH_BYPASS=true` and `E2E_AUTH_ROLE=player|admin`.
3. **Browser-side mocking**: `page.route()` intercepts `/api/v1/*` calls from the browser for deterministic content data (API responses, not auth).
4. **Two Playwright projects**: `player` project (E2E_AUTH_ROLE=player) and `admin` project (E2E_AUTH_ROLE=admin), each with their own `webServer` on different ports.

**Safety**: `E2E_AUTH_BYPASS` is a server-side env var (no `NEXT_PUBLIC_` prefix), not exposed to the browser, not set in Vercel/Cloud Run, and guarded by `process.env.NODE_ENV !== "production"` check.

## Functional Requirements

### FR-001: Fixture Data Factory

Create typed mock data factories for all API responses used across tests.

**Acceptance Criteria:**
- AC-1.1: `portal/e2e/fixtures/factories.ts` exports factory functions: `mockUser()`, `mockMetrics()`, `mockConversations()`, `mockPipelineEvents()`, `mockJobs()`, `mockVices()`, `mockInsights()`, `mockDiary()`, `mockNikitaMind()`, `mockNikitaCircle()`, `mockNikitaDay()`, `mockNikitaStories()`
- AC-1.2: All factories return TypeScript-typed objects matching API response schemas
- AC-1.3: Factories accept partial overrides: `mockUser({ chapter: 3, game_status: "active" })`
- AC-1.4: Single `mockApiRoutes(page)` helper that registers all `page.route()` interceptors with factory defaults

### FR-002: Auth Bypass Infrastructure

Solve the server-side `getUser()` problem so protected routes render without real Supabase credentials. Middleware runs server-side — `page.route()` cannot intercept it.

**Acceptance Criteria:**
- AC-2.1: `portal/src/lib/supabase/middleware.ts` adds env-gated bypass: when `E2E_AUTH_BYPASS=true` AND `process.env.NODE_ENV !== "production"`, skip `supabase.auth.getUser()` and return mock response based on `E2E_AUTH_ROLE` env var (`"player"` or `"admin"`)
- AC-2.2: Mock player user has `{ id: "e2e-player-id", email: "e2e-player@test.local", user_metadata: {} }`
- AC-2.3: Mock admin user has `{ id: "e2e-admin-id", email: "e2e-admin@test.local", user_metadata: { role: "admin" } }` (uses `@test.local` to exercise the metadata-based role path explicitly, not the ADMIN_EMAILS list)
- AC-2.4: `portal/playwright.config.ts` updated with two projects: `player` (port 3003, E2E_AUTH_ROLE=player) and `admin` (port 3004, E2E_AUTH_ROLE=admin), each with their own `webServer`
- AC-2.5: `E2E_AUTH_BYPASS` is NOT prefixed with `NEXT_PUBLIC_` (server-side only)
- AC-2.6: Production guard: bypass code is wrapped in `if (process.env.NODE_ENV !== "production")` — runtime guard prevents execution in production (Edge Runtime does not perform compile-time dead-code elimination)
- AC-2.7: Player project tests see `/dashboard/*` routes; admin project tests see `/admin/*` routes

### FR-003: Content Assertion Helpers

Replace shallow assertions with content-validating helpers.

**Acceptance Criteria:**
- AC-3.1: `portal/e2e/fixtures/assertions.ts` exports helpers: `expectTableRows(page, min)`, `expectChartRendered(page)`, `expectCardContent(page, testId, textPattern)`, `expectNoEmptyState(page)`, `expectDataLoaded(page)` (waits for skeleton removal + content presence)
- AC-3.2: All helpers use `data-testid` attributes (not CSS class selectors)
- AC-3.3: No helper uses `.catch(() => false)` pattern
- AC-3.4: All helpers have explicit timeout (default 10s) and fail with descriptive error messages

### FR-004: Fix Existing Anti-Patterns

Rewrite existing tests to use real assertions.

**Acceptance Criteria:**
- AC-4.1: Remove all `.catch(() => false)` patterns from `dashboard.spec.ts`, `data-viz.spec.ts`, `admin-mutations.spec.ts`, `player.spec.ts`, `transitions-export.spec.ts`
- AC-4.2: Replace all triple-OR assertions (`hasA || hasB || hasC`) with specific state assertions using `mockApiRoutes` — test the exact state, not any-of-three
- AC-4.3: Replace `toBeGreaterThanOrEqual(0)` with `toBeGreaterThan(0)` or exact count assertions
- AC-4.4: Every rewritten test uses `mockApiRoutes(page)` for deterministic data
- AC-4.5: Zero `.catch(() =>` patterns remain in `portal/e2e/` after completion (includes 2 instances in `portal/e2e/fixtures.ts` at ~lines 80 and 90, addressed by T2.5 refactor)

### FR-005: Missing Route Coverage — Player Routes

Add E2E tests for all uncovered player routes.

**Acceptance Criteria:**
- AC-5.1: `portal/e2e/nikita-pages.spec.ts` covers `/dashboard/nikita` (hub), `/dashboard/nikita/mind`, `/dashboard/nikita/circle`, `/dashboard/nikita/day`, `/dashboard/nikita/stories`
- AC-5.2: `portal/e2e/insights.spec.ts` covers `/dashboard/insights` with chart content assertions
- AC-5.3: `portal/e2e/diary.spec.ts` covers `/dashboard/diary` with entry content assertions
- AC-5.4: `portal/e2e/conversation-detail.spec.ts` covers `/dashboard/conversations/[id]` with message content assertions
- AC-5.5: Each test uses `setupMockAuth(page, "player")` + `mockApiRoutes(page)` for deterministic rendering
- AC-5.6: Each test asserts content presence, not just selector existence

### FR-006: Missing Route Coverage — Admin Routes

Add E2E tests for all uncovered admin routes.

**Acceptance Criteria:**
- AC-6.1: `portal/e2e/admin-pipeline.spec.ts` covers `/admin/pipeline` with stage timing table assertions
- AC-6.2: `portal/e2e/admin-jobs.spec.ts` covers `/admin/jobs` with job list content assertions
- AC-6.3: `portal/e2e/admin-conversation-detail.spec.ts` covers `/admin/conversations/[id]` with pipeline event assertions
- AC-6.4: `portal/e2e/admin-user-detail.spec.ts` covers `/admin/users/[id]` with user metric assertions
- AC-6.5: Extend `admin.spec.ts` to cover `/admin/text` and `/admin/voice` with content assertions
- AC-6.6: Each test uses `setupMockAuth(page, "admin")` + `mockApiRoutes(page)`

### FR-007: `data-testid` Instrumentation

Add `data-testid` attributes to portal components for reliable test selectors.

**Acceptance Criteria:**
- AC-7.1: All dashboard cards have `data-testid="card-{name}"` (score-ring, engagement-chart, chapter-progress, etc.)
- AC-7.2: All tables have `data-testid="table-{name}"` and rows have `data-testid="row-{index}"`
- AC-7.3: All chart containers have `data-testid="chart-{name}"`
- AC-7.4: Navigation elements have `data-testid="nav-{name}"`
- AC-7.5: Loading skeletons have `data-testid="skeleton-{name}"`
- AC-7.6: Empty states have `data-testid="empty-{name}"`
- AC-7.7: Error states have `data-testid="error-{name}"`
- AC-7.8: Every component referenced by an E2E assertion has a corresponding `data-testid` attribute (no arbitrary minimum — scales with test suite)

### FR-008: CI Integration

Add Playwright E2E step to `portal-ci.yml`.

**Acceptance Criteria:**
- AC-8.1: New `e2e` job in `.github/workflows/portal-ci.yml` that depends on `lint-and-type-check`
- AC-8.2: Uses `npx playwright install --with-deps chromium` for browser setup
- AC-8.3: Runs `npx playwright test` with `CI=true` env var
- AC-8.4: Single worker (`workers: 1` already in config)
- AC-8.5: Uploads `playwright-report/` as artifact on failure
- AC-8.6: Uses dummy env vars for Supabase (same as existing build step)
- AC-8.7: Total CI time increase < 5 minutes (Playwright install ~60s + dev server startup ~20s + test execution ~120s + overhead)

## Mock Schema Reference

Factories in `portal/e2e/fixtures/factories.ts` MUST match the **TypeScript interfaces** in `portal/src/lib/api/types.ts`, NOT the backend Pydantic models. Rationale: `page.route()` intercepts browser-side fetches, so mocked JSON is consumed by TypeScript code that expects the TS interface shape.

### Factory → TypeScript Interface Mapping

| Factory Function | TS Interface (`types.ts`) | Notes |
|---|---|---|
| `mockUser()` | `User` | |
| `mockMetrics()` | `UserMetrics` | |
| `mockConversations()` | `ConversationsResponse` | See drift D1 |
| `mockPipelineEvents()` | `PipelineHistoryItem[]` | See drift D3 |
| `mockJobs()` | `Job[]` | |
| `mockVices()` | `VicePreference[]` | |
| `mockInsights()` | `InsightsResponse` | |
| `mockDiary()` | `DiaryEntry[]` | |
| `mockNikitaMind()` | `NikitaMindState` | |
| `mockNikitaCircle()` | `NikitaCircle` | |
| `mockNikitaDay()` | `NikitaDay` | |
| `mockNikitaStories()` | `NikitaStory[]` | |

### Known TS/Pydantic Drifts (Accepted Deviations)

Factories match TS types because `page.route()` intercepts browser-side fetches — the browser JS/TS code parses the response, not the backend.

| ID | TS Interface | TS Field | Backend Pydantic Field | Resolution |
|---|---|---|---|---|
| D1 | `ConversationsResponse` | `total: number` | `total_count: int` | Factory uses `total` (TS). Backend serializes as `total_count`; the API route or proxy layer maps to `total`. |
| D2 | `ConversationMessage` | `id: string`, `created_at: string` | Not present in some response models | Factory includes `id` and `created_at` (required by TS interface for rendering message lists). |
| D3 | `PipelineRun` / `PipelineHistoryItem` | `success: boolean`, `stages: Stage[]` | `status: str`, `stage_results: list` | Factory uses TS shape (`success`, `stages[]`). Backend shape differs; API layer transforms before response. |

## `data-testid` Naming Reference

Mapping of spec `data-testid` names to actual portal component files:

| `data-testid` | Component File | Element |
|---|---|---|
| `card-score-ring` | `portal/src/components/dashboard/mood-orb.tsx` | Score ring / mood orb container |
| `card-engagement-chart` | `portal/src/components/dashboard/engagement-chart.tsx` | Engagement chart card |
| `card-chapter-progress` | `portal/src/components/dashboard/chapter-progress.tsx` | Chapter progress card |
| `table-users` | `portal/src/components/admin/user-table.tsx` | Admin users table |
| `row-{index}` | `portal/src/components/admin/user-table.tsx` | Table row by index |
| `chart-engagement` | `portal/src/components/dashboard/engagement-chart.tsx` | Chart SVG container |
| `chart-insights` | `portal/src/components/dashboard/insights-chart.tsx` | Insights chart SVG |
| `nav-sidebar` | `portal/src/components/layout/sidebar.tsx` | Sidebar navigation |
| `nav-mobile` | `portal/src/components/layout/mobile-nav.tsx` | Mobile nav drawer |
| `skeleton-{name}` | Various `*-skeleton.tsx` files | Loading skeleton |
| `empty-{name}` | Various components with empty states | Empty state container |
| `error-{name}` | Various components with error states | Error boundary/fallback |

### FR-002 Addendum: Production Guard Tests

- AC-2.8: Two vitest unit tests in `portal/src/lib/supabase/__tests__/middleware-bypass.test.ts`:
  1. Verify bypass is **inactive** when `NODE_ENV=production` (even if `E2E_AUTH_BYPASS=true`)
  2. Verify bypass is **active** when `NODE_ENV=test` and `E2E_AUTH_BYPASS=true`

## Out of Scope

The following are explicitly out of scope for Spec 112:

- **Mobile viewport tests** for new routes (existing `mobile-nav.spec.ts` is audited but no new viewport tests added)
- **axe accessibility audits** for new routes (existing `accessibility.spec.ts` covers login only; extending is a separate spec)
- **Dark mode chart verification** (portal is dark-only; no theme toggle testing needed)
- **API error-state E2E tests** (500 responses) — dynamic routes test invalid-ID error states, but generic server errors are not mocked
- **Python E2E suite** (`tests/e2e/portal/`) — complementary but separate; this spec targets `portal/e2e/` (TypeScript) only
- **GH #103 stale docs** — documentation cleanup is not addressed by this spec

## Non-Functional Requirements

- Mock data factories must be type-safe (TypeScript, no `any`)
- No test should depend on external network calls (Supabase, Cloud Run)
- All tests deterministic — same result on every run
- Test execution time: < 180s total for all E2E tests (single worker, excluding Playwright install + dev server startup)
- `data-testid` attributes kept in production (minimal perf impact, no build complexity)

## Route Coverage Matrix

| # | Route | Current E2E | Target E2E | Content Validated |
|---|-------|-------------|------------|-------------------|
| 1 | `/` (landing) | auth-flow | auth-flow | Redirect only |
| 2 | `/login` | login, auth-flow, accessibility | login, auth-flow, accessibility | Yes (form elements) |
| 3 | `/auth/callback` | auth-flow | auth-flow | Redirect only |
| 4 | `/dashboard` | dashboard | dashboard (rewrite) | Yes (score ring, chart) |
| 5 | `/dashboard/engagement` | dashboard | dashboard (rewrite) | Yes (timeline chart) |
| 6 | `/dashboard/vices` | player | player (rewrite) | Yes (vice cards) |
| 7 | `/dashboard/conversations` | player | player (rewrite) | Yes (message list) |
| 8 | `/dashboard/conversations/[id]` | NONE | conversation-detail | Yes (messages) |
| 9 | `/dashboard/settings` | player | player (rewrite) | Yes (settings form) |
| 10 | `/dashboard/nikita` | NONE | nikita-pages | Yes (hub content) |
| 11 | `/dashboard/nikita/mind` | NONE | nikita-pages | Yes (mind state) |
| 12 | `/dashboard/nikita/circle` | NONE | nikita-pages | Yes (social graph) |
| 13 | `/dashboard/nikita/day` | NONE | nikita-pages | Yes (daily schedule) |
| 14 | `/dashboard/nikita/stories` | NONE | nikita-pages | Yes (story entries) |
| 15 | `/dashboard/insights` | NONE | insights | Yes (insight cards) |
| 16 | `/dashboard/diary` | NONE | diary | Yes (diary entries) |
| 17 | `/admin` | admin, admin-mutations | admin (rewrite) | Yes (user table) |
| 18 | `/admin/users` | admin-mutations | admin (rewrite) | Yes (user rows) |
| 19 | `/admin/users/[id]` | NONE | admin-user-detail | Yes (user metrics) |
| 20 | `/admin/prompts` | admin | admin (rewrite) | Yes (prompt list) |
| 21 | `/admin/text` | NONE | admin (extend) | Yes (conversations) |
| 22 | `/admin/voice` | NONE | admin (extend) | Yes (voice sessions) |
| 23 | `/admin/pipeline` | NONE | admin-pipeline | Yes (stage timings) |
| 24 | `/admin/jobs` | NONE | admin-jobs | Yes (job list) |
| 25 | `/admin/conversations/[id]` | NONE | admin-conversation-detail | Yes (pipeline events) |

**Coverage**: 10/25 current -> 25/25 target. Content validated: 0/25 current -> 25/25 target.

## Test Strategy

This spec is about tests, so the meta-test strategy is:

1. **Factory tests** (vitest): Verify `mockUser()`, `mockMetrics()` etc. return correctly typed objects
2. **Assertion helper tests** (vitest): Verify helpers fail when expected conditions are not met
3. **CI validation**: Verify Playwright runs in GitHub Actions with dummy env vars
4. **Anti-pattern regression**: `rg ".catch\(\(\) =>" portal/e2e/` returns zero matches post-implementation
5. **Coverage audit**: Script that extracts all `page.tsx` routes and verifies each has a corresponding test

## Files to Create

| File | Purpose |
|---|---|
| `portal/e2e/fixtures/factories.ts` | Mock data factory functions |
| `portal/e2e/fixtures/api-mocks.ts` | Browser-side API route mocking (mockApiRoutes helper) |
| `portal/e2e/fixtures/assertions.ts` | Content assertion helpers |
| `portal/e2e/fixtures/index.ts` | Re-exports |
| `portal/e2e/nikita-pages.spec.ts` | Tests for 5 `/dashboard/nikita/*` routes |
| `portal/e2e/insights.spec.ts` | Tests for `/dashboard/insights` |
| `portal/e2e/diary.spec.ts` | Tests for `/dashboard/diary` |
| `portal/e2e/conversation-detail.spec.ts` | Tests for `/dashboard/conversations/[id]` |
| `portal/e2e/admin-pipeline.spec.ts` | Tests for `/admin/pipeline` |
| `portal/e2e/admin-jobs.spec.ts` | Tests for `/admin/jobs` |
| `portal/e2e/admin-conversation-detail.spec.ts` | Tests for `/admin/conversations/[id]` |
| `portal/e2e/admin-user-detail.spec.ts` | Tests for `/admin/users/[id]` |

## Files to Modify

| File | Change |
|---|---|
| `portal/e2e/dashboard.spec.ts` | Rewrite with `mockApiRoutes` + content assertions |
| `portal/e2e/data-viz.spec.ts` | Rewrite with `mockApiRoutes` + content assertions |
| `portal/e2e/admin.spec.ts` | Rewrite + extend for `/admin/text`, `/admin/voice` |
| `portal/e2e/admin-mutations.spec.ts` | Rewrite with `mockApiRoutes` |
| `portal/e2e/player.spec.ts` | Rewrite with `mockApiRoutes` + content assertions |
| `portal/e2e/transitions-export.spec.ts` | Fix `body?.length > 0` anti-pattern with content assertions |
| `portal/e2e/mobile-nav.spec.ts` | Audit and fix any anti-patterns |
| `portal/e2e/fixtures.ts` | Refactor — move helpers to `fixtures/` directory |
| `portal/src/lib/supabase/middleware.ts` | Add E2E auth bypass (env-gated, production-safe) |
| `portal/playwright.config.ts` | Add player/admin projects with separate webServers |
| `.github/workflows/portal-ci.yml` | Add Playwright E2E job |
| ~20 portal component files | Add `data-testid` attributes |

## Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Auth mock strategy | Env-gated middleware bypass (`E2E_AUTH_BYPASS`) | `page.route()` cannot intercept server-side middleware calls; env var is server-only, production-guarded |
| Selector strategy | `data-testid` attributes | Stable across refactors, explicit intent, recommended by Playwright docs |
| Mock data format | TypeScript factory functions with overrides | Type-safe, composable, avoids JSON file drift |
| CI integration | Separate job after lint/build | Fails fast on lint/type errors; E2E only runs if build succeeds |
| Coverage target | 25/25 routes with content validation | Complete coverage eliminates blind spots |
| Phasing | Phase A: infra + fix anti-patterns; Phase B: new route coverage | Reduces PR blast radius, stays under 400-line PR limit |
| Python E2E suite | Out of scope | `tests/e2e/portal/` (Python) is complementary; this spec targets `portal/e2e/` (TypeScript) only |
| Edge cases | Invalid IDs + empty states + token expiry tested | Dynamic routes (`[id]`) get both happy-path and error-state tests; mock tokens use long expiry |
