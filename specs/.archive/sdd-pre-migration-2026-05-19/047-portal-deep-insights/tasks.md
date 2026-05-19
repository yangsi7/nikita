# Tasks: Spec 047 — Portal Deep Insights & History

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
**Created**: 2026-02-12

---

## Progress Summary

| Phase | Tasks | Completed | Status |
|-------|-------|-----------|--------|
| 1. Backend API | 5 | 0 | Pending |
| 2. Frontend Foundation | 4 | 0 | Pending |
| 3. Insights Page + Score Breakdown | 5 | 0 | Pending |
| 4. Open Threads Tab | 4 | 0 | Pending |
| 5. Emotional Trajectory Tab | 3 | 0 | Pending |
| 6. Enhanced Conversations | 4 | 0 | Pending |
| 7. Enhanced Engagement | 2 | 0 | Pending |
| 8. Polish + Testing | 4 | 0 | Pending |
| **Total** | **31** | **0** | **Pending** |

---

## Phase 1: Backend API (2 endpoints + schemas)

### T1.1: Add Pydantic Schemas for New Endpoints
- **Status**: [ ] Pending
- **Priority**: P2
- **Effort**: S (30 min)
- **Files**: `nikita/api/schemas/portal.py`
- **ACs**:
  - [ ] AC-T1.1.1: `DetailedScorePoint` schema with fields: `id` (UUID), `score` (float, ge=0, le=100), `chapter` (int, ge=1, le=5), `event_type` (str|None), `recorded_at` (datetime), `intimacy_delta` (float|None=None), `passion_delta` (float|None=None), `trust_delta` (float|None=None), `secureness_delta` (float|None=None), `score_delta` (float|None=None), `conversation_id` (UUID|None=None, extracted from event_details JSONB), with `model_config = {"from_attributes": True}`
  - [ ] AC-T1.1.2: `DetailedScoreHistoryResponse` schema with `points: list[DetailedScorePoint]` and `total_count: int = Field(ge=0)`
  - [ ] AC-T1.1.3: `ThreadResponse` schema with fields: `id` (UUID), `thread_type` (str), `content` (str), `status` (str), `source_conversation_id` (UUID|None=None), `created_at` (datetime), `resolved_at` (datetime|None=None), with `model_config = {"from_attributes": True}`
  - [ ] AC-T1.1.4: `ThreadListResponse` schema with `threads: list[ThreadResponse]`, `total_count: int = Field(ge=0)`, `open_count: int = Field(ge=0)`
  - [ ] AC-T1.1.5: All delta fields default to `None` for records without `event_details` JSONB

### T1.2: Add Detailed Score History Endpoint
- **Status**: [ ] Pending
- **Priority**: P2
- **Effort**: M (60 min)
- **Files**: `nikita/api/routes/portal.py`
- **ACs**:
  - [ ] AC-T1.2.1: `GET /api/v1/portal/score-history/detailed?days=30` endpoint following existing pattern (`get_current_user_id` + `get_async_session` dependencies)
  - [ ] AC-T1.2.2: Uses `ScoreHistoryRepository.get_history_since()` (at `score_history_repository.py:161-185`) and unpacks `event_details` JSONB per record: extracts `intimacy_delta`, `passion_delta`, `trust_delta`, `secureness_delta`, `composite_delta` (mapped to `score_delta`)
  - [ ] AC-T1.2.3: Missing `event_details` or missing keys gracefully default to `None`; `days` query param defaults to 30
  - [ ] AC-T1.2.4: Returns `DetailedScoreHistoryResponse` with points ordered by `recorded_at` ASC

### T1.3: Add Thread Repository Filtered Query + Thread List Endpoint
- **Status**: [ ] Pending
- **Priority**: P3
- **Effort**: M (60 min)
- **Files**: `nikita/db/repositories/thread_repository.py`, `nikita/api/routes/portal.py`
- **Note**: `get_open_threads()` at `thread_repository.py:65-93` is hardcoded to `status == "open"`. Need new method for all-status queries.
- **ACs**:
  - [ ] AC-T1.3.1: New `get_threads_filtered(user_id, status=None, thread_type=None, limit=50, offset=0)` method in `ConversationThreadRepository`; when status is None or "all", returns threads of all statuses; returns `tuple[list[ConversationThread], int]` (threads + total count)
  - [ ] AC-T1.3.2: `GET /api/v1/portal/threads?status=open&type=all&limit=50` endpoint with query params: `status` (open|resolved|expired|all, default=open), `type` (thread_type or "all", default=all), `limit` (int, default=50)
  - [ ] AC-T1.3.3: Returns `ThreadListResponse` with `open_count` computed via separate count query for open status regardless of current filter
  - [ ] AC-T1.3.4: Requires authenticated user; orders by `created_at` DESC (newest first)

### T1.4: Emotional State History Endpoint (Conditional)
- **Status**: [ ] Pending
- **Priority**: P2
- **Effort**: M (45 min)
- **Files**: `nikita/api/routes/portal.py`
- **Note**: Spec 046 defines `GET /portal/emotional-state/history?hours=24`. Check at implementation time — if already exists, mark SKIPPED and reuse.
- **ACs**:
  - [ ] AC-T1.4.1: Check if Spec 046 already added emotional-state/history endpoint — if so, mark this task SKIPPED
  - [ ] AC-T1.4.2: If not: add `GET /api/v1/portal/emotional-state/history?days=30` using `StateStore.get_state_history()` (`store.py:216-249`)
  - [ ] AC-T1.4.3: Returns `EmotionalTrajectoryResponse` (states list + total_count) ordered by `last_updated` ASC; requires authenticated user

### T1.5: Backend Unit Tests
- **Status**: [ ] Pending
- **Priority**: P2
- **Effort**: M (60 min)
- **Files**: `tests/api/test_portal_insights.py`
- **ACs**:
  - [ ] AC-T1.5.1: Detailed score history tests: returns points with metric deltas from `event_details` JSONB, handles null/missing `event_details` gracefully (defaults to None), respects `days` parameter
  - [ ] AC-T1.5.2: Thread list tests: filters by status (open/resolved/expired/all), filters by thread_type, `open_count` correct regardless of filter, pagination with limit
  - [ ] AC-T1.5.3: Repository test: `get_threads_filtered()` returns correct results for each status + type combination
  - [ ] AC-T1.5.4: Both endpoints return 401 without authentication; minimum 15 tests, all passing

---

## Phase 2: Frontend Foundation (Types + API + Hooks)

### T2.1: Fix ConversationDetail Type + Add New TypeScript Interfaces
- **Status**: [ ] Pending
- **Priority**: P2
- **Effort**: S (30 min)
- **Files**: `portal/src/lib/api/types.ts`
- **Note**: Current `ConversationDetail` (`types.ts:89-95`) is missing `extracted_entities`, `conversation_summary`, `score_delta`, `emotional_tone`, `is_boss_fight` that the backend returns. Must fix for Analysis tab.
- **ACs**:
  - [ ] AC-T2.1.1: `ConversationDetail` interface updated to include: `score_delta` (number|null), `emotional_tone` (string|null), `extracted_entities` (Record<string, unknown>|null), `conversation_summary` (string|null), `is_boss_fight` (boolean) — matching backend `ConversationDetailResponse`
  - [ ] AC-T2.1.2: New `DetailedScorePoint` interface: `id` (string), `score` (number), `chapter` (number), `event_type` (string|null), `recorded_at` (string), `intimacy_delta` (number|null), `passion_delta` (number|null), `trust_delta` (number|null), `secureness_delta` (number|null), `score_delta` (number|null), `conversation_id` (string|null)
  - [ ] AC-T2.1.3: New `DetailedScoreHistory` interface: `{ points: DetailedScorePoint[]; total_count: number }`
  - [ ] AC-T2.1.4: New `Thread` interface: `id` (string), `thread_type` (string), `content` (string), `status` (string), `source_conversation_id` (string|null), `created_at` (string), `resolved_at` (string|null)
  - [ ] AC-T2.1.5: New `ThreadList` interface: `{ threads: Thread[]; total_count: number; open_count: number }`; no `any` types used (NFR-005)

### T2.2: Add Portal API Methods
- **Status**: [ ] Pending
- **Priority**: P2
- **Effort**: S (20 min)
- **Files**: `portal/src/lib/api/portal.ts`
- **ACs**:
  - [ ] AC-T2.2.1: `portalApi.getDetailedScoreHistory(days = 30)` calling `GET /portal/score-history/detailed?days=${days}` with typed return `DetailedScoreHistory`
  - [ ] AC-T2.2.2: `portalApi.getThreads(params?: { status?: string; type?: string; limit?: number })` calling `GET /portal/threads` with query params, typed return `ThreadList`
  - [ ] AC-T2.2.3: If Spec 046 already added `getEmotionalTrajectory()`, REUSE it; otherwise add `portalApi.getEmotionalTrajectory(days = 30)`. All methods follow existing pattern at `portal.ts:8-27`

### T2.3: Create useDetailedScores Hook
- **Status**: [ ] Pending
- **Priority**: P2
- **Effort**: S (20 min)
- **Files**: `portal/src/hooks/use-detailed-scores.ts`
- **ACs**:
  - [ ] AC-T2.3.1: `useDetailedScores(days = 30)` hook using TanStack Query `useQuery`
  - [ ] AC-T2.3.2: Query key: `["portal", "detailed-scores", days]`; staleTime: `STALE_TIMES.history` (60s per NFR-006)
  - [ ] AC-T2.3.3: Returns `{ data, isLoading, error }` following existing hook pattern from `use-score-history.ts`

### T2.4: Create useThreads Hook
- **Status**: [ ] Pending
- **Priority**: P2
- **Effort**: S (20 min)
- **Files**: `portal/src/hooks/use-threads.ts`
- **ACs**:
  - [ ] AC-T2.4.1: `useThreads(status = "open", type = "all")` hook using TanStack Query
  - [ ] AC-T2.4.2: Query key: `["portal", "threads", status, type]`; staleTime: `STALE_TIMES.history` (60s per NFR-006)
  - [ ] AC-T2.4.3: Returns `{ data, isLoading, error }` following existing hook pattern

---

## Phase 3: Insights Page + Score Breakdown Tab

### T3.1: Add Insights Sidebar Nav + Page Shell with Tabs
- **Status**: [ ] Pending
- **Priority**: P2
- **Effort**: M (45 min)
- **Files**: `portal/src/components/layout/sidebar.tsx`, `portal/src/app/dashboard/insights/page.tsx`
- **ACs**:
  - [ ] AC-T3.1.1: "Insights" item added to `playerItems` array (`sidebar.tsx:21-28`) with Lucide `Lightbulb` icon and href `/dashboard/insights`; active state highlights correctly (follows `pathname.startsWith` pattern at `sidebar.tsx:72-73`)
  - [ ] AC-T3.1.2: New page at `/dashboard/insights` with shadcn `Tabs`: "Score Breakdown" | "Open Threads" | "Emotional Trajectory"
  - [ ] AC-T3.1.3: Tab state synced to URL via `?tab=scores|threads|trajectory` query param (default: `scores`)
  - [ ] AC-T3.1.4: Glassmorphism styling: `bg-white/5 backdrop-blur-md border border-white/10`; each tab content lazy-loads with skeleton

### T3.2: MetricDeltaChart Component (4-Metric Area Chart)
- **Status**: [ ] Pending
- **Priority**: P2
- **Effort**: L (90 min)
- **Files**: `portal/src/components/insights/metric-delta-chart.tsx`
- **ACs**:
  - [ ] AC-T3.2.1: Recharts `AreaChart` with 4 semi-transparent filled areas: Intimacy (rose-400), Passion (orange-400), Trust (cyan-400), Secureness (violet-400)
  - [ ] AC-T3.2.2: X-axis: dates; Y-axis: metric values 0-100 (cumulative view) or variable delta range (deltas view)
  - [ ] AC-T3.2.3: Toggle button switches between "Cumulative values" and "Per-interaction deltas" views
  - [ ] AC-T3.2.4: Hover tooltip shows date + all 4 metric values at that data point
  - [ ] AC-T3.2.5: Lazy-loaded via `next/dynamic(() => import(...), { ssr: false })` to avoid SSR Recharts issues
  - [ ] AC-T3.2.6: Responsive: min 200px height mobile, 320px desktop; `aria-label` + `role="img"` on SVG container

### T3.3: InteractionImpactList Component
- **Status**: [ ] Pending
- **Priority**: P2
- **Effort**: M (60 min)
- **Files**: `portal/src/components/insights/interaction-impact-list.tsx`
- **ACs**:
  - [ ] AC-T3.3.1: Scrollable list (shadcn `ScrollArea`) of score events ordered by `recorded_at` DESC
  - [ ] AC-T3.3.2: Each item shows: event_type icon, timestamp (relative), composite `score_delta`, and 4 metric deltas as colored pills — positive=green `+N.N`, negative=red `-N.N`, zero=gray `0.0`, null hidden
  - [ ] AC-T3.3.3: Conversation-type events render as clickable links to `/dashboard/conversations/{id}`
  - [ ] AC-T3.3.4: Event type icons (Lucide): conversation (MessageCircle), decay (TrendingDown), boss_pass (Trophy), boss_fail (XCircle), chapter_advance (ArrowUp), manual_adjustment (Wrench)

### T3.4: Score Breakdown Tab Assembly
- **Status**: [ ] Pending
- **Priority**: P2
- **Effort**: S (30 min)
- **Files**: `portal/src/app/dashboard/insights/page.tsx`
- **ACs**:
  - [ ] AC-T3.4.1: Score Breakdown tab renders `MetricDeltaChart` above `InteractionImpactList`
  - [ ] AC-T3.4.2: Data loaded via `useDetailedScores(30)` hook; passed to both child components
  - [ ] AC-T3.4.3: `aria-label` on chart section: "Score metric trends over the last 30 days"

### T3.5: Score Breakdown Loading + Empty States
- **Status**: [ ] Pending
- **Priority**: P2
- **Effort**: S (30 min)
- **Files**: `portal/src/components/insights/metric-delta-chart.tsx`, `portal/src/components/insights/interaction-impact-list.tsx`
- **ACs**:
  - [ ] AC-T3.5.1: Skeleton loaders while `useDetailedScores` is loading (chart skeleton rectangle + list skeleton rows)
  - [ ] AC-T3.5.2: Empty state when `points.length === 0`: "No score events yet. Start chatting with Nikita to see your metrics."
  - [ ] AC-T3.5.3: Error state with retry button if API call fails

---

## Phase 4: Open Threads Tab

### T4.1: ThreadSummaryCards Component
- **Status**: [ ] Pending
- **Priority**: P3
- **Effort**: M (45 min)
- **Files**: `portal/src/components/insights/thread-summary-cards.tsx`
- **ACs**:
  - [ ] AC-T4.1.1: Three GlassCard summary cards in a responsive row: "Total Open" (count), "By Type" (non-zero type pills with counts), "Oldest Open Thread" (date + age in days)
  - [ ] AC-T4.1.2: Oldest thread urgency colors: default for <=7 days, amber if >7 days, red if >14 days
  - [ ] AC-T4.1.3: Skeleton loading state for each card; cards use `bg-white/5 backdrop-blur-md border border-white/10`

### T4.2: ThreadTable Component with Expandable Rows
- **Status**: [ ] Pending
- **Priority**: P3
- **Effort**: L (90 min)
- **Files**: `portal/src/components/insights/thread-table.tsx`
- **ACs**:
  - [ ] AC-T4.2.1: shadcn `Table` with columns: Type (icon), Content (truncated 100 chars), Source Conversation (link), Status (badge), Created (relative date), Age (days)
  - [ ] AC-T4.2.2: Thread type icons (Lucide): unresolved (CircleHelp), cliffhanger (BookOpen), promise (Handshake), curiosity (Search), callback (Undo2), follow_up (Redo2), question (MessageCircleQuestion), topic (Hash)
  - [ ] AC-T4.2.3: Status badges: open (cyan with `animate-pulse`), resolved (green), expired (gray with `line-through`)
  - [ ] AC-T4.2.4: Click row to expand inline: full thread content, source conversation summary + "View Conversation" link, `created_at` timestamp, `resolved_at` if resolved; collapse on second click
  - [ ] AC-T4.2.5: Sortable by Created date (default DESC); `aria-label="Conversation threads"`, `aria-sort` on sortable column, keyboard navigable

### T4.3: Thread Type + Status Filters
- **Status**: [ ] Pending
- **Priority**: P3
- **Effort**: S (30 min)
- **Files**: `portal/src/components/insights/thread-table.tsx`
- **ACs**:
  - [ ] AC-T4.3.1: Type filter (shadcn `Select`): "All Types" + 8 thread type options
  - [ ] AC-T4.3.2: Status filter (shadcn `Select`): "Open" (default) / "Resolved" / "Expired" / "All"
  - [ ] AC-T4.3.3: Filters update `useThreads()` hook params and trigger re-fetch

### T4.4: Open Threads Tab Assembly + Empty State
- **Status**: [ ] Pending
- **Priority**: P3
- **Effort**: S (30 min)
- **Files**: `portal/src/app/dashboard/insights/page.tsx`
- **ACs**:
  - [ ] AC-T4.4.1: Open Threads tab renders `ThreadSummaryCards` above filter bar above `ThreadTable`
  - [ ] AC-T4.4.2: Empty state when zero threads: "No conversation threads yet. Threads appear after your first few conversations with Nikita."
  - [ ] AC-T4.4.3: Skeleton loaders while `useThreads` is loading (3 card skeletons + table skeleton)

---

## Phase 5: Emotional Trajectory Tab (Depends: Spec 046)

### T5.1: EmotionalTrajectoryChart Component
- **Status**: [ ] Pending
- **Priority**: P2
- **Effort**: L (90 min)
- **Files**: `portal/src/components/insights/emotional-trajectory-chart.tsx`
- **Depends**: Spec 046 emotional-state/history endpoint (reuse if available)
- **ACs**:
  - [ ] AC-T5.1.1: Recharts `AreaChart` with 4 semi-transparent lines: Arousal (amber-400), Valence (emerald-400), Dominance (blue-400), Intimacy (rose-400)
  - [ ] AC-T5.1.2: Y-axis: 0.0-1.0; X-axis: timestamps; conflict regions as vertical red-tinted `ReferenceArea` bands when `conflict_state !== "none"`
  - [ ] AC-T5.1.3: Hover tooltip shows all 4 dimension values + conflict state description at that data point
  - [ ] AC-T5.1.4: Toggle between 7-day and 30-day views via button group
  - [ ] AC-T5.1.5: Lazy-loaded via `next/dynamic({ ssr: false })`; `aria-label="Nikita's emotional trajectory over time"` + `role="img"` on SVG container; responsive min 200px mobile / 320px desktop

### T5.2: EmotionalStateDescription Component
- **Status**: [ ] Pending
- **Priority**: P2
- **Effort**: S (30 min)
- **Files**: `portal/src/components/insights/emotional-state-description.tsx`
- **ACs**:
  - [ ] AC-T5.2.1: GlassCard below chart showing latest emotional state in human-readable form (e.g. "Nikita is feeling energetic (arousal: 0.8) and happy (valence: 0.9)")
  - [ ] AC-T5.2.2: Maps dimension values to descriptive words: arousal (calm <0.3 / moderate / energetic >0.7 / excited >0.9), valence (unhappy / neutral / happy / elated), dominance (submissive / moderate / assertive), intimacy (guarded / cautious / open / vulnerable)
  - [ ] AC-T5.2.3: Includes conflict state description if not "none"; hidden entirely if no emotional data exists; updates on data refresh

### T5.3: Emotional Trajectory Tab Assembly + Fallback
- **Status**: [ ] Pending
- **Priority**: P2
- **Effort**: S (15 min)
- **Files**: `portal/src/app/dashboard/insights/page.tsx`
- **ACs**:
  - [ ] AC-T5.3.1: Emotional Trajectory tab renders `EmotionalTrajectoryChart` above `EmotionalStateDescription`
  - [ ] AC-T5.3.2: If endpoint returns 404 or empty: fallback "Emotional trajectory coming soon. This feature requires the emotional intelligence module."
  - [ ] AC-T5.3.3: Skeleton loaders during data fetch

---

## Phase 6: Enhanced Conversations

### T6.1: Enhance ConversationCard Tone Badge (FR-006)
- **Status**: [ ] Pending
- **Priority**: P2
- **Effort**: S (30 min)
- **Files**: `portal/src/components/dashboard/conversation-card.tsx`
- **Note**: FR-005 (score_delta badge) already implemented at `conversation-card.tsx:42-50`. Only FR-006 (tone badge) needs enhancement from 2px dot to labeled badge.
- **ACs**:
  - [ ] AC-T6.1.1: Replace 2px tone dot (`conversation-card.tsx:37-41`) with labeled shadcn `Badge` showing tone text value (e.g. "positive", "flirty")
  - [ ] AC-T6.1.2: Tone color mapping: positive=emerald, neutral=gray, negative=rose, mixed=amber, flirty=pink, tense=orange
  - [ ] AC-T6.1.3: Null tones render no badge; badge has text label alongside color for accessibility (NFR-002)
  - [ ] AC-T6.1.4: Verify existing FR-005 score_delta badge still renders correctly after changes

### T6.2: Add Analysis Tab to Conversation Detail Page
- **Status**: [ ] Pending
- **Priority**: P2
- **Effort**: M (45 min)
- **Files**: `portal/src/app/dashboard/conversations/[id]/page.tsx`
- **ACs**:
  - [ ] AC-T6.2.1: shadcn `Tabs` wrapping existing messages ScrollArea as "Messages" tab (default active)
  - [ ] AC-T6.2.2: New "Analysis" tab renders `ConversationAnalysis` component
  - [ ] AC-T6.2.3: Tab switching does not trigger page reload; keyboard accessible (`aria-selected`, `aria-controls`)

### T6.3: ConversationAnalysis Component
- **Status**: [ ] Pending
- **Priority**: P2
- **Effort**: M (60 min)
- **Files**: `portal/src/components/dashboard/conversation-analysis.tsx`
- **ACs**:
  - [ ] AC-T6.3.1: **Extracted Entities** section: key-value display from `extracted_entities` JSONB in a glass card; "No entities extracted" if null/empty
  - [ ] AC-T6.3.2: **Score Breakdown** section: 4-metric delta display (intimacy=rose, passion=orange, trust=cyan, secureness=violet) with colored values; "No score data" if unavailable
  - [ ] AC-T6.3.3: **Linked Threads** section: list threads where `source_conversation_id` matches; each card shows type icon, content (100 chars), status badge (open=cyan, resolved=green, expired=gray), `created_at`; click navigates to `/dashboard/insights?tab=threads`
  - [ ] AC-T6.3.4: Separator between sections; empty state per section when data null/empty

### T6.4: Wire Analysis Tab Data
- **Status**: [ ] Pending
- **Priority**: P2
- **Effort**: S (30 min)
- **Files**: `portal/src/app/dashboard/conversations/[id]/page.tsx`
- **ACs**:
  - [ ] AC-T6.4.1: Pass `extracted_entities`, `conversation_summary`, `score_delta`, `emotional_tone` from `useConversation(id)` to `ConversationAnalysis` (requires T2.1 type fix)
  - [ ] AC-T6.4.2: Linked threads fetched via `useThreads({ status: "all" })` filtered client-side by `source_conversation_id === conversation.id`
  - [ ] AC-T6.4.3: Loading skeleton for Analysis tab while data fetches

---

## Phase 7: Enhanced Engagement

### T7.1: ClingyDistantCounters Component
- **Status**: [ ] Pending
- **Priority**: P3
- **Effort**: S (30 min)
- **Files**: `portal/src/components/dashboard/clingy-distant-counters.tsx`, `portal/src/app/dashboard/engagement/page.tsx`
- **ACs**:
  - [ ] AC-T7.1.1: Two counter displays: "Consecutive Clingy Days" with warning icon (amber >3 days) and "Consecutive Distant Days" with snowflake icon (blue >3 days); 0-3 days = neutral styling
  - [ ] AC-T7.1.2: Values from existing `EngagementResponse.consecutive_clingy_days` / `consecutive_distant_days` (already returned by `useEngagement()` hook)
  - [ ] AC-T7.1.3: Tooltip explaining what calibration score means and how contact frequency affects it
  - [ ] AC-T7.1.4: Rendered below existing `EngagementPulse` visualization on engagement page

### T7.2: Calibration Score Gauge Display
- **Status**: [ ] Pending
- **Priority**: P3
- **Effort**: M (45 min)
- **Files**: `portal/src/components/dashboard/calibration-trend.tsx`, `portal/src/app/dashboard/engagement/page.tsx`
- **Note**: Calibration history is NOT stored over time. Show current value only as gauge/indicator (not trend line). Upgrade to line chart if history becomes available later.
- **ACs**:
  - [ ] AC-T7.2.1: Calibration score gauge showing current `calibration_score` (0.0-1.0) from existing `EngagementResponse` with visual indicator (progress bar or radial gauge)
  - [ ] AC-T7.2.2: Green zone at 0.7+ (ideal); amber zone 0.4-0.7 (needs improvement); red zone below 0.4 (critical); reference line at 0.7 visible
  - [ ] AC-T7.2.3: Rendered below `ClingyDistantCounters`; uses existing `useEngagement()` data; glassmorphism card styling
  - [ ] AC-T7.2.4: Explanatory text below gauge describing what the calibration score means

---

## Phase 8: Polish + Testing

### T8.1: Responsive Design Verification
- **Status**: [ ] Pending
- **Priority**: P2
- **Effort**: S (30 min)
- **Files**: All new components in `portal/src/components/insights/`, `portal/src/components/dashboard/`
- **ACs**:
  - [ ] AC-T8.1.1: Charts stack vertically on mobile (<768px), side-by-side where appropriate on desktop (>=1024px)
  - [ ] AC-T8.1.2: Thread table: horizontal scroll on mobile with pinned Type column
  - [ ] AC-T8.1.3: All area charts: min 200px height mobile, 320px desktop (NFR-003)
  - [ ] AC-T8.1.4: No horizontal overflow at any breakpoint except intentional table scroll

### T8.2: Accessibility Audit
- **Status**: [ ] Pending
- **Priority**: P2
- **Effort**: S (30 min)
- **Files**: All new components
- **ACs**:
  - [ ] AC-T8.2.1: All charts have `role="img"` + `aria-label` on SVG container (NFR-002)
  - [ ] AC-T8.2.2: Thread table: `aria-label`, sortable columns announce direction via `aria-sort`, keyboard navigable
  - [ ] AC-T8.2.3: All badges include text labels (color not sole indicator); tabs have `aria-selected` + `aria-controls`
  - [ ] AC-T8.2.4: Minimum 4.5:1 contrast ratio on glass surfaces verified

### T8.3: Playwright E2E Tests
- **Status**: [ ] Pending
- **Priority**: P2
- **Effort**: M (60 min)
- **Files**: `portal/tests/insights.spec.ts`
- **ACs**:
  - [ ] AC-T8.3.1: Test: Insights page loads at `/dashboard/insights` with 3 tabs visible; sidebar nav item present
  - [ ] AC-T8.3.2: Test: Tab switching updates URL query param (`?tab=scores`, `?tab=threads`, `?tab=trajectory`)
  - [ ] AC-T8.3.3: Test: Conversation detail Analysis tab renders entities section
  - [ ] AC-T8.3.4: Test: Engagement page shows clingy/distant counters and calibration gauge
  - [ ] AC-T8.3.5: Minimum 8 E2E tests, all passing; no regressions on existing portal E2E suite

### T8.4: Dark Theme Consistency + Performance
- **Status**: [ ] Pending
- **Priority**: P2
- **Effort**: S (20 min)
- **Files**: All new components
- **ACs**:
  - [ ] AC-T8.4.1: All cards use `bg-white/5 backdrop-blur-md border border-white/10`; badge colors follow existing portal system
  - [ ] AC-T8.4.2: No light-mode artifacts (no white backgrounds, no light text-on-light issues)
  - [ ] AC-T8.4.3: All chart components lazy-loaded via `next/dynamic` (code-split verified in network waterfall)
  - [ ] AC-T8.4.4: LCP < 2s on insights page; cached data serves immediately within staleTime window (NFR-001)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-02-12 | Initial task breakdown (27 tasks) |
| 1.1 | 2026-02-12 | Enhanced with codebase research: thread repo query, ConversationDetail type fix, file:line refs |
| 2.0 | 2026-02-12 | Full rewrite: 8-phase structure (T1.1-T8.4), 31 tasks, plan-aligned task IDs, unified AC format |
