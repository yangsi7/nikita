# Spec 112 — Implementation Plan

## Overview

~1200 lines across ~30 files. 12 new test/fixture files + modifications to 8 existing test files + 2 config files + ~20 portal components (data-testid). Two phases to stay under 400-line PR limit.

## Phase A: Infrastructure + Anti-Pattern Fixes (PR 1)

### US-1: Auth Bypass Infrastructure
- T1.1: Modify `portal/src/lib/supabase/middleware.ts` — add env-gated E2E bypass (~15 lines)
- T1.2: Update `portal/playwright.config.ts` — two projects (player port 3003, admin port 3004) with separate webServers

### US-2: Fixture Infrastructure
- T2.1: Create `portal/e2e/fixtures/factories.ts` — mock data factories (mockUser, mockMetrics, mockConversations, mockPipelineEvents, mockJobs, mockVices, mockInsights, mockDiary, mockNikitaMind, mockNikitaCircle, mockNikitaDay, mockNikitaStories)
- T2.2: Create `portal/e2e/fixtures/api-mocks.ts` — browser-side API route mocking (mockApiRoutes helper). Named `api-mocks.ts` (not `auth.ts`) because it contains API response mocking, not auth logic.
- T2.3: Create `portal/e2e/fixtures/assertions.ts` — content assertion helpers (expectTableRows, expectChartRendered, expectCardContent, expectDataLoaded, expectNoEmptyState)
- T2.4: Create `portal/e2e/fixtures/index.ts` — re-exports
- T2.5: Refactor `portal/e2e/fixtures.ts` — move existing helpers (navigateAndWait, etc.) into fixtures/ directory. Delete old `fixtures.ts` after US-3 completes (not kept as shim). This also eliminates 2 `.catch(() => false)` instances at ~lines 80/90.

### US-3: Fix Anti-Patterns in Existing Tests
- T3.1: Rewrite `portal/e2e/dashboard.spec.ts` — replace .catch(() => false), triple-OR, >=0 with mockApiRoutes + content assertions
- T3.2: Rewrite `portal/e2e/data-viz.spec.ts` — replace .catch(() => false) with mockApiRoutes + chart assertions
- T3.3: Rewrite `portal/e2e/admin-mutations.spec.ts` — replace .catch(() => false) with mockApiRoutes + table assertions
- T3.4: Rewrite `portal/e2e/player.spec.ts` — replace .catch(() => false) with mockApiRoutes + content assertions
- T3.5: Fix `portal/e2e/transitions-export.spec.ts` — replace body?.length > 0 with content assertions
- T3.6: Audit `portal/e2e/mobile-nav.spec.ts` — fix any anti-patterns found

### US-4: `data-testid` Instrumentation (Phase A subset)
- T4.1: Add `data-testid` to dashboard components (score-ring, engagement-chart, chapter-progress, metric cards)
- T4.2: Add `data-testid` to admin components (user-table, user-rows, prompt-list)
- T4.3: Add `data-testid` to shared components (skeleton, empty-state, error-state, nav items)

### US-5: CI Integration
- T5.1: Add `e2e` job to `.github/workflows/portal-ci.yml` — depends on lint-and-type-check, installs Chromium, runs Playwright, uploads report on failure

### US-6: Meta Tests (vitest)
- T6.1: Write vitest tests for factory functions (type correctness, override support)
- T6.2: Write vitest tests for assertion helpers (fail on missing elements)
- T6.3: Write 2 vitest tests for middleware bypass production guard (inactive in production, active in test) — see AC-2.8

**Note**: `vitest.config.ts` may need an `e2e/` path alias or include pattern for US-6 meta-tests if factory/assertion imports resolve from `portal/e2e/`.

## Phase B: New Route Coverage (PR 2)

### US-7: Player Route Tests
- T7.1: Create `portal/e2e/nikita-pages.spec.ts` — 5 nikita sub-routes (hub, mind, circle, day, stories)
- T7.2: Create `portal/e2e/insights.spec.ts` — /dashboard/insights
- T7.3: Create `portal/e2e/diary.spec.ts` — /dashboard/diary
- T7.4: Create `portal/e2e/conversation-detail.spec.ts` — /dashboard/conversations/[id] (happy path + invalid ID error state)

### US-8: Admin Route Tests
- T8.1: Create `portal/e2e/admin-pipeline.spec.ts` — /admin/pipeline
- T8.2: Create `portal/e2e/admin-jobs.spec.ts` — /admin/jobs
- T8.3: Create `portal/e2e/admin-conversation-detail.spec.ts` — /admin/conversations/[id] (happy path + invalid ID)
- T8.4: Create `portal/e2e/admin-user-detail.spec.ts` — /admin/users/[id] (happy path + invalid ID)
- T8.5: Extend `portal/e2e/admin.spec.ts` — add /admin/text and /admin/voice content assertions

### US-9: `data-testid` Instrumentation (Phase B subset)
- T9.1: Add `data-testid` to nikita page components (mind-state, circle-graph, day-schedule, stories-list, hub-content)
- T9.2: Add `data-testid` to insights/diary components (insight-cards, diary-entries)
- T9.3: Add `data-testid` to admin detail components (pipeline-stages, job-list, conversation-events, user-metrics)

## Dependencies

```
US-1 → US-2 (auth bypass needed before fixtures can work)
US-2 → US-3 (fixtures needed for test rewrites)
US-4 → US-3 (data-testid needed before assertions can reference them)
US-6 written BEFORE US-2 (TDD — tests first)
US-5 independent (CI config, can be done anytime in Phase A)
Phase B depends on Phase A (all US-7/8/9 depend on US-1/2/4 infrastructure)
```

## Estimated Lines

| Component | Lines |
|-----------|-------|
| Middleware bypass (T1.1) | ~15 |
| Playwright config (T1.2) | ~30 |
| Factories (T2.1) | ~180 |
| API route mocking (T2.2) | ~80 |
| Assertion helpers (T2.3) | ~60 |
| Fixture refactor (T2.4-2.5) | ~20 |
| Anti-pattern rewrites (T3.1-3.6) | ~200 (net change) |
| data-testid Phase A (T4.1-4.3) | ~80 (across ~12 components) |
| CI job (T5.1) | ~30 |
| Meta tests (T6.1-6.2) | ~60 |
| Player route tests (T7.1-7.4) | ~200 |
| Admin route tests (T8.1-8.5) | ~200 |
| data-testid Phase B (T9.1-9.3) | ~60 (across ~8 components) |
| **Total** | **~1215** |

## Phase A PR: ~575 lines | Phase B PR: ~460 lines
