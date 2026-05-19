# Implementation Plan: Spec 046 — Portal Emotional Intelligence Dashboard

## Research Notes

### Backend Data Sources (verified with file:line references)
- **StateStore** (`nikita/emotional_state/store.py:30-350`): Singleton, uses raw SQL. Methods: `get_current_state(user_id)`, `get_state_history(user_id, days, limit)`. Returns `EmotionalStateModel` Pydantic model with `to_description()`.
- **EventStore** (`nikita/life_simulation/store.py:36-527`): Singleton, uses raw SQL. Methods: `get_events_for_date(user_id, date)`, `get_recent_events(user_id, days)`, `get_active_arcs(user_id)`. Returns `LifeEvent`, `NarrativeArc` domain models.
- **NikitaThoughtRepository** (`nikita/db/repositories/thought_repository.py:21-289`): SQLAlchemy-based. Methods: `get_active_thoughts(user_id, thought_type, limit)`. No offset/pagination — new method needed for portal.
- **NarrativeArcRepository** (`nikita/db/repositories/narrative_arc_repository.py:22-246`): SQLAlchemy-based. Methods: `get_active_arcs(user_id)`, `get_all_arcs(user_id)`.
- **SocialCircleRepository** (`nikita/db/repositories/social_circle_repository.py:21-183`): SQLAlchemy-based. Methods: `get_circle(user_id)`, `get_active_friends(user_id)`.

### Key Differences from Existing Portal Endpoints
- **StateStore + EventStore** use internal session factories (singleton pattern), NOT the injected `AsyncSession` from `get_async_session()`. Portal endpoints will need to instantiate stores or use singletons.
- **NikitaThoughtRepository, NarrativeArcRepository, SocialCircleRepository** follow standard DI pattern with injected `AsyncSession`.

### Frontend Patterns (from Spec 044)
- **Hooks**: One hook per data domain, wraps `useQuery` with `queryKey` + `staleTime`. File: `portal/src/hooks/use-{name}.ts`.
- **API client**: `portalApi.getXxx()` methods in `portal/src/lib/api/portal.ts`.
- **Types**: Interfaces in `portal/src/lib/api/types.ts`.
- **Pages**: `portal/src/app/dashboard/{route}/page.tsx`, "use client" directive, loading/error states.
- **Components**: `portal/src/components/dashboard/` (existing) and `portal/src/components/nikita/` (new).
- **Glass system**: `GlassCard` with variants: default, elevated, danger, amber (`portal/src/components/glass/glass-card.tsx`).
- **Sidebar**: `portal/src/components/layout/sidebar.tsx` — `playerItems` array at line 21.
- **Constants**: `portal/src/lib/constants.ts` — `STALE_TIMES` object at line 30.

### StateStore/EventStore Integration Decision
StateStore and EventStore are singletons with internal session management. The portal endpoints will use `get_state_store()` and `get_event_store()` factory functions rather than injecting AsyncSession for these stores. Thought, NarrativeArc, and SocialCircle repositories will use the standard injected session.

---

## Architecture

### Component Diagram

```
Portal Backend (nikita/api/)
├── routes/portal.py               [MODIFY] Add 6 new GET endpoints
└── schemas/portal.py              [MODIFY] Add 6 new response schemas

Portal Frontend (portal/src/)
├── lib/api/
│   ├── portal.ts                  [MODIFY] Add 6 new API client methods
│   └── types.ts                   [MODIFY] Add 6 new TypeScript interfaces
├── lib/constants.ts               [MODIFY] Add stale time entries
├── hooks/
│   ├── use-emotional-state.ts     [NEW] Emotional state + history hooks
│   ├── use-life-events.ts         [NEW] Life events hook with date param
│   ├── use-thoughts.ts            [NEW] Thoughts hook with pagination
│   ├── use-narrative-arcs.ts      [NEW] Narrative arcs hook
│   └── use-social-circle.ts       [NEW] Social circle hook
├── components/nikita/
│   ├── mood-orb.tsx               [NEW] 4D animated mood orb
│   ├── mood-orb-mini.tsx          [NEW] 48px compact orb
│   ├── conflict-banner.tsx        [NEW] Conflict state alert
│   ├── life-event-card.tsx        [NEW] Single event card
│   ├── life-event-timeline.tsx    [NEW] Full timeline with grouping
│   ├── thought-card.tsx           [NEW] Inner monologue card
│   ├── thought-feed.tsx           [NEW] Filterable thought list
│   ├── narrative-arc-card.tsx     [NEW] Arc progress card
│   ├── arc-milestone-path.tsx     [NEW] 5-dot stage indicator
│   └── friend-card.tsx            [NEW] Social circle member card
├── components/layout/sidebar.tsx  [MODIFY] Add "Nikita's World" section
├── app/dashboard/page.tsx         [MODIFY] Add mini orb + conflict banner + thought preview
└── app/dashboard/nikita/
    ├── page.tsx                   [NEW] Hub page
    ├── day/page.tsx               [NEW] Life events timeline
    ├── mind/page.tsx              [NEW] Thoughts browser
    ├── stories/page.tsx           [NEW] Narrative arcs viewer
    └── circle/page.tsx            [NEW] Social circle gallery
```

### Data Flow

```
Backend Stores               FastAPI Routes              React Query Hooks       Components
─────────────               ──────────────              ─────────────────       ──────────
StateStore.get_current_state → GET /portal/emotional-state → useEmotionalState → MoodOrb
StateStore.get_state_history → GET /portal/emotional-state/history → useEmotionalHistory → Sparkline
EventStore.get_events_for_date → GET /portal/life-events → useLifeEvents → LifeEventTimeline
NikitaThoughtRepo.get_all   → GET /portal/thoughts → useThoughts → ThoughtFeed
NarrativeArcRepo.get_all    → GET /portal/narrative-arcs → useNarrativeArcs → NarrativeArcCard
SocialCircleRepo.get_circle → GET /portal/social-circle → useSocialCircle → FriendCard
```

---

## Implementation Phases

### Phase 1: Backend API Endpoints + Schemas (P1)

**Goal**: Add 6 new portal endpoints with Pydantic response schemas and pytest tests.

**Changes**:
1. Add 6 response schemas to `nikita/api/schemas/portal.py`
2. Add `get_paginated_thoughts()` method to `NikitaThoughtRepository`
3. Add 6 new route handlers to `nikita/api/routes/portal.py`
4. Write pytest tests for all 6 endpoints

**Key Pattern**: StateStore/EventStore use singletons (`get_state_store()`, `get_event_store()`). Thought/Arc/Social repos use injected `AsyncSession`.

**Estimated Effort**: M (2-3 hours)

### Phase 2: Frontend Foundation — Types + API Client + Hooks (P1)

**Goal**: Set up TypeScript interfaces, API client methods, React Query hooks, and stale time constants.

**Changes**:
1. Add 6 TypeScript interfaces to `portal/src/lib/api/types.ts`
2. Add 6 API methods to `portal/src/lib/api/portal.ts`
3. Add stale times to `portal/src/lib/constants.ts`
4. Create 5 React Query hooks in `portal/src/hooks/`

**Estimated Effort**: S (1 hour)

### Phase 3: Mood Orb + Conflict Banner Components (P1)

**Goal**: Build the animated 4D mood orb, mini variant, and conflict banner.

**Changes**:
1. `mood-orb.tsx`: Full-size orb with CSS keyframe animation, gradient interpolation, glow effect
2. `mood-orb-mini.tsx`: 48px compact variant for dashboard hero
3. `conflict-banner.tsx`: GlassCard danger variant with trigger text and time-in-conflict

**Key Technical Details**:
- Use CSS custom properties for animation speed (arousal), color (valence), scale (dominance), glow (intimacy)
- GPU-composited animations: `transform` + `opacity` only
- `prefers-reduced-motion` media query for accessibility

**Estimated Effort**: M (2 hours)

### Phase 4: Life Events Timeline + Calendar (P1)

**Goal**: Build the life events timeline with time-of-day grouping, domain colors, and calendar navigation.

**Changes**:
1. `life-event-card.tsx`: Single event card with domain-colored left border, icon, entity badges
2. `life-event-timeline.tsx`: Full timeline grouped by morning/afternoon/evening/night
3. `/dashboard/nikita/day/page.tsx`: Page with Calendar component and domain filter toggles

**Estimated Effort**: M (2 hours)

### Phase 5: Thoughts Feed + Filtering (P1)

**Goal**: Build the thoughts browser with type-based filtering, pagination, and visual treatments per thought type.

**Changes**:
1. `thought-card.tsx`: Styled card with type icon, color, italic content, expired/used badges
2. `thought-feed.tsx`: Category filter chips + individual type dropdown + "Load more" button
3. `/dashboard/nikita/mind/page.tsx`: Full page with ThoughtFeed component

**Key Technical Details**:
- 15 thought types mapped to icons/colors (defined as static config object)
- Category grouping: Emotional (5), Cognitive (3), Social (2), Psychological (5)
- Infinite scroll via `useInfiniteQuery` or manual "Load more" with offset

**Estimated Effort**: M (2 hours)

### Phase 6: Narrative Arcs + Social Circle (P2)

**Goal**: Build the narrative arc viewer with 5-dot milestone path and the social circle gallery.

**Changes**:
1. `arc-milestone-path.tsx`: 5-dot connected path with glow/filled/outlined stages
2. `narrative-arc-card.tsx`: Arc card with milestone path, progress bar, character badges, emotional impact bars
3. `friend-card.tsx`: Friend card with name, role badge, personality excerpt, expandable detail
4. `/dashboard/nikita/stories/page.tsx`: Arcs page with active/resolved sections
5. `/dashboard/nikita/circle/page.tsx`: Social circle grid page

**Estimated Effort**: M (2 hours)

### Phase 7: Hub Page + Dashboard Integration + Sidebar (P1)

**Goal**: Build the Nikita hub page, integrate mini orb + conflict banner + thought preview into main dashboard, update sidebar navigation.

**Changes**:
1. `/dashboard/nikita/page.tsx`: Hub layout with MoodOrb, today's events, recent thoughts, nav links
2. Modify `/dashboard/page.tsx`: Add MoodOrbMini, ConflictBanner, ThoughtPreview
3. Modify sidebar: Add "Nikita's World" section with sub-items
4. Add skeleton loading states for all new sections

**Estimated Effort**: M (2 hours)

### Phase 8: Polish + Accessibility + Testing (P1)

**Goal**: Ensure responsive design, accessibility, and performance.

**Changes**:
1. Responsive breakpoints for all new components
2. `role="img"` + `aria-label` on mood orb
3. `prefers-reduced-motion` media query
4. Keyboard navigation for timeline events
5. Empty state messages for each data section
6. Playwright E2E tests for new pages

**Estimated Effort**: M (2 hours)

---

## Dependencies

| Phase | Depends On | Reason |
|-------|-----------|--------|
| Phase 2 | Phase 1 | Frontend types mirror backend schemas |
| Phase 3 | Phase 2 | Components use hooks from Phase 2 |
| Phase 4 | Phase 2 | Components use hooks from Phase 2 |
| Phase 5 | Phase 2 | Components use hooks from Phase 2 |
| Phase 6 | Phase 2 | Components use hooks from Phase 2 |
| Phase 7 | Phase 3-6 | Hub page assembles all component groups |
| Phase 8 | Phase 3-7 | Polish requires all components to exist |

Phases 3-6 can be parallelized after Phase 2 completes.

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| StateStore uses internal sessions, not DI | LOW | Use singleton `get_state_store()` / `get_event_store()` factory functions |
| NikitaThoughtRepository lacks offset pagination | LOW | Add `get_paginated()` method with `offset` + `limit` params |
| Mood orb animation janky on low-end | LOW | CSS `transform` + `opacity` only; `will-change: transform`; reduced-motion fallback |
| Empty data for new users | MEDIUM | Graceful empty states with CTAs ("Start talking to Nikita") |
| Large thought payload | LOW | Server-side pagination (limit=20, offset-based) |
| Sidebar crowding with new section | LOW | Use collapsible section with separator |
