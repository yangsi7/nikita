# Spec 046: Portal Emotional Intelligence Dashboard

**Status**: DRAFT
**Created**: 2026-02-12
**Depends On**: Spec 044 (Portal Respec), Spec 023 (Emotional State Engine), Spec 022 (Life Simulation Engine), Spec 027 (Conflict Generation System)

---

## Problem Statement

The portal dashboard currently surfaces only ~36% of backend data. Nine complete data systems — emotional state (4D mood + conflict), life simulation (daily events), inner thoughts, narrative arcs, and social circle — are 100% invisible to the player. This spec makes Nikita "feel alive" by exposing her emotional state, daily activities, inner monologue, storylines, and social circle through an immersive, game-world-consistent dashboard. All data systems already exist in the backend (Specs 022, 023, 024, 027, 035); this spec builds the API surface and portal UI to display them.

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Backend API | FastAPI | 6 new portal endpoints in `nikita/api/routes/portal.py` |
| Data Stores | StateStore, EventStore, SQLAlchemy repos | Existing — no new tables |
| Frontend Framework | Next.js 16 (App Router) | Existing portal at `portal/` |
| Styling | Tailwind CSS 4 (dark theme) | Existing glassmorphism system |
| Components | shadcn/ui + Radix UI | Extend existing component set |
| Animation | CSS keyframes + Tailwind animate | Mood orb pulse, glow effects |
| Server State | TanStack Query 5 | Stale time strategy per data type |
| Deployment | Vercel (portal) + Cloud Run (API) | Existing infrastructure |

---

## Functional Requirements

### Mood Orb Visualization (FR-001 -- FR-003)

**FR-001**: 4D Emotional State Mood Orb
- Display Nikita's current emotional state as an animated CSS gradient orb on a glassmorphism card
- 4 dimensions mapped to visual properties:
  - `arousal` (0.0-1.0) -> pulse animation speed: 0.0 = 4s cycle (calm), 1.0 = 0.8s cycle (excited)
  - `valence` (0.0-1.0) -> color warmth: 0.0 = cool blue/indigo (`#6366f1`), 1.0 = warm rose/coral (`#fb7185`)
  - `dominance` (0.0-1.0) -> orb scale: 0.0 = `scale(0.85)` (submissive), 1.0 = `scale(1.15)` (dominant)
  - `intimacy` (0.0-1.0) -> glow intensity: 0.0 = `0 0 10px` dim, 1.0 = `0 0 40px 15px` bright bloom
- Orb rendered as radial-gradient sphere with CSS `animation: pulse` keyframe
- Natural language description from `to_description()` displayed below the orb as muted text
- Data: `GET /api/v1/portal/emotional-state` -> `EmotionalStateResponse`
- AC:
  - [ ] AC-001.1: Orb renders with radial gradient; pulse speed varies with arousal value
  - [ ] AC-001.2: Color interpolates between cool (valence < 0.3) and warm (valence > 0.7) hues
  - [ ] AC-001.3: Orb size scales proportionally with dominance dimension
  - [ ] AC-001.4: Glow box-shadow intensity correlates with intimacy value
  - [ ] AC-001.5: Natural language description renders below orb from `to_description()` output
  - [ ] AC-001.6: Default state (all 0.5) renders as neutral purple orb with moderate pulse

**FR-002**: Conflict State Visual Override
- When `conflict_state != "none"`, the orb appearance changes:
  - `cold` -> icy blue gradient (`#93c5fd` to `#3b82f6`), slow frozen pulse (5s)
  - `passive_aggressive` -> shifting amber/gray gradient, irregular stutter animation
  - `vulnerable` -> soft pink glow, small scale, high intimacy glow
  - `explosive` -> red pulsing gradient (`#ef4444` to `#dc2626`), fast 0.4s pulse, large scale
- Conflict banner displayed above the orb: danger-variant `GlassCard` with conflict trigger text
- Time-in-conflict badge: "In conflict for Xh Ym"
- Data: `conflict_state`, `conflict_started_at`, `conflict_trigger` fields from `EmotionalStateResponse`
- AC:
  - [ ] AC-002.1: Each conflict state produces visually distinct orb appearance
  - [ ] AC-002.2: Conflict banner renders as `GlassCard variant="danger"` with trigger text
  - [ ] AC-002.3: Time-in-conflict badge computes duration from `conflict_started_at`
  - [ ] AC-002.4: Banner hidden when `conflict_state === "none"`

**FR-003**: Mood History Sparkline (Optional Enhancement)
- Small sparkline chart (24h valence/arousal trend) below the orb description
- Uses existing Recharts area chart component pattern
- Data: `GET /api/v1/portal/emotional-state/history?hours=24` -> `EmotionalStateHistoryResponse`
- AC:
  - [ ] AC-003.1: Sparkline renders 24h valence trend as a mini area chart (80px height)
  - [ ] AC-003.2: Chart hidden if fewer than 2 data points available

### Life Events Timeline (FR-004 -- FR-006)

**FR-004**: Daily Life Events Timeline
- Vertical timeline layout grouped by time of day: morning, afternoon, evening, night
- Each event rendered as a glass card with:
  - Domain-colored left border: work = `#3b82f6` (blue), social = `#a855f7` (purple), personal = `#22c55e` (green)
  - Event type icon (from Lucide icon set, mapped per `EventType`)
  - Natural language `description` as card body text (already stored as natural language)
  - Entity tags rendered as `Badge` components
  - Importance indicator (high > 0.7 gets subtle highlight)
- Time-of-day section headers with appropriate icons (sunrise, sun, sunset, moon)
- Data: `GET /api/v1/portal/life-events?date=YYYY-MM-DD` -> `LifeEventsResponse`
- AC:
  - [ ] AC-004.1: Events render grouped by time_of_day in correct order (morning -> night)
  - [ ] AC-004.2: Domain color coding matches: work=blue, social=purple, personal=green
  - [ ] AC-004.3: Entity names render as Badge components within each event card
  - [ ] AC-004.4: Empty state shows "Nikita had a quiet day" message when no events exist
  - [ ] AC-004.5: High-importance events (> 0.7) have elevated glass card variant

**FR-005**: Calendar Navigation for Life Events
- Date picker (shadcn `Calendar` component) for selecting which day to view
- Default to today; past dates available, future dates disabled
- Previous/next day arrow buttons for quick navigation
- Day indicator showing event count per day (dot indicators on calendar)
- AC:
  - [ ] AC-005.1: Calendar component renders with today selected by default
  - [ ] AC-005.2: Selecting a date fetches events for that date
  - [ ] AC-005.3: Future dates are disabled in the calendar
  - [ ] AC-005.4: Previous/next buttons navigate one day at a time

**FR-006**: Event Domain Filtering
- Toggle filter buttons for work/social/personal domains
- Default: all domains shown
- Filter state persisted in URL search params
- AC:
  - [ ] AC-006.1: Three domain toggle buttons render with domain colors
  - [ ] AC-006.2: Toggling a domain filters the displayed events
  - [ ] AC-006.3: Filter state reflected in URL search params

### Nikita's Thoughts Feed (FR-007 -- FR-009)

**FR-007**: Inner Monologue Cards
- First-person thought cards displayed in a masonry or stacked layout
- 15 thought types with distinct visual treatments:

| Type | Icon | Color | Category |
|------|------|-------|----------|
| `worry` | AlertTriangle | amber-400 | Emotional |
| `curiosity` | Search | blue-400 | Cognitive |
| `anticipation` | Sparkles | green-400 | Emotional |
| `reflection` | BookOpen | purple-400 | Cognitive |
| `desire` | Heart | rose-400 | Emotional |
| `thinking` | Brain | gray-400 | Cognitive |
| `wants_to_share` | MessageCircle | teal-400 | Social |
| `question` | HelpCircle | cyan-400 | Social |
| `feeling` | Smile | pink-400 | Emotional |
| `missing_him` | HeartCrack | red-400 | Emotional |
| `trigger_response` | Zap | orange-400 | Psychological |
| `defense_active` | Shield | red-500 | Psychological |
| `wound_surfacing` | Flame | amber-500 | Psychological |
| `attachment_shift` | Link | indigo-400 | Psychological |
| `healing_moment` | Leaf | emerald-400 | Psychological |

- Each card shows: thought type badge, content text in italic/serif styling, creation timestamp
- Expired thoughts (past `expires_at`) shown with reduced opacity (0.5) and "expired" badge
- Used thoughts (non-null `used_at`) shown with "shared with you" indicator
- Source conversation link when `source_conversation_id` is present
- Data: `GET /api/v1/portal/thoughts?limit=20&type=all` -> `ThoughtsResponse`
- AC:
  - [ ] AC-007.1: Each thought type renders with its designated icon and color
  - [ ] AC-007.2: Thought content renders in italic serif font styling
  - [ ] AC-007.3: Expired thoughts render with 50% opacity and "expired" badge
  - [ ] AC-007.4: Used thoughts show "shared with you" indicator with used_at timestamp
  - [ ] AC-007.5: Psychological thought types (trigger_response, defense_active, wound_surfacing, attachment_shift, healing_moment) show psychological_context metadata when available

**FR-008**: Thought Type Filtering
- Horizontal scrollable filter chip bar with thought type categories:
  - All | Emotional | Cognitive | Social | Psychological
- Individual type filter dropdown for specific types
- Count badge per category showing number of active thoughts
- AC:
  - [ ] AC-008.1: Category filter chips render with counts
  - [ ] AC-008.2: Filtering by category shows only matching thought types
  - [ ] AC-008.3: Individual type dropdown lists all 15 types
  - [ ] AC-008.4: Filters combinable (category + individual type)

**FR-009**: Thought Pagination
- Infinite scroll or "Load more" button for older thoughts
- Default page size: 20 thoughts
- Sort: newest first (by `created_at` DESC)
- AC:
  - [ ] AC-009.1: Initial load shows 20 most recent thoughts
  - [ ] AC-009.2: "Load more" fetches next page of 20
  - [ ] AC-009.3: Loading state shown during fetch

### Narrative Arcs Viewer (FR-010 -- FR-011)

**FR-010**: Active Storyline Progress
- Each active narrative arc rendered as a glassmorphism card with:
  - Arc template name as title
  - Category badge (e.g., "work_drama", "friendship_test")
  - 5-dot connected milestone path: `setup -> rising -> climax -> falling -> resolved`
  - Current stage dot highlighted with glow effect; completed stages filled; future stages outlined
  - Stage progress percentage within current stage
  - `conversations_in_arc` / `max_conversations` as progress bar
  - Current description text
  - Involved characters as Badge components
  - Emotional impact mini-bars (valence, arousal deltas)
- Resolved arcs shown in collapsed section below active arcs
- Data: `GET /api/v1/portal/narrative-arcs` -> `NarrativeArcsResponse`
- AC:
  - [ ] AC-010.1: Active arcs render with 5-dot milestone path
  - [ ] AC-010.2: Current stage dot has glow; completed stages are filled; future stages are outlined
  - [ ] AC-010.3: Progress bar shows conversations_in_arc / max_conversations ratio
  - [ ] AC-010.4: Involved characters render as Badge components
  - [ ] AC-010.5: Resolved arcs appear in collapsed "Completed Stories" section
  - [ ] AC-010.6: Empty state shows "No active storylines" message

**FR-011**: Arc Detail View
- Click on an arc card to expand and show:
  - Full current_description text
  - Emotional impact breakdown (4 dimension deltas as horizontal bars)
  - Timeline of stage transitions (if available from metadata)
- AC:
  - [ ] AC-011.1: Clicking an arc card expands to show detail view
  - [ ] AC-011.2: Emotional impact renders as 4 horizontal bar indicators
  - [ ] AC-011.3: Collapse/expand animation is smooth

### Social Circle Gallery (FR-012 -- FR-013)

**FR-012**: Friend Character Grid
- Grid layout (2-col mobile, 3-col tablet, 4-col desktop) of friend character cards
- Each card shows:
  - Friend name as title
  - Role badge (e.g., "best_friend", "work_buddy", "gym_partner")
  - Age and occupation as subtitle text
  - Personality snippet (first 120 chars, expandable)
  - Relationship to Nikita description
  - Storyline potential tags as small Badge components
  - Active indicator (green dot for `is_active: true`, gray for inactive)
- Data: `GET /api/v1/portal/social-circle` -> `SocialCircleResponse`
- AC:
  - [ ] AC-012.1: Friend cards render in responsive grid layout
  - [ ] AC-012.2: Each card shows name, role badge, age, occupation
  - [ ] AC-012.3: Personality text truncated at 120 chars with "show more" toggle
  - [ ] AC-012.4: Storyline potential renders as small Badge components
  - [ ] AC-012.5: Active/inactive status shown with colored dot indicator
  - [ ] AC-012.6: Empty state shows "Nikita hasn't introduced her friends yet" message

**FR-013**: Friend Detail Expansion
- Click on a friend card to expand inline and show:
  - Full personality text
  - Complete relationship_to_nikita description
  - All storyline_potential tags with descriptions
  - Adapted traits as key-value list
- AC:
  - [ ] AC-013.1: Clicking a friend card expands to show full details
  - [ ] AC-013.2: Adapted traits render as key-value pairs
  - [ ] AC-013.3: Collapse/expand animation is smooth

### Main Dashboard Integration (FR-014 -- FR-016)

**FR-014**: Compact Mood Indicator on Dashboard
- Mini mood orb (48px diameter) with one-line description on the existing `/dashboard` page
- Positioned in the hero section alongside score ring
- Clicking navigates to `/dashboard/nikita` (full hub)
- Data: Reuses `GET /api/v1/portal/emotional-state` with `staleTime: 15s`
- AC:
  - [ ] AC-014.1: Mini orb renders at 48px with same color/animation mapping as full orb
  - [ ] AC-014.2: One-line mood description renders beside the orb
  - [ ] AC-014.3: Clicking the orb navigates to `/dashboard/nikita`
  - [ ] AC-014.4: Data shared with full orb via React Query cache key

**FR-015**: Conflict Banner on Dashboard
- When `conflict_state !== "none"`, a danger-variant glass card banner appears at top of dashboard
- Shows conflict state label, trigger text, and time-in-conflict
- "See more" link to `/dashboard/nikita`
- AC:
  - [ ] AC-015.1: Banner renders only when conflict_state is not "none"
  - [ ] AC-015.2: Uses `GlassCard variant="danger"` component
  - [ ] AC-015.3: Displays conflict type, trigger, and duration
  - [ ] AC-015.4: "See more" link navigates to nikita hub page

**FR-016**: Latest Thoughts Preview on Dashboard
- 1-2 most recent thoughts shown as compact cards below the mood indicator
- Thought type icon + first 80 chars of content
- "See all" link to `/dashboard/nikita/mind`
- Data: `GET /api/v1/portal/thoughts?limit=2`
- AC:
  - [ ] AC-016.1: 2 most recent thoughts render as compact cards
  - [ ] AC-016.2: Each shows thought type icon and truncated content (80 chars)
  - [ ] AC-016.3: "See all" link navigates to `/dashboard/nikita/mind`
  - [ ] AC-016.4: Hidden when no thoughts exist

### Nikita Hub Page (FR-017)

**FR-017**: Hub Page Layout (`/dashboard/nikita`)
- Full-page layout combining:
  - Mood orb visualization (FR-001, FR-002) — top section
  - Today's life events summary (top 5 by importance) — middle section
  - Recent thoughts (top 3) — bottom section
  - Navigation links to sub-pages: Day View, Mind, Stories, Circle
- Glassmorphism section cards with consistent spacing
- AC:
  - [ ] AC-017.1: Hub page renders mood orb, today's events, and recent thoughts
  - [ ] AC-017.2: Navigation links to all 4 sub-pages render and are functional
  - [ ] AC-017.3: Page loads within 2s (LCP) on warm cache
  - [ ] AC-017.4: All sections show skeleton loaders while fetching

---

## Non-Functional Requirements

**NFR-001**: Performance
- Mood orb CSS animation must not cause layout thrashing (use `transform` and `opacity` only)
- Stale time strategy prevents excessive API calls (see Stale Time Strategy table)
- All sub-pages code-split via Next.js dynamic imports
- AC: LCP < 2s on warm cache; orb animation at 60fps; no CLS from async data loading

**NFR-002**: Accessibility
- Mood orb: `role="img"` with `aria-label` describing the emotional state in plain text
- `prefers-reduced-motion`: replace pulse animation with static state indicator
- All thought type icons have `aria-label` with type name
- Timeline events navigable via keyboard (Tab/Enter)
- Color alone does not convey domain/type meaning — icons and text labels always present
- AC: WCAG 2.1 AA compliance; screen reader announces "Nikita is feeling [description]"

**NFR-003**: Responsive Design
- Mobile-first layout:
  - Mood orb centered at 100px on mobile, 140px on desktop
  - Timeline single-column on mobile, with time-of-day headers
  - Thought cards single-column on mobile, 2-column on tablet, 3-column on desktop
  - Friend grid: 1-col mobile, 2-col tablet, 3-4-col desktop
- All sections use existing responsive patterns from Spec 044

**NFR-004**: Dark Theme Consistency
- All new components use existing glassmorphism design tokens (`glass-card`, `glass-card-elevated`, `glass-card-danger`)
- No new color primitives — derive mood orb colors from existing Tailwind palette
- Consistent with existing portal dark theme

**NFR-005**: Data Freshness
- Emotional state polling: `refetchInterval: 30s` (changes with every conversation)
- Life events: no polling (generated daily, fetched on page load)
- Thoughts: `refetchInterval: 60s` (new after each pipeline run)
- Narrative arcs: no polling (advance slowly, fetched on page load)
- Social circle: no polling (set during onboarding, cached 5min)

---

## API Endpoints

### New Portal Endpoints (6)

| Method | Path | Query Params | Response Type | Source |
|--------|------|-------------|---------------|--------|
| GET | `/api/v1/portal/emotional-state` | — | `EmotionalStateResponse` | `StateStore.get_current_state(user_id)` |
| GET | `/api/v1/portal/emotional-state/history` | `hours` (default: 24) | `EmotionalStateHistoryResponse` | `StateStore.get_state_history(user_id, hours)` |
| GET | `/api/v1/portal/life-events` | `date` (YYYY-MM-DD, default: today) | `LifeEventsResponse` | `EventStore.get_events_for_date(user_id, date)` |
| GET | `/api/v1/portal/thoughts` | `limit` (default: 20), `offset`, `type` (default: all) | `ThoughtsResponse` | `NikitaThought` SQLAlchemy query |
| GET | `/api/v1/portal/narrative-arcs` | `active_only` (default: true) | `NarrativeArcsResponse` | `UserNarrativeArc` SQLAlchemy query |
| GET | `/api/v1/portal/social-circle` | — | `SocialCircleResponse` | `UserSocialCircle` SQLAlchemy query |

### Authentication

All endpoints require Supabase JWT authentication. User ID extracted from JWT claims via existing `get_current_user()` dependency. All queries scoped to authenticated user — no cross-user data access.

### Existing Endpoints Used (Unchanged)

| Endpoint | Used By |
|----------|---------|
| `GET /api/v1/portal/stats` | Dashboard hero section (score, chapter) |
| `GET /api/v1/portal/conversations` | Thought source_conversation links |

---

## Data Model — API Response Contracts

### EmotionalStateResponse

```typescript
interface EmotionalStateResponse {
  state_id: string
  arousal: number        // 0.0-1.0
  valence: number        // 0.0-1.0
  dominance: number      // 0.0-1.0
  intimacy: number       // 0.0-1.0
  conflict_state: "none" | "passive_aggressive" | "cold" | "vulnerable" | "explosive"
  conflict_started_at: string | null  // ISO 8601
  conflict_trigger: string | null
  description: string    // from to_description()
  last_updated: string   // ISO 8601
}
```

### EmotionalStateHistoryResponse

```typescript
interface EmotionalStateHistoryResponse {
  points: EmotionalStatePoint[]
  total_count: number
}

interface EmotionalStatePoint {
  arousal: number
  valence: number
  dominance: number
  intimacy: number
  conflict_state: string
  recorded_at: string    // ISO 8601
}
```

### LifeEventsResponse

```typescript
interface LifeEventsResponse {
  events: LifeEventItem[]
  date: string           // YYYY-MM-DD
  total_count: number
}

interface LifeEventItem {
  event_id: string
  time_of_day: "morning" | "afternoon" | "evening" | "night"
  domain: "work" | "social" | "personal"
  event_type: string     // One of 17 EventType values
  description: string    // Natural language
  entities: string[]     // Entity names
  importance: number     // 0.0-1.0
  emotional_impact: {
    arousal_delta: number
    valence_delta: number
    dominance_delta: number
    intimacy_delta: number
  }
  narrative_arc_id: string | null
}
```

### ThoughtsResponse

```typescript
interface ThoughtsResponse {
  thoughts: ThoughtItem[]
  total_count: number
  has_more: boolean
}

interface ThoughtItem {
  id: string
  thought_type: string   // One of 15 types
  content: string        // First-person inner monologue
  source_conversation_id: string | null
  expires_at: string | null
  used_at: string | null
  is_expired: boolean    // Computed: expires_at < now
  psychological_context: Record<string, unknown> | null
  created_at: string     // ISO 8601
}
```

### NarrativeArcsResponse

```typescript
interface NarrativeArcsResponse {
  active_arcs: NarrativeArcItem[]
  resolved_arcs: NarrativeArcItem[]
  total_count: number
}

interface NarrativeArcItem {
  id: string
  template_name: string
  category: string
  current_stage: "setup" | "rising" | "climax" | "falling" | "resolved"
  stage_progress: number
  conversations_in_arc: number
  max_conversations: number
  current_description: string | null
  involved_characters: string[]
  emotional_impact: Record<string, number>  // e.g., { valence: 0.1, arousal: -0.05 }
  is_active: boolean
  started_at: string     // ISO 8601
  resolved_at: string | null
}
```

### SocialCircleResponse

```typescript
interface SocialCircleResponse {
  friends: SocialCircleMember[]
  total_count: number
}

interface SocialCircleMember {
  id: string
  friend_name: string
  friend_role: string
  age: number | null
  occupation: string | null
  personality: string | null
  relationship_to_nikita: string | null
  storyline_potential: string[]
  is_active: boolean
}
```

---

## UI/UX Requirements

### Design System

All new components MUST use the existing glassmorphism design system from Spec 044:

| Token | Usage | Reference |
|-------|-------|-----------|
| `glass-card` | Default card container | `portal/src/components/glass/glass-card.tsx` |
| `glass-card-elevated` | High-importance event cards | `GlassCard variant="elevated"` |
| `glass-card-danger` | Conflict banner | `GlassCard variant="danger"` |
| `glass-card-amber` | Warning states | `GlassCard variant="amber"` |

### New Components Required

| Component | Location | Purpose |
|-----------|----------|---------|
| `MoodOrb` | `portal/src/components/nikita/mood-orb.tsx` | Animated 4D emotional state orb |
| `MoodOrbMini` | `portal/src/components/nikita/mood-orb-mini.tsx` | Compact 48px orb for dashboard |
| `ConflictBanner` | `portal/src/components/nikita/conflict-banner.tsx` | Conflict state alert card |
| `LifeEventCard` | `portal/src/components/nikita/life-event-card.tsx` | Single life event timeline card |
| `LifeEventTimeline` | `portal/src/components/nikita/life-event-timeline.tsx` | Full timeline with time-of-day groups |
| `ThoughtCard` | `portal/src/components/nikita/thought-card.tsx` | Inner monologue card |
| `ThoughtFeed` | `portal/src/components/nikita/thought-feed.tsx` | Filterable thought list |
| `NarrativeArcCard` | `portal/src/components/nikita/narrative-arc-card.tsx` | Storyline progress card |
| `ArcMilestonePath` | `portal/src/components/nikita/arc-milestone-path.tsx` | 5-dot stage indicator |
| `FriendCard` | `portal/src/components/nikita/friend-card.tsx` | Social circle member card |

### Portal Routes

| Route | Page Component | Description |
|-------|----------------|-------------|
| `/dashboard/nikita` | `app/dashboard/nikita/page.tsx` | Hub: orb + today events + thoughts + nav |
| `/dashboard/nikita/day` | `app/dashboard/nikita/day/page.tsx` | Full life events timeline with calendar |
| `/dashboard/nikita/mind` | `app/dashboard/nikita/mind/page.tsx` | Full thoughts browser with type filters |
| `/dashboard/nikita/stories` | `app/dashboard/nikita/stories/page.tsx` | Narrative arcs viewer |
| `/dashboard/nikita/circle` | `app/dashboard/nikita/circle/page.tsx` | Social circle gallery |

### Sidebar Navigation Update

Add "Nikita's World" section to player sidebar (between Engagement and Conversations):

```
Dashboard
Engagement
  --- separator ---
Nikita's World      <- NEW (links to /dashboard/nikita)
  Her Day           <- NEW sub-item
  Her Mind          <- NEW sub-item
  Her Stories       <- NEW sub-item
  Her Circle        <- NEW sub-item
  --- separator ---
Conversations
Diary
Vices
Settings
```

### Skeleton Loading States

| Section | Skeleton Shape |
|---------|---------------|
| Mood Orb | Circular skeleton (140px) + text skeleton (200px width) |
| Life Events | 4 card skeletons (full width, 80px height) with left border |
| Thoughts | 3 card skeletons (variable height 60-100px) in masonry |
| Narrative Arcs | 2 card skeletons (full width, 120px) with 5-dot placeholder |
| Social Circle | 4 card skeletons in grid (200px height) |

---

## Stale Time Strategy

| Data | staleTime | refetchInterval | gcTime | Rationale |
|------|-----------|-----------------|--------|-----------|
| Emotional state | 15s | 30s | 5min | Changes every conversation |
| Emotional history | 60s | none | 10min | Historical, rarely changes |
| Life events | 60s | none | 10min | Generated daily |
| Thoughts | 30s | 60s | 5min | New after each pipeline run |
| Narrative arcs | 60s | none | 10min | Advance slowly |
| Social circle | 300s | none | 30min | Set during onboarding, rarely changes |

---

## Out of Scope

- **Emotional state editing**: Players cannot modify Nikita's mood (read-only display)
- **Admin dashboard for emotional data**: Admin views of emotional state are deferred to a future spec
- **Real-time WebSocket updates**: Polling via `refetchInterval` is sufficient for MVP
- **Mood history charts**: Full multi-day mood trend analysis (only 24h sparkline in this spec)
- **Thought creation**: Players cannot create thoughts (generated by pipeline)
- **Social circle editing**: Players cannot modify friends (generated during onboarding)
- **Notification system**: Push notifications for mood changes or new thoughts
- **Export/share**: No ability to export or share emotional data

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Empty data for new users (no emotional state yet) | MEDIUM | Graceful empty states with "Start talking to Nikita" CTA |
| Mood orb CSS animation perf on low-end devices | LOW | Use only `transform` + `opacity` for GPU compositing; `prefers-reduced-motion` fallback |
| Stale emotional state if pipeline fails | LOW | Show `last_updated` timestamp so player knows data freshness |
| Large number of thoughts causing slow load | LOW | Server-side pagination (limit 20, offset-based) |
| Narrative arcs empty for users in early chapters | MEDIUM | Show "Stories develop as your relationship grows" message |
| Social circle empty if onboarding incomplete | LOW | Show "Complete voice onboarding to meet Nikita's friends" CTA |

---

## Backend Data Source Mapping

### Verified Models (with file:line references)

| Model | File | Key Fields |
|-------|------|------------|
| `EmotionalStateModel` | `nikita/emotional_state/models.py:34-306` | arousal, valence, dominance, intimacy, conflict_state, conflict_trigger, to_description() |
| `ConflictState` | `nikita/emotional_state/models.py:20-31` | none, passive_aggressive, cold, vulnerable, explosive |
| `StateStore` | `nikita/emotional_state/store.py:30-200` | get_current_state(), get_state_history() (needs hours param) |
| `LifeEvent` | `nikita/life_simulation/models.py:133-181` | event_date, time_of_day, domain, event_type, description, entities, emotional_impact, importance |
| `EventDomain` | `nikita/life_simulation/models.py:17-22` | work, social, personal |
| `EventType` | `nikita/life_simulation/models.py:25-54` | 17 types across 3 domains |
| `TimeOfDay` | `nikita/life_simulation/models.py:85-91` | morning, afternoon, evening, night |
| `EventStore` | `nikita/life_simulation/store.py:36-80` | get_events_for_date(), get_recent_events(), get_active_arcs() |
| `NikitaThought` | `nikita/db/models/context.py:129-188` | thought_type, content, source_conversation_id, expires_at, used_at, psychological_context |
| `UserNarrativeArc` | `nikita/db/models/narrative_arc.py:21-61` | template_name, category, current_stage, stage_progress, conversations_in_arc, max_conversations, involved_characters, emotional_impact |
| `UserSocialCircle` | `nikita/db/models/social_circle.py:21-51` | friend_name, friend_role, age, occupation, personality, relationship_to_nikita, storyline_potential, is_active |

### Existing Portal Patterns (to follow)

| Pattern | File | Usage |
|---------|------|-------|
| API client | `portal/src/lib/api/portal.ts:1-27` | `portalApi.getXxx()` methods |
| Type definitions | `portal/src/lib/api/types.ts:1-273` | TypeScript interfaces |
| Base client | `portal/src/lib/api/client.ts` | Auth headers, base URL |
| Glass components | `portal/src/components/glass/glass-card.tsx:1-57` | `GlassCard`, `GlassCardWithHeader` |
| Existing React Query | Page components | `useQuery` with `queryKey` and `staleTime` |
