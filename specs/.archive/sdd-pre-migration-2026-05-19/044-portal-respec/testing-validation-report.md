## Testing Validation Report

**Spec:** /Users/yangsim/Nanoleq/sideProjects/nikita/specs/044-portal-respec/spec.md
**Status:** FAIL
**Timestamp:** 2026-02-08T00:00:00Z

### Summary
- CRITICAL: 3
- HIGH: 5
- MEDIUM: 4
- LOW: 3

---

### Findings

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| CRITICAL | Test Strategy | No testing strategy section in specification | spec.md (entire file) | Add "## Testing Strategy" section with approach, test types, tools, and TDD methodology |
| CRITICAL | Testing Pyramid | No testing pyramid definition or balance targets | spec.md (entire file) | Define unit/integration/E2E split with targets (~70% unit, ~20% integration, ~10% E2E) |
| CRITICAL | TDD Enablement | Acceptance criteria not testable (vague success conditions) | spec.md:38-228 (all FRs) | Rewrite all ACs to be SMART: Specific, Measurable, Automated, Reproducible |
| HIGH | Unit Tests | No unit test requirements specified | plan.md, tasks.md | Add unit test tasks for components, hooks, utilities with coverage targets (≥80%) |
| HIGH | Integration Tests | No integration test scenarios for API→Frontend | plan.md, tasks.md | Define integration tests for TanStack Query hooks + API contract validation |
| HIGH | E2E Tests | E2E tests incomplete (missing critical flows) | tasks.md:502-525 | Add E2E tests for: settings changes, vice discovery flow, conversation detail, diary view, admin filters |
| HIGH | Coverage Targets | No coverage thresholds defined | spec.md (missing section) | Specify: Overall 80%, Critical paths 95%, Components 85%, Hooks 90%, Utils 95% |
| HIGH | Mock Strategy | No mock/stub strategy for API integration | spec.md, plan.md | Define MSW (Mock Service Worker) for API mocking; outline fixture data structure |
| MEDIUM | Component Tests | Component test requirements missing | tasks.md:T7.x | Add component test tasks (Vitest + Testing Library) for 15+ components |
| MEDIUM | CI/CD Integration | No CI/CD test execution requirements | spec.md (NFR missing) | Add NFR for CI pipeline: lint → type-check → unit → integration → E2E on PR/deploy |
| MEDIUM | Test Isolation | No test isolation patterns specified | spec.md, plan.md | Define fixture strategy, test database reset, parallel execution constraints |
| MEDIUM | Accessibility Testing | Manual accessibility audit insufficient | tasks.md:T7.5 | Add automated a11y checks in component tests (jest-axe); run axe on every component |
| LOW | Test Data | No test data generation strategy | spec.md, plan.md | Document fixture factories for user stats, score history, conversations (faker.js) |
| LOW | Performance Testing | No performance test requirements | spec.md (NFR-001 lacks tests) | Add Lighthouse CI thresholds: LCP <2s, FID <100ms, CLS <0.1 in CI pipeline |
| LOW | Visual Regression | No visual regression testing | tasks.md:T7.1 | Add Playwright screenshot comparison for critical views (dashboard, admin overview) |

---

### Testing Pyramid Analysis

**Target (Best Practice):**
```
     E2E: 10% (~30 tests)
      ↑
Integration: 20% (~60 tests)
      ↑
    Unit: 70% (~210 tests)
```

**Actual in Spec:**
```
     E2E: 100% (6 tests — all specified)
      ↑
Integration: 0% (0 tests — MISSING)
      ↑
    Unit: 0% (0 tests — MISSING)
```

**Verdict:** ❌ **INVERTED PYRAMID** — Spec only defines E2E tests. Unit and integration tests completely absent.

**Impact:**
- E2E tests are slow (minutes), brittle, expensive to maintain
- Without unit tests, bugs surface late in E2E phase
- Without integration tests, API contract mismatches undetected until E2E
- TDD workflow impossible (no unit tests to write first)

**Required Fix:**
1. Add ~210 unit tests across 7 phases (30 tests/phase)
2. Add ~60 integration tests (API hooks + Supabase auth + data fetching)
3. Keep 6 E2E tests + add 24 more for coverage (~30 total)

---

### AC Testability Analysis

| AC ID | AC Description | Testable | Test Type | Issue |
|-------|----------------|----------|-----------|-------|
| FR-001 | "Unauthenticated users redirect to /login" | ✅ YES | E2E, Integration | Clear pass/fail condition |
| FR-001 | "Valid sessions persist across page navigations" | ⚠️ PARTIAL | E2E | Vague "persist" — define: session token in cookies, no re-auth for N minutes |
| FR-004 | "Ring animates on load" | ❌ NO | Unit | "Animates" not measurable — specify: animation duration 1s, easing cubic-bezier, final transform scale(1) |
| FR-004 | "Color matches threshold" | ✅ YES | Unit | Clear: score < 30 → red, 30-55 → amber, 55-75 → cyan, >75 → rose |
| FR-004 | "Boss bar visible only during boss_fight" | ✅ YES | Unit, Integration | Clear boolean condition |
| FR-005 | "Chart renders 30-day data" | ⚠️ PARTIAL | Integration | Ambiguous "renders" — specify: 30 data points in DOM, x-axis labels match dates |
| FR-005 | "Event markers show on hover" | ❌ NO | E2E | "Show" not testable — specify: tooltip DOM element visible, contains event type + score |
| FR-006 | "Animation plays once" | ❌ NO | Unit | How to verify "once"? Specify: framer-motion initial={scale: 0} animate={scale: 1} transition once |
| FR-007 | "Current state glows" | ❌ NO | Unit | "Glows" not testable — specify: CSS class `.glow` applied, box-shadow value rgba(255,105,180,0.6) |
| FR-008 | "Timer counts down" | ⚠️ PARTIAL | Integration | Missing: countdown interval (1s?), does it stop at 0? |
| FR-009 | "Undiscovered appear locked" | ✅ YES | Unit | Clear: CSS class `.blur`, icon "?" rendered |
| FR-010 | "List paginated" | ⚠️ PARTIAL | Integration | Missing: page size, total count header, "next" button disabled on last page |
| FR-011 | "Tone color correct" | ✅ YES | Unit | Clear mapping: pink/gray/blue |
| FR-012 | "Settings save correctly" | ❌ NO | Integration | Vague "correctly" — specify: PUT returns 200, useSettings refetches, toast shown |
| FR-012 | "Telegram link generates code" | ⚠️ PARTIAL | Integration | Missing: code format (6 digits?), expiry time |
| FR-015 | "Loading shows skeletons" | ✅ YES | Unit | Clear: Skeleton component rendered while isLoading=true |
| FR-015 | "API errors show retry" | ✅ YES | Unit, Integration | Clear: error boundary renders, "Retry" button present |
| FR-016 | "6 KPI cards render with correct data" | ⚠️ PARTIAL | Integration | Missing: define "correct" — match backend schema? specific field names? |
| FR-017 | "Search returns matching users" | ⚠️ PARTIAL | Integration | Missing: search algorithm (substring? fuzzy?), debounce time (300ms per plan) |
| FR-019 | "All 6 existing mutations work" | ✅ YES | Integration, E2E | Clear: 6 endpoints, each returns 200, data updated |
| FR-020 | "9 stages render with correct names" | ✅ YES | Integration | Clear: names match Spec 042 |
| FR-026 | "Both endpoints return real data" | ✅ YES | Integration | Clear: non-empty response, specific fields present |
| FR-030 | "Prompt preview returns actual prompt" | ✅ YES | Integration | Clear: non-stub, uses PromptGenerator |
| NFR-001 | "Initial page load < 2s (LCP)" | ✅ YES | Performance | Clear metric via Lighthouse |
| NFR-002 | "WCAG 2.1 AA compliance" | ✅ YES | Accessibility | Clear via axe-core |
| NFR-005 | "Strict TypeScript, no `any` types" | ✅ YES | Static Analysis | Clear: tsc --strict, eslint @typescript-eslint/no-explicit-any error |

**Testability Score: 12/25 CLEAR, 9/25 PARTIAL, 4/25 UNTESTABLE**

---

### Test Scenario Inventory

#### E2E Scenarios (Specified)

| Scenario | Priority | User Flow | Status |
|----------|----------|-----------|--------|
| Auth Flow | P1 | Login → magic link → redirect → session persist | ✅ Specified (T7.2) |
| Player Dashboard | P1 | Load dashboard → see score ring + timeline + radar | ✅ Specified (T7.3) |
| Admin Mutations | P1 | Admin → user detail → god mode → set score → confirm | ✅ Specified (T7.4) |
| Accessibility | P2 | axe-core audit all pages | ✅ Specified (T7.5) |

#### E2E Scenarios (MISSING — Critical Gaps)

| Scenario | Priority | User Flow | Status |
|----------|----------|-----------|--------|
| Settings Update | P1 | Dashboard → settings → change timezone → save → persist | ❌ MISSING |
| Telegram Link | P1 | Settings → link Telegram → code display → verify status | ❌ MISSING |
| Account Deletion | P1 | Settings → danger zone → confirm → logout | ❌ MISSING |
| Conversation Detail | P2 | Conversations → click row → expand messages → scroll | ❌ MISSING |
| Admin User Search | P1 | Admin → users → search "test" → filter chapter 2 → results | ❌ MISSING |
| Admin Pipeline Trigger | P2 | Admin → user → trigger pipeline → job ID returned | ❌ MISSING |
| Vice Discovery Flow | P2 | Dashboard → vices → see discovered → locked blurred | ❌ MISSING |
| Decay Warning Urgent | P2 | Dashboard → engagement → grace < 25% → CTA pulse | ❌ MISSING |
| Mobile Navigation | P2 | Mobile viewport → bottom tabs → navigate → sidebar sheet | ❌ MISSING |

**E2E Coverage: 4/13 flows = 31%** (Target: 80%+ for critical paths)

---

#### Integration Test Points (MISSING)

| Component | Integration Point | Mock Required |
|-----------|-------------------|---------------|
| useUserStats | GET /api/v1/portal/stats | ✅ MSW handler |
| useScoreHistory | GET /api/v1/portal/score-history | ✅ MSW handler |
| useEngagement | GET /api/v1/portal/engagement | ✅ MSW handler |
| useDecay | GET /api/v1/portal/decay | ✅ MSW handler |
| useVices | GET /api/v1/portal/vices | ✅ MSW handler |
| useConversations | GET /api/v1/portal/conversations + /conversations/{id} | ✅ MSW handler |
| useSummaries | GET /api/v1/portal/daily-summaries | ✅ MSW handler |
| useSettings | GET/PUT /api/v1/portal/settings | ✅ MSW handler |
| useAdminUsers | GET /api/v1/admin/users (search, filter, paginate) | ✅ MSW handler |
| useAdminMutations | PUT/POST /api/v1/admin/users/{id}/* (6 mutations) | ✅ MSW handler |
| Supabase Auth | createClient, getSession, signOut | ✅ Supabase mock |
| API Client | Auth header injection, error handling | ✅ fetch mock |

**Integration Test Estimate: ~60 tests** (5 tests/hook × 12 hooks)

---

#### Unit Test Coverage (MISSING)

| Module | Functions | Coverage Target |
|--------|-----------|------------------|
| **Charts** | ScoreRing, ScoreTimeline, RadarMetrics, Sparkline | 85% (animation logic, color thresholds, data transforms) |
| **Components** | 15 dashboard + 8 admin + 3 shared = 26 components | 85% (props, conditional render, event handlers) |
| **Hooks** | 12 TanStack Query hooks | 90% (query keys, stale time, error states, mutations) |
| **Utils** | cn(), formatScore(), formatDate(), formatDuration() | 95% (edge cases: null, undefined, large numbers) |
| **API Client** | Auth injection, error parsing, retry logic | 90% (401 handling, network errors, timeout) |
| **Forms** | Zod schemas (settings, mutations) | 95% (validation rules, error messages) |
| **Glassmorphism** | GlassCard variants (default, elevated, danger) | 85% (className merging, forwarded ref) |

**Unit Test Estimate: ~210 tests**
- Charts: 4 components × 8 tests = 32
- Components: 26 components × 4 tests = 104
- Hooks: 12 hooks × 5 tests = 60
- Utils: 4 utils × 3 tests = 12
- API Client: 1 module × 6 tests = 6
- Forms: 2 schemas × 4 tests = 8

---

### TDD Readiness Checklist

- [ ] **ACs are specific** — 9/25 ACs fail (vague: "animates", "glows", "correctly")
- [ ] **ACs are measurable** — 13/25 ACs lack quantifiable success criteria
- [ ] **Test types clear per AC** — No mapping of AC → test type in spec
- [ ] **Red-green-refactor path clear** — Impossible without unit test requirements

**Verdict:** ❌ **NOT READY FOR TDD**

**Blockers:**
1. No unit tests defined → can't write failing tests first
2. Vague ACs → can't determine test pass/fail
3. No test-first workflow → spec assumes implementation → tests order

**Required Changes for TDD:**
1. Rewrite all 25 ACs to be SMART (see recommendations below)
2. Add unit test tasks to tasks.md (T2.X, T3.X for each component)
3. Add "Test-First Protocol" section: write tests → see red → implement → see green

---

### Coverage Requirements

- [ ] **Overall target specified** — MISSING (recommend 80%)
- [ ] **Critical path coverage** — MISSING (recommend 95% for auth, mutations, payment flows)
- [ ] **Branch coverage** — MISSING (recommend 75%)
- [ ] **Exclusions documented** — MISSING (recommend: autogenerated shadcn components, types.ts)

**Recommendations:**
```markdown
## Coverage Targets (add to spec.md)

| Layer | Target | Enforcement |
|-------|--------|-------------|
| Overall | 80% | CI fails if < 80% |
| Components | 85% | Per-component threshold |
| Hooks | 90% | Critical for data fetching |
| Utils | 95% | Pure functions, high value |
| API Client | 90% | Auth logic critical |
| E2E Critical Paths | 95% | Auth, mutations, settings |

**Exclusions:**
- `src/components/ui/*` (autogenerated shadcn primitives — tested upstream)
- `src/lib/api/types.ts` (TypeScript definitions, no logic)
- `*.config.ts` (build configs, tested by framework)
```

---

### Recommendations

#### 1. Add Testing Strategy Section to spec.md (CRITICAL)

**Insert after line 332 (before Appendix):**

```markdown
## Testing Strategy

### Approach

**Test-Driven Development (TDD) Workflow:**
1. Write failing test for AC
2. Implement minimal code to pass
3. Refactor while keeping tests green
4. Repeat for next AC

**Testing Pyramid (70-20-10):**
- **70% Unit Tests** (~210 tests): Components, hooks, utils, forms
- **20% Integration Tests** (~60 tests): API hooks, Supabase auth, data fetching
- **10% E2E Tests** (~30 tests): Critical user flows end-to-end

### Tools

| Layer | Tool | Purpose |
|-------|------|---------|
| Unit | Vitest + Testing Library | Component/hook/util tests, fast execution |
| Integration | MSW (Mock Service Worker) | API mocking, contract validation |
| E2E | Playwright | Browser automation, cross-browser testing |
| Accessibility | jest-axe + axe-playwright | WCAG 2.1 AA compliance |
| Visual | Playwright Screenshots | Regression detection |
| Coverage | Vitest Coverage (c8) | Enforce 80% threshold |

### Test Infrastructure

- **Fixtures:** Faker.js for test data generation (user stats, conversations, scores)
- **Mocks:** MSW handlers for all 12 portal + 30 admin endpoints
- **Supabase:** Mock client for auth flows (login, session, logout)
- **Isolation:** Each test resets fixtures, no shared state
- **Parallelization:** Vitest parallel by default, Playwright sharded in CI

### CI/CD Integration

```yaml
on: [pull_request, push]
jobs:
  test:
    - Lint (ESLint + Prettier)
    - Type-check (tsc --noEmit)
    - Unit tests (Vitest, 80% coverage required)
    - Integration tests (Vitest + MSW)
    - E2E tests (Playwright, critical paths)
    - Accessibility (axe-core on all pages)
    - Lighthouse CI (LCP < 2s, FID < 100ms)
```

Deployment blocked if any stage fails.
```

---

#### 2. Rewrite Vague ACs to be SMART (CRITICAL)

**Current (FR-004):**
```
- AC: Ring animates on load; color matches threshold; boss bar visible only during boss_fight
```

**Fixed:**
```
- AC-004.1: Score ring animates from 0 to actual score over 1s with cubic-bezier(0.4, 0, 0.2, 1) easing on mount
- AC-004.2: Ring color matches threshold: score < 30 → #ef4444 (red), 30-55 → #f59e0b (amber), 55-75 → #06b6d4 (cyan), >75 → #f43f5e (rose)
- AC-004.3: Boss progress bar (Progress component) renders when game_status="boss_fight", value={progress_to_boss}, max={boss_threshold}
- AC-004.4: Boss progress bar hidden when game_status ≠ "boss_fight"
- **Unit Test:** `describe('ScoreRing', () => { test('animates score from 0 to 75 over 1s', ...) })`
```

**Current (FR-005):**
```
- AC: Chart renders 30-day data; event markers show on hover; responsive on mobile
```

**Fixed:**
```
- AC-005.1: ScoreTimeline renders AreaChart with data.length === 30 when score-history returns 30 points
- AC-005.2: AreaChart x-axis shows dates from (today - 30d) to today in MM/DD format
- AC-005.3: Event markers render as CustomDot: star (event_type="boss"), diamond (event_type="chapter"), circle (event_type="conversation")
- AC-005.4: Tooltip displays on marker hover: "<score> — <event_type> on <date>"
- AC-005.5: Chart height 200px on mobile (<768px), 280px on desktop (≥768px)
- **Integration Test:** `test('fetches 30-day score history and renders 30 data points', ...) `
```

**Current (FR-012):**
```
- AC: Settings save correctly; Telegram link generates code; deletion requires confirmation
```

**Fixed:**
```
- AC-012.1: Settings form submits on "Save" → PUT /portal/settings → returns 200 → useSettings refetches → toast.success("Settings saved")
- AC-012.2: Form validation: timezone required (Zod), email read-only
- AC-012.3: "Link Telegram" button → POST /portal/link-telegram → returns {code: "ABC123", expires_in: 300} → code displayed in input (read-only)
- AC-012.4: "Delete Account" button → Dialog opens → requires typing "DELETE" → POST /portal/account DELETE → signOut() → redirect to /login
- **E2E Test:** `test('settings update persists across page refresh', ...) `
```

**Repeat for all 25 FRs.**

---

#### 3. Add Unit Test Tasks to tasks.md (HIGH)

**Insert after Phase 2:**

```markdown
### T2.10: Unit Tests — Charts
- **US**: US-1, US-2, US-3 | **Priority**: P1
- **Files**: `src/components/charts/__tests__/score-ring.test.tsx`, `score-timeline.test.tsx`, `radar-metrics.test.tsx`, `sparkline.test.tsx`
- **ACs**:
  - [ ] ScoreRing: animation timing, color thresholds (4 ranges), props (score, size, strokeWidth)
  - [ ] ScoreTimeline: data rendering (30 points), event markers (3 types), tooltip content, responsive height
  - [ ] RadarMetrics: 4 axes rendered, data mapping, animation, trend arrows
  - [ ] Sparkline: trend line rendering, positive/negative color, data scaling
  - [ ] **Target**: 32 tests, 85% coverage

### T2.11: Unit Tests — Dashboard Components
- **US**: US-1, US-2, US-3 | **Priority**: P1
- **Files**: `src/components/dashboard/__tests__/*.test.tsx`
- **ACs**:
  - [ ] RelationshipHero: boss bar conditional, badge rendering, layout
  - [ ] HiddenMetrics: metric labels, weight percentages, responsive radar→bar
  - [ ] **Target**: 8 tests, 85% coverage

### T2.12: Integration Tests — Portal Hooks
- **US**: US-1, US-2, US-3 | **Priority**: P1
- **Files**: `src/hooks/__tests__/use-user-stats.test.ts`, `use-score-history.test.ts`
- **ACs**:
  - [ ] MSW handlers for GET /portal/stats and /portal/score-history
  - [ ] useUserStats: loading state, success data, error state, staleTime 30s
  - [ ] useScoreHistory: 30-day param, data transformation, pagination
  - [ ] **Target**: 10 tests, 90% coverage
```

**Repeat for Phases 3-6.**

---

#### 4. Define Integration Test Strategy (HIGH)

**Insert in plan.md after "Data Fetching Strategy" (line 157):**

```markdown
### Integration Testing Strategy

**MSW Setup:**
```typescript
// src/mocks/handlers.ts
import { http, HttpResponse } from 'msw'

export const handlers = [
  http.get('/api/v1/portal/stats', () => {
    return HttpResponse.json({
      id: 'user-123',
      relationship_score: 75,
      chapter: 3,
      // ... full UserStatsResponse fixture
    })
  }),
  // ... 42 more handlers for all endpoints
]
```

**Test Pattern:**
```typescript
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useUserStats } from '@/hooks/use-user-stats'

test('useUserStats fetches and returns user stats', async () => {
  const queryClient = new QueryClient()
  const wrapper = ({ children }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )

  const { result } = renderHook(() => useUserStats(), { wrapper })

  await waitFor(() => expect(result.current.isSuccess).toBe(true))
  expect(result.current.data?.relationship_score).toBe(75)
  expect(result.current.data?.chapter).toBe(3)
})
```

**Fixture Management:**
- Central `fixtures/` directory with typed data factories
- Faker.js for realistic data generation
- Separate fixtures per domain: users, scores, conversations, etc.
```

---

#### 5. Add Missing E2E Test Tasks (HIGH)

**Insert in tasks.md Phase 7:**

```markdown
### T7.7: E2E — Settings & Telegram
- **US**: US-4 | **Priority**: P1
- **Files**: `portal/tests/settings.spec.ts`
- **ACs**:
  - [ ] Update timezone → save → refresh page → timezone persists
  - [ ] Link Telegram → code displayed → status shows "Pending"
  - [ ] Delete account → type DELETE → confirm → redirects to /login

### T7.8: E2E — Conversations & Diary
- **US**: US-11, US-13 | **Priority**: P2
- **Files**: `portal/tests/conversations.spec.ts`
- **ACs**:
  - [ ] Conversation list loads → click row → messages expand → scroll works
  - [ ] Diary page shows entries → tone colors correct → score delta visible

### T7.9: E2E — Admin Search & Filters
- **US**: US-5 | **Priority**: P1
- **Files**: `portal/tests/admin-users.spec.ts`
- **ACs**:
  - [ ] Search "test" → matching users displayed
  - [ ] Filter chapter=2 + status=active → results updated
  - [ ] Sort by score descending → order verified

### T7.10: E2E — Mobile Navigation
- **US**: All | **Priority**: P2
- **Files**: `portal/tests/mobile.spec.ts`
- **ACs**:
  - [ ] Viewport 375px → bottom tabs visible → navigate → active tab highlighted
  - [ ] Hamburger opens sidebar sheet → close button works
```

---

#### 6. Add Coverage Enforcement to NFRs (MEDIUM)

**Insert in spec.md NFR section (after NFR-005):**

```markdown
**NFR-006**: Test Coverage
- Overall: 80% (CI fails if below)
- Components: 85%
- Hooks: 90%
- Utils: 95%
- Critical paths (auth, mutations): 95%
- Branch coverage: 75%
- Exclusions: `src/components/ui/*` (shadcn), `*.config.ts`, `types.ts`

**NFR-007**: CI/CD Testing
- All PRs must pass: lint, type-check, unit, integration, E2E
- E2E runs on Playwright sharded (3 workers)
- Lighthouse CI enforces: LCP < 2s, FID < 100ms, CLS < 0.1
- Deployment blocked if any test fails
```

---

#### 7. Document Mock Strategy (MEDIUM)

**Add to plan.md Phase 7:**

```markdown
### Mock Service Worker (MSW) Configuration

**Installation:**
```bash
pnpm add -D msw @mswjs/http-middleware
```

**Setup:**
```typescript
// src/mocks/browser.ts
import { setupWorker } from 'msw/browser'
import { handlers } from './handlers'
export const worker = setupWorker(...handlers)

// src/mocks/server.ts (for Node tests)
import { setupServer } from 'msw/node'
import { handlers } from './handlers'
export const server = setupServer(...handlers)

// vitest.setup.ts
import { beforeAll, afterEach, afterAll } from 'vitest'
import { server } from './src/mocks/server'

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())
```

**Handler Example:**
```typescript
// src/mocks/handlers/portal.ts
export const portalHandlers = [
  http.get('/api/v1/portal/stats', () => {
    return HttpResponse.json(userStatsFixture())
  }),
  http.get('/api/v1/portal/score-history', ({ request }) => {
    const url = new URL(request.url)
    const days = url.searchParams.get('days') || '30'
    return HttpResponse.json(scoreHistoryFixture(parseInt(days)))
  }),
]
```

**Supabase Mock:**
```typescript
// src/mocks/supabase.ts
export const createMockSupabaseClient = () => ({
  auth: {
    getSession: vi.fn().mockResolvedValue({ data: { session: mockSession } }),
    signOut: vi.fn().mockResolvedValue({ error: null }),
  },
})
```
```

---

#### 8. Add Component Test Examples (LOW)

**Add to tasks.md T2.10 acceptance criteria:**

```markdown
- **Example Test (ScoreRing):**
  ```typescript
  import { render, screen } from '@testing-library/react'
  import { ScoreRing } from '../score-ring'

  describe('ScoreRing', () => {
    test('renders with correct score', () => {
      render(<ScoreRing score={75} />)
      expect(screen.getByText('75')).toBeInTheDocument()
    })

    test('applies rose color for score > 75', () => {
      const { container } = render(<ScoreRing score={80} />)
      const ring = container.querySelector('.score-ring')
      expect(ring).toHaveStyle({ '--ring-color': 'var(--color-rose)' })
    })

    test('animates from 0 to score on mount', async () => {
      render(<ScoreRing score={75} />)
      // Framer Motion test: verify initial={0} animate={75}
      await waitFor(() => expect(screen.getByText('75')).toBeInTheDocument())
    })
  })
  ```
```

---

#### 9. Add Accessibility Testing Requirements (MEDIUM)

**Insert in tasks.md T7.5:**

```markdown
### T7.5: Accessibility — Automated + Manual
- **US**: All | **Priority**: P2 | **NFR**: NFR-002
- **Files**: `portal/tests/accessibility.spec.ts`, component tests with jest-axe
- **ACs**:
  - [ ] **Automated (jest-axe):** Every component test includes `expect(await axe(container)).toHaveNoViolations()`
  - [ ] **E2E (axe-playwright):** All pages scanned: dashboard, settings, admin overview, user detail
  - [ ] **Manual checks:** Keyboard navigation (Tab order), screen reader labels (NVDA/VoiceOver), focus visible
  - [ ] **Chart accessibility:** aria-labels on ScoreRing ("Relationship score: 75 out of 100"), RadarChart ("Hidden metrics: Intimacy 70, Passion 60, Trust 80, Secureness 65")
  - [ ] **WCAG violations:** 0 critical, 0 serious (moderate/minor acceptable with justification)
  - [ ] **Contrast:** 4.5:1 minimum on glass surfaces (verify with Chrome DevTools)
```

---

#### 10. Add Performance Testing to CI (LOW)

**Insert in spec.md NFR-001:**

```markdown
**Performance Testing (CI Enforcement):**
- Lighthouse CI runs on every PR
- Thresholds (blocking):
  - LCP (Largest Contentful Paint): < 2.0s
  - FID (First Input Delay): < 100ms
  - CLS (Cumulative Layout Shift): < 0.1
  - Performance Score: ≥ 90
- Bundle size budget: 200KB initial JS (gzip), 500KB total (with charts lazy-loaded)
- Recharts code-split: `const Chart = lazy(() => import('./chart'))`
```

---

### Final Summary

**Current State:** Specification is implementation-ready but **NOT test-ready**.

**Core Issues:**
1. **No testing pyramid** — only E2E tests defined (inverted pyramid)
2. **Vague ACs** — 13/25 lack measurable success criteria
3. **No TDD workflow** — unit tests not specified, can't write tests first
4. **Missing coverage targets** — no enforcement or thresholds
5. **No mock strategy** — integration tests impossible without API mocks

**Path to PASS:**
1. ✅ Add "Testing Strategy" section to spec.md (pyramid, tools, TDD workflow)
2. ✅ Rewrite all 25 FRs with SMART ACs (specific, measurable, automated, reproducible)
3. ✅ Add ~210 unit test tasks to tasks.md (Phases 2-6)
4. ✅ Add ~60 integration test tasks (MSW + hooks)
5. ✅ Expand E2E tests from 6 to ~30 (add 9 missing critical flows)
6. ✅ Define coverage targets in NFRs (80% overall, 95% critical)
7. ✅ Document MSW setup + fixture strategy in plan.md
8. ✅ Add accessibility automation (jest-axe in component tests)
9. ✅ Add Lighthouse CI thresholds to NFR-001

**Effort Estimate:** 4-6 hours to update spec/plan/tasks artifacts.

**Post-Fix:** Re-run all 6 validators (this validator will PASS with 0 CRITICAL, 0 HIGH findings).

---

## Appendix: Test Estimate Breakdown

| Test Type | Count | Avg Time/Test | Total Effort |
|-----------|-------|---------------|--------------|
| Unit (Components) | 104 | 5 min | 8.7 hours |
| Unit (Charts) | 32 | 8 min | 4.3 hours |
| Unit (Hooks logic) | 60 | 4 min | 4 hours |
| Unit (Utils) | 12 | 3 min | 0.6 hours |
| Integration (Hooks + MSW) | 60 | 10 min | 10 hours |
| E2E (Critical flows) | 30 | 15 min | 7.5 hours |
| Accessibility | 10 | 10 min | 1.7 hours |
| **Total** | **308** | **avg 7 min** | **36.8 hours** |

**Estimated Implementation Time (TDD):**
- Phase 2 (Player Core): 6-8h implementation + 4h tests = **10-12h**
- Phase 3 (Player Features): 8-12h implementation + 6h tests = **14-18h**
- Phase 4 (Admin Core): 8-10h implementation + 5h tests = **13-15h**
- Phase 5 (Admin Features): 6-8h implementation + 4h tests = **10-12h**
- Phase 6 (Backend): 4-6h implementation + 2h tests = **6-8h**
- Phase 7 (Testing): 4-6h (E2E + accessibility + Lighthouse) = **4-6h**

**Total with Tests: 57-71 hours** (vs original estimate 42-59h without proper testing)

**Testing adds ~30% to implementation time but prevents 10x cost in production bugs.**
