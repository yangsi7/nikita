# Tasks: Spec 044 — Portal Respec

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
**Created**: 2026-02-07
**Total**: 55 tasks | ~300 tests estimated

---

## Phase 0: Project Setup

### T0.1: Scaffold Next.js 15 Project
- **US**: Setup | **Priority**: P0
- **Files**: `portal/package.json`, `portal/next.config.ts`, `portal/tsconfig.json`, `portal/postcss.config.mjs`
- **ACs**:
  - [x] `npx create-next-app@latest` with App Router, TypeScript strict, Tailwind CSS
  - [x] `pnpm add recharts framer-motion @supabase/ssr @tanstack/react-query react-hook-form zod`
  - [x] Dev server starts without errors

### T0.2: Configure shadcn/ui
- **US**: Setup | **Priority**: P0
- **Files**: `portal/components.json`, `portal/src/components/ui/*`
- **ACs**:
  - [x] `npx shadcn@latest init` with New York style, CSS variables, dark theme
  - [x] Add 23 primitives: Card, Badge, Table, Dialog, Tabs, Progress, Skeleton, Sidebar, Avatar, Tooltip, Input, Select, Switch, Separator, ScrollArea, Sheet, Breadcrumb, DropdownMenu, Alert, Accordion, Slider, Form, Button
  - [x] All components importable without errors

### T0.3: Design Token System
- **US**: Setup | **Priority**: P0
- **Files**: `portal/src/app/globals.css`, `portal/tailwind.config.ts`
- **ACs**:
  - [x] All design tokens from product brief Section 6 defined as CSS variables
  - [x] Tailwind config extends with custom colors, blur, glow, radius, spacing
  - [x] Glassmorphism utility classes: `.glass-card`, `.glass-card-elevated`, `.glass-card-danger`

### T0.4: Vercel Deployment Config
- **US**: Setup | **Priority**: P0
- **Files**: `portal/vercel.json`, `portal/.env.example`
- **ACs**:
  - [x] API rewrites to backend URL
  - [x] Environment variables documented in `.env.example`
  - [x] Build succeeds on Vercel

---

## Phase 1: Design System + Auth

### T1.1: GlassCard Component
- **US**: All | **Priority**: P0
- **Files**: `src/components/glass/glass-card.tsx`, `src/components/glass/glass-panel.tsx`
- **ACs**:
  - [ ] Three variants: default, elevated, danger (red border)
  - [ ] Accepts children, className, onClick; forwarded ref
  - [ ] Matches glassmorphism tokens (blur, border, shadow)

### T1.2: Supabase Auth Setup
- **US**: US-4 | **Priority**: P1 | **FR**: FR-001
- **Files**: `src/lib/supabase/client.ts`, `src/lib/supabase/server.ts`, `src/lib/supabase/middleware.ts`
- **ACs**:
  - [ ] Browser client for client components
  - [ ] Server client for RSC/API routes
  - [ ] Middleware refreshes tokens, reads session

### T1.3: Login Page
- **US**: US-4 | **Priority**: P1 | **FR**: FR-001
- **Files**: `src/app/login/page.tsx`
- **ACs**:
  - [ ] Magic link email input + submit; OTP fallback
  - [ ] Loading state during auth; error messages displayed
  - [ ] Redirect to `/dashboard` on success

### T1.4: Auth Callback Route
- **US**: US-4 | **Priority**: P1 | **FR**: FR-001
- **Files**: `src/app/auth/callback/route.ts`
- **ACs**:
  - [ ] Handles PKCE code exchange
  - [ ] Redirects to `/dashboard` (player) or `/admin` (admin) based on role

### T1.5: Next.js Auth Middleware
- **US**: US-4, US-5 | **Priority**: P1 | **FR**: FR-002
- **Files**: `portal/middleware.ts`
- **ACs**:
  - [ ] Unauthenticated → redirect to `/login`
  - [ ] `/admin/*` requires admin role; wrong role → 403 page
  - [ ] `/dashboard/*` allows any authenticated user

### T1.6: Sidebar Component
- **US**: US-1, US-5 | **Priority**: P1 | **FR**: FR-013, FR-025
- **Files**: `src/components/layout/sidebar.tsx`, `src/components/layout/sidebar-item.tsx`, `src/components/layout/mobile-nav.tsx`
- **ACs**:
  - [ ] Collapse/expand toggle (48px ↔ 240px)
  - [ ] Player variant (rose accent) and admin variant (cyan accent)
  - [ ] Mobile: bottom tab bar with 5 items + hamburger

### T1.7: Providers + Root Layout
- **US**: All | **Priority**: P0
- **Files**: `src/app/providers.tsx`, `src/app/layout.tsx`
- **ACs**:
  - [ ] QueryClientProvider wraps app
  - [ ] Inter + JetBrains Mono fonts loaded
  - [ ] Dark background applied to body (`bg-void`)

### T1.8: Shared Components
- **US**: All | **Priority**: P0 | **FR**: FR-015
- **Files**: `src/components/shared/loading-skeleton.tsx`, `src/components/shared/error-boundary.tsx`, `src/components/shared/empty-state.tsx`
- **ACs**:
  - [ ] LoadingSkeleton renders pulse animation matching glass cards
  - [ ] ErrorBoundary catches render errors, shows retry button
  - [ ] EmptyState shows message + optional illustration

---

## Phase 2: Player Dashboard Core (P1)

### T2.1: API Client + Types
- **US**: All | **Priority**: P0
- **Files**: `src/lib/api/client.ts`, `src/lib/api/types.ts`, `src/lib/utils.ts`, `src/lib/constants.ts`
- **ACs**:
  - [ ] Fetch wrapper injects Supabase auth token
  - [ ] All backend response types mirrored in TypeScript (strict, no `any`)
  - [ ] Utility functions: `cn()`, `formatScore()`, `formatDate()`, `formatDuration()`

### T2.2: Portal API Functions
- **US**: US-1, US-2, US-3 | **Priority**: P1
- **Files**: `src/lib/api/portal.ts`
- **ACs**:
  - [ ] 12 typed functions matching 12 portal endpoints
  - [ ] Error handling returns typed error objects
  - [ ] All functions use `client.ts` wrapper

### T2.3: TanStack Hooks — Stats + History
- **US**: US-1, US-2, US-3 | **Priority**: P1
- **Files**: `src/hooks/use-user-stats.ts`, `src/hooks/use-score-history.ts`
- **ACs**:
  - [ ] `useUserStats()` returns typed data, isLoading, error
  - [ ] `useScoreHistory(days=30)` returns chart-ready data
  - [ ] staleTime: 30s for stats, 60s for history

### T2.4: ScoreRing Chart Component
- **US**: US-1 | **Priority**: P1 | **FR**: FR-004
- **Files**: `src/components/charts/score-ring.tsx`
- **ACs**:
  - [ ] Animated conic-gradient ring (Framer Motion, 0-100)
  - [ ] Color transitions at thresholds: red (<30), amber (30-55), cyan (55-75), rose (>75)
  - [ ] Accepts `score`, `size`, `strokeWidth` props

### T2.5: RelationshipHero Section
- **US**: US-1 | **Priority**: P1 | **FR**: FR-004
- **Files**: `src/components/dashboard/relationship-hero.tsx`
- **ACs**:
  - [ ] ScoreRing centered with chapter badge, mood indicator, game status badge
  - [ ] Boss progress bar visible only during `boss_fight`
  - [ ] Days played counter (subtle, bottom-right)

### T2.6: ScoreTimeline Chart
- **US**: US-2 | **Priority**: P1 | **FR**: FR-005
- **Files**: `src/components/charts/score-timeline.tsx`
- **ACs**:
  - [ ] Recharts AreaChart with pink gradient fill, 30-day x-axis
  - [ ] Event markers (CustomDot): star (boss), diamond (chapter), circle (conversation)
  - [ ] Tooltip with score + event details on hover

### T2.7: RadarMetrics Chart
- **US**: US-3 | **Priority**: P1 | **FR**: FR-006
- **Files**: `src/components/charts/radar-metrics.tsx`
- **ACs**:
  - [ ] Recharts RadarChart with 4 axes: Intimacy, Passion, Trust, Secureness
  - [ ] Semi-transparent rose fill; animated scale-from-center on load
  - [ ] Weight labels visible; trend arrows per metric

### T2.8: HiddenMetrics Section
- **US**: US-3 | **Priority**: P1 | **FR**: FR-006
- **Files**: `src/components/dashboard/hidden-metrics.tsx`
- **ACs**:
  - [ ] GlassCard containing RadarMetrics + metric value labels
  - [ ] Weight percentages displayed below chart
  - [ ] Responsive: radar on desktop, simplified bar chart on mobile

### T2.9: Dashboard Landing Page
- **US**: US-1, US-2, US-3 | **Priority**: P1
- **Files**: `src/app/dashboard/page.tsx`, `src/app/dashboard/layout.tsx`
- **ACs**:
  - [ ] Composes RelationshipHero + ScoreTimeline + HiddenMetrics
  - [ ] Grid layout: hero full-width, timeline + metrics side-by-side on lg
  - [ ] Loading skeletons for all three sections

---

## Phase 3: Player Features (P2/P3)

### T3.1: TanStack Hooks — Player Features
- **US**: US-8-US-13 | **Priority**: P2
- **Files**: `src/hooks/use-engagement.ts`, `src/hooks/use-decay.ts`, `src/hooks/use-vices.ts`, `src/hooks/use-conversations.ts`, `src/hooks/use-summaries.ts`, `src/hooks/use-settings.ts`
- **ACs**:
  - [ ] 6 hooks with proper queryKeys, staleTime, error handling
  - [ ] `useSettings` includes `useMutation` for PUT settings
  - [ ] `useConversations` supports pagination (page, pageSize)

### T3.2: EngagementPulse Component
- **US**: US-8 | **Priority**: P2 | **FR**: FR-007
- **Files**: `src/components/dashboard/engagement-pulse.tsx`
- **ACs**:
  - [ ] 6-node state machine visualization (CSS/SVG)
  - [ ] Current state: bright glow + pulse animation
  - [ ] Multiplier badge: green (1.0x), amber (0.7x), red (0.5x)

### T3.3: DecayWarning Component
- **US**: US-9 | **Priority**: P2 | **FR**: FR-008
- **Files**: `src/components/dashboard/decay-warning.tsx`
- **ACs**:
  - [ ] Countdown timer (hours:minutes) with circular progress ring
  - [ ] Color transitions: green (>50%) → amber (25-50%) → red (<25%)
  - [ ] "Talk to Nikita" CTA with pulse when grace < 25%

### T3.4: Engagement + Decay Page
- **US**: US-8, US-9 | **Priority**: P2
- **Files**: `src/app/dashboard/engagement/page.tsx`
- **ACs**:
  - [ ] Composes EngagementPulse + DecayWarning
  - [ ] DecayWarning hidden when not decaying and grace > 50%

### T3.5: ViceCard + Vices Page
- **US**: US-10 | **Priority**: P2 | **FR**: FR-009
- **Files**: `src/components/dashboard/vice-card.tsx`, `src/app/dashboard/vices/page.tsx`
- **ACs**:
  - [ ] Glass card per vice: name, intensity (1-5 pips), description
  - [ ] Border color by intensity: blue (1) → teal (2) → amber (3) → orange (4) → pink (5)
  - [ ] Undiscovered vices: blurred locked cards with "?" icon

### T3.6: ConversationCard + List Page
- **US**: US-11 | **Priority**: P2 | **FR**: FR-010
- **Files**: `src/components/dashboard/conversation-card.tsx`, `src/app/dashboard/conversations/page.tsx`
- **ACs**:
  - [ ] Card: platform icon, date, message count, tone dot, score delta chip
  - [ ] Pagination with "Load more" button
  - [ ] Click navigates to detail page

### T3.7: ConversationDetail Page
- **US**: US-11 | **Priority**: P2 | **FR**: FR-010
- **Files**: `src/app/dashboard/conversations/[id]/page.tsx`
- **ACs**:
  - [ ] Chat-bubble layout (Nikita left, Player right)
  - [ ] Timestamps per message; boss fight badge if applicable
  - [ ] ScrollArea for long conversations

### T3.8: DiaryEntry + Diary Page
- **US**: US-13 | **Priority**: P3 | **FR**: FR-011
- **Files**: `src/components/dashboard/diary-entry.tsx`, `src/app/dashboard/diary/page.tsx`
- **ACs**:
  - [ ] Italic serif styling; "Dear Diary" header
  - [ ] Tone-coded border: pink (positive), gray (neutral), blue (negative)
  - [ ] Score delta for day + conversation count badge

### T3.9: Settings Page
- **US**: US-4 | **Priority**: P1 | **FR**: FR-012
- **Files**: `src/app/dashboard/settings/page.tsx`
- **ACs**:
  - [ ] React Hook Form + Zod validation for settings
  - [ ] Telegram link: shows code, status indicator
  - [ ] Danger Zone: red glass card with delete confirmation dialog

---

## Phase 4: Admin Dashboard (P1)

### T4.1: Admin API Functions
- **US**: US-5, US-6, US-7 | **Priority**: P1
- **Files**: `src/lib/api/admin.ts`
- **ACs**:
  - [ ] 30+ typed functions for admin endpoints
  - [ ] Mutation functions for all 6 existing PUT/POST endpoints
  - [ ] Error handling returns typed error objects

### T4.2: TanStack Hooks — Admin
- **US**: US-5, US-6, US-7 | **Priority**: P1
- **Files**: `src/hooks/use-admin-users.ts`, `src/hooks/use-admin-user.ts`, `src/hooks/use-admin-mutations.ts`, `src/hooks/use-admin-pipeline.ts`, `src/hooks/use-admin-stats.ts`
- **ACs**:
  - [ ] `useAdminUsers(filters)` supports search, pagination, sort
  - [ ] `useAdminMutations()` returns 6 mutation functions with optimistic updates
  - [ ] `useAdminPipeline()` returns 9-stage health data

### T4.3: KpiCard + Sparkline
- **US**: US-7 | **Priority**: P1
- **Files**: `src/components/admin/kpi-card.tsx`, `src/components/charts/sparkline.tsx`
- **ACs**:
  - [ ] KPI value + label + trend sparkline in GlassCard
  - [ ] Color-coded: green (good), amber (warning), red (bad)
  - [ ] Responsive: 2x3 grid on lg, 1-column stack on mobile

### T4.4: System Overview Page
- **US**: US-7 | **Priority**: P1 | **FR**: FR-016
- **Files**: `src/app/admin/page.tsx`
- **ACs**:
  - [ ] 6 KPI cards: Active Users, New Signups, Pipeline Success, Avg Time, Error Rate, Voice Calls
  - [ ] Data from admin/stats + unified-pipeline/health
  - [ ] Loading skeletons for all cards

### T4.5: UserTable Component
- **US**: US-5 | **Priority**: P1 | **FR**: FR-017
- **Files**: `src/components/admin/user-table.tsx`
- **ACs**:
  - [ ] shadcn Table with sortable columns: Name, Score, Chapter, Engagement, Status, Last Active
  - [ ] Search bar (debounced, 300ms)
  - [ ] Filter dropdowns: chapter, engagement, game status
  - [ ] Server-side pagination

### T4.6: Users List Page
- **US**: US-5 | **Priority**: P1 | **FR**: FR-017
- **Files**: `src/app/admin/users/page.tsx`
- **ACs**:
  - [ ] UserTable with search + filters
  - [ ] Row click navigates to `/admin/users/:id`
  - [ ] Score range slider filter

### T4.7: UserDetail Component
- **US**: US-5 | **Priority**: P1 | **FR**: FR-018
- **Files**: `src/components/admin/user-detail.tsx`
- **ACs**:
  - [ ] Full profile card with all user fields
  - [ ] RadarMetrics chart (reuse from player)
  - [ ] Tabs: Conversations, Memory, Prompts, Pipeline History

### T4.8: GodModePanel Component
- **US**: US-6 | **Priority**: P1 | **FR**: FR-019
- **Files**: `src/components/admin/god-mode-panel.tsx`
- **ACs**:
  - [ ] Amber-bordered GlassCard with 6 mutation controls
  - [ ] Each mutation: input/dropdown + reason field + submit
  - [ ] Confirmation dialog before execution; optimistic UI update
  - [ ] Toast notification on success/failure

### T4.9: User Detail Page
- **US**: US-5, US-6 | **Priority**: P1 | **FR**: FR-018, FR-019
- **Files**: `src/app/admin/users/[id]/page.tsx`
- **ACs**:
  - [ ] UserDetail + GodModePanel composed
  - [ ] Breadcrumb: Admin > Users > {user name}
  - [ ] Back button returns to user list preserving filters

### T4.10: PipelineBoard Component
- **US**: US-7 | **Priority**: P1 | **FR**: FR-020
- **Files**: `src/components/admin/pipeline-board.tsx`
- **ACs**:
  - [ ] 9 columns: extraction, memory_update, life_sim, emotional, game_state, conflict, touchpoint, summary, prompt_builder
  - [ ] Per column: success %, avg ms, error count
  - [ ] Color: green (>95%), amber (80-95%), red (<80%)

### T4.11: Pipeline Health Page
- **US**: US-7 | **Priority**: P1 | **FR**: FR-020
- **Files**: `src/app/admin/pipeline/page.tsx`
- **ACs**:
  - [ ] PipelineBoard + recent failures table
  - [ ] Failures: conversation ID, stage, error, timestamp
  - [ ] Auto-refresh every 30s

### T4.12: Admin Layout
- **US**: US-5 | **Priority**: P1 | **FR**: FR-025
- **Files**: `src/app/admin/layout.tsx`
- **ACs**:
  - [ ] Admin sidebar with cyan accent: Overview, Users, Voice, Text, Pipeline, Jobs, Prompts
  - [ ] Auth guard: redirects non-admin to /dashboard
  - [ ] Breadcrumb component below header

---

## Phase 5: Admin Features (P2/P3)

### T5.1: TranscriptViewer Component
- **US**: US-12 | **Priority**: P2
- **Files**: `src/components/admin/transcript-viewer.tsx`
- **ACs**:
  - [ ] Chat-bubble format: Nikita (left), User (right)
  - [ ] Timestamps per turn; metadata badges (latency, tokens)
  - [ ] ScrollArea for long transcripts

### T5.2: Voice Monitor Page
- **US**: US-12 | **Priority**: P2 | **FR**: FR-021
- **Files**: `src/app/admin/voice/page.tsx`
- **ACs**:
  - [ ] Call history table: date, duration, user, agent ID
  - [ ] Click row opens TranscriptViewer in Sheet/side panel
  - [ ] Filter by user, date range

### T5.3: Text Monitor Page
- **US**: US-12 | **Priority**: P2 | **FR**: FR-022
- **Files**: `src/app/admin/text/page.tsx`
- **ACs**:
  - [ ] Conversation list with filters (user, date, platform)
  - [ ] Pipeline stage stepper (9 stages with timing)
  - [ ] Thread/thought inspectors as expandable sections

### T5.4: JobCard Component
- **US**: US-15 | **Priority**: P3
- **Files**: `src/components/admin/job-card.tsx`
- **ACs**:
  - [ ] Job name, last run time, status badge (success/failed)
  - [ ] Execution history mini-chart (24h)
  - [ ] Manual trigger button with confirmation dialog

### T5.5: Job Monitor Page
- **US**: US-15 | **Priority**: P3 | **FR**: FR-023
- **Files**: `src/app/admin/jobs/page.tsx`
- **ACs**:
  - [ ] 5 job cards: decay, deliver, summary, cleanup, process-conversations
  - [ ] Manual trigger calls task endpoints
  - [ ] Failure log expandable per job

### T5.6: Prompt Inspector Page
- **US**: US-14 | **Priority**: P3 | **FR**: FR-024
- **Files**: `src/app/admin/prompts/page.tsx`
- **ACs**:
  - [ ] Prompt list: user, platform, timestamp, token count
  - [ ] Click opens prompt in syntax-highlighted viewer
  - [ ] Token breakdown by section (if available)

---

## Phase 6: Backend Changes

### T6.1: Fix Admin Prompt Endpoints
- **US**: US-14 | **Priority**: P2 | **FR**: FR-026
- **Files**: `nikita/api/routes/admin.py` (lines ~797-828)
- **ACs**:
  - [ ] `GET /admin/prompts` queries `generated_prompts` table, returns paginated list
  - [ ] `GET /admin/prompts/{id}` returns prompt content + token count
  - [ ] Tests verify both endpoints return real data

### T6.2: Fix Pipeline Stage Names
- **US**: US-7 | **Priority**: P1 | **FR**: FR-027
- **Files**: `nikita/api/routes/admin_debug.py` (lines ~1197-1294)
- **ACs**:
  - [ ] Stage names match Spec 042: extraction, memory_update, life_sim, emotional, game_state, conflict, touchpoint, summary, prompt_builder
  - [ ] Reads from `PipelineOrchestrator.STAGE_DEFINITIONS` or job_executions
  - [ ] Test verifies 9 correct stage names returned

### T6.3: Remove Deprecated Endpoints
- **US**: — | **Priority**: P0 | **FR**: FR-028
- **Files**: `nikita/api/routes/admin.py` (~line 991), `nikita/api/routes/tasks.py` (~line 733)
- **ACs**:
  - [ ] `GET /admin/pipeline-health` returns 410 Gone
  - [ ] Duplicate `POST /tasks/touchpoints` at line 733 deleted
  - [ ] Tests verify 410 response and no route shadowing

### T6.4: Trigger Pipeline Endpoint
- **US**: US-6 | **Priority**: P2 | **FR**: FR-029
- **Files**: `nikita/api/routes/admin.py`, `nikita/api/schemas/admin.py`
- **ACs**:
  - [ ] `POST /admin/users/{id}/trigger-pipeline` invokes PipelineOrchestrator for user
  - [ ] Returns `{ job_id, status: "started" }`
  - [ ] Requires admin auth + reason; logs to audit_logs

### T6.5: Pipeline History Endpoint
- **US**: US-5 | **Priority**: P2 | **FR**: FR-029
- **Files**: `nikita/api/routes/admin.py`, `nikita/api/schemas/admin.py`
- **ACs**:
  - [ ] `GET /admin/users/{id}/pipeline-history` returns list of pipeline runs
  - [ ] Each run: id, started_at, completed_at, stages[]{name, duration_ms, status}, success
  - [ ] Paginated, sorted by started_at desc

### T6.6: Set Individual Metrics Endpoint
- **US**: US-6 | **Priority**: P2 | **FR**: FR-029
- **Files**: `nikita/api/routes/admin.py`, `nikita/api/schemas/admin.py`
- **ACs**:
  - [ ] `PUT /admin/users/{id}/metrics` accepts partial metrics (intimacy, passion, trust, secureness)
  - [ ] Validates each metric 0-100; requires reason
  - [ ] Persists to user_metrics; logs to audit_logs

### T6.7: Fix Summary Generation
- **US**: — | **Priority**: P2 | **FR**: FR-030
- **Files**: `nikita/api/routes/tasks.py` (~line 412)
- **ACs**:
  - [ ] `POST /tasks/summary` generates summaries using PromptGenerator (not deprecated stub)
  - [ ] Returns count of summaries generated
  - [ ] Test verifies non-stub response

### T6.8: Fix Prompt Preview
- **US**: US-14 | **Priority**: P2 | **FR**: FR-030
- **Files**: `nikita/api/routes/admin_debug.py` (~line 643)
- **ACs**:
  - [ ] `POST /admin/debug/prompts/{user_id}/preview` uses PromptGenerator
  - [ ] Returns actual generated prompt + token count
  - [ ] Test verifies non-stub response

### T6.9: Backend Test Suite
- **US**: All | **Priority**: P1
- **Files**: `tests/api/routes/test_admin_prompts.py`, `tests/api/routes/test_admin_pipeline_names.py`, `tests/api/routes/test_admin_mutations_new.py`
- **ACs**:
  - [ ] Tests for T6.1-T6.8 endpoints (≥20 tests)
  - [ ] All existing tests still pass (regression)
  - [ ] Coverage ≥ 80% for modified files

---

## Phase 7: Testing + Deployment

### T7.1: Playwright Setup
- **US**: All | **Priority**: P1
- **Files**: `portal/playwright.config.ts`, `portal/tests/setup.ts`
- **ACs**:
  - [ ] Playwright configured for Next.js dev server
  - [ ] Auth setup helper (login as player, login as admin)
  - [ ] Screenshot comparison baseline

### T7.2: E2E — Auth Flow
- **US**: US-4 | **Priority**: P1
- **Files**: `portal/tests/auth.spec.ts`
- **ACs**:
  - [ ] Login with magic link redirects to dashboard
  - [ ] Unauthenticated user redirected to /login
  - [ ] Admin can access /admin/*; player cannot

### T7.3: E2E — Player Dashboard
- **US**: US-1, US-2, US-3 | **Priority**: P1
- **Files**: `portal/tests/dashboard.spec.ts`
- **ACs**:
  - [ ] Score ring renders with correct score value
  - [ ] Timeline chart has data points
  - [ ] Radar chart shows 4 axes

### T7.4: E2E — Admin Mutations
- **US**: US-6 | **Priority**: P1
- **Files**: `portal/tests/admin-mutations.spec.ts`
- **ACs**:
  - [ ] Set score mutation persists and refreshes UI
  - [ ] Confirmation dialog appears before mutation
  - [ ] Error state shown on invalid input

### T7.5: Accessibility Audit
- **US**: All | **Priority**: P2 | **NFR**: NFR-002
- **Files**: `portal/tests/accessibility.spec.ts`
- **ACs**:
  - [ ] axe-core reports 0 critical violations
  - [ ] All interactive elements keyboard-navigable
  - [ ] Charts have aria-labels

### T7.6: Vercel Deployment
- **US**: All | **Priority**: P1
- **Files**: `portal/vercel.json`, CI/CD config
- **ACs**:
  - [ ] Production build succeeds
  - [ ] API rewrites working (portal → backend)
  - [ ] Environment variables set in Vercel dashboard

---

## Progress Summary

| Phase | Tasks | Completed | Status |
|-------|-------|-----------|--------|
| 0: Setup | 4 | 0 | Pending |
| 1: Design + Auth | 8 | 0 | Pending |
| 2: Player Core | 9 | 0 | Pending |
| 3: Player Features | 9 | 0 | Pending |
| 4: Admin Core | 12 | 0 | Pending |
| 5: Admin Features | 6 | 0 | Pending |
| 6: Backend | 9 | 0 | Pending |
| 7: Testing | 6 | 0 | Pending |
| **Total** | **63** | **0** | **Pending** |

---

## Version History

| Date | Change | Author |
|------|--------|--------|
| 2026-02-07 | Initial creation (63 tasks) | portal-specifier agent |
