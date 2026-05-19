# Implementation Plan: Spec 047 — Portal Deep Insights & History

**Status**: READY
**Spec**: [spec.md](spec.md) | **Tasks**: [tasks.md](tasks.md)
**Depends On**: Spec 044 (Portal Respec), Spec 042 (Unified Pipeline), Spec 046 (Emotional Intelligence)

---

## Research Notes

### Existing Backend (REUSE — no recreation)

| Repository | Method | File:Line | Notes |
|-----------|--------|-----------|-------|
| `ScoreHistoryRepository` | `get_history_since(user_id, since, limit=1000)` | `score_history_repository.py:161-185` | Returns full `ScoreHistory` ORM including `event_details` JSONB |
| `ConversationThreadRepository` | `get_open_threads(user_id, thread_type, limit)` | `thread_repository.py:65-93` | Supports type filter, limit; returns newest first |
| `ConversationThreadRepository` | `get_threads_for_prompt(user_id, max_per_type)` | `thread_repository.py:95-120` | Grouped by type — useful for summary stats |
| `StateStore` | `get_state_history(user_id, days, limit)` | `emotional_state/store.py:216-249` | Returns `EmotionalStateModel` list (4D + conflict_state) |

**Thread repository** currently has NO method for querying by all statuses (open + resolved + expired). `get_open_threads()` is hardcoded to `status == "open"`. A new `get_by_user()` method may be needed for `?status=all` or we add a `get_threads_filtered()` method.

### Existing Frontend (ENHANCE)

| Component | File | Current State | Enhancement |
|-----------|------|---------------|-------------|
| `ConversationCard` | `conversation-card.tsx` | Shows `score_delta` outline badge + tone color dot (2px circle) | Spec wants tone dot to become labeled badge. Card already has both fields from API. Minor CSS change. |
| `ConversationDetailPage` | `conversations/[id]/page.tsx` | Messages only in `ScrollArea` | Add `Tabs` component: "Messages" (existing) / "Analysis" (new) |
| `EngagementPage` | `engagement/page.tsx` | `EngagementPulse` + `DecayWarning` | Add `CalibrationTrendChart` + `ClingyDistantCounters` below |
| Sidebar | `layout/sidebar.tsx:21-28` | 6 `playerItems` array | Insert `{ title: "Insights", href: "/dashboard/insights", icon: Lightbulb }` |

### Spec 046 Overlap

Spec 046 defines `GET /api/v1/portal/emotional-state/history?hours=24` with `EmotionalStateHistoryResponse`. Spec 047's FR-015 wants `?days=30`. **Resolution**: Spec 047 reuses the Spec 046 endpoint. If it uses `hours`, pass `hours=720` for 30 days. If Spec 046 is not yet implemented at implementation time, add a minimal version with `days` parameter. The Emotional Trajectory tab (FR-016) in the Insights page consumes this data.

### Existing API Pattern

All portal endpoints follow: `portal.py:44-89`
```python
@router.get("/endpoint", response_model=ResponseSchema)
async def get_endpoint(
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
):
    repo = SomeRepository(session)
    data = await repo.get_stuff(user_id)
    return ResponseSchema(...)
```

### Existing Hook Pattern

All hooks follow: `use-score-history.ts`
```typescript
export function useHookName(param = default) {
  return useQuery({
    queryKey: ["portal", "key", param],
    queryFn: () => portalApi.getMethod(param),
    staleTime: STALE_TIMES.history, // 60_000
  })
}
```

### ConversationCard Already Has Badges

`conversation-card.tsx:42-50` already renders `score_delta` as an outline badge and `tone` as a 2px colored dot. The spec wants:
- FR-005: Score delta badge → **already implemented** (green/red/gray outline badge)
- FR-006: Emotional tone badge → currently a tiny dot, needs label text + full badge treatment

So FR-005 is essentially done. FR-006 requires enhancing the tone dot to a labeled badge.

### ConversationDetail Missing Fields

`conversations/[id]/page.tsx` uses `useConversation(id)` which returns `ConversationDetail` type. But the TypeScript `ConversationDetail` interface (`types.ts:89-95`) is **missing** `extracted_entities`, `conversation_summary`, `score_delta`, `emotional_tone`, and `is_boss_fight`. The backend DOES return these fields (`ConversationDetailResponse` in `portal.py:132-144`). **Fix needed**: Update TypeScript `ConversationDetail` to include these fields.

---

## Architecture

### Backend Addition (2 new endpoints)

```
nikita/api/
├── schemas/portal.py     # ADD: DetailedScorePoint, DetailedScoreHistoryResponse,
│                          #      ThreadResponse, ThreadListResponse
└── routes/portal.py       # ADD: get_detailed_score_history(), get_threads()
```

### Frontend Addition

```
portal/src/
├── lib/api/
│   ├── types.ts                    # ADD: DetailedScorePoint, DetailedScoreHistory,
│   │                               #      Thread, ThreadList + FIX ConversationDetail
│   └── portal.ts                   # ADD: getDetailedScoreHistory(), getThreads()
├── hooks/
│   ├── use-detailed-scores.ts      # NEW
│   └── use-threads.ts              # NEW
├── app/dashboard/
│   ├── insights/page.tsx           # NEW: Tabbed insights hub
│   ├── conversations/[id]/page.tsx # MODIFY: Add Analysis tab
│   └── engagement/page.tsx         # MODIFY: Add calibration + counters
├── components/
│   ├── insights/
│   │   ├── metric-delta-chart.tsx       # NEW: 4-metric Recharts AreaChart
│   │   ├── interaction-impact-list.tsx  # NEW: Score event list with delta pills
│   │   ├── thread-table.tsx             # NEW: DataTable with expandable rows
│   │   ├── thread-summary-cards.tsx     # NEW: Open/type/oldest stats
│   │   └── emotional-trajectory-chart.tsx # NEW or REUSE from Spec 046
│   └── dashboard/
│       ├── conversation-card.tsx        # MODIFY: Enhance tone badge
│       ├── conversation-analysis.tsx    # NEW: Analysis tab content
│       ├── calibration-trend.tsx        # NEW: Calibration line chart
│       └── clingy-distant-counters.tsx  # NEW: Clingy/distant indicators
└── components/layout/
    └── sidebar.tsx                      # MODIFY: Add "Insights" nav item
```

### Data Flow

```
Score History Detailed:
  ScoreHistoryRepository.get_history_since()
    → unpack event_details JSONB per record
    → DetailedScoreHistoryResponse
    → portalApi.getDetailedScoreHistory()
    → useDetailedScores()
    → MetricDeltaChart + InteractionImpactList

Threads:
  ConversationThreadRepository (get_open_threads or new filtered method)
    → ThreadListResponse
    → portalApi.getThreads()
    → useThreads()
    → ThreadTable + ThreadSummaryCards

Emotional Trajectory (FROM SPEC 046):
  Spec 046 endpoint → portalApi (reuse 046 method)
    → useEmotionalTrajectory()
    → EmotionalTrajectoryChart + EmotionalDescription

Conversation Enhancement:
  Existing getConversations() → ConversationCard (enhance tone badge)
  Existing getConversation() → Tabs: Messages | Analysis

Engagement Enhancement:
  Existing getEngagement() → CalibrationTrendChart + ClingyDistantCounters
```

---

## Implementation Phases

### Phase 1: Backend API (2 endpoints + schemas) [T1.1-T1.5]
**Effort**: 2-3 hours | **Priority**: P2

1. Add `DetailedScorePoint` + `DetailedScoreHistoryResponse` Pydantic schemas
2. Add `ThreadResponse` + `ThreadListResponse` Pydantic schemas
3. Add `GET /portal/score-history/detailed?days=30` endpoint
4. Add `GET /portal/threads?status=open&type=all&limit=50` endpoint
5. Add `get_threads_filtered()` to `ConversationThreadRepository` (supports all statuses)
6. Backend unit tests for both endpoints

### Phase 2: Frontend Types + API + Hooks [T2.1-T2.4]
**Effort**: 1-2 hours | **Priority**: P2

1. Fix `ConversationDetail` type to include missing backend fields
2. Add new TypeScript interfaces: `DetailedScorePoint`, `DetailedScoreHistory`, `Thread`, `ThreadList`
3. Add `portalApi.getDetailedScoreHistory()` and `portalApi.getThreads()`
4. Create `useDetailedScores` + `useThreads` hooks with staleTime config

### Phase 3: Insights Page + Sidebar Nav [T3.1-T3.5]
**Effort**: 4-6 hours | **Priority**: P2

1. Add "Insights" to sidebar navigation (`sidebar.tsx`)
2. Create `/dashboard/insights/page.tsx` with tab navigation (URL query param state)
3. Score Breakdown tab: `MetricDeltaChart` (Recharts AreaChart, 4 metrics, cumulative/delta toggle)
4. Score Breakdown tab: `InteractionImpactList` (scrollable event list, delta pills, conv links)
5. Loading skeletons + empty states for Score Breakdown tab

### Phase 4: Open Threads Tab [T4.1-T4.4]
**Effort**: 3-4 hours | **Priority**: P3

1. `ThreadSummaryCards`: total open count, by-type breakdown, oldest thread with age
2. `ThreadTable`: sortable data table with type icons, status badges, expand on click
3. Type + status filter dropdowns
4. Empty state for zero threads

### Phase 5: Emotional Trajectory Tab [T5.1-T5.3]
**Effort**: 2-3 hours | **Priority**: P2 | **Depends**: Spec 046

1. `EmotionalTrajectoryChart`: 4-line area chart with conflict bands, 7d/30d toggle
2. `EmotionalDescription`: human-readable latest state card
3. Fallback empty state if Spec 046 endpoint not yet available

### Phase 6: Enhanced Conversations [T6.1-T6.4]
**Effort**: 3-4 hours | **Priority**: P2

1. Enhance `ConversationCard` tone dot → labeled badge (FR-006)
2. Add Tabs to conversation detail page (Messages | Analysis)
3. Create `ConversationAnalysis` component (extracted entities, score breakdown, linked threads)
4. Wire Analysis tab data from existing `ConversationDetail` response

### Phase 7: Enhanced Engagement [T7.1-T7.2]
**Effort**: 2-3 hours | **Priority**: P3

1. `ClingyDistantCounters` with warning colors at >3 days
2. Calibration score display (gauge/indicator — note: history may not be stored, so show current value)

### Phase 8: Polish + Testing [T8.1-T8.4]
**Effort**: 2-3 hours | **Priority**: P2

1. Responsive testing (mobile stacks, table horizontal scroll)
2. Accessibility (aria-labels, keyboard nav, contrast)
3. Playwright E2E tests for insights page
4. Dark theme consistency check

---

## Dependencies

| Dependency | Required By | Status |
|-----------|-------------|--------|
| Spec 044 (Portal Respec) | All frontend | COMPLETE |
| Spec 042 (Unified Pipeline) | event_details JSONB population | COMPLETE |
| Spec 046 (Emotional Intelligence) | Phase 5 (Emotional Trajectory tab) | IN PROGRESS |
| `ScoreHistoryRepository` | Phase 1 | EXISTS (`score_history_repository.py:161`) |
| `ConversationThreadRepository` | Phase 1 | EXISTS (`thread_repository.py:65`) |
| Recharts | Phases 3, 5, 7 | INSTALLED |
| shadcn/ui (tabs, table, badge, card) | Phases 3-7 | INSTALLED |

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| `event_details` JSONB null for old records | MEDIUM | Default metric deltas to `null`; UI shows "N/A" |
| Spec 046 emotional endpoint not ready | LOW | Emotional Trajectory tab shows "Coming soon" empty state |
| No FK from conversation → score_history | MEDIUM | Lookup by user_id + event_type + timestamp proximity |
| Calibration history not stored over time | MEDIUM | Show current calibration_score only (gauge, not trend) |
| Thread table empty for new users | LOW | Empty state with explanation text |
| `ConversationDetail` TS type missing fields | LOW | Fix in Phase 2 (already returned by backend) |

---

## File Change Summary

| File | Change | Lines Est. |
|------|--------|-----------|
| `nikita/api/schemas/portal.py` | ADD 4 schemas | +45 |
| `nikita/api/routes/portal.py` | ADD 2 endpoints | +65 |
| `nikita/db/repositories/thread_repository.py` | ADD get_threads_filtered() | +30 |
| `portal/src/lib/api/types.ts` | ADD 4 types + FIX ConversationDetail | +40 |
| `portal/src/lib/api/portal.ts` | ADD 2 methods | +10 |
| `portal/src/hooks/use-detailed-scores.ts` | NEW | +12 |
| `portal/src/hooks/use-threads.ts` | NEW | +15 |
| `portal/src/app/dashboard/insights/page.tsx` | NEW | +80 |
| `portal/src/components/insights/metric-delta-chart.tsx` | NEW | +120 |
| `portal/src/components/insights/interaction-impact-list.tsx` | NEW | +80 |
| `portal/src/components/insights/thread-table.tsx` | NEW | +150 |
| `portal/src/components/insights/thread-summary-cards.tsx` | NEW | +60 |
| `portal/src/components/insights/emotional-trajectory-chart.tsx` | NEW | +130 |
| `portal/src/components/dashboard/conversation-card.tsx` | MODIFY | +10 |
| `portal/src/components/dashboard/conversation-analysis.tsx` | NEW | +100 |
| `portal/src/components/dashboard/calibration-trend.tsx` | NEW | +60 |
| `portal/src/components/dashboard/clingy-distant-counters.tsx` | NEW | +50 |
| `portal/src/app/dashboard/conversations/[id]/page.tsx` | MODIFY | +35 |
| `portal/src/app/dashboard/engagement/page.tsx` | MODIFY | +15 |
| `portal/src/components/layout/sidebar.tsx` | MODIFY | +2 |
| Backend tests | NEW | +150 |
| E2E tests | NEW | +50 |
| **TOTAL** | | **~1,310** |
