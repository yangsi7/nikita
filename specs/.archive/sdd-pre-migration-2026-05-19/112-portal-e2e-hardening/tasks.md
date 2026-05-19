# Spec 112 — Tasks

## Phase A: Infrastructure + Anti-Pattern Fixes

### US-1: Auth Bypass Infrastructure

- [ ] T1.1: Modify `portal/src/lib/supabase/middleware.ts` — env-gated E2E bypass (E2E_AUTH_BYPASS + E2E_AUTH_ROLE)
- [ ] T1.2: Update `portal/playwright.config.ts` — player (port 3003) + admin (port 3004) projects with separate webServers

### US-2: Fixture Infrastructure

- [ ] T2.1: Create `portal/e2e/fixtures/factories.ts` — 12 mock data factory functions with TypeScript types
- [ ] T2.2: Create `portal/e2e/fixtures/api-mocks.ts` — mockApiRoutes(page) helper for browser-side API interception
- [ ] T2.3: Create `portal/e2e/fixtures/assertions.ts` — expectTableRows, expectChartRendered, expectCardContent, expectDataLoaded, expectNoEmptyState
- [ ] T2.4: Create `portal/e2e/fixtures/index.ts` — re-exports
- [ ] T2.5: Refactor `portal/e2e/fixtures.ts` — move navigateAndWait etc. into fixtures/ directory; delete old `fixtures.ts` after US-3 completes (not kept as shim)

### US-3: Fix Anti-Patterns

- [ ] T3.1: Rewrite `portal/e2e/dashboard.spec.ts` — mockApiRoutes + content assertions
- [ ] T3.2: Rewrite `portal/e2e/data-viz.spec.ts` — mockApiRoutes + chart assertions
- [ ] T3.3: Rewrite `portal/e2e/admin-mutations.spec.ts` — mockApiRoutes + table assertions
- [ ] T3.4: Rewrite `portal/e2e/player.spec.ts` — mockApiRoutes + content assertions
- [ ] T3.5: Fix `portal/e2e/transitions-export.spec.ts` — content assertions
- [ ] T3.6: Audit + fix `portal/e2e/mobile-nav.spec.ts`

### US-4: data-testid (Phase A)

- [ ] T4.1: Dashboard components — score-ring, engagement-chart, chapter-progress, metric cards
- [ ] T4.2: Admin components — user-table, user-rows, prompt-list
- [ ] T4.3: Shared components — skeleton, empty-state, error-state, nav items

### US-5: CI Integration

- [ ] T5.1: Add `e2e` job to `.github/workflows/portal-ci.yml`

### US-6: Meta Tests

- [ ] T6.1: Vitest tests for factory functions
- [ ] T6.2: Vitest tests for assertion helpers
- [ ] T6.3: Vitest tests for middleware bypass production guard (2 tests: inactive in production, active in test)

## Phase B: New Route Coverage

### US-7: Player Route Tests

- [ ] T7.1: Create `portal/e2e/nikita-pages.spec.ts` — hub, mind, circle, day, stories
- [ ] T7.2: Create `portal/e2e/insights.spec.ts` — /dashboard/insights
- [ ] T7.3: Create `portal/e2e/diary.spec.ts` — /dashboard/diary
- [ ] T7.4: Create `portal/e2e/conversation-detail.spec.ts` — /dashboard/conversations/[id] (happy + error)

### US-8: Admin Route Tests

- [ ] T8.1: Create `portal/e2e/admin-pipeline.spec.ts` — /admin/pipeline
- [ ] T8.2: Create `portal/e2e/admin-jobs.spec.ts` — /admin/jobs
- [ ] T8.3: Create `portal/e2e/admin-conversation-detail.spec.ts` — /admin/conversations/[id] (happy + error)
- [ ] T8.4: Create `portal/e2e/admin-user-detail.spec.ts` — /admin/users/[id] (happy + error)
- [ ] T8.5: Extend `portal/e2e/admin.spec.ts` — /admin/text + /admin/voice

### US-9: data-testid (Phase B)

- [ ] T9.1: Nikita page components — mind-state, circle-graph, day-schedule, stories-list, hub-content
- [ ] T9.2: Insights/diary components — insight-cards, diary-entries
- [ ] T9.3: Admin detail components — pipeline-stages, job-list, conversation-events, user-metrics
