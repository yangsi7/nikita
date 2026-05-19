## Frontend Validation Report

**Spec:** `specs/112-portal-e2e-hardening/spec.md`
**Status:** PASS
**Timestamp:** 2026-03-11T14:30:00Z
**Validator:** sdd-frontend-validator (Claude Opus 4.6)

### Summary
- CRITICAL: 0
- HIGH: 0
- MEDIUM: 5
- LOW: 3

### Rationale

Spec 112 is primarily a **testing infrastructure** spec, not a UI feature spec. It adds `data-testid` attributes and rewrites E2E test assertions -- it does not introduce new components, pages, layouts, or user-facing functionality. The frontend validation scope is therefore narrower than a typical feature spec. All UI-impacting changes (data-testid instrumentation) are additive and non-breaking. The spec correctly identifies all existing anti-patterns (verified against codebase), proposes sound Playwright patterns (`page.route()`, env-gated middleware bypass), and has comprehensive route coverage targets (10/25 -> 25/25).

### Findings

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| MEDIUM | Component Spec | `data-testid` component list uses generic names (score-ring, engagement-chart) that don't match actual component filenames in `portal/src/components/dashboard/` (mood-orb.tsx, relationship-hero.tsx, score-detail-chart.tsx, etc.) | spec.md:166-173, AC-7.1 | Add a mapping table: `data-testid` value -> actual component file. The 21 dashboard components and 7 admin components should each be enumerated with their target `data-testid`. |
| MEDIUM | Component Spec | Plan says "~20 portal components" for data-testid but the dashboard alone has 21 component files, admin has 7, shared has 11, and charts likely more. The actual count is ~40+ components. | plan.md:1, spec.md:270 | Audit all components that render testable content and provide an explicit list. The "~20" estimate may be sufficient if only components referenced by assertions need IDs, but this should be stated explicitly. |
| MEDIUM | Responsive | Spec does not specify whether new E2E tests should include mobile viewport testing beyond the existing `mobile-nav.spec.ts`. The 15 new route tests (FR-005, FR-006) all appear to target desktop viewport only. | spec.md:137-160 | Add a note that responsive testing is out of scope for this spec, OR add at least one mobile viewport test per new spec file (since the portal is responsive and bugs could hide at mobile widths). |
| MEDIUM | Accessibility Testing | The `accessibility.spec.ts` file (axe-core) currently only tests 3 routes (/login, /dashboard, /admin). Spec 112 adds 15 new route tests but does not extend axe accessibility audits to the new routes. | spec.md (missing) | Add AC to FR-005/FR-006 requiring axe audit on at least the new route groupings (nikita sub-pages, insights, diary, admin detail pages), OR explicitly mark a11y extension as out of scope. |
| MEDIUM | Dark Mode | Spec correctly sets `colorScheme: "dark"` in playwright.config.ts (line 18), and portal is hardcoded dark (`className="dark"` in layout.tsx:29). However, no AC verifies that mock data renders correctly in dark theme (e.g., chart colors, contrast). | playwright.config.ts:18 | LOW risk since portal is dark-only. Consider adding a single visual regression test or contrast check for charts rendered with mock data. |
| LOW | Anti-Pattern Coverage | `fixtures.ts:90` contains `.catch(() => false)` in the `hasSidebarNav` helper. Spec AC-4.5 says "Zero `.catch(() =>` patterns remain in `portal/e2e/`" but only lists 5 spec files in AC-4.1, not fixtures.ts itself. | spec.md:131, fixtures.ts:90 | AC-4.1 should explicitly include `portal/e2e/fixtures.ts` (or its replacement in `fixtures/`). The refactor in T2.5 will likely address this, but the AC should be explicit. |
| LOW | Anti-Pattern Coverage | `auth-flow.spec.ts:195` contains `toBeGreaterThanOrEqual(0)` -- same anti-pattern as dashboard.spec.ts. This file is not listed in FR-004 for rewriting. | auth-flow.spec.ts:195 | Add `auth-flow.spec.ts` to FR-004 audit scope, or explicitly exclude it with rationale (e.g., "auth-flow tests real auth, not content"). |
| LOW | Performance | No specification for Playwright test timeout tuning per route. Some pages (e.g., `/admin/pipeline` with stage timing tables, `/dashboard/insights` with charts) may need longer `waitForSelector` timeouts than the default 10s in assertion helpers. | spec.md:124 (AC-3.4) | The 10s default with explicit timeout parameter (AC-3.4) is adequate. Consider documenting expected render times for heavy pages in the factories or test comments. |

### Component Inventory

| Component | Type | Needs data-testid | Notes |
|-----------|------|-------------------|-------|
| mood-orb.tsx | Custom | Yes | Dashboard - maps to "score-ring" in spec |
| relationship-hero.tsx | Custom | Yes | Dashboard main card |
| score-detail-chart.tsx | Custom (Recharts) | Yes | Maps to "engagement-chart" concept |
| warmth-meter.tsx | Custom | Yes | Dashboard metric |
| vice-card.tsx | Custom | Yes | Player vices page |
| thought-feed.tsx | Custom | Yes | Nikita mind page |
| social-circle-gallery.tsx | Custom | Yes | Nikita circle page |
| life-event-timeline.tsx | Custom | Yes | Nikita day page |
| story-arc-viewer.tsx | Custom | Yes | Nikita stories page |
| diary-entry.tsx | Custom | Yes | Diary page |
| user-table.tsx | Custom | Yes | Admin user management |
| pipeline-board.tsx | Custom | Yes | Admin pipeline page |
| job-card.tsx | Custom | Yes | Admin jobs page |
| transcript-viewer.tsx | Custom | Yes | Admin conversation detail |
| user-detail.tsx | Custom | Yes | Admin user detail |
| kpi-card.tsx | Custom | Yes | Admin KPI metrics |
| empty-state.tsx | Shared | Yes | Generic empty state |
| loading-skeleton.tsx | Shared | Yes | Generic skeleton |
| error-boundary-wrapper.tsx | Shared | Yes | Generic error state |
| engagement-timeline.tsx | Chart | Yes | Dashboard engagement chart |
| vice-radar.tsx | Chart | Yes | Vice radar chart |

### Accessibility Checklist
- [x] axe-core integration exists (accessibility.spec.ts)
- [x] Keyboard navigation tests present
- [x] WCAG 2.1 AA tags used in axe scans
- [x] Color contrast audit (informational, not blocking)
- [x] `role="alert"` present in portal (conflict-banner, offline-banner, sr-announcer)
- [x] Focus management not impacted (no new interactive components)
- [ ] axe audits not extended to 15 new routes -- MEDIUM (see findings)

### Responsive Checklist
- [x] Desktop layout tested (1280x720 in playwright.config.ts)
- [x] Mobile viewport tested in mobile-nav.spec.ts (375x812)
- [ ] New route tests do not include mobile viewport -- MEDIUM (see findings)
- [x] Dark theme hardcoded (dark-only portal, no light mode to test)

### data-testid Strategy Assessment
- [x] Naming convention defined: `card-{name}`, `table-{name}`, `row-{index}`, `chart-{name}`, `nav-{name}`, `skeleton-{name}`, `empty-{name}`, `error-{name}`
- [x] Stable across refactors (not tied to CSS classes)
- [x] Kept in production (spec decision, minimal perf impact)
- [x] Playwright best practice followed
- [ ] Mapping to actual component files not explicit -- MEDIUM (see findings)

### Playwright Pattern Assessment
- [x] `page.route()` for browser-side API mocking -- correct, already used in 3 existing tests
- [x] Env-gated middleware bypass for server-side auth -- sound approach for Next.js SSR
- [x] Production guard (`NODE_ENV !== "production"`) -- correctly specified
- [x] `E2E_AUTH_BYPASS` not `NEXT_PUBLIC_` prefixed -- correctly specified
- [x] Two Playwright projects (player/admin) on separate ports -- good isolation
- [x] `context.addCookies()` NOT needed with env bypass approach -- correct simplification
- [x] Factory functions with TypeScript types and partial overrides -- composable pattern

### Anti-Pattern Verification (Codebase Confirmed)
The spec accurately identifies all existing anti-patterns:
- `.catch(() => false)`: 20 instances across 5 files (dashboard, data-viz, admin-mutations, player, mobile-nav) + 1 in fixtures.ts
- Triple-OR assertions: 7 instances across 4 files (dashboard, data-viz, admin-mutations, mobile-nav)
- `toBeGreaterThanOrEqual(0)`: 2 instances (dashboard:155, auth-flow:195)
- `body?.length > 0`: 8 instances across 4 files

### Recommendations

1. **MEDIUM: Explicit data-testid mapping table**
   - Add a table in spec.md mapping each `data-testid` value to its target component file path
   - Example: `data-testid="card-score-ring"` -> `portal/src/components/dashboard/mood-orb.tsx`
   - This prevents ambiguity during implementation and ensures the ~20 count is accurate

2. **MEDIUM: Decide on mobile viewport coverage for new routes**
   - Either add `test.describe("mobile", ...)` blocks to new spec files with `page.setViewportSize({ width: 375, height: 812 })`
   - Or add a note: "Mobile viewport testing for new routes is deferred to a future spec"

3. **MEDIUM: Extend axe audits or explicitly defer**
   - Option A: Add `accessibility.spec.ts` tests for `/dashboard/nikita`, `/dashboard/insights`, `/admin/pipeline`
   - Option B: Add to spec: "Accessibility audits for new routes are out of scope (covered by existing axe tests on /dashboard and /admin parent routes)"

4. **MEDIUM: Dark mode chart rendering**
   - Since mock data will now deterministically render charts, add a basic check that chart SVGs have non-white fill colors (confirms dark theme applies to data viz)

5. **LOW: Include fixtures.ts in anti-pattern cleanup AC**
   - Change AC-4.1 to include `portal/e2e/fixtures.ts` (or note it's addressed by T2.5 refactor)
   - Change AC-4.5 scope to: "Zero `.catch(() =>` patterns remain in `portal/e2e/**/*` after completion"

6. **LOW: Add auth-flow.spec.ts to anti-pattern audit**
   - `auth-flow.spec.ts:195` has `toBeGreaterThanOrEqual(0)` -- should be reviewed

7. **LOW: Document render time expectations**
   - Add comments in factory files noting which pages are expected to be heavier (pipeline with tables, insights with charts)

### Overall Assessment

This is a well-structured testing infrastructure spec. The approach (Hybrid A+C with env-gated auth bypass) is sound for Next.js 16 with Supabase SSR middleware. The phased PR strategy (Phase A: infra + fixes, Phase B: new coverage) correctly manages blast radius. All anti-patterns identified in the spec were verified against the actual codebase. The `data-testid` naming convention follows Playwright best practices.

The 5 MEDIUM findings are all about completeness/explicitness rather than fundamental design issues. None block implementation. The spec can proceed to implementation planning as-is, with the recommendations addressed as minor amendments.
