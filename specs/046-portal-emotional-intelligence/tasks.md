# Tasks: Spec 046 — Portal Emotional Intelligence Dashboard

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)
**Created**: 2026-02-12

---

## Progress Summary

| Phase | Tasks | Completed | Status |
|-------|-------|-----------|--------|
| 1. Backend API Endpoints + Schemas | 7 | 0 | Pending |
| 2. Frontend Foundation | 5 | 0 | Pending |
| 3. Mood Orb + Conflict Banner | 4 | 0 | Pending |
| 4. Life Events Timeline + Calendar | 4 | 0 | Pending |
| 5. Thoughts Feed + Filtering | 4 | 0 | Pending |
| 6. Narrative Arcs + Social Circle | 5 | 0 | Pending |
| 7. Hub Page + Dashboard Integration + Sidebar | 5 | 0 | Pending |
| 8. Polish + Accessibility + Testing | 4 | 0 | Pending |
| **Total** | **38** | **0** | **Pending** |

---

## Phase 1: Backend API Endpoints + Schemas

### T1.1: Add Emotional State Response Schemas
- **Status**: [ ] Pending
- **Priority**: P1
- **Effort**: S (30 min)
- **Files**: `nikita/api/schemas/portal.py`
- **ACs**:
  - [ ] AC-T1.1.1: `EmotionalStateResponse` schema with fields: state_id (str), arousal (float), valence (float), dominance (float), intimacy (float), conflict_state (Literal), conflict_started_at (datetime|None), conflict_trigger (str|None), description (str), last_updated (datetime)
  - [ ] AC-T1.1.2: `EmotionalStatePointSchema` with arousal, valence, dominance, intimacy, conflict_state, recorded_at fields
  - [ ] AC-T1.1.3: `EmotionalStateHistoryResponse` with `points: list[EmotionalStatePointSchema]` and `total_count: int`
  - [ ] AC-T1.1.4: All float fields (arousal, valence, dominance, intimacy) validated with `ge=0.0, le=1.0`
  - [ ] AC-T1.1.5: `conflict_state` uses `Literal["none", "passive_aggressive", "cold", "vulnerable", "explosive"]`

### T1.2: Add Life Events, Thoughts, Arcs, and Social Circle Response Schemas
- **Status**: [ ] Pending
- **Priority**: P1
- **Effort**: S (45 min)
- **Files**: `nikita/api/schemas/portal.py`
- **ACs**:
  - [ ] AC-T1.2.1: `LifeEventItemSchema` with event_id, time_of_day, domain, event_type, description, entities (list[str]), importance (float), emotional_impact (nested 4-delta object), narrative_arc_id; `LifeEventsResponse` with events list, date (str), total_count
  - [ ] AC-T1.2.2: `ThoughtItemSchema` with id, thought_type, content, source_conversation_id, expires_at, used_at, is_expired (bool), psychological_context (dict|None), created_at; `ThoughtsResponse` with thoughts list, total_count, has_more (bool)
  - [ ] AC-T1.2.3: `NarrativeArcItemSchema` with id, template_name, category, current_stage (Literal 5 stages), stage_progress, conversations_in_arc, max_conversations, current_description, involved_characters (list[str]), emotional_impact (dict), is_active, started_at, resolved_at; `NarrativeArcsResponse` with active_arcs, resolved_arcs, total_count
  - [ ] AC-T1.2.4: `SocialCircleMemberSchema` with id, friend_name, friend_role, age (int|None), occupation (str|None), personality (str|None), relationship_to_nikita (str|None), storyline_potential (list[str]), is_active (bool); `SocialCircleResponse` with friends list, total_count

### T1.3: Add GET /portal/emotional-state Endpoint
- **Status**: [ ] Pending
- **Priority**: P1
- **Effort**: S (30 min)
- **Files**: `nikita/api/routes/portal.py`
- **ACs**:
  - [ ] AC-T1.3.1: Endpoint registered at `GET /api/v1/portal/emotional-state` using `get_state_store()` singleton pattern
  - [ ] AC-T1.3.2: Calls `state.to_description()` for the description field
  - [ ] AC-T1.3.3: Returns default state (all 0.5, conflict_state="none", description from defaults) when no state exists for user
  - [ ] AC-T1.3.4: Follows existing DI pattern `Annotated[UUID, Depends(get_current_user_id)]` for auth

### T1.4: Add GET /portal/emotional-state/history Endpoint
- **Status**: [ ] Pending
- **Priority**: P1
- **Effort**: S (30 min)
- **Files**: `nikita/api/routes/portal.py`
- **ACs**:
  - [ ] AC-T1.4.1: Endpoint registered at `GET /api/v1/portal/emotional-state/history` with `hours` query param (default: 24)
  - [ ] AC-T1.4.2: Calls `get_state_store().get_state_history(user_id, days=ceil(hours/24), limit=100)` and filters to requested hours window
  - [ ] AC-T1.4.3: Returns empty `points` list (not error) when no history exists

### T1.5: Add GET /portal/life-events and GET /portal/thoughts Endpoints
- **Status**: [ ] Pending
- **Priority**: P1
- **Effort**: M (60 min)
- **Files**: `nikita/api/routes/portal.py`, `nikita/db/repositories/thought_repository.py`
- **ACs**:
  - [ ] AC-T1.5.1: Life events endpoint at `GET /api/v1/portal/life-events` with `date` query param (YYYY-MM-DD, default: today); uses `get_event_store()` singleton; events sorted by time_of_day order (morning -> night)
  - [ ] AC-T1.5.2: Thoughts endpoint at `GET /api/v1/portal/thoughts` with `limit` (default: 20), `offset` (default: 0), `type` (default: "all") query params
  - [ ] AC-T1.5.3: New `get_paginated_thoughts(user_id, limit, offset, thought_type)` method added to `NikitaThoughtRepository` returning ALL thoughts (including expired/used) ordered by `created_at DESC`
  - [ ] AC-T1.5.4: `is_expired` computed server-side: `expires_at is not None and expires_at < utcnow()`; `has_more` computed from `total_count > offset + limit`

### T1.6: Add GET /portal/narrative-arcs and GET /portal/social-circle Endpoints
- **Status**: [ ] Pending
- **Priority**: P1
- **Effort**: S (45 min)
- **Files**: `nikita/api/routes/portal.py`
- **ACs**:
  - [ ] AC-T1.6.1: Narrative arcs endpoint at `GET /api/v1/portal/narrative-arcs` with `active_only` query param (default: true); uses `NarrativeArcRepository(session)` with standard DI
  - [ ] AC-T1.6.2: When `active_only=false`, both active and resolved arcs returned in separate lists; when `active_only=true`, resolved_arcs list is empty
  - [ ] AC-T1.6.3: Social circle endpoint at `GET /api/v1/portal/social-circle`; uses `SocialCircleRepository(session).get_circle(user_id)` with standard injected `AsyncSession`

### T1.7: Write Backend Endpoint Tests
- **Status**: [ ] Pending
- **Priority**: P1
- **Effort**: M (90 min)
- **Files**: `tests/api/test_portal_emotional.py` (NEW)
- **ACs**:
  - [ ] AC-T1.7.1: Tests for all 6 endpoints covering success cases with mock data (mocked StateStore, EventStore, and SQLAlchemy repos)
  - [ ] AC-T1.7.2: Tests for empty-state responses: no emotional state returns default, no events returns empty list, no thoughts returns empty list, no arcs returns empty lists, no friends returns empty list
  - [ ] AC-T1.7.3: Tests for query parameter handling: date parsing for life-events, limit/offset bounds for thoughts, type filtering for thoughts, active_only toggle for arcs, hours param for history
  - [ ] AC-T1.7.4: Tests for authentication enforcement (401 without JWT)
  - [ ] AC-T1.7.5: Test `get_paginated_thoughts()` new method on `NikitaThoughtRepository` (correct ordering, offset, limit, type filter)
  - [ ] AC-T1.7.6: All tests pass (`pytest tests/api/test_portal_emotional.py -v` exits 0)

---

## Phase 2: Frontend Foundation — Types + API Client + Hooks

### T2.1: Add TypeScript Interfaces for All 6 API Responses
- **Status**: [ ] Pending
- **Priority**: P1
- **Effort**: S (30 min)
- **Files**: `portal/src/lib/api/types.ts`
- **ACs**:
  - [ ] AC-T2.1.1: `EmotionalStateResponse` and `EmotionalStatePoint` interfaces matching backend schema exactly (field names, types, nullability)
  - [ ] AC-T2.1.2: `LifeEventsResponse`, `LifeEventItem`, and `EmotionalImpact` (nested) interfaces with domain/time_of_day as string union types
  - [ ] AC-T2.1.3: `ThoughtsResponse` and `ThoughtItem` interfaces with `thought_type` as union of all 15 string literal types
  - [ ] AC-T2.1.4: `NarrativeArcsResponse`, `NarrativeArcItem`, `SocialCircleResponse`, `SocialCircleMember` interfaces
  - [ ] AC-T2.1.5: All interfaces exported; TypeScript compiles without errors (`tsc --noEmit` passes)

### T2.2: Add 6 API Client Methods to portalApi
- **Status**: [ ] Pending
- **Priority**: P1
- **Effort**: S (30 min)
- **Files**: `portal/src/lib/api/portal.ts`
- **ACs**:
  - [ ] AC-T2.2.1: `getEmotionalState()` method calling `GET /api/v1/portal/emotional-state`
  - [ ] AC-T2.2.2: `getEmotionalStateHistory(hours?: number)` method with optional hours query param; backend converts hours to days via `ceil(hours/24)` for StateStore.get_state_history(), then post-filters by exact timestamp; total_count computed from filtered result set
  - [ ] AC-T2.2.3: `getLifeEvents(date?: string)` and `getThoughts(params: { limit?: number; offset?: number; type?: string })` methods
  - [ ] AC-T2.2.4: `getNarrativeArcs(activeOnly?: boolean)` and `getSocialCircle()` methods
  - [ ] AC-T2.2.5: All methods use existing `client.get()` base pattern with auth headers from `portal/src/lib/api/client.ts`

### T2.3: Add Stale Time Constants
- **Status**: [ ] Pending
- **Priority**: P1
- **Effort**: S (15 min)
- **Files**: `portal/src/lib/constants.ts`
- **ACs**:
  - [ ] AC-T2.3.1: `STALE_TIMES.emotionalState` = 15_000 (15s), `STALE_TIMES.emotionalHistory` = 60_000 (60s)
  - [ ] AC-T2.3.2: `STALE_TIMES.lifeEvents` = 60_000 (60s), `STALE_TIMES.thoughts` = 30_000 (30s)
  - [ ] AC-T2.3.3: `STALE_TIMES.narrativeArcs` = 60_000 (60s), `STALE_TIMES.socialCircle` = 300_000 (5min)

### T2.4: Create React Query Hooks for Emotional State, Life Events, and Thoughts
- **Status**: [ ] Pending
- **Priority**: P1
- **Effort**: M (60 min)
- **Files**: `portal/src/hooks/use-emotional-state.ts` (NEW), `portal/src/hooks/use-life-events.ts` (NEW), `portal/src/hooks/use-thoughts.ts` (NEW)
- **ACs**:
  - [ ] AC-T2.4.1: `useEmotionalState()` hook with `queryKey: ["emotional-state"]`, `staleTime: STALE_TIMES.emotionalState`, `refetchInterval: 30_000`
  - [ ] AC-T2.4.2: `useEmotionalHistory(hours?: number)` hook with `queryKey: ["emotional-history", hours]`, `staleTime: STALE_TIMES.emotionalHistory`, no refetchInterval
  - [ ] AC-T2.4.3: `useLifeEvents(date?: string)` hook with `queryKey: ["life-events", date]`, `staleTime: STALE_TIMES.lifeEvents`, no refetchInterval
  - [ ] AC-T2.4.4: `useThoughts(params)` hook with `queryKey: ["thoughts", params]`, `staleTime: STALE_TIMES.thoughts`, `refetchInterval: 60_000`; supports offset pagination via params

### T2.5: Create React Query Hooks for Narrative Arcs and Social Circle
- **Status**: [ ] Pending
- **Priority**: P1
- **Effort**: S (30 min)
- **Files**: `portal/src/hooks/use-narrative-arcs.ts` (NEW), `portal/src/hooks/use-social-circle.ts` (NEW)
- **ACs**:
  - [ ] AC-T2.5.1: `useNarrativeArcs(activeOnly?: boolean)` hook with `queryKey: ["narrative-arcs", activeOnly]`, `staleTime: STALE_TIMES.narrativeArcs`, no refetchInterval
  - [ ] AC-T2.5.2: `useSocialCircle()` hook with `queryKey: ["social-circle"]`, `staleTime: STALE_TIMES.socialCircle`, `gcTime: 30 * 60 * 1000`, no refetchInterval
  - [ ] AC-T2.5.3: All 5 hooks handle loading and error states via standard `useQuery` return values (`isLoading`, `isError`, `data`)

---

## Phase 3: Mood Orb + Conflict Banner Components

### T3.1: Build MoodOrb Component with 4D Animated Visualization
- **Status**: [ ] Pending
- **Priority**: P1
- **Effort**: M (90 min)
- **Files**: `portal/src/components/nikita/mood-orb.tsx` (NEW)
- **ACs**:
  - [ ] AC-T3.1.1: Orb renders as radial-gradient sphere (140px desktop, 100px mobile) inside a `GlassCard`
  - [ ] AC-T3.1.2: `arousal` (0.0-1.0) maps to CSS pulse animation speed via CSS custom property: 4s cycle at 0.0, 0.8s cycle at 1.0
  - [ ] AC-T3.1.3: `valence` (0.0-1.0) maps to color: cool blue/indigo (`#6366f1`) at 0.0, neutral purple at 0.5, warm rose/coral (`#fb7185`) at 1.0
  - [ ] AC-T3.1.4: `dominance` (0.0-1.0) maps to orb scale: `scale(0.85)` at 0.0, `scale(1.15)` at 1.0
  - [ ] AC-T3.1.5: `intimacy` (0.0-1.0) maps to glow box-shadow: `0 0 10px` dim at 0.0, `0 0 40px 15px` bright bloom at 1.0
  - [ ] AC-T3.1.6: Natural language `description` renders as muted text below the orb
  - [ ] AC-T3.1.7: Animation uses only `transform` and `opacity` properties (GPU-composited, no layout thrashing); `will-change: transform` set
  - [ ] AC-T3.1.8: Default state (all 0.5) renders as neutral purple orb with moderate pulse

### T3.2: Add Conflict State Visual Overrides to MoodOrb
- **Status**: [ ] Pending
- **Priority**: P1
- **Effort**: M (60 min)
- **Files**: `portal/src/components/nikita/mood-orb.tsx` (MODIFY), `portal/src/components/nikita/conflict-banner.tsx` (NEW)
- **ACs**:
  - [ ] AC-T3.2.1: When `conflict_state !== "none"`, orb appearance overrides: `cold` -> icy blue gradient (`#93c5fd` to `#3b82f6`), 5s frozen pulse; `passive_aggressive` -> amber/gray gradient, irregular stutter animation; `vulnerable` -> soft pink glow, small scale, high intimacy glow; `explosive` -> red gradient (`#ef4444` to `#dc2626`), 0.4s fast pulse, large scale
  - [ ] AC-T3.2.2: `ConflictBanner` component renders as `GlassCard variant="danger"` with conflict trigger text and "In conflict for Xh Ym" badge computed from `conflict_started_at`
  - [ ] AC-T3.2.3: `ConflictBanner` hidden (returns null) when `conflict_state === "none"`
  - [ ] AC-T3.2.4: "See more" link on banner navigates to `/dashboard/nikita`

### T3.3: Build MoodOrbMini Component (48px Dashboard Variant)
- **Status**: [ ] Pending
- **Priority**: P1
- **Effort**: S (30 min)
- **Files**: `portal/src/components/nikita/mood-orb-mini.tsx` (NEW)
- **ACs**:
  - [ ] AC-T3.3.1: Renders a 48px diameter orb with same color/animation logic as full MoodOrb (shared utility for color/speed computation)
  - [ ] AC-T3.3.2: One-line mood description text renders beside the orb (truncated if > ~40 chars)
  - [ ] AC-T3.3.3: Clicking navigates to `/dashboard/nikita` using `next/navigation` router
  - [ ] AC-T3.3.4: Data shared with full orb via React Query cache key `["emotional-state"]`

### T3.4: Add Mood History Sparkline (Optional Enhancement)
- **Status**: [ ] Pending
- **Priority**: P2
- **Effort**: S (45 min)
- **Files**: `portal/src/components/nikita/mood-orb.tsx` (MODIFY)
- **ACs**:
  - [ ] AC-T3.4.1: 24h valence sparkline renders as mini Recharts area chart (80px height) below the orb description, using existing Recharts pattern from portal
  - [ ] AC-T3.4.2: Sparkline hidden when fewer than 2 data points available from `useEmotionalHistory(24)`
  - [ ] AC-T3.4.3: Sparkline uses muted colors consistent with dark theme (semi-transparent fill, no axis labels)

---

## Phase 4: Life Events Timeline + Calendar

### T4.1: Build LifeEventCard Component
- **Status**: [ ] Pending
- **Priority**: P1
- **Effort**: M (60 min)
- **Files**: `portal/src/components/nikita/life-event-card.tsx` (NEW)
- **ACs**:
  - [ ] AC-T4.1.1: Card renders inside `GlassCard` with domain-colored left border: work=`#3b82f6` (blue), social=`#a855f7` (purple), personal=`#22c55e` (green)
  - [ ] AC-T4.1.2: Event type icon from Lucide icon set, mapped per `event_type` string via static config object (17 EventType values)
  - [ ] AC-T4.1.3: Entity names render as `Badge` components within each card
  - [ ] AC-T4.1.4: High-importance events (importance > 0.7) use `GlassCard variant="elevated"` for subtle highlight
  - [ ] AC-T4.1.5: Natural language `description` renders as card body text

### T4.2: Build LifeEventTimeline Component with Time-of-Day Grouping
- **Status**: [ ] Pending
- **Priority**: P1
- **Effort**: M (60 min)
- **Files**: `portal/src/components/nikita/life-event-timeline.tsx` (NEW)
- **ACs**:
  - [ ] AC-T4.2.1: Events grouped by `time_of_day` in correct order: morning, afternoon, evening, night
  - [ ] AC-T4.2.2: Section headers with Lucide time-of-day icons: Sunrise (morning), Sun (afternoon), Sunset (evening), Moon (night)
  - [ ] AC-T4.2.3: Vertical timeline layout with connecting line between event groups
  - [ ] AC-T4.2.4: Empty state shows "Nikita had a quiet day" message when no events for selected date
  - [ ] AC-T4.2.5: Skeleton loading state: 4 card skeletons (full width, 80px height) with left border

### T4.3: Build Day View Page with Calendar Navigation
- **Status**: [ ] Pending
- **Priority**: P1
- **Effort**: M (60 min)
- **Files**: `portal/src/app/(player)/dashboard/nikita/day/page.tsx` (NEW)
- **ACs**:
  - [ ] AC-T4.3.1: Page renders shadcn `Calendar` component with today selected by default
  - [ ] AC-T4.3.2: Selecting a date fetches events for that date via `useLifeEvents(date)`
  - [ ] AC-T4.3.3: Future dates disabled in the calendar
  - [ ] AC-T4.3.4: Previous/next day arrow buttons navigate one day at a time
  - [ ] AC-T4.3.5: Page uses `"use client"` directive; title "Her Day" with subtitle

### T4.4: Add Domain Filtering to Day View
- **Status**: [ ] Pending
- **Priority**: P2
- **Effort**: S (30 min)
- **Files**: `portal/src/app/(player)/dashboard/nikita/day/page.tsx` (MODIFY)
- **ACs**:
  - [ ] AC-T4.4.1: Three domain toggle buttons render with domain colors: work=blue, social=purple, personal=green
  - [ ] AC-T4.4.2: Toggling a domain filters displayed events client-side (no re-fetch needed)
  - [ ] AC-T4.4.3: Filter state persisted in URL search params via `useSearchParams`

---

## Phase 5: Thoughts Feed + Filtering

### T5.1: Build ThoughtCard Component with 15-Type Visual Treatments
- **Status**: [ ] Pending
- **Priority**: P1
- **Effort**: M (60 min)
- **Files**: `portal/src/components/nikita/thought-card.tsx` (NEW)
- **ACs**:
  - [ ] AC-T5.1.1: Static config object maps all 15 thought types to: Lucide icon component, Tailwind color class, and category (Emotional/Cognitive/Social/Psychological) -- worry=AlertTriangle/amber-400, curiosity=Search/blue-400, anticipation=Sparkles/green-400, reflection=BookOpen/purple-400, desire=Heart/rose-400, thinking=Brain/gray-400, wants_to_share=MessageCircle/teal-400, question=HelpCircle/cyan-400, feeling=Smile/pink-400, missing_him=HeartCrack/red-400, trigger_response=Zap/orange-400, defense_active=Shield/red-500, wound_surfacing=Flame/amber-500, attachment_shift=Link/indigo-400, healing_moment=Leaf/emerald-400
  - [ ] AC-T5.1.2: Thought content renders in italic serif font styling; type badge with icon and color renders at top
  - [ ] AC-T5.1.3: Expired thoughts (is_expired=true) render with 50% opacity and "expired" badge
  - [ ] AC-T5.1.4: Used thoughts (used_at not null) show "shared with you" indicator with used_at timestamp
  - [ ] AC-T5.1.5: Psychological types (trigger_response, defense_active, wound_surfacing, attachment_shift, healing_moment) show `psychological_context` metadata in a muted detail section when available

### T5.2: Build ThoughtFeed Component with Category Filtering
- **Status**: [ ] Pending
- **Priority**: P1
- **Effort**: M (60 min)
- **Files**: `portal/src/components/nikita/thought-feed.tsx` (NEW)
- **ACs**:
  - [ ] AC-T5.2.1: Horizontal scrollable filter chip bar with categories: All, Emotional (5 types), Cognitive (3 types), Social (2 types), Psychological (5 types)
  - [ ] AC-T5.2.2: Count badge per category showing number of active (non-expired) thoughts
  - [ ] AC-T5.2.3: Individual type dropdown lists all 15 types with their icons for granular filtering
  - [ ] AC-T5.2.4: Filters combinable: selecting a category pre-filters, then individual type narrows further

### T5.3: Add Thought Pagination (Load More)
- **Status**: [ ] Pending
- **Priority**: P1
- **Effort**: S (30 min)
- **Files**: `portal/src/components/nikita/thought-feed.tsx` (MODIFY)
- **ACs**:
  - [ ] AC-T5.3.1: Initial load fetches 20 most recent thoughts (newest first by `created_at`)
  - [ ] AC-T5.3.2: "Load more" button appends next page of 20 via incrementing offset parameter
  - [ ] AC-T5.3.3: Loading skeleton shown during fetch; button disabled while loading
  - [ ] AC-T5.3.4: "Load more" button hidden when `has_more === false` from API response

### T5.4: Build Mind Page
- **Status**: [ ] Pending
- **Priority**: P1
- **Effort**: S (30 min)
- **Files**: `portal/src/app/(player)/dashboard/nikita/mind/page.tsx` (NEW)
- **ACs**:
  - [ ] AC-T5.4.1: Page renders `ThoughtFeed` component as full-width content with "Her Mind" title
  - [ ] AC-T5.4.2: Skeleton loading state: 3 card skeletons (variable height 60-100px) in stacked layout
  - [ ] AC-T5.4.3: Empty state shows "No thoughts yet -- they'll appear after your next conversation" message

---

## Phase 6: Narrative Arcs + Social Circle

### T6.1: Build ArcMilestonePath Component (5-Dot Stage Indicator)
- **Status**: [ ] Pending
- **Priority**: P2
- **Effort**: S (45 min)
- **Files**: `portal/src/components/nikita/arc-milestone-path.tsx` (NEW)
- **ACs**:
  - [ ] AC-T6.1.1: 5 dots rendered in horizontal connected path with labels: setup, rising, climax, falling, resolved
  - [ ] AC-T6.1.2: Current stage dot highlighted with glow effect (box-shadow ring)
  - [ ] AC-T6.1.3: Completed stages (before current) rendered as solid filled dots
  - [ ] AC-T6.1.4: Future stages (after current) rendered as outlined/empty dots
  - [ ] AC-T6.1.5: Connecting lines between dots with appropriate styling (solid for completed segments, dashed for future)

### T6.2: Build NarrativeArcCard Component with Expandable Detail
- **Status**: [ ] Pending
- **Priority**: P2
- **Effort**: M (60 min)
- **Files**: `portal/src/components/nikita/narrative-arc-card.tsx` (NEW)
- **ACs**:
  - [ ] AC-T6.2.1: Card renders `template_name` as title, `category` as badge (e.g., "work_drama", "friendship_test")
  - [ ] AC-T6.2.2: `ArcMilestonePath` component embedded showing `current_stage`
  - [ ] AC-T6.2.3: Progress bar shows `conversations_in_arc / max_conversations` ratio as fill percentage
  - [ ] AC-T6.2.4: `involved_characters` render as `Badge` components
  - [ ] AC-T6.2.5: Click to expand shows full `current_description` text and emotional impact as 4 horizontal bar indicators (valence, arousal, dominance, intimacy deltas)
  - [ ] AC-T6.2.6: Smooth collapse/expand animation via CSS transition (max-height or height)

### T6.3: Build FriendCard Component with Expandable Detail
- **Status**: [ ] Pending
- **Priority**: P2
- **Effort**: M (60 min)
- **Files**: `portal/src/components/nikita/friend-card.tsx` (NEW)
- **ACs**:
  - [ ] AC-T6.3.1: Card shows `friend_name` as title, `friend_role` as badge, age and occupation as subtitle
  - [ ] AC-T6.3.2: Personality text truncated at 120 chars with "show more" toggle to expand full text
  - [ ] AC-T6.3.3: `storyline_potential` tags render as small `Badge` components
  - [ ] AC-T6.3.4: Active/inactive status shown with colored dot indicator: green dot for `is_active=true`, gray dot for inactive
  - [ ] AC-T6.3.5: Click to expand shows full personality, `relationship_to_nikita`, all storyline tags, adapted traits as key-value list; smooth collapse/expand animation

### T6.4: Build Stories Page (Narrative Arcs Viewer)
- **Status**: [ ] Pending
- **Priority**: P2
- **Effort**: S (45 min)
- **Files**: `portal/src/app/(player)/dashboard/nikita/stories/page.tsx` (NEW)
- **ACs**:
  - [ ] AC-T6.4.1: Active arcs section renders `NarrativeArcCard` for each active arc
  - [ ] AC-T6.4.2: Collapsed "Completed Stories" section below active arcs, expandable to show resolved arcs
  - [ ] AC-T6.4.3: Empty state shows "No active storylines -- stories develop as your relationship grows" message
  - [ ] AC-T6.4.4: Skeleton loading state: 2 card skeletons (full width, 120px) with 5-dot placeholder

### T6.5: Build Circle Page (Social Circle Gallery)
- **Status**: [ ] Pending
- **Priority**: P2
- **Effort**: S (45 min)
- **Files**: `portal/src/app/(player)/dashboard/nikita/circle/page.tsx` (NEW)
- **ACs**:
  - [ ] AC-T6.5.1: Friends render in responsive grid: 1-col mobile, 2-col tablet (md:grid-cols-2), 3-4-col desktop (lg:grid-cols-3 xl:grid-cols-4)
  - [ ] AC-T6.5.2: Each friend rendered as `FriendCard` component
  - [ ] AC-T6.5.3: Empty state shows "Nikita hasn't introduced her friends yet -- complete voice onboarding to meet them" CTA
  - [ ] AC-T6.5.4: Skeleton loading state: 4 card skeletons in grid (200px height)

---

## Phase 7: Hub Page + Dashboard Integration + Sidebar

### T7.1: Build Nikita Hub Page (`/dashboard/nikita`)
- **Status**: [ ] Pending
- **Priority**: P1
- **Effort**: M (90 min)
- **Files**: `portal/src/app/(player)/dashboard/nikita/page.tsx` (NEW)
- **ACs**:
  - [ ] AC-T7.1.1: Top section: full `MoodOrb` with `ConflictBanner` (when active) in glassmorphism card
  - [ ] AC-T7.1.2: Middle section: today's top 5 life events by importance (summary from `useLifeEvents(todayDate)`)
  - [ ] AC-T7.1.3: Bottom section: 3 most recent thoughts from `useThoughts({ limit: 3 })`
  - [ ] AC-T7.1.4: Navigation links (as glassmorphism cards or buttons) to 4 sub-pages: "Her Day", "Her Mind", "Her Stories", "Her Circle"
  - [ ] AC-T7.1.5: All sections show skeleton loaders while fetching (orb=circular 140px, events=4 cards, thoughts=3 cards)
  - [ ] AC-T7.1.6: Glassmorphism section cards with consistent spacing; page loads within 2s (LCP) on warm cache

### T7.2: Add Nikita Layout with Sub-navigation
- **Status**: [ ] Pending
- **Priority**: P1
- **Effort**: S (30 min)
- **Files**: `portal/src/app/(player)/dashboard/nikita/layout.tsx` (NEW)
- **ACs**:
  - [ ] AC-T7.2.1: Shared layout for all `/dashboard/nikita/*` pages
  - [ ] AC-T7.2.2: "Nikita's World" title header with back-to-dashboard link
  - [ ] AC-T7.2.3: Horizontal tab navigation for sub-pages: Hub, Her Day, Her Mind, Her Stories, Her Circle -- active tab highlighted

### T7.3: Integrate MoodOrbMini + ConflictBanner into Main Dashboard
- **Status**: [ ] Pending
- **Priority**: P1
- **Effort**: S (45 min)
- **Files**: `portal/src/app/(player)/dashboard/page.tsx` (MODIFY)
- **ACs**:
  - [ ] AC-T7.3.1: `MoodOrbMini` renders in the hero section alongside existing score ring; clicking navigates to `/dashboard/nikita`
  - [ ] AC-T7.3.2: `ConflictBanner` renders at top of dashboard when `conflict_state !== "none"`; hidden when no active conflict
  - [ ] AC-T7.3.3: Data fetched via `useEmotionalState()` with `staleTime: 15s` and shared React Query cache

### T7.4: Add Latest Thoughts Preview to Main Dashboard
- **Status**: [ ] Pending
- **Priority**: P1
- **Effort**: S (30 min)
- **Files**: `portal/src/app/(player)/dashboard/page.tsx` (MODIFY)
- **ACs**:
  - [ ] AC-T7.4.1: 2 most recent thoughts render as compact cards below the mood indicator
  - [ ] AC-T7.4.2: Each shows thought type icon and truncated content (80 chars max)
  - [ ] AC-T7.4.3: "See all" link navigates to `/dashboard/nikita/mind`
  - [ ] AC-T7.4.4: Section hidden when no thoughts exist

### T7.5: Update Sidebar Navigation with "Nikita's World" Section
- **Status**: [ ] Pending
- **Priority**: P1
- **Effort**: S (30 min)
- **Files**: `portal/src/components/layout/sidebar.tsx` (MODIFY)
- **ACs**:
  - [ ] AC-T7.5.1: "Nikita's World" section added to `playerItems` array between existing sections (after Score History, before Conversations) with Sparkles icon
  - [ ] AC-T7.5.2: Sub-items: "Her Day" -> `/dashboard/nikita/day`, "Her Mind" -> `/dashboard/nikita/mind`, "Her Stories" -> `/dashboard/nikita/stories`, "Her Circle" -> `/dashboard/nikita/circle`
  - [ ] AC-T7.5.3: Separator lines rendered before and after the new section
  - [ ] AC-T7.5.4: Active route highlighting works correctly for parent item and all sub-items

---

## Phase 8: Polish + Accessibility + Testing

### T8.1: Add Responsive Breakpoints for All New Components
- **Status**: [ ] Pending
- **Priority**: P1
- **Effort**: M (60 min)
- **Files**: All `portal/src/components/nikita/*.tsx` files, all new page files
- **ACs**:
  - [ ] AC-T8.1.1: MoodOrb: centered at 100px on mobile, 140px on desktop (Tailwind responsive classes)
  - [ ] AC-T8.1.2: Life event timeline: single-column on mobile with time-of-day headers
  - [ ] AC-T8.1.3: Thought cards: 1-col mobile, 2-col tablet (md:), 3-col desktop (lg:)
  - [ ] AC-T8.1.4: Friend grid: 1-col mobile, 2-col tablet (md:), 3-4-col desktop (lg: xl:)
  - [ ] AC-T8.1.5: All layouts use existing Tailwind responsive patterns from Spec 044

### T8.2: Add Accessibility Attributes and Reduced Motion Support
- **Status**: [ ] Pending
- **Priority**: P1
- **Effort**: S (45 min)
- **Files**: `portal/src/components/nikita/mood-orb.tsx`, `portal/src/components/nikita/mood-orb-mini.tsx`, `portal/src/components/nikita/thought-card.tsx`, `portal/src/components/nikita/life-event-timeline.tsx`
- **ACs**:
  - [ ] AC-T8.2.1: MoodOrb and MoodOrbMini have `role="img"` with `aria-label` describing emotional state (e.g., "Nikita is feeling [description]")
  - [ ] AC-T8.2.2: `@media (prefers-reduced-motion: reduce)` replaces pulse animation with static state indicator (no animation, just color)
  - [ ] AC-T8.2.3: All thought type icons have `aria-label` with human-readable type name
  - [ ] AC-T8.2.4: Timeline events navigable via keyboard: Tab to focus each card, Enter to expand detail
  - [ ] AC-T8.2.5: Color is never the sole indicator of meaning -- icons and text labels always accompany color coding (domains, thought types, statuses)

### T8.3: Add Empty State Messages for All Data Sections
- **Status**: [ ] Pending
- **Priority**: P1
- **Effort**: S (30 min)
- **Files**: All new page and component files
- **ACs**:
  - [ ] AC-T8.3.1: Emotional state default: neutral 0.5x4 orb with "Start talking to Nikita to see her mood" text
  - [ ] AC-T8.3.2: Life events empty: "Nikita had a quiet day" message
  - [ ] AC-T8.3.3: Thoughts empty: "No thoughts yet -- they'll appear after your next conversation" message
  - [ ] AC-T8.3.4: Narrative arcs empty: "No active storylines -- stories develop as your relationship grows" message
  - [ ] AC-T8.3.5: Social circle empty: "Nikita hasn't introduced her friends yet -- complete voice onboarding to meet them" CTA
  - [ ] AC-T8.3.6: All pages use existing `ErrorDisplay` component for API errors with retry button

### T8.4: Write Playwright E2E Tests for New Pages
- **Status**: [ ] Pending
- **Priority**: P1
- **Effort**: M (90 min)
- **Files**: `portal/e2e/nikita-world.spec.ts` (NEW)
- **ACs**:
  - [ ] AC-T8.4.1: Test: Hub page (`/dashboard/nikita`) loads and displays mood orb section, events section, thoughts section
  - [ ] AC-T8.4.2: Test: Day page (`/dashboard/nikita/day`) loads with calendar; selecting a date shows events or empty state
  - [ ] AC-T8.4.3: Test: Mind page (`/dashboard/nikita/mind`) loads with thought feed; category filter chips render and filter correctly
  - [ ] AC-T8.4.4: Test: Stories page (`/dashboard/nikita/stories`) loads; shows active arcs section and collapsed "Completed Stories" section
  - [ ] AC-T8.4.5: Test: Circle page (`/dashboard/nikita/circle`) loads; shows friend grid or empty state
  - [ ] AC-T8.4.6: Test: Sidebar "Nikita's World" section renders with all 4 sub-item links; each link navigates to correct route
  - [ ] AC-T8.4.7: Test: Main dashboard shows MoodOrbMini and thought preview cards; clicking mini orb navigates to hub
  - [ ] AC-T8.4.8: All E2E tests pass (`npx playwright test nikita-world.spec.ts` exits 0)

---

## Version History

| Date | Author | Changes |
|------|--------|---------|
| 2026-02-12 | Claude | Initial task breakdown -- 38 tasks across 8 phases, aligned with plan.md |
