# Spec 044: Portal Respec — Full Redesign

**Status**: DRAFT
**Created**: 2026-02-07
**Depends On**: Spec 043 (Integration Wiring Fixes)
**Supersedes**: Old `portal/` directory (deleted)

---

## Problem Statement

The original Next.js portal was deleted during cleanup. Nikita needs a modern, dark-themed web portal rebuilt from scratch atop the Spec 042 unified pipeline architecture. Two distinct dashboards are required: a player-facing "Relationship Pulse" and an admin "Mission Control" with full read/write capabilities.

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Framework | Next.js (App Router) | 15 |
| Styling | Tailwind CSS | 4 |
| Components | shadcn/ui + Radix UI | latest |
| Charts | Recharts | 2.x |
| Animation | Framer Motion | 11.x |
| Auth | Supabase SSR (@supabase/ssr) | latest |
| Server State | TanStack Query (React Query) | 5.x |
| Forms | React Hook Form + Zod | latest |
| Deployment | Vercel | — |
| Theme | Dark-only (glassmorphism) | — |

---

## Functional Requirements

### Auth (FR-001 — FR-003)

**FR-001**: Supabase SSR Authentication
- Magic link / OTP login via Supabase Auth
- Server-side session validation via `@supabase/ssr` middleware
- AC: Unauthenticated users redirect to `/login`; valid sessions persist across page navigations

**FR-002**: Role-Based Access Control
- Two roles: `player` (default) and `admin`
- Role stored in Supabase `auth.users.raw_user_meta_data.role`
- AC: `/dashboard/*` requires `player` or `admin`; `/admin/*` requires `admin`; wrong role shows 403

**FR-003**: Session Management
- Auto-refresh tokens via middleware
- Logout clears session and redirects to `/login`
- AC: Expired tokens auto-refresh; manual logout works; PKCE flow for magic link callback

### Player Dashboard (FR-004 — FR-015)

**FR-004**: Relationship Hero Section
- Animated score ring (conic-gradient, 0-100) with color transitions: red (<30), amber (30-55), cyan (55-75), rose (>75)
- Chapter badge (roman numeral I-V), mood indicator, game status badge, boss progress bar (during boss_fight)
- Data: `GET /api/v1/portal/stats` → `UserStatsResponse`
- AC: Ring animates on load; color matches threshold; boss bar visible only during boss_fight

**FR-005**: Score Timeline Chart
- 30-day area chart (Recharts) with gradient fill
- Event markers: boss events (star), chapter advances (diamond), decay (down-arrow), conversations (circle)
- Hover tooltips with score + event details; current score badge at rightmost point
- Data: `GET /api/v1/portal/score-history` → `ScoreHistoryResponse`
- AC: Chart renders 30-day data; event markers show on hover; responsive on mobile

**FR-006**: Hidden Metrics Radar
- 4-axis radar chart: Intimacy, Passion, Trust, Secureness
- Semi-transparent rose fill with neon edges; animated scale-from-center on load
- Trend arrows per metric (up/down/stable vs last session); weight labels
- Data: `GET /api/v1/portal/stats` → `metrics` field
- AC: Radar renders 4 axes with correct values; animation plays once; weights displayed

**FR-007**: Engagement Pulse
- 6-node state machine visualization (Calibrating, In Zone, Drifting, Clingy, Distant, Out of Zone)
- Current state highlighted with glow + pulse; transition edges dimmed
- Multiplier badge (1.0x green / 0.7x amber / 0.5x red)
- Data: `GET /api/v1/portal/engagement` → `EngagementResponse`
- AC: Current state glows; multiplier badge correct; recent transitions listed

**FR-008**: Decay Warning
- Countdown timer (hours:minutes) with circular progress ring
- Color gradient: green (>50% grace) → amber (25-50%) → red (<25%)
- Projected score loss text; "Talk to Nikita" CTA with pulse when urgent
- Visible only when `is_decaying: true` or grace < 50%
- Data: `GET /api/v1/portal/decay` → `DecayStatusResponse`
- AC: Timer counts down; CTA visible when urgent; hidden when not decaying

**FR-009**: Vice Discoveries
- Scrollable row of glass cards per discovered vice
- Intensity bar (1-5 pips) with color gradient (blue → pink)
- Nikita's first-person description (italic); undiscovered = blurred locked cards
- Data: `GET /api/v1/portal/vices` → `VicePreferenceResponse[]`
- AC: Discovered vices render with intensity; undiscovered appear locked; 8 categories total

**FR-010**: Conversation History
- Paginated glass card list per conversation
- Platform icon (Telegram/Voice), date, message count, tone indicator dot, score delta chip
- Click expands to full message thread in chat-bubble layout
- Data: `GET /api/v1/portal/conversations` + `GET /api/v1/portal/conversations/{id}`
- AC: List paginated; tone dots color-coded; expanded view shows messages

**FR-011**: Nikita's Diary
- Vertical timeline of daily summary entries
- Italic/serif font styling; tone-coded border (pink/gray/blue)
- Score delta for the day (start → end); conversation count badge
- Data: `GET /api/v1/portal/daily-summaries` → `DailySummaryResponse[]`
- AC: Entries render in first-person; tone color correct; sorted by date desc

**FR-012**: Settings Page
- Account section: email display, timezone selector
- Telegram Link section: status indicator + link/unlink with code display
- Danger Zone: red-bordered card with "Delete Account" (confirmation dialog)
- Data: `GET/PUT /api/v1/portal/settings`, `POST /api/v1/portal/link-telegram`, `DELETE /api/v1/portal/account`
- AC: Settings save correctly; Telegram link generates code; deletion requires confirmation

**FR-013**: Sidebar Navigation (Player)
- Collapsed (icon-only 48px) with tooltip; expanded (240px) with icon + label
- Mobile: bottom tab bar (5 items) + hamburger overflow
- Active item: glass highlight with left rose accent border
- AC: Sidebar toggles collapse/expand; mobile shows tab bar; active state visible

**FR-014**: Responsive Layout
- Mobile-first for player dashboard; breakpoints: sm(640), md(768), lg(1024), xl(1280)
- Score ring and chart stack vertically on mobile; grid on desktop
- AC: All sections render correctly at all breakpoints; no horizontal scroll

**FR-015**: Loading & Error States
- Skeleton loaders for every section (shadcn Skeleton component)
- Error boundaries with retry buttons; empty states with illustrations
- AC: Loading shows skeletons; API errors show retry; empty data shows message

### Admin Dashboard (FR-016 — FR-025)

**FR-016**: System Overview
- 2x3 KPI card grid: Active Users (24h), New Signups (7d), Pipeline Success Rate, Avg Processing Time, Error Rate (24h), Active Voice Calls
- Each card: value + trend sparkline
- Data: `GET /api/v1/admin/stats`, `GET /api/v1/admin/unified-pipeline/health`
- AC: 6 KPI cards render with correct data; sparklines show trends

**FR-017**: User Management — List
- Searchable data table with server-side pagination
- Search by name, Telegram ID, email, UUID
- Filters: chapter (1-5), engagement state, score range, game status
- Sortable columns: Name, Score, Chapter, Engagement, Status, Last Active
- Data: `GET /api/v1/admin/users`
- AC: Search returns matching users; filters narrow results; pagination works

**FR-018**: User Management — Detail
- Full profile card with all user fields
- 4-metric radar chart (same component as player)
- Tabs: Conversations, Memory Facts, Ready Prompts, Pipeline History
- Data: `GET /api/v1/admin/users/{id}/*` (metrics, engagement, vices, conversations, memory, scores, boss)
- AC: Profile renders all fields; tabs load data on selection; radar matches player component

**FR-019**: User Management — God Mode Mutations
- Amber-bordered glass card panel with mutation controls
- SET score: number input (0-100); SET chapter: dropdown (1-5); SET engagement: dropdown (6 states)
- SET status: dropdown (active/boss_fight/game_over/won); RESET boss: button; Clear engagement: button
- All require reason text + confirmation dialog
- Data: `PUT /api/v1/admin/users/{id}/{score|chapter|status|engagement}`, `POST /api/v1/admin/users/{id}/{reset-boss|clear-engagement}`
- AC: All 6 existing mutations work; confirmation required; reason logged; optimistic UI update

**FR-020**: Pipeline Health Board
- 9-column stage display (extraction → prompt_builder) using Spec 042 actual stage names
- Per-stage: success rate %, avg time ms, error count
- Color coding: green (>95%), amber (80-95%), red (<80%)
- Recent failures table: conversation ID, stage, error, timestamp
- Data: `GET /api/v1/admin/unified-pipeline/health`
- AC: 9 stages render with correct names; color coding matches thresholds; failures listed

**FR-021**: Voice Monitor
- Call history table: date, duration, user, agent ID
- Transcript viewer side panel: chat-bubble format with timestamps
- Data: `GET /api/v1/admin/voice/conversations`, `GET /api/v1/admin/voice/conversations/{id}`
- AC: Call list paginated; transcript renders in bubbles; metadata visible

**FR-022**: Text Monitor
- Conversation list with filters (user, date range, platform)
- Pipeline stage viewer: horizontal stepper with timing per stage
- Thread/Thought inspectors
- Data: `GET /api/v1/admin/text/*` endpoints
- AC: Conversation list loads; pipeline stepper shows 9 stages; threads/thoughts visible

**FR-023**: Job Monitor
- 5 job cards (decay, deliver, summary, cleanup, process-conversations)
- Per job: last run time + status, execution history chart (24h), manual trigger button
- Data: `GET /api/v1/admin/processing-stats`
- AC: 5 job cards render; manual trigger with confirmation; history chart loads

**FR-024**: Prompt Inspector
- Prompt list: user, platform, timestamp, token count
- Prompt viewer: syntax-highlighted system prompt
- Token breakdown visualization
- Data: `GET /api/v1/admin/prompts`, `GET /api/v1/admin/conversations/{id}/prompts`
- AC: Prompt list loads; viewer shows formatted prompt; token count visible

**FR-025**: Admin Sidebar Navigation
- Same component as player sidebar but with cyan accent + admin items
- Items: Overview, Users, Voice, Text, Pipeline, Jobs, Prompts
- AC: All 7 nav items accessible; cyan accent on active; collapse/expand works

### Backend Changes (FR-026 — FR-030)

**FR-026**: Fix Admin Prompt Endpoints (MODIFY)
- `GET /api/v1/admin/prompts` currently returns empty stub → query `generated_prompts` + `ready_prompts` tables
- `GET /api/v1/admin/prompts/{id}` returns 501 → return actual prompt data with token count
- AC: Both endpoints return real data; token count calculated; paginated

**FR-027**: Fix Pipeline Stage Names (MODIFY)
- `GET /admin/debug/text/pipeline/{conv_id}` uses old hardcoded stage names
- Update to use `PipelineOrchestrator.STAGE_DEFINITIONS` or query `job_executions`
- AC: Pipeline status returns correct 9 stage names matching Spec 042

**FR-028**: Remove Deprecated Endpoints (DEPRECATE)
- Delete `GET /api/v1/admin/pipeline-health` (returns `status="deprecated"`)
- Remove duplicate `POST /api/v1/tasks/touchpoints` at line 733
- AC: Deprecated endpoint returns 410 Gone; duplicate route removed

**FR-029**: New Admin Mutation Endpoints
- `POST /api/v1/admin/users/{id}/trigger-pipeline` — trigger pipeline run for user
- `GET /api/v1/admin/users/{id}/pipeline-history` — pipeline execution timeline with stage timings
- `PUT /api/v1/admin/users/{id}/metrics` — set individual metrics (intimacy, passion, trust, secureness)
- AC: All 3 endpoints return correct data; trigger starts actual pipeline; metrics update persists

**FR-030**: Fix Summary Generation Stub (MODIFY)
- `POST /api/v1/tasks/summary` returns deprecated placeholder → implement using PromptGenerator
- `POST /admin/debug/prompts/{user_id}/preview` returns deprecated stub → use PromptGenerator
- AC: Summary endpoint generates LLM summaries; prompt preview returns actual generated prompt

---

## Non-Functional Requirements

**NFR-001**: Performance
- Initial page load < 2s (LCP); interaction response < 200ms; TanStack Query cache for repeated requests
- Recharts lazy-loaded; code-split per route

**NFR-002**: Accessibility
- WCAG 2.1 AA compliance; keyboard navigation for all interactive elements
- aria-labels on charts and data visualizations; 4.5:1 contrast ratio on glass surfaces

**NFR-003**: Responsive Design
- Player dashboard: mobile-first (stacked layout < 768px, grid >= 1024px)
- Admin dashboard: desktop-first (minimum 1024px recommended, functional at 768px)

**NFR-004**: Dark Theme Only
- No light theme support; all design tokens assume dark background
- `prefers-reduced-motion` support for animations

**NFR-005**: Type Safety
- Strict TypeScript (`strict: true`); Zod schemas for API responses; no `any` types

---

## User Stories

### P1 — Must Have

| ID | Story | Priority |
|----|-------|----------|
| US-1 | As a player, I want to see my relationship score as an animated ring so I know my standing | P1 |
| US-2 | As a player, I want a 30-day score chart with event markers to track my trajectory | P1 |
| US-3 | As a player, I want to see hidden metrics as a radar chart to understand relationship dimensions | P1 |
| US-4 | As a player, I want to manage settings and link Telegram to configure my experience | P1 |
| US-5 | As an admin, I want to search users and see full game state to debug issues | P1 |
| US-6 | As an admin, I want to SET any user's score/chapter/engagement/status to fix game state | P1 |
| US-7 | As an admin, I want to see pipeline health per-stage to monitor system performance | P1 |

### P2 — Should Have

| ID | Story | Priority |
|----|-------|----------|
| US-8 | As a player, I want to see engagement state + multiplier to understand contact frequency effects | P2 |
| US-9 | As a player, I want a decay countdown timer to know when to talk to Nikita | P2 |
| US-10 | As a player, I want to browse my vice discoveries to see Nikita's detection patterns | P2 |
| US-11 | As a player, I want conversation history with tone/score to review past interactions | P2 |
| US-12 | As an admin, I want to monitor voice calls and text conversations to debug interactions | P2 |

### P3 — Nice to Have

| ID | Story | Priority |
|----|-------|----------|
| US-13 | As a player, I want to read Nikita's diary entries for emotional connection | P3 |
| US-14 | As an admin, I want to inspect generated prompts with token analysis | P3 |
| US-15 | As an admin, I want to manually trigger background jobs and see history | P3 |

---

## Data Models — API Contracts

### Existing Schemas (KEEP — 13 portal, 25+ admin endpoints)

All portal endpoints (`/api/v1/portal/*`) are confirmed CLEAN per API audit. Key response types:

| Schema | Endpoint | Fields |
|--------|----------|--------|
| `UserStatsResponse` | `GET /portal/stats` | id, relationship_score, chapter, chapter_name, boss_threshold, progress_to_boss, days_played, game_status, last_interaction_at, boss_attempts, metrics |
| `UserMetricsResponse` | nested in stats | intimacy, passion, trust, secureness, weights |
| `EngagementResponse` | `GET /portal/engagement` | state, multiplier, calibration_score, consecutive_*, recent_transitions[] |
| `ScoreHistoryResponse` | `GET /portal/score-history` | points[]{score, chapter, event_type, recorded_at}, total_count |
| `DecayStatusResponse` | `GET /portal/decay` | grace_period_hours, hours_remaining, decay_rate, current_score, projected_score, is_decaying |
| `VicePreferenceResponse[]` | `GET /portal/vices` | category, intensity_level, engagement_score, discovered_at |
| `AdminUserListItem` | `GET /admin/users` | id, telegram_id, email, relationship_score, chapter, engagement_state, game_status |
| `AdminSetScoreRequest` | `PUT /admin/users/{id}/score` | score (0-100), reason |

### New Schemas (FR-029)

| Schema | Purpose |
|--------|---------|
| `TriggerPipelineRequest` | `{ reason: string }` |
| `TriggerPipelineResponse` | `{ job_id: UUID, status: "started" }` |
| `PipelineHistoryResponse` | `{ runs[]: { id, started_at, completed_at, stages[]{name, duration_ms, status}, success } }` |
| `AdminSetMetricsRequest` | `{ intimacy?: float, passion?: float, trust?: float, secureness?: float, reason: string }` |

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Spec 043 not complete (pipeline broken) | HIGH | Spec 043 runs in parallel; portal can use existing endpoints first |
| Glassmorphism performance (backdrop-filter) | MEDIUM | Limit glass layers to 2-3; test on low-end devices; `will-change` hints |
| Recharts bundle size | MEDIUM | Tree-shake unused chart types; lazy-load chart components |
| Supabase Auth SSR complexity | MEDIUM | Follow `@supabase/ssr` official docs; test PKCE flow |
| Admin mutation safety | HIGH | All mutations require reason + confirmation; audit log all changes |
| Mobile radar chart readability | LOW | Simplify to bar chart on mobile; radar on desktop only |

---

## Appendix: Design Tokens Reference

See product brief `docs-to-process/20260207-product-brief-portal-redesign.md` Section 6 for complete design token definitions (backgrounds, glass surfaces, text, accents, typography, spacing, radius, animation).
