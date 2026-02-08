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

**FR-030**: Fix Prompt Preview Stub (MODIFY)
- `POST /api/v1/tasks/summary` is **already implemented** (generates LLM summaries via PromptGenerator) — no changes needed
- `POST /admin/debug/prompts/{user_id}/preview` returns deprecated stub → implement using PromptGenerator
- AC: Prompt preview endpoint returns actual generated prompt with token count; summary endpoint confirmed working

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

---

## shadcn/ui Configuration

### components.json

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": true,
  "tsx": true,
  "tailwind": {
    "config": "",
    "css": "src/app/globals.css",
    "baseColor": "zinc",
    "cssVariables": true,
    "prefix": ""
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  },
  "iconLibrary": "lucide"
}
```

### Install Command

```bash
pnpm dlx shadcn@latest add card badge table dialog tabs progress skeleton sidebar avatar tooltip input select switch separator scroll-area sheet breadcrumb dropdown-menu alert accordion slider form button sonner command popover calendar toggle hover-card chart
```

### Component Inventory

| Component | Registry | Portal Role |
|-----------|----------|-------------|
| `card` | @shadcn/card | Score hero, KPI cards, vice cards, decay warning, god-mode panel, job cards |
| `badge` | @shadcn/badge | Chapter badge, game status, engagement state, score delta chips, platform icons |
| `table` | @shadcn/table | User list (admin), call history, pipeline failures, prompt list, conversation list |
| `dialog` | @shadcn/dialog | Delete account confirmation, god-mode mutation confirmation, pipeline trigger confirm |
| `tabs` | @shadcn/tabs | User detail tabs (Conversations/Memory/Prompts/Pipeline), settings sections |
| `progress` | @shadcn/progress | Boss progress bar, pipeline stage progress, decay countdown ring |
| `skeleton` | @shadcn/skeleton | Loading states for every section (score ring, charts, cards, tables, KPIs) |
| `sidebar` | @shadcn/sidebar | Player nav (rose accent) + Admin nav (cyan accent), collapsible, mobile hamburger |
| `avatar` | @shadcn/avatar | User avatars in admin user list, conversation thread bubbles |
| `tooltip` | @shadcn/tooltip | Sidebar collapsed labels, chart data point hover, metric explanations |
| `input` | @shadcn/input | Search (admin users), god-mode score input, reason text, settings fields |
| `select` | @shadcn/select | Chapter filter, engagement filter, status filter, timezone selector, god-mode dropdowns |
| `switch` | @shadcn/switch | Feature toggles (future), notification preferences |
| `separator` | @shadcn/separator | Section dividers in settings, sidebar section separators |
| `scroll-area` | @shadcn/scroll-area | Vice discovery row, conversation message thread, prompt viewer, transcript viewer |
| `sheet` | @shadcn/sheet | Mobile sidebar overlay, voice transcript side panel, expanded conversation view |
| `breadcrumb` | @shadcn/breadcrumb | Admin navigation path (Users > User Detail > Conversations) |
| `dropdown-menu` | @shadcn/dropdown-menu | User actions menu (admin), sort options, bulk actions |
| `alert` | @shadcn/alert | Decay urgent warning, game-over notification, mutation success/error feedback |
| `accordion` | @shadcn/accordion | Pipeline stage details expand, FAQ/help sections, conversation thread groups |
| `slider` | @shadcn/slider | Score range filter (admin), metric adjustment (god-mode) |
| `form` | @shadcn/form | Settings form, god-mode mutation forms (React Hook Form + Zod integration) |
| `button` | @shadcn/button | All CTAs: "Talk to Nikita", "Trigger Pipeline", "Reset Boss", "Save Settings" |
| `sonner` | @shadcn/sonner | Toast notifications: mutation success, save confirmation, error alerts |
| `command` | @shadcn/command | Admin user search (Cmd+K palette), quick navigation |
| `popover` | @shadcn/popover | Filter dropdowns, date range picker anchor, metric explanation popups |
| `calendar` | @shadcn/calendar | Date range filter for conversations and pipeline history |
| `toggle` | @shadcn/toggle | Chart view toggles (area/line), timeline range toggles (7d/30d/all) |
| `hover-card` | @shadcn/hover-card | User preview on hover (admin list), vice detail preview |
| `chart` | @shadcn/chart | Recharts wrapper: score timeline, radar chart, sparklines, pipeline timing chart |

---

## Component Patterns

### Accessibility Requirements

All components MUST meet WCAG 2.1 AA. Per-component requirements:

| Component | Required Attributes | Notes |
|-----------|-------------------|-------|
| **Dialog** | `aria-labelledby` on dialog title, `aria-describedby` on dialog description, focus trap active while open | Confirmation dialogs must announce action consequence |
| **Table** | `aria-label` on `<table>`, `scope="col"` on headers, `aria-sort` on sortable columns, `aria-live="polite"` on pagination status | Admin tables must announce row count changes |
| **Tabs** | `aria-selected` on active tab, `aria-controls` linking tab to panel, `role="tablist"` on container | Keyboard arrow navigation between tabs |
| **Sidebar** | `aria-expanded` on toggle, `aria-current="page"` on active item, `role="navigation"` with `aria-label="Main"` | Collapsed state must still expose labels via `aria-label` |
| **Sheet** | `aria-modal="true"`, focus trap, `Escape` key closes, `aria-labelledby` on title | Mobile sidebar sheet must restore focus on close |
| **Alert** | `role="alert"` for urgent (decay), `role="status"` for informational, `aria-live="assertive"` for errors | Color alone must not convey meaning — include icon + text |
| **Charts** | `aria-label` describing chart purpose, `role="img"` on SVG container, `<desc>` element with data summary | Score timeline: "Score trend over 30 days, current score {N}" |
| **Radar Chart** | `aria-label` with all 4 metric values as text alternative | Fallback table for screen readers with metric name/value pairs |
| **Score Ring** | `role="meter"`, `aria-valuenow`, `aria-valuemin="0"`, `aria-valuemax="100"`, `aria-label="Relationship score"` | Announce color threshold zone in label |

### Loading States (Skeleton Patterns)

Every data-fetching section MUST show a skeleton loader while loading. Skeleton shapes match final content layout:

| Section | Skeleton Shape | Implementation |
|---------|---------------|----------------|
| **Score Ring** | Circular `Skeleton` (120px diameter) + horizontal text skeletons below | `<Skeleton className="h-[120px] w-[120px] rounded-full" />` |
| **Score Timeline Chart** | Rectangular area skeleton (full width, 280px height) | `<Skeleton className="h-[280px] w-full rounded-xl" />` |
| **Radar Chart** | Square skeleton (300x300) centered | `<Skeleton className="h-[300px] w-[300px] rounded-full mx-auto" />` |
| **Card Grid** (KPIs, Vices) | Card-shaped skeletons in grid layout (3-col lg, 2-col md, 1-col sm) | `<Skeleton className="h-[140px] rounded-xl" />` per card position |
| **Data Table** | Row skeletons (6 rows, full width, 48px height each) with column-width variation | `<Skeleton className="h-12 w-full" />` repeated, staggered widths |
| **KPI Numbers** | Short horizontal skeletons (80px width, 36px height) per metric | `<Skeleton className="h-9 w-20" />` |
| **Engagement State Machine** | 6 circular node skeletons arranged in state machine layout | `<Skeleton className="h-16 w-16 rounded-full" />` per node |
| **Decay Timer** | Circular progress skeleton (80px) + text skeleton | `<Skeleton className="h-20 w-20 rounded-full" />` |
| **Conversation List** | Card skeletons (4 items, 80px height each) stacked | `<Skeleton className="h-20 w-full rounded-lg" />` per item |
| **Sidebar** | Narrow vertical skeleton (full height, 48px/240px width) | `<Skeleton className="h-full w-12" />` (collapsed) |

**Pattern**: Create a reusable `<SectionSkeleton variant="ring|chart|card-grid|table|kpi" />` wrapper component.

### Toast System (Sonner)

Use `sonner` for all user-facing notifications. Configuration in `src/app/providers.tsx`:

```tsx
import { Toaster } from "@/components/ui/sonner"

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <>
      {children}
      <Toaster
        richColors
        theme="dark"
        position="bottom-right"
        toastOptions={{
          duration: 4000,
          classNames: {
            toast: "backdrop-blur-md bg-white/5 border-white/10",
          },
        }}
      />
    </>
  )
}
```

**Toast Types and Colors**:

| Type | Color | Use Case | Example |
|------|-------|----------|---------|
| `toast.success()` | Teal | Mutation confirmed, settings saved | "Score updated to 75" |
| `toast.error()` | Red | API failure, validation error | "Failed to save settings" |
| `toast.warning()` | Amber | Confirmation needed, rate limit | "This action cannot be undone" |
| `toast.info()` | Cyan | Status update, background job | "Pipeline triggered for user" |

**Usage Pattern**:
```tsx
import { toast } from "sonner"

// God-mode mutation
async function updateScore(userId: string, score: number, reason: string) {
  try {
    await api.put(`/admin/users/${userId}/score`, { score, reason })
    toast.success(`Score updated to ${score}`)
  } catch (error) {
    toast.error("Failed to update score", {
      description: error instanceof Error ? error.message : "Unknown error",
    })
  }
}
```

---

## Responsive Breakpoints

Tailwind breakpoint mapping to component behaviors:

| Breakpoint | Width | Player Dashboard | Admin Dashboard |
|------------|-------|------------------|-----------------|
| `< sm` (< 640px) | Mobile portrait | Cards stack vertically (1-col); score ring centered; charts full-width; bottom tab navigation | Not supported (redirect to player or show warning) |
| `sm` (640px) | Mobile landscape | Cards 1-col; score ring + chapter badge side-by-side; charts full-width | Minimal: KPIs 2-col, tables horizontal scroll |
| `md` (768px) | Tablet | Cards 2-col grid; sidebar collapses to hamburger icon; charts full-width | Functional: sidebar hamburger, tables scrollable, KPIs 2-col |
| `lg` (1024px) | Desktop | Cards 2-col; charts 2-col (timeline + radar side-by-side); sidebar expanded | Full layout: sidebar expanded, tables full-width, KPIs 3-col |
| `xl` (1280px) | Wide desktop | Cards 3-col; max-width container (1280px); generous spacing | Full layout: extra breathing room, wider side panels |

### Per-Component Responsive Rules

| Component | < md (Mobile) | md-lg (Tablet) | >= lg (Desktop) |
|-----------|---------------|----------------|-----------------|
| **Sidebar** | Hidden; bottom tab bar (5 items) + hamburger Sheet for overflow | Collapsed (48px icon-only) with expand toggle | Expanded (240px) with icon + label |
| **Score Ring** | Centered, 100px diameter, stacked above chart | Left-aligned, 120px diameter | 120px in hero section grid |
| **Charts** (Timeline, Radar) | Full width, stacked vertically, 200px height | Full width, stacked, 280px height | 2-column grid, 320px height |
| **Card Grid** (KPIs) | 1-column stack | 2-column grid | 3-column grid (2x3 for admin KPIs) |
| **Vice Cards** | Horizontal scroll row | 2-column grid | 3-4 column grid |
| **Data Tables** | Horizontal scroll with `ScrollArea`; pin first column | Full width with horizontal scroll if needed | Full width, all columns visible |
| **Dialog/Sheet** | Full-screen Sheet (bottom slide-up) | Centered Dialog (max-w-lg) | Centered Dialog (max-w-lg) |
| **Navigation** | Bottom tab bar (Dashboard, History, Vices, Settings, More) | Collapsed sidebar | Expanded sidebar |
| **Conversation Expanded** | Full-screen overlay | Side panel Sheet (50% width) | Inline expansion or side panel |

### Implementation Pattern

```tsx
// Card grid responsive pattern
<div className="grid grid-cols-1 gap-4 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
  {kpiCards.map(card => <KPICard key={card.id} {...card} />)}
</div>

// Chart layout responsive pattern
<div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
  <ScoreTimelineChart />
  <MetricsRadarChart />
</div>

// Sidebar responsive pattern (using shadcn Sidebar)
<SidebarProvider>
  <Sidebar collapsible="icon" className="hidden md:flex">
    {/* Desktop/tablet sidebar */}
  </Sidebar>
  <main className="flex-1">
    {/* Mobile bottom tabs rendered inside main */}
    <BottomTabBar className="fixed bottom-0 md:hidden" />
  </main>
</SidebarProvider>
```

---

## Environment Variables

All environment variables required for Vercel deployment:

| Variable | Scope | Required | Description |
|----------|-------|----------|-------------|
| `NEXT_PUBLIC_SUPABASE_URL` | Client + Server | Yes | Supabase project URL (e.g., `https://xxx.supabase.co`) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Client + Server | Yes | Supabase anonymous/public key for client-side auth |
| `NEXT_PUBLIC_API_URL` | Client + Server | Yes | Backend API base URL (e.g., `https://nikita-api-1040094048579.us-central1.run.app`) |
| `SUPABASE_SERVICE_ROLE_KEY` | Server only | Yes | Supabase service role key for admin operations (RLS bypass). **Never expose to client.** |

### Vercel Configuration

```bash
# Set via Vercel CLI or Dashboard
vercel env add NEXT_PUBLIC_SUPABASE_URL production
vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY production
vercel env add NEXT_PUBLIC_API_URL production
vercel env add SUPABASE_SERVICE_ROLE_KEY production  # server-only, encrypted
```

### Local Development (.env.local)

```env
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
NEXT_PUBLIC_API_URL=http://localhost:8000
SUPABASE_SERVICE_ROLE_KEY=eyJ...
```

### Security Rules

1. **`SUPABASE_SERVICE_ROLE_KEY`** must ONLY be used in Server Components, Route Handlers, and Server Actions. Never import in client components.
2. **`NEXT_PUBLIC_*`** variables are bundled into client JavaScript — only use for non-sensitive values.
3. Add `.env.local` to `.gitignore` (Next.js does this by default).
4. In Vercel, mark `SUPABASE_SERVICE_ROLE_KEY` as "Sensitive" to hide from logs.
