# Spec 047: Portal Deep Insights & History

**Status**: DRAFT
**Created**: 2026-02-12
**Depends On**: Spec 044 (Portal Respec), Spec 042 (Unified Pipeline), Spec 046 (Portal Emotional Intelligence)
**Complements**: Spec 046 (Nikita-alive dashboard) -- this spec adds analytical depth for the player

---

## Problem Statement

The current portal dashboard shows high-level metrics (composite score, chapter, engagement state) but lacks analytical depth. Players cannot see how individual interactions affect their four hidden metrics (intimacy, passion, trust, secureness), cannot track unresolved conversation threads, and have no visibility into their 4D emotional trajectory over time. The `score_history.event_details` JSONB column already stores metric deltas per interaction, the `conversation_threads` table already tracks open threads, and the `emotional_states` table already stores 4D state history -- but none of this data is surfaced in the portal.

This spec adds five analytical features: per-interaction metric breakdowns, enhanced conversation cards with score/tone badges, open thread tracking, engagement calibration details, and a 4D emotional trajectory chart.

---

## Tech Stack (Inherited from Spec 044)

| Layer | Technology | Version |
|-------|-----------|---------|
| Framework | Next.js (App Router) | 16 |
| Styling | Tailwind CSS | 4 |
| Components | shadcn/ui + Radix UI | latest |
| Charts | Recharts | 2.x |
| Animation | Framer Motion | 11.x |
| Server State | TanStack Query (React Query) | 5.x |
| Deployment | Vercel | -- |
| Theme | Dark-only (glassmorphism) | -- |

---

## Functional Requirements

### Score Metric Deltas (FR-001 -- FR-004)

**FR-001**: Detailed Score History Endpoint
- New backend endpoint `GET /api/v1/portal/score-history/detailed?days=30` returning score history records with full `event_details` JSONB unpacked
- Response includes per-record metric deltas: `intimacy_delta`, `passion_delta`, `trust_delta`, `secureness_delta` extracted from `event_details`
- Data source: `ScoreHistoryRepository.get_history_since()` with `event_details` included
- AC: Endpoint returns score history with metric deltas; missing deltas default to `null`; pagination via `?days=N` parameter (default 30)

**FR-002**: Metric Delta Area Chart
- Stacked area chart (Recharts) showing 4 individual metric trends over 30 days
- Colors: Intimacy (rose-400), Passion (orange-400), Trust (cyan-400), Secureness (violet-400)
- X-axis: dates; Y-axis: cumulative metric values (0-100)
- Toggle between "Cumulative values" and "Per-interaction deltas" views
- Data: `GET /api/v1/portal/score-history/detailed`
- AC: Chart renders 4 metric lines; toggle switches views; hover tooltip shows all 4 values + date; responsive on mobile (stacks vertically)

**FR-003**: Interaction Impact List
- Below the chart, a scrollable list of recent score events showing: event_type icon, timestamp, composite score delta, and 4 individual metric deltas as colored pills
- Positive deltas: green pill with `+N.N`; Negative deltas: red pill with `-N.N`; Zero: gray pill with `0.0`
- Click links to source conversation (if event_type is `conversation`)
- AC: List shows events ordered by date DESC; pills color-coded correctly; conversation events link to `/dashboard/conversations/{id}`

**FR-004**: Insights Page Route
- New route `/dashboard/insights` containing: metric delta chart (FR-002), interaction list (FR-003), open threads tracker (FR-009), emotional trajectory chart (FR-015)
- Tab navigation at top: "Score Breakdown" | "Open Threads" | "Emotional Trajectory"
- AC: Route accessible from sidebar navigation; tabs switch content; URL updates with tab state via query param

### Enhanced Conversations (FR-005 -- FR-008)

**FR-005**: Score Delta Badges on Conversation Cards
- Existing conversation list cards (`/dashboard/conversations`) get a score_delta badge in the top-right corner
- Badge: green background + white text for positive (`+1.2`), red background + white text for negative (`-0.8`), gray for zero or null
- Data: Already available in `ConversationListItem.score_delta` field
- AC: All conversation cards show score_delta badge; badge colors correct; null deltas show no badge

**FR-006**: Emotional Tone Badges on Conversation Cards
- Add an emotional_tone badge below the score_delta badge
- Tone color mapping: positive (emerald), neutral (gray), negative (rose), mixed (amber), flirty (pink), tense (orange)
- Data: Already available in `ConversationListItem.emotional_tone` field
- AC: Tone badge renders with correct color; null tones show no badge; badge text is the tone value

**FR-007**: Conversation Analysis Tab
- Conversation detail page (`/dashboard/conversations/[id]`) gets a new "Analysis" tab alongside existing "Messages" tab
- Analysis tab shows:
  - **Extracted Entities**: Key-value display from `extracted_entities` JSONB (already in `ConversationDetailResponse`)
  - **Score Breakdown**: 4-metric delta display for this conversation (requires matching score_history record)
  - **Linked Threads**: List of conversation threads linked to this conversation via `source_conversation_id`
- Data: `ConversationDetailResponse.extracted_entities` + score_history lookup + thread lookup
- AC: Tab switches between Messages and Analysis; entities render as key-value pairs; score breakdown shows 4 metrics; linked threads clickable

**FR-008**: Conversation Thread Links in Analysis
- Threads linked to a conversation appear as clickable cards in the Analysis tab
- Each card shows: thread_type icon, content preview (truncated to 100 chars), status badge (open/resolved/expired), created_at
- Click navigates to the Insights page Open Threads tab with that thread highlighted
- AC: Linked threads appear in Analysis tab; status badge color-coded (open=cyan, resolved=green, expired=gray); click navigates correctly

### Open Threads Tracker (FR-009 -- FR-012)

**FR-009**: Thread List Endpoint
- New backend endpoint `GET /api/v1/portal/threads?status=open&type=all&limit=50`
- Returns list of `ConversationThread` records for the authenticated user
- Filters: `status` (open|resolved|expired|all), `type` (thread_type value or `all`)
- Data source: `ConversationThreadRepository.get_open_threads()` / `get_by_user()`
- AC: Endpoint returns filtered threads; pagination via limit/offset; default status=open

**FR-010**: Thread List Table
- Data table (shadcn Table) with columns: Type (icon), Content (truncated), Source Conversation (link), Status, Created, Age
- Thread type icons: unresolved (circle-question), cliffhanger (book-open), promise (handshake), curiosity (search), callback (arrow-left), follow_up (arrow-right), question (message-circle-question), topic (hash)
- Status badges: open (cyan pulse), resolved (green), expired (gray strikethrough)
- Sortable by Created date; filterable by type and status via dropdown selects
- AC: Table renders all thread fields; type icons correct; status badges color-coded; sort works; filters narrow results

**FR-011**: Thread Detail Expansion
- Click a table row to expand inline, showing: full thread content, source conversation summary (if linked), created_at timestamp, resolved_at (if resolved)
- If source conversation exists, show a "View Conversation" link to `/dashboard/conversations/{source_conversation_id}`
- AC: Row expansion shows full content; conversation link works; resolved threads show resolution timestamp

**FR-012**: Thread Summary Statistics
- Above the table, show summary cards: Total Open (count), By Type breakdown (mini chart or pill counts), Oldest Open Thread (date + age)
- AC: Counts correct; type breakdown shows non-zero types only; oldest thread highlights urgency if > 7 days old (amber) or > 14 days (red)

### Engagement Calibration Details (FR-013 -- FR-014)

**FR-013**: Calibration Trend on Engagement Page
- Enhance existing `/dashboard/engagement` page with a calibration score trend line chart (7-day or 30-day)
- Y-axis: calibration_score (0.0-1.0); X-axis: dates
- Reference line at 0.7 (ideal zone threshold) with green shading above
- Data: Requires new backend data -- engagement history over time
- AC: Trend chart renders below existing engagement state machine; reference line visible; green zone shading above 0.7

**FR-014**: Clingy/Distant Detection Display
- Show clinginess and neglect indicators on the engagement page
- Display `consecutive_clingy_days` and `consecutive_distant_days` as colored counters
- Clingy (>3 days): amber counter with warning icon; Distant (>3 days): blue counter with snowflake icon
- Ideal engagement tooltip explaining what the calibration score means
- Data: Already in `EngagementResponse.consecutive_clingy_days` / `consecutive_distant_days`
- AC: Counters render with correct values; color thresholds applied (>3 days = warning color); tooltip explains calibration

### Emotional Trajectory Chart (FR-015 -- FR-017)

**FR-015**: Emotional State History Endpoint
- Backend endpoint `GET /api/v1/portal/emotional-state/history?days=30`
- Returns time-series of `EmotionalStateModel` records: arousal, valence, dominance, intimacy, conflict_state, last_updated
- Data source: `StateStore.get_state_history()`
- Note: This endpoint may already exist from Spec 046. If so, reuse it.
- AC: Endpoint returns emotional state time-series; respects `days` parameter; ordered by last_updated ASC

**FR-016**: 4D Area Chart
- Stacked/layered area chart with 4 semi-transparent lines:
  - Arousal (amber-400), Valence (emerald-400), Dominance (blue-400), Intimacy (rose-400)
- Y-axis: 0.0-1.0; X-axis: timestamps
- Conflict regions: vertical red-tinted bands when `conflict_state != "none"`
- Hover tooltip shows all 4 values + conflict state description at that point
- Toggle between 7-day and 30-day views
- Data: `GET /api/v1/portal/emotional-state/history`
- AC: 4 lines render with correct colors; conflict bands show red shading; tooltip displays all 4 dimensions + conflict state; time range toggle works

**FR-017**: Emotional State Description
- Below the chart, a text card showing the latest emotional state in human-readable form
- Example: "Nikita is feeling energetic (arousal: 0.8) and happy (valence: 0.9), moderately assertive (dominance: 0.6), and quite open (intimacy: 0.7)"
- Updates when new data loads
- AC: Description reflects latest emotional state values; updates on data refresh; hidden if no emotional data exists

---

## Non-Functional Requirements

**NFR-001**: Performance
- All new endpoints respond in <500ms for 30 days of data
- Charts lazy-loaded (code-split) to avoid blocking initial page render
- TanStack Query cache with appropriate staleTime per data type (see Stale Time Strategy)
- AC: LCP < 2s on insights page; charts load progressively; cached data serves immediately on revisit

**NFR-002**: Accessibility
- All charts have `aria-label` describing chart purpose and `role="img"` on SVG container
- Thread table has `aria-label`, sortable columns announce sort direction
- Color is not the sole indicator: badges include text labels alongside color
- Minimum 4.5:1 contrast ratio on glass surfaces
- AC: Screen reader announces chart summaries; table is keyboard-navigable; badges readable without color

**NFR-003**: Responsive Design
- Insights page: charts stack vertically on mobile (<768px), side-by-side on desktop (>=1024px)
- Thread table: horizontal scroll on mobile with pinned Type column
- Area charts: minimum 200px height on mobile, 320px on desktop
- AC: All sections render correctly at mobile/tablet/desktop breakpoints; no horizontal overflow except intentional table scroll

**NFR-004**: Dark Theme Consistency
- All new components match Spec 044 glassmorphism design tokens
- Glass card backgrounds: `bg-white/5 backdrop-blur-md border border-white/10`
- Badge colors follow existing portal color system
- AC: Visual consistency with existing portal pages; no light-mode artifacts

**NFR-005**: Type Safety
- All new API response types defined as Zod schemas in portal
- No `any` types in new components
- Backend schemas use Pydantic v2 with strict typing
- AC: TypeScript strict mode passes; Zod validates all API responses

**NFR-006**: Data Freshness
- Thread data: staleTime 60s, no auto-refetch
- Detailed score history: staleTime 60s, no auto-refetch
- Emotional trajectory: staleTime 30s, no auto-refetch (reuses Spec 046 endpoint if available)
- Engagement calibration: staleTime 60s, no auto-refetch
- AC: Cached data served within staleTime; manual refresh triggers re-fetch; stale data shows refresh indicator

---

## User Stories

### P2 -- Should Have

| ID | Story | FRs |
|----|-------|-----|
| US-1 | As a player, I want to see how each interaction affected my 4 hidden metrics so I can understand what makes Nikita happy | FR-001, FR-002, FR-003, FR-004 |
| US-2 | As a player, I want score delta and emotional tone badges on my conversation list so I can quickly see which conversations went well | FR-005, FR-006 |
| US-3 | As a player, I want a detailed analysis tab on conversation detail pages so I can understand what Nikita extracted from our conversation | FR-007, FR-008 |
| US-5 | As a player, I want to see Nikita's emotional trajectory over time as a 4D chart so I can track her mood patterns | FR-015, FR-016, FR-017 |

### P3 -- Nice to Have

| ID | Story | FRs |
|----|-------|-----|
| US-4 | As a player, I want to see my unresolved conversation threads so I know what topics to bring up next | FR-009, FR-010, FR-011, FR-012 |
| US-6 | As a player, I want to see my engagement calibration trend and clingy/distant indicators so I can optimize my contact frequency | FR-013, FR-014 |

---

## Data Models -- API Contracts

### Existing Schemas (REUSE)

| Schema | Endpoint | Key Fields |
|--------|----------|------------|
| `ScoreHistoryPoint` | `GET /portal/score-history` | score, chapter, event_type, recorded_at |
| `ConversationListItem` | `GET /portal/conversations` | id, platform, started_at, ended_at, score_delta, emotional_tone, message_count |
| `ConversationDetailResponse` | `GET /portal/conversations/{id}` | id, messages, score_delta, emotional_tone, extracted_entities, conversation_summary |
| `EngagementResponse` | `GET /portal/engagement` | state, multiplier, calibration_score, consecutive_clingy_days, consecutive_distant_days, recent_transitions |

### New Backend Schemas

**DetailedScorePoint** (FR-001)

```python
class DetailedScorePoint(BaseModel):
    """Score history point with metric deltas from event_details JSONB."""

    id: UUID
    score: float = Field(ge=0, le=100)
    chapter: int = Field(ge=1, le=5)
    event_type: str | None
    recorded_at: datetime

    # Metric deltas (extracted from event_details JSONB)
    intimacy_delta: float | None = None
    passion_delta: float | None = None
    trust_delta: float | None = None
    secureness_delta: float | None = None

    # Composite delta
    score_delta: float | None = None

    model_config = {"from_attributes": True}


class DetailedScoreHistoryResponse(BaseModel):
    """Detailed score history with metric breakdowns."""

    points: list[DetailedScorePoint]
    total_count: int = Field(ge=0)
```

**ThreadResponse** (FR-009)

```python
class ThreadResponse(BaseModel):
    """Conversation thread for portal display."""

    id: UUID
    thread_type: str  # unresolved|cliffhanger|promise|curiosity|callback|follow_up|question|topic
    content: str
    status: str  # open|resolved|expired
    source_conversation_id: UUID | None = None
    created_at: datetime
    resolved_at: datetime | None = None

    model_config = {"from_attributes": True}


class ThreadListResponse(BaseModel):
    """Paginated thread list."""

    threads: list[ThreadResponse]
    total_count: int = Field(ge=0)
    open_count: int = Field(ge=0)
```

**EmotionalStatePoint** (FR-015 -- may already exist from Spec 046)

```python
class EmotionalStatePoint(BaseModel):
    """Emotional state point for trajectory chart."""

    arousal: float = Field(ge=0, le=1)
    valence: float = Field(ge=0, le=1)
    dominance: float = Field(ge=0, le=1)
    intimacy: float = Field(ge=0, le=1)
    conflict_state: str  # none|brewing|active|resolution|cooldown
    last_updated: datetime


class EmotionalTrajectoryResponse(BaseModel):
    """Emotional state history for charts."""

    states: list[EmotionalStatePoint]
    total_count: int = Field(ge=0)
```

### New Portal TypeScript Types

```typescript
// portal/src/lib/api/types.ts (additions)

export interface DetailedScorePoint {
  id: string
  score: number
  chapter: number
  event_type: string | null
  recorded_at: string
  intimacy_delta: number | null
  passion_delta: number | null
  trust_delta: number | null
  secureness_delta: number | null
  score_delta: number | null
}

export interface DetailedScoreHistory {
  points: DetailedScorePoint[]
  total_count: number
}

export interface Thread {
  id: string
  thread_type: string
  content: string
  status: string
  source_conversation_id: string | null
  created_at: string
  resolved_at: string | null
}

export interface ThreadList {
  threads: Thread[]
  total_count: number
  open_count: number
}

export interface EmotionalStatePoint {
  arousal: number
  valence: number
  dominance: number
  intimacy: number
  conflict_state: string
  last_updated: string
}

export interface EmotionalTrajectory {
  states: EmotionalStatePoint[]
  total_count: number
}
```

---

## New API Endpoints

| Method | Path | Response Type | Backend Source | Auth |
|--------|------|---------------|---------------|------|
| GET | `/api/v1/portal/score-history/detailed?days=30` | `DetailedScoreHistoryResponse` | `ScoreHistoryRepository.get_history_since()` + unpack `event_details` | Player |
| GET | `/api/v1/portal/threads?status=open&type=all&limit=50` | `ThreadListResponse` | `ConversationThreadRepository.get_open_threads()` / `get_by_user()` | Player |
| GET | `/api/v1/portal/emotional-state/history?days=30` | `EmotionalTrajectoryResponse` | `StateStore.get_state_history()` | Player (may overlap Spec 046) |

### Enhanced Existing Endpoints (0 backend changes)

The following already return all needed data -- only frontend rendering changes:
- `GET /api/v1/portal/conversations` -- already returns `score_delta`, `emotional_tone`
- `GET /api/v1/portal/conversations/{id}` -- already returns `extracted_entities`, `conversation_summary`
- `GET /api/v1/portal/engagement` -- already returns `calibration_score`, `consecutive_clingy_days`, `consecutive_distant_days`

---

## New/Enhanced Portal Routes

| Route | Type | Description | Tab Structure |
|-------|------|-------------|---------------|
| `/dashboard/insights` | NEW | Analytics hub | "Score Breakdown" / "Open Threads" / "Emotional Trajectory" |
| `/dashboard/conversations` | ENHANCED | Add score_delta + tone badges to cards | -- |
| `/dashboard/conversations/[id]` | ENHANCED | Add "Analysis" tab | "Messages" / "Analysis" |
| `/dashboard/engagement` | ENHANCED | Add calibration trend + clingy/distant counters | -- |

---

## Portal API Integration Pattern

```typescript
// portal/src/lib/api/portal.ts (additions)
export const portalApi = {
  // ... existing methods ...

  // New: Detailed score history with metric deltas
  getDetailedScoreHistory: (days = 30) =>
    api.get<DetailedScoreHistory>(`/portal/score-history/detailed?days=${days}`),

  // New: Conversation threads
  getThreads: (params?: { status?: string; type?: string; limit?: number }) =>
    api.get<ThreadList>("/portal/threads", { params }),

  // New: Emotional trajectory (may overlap Spec 046)
  getEmotionalTrajectory: (days = 30) =>
    api.get<EmotionalTrajectory>(`/portal/emotional-state/history?days=${days}`),
}
```

---

## Component Hierarchy

```
/dashboard/insights (NEW page)
├── InsightsTabNav
│   ├── Tab: "Score Breakdown"
│   │   ├── MetricDeltaChart (Recharts AreaChart, FR-002)
│   │   │   ├── ViewToggle ("Cumulative" | "Deltas")
│   │   │   └── ChartTooltip (4 metric values)
│   │   └── InteractionImpactList (FR-003)
│   │       └── ImpactCard[] (event_type icon, delta pills, conv link)
│   ├── Tab: "Open Threads"
│   │   ├── ThreadSummaryCards (FR-012)
│   │   │   ├── TotalOpenCard
│   │   │   ├── ByTypeBreakdown
│   │   │   └── OldestThreadCard
│   │   └── ThreadTable (FR-010, FR-011)
│   │       ├── TypeFilter (Select)
│   │       ├── StatusFilter (Select)
│   │       └── ExpandableRow[] (full content, conv link)
│   └── Tab: "Emotional Trajectory"
│       ├── EmotionalTrajectoryChart (Recharts AreaChart, FR-016)
│       │   ├── TimeRangeToggle (7d | 30d)
│       │   ├── ConflictBands (red vertical regions)
│       │   └── ChartTooltip (4D + conflict state)
│       └── EmotionalStateDescription (FR-017)

/dashboard/conversations (ENHANCED)
└── ConversationCard[] (existing)
    ├── ScoreDeltaBadge (FR-005, NEW)
    └── EmotionalToneBadge (FR-006, NEW)

/dashboard/conversations/[id] (ENHANCED)
└── ConversationDetail (existing)
    └── Tabs
        ├── "Messages" (existing)
        └── "Analysis" (NEW, FR-007)
            ├── ExtractedEntities (key-value display)
            ├── ConversationScoreBreakdown (4-metric deltas)
            └── LinkedThreadsList (FR-008)

/dashboard/engagement (ENHANCED)
└── EngagementPage (existing)
    ├── StateMachineViz (existing)
    ├── CalibrationTrendChart (NEW, FR-013)
    └── ClingyDistantCounters (NEW, FR-014)
```

---

## Stale Time Strategy

| Data | staleTime | refetchInterval | Rationale |
|------|-----------|-----------------|-----------|
| Detailed score history | 60s | none | Updated by pipeline after conversation |
| Threads | 60s | none | Updated by pipeline |
| Emotional trajectory | 30s | none | Reuses Spec 046 endpoint |
| Engagement calibration | 60s | none | Standard analytics |

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| `event_details` JSONB may not contain metric deltas for historical records | MEDIUM | Default to `null` for missing deltas; show "N/A" in UI; only recent records (post-Spec 042 pipeline) will have deltas |
| Spec 046 emotional endpoint overlap | LOW | Check if `/portal/emotional-state/history` already exists from Spec 046; if so, reuse without creating duplicate |
| Thread table empty for new users | LOW | Show empty state with explanation ("Threads appear after your first few conversations") |
| Area chart performance with 30 days of data (potentially hundreds of points) | MEDIUM | Downsample to max 200 points for chart rendering; keep full data for list view |
| Engagement calibration history not currently stored | MEDIUM | FR-013 may need new storage; fallback to showing only current calibration_score if history unavailable |
| Recharts bundle size impact from additional charts | LOW | Lazy-load chart components; shared Recharts instance across all chart pages |

---

## Dependencies on Existing Code

### Backend (Python) -- Files to Modify or Use

| File | Purpose | Change Type |
|------|---------|-------------|
| `nikita/api/schemas/portal.py` | Add `DetailedScorePoint`, `ThreadResponse`, `EmotionalStatePoint` schemas | ADD |
| `nikita/api/routes/portal.py` | Add 2-3 new endpoints | ADD |
| `nikita/db/repositories/score_history_repository.py:161-185` | `get_history_since()` already returns full `ScoreHistory` including `event_details` | REUSE |
| `nikita/db/repositories/thread_repository.py:65-93` | `get_open_threads()` already supports type filter + limit | REUSE |
| `nikita/emotional_state/store.py:216-226` | `get_state_history()` already returns `EmotionalStateModel` list | REUSE |
| `nikita/db/models/game.py:19-66` | `ScoreHistory` model with `event_details` JSONB | REUSE |
| `nikita/db/models/context.py:67-126` | `ConversationThread` model | REUSE |
| `nikita/emotional_state/models.py:34-83` | `EmotionalStateModel` with 4D + conflict | REUSE |

### Frontend (TypeScript) -- Files to Modify or Create

| File | Purpose | Change Type |
|------|---------|-------------|
| `portal/src/lib/api/types.ts` | Add new TypeScript types | ADD |
| `portal/src/lib/api/portal.ts` | Add new API methods | ADD |
| `portal/src/app/dashboard/insights/page.tsx` | New insights page | CREATE |
| `portal/src/components/insights/*` | New chart + table components | CREATE |
| `portal/src/app/dashboard/conversations/page.tsx` | Add badges to cards | MODIFY |
| `portal/src/app/dashboard/conversations/[id]/page.tsx` | Add Analysis tab | MODIFY |
| `portal/src/app/dashboard/engagement/page.tsx` | Add calibration trend + counters | MODIFY |
| `portal/src/components/ui/sidebar.tsx` (or nav config) | Add "Insights" nav item | MODIFY |

---

## shadcn/ui Components Used

All components below are already installed per Spec 044. No new installs needed.

| Component | Usage in Spec 047 |
|-----------|-------------------|
| `tabs` | Insights page tab navigation; conversation detail Messages/Analysis tabs |
| `table` | Thread list table with sortable columns |
| `badge` | Score delta badges, tone badges, thread status badges, type badges |
| `card` | Thread summary cards, emotional description card, interaction impact cards |
| `select` | Thread type filter, thread status filter |
| `tooltip` | Chart data point hover, calibration explanation, metric explanations |
| `chart` | Recharts wrapper for area charts (metric deltas, emotional trajectory, calibration trend) |
| `toggle` | Chart view toggles (cumulative/deltas, 7d/30d) |
| `skeleton` | Loading states for all new sections |
| `scroll-area` | Interaction impact list scroll, thread content expansion |
| `separator` | Section dividers in Analysis tab |
| `accordion` | Thread row expansion (alternative to inline expand) |

---

## Appendix: Backend Data Evidence

### ScoreHistory.event_details JSONB Structure

From `nikita/db/models/game.py:44-47`:
```python
event_details: Mapped[dict[str, Any] | None] = mapped_column(
    JSONB,
    nullable=True,
)  # Store deltas, reasons
```

The pipeline's GameStateStage writes metric deltas into this field during scoring. Expected structure:
```json
{
  "intimacy_delta": 1.2,
  "passion_delta": -0.3,
  "trust_delta": 0.8,
  "secureness_delta": 0.5,
  "composite_delta": 0.9,
  "reason": "positive conversation about shared interests"
}
```

### ConversationThread Types and Statuses

From `nikita/db/models/context.py:24-42`:
- **Types**: `unresolved`, `cliffhanger`, `promise`, `curiosity`, `callback`, `follow_up`, `question`, `topic`
- **Statuses**: `open`, `resolved`, `expired`

### EmotionalStateModel Dimensions

From `nikita/emotional_state/models.py:56-80`:
- **arousal** (0.0-1.0): Energy level (calm to excited)
- **valence** (0.0-1.0): Mood (negative to positive)
- **dominance** (0.0-1.0): Control (submissive to assertive)
- **intimacy** (0.0-1.0): Openness (guarded to vulnerable)
- **conflict_state**: none | brewing | active | resolution | cooldown

### Score Event Types

From `nikita/db/models/game.py:58-66`:
- `conversation`, `decay`, `boss_pass`, `boss_fail`, `chapter_advance`, `manual_adjustment`
