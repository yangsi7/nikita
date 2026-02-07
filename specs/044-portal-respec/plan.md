# Plan: Spec 044 — Portal Respec Implementation

**Spec**: [spec.md](spec.md)
**Created**: 2026-02-07
**Depends On**: Spec 043 (pipeline wiring fixes)

---

## Architecture

### Project Structure

```
portal/
├── next.config.ts
├── package.json
├── tailwind.config.ts
├── tsconfig.json
├── components.json              # shadcn/ui config
├── postcss.config.mjs
├── src/
│   ├── app/
│   │   ├── layout.tsx           # Root layout (dark theme, fonts, providers)
│   │   ├── page.tsx             # Redirect to /dashboard or /login
│   │   ├── globals.css          # Design tokens, glassmorphism utilities
│   │   ├── providers.tsx        # QueryClientProvider, SupabaseProvider
│   │   ├── login/
│   │   │   └── page.tsx         # Magic link / OTP login
│   │   ├── auth/
│   │   │   └── callback/
│   │   │       └── route.ts     # PKCE callback handler
│   │   ├── dashboard/
│   │   │   ├── layout.tsx       # Player sidebar + auth guard
│   │   │   ├── page.tsx         # Hero + Timeline + Metrics (landing)
│   │   │   ├── engagement/
│   │   │   │   └── page.tsx     # Engagement Pulse + Decay Warning
│   │   │   ├── vices/
│   │   │   │   └── page.tsx     # Vice Discoveries
│   │   │   ├── conversations/
│   │   │   │   ├── page.tsx     # Conversation list
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx # Conversation detail
│   │   │   ├── diary/
│   │   │   │   └── page.tsx     # Nikita's Diary
│   │   │   └── settings/
│   │   │       └── page.tsx     # Settings + Danger Zone
│   │   └── admin/
│   │       ├── layout.tsx       # Admin sidebar + auth guard
│   │       ├── page.tsx         # System Overview (KPI grid)
│   │       ├── users/
│   │       │   ├── page.tsx     # User search + table
│   │       │   └── [id]/
│   │       │       └── page.tsx # User detail + God Mode
│   │       ├── voice/
│   │       │   └── page.tsx     # Voice monitor
│   │       ├── text/
│   │       │   └── page.tsx     # Text monitor
│   │       ├── pipeline/
│   │       │   └── page.tsx     # Pipeline health board
│   │       ├── jobs/
│   │       │   └── page.tsx     # Job monitor
│   │       └── prompts/
│   │           └── page.tsx     # Prompt inspector
│   ├── components/
│   │   ├── ui/                  # shadcn/ui primitives (auto-generated)
│   │   ├── glass/               # Glassmorphism wrappers
│   │   │   ├── glass-card.tsx
│   │   │   └── glass-panel.tsx
│   │   ├── charts/              # Chart components
│   │   │   ├── score-ring.tsx
│   │   │   ├── score-timeline.tsx
│   │   │   ├── radar-metrics.tsx
│   │   │   └── sparkline.tsx
│   │   ├── dashboard/           # Player dashboard sections
│   │   │   ├── relationship-hero.tsx
│   │   │   ├── hidden-metrics.tsx
│   │   │   ├── engagement-pulse.tsx
│   │   │   ├── decay-warning.tsx
│   │   │   ├── vice-card.tsx
│   │   │   ├── conversation-card.tsx
│   │   │   └── diary-entry.tsx
│   │   ├── admin/               # Admin components
│   │   │   ├── kpi-card.tsx
│   │   │   ├── user-table.tsx
│   │   │   ├── user-detail.tsx
│   │   │   ├── god-mode-panel.tsx
│   │   │   ├── pipeline-board.tsx
│   │   │   ├── job-card.tsx
│   │   │   └── transcript-viewer.tsx
│   │   ├── layout/              # Shared layout
│   │   │   ├── sidebar.tsx
│   │   │   ├── sidebar-item.tsx
│   │   │   └── mobile-nav.tsx
│   │   └── shared/              # Shared components
│   │       ├── loading-skeleton.tsx
│   │       ├── error-boundary.tsx
│   │       └── empty-state.tsx
│   ├── lib/
│   │   ├── api/
│   │   │   ├── client.ts        # Axios/fetch wrapper with auth headers
│   │   │   ├── portal.ts        # Player API functions (typed)
│   │   │   ├── admin.ts         # Admin API functions (typed)
│   │   │   └── types.ts         # Shared TypeScript types (mirrors backend schemas)
│   │   ├── supabase/
│   │   │   ├── client.ts        # Browser Supabase client
│   │   │   ├── server.ts        # Server Supabase client
│   │   │   └── middleware.ts    # Auth middleware for route protection
│   │   ├── utils.ts             # cn(), formatScore(), formatDate()
│   │   └── constants.ts         # Theme tokens, game constants
│   └── hooks/
│       ├── use-user-stats.ts    # TanStack Query: portal/stats
│       ├── use-score-history.ts # TanStack Query: portal/score-history
│       ├── use-engagement.ts    # TanStack Query: portal/engagement
│       ├── use-decay.ts         # TanStack Query: portal/decay
│       ├── use-vices.ts         # TanStack Query: portal/vices
│       ├── use-conversations.ts # TanStack Query: portal/conversations
│       ├── use-summaries.ts     # TanStack Query: portal/daily-summaries
│       ├── use-settings.ts      # TanStack Query: portal/settings (with mutation)
│       ├── use-admin-users.ts   # TanStack Query: admin/users
│       ├── use-admin-user.ts    # TanStack Query: admin/users/{id}
│       ├── use-admin-mutations.ts  # TanStack Mutations: admin SET endpoints
│       ├── use-admin-pipeline.ts   # TanStack Query: admin/pipeline
│       └── use-admin-stats.ts      # TanStack Query: admin/stats
├── middleware.ts                 # Next.js middleware (auth redirect)
└── public/
    └── favicon.ico
```

### Component Hierarchy

```
Page → Section → Card → Widget

dashboard/page.tsx
├─ RelationshipHero (section)
│  ├─ GlassCard (container)
│  ├─ ScoreRing (chart)
│  ├─ Badge (chapter)
│  └─ Badge (game status)
├─ ScoreTimeline (section)
│  ├─ GlassCard (container)
│  └─ AreaChart (Recharts)
└─ HiddenMetrics (section)
   ├─ GlassCard (container)
   └─ RadarChart (Recharts)
```

### Data Fetching Strategy

```
TanStack Query (React Query v5)
├─ QueryClientProvider in providers.tsx
├─ Per-hook: queryKey + queryFn + staleTime
├─ Stale time: 30s for stats, 60s for history, 5m for settings
├─ Optimistic updates for admin mutations
└─ Prefetching on sidebar hover for next page
```

### Auth Architecture

```
middleware.ts (Next.js edge middleware)
├─ Check session via @supabase/ssr
├─ /login → allow unauthenticated
├─ /auth/callback → allow (PKCE handler)
├─ /dashboard/* → require auth (any role)
├─ /admin/* → require auth + admin role
└─ else → redirect to /login
```

### shadcn/ui Component Map

| shadcn Component | Used In |
|------------------|---------|
| Card | GlassCard wrapper, KPI cards, Vice cards, Diary entries |
| Badge | Chapter badge, game status, tone indicators, score delta |
| Table | User list, conversation list, call history, failures |
| Dialog | Confirmation modals (mutations, account deletion) |
| Tabs | User detail tabs, settings sections |
| Progress | Boss progress bar, pipeline stage progress |
| Skeleton | All loading states |
| Sidebar | Player + Admin navigation |
| Avatar | User avatars in admin |
| Tooltip | Chart hover, metric explanations |
| Input | Search, mutation inputs, settings forms |
| Select | Chapter dropdown, engagement dropdown, filters |
| Switch | Notification toggles |
| Separator | Section dividers |
| ScrollArea | Transcript viewer, conversation messages |
| Sheet | Mobile navigation drawer |
| Breadcrumb | Admin navigation path |
| DropdownMenu | User actions, filter dropdowns |
| Alert | Error messages, decay warnings |
| Accordion | Pipeline stage details, FAQ |
| Slider | Score range filter (admin) |
| Form | Settings, mutation inputs (React Hook Form) |

---

## Phase Breakdown

### Phase 0: Project Setup (T0.x)

**Goal**: Scaffold Next.js 15 project with all dependencies.

- Initialize Next.js 15 with App Router + TypeScript strict
- Install: shadcn/ui, Tailwind CSS 4, Recharts, Framer Motion, @supabase/ssr, @tanstack/react-query, react-hook-form, zod
- Configure shadcn/ui via `components.json` (dark theme, CSS variables)
- Add shadcn primitives: Card, Badge, Table, Dialog, Tabs, Progress, Skeleton, Sidebar, Avatar, Tooltip, Input, Select, Switch, Separator, ScrollArea, Sheet, Breadcrumb, DropdownMenu, Alert, Accordion, Slider, Form, Button
- Create `globals.css` with full design token system (Section 6 of product brief)
- Create `tailwind.config.ts` with custom colors, glassmorphism utilities
- Configure Vercel deployment (`vercel.json`)

### Phase 1: Design System + Auth (T1.x)

**Goal**: Glassmorphism design system + Supabase auth working.

- GlassCard component (glass-card.tsx, glass-panel.tsx) with 3 variants (default, elevated, danger)
- Supabase SSR auth: client.ts, server.ts, middleware.ts
- Login page with magic link / OTP
- Auth callback route (PKCE)
- Next.js middleware for route protection
- Sidebar component (shared between player + admin)
- providers.tsx (QueryClient + Supabase)
- Root layout with Inter + JetBrains Mono fonts

### Phase 2: Player Dashboard Core — P1 (T2.x)

**Goal**: Landing page with Hero, Timeline, Metrics.

- API client (client.ts) with auth header injection
- TypeScript types matching backend schemas (types.ts)
- Portal API functions (portal.ts)
- TanStack Query hooks: useUserStats, useScoreHistory
- RelationshipHero component with ScoreRing (Framer Motion conic-gradient)
- ScoreTimeline component with Recharts AreaChart + event markers
- HiddenMetrics component with Recharts RadarChart
- Dashboard layout with sidebar
- Loading skeletons for all sections
- Error boundary with retry

### Phase 3: Player Features — P2/P3 (T3.x)

**Goal**: Engagement, Decay, Vices, Conversations, Diary, Settings.

- TanStack hooks: useEngagement, useDecay, useVices, useConversations, useSummaries, useSettings
- EngagementPulse component (state machine SVG/CSS visualization)
- DecayWarning component (countdown timer + progress ring)
- ViceCard component (intensity pips + glass styling)
- ConversationCard + ConversationDetail (chat-bubble messages)
- DiaryEntry component (italic font, tone-coded border)
- Settings page with React Hook Form + Zod
- Telegram link flow
- Account deletion with confirmation dialog

### Phase 4: Admin Dashboard — P1 (T4.x)

**Goal**: System Overview, User Management, Pipeline Health.

- Admin API functions (admin.ts)
- TanStack hooks: useAdminUsers, useAdminUser, useAdminMutations, useAdminPipeline, useAdminStats
- KpiCard component with sparkline
- System Overview page (6 KPI cards)
- UserTable component with search, filters, sort, pagination
- UserDetail page with profile card + radar + tabs
- GodModePanel with all 6 mutation controls + confirmation dialogs
- PipelineBoard component (9-stage columns with color coding)
- Admin layout with cyan-accented sidebar

### Phase 5: Admin Features — P2/P3 (T5.x)

**Goal**: Voice, Text, Jobs, Prompts monitors.

- TranscriptViewer component (chat-bubble layout)
- Voice monitor page (call table + transcript panel)
- Text monitor page (conversation list + pipeline stepper + threads)
- JobCard component (status + history chart + manual trigger)
- Job monitor page (5 job cards)
- Prompt inspector page (prompt list + viewer + token analysis)

### Phase 6: Backend Changes (T6.x)

**Goal**: Fix stubs + add new endpoints from FR-026 — FR-030.

- Fix admin prompt endpoints (query generated_prompts + ready_prompts)
- Fix pipeline stage names in admin_debug.py
- Remove deprecated /pipeline-health endpoint
- Remove duplicate /touchpoints route
- Add `POST /admin/users/{id}/trigger-pipeline`
- Add `GET /admin/users/{id}/pipeline-history`
- Add `PUT /admin/users/{id}/metrics`
- Fix summary generation stub
- Fix prompt preview stub

### Phase 7: Testing + Deployment (T7.x)

**Goal**: E2E tests, accessibility, deployment.

- Playwright E2E: login flow, dashboard rendering, admin mutations
- Component tests: ScoreRing, RadarChart, GlassCard
- Accessibility audit: axe-core on all pages
- Lighthouse performance check (target: >90)
- Vercel deployment config (env vars, rewrites, headers)
- CORS configuration for API backend

---

## File Map — Key Files to Create

| File | Responsibility | Lines (est) |
|------|---------------|-------------|
| `src/app/globals.css` | Design tokens, glass utilities | 200 |
| `src/lib/api/types.ts` | TypeScript types for all API responses | 200 |
| `src/lib/api/client.ts` | Auth-injected fetch wrapper | 60 |
| `src/lib/api/portal.ts` | 12 portal API functions | 120 |
| `src/lib/api/admin.ts` | 30+ admin API functions | 200 |
| `src/components/glass/glass-card.tsx` | Glassmorphism Card wrapper | 80 |
| `src/components/charts/score-ring.tsx` | Animated score ring (Framer Motion) | 120 |
| `src/components/charts/score-timeline.tsx` | 30-day area chart (Recharts) | 150 |
| `src/components/charts/radar-metrics.tsx` | 4-axis radar (Recharts) | 100 |
| `src/components/admin/god-mode-panel.tsx` | 6 mutation controls | 200 |
| `src/components/admin/pipeline-board.tsx` | 9-stage health board | 180 |
| `src/components/layout/sidebar.tsx` | Shared sidebar (player/admin) | 150 |

---

## Rollback Strategy

- Phase 0-1: Delete `portal/` directory, no backend changes
- Phase 2-5: Frontend-only changes, no backend impact
- Phase 6: Backend changes behind feature flags or versioned endpoints
- Phase 7: Deployment can be reverted via Vercel instant rollback

---

## Estimated Effort

| Phase | Tasks | Estimated Hours |
|-------|-------|-----------------|
| 0: Setup | 6 | 2-3h |
| 1: Design + Auth | 8 | 4-6h |
| 2: Player Core | 10 | 6-8h |
| 3: Player Features | 12 | 8-12h |
| 4: Admin Core | 10 | 8-10h |
| 5: Admin Features | 8 | 6-8h |
| 6: Backend | 9 | 4-6h |
| 7: Testing | 6 | 4-6h |
| **Total** | **69** | **42-59h** |
