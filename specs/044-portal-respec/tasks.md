# Tasks: Spec 044 — Portal Respec

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
**Created**: 2026-02-07
**Total**: 63 tasks | ~300 tests estimated

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
  - [x] Three variants: default, elevated, danger (red border)
  - [x] Accepts children, className, onClick; forwarded ref
  - [x] Matches glassmorphism tokens (blur, border, shadow)

### T1.2: Supabase Auth Setup
- **US**: US-4 | **Priority**: P1 | **FR**: FR-001
- **Files**: `src/lib/supabase/client.ts`, `src/lib/supabase/server.ts`, `src/lib/supabase/middleware.ts`
- **ACs**:
  - [x] Browser client for client components
  - [x] Server client for RSC/API routes
  - [x] Middleware refreshes tokens, reads session

### T1.3: Login Page
- **US**: US-4 | **Priority**: P1 | **FR**: FR-001
- **Files**: `src/app/login/page.tsx`
- **ACs**:
  - [x] Magic link email input + submit; OTP fallback
  - [x] Loading state during auth; error messages displayed
  - [x] Redirect to `/dashboard` on success

### T1.4: Auth Callback Route
- **US**: US-4 | **Priority**: P1 | **FR**: FR-001
- **Files**: `src/app/auth/callback/route.ts`
- **ACs**:
  - [x] Handles PKCE code exchange
  - [x] Redirects to `/dashboard` (player) or `/admin` (admin) based on role

### T1.5: Next.js Auth Middleware
- **US**: US-4, US-5 | **Priority**: P1 | **FR**: FR-002
- **Files**: `portal/middleware.ts`
- **ACs**:
  - [x] Unauthenticated → redirect to `/login`
  - [x] `/admin/*` requires admin role; wrong role → 403 page
  - [x] `/dashboard/*` allows any authenticated user

### T1.6: Sidebar Component
- **US**: US-1, US-5 | **Priority**: P1 | **FR**: FR-013, FR-025
- **Files**: `src/components/layout/sidebar.tsx`, `src/components/layout/sidebar-item.tsx`, `src/components/layout/mobile-nav.tsx`
- **ACs**:
  - [x] Collapse/expand toggle (48px <-> 240px)
  - [x] Player variant (rose accent) and admin variant (cyan accent)
  - [x] Mobile: bottom tab bar with 5 items + hamburger

### T1.7: Providers + Root Layout
- **US**: All | **Priority**: P0
- **Files**: `src/app/providers.tsx`, `src/app/layout.tsx`
- **ACs**:
  - [x] QueryClientProvider wraps app
  - [x] Inter + JetBrains Mono fonts loaded
  - [x] Dark background applied to body (`bg-void`)

### T1.8: Shared Components
- **US**: All | **Priority**: P0 | **FR**: FR-015
- **Files**: `src/components/shared/loading-skeleton.tsx`, `src/components/shared/error-boundary.tsx`, `src/components/shared/empty-state.tsx`
- **ACs**:
  - [x] LoadingSkeleton renders pulse animation matching glass cards
  - [x] ErrorBoundary catches render errors, shows retry button
  - [x] EmptyState shows message + optional illustration

---

## Phase 2: Player Dashboard Core (P1)

### T2.1: API Client + Types
- **US**: All | **Priority**: P0
- **Files**: `src/lib/api/client.ts`, `src/lib/api/types.ts`, `src/lib/utils.ts`, `src/lib/constants.ts`
- **ACs**:
  - [x] Fetch wrapper injects Supabase auth token
  - [x] All backend response types mirrored in TypeScript (strict, no `any`)
  - [x] Utility functions: `cn()`, `formatScore()`, `formatDate()`, `formatDuration()`

### T2.2: Portal API Functions
- **US**: US-1, US-2, US-3 | **Priority**: P1
- **Files**: `src/lib/api/portal.ts`
- **ACs**:
  - [x] 12 typed functions matching 12 portal endpoints
  - [x] Error handling returns typed error objects
  - [x] All functions use `client.ts` wrapper

### T2.3: TanStack Hooks — Stats + History
- **US**: US-1, US-2, US-3 | **Priority**: P1
- **Files**: `src/hooks/use-user-stats.ts`, `src/hooks/use-score-history.ts`
- **ACs**:
  - [x] `useUserStats()` returns typed data, isLoading, error
  - [x] `useScoreHistory(days=30)` returns chart-ready data
  - [x] staleTime: 30s for stats, 60s for history

### T2.4: ScoreRing Chart Component
- **US**: US-1 | **Priority**: P1 | **FR**: FR-004
- **Files**: `src/components/charts/score-ring.tsx`
- **ACs**:
  - [x] Animated conic-gradient ring (Framer Motion, 0-100)
  - [x] Color transitions at thresholds: red (<30), amber (30-55), cyan (55-75), rose (>75)
  - [x] Accepts `score`, `size`, `strokeWidth` props

### T2.5: RelationshipHero Section
- **US**: US-1 | **Priority**: P1 | **FR**: FR-004
- **Files**: `src/components/dashboard/relationship-hero.tsx`
- **ACs**:
  - [x] ScoreRing centered with chapter badge, mood indicator, game status badge
  - [x] Boss progress bar visible only during `boss_fight`
  - [x] Days played counter (subtle, bottom-right)

### T2.6: ScoreTimeline Chart
- **US**: US-2 | **Priority**: P1 | **FR**: FR-005
- **Files**: `src/components/charts/score-timeline.tsx`
- **ACs**:
  - [x] Recharts AreaChart with pink gradient fill, 30-day x-axis
  - [x] Event markers (CustomDot): star (boss), diamond (chapter), circle (conversation)
  - [x] Tooltip with score + event details on hover

### T2.7: RadarMetrics Chart
- **US**: US-3 | **Priority**: P1 | **FR**: FR-006
- **Files**: `src/components/charts/radar-metrics.tsx`
- **ACs**:
  - [x] Recharts RadarChart with 4 axes: Intimacy, Passion, Trust, Secureness
  - [x] Semi-transparent rose fill; animated scale-from-center on load
  - [x] Weight labels visible; trend arrows per metric

### T2.8: HiddenMetrics Section
- **US**: US-3 | **Priority**: P1 | **FR**: FR-006
- **Files**: `src/components/dashboard/hidden-metrics.tsx`
- **ACs**:
  - [x] GlassCard containing RadarMetrics + metric value labels
  - [x] Weight percentages displayed below chart
  - [x] Responsive: radar on desktop, simplified bar chart on mobile

### T2.9: Dashboard Landing Page
- **US**: US-1, US-2, US-3 | **Priority**: P1
- **Files**: `src/app/dashboard/page.tsx`, `src/app/dashboard/layout.tsx`
- **ACs**:
  - [x] Composes RelationshipHero + ScoreTimeline + HiddenMetrics
  - [x] Grid layout: hero full-width, timeline + metrics side-by-side on lg
  - [x] Loading skeletons for all three sections

---

## Phase 3: Player Features (P2/P3)

### T3.1: TanStack Hooks — Player Features
- **US**: US-8-US-13 | **Priority**: P2
- **Files**: `src/hooks/use-engagement.ts`, `src/hooks/use-decay.ts`, `src/hooks/use-vices.ts`, `src/hooks/use-conversations.ts`, `src/hooks/use-summaries.ts`, `src/hooks/use-settings.ts`
- **ACs**:
  - [x] 6 hooks with proper queryKeys, staleTime, error handling
  - [x] `useSettings` includes `useMutation` for PUT settings
  - [x] `useConversations` supports pagination (page, pageSize)

### T3.2: EngagementPulse Component
- **US**: US-8 | **Priority**: P2 | **FR**: FR-007
- **Files**: `src/components/dashboard/engagement-pulse.tsx`
- **ACs**:
  - [x] 6-node state machine visualization (CSS/SVG)
  - [x] Current state: bright glow + pulse animation
  - [x] Multiplier badge: green (1.0x), amber (0.7x), red (0.5x)

### T3.3: DecayWarning Component
- **US**: US-9 | **Priority**: P2 | **FR**: FR-008
- **Files**: `src/components/dashboard/decay-warning.tsx`
- **ACs**:
  - [x] Countdown timer (hours:minutes) with circular progress ring
  - [x] Color transitions: green (>50%) -> amber (25-50%) -> red (<25%)
  - [x] "Talk to Nikita" CTA with pulse when grace < 25%

### T3.4: Engagement + Decay Page
- **US**: US-8, US-9 | **Priority**: P2
- **Files**: `src/app/dashboard/engagement/page.tsx`
- **ACs**:
  - [x] Composes EngagementPulse + DecayWarning
  - [x] DecayWarning hidden when not decaying and grace > 50%

### T3.5: ViceCard + Vices Page
- **US**: US-10 | **Priority**: P2 | **FR**: FR-009
- **Files**: `src/components/dashboard/vice-card.tsx`, `src/app/dashboard/vices/page.tsx`
- **ACs**:
  - [x] Glass card per vice: name, intensity (1-5 pips), description
  - [x] Border color by intensity: blue (1) -> teal (2) -> amber (3) -> orange (4) -> pink (5)
  - [x] Undiscovered vices: blurred locked cards with "?" icon

### T3.6: ConversationCard + List Page
- **US**: US-11 | **Priority**: P2 | **FR**: FR-010
- **Files**: `src/components/dashboard/conversation-card.tsx`, `src/app/dashboard/conversations/page.tsx`
- **ACs**:
  - [x] Card: platform icon, date, message count, tone dot, score delta chip
  - [x] Pagination with "Load more" button
  - [x] Click navigates to detail page

### T3.7: ConversationDetail Page
- **US**: US-11 | **Priority**: P2 | **FR**: FR-010
- **Files**: `src/app/dashboard/conversations/[id]/page.tsx`
- **ACs**:
  - [x] Chat-bubble layout (Nikita left, Player right)
  - [x] Timestamps per message; boss fight badge if applicable
  - [x] ScrollArea for long conversations

### T3.8: DiaryEntry + Diary Page
- **US**: US-13 | **Priority**: P3 | **FR**: FR-011
- **Files**: `src/components/dashboard/diary-entry.tsx`, `src/app/dashboard/diary/page.tsx`
- **ACs**:
  - [x] Italic serif styling; "Dear Diary" header
  - [x] Tone-coded border: pink (positive), gray (neutral), blue (negative)
  - [x] Score delta for day + conversation count badge

### T3.9: Settings Page
- **US**: US-4 | **Priority**: P1 | **FR**: FR-012
- **Files**: `src/app/dashboard/settings/page.tsx`
- **ACs**:
  - [x] React Hook Form + Zod validation for settings
  - [x] Telegram link: shows code, status indicator
  - [x] Danger Zone: red glass card with delete confirmation dialog

---

## Phase 4: Admin Dashboard (P1)

### T4.1: Admin API Functions
- **US**: US-5, US-6, US-7 | **Priority**: P1
- **Files**: `src/lib/api/admin.ts`
- **ACs**:
  - [x] 30+ typed functions for admin endpoints
  - [x] Mutation functions for all 6 existing PUT/POST endpoints
  - [x] Error handling returns typed error objects

### T4.2: TanStack Hooks — Admin
- **US**: US-5, US-6, US-7 | **Priority**: P1
- **Files**: `src/hooks/use-admin-users.ts`, `src/hooks/use-admin-user.ts`, `src/hooks/use-admin-mutations.ts`, `src/hooks/use-admin-pipeline.ts`, `src/hooks/use-admin-stats.ts`
- **ACs**:
  - [x] `useAdminUsers(filters)` supports search, pagination, sort
  - [x] `useAdminMutations()` returns 6 mutation functions with optimistic updates
  - [x] `useAdminPipeline()` returns 9-stage health data

### T4.3: KpiCard + Sparkline
- **US**: US-7 | **Priority**: P1
- **Files**: `src/components/admin/kpi-card.tsx`, `src/components/charts/sparkline.tsx`
- **ACs**:
  - [x] KPI value + label + trend sparkline in GlassCard
  - [x] Color-coded: green (good), amber (warning), red (bad)
  - [x] Responsive: 2x3 grid on lg, 1-column stack on mobile

### T4.4: System Overview Page
- **US**: US-7 | **Priority**: P1 | **FR**: FR-016
- **Files**: `src/app/admin/page.tsx`
- **ACs**:
  - [x] 6 KPI cards: Active Users, New Signups, Pipeline Success, Avg Time, Error Rate, Voice Calls
  - [x] Data from admin/stats + unified-pipeline/health
  - [x] Loading skeletons for all cards

### T4.5: UserTable Component
- **US**: US-5 | **Priority**: P1 | **FR**: FR-017
- **Files**: `src/components/admin/user-table.tsx`
- **ACs**:
  - [x] shadcn Table with sortable columns: Name, Score, Chapter, Engagement, Status, Last Active
  - [x] Search bar (debounced, 300ms)
  - [x] Filter dropdowns: chapter, engagement, game status
  - [x] Server-side pagination

### T4.6: Users List Page
- **US**: US-5 | **Priority**: P1 | **FR**: FR-017
- **Files**: `src/app/admin/users/page.tsx`
- **ACs**:
  - [x] UserTable with search + filters
  - [x] Row click navigates to `/admin/users/:id`
  - [x] Score range slider filter

### T4.7: UserDetail Component
- **US**: US-5 | **Priority**: P1 | **FR**: FR-018
- **Files**: `src/components/admin/user-detail.tsx`
- **ACs**:
  - [x] Full profile card with all user fields
  - [x] RadarMetrics chart (reuse from player)
  - [x] Tabs: Conversations, Memory, Prompts, Pipeline History

### T4.8: GodModePanel Component
- **US**: US-6 | **Priority**: P1 | **FR**: FR-019
- **Files**: `src/components/admin/god-mode-panel.tsx`
- **ACs**:
  - [x] Amber-bordered GlassCard with 6 mutation controls
  - [x] Each mutation: input/dropdown + reason field + submit
  - [x] Confirmation dialog before execution; optimistic UI update
  - [x] Toast notification on success/failure

### T4.9: User Detail Page
- **US**: US-5, US-6 | **Priority**: P1 | **FR**: FR-018, FR-019
- **Files**: `src/app/admin/users/[id]/page.tsx`
- **ACs**:
  - [x] UserDetail + GodModePanel composed
  - [x] Breadcrumb: Admin > Users > {user name}
  - [x] Back button returns to user list preserving filters

### T4.10: PipelineBoard Component
- **US**: US-7 | **Priority**: P1 | **FR**: FR-020
- **Files**: `src/components/admin/pipeline-board.tsx`
- **ACs**:
  - [x] 9 columns: extraction, memory_update, life_sim, emotional, game_state, conflict, touchpoint, summary, prompt_builder
  - [x] Per column: success %, avg ms, error count
  - [x] Color: green (>95%), amber (80-95%), red (<80%)

### T4.11: Pipeline Health Page
- **US**: US-7 | **Priority**: P1 | **FR**: FR-020
- **Files**: `src/app/admin/pipeline/page.tsx`
- **ACs**:
  - [x] PipelineBoard + recent failures table
  - [x] Failures: conversation ID, stage, error, timestamp
  - [x] Auto-refresh every 30s

### T4.12: Admin Layout
- **US**: US-5 | **Priority**: P1 | **FR**: FR-025
- **Files**: `src/app/admin/layout.tsx`
- **ACs**:
  - [x] Admin sidebar with cyan accent: Overview, Users, Voice, Text, Pipeline, Jobs, Prompts
  - [x] Auth guard: redirects non-admin to /dashboard
  - [x] Breadcrumb component below header

---

## Phase 5: Admin Features (P2/P3)

### T5.1: TranscriptViewer Component
- **US**: US-12 | **Priority**: P2
- **Files**: `src/components/admin/transcript-viewer.tsx`
- **ACs**:
  - [x] Chat-bubble format: Nikita (left), User (right)
  - [x] Timestamps per turn; metadata badges (latency, tokens)
  - [x] ScrollArea for long transcripts

### T5.2: Voice Monitor Page
- **US**: US-12 | **Priority**: P2 | **FR**: FR-021
- **Files**: `src/app/admin/voice/page.tsx`
- **ACs**:
  - [x] Call history table: date, duration, user, agent ID
  - [x] Click row opens TranscriptViewer in Sheet/side panel
  - [x] Filter by user, date range

### T5.3: Text Monitor Page
- **US**: US-12 | **Priority**: P2 | **FR**: FR-022
- **Files**: `src/app/admin/text/page.tsx`
- **ACs**:
  - [x] Conversation list with filters (user, date, platform)
  - [x] Pipeline stage stepper (9 stages with timing)
  - [x] Thread/thought inspectors as expandable sections

### T5.4: JobCard Component
- **US**: US-15 | **Priority**: P3
- **Files**: `src/components/admin/job-card.tsx`
- **ACs**:
  - [x] Job name, last run time, status badge (success/failed)
  - [x] Execution history mini-chart (24h)
  - [x] Manual trigger button with confirmation dialog

### T5.5: Job Monitor Page
- **US**: US-15 | **Priority**: P3 | **FR**: FR-023
- **Files**: `src/app/admin/jobs/page.tsx`
- **ACs**:
  - [x] 5 job cards: decay, deliver, summary, cleanup, process-conversations
  - [x] Manual trigger calls task endpoints
  - [x] Failure log expandable per job

### T5.6: Prompt Inspector Page
- **US**: US-14 | **Priority**: P3 | **FR**: FR-024
- **Files**: `src/app/admin/prompts/page.tsx`
- **ACs**:
  - [x] Prompt list: user, platform, timestamp, token count
  - [x] Click opens prompt in syntax-highlighted viewer
  - [x] Token breakdown by section (if available)

---

## Phase 6: Backend Changes

### T6.1: Fix Admin Prompt Endpoints
- **US**: US-14 | **Priority**: P2 | **FR**: FR-026
- **Files**: `nikita/api/routes/admin.py` (lines ~797-828)
- **ACs**:
  - [x] `GET /admin/prompts` queries `generated_prompts` table, returns paginated list
  - [x] `GET /admin/prompts/{id}` returns prompt content + token count
  - [x] Tests verify both endpoints return real data

### T6.2: Fix Pipeline Stage Names
- **US**: US-7 | **Priority**: P1 | **FR**: FR-027
- **Files**: `nikita/api/routes/admin_debug.py` (lines ~1197-1294)
- **ACs**:
  - [x] Stage names match Spec 042: extraction, memory_update, life_sim, emotional, game_state, conflict, touchpoint, summary, prompt_builder
  - [x] Reads from `PipelineOrchestrator.STAGE_DEFINITIONS` or job_executions
  - [x] Test verifies 9 correct stage names returned

### T6.3: Remove Deprecated Endpoints
- **US**: --- | **Priority**: P0 | **FR**: FR-028
- **Files**: `nikita/api/routes/admin.py` (~line 991), `nikita/api/routes/tasks.py` (~line 733)
- **ACs**:
  - [x] `GET /admin/pipeline-health` returns 410 Gone
  - [x] Duplicate `POST /tasks/touchpoints` at line 733 deleted
  - [x] Tests verify 410 response and no route shadowing

### T6.4: Trigger Pipeline Endpoint
- **US**: US-6 | **Priority**: P2 | **FR**: FR-029
- **Files**: `nikita/api/routes/admin.py`, `nikita/api/schemas/admin.py`
- **ACs**:
  - [x] `POST /admin/users/{id}/trigger-pipeline` invokes PipelineOrchestrator for user
  - [x] Returns `{ job_id, status: "started" }`
  - [x] Requires admin auth + reason; logs to audit_logs

### T6.5: Pipeline History Endpoint
- **US**: US-5 | **Priority**: P2 | **FR**: FR-029
- **Files**: `nikita/api/routes/admin.py`, `nikita/api/schemas/admin.py`
- **ACs**:
  - [x] `GET /admin/users/{id}/pipeline-history` returns list of pipeline runs
  - [x] Each run: id, started_at, completed_at, stages[]{name, duration_ms, status}, success
  - [x] Paginated, sorted by started_at desc

### T6.6: Set Individual Metrics Endpoint
- **US**: US-6 | **Priority**: P2 | **FR**: FR-029
- **Files**: `nikita/api/routes/admin.py`, `nikita/api/schemas/admin.py`
- **ACs**:
  - [x] `PUT /admin/users/{id}/metrics` accepts partial metrics (intimacy, passion, trust, secureness)
  - [x] Validates each metric 0-100; requires reason
  - [x] Persists to user_metrics; logs to audit_logs

### T6.7: Fix Summary Generation
- **US**: --- | **Priority**: P2 | **FR**: FR-030
- **Files**: `nikita/api/routes/tasks.py` (~line 412)
- **ACs**:
  - [x] `POST /tasks/summary` generates summaries using PromptGenerator (not deprecated stub)
  - [x] Returns count of summaries generated
  - [x] Test verifies non-stub response

### T6.8: Fix Prompt Preview
- **US**: US-14 | **Priority**: P2 | **FR**: FR-030
- **Files**: `nikita/api/routes/admin_debug.py` (~line 643)
- **ACs**:
  - [x] `POST /admin/debug/prompts/{user_id}/preview` uses PromptGenerator
  - [x] Returns actual generated prompt + token count
  - [x] Test verifies non-stub response

### T6.9: Backend Test Suite
- **US**: All | **Priority**: P1
- **Files**: `tests/api/routes/test_admin_prompts.py`, `tests/api/routes/test_admin_pipeline_names.py`, `tests/api/routes/test_admin_mutations_new.py`
- **ACs**:
  - [x] Tests for T6.1-T6.8 endpoints (>=20 tests)
  - [x] All existing tests still pass (regression)
  - [x] Coverage >= 80% for modified files

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
  - [x] Production build succeeds
  - [x] API rewrites working (portal -> backend)
  - [x] Environment variables set in Vercel dashboard

---

## Progress Summary

| Phase | Tasks | Completed | Status |
|-------|-------|-----------|--------|
| 0: Setup | 4 | 4 | Complete |
| 1: Design + Auth | 8 | 8 | Complete |
| 2: Player Core | 9 | 9 | Complete |
| 3: Player Features | 9 | 9 | Complete |
| 4: Admin Core | 12 | 12 | Complete |
| 5: Admin Features | 6 | 6 | Complete |
| 6: Backend | 9 | 9 | Complete |
| 7: Testing | 6 | 1 | In Progress |
| **Total** | **63** | **58** | **92% Complete** |

**Note**: Phase 7 tasks T7.1-T7.5 (Playwright E2E tests) are pending — portal is deployed and functional but lacks automated E2E test coverage. T7.6 (Vercel Deployment) is complete.

---

## Version History

| Date | Change | Author |
|------|--------|--------|
| 2026-02-07 | Initial creation (63 tasks) | portal-specifier agent |
| 2026-02-08 | Phases 0-6 implemented, T7.6 deployed to Vercel (commit add61e3) | Claude |
| 2026-02-09 | Task statuses updated to match implementation (58/63 complete) | Claude (Spec Alignment) |
