# Audit Report: Spec 047 -- Portal Deep Insights & History

**Date**: 2026-02-12
**Auditor**: Claude Opus 4.6 (SDD Audit)
**Result**: CONDITIONAL PASS

---

## Summary

| Category | Score | Issues |
|----------|-------|--------|
| Requirement Coverage | 9/10 | 2 minor |
| Task Quality | 8/10 | 3 issues |
| AC Testability | 9/10 | 2 minor |
| Architecture Consistency | 9/10 | 2 minor |
| Completeness | 8/10 | 3 issues |
| **Overall** | **43/50** | **12 total** |

**Verdict**: CONDITIONAL PASS -- 6 items to fix before implementation (all LOW/MEDIUM severity).

---

## Detailed Findings

### 1. Requirement Coverage

**FR-to-Plan Traceability** (17 FRs)

| FR | Plan Phase | Task(s) | Status |
|----|-----------|---------|--------|
| FR-001 | Phase 1 | T1.1, T1.2 | COVERED |
| FR-002 | Phase 3 | T3.3 | COVERED |
| FR-003 | Phase 3 | T3.4 | COVERED |
| FR-004 | Phase 3 | T3.1, T3.2 | COVERED |
| FR-005 | Phase 6 | T4.1 | COVERED |
| FR-006 | Phase 6 | T4.2 | COVERED |
| FR-007 | Phase 6 | T4.3 | COVERED |
| FR-008 | Phase 6 | T4.4 | COVERED |
| FR-009 | Phase 1 | T1.1, T1.3 | COVERED |
| FR-010 | Phase 4 | T5.2, T5.3 | COVERED |
| FR-011 | Phase 4 | T5.4 | COVERED |
| FR-012 | Phase 4 | T5.1 | COVERED |
| FR-013 | Phase 7 | T6.1 | COVERED |
| FR-014 | Phase 7 | T6.2 | COVERED |
| FR-015 | Phase 1 / Phase 5 | T1.4 | COVERED |
| FR-016 | Phase 5 | T6.3 | COVERED |
| FR-017 | Phase 5 | T6.4 | COVERED |

All 17 FRs traced to at least one plan phase and at least one task. No orphaned FRs.

**NFR Coverage**:

| NFR | Task(s) | Status |
|-----|---------|--------|
| NFR-001 (Performance) | T7.3 | COVERED |
| NFR-002 (Accessibility) | T7.1 | COVERED |
| NFR-003 (Responsive) | T7.2 | COVERED |
| NFR-004 (Dark Theme) | Not explicit task | MINOR GAP (F-1) |
| NFR-005 (Type Safety) | T2.1 | COVERED |
| NFR-006 (Data Freshness) | T2.3 | COVERED |

**F-1 (LOW)**: NFR-004 (dark theme consistency) has no explicit task or AC. It is implicitly handled by using existing glass design tokens, but a verification step should be added to T7.1 or T7.2.

**F-2 (LOW)**: Plan Phase 2 mentions "Fix `ConversationDetail` type to include missing backend fields" as item 1, but no dedicated task in tasks.md covers this. T2.1 only mentions adding NEW types, not fixing existing `ConversationDetail`. This fix is a prerequisite for T4.3 (Analysis tab) since the Analysis tab needs `extracted_entities`, `conversation_summary`, `score_delta`, and `emotional_tone` from the response.

**Recommendation for F-2**: Add an AC to T2.1 or create a new task: "Fix `ConversationDetail` TypeScript interface to include `extracted_entities`, `conversation_summary`, `score_delta`, `emotional_tone`, `is_boss_fight` fields (already returned by backend)."

### 2. Task Quality

**Task Count Discrepancy (F-3, LOW)**:
- Header says "Total: 28 tasks" but actual count is 27 (4+3+4+4+4+4+4=27)
- Progress Summary table also says 27. Header should be corrected to 27.

**Missing Repository Task (F-4, MEDIUM)**:
- Plan Phase 1 item 5 says: "Add `get_threads_filtered()` to `ConversationThreadRepository`"
- Plan file change summary lists: `thread_repository.py | ADD get_threads_filtered() | +30`
- Research notes confirm: "A new `get_by_user()` method may be needed for `?status=all`"
- But tasks.md has NO dedicated task for this. T1.3 (Threads endpoint) mentions using the repository but does not have an AC for creating the new repository method.
- **Impact**: Without `get_threads_filtered()`, the `?status=resolved` and `?status=expired` and `?status=all` filters cannot work. `get_open_threads()` is hardcoded to `status == "open"`.
- **Recommendation**: Add an AC to T1.3: "New `get_threads_filtered(user_id, status, thread_type, limit)` method added to `ConversationThreadRepository` supporting all status values" or create T1.5 for it.

**Task Size Assessment**:

| Task | Estimated Effort | Assessment |
|------|-----------------|------------|
| T1.1 (Schemas) | 30 min | OK |
| T1.2 (Score endpoint) | 45 min | OK |
| T1.3 (Threads endpoint) | 60 min | OK (with repo method) |
| T1.4 (Emotional endpoint) | 30 min | OK (conditional) |
| T2.1-T2.3 | 30-45 min each | OK |
| T3.1-T3.4 | 45-90 min each | OK |
| T4.1-T4.4 | 30-60 min each | OK |
| T5.1-T5.4 | 45-90 min each | OK |
| T6.1-T6.4 | 45-90 min each | OK |
| T7.1-T7.4 | 30-60 min each | OK |

No tasks exceed 2 hours. Sizes are appropriate.

**Dependency Chain**: Each phase depends on the previous. Phase 6 (Emotional Trajectory) depends on Spec 046. This is correctly noted.

### 3. AC Testability

**Strengths**:
- Most ACs use concrete values (e.g., "rose-400", "0.7 threshold", ">7 days amber, >14 days red")
- Color mappings are explicit (positive=emerald, neutral=gray, etc.)
- Backend ACs include specific test case descriptions
- Empty states and null handling are covered

**F-5 (LOW)**: T3.3 AC for "Cumulative" view says "running metric totals" but does not specify the accumulation algorithm. If `event_details` has delta values, the cumulative view must sum deltas from oldest to newest. The AC should specify: "Cumulative view shows running sum of deltas from oldest to newest event, or raw metric values if available."

**F-6 (LOW)**: T4.3 AC for "Score Breakdown section" says "matched from detailed score history" but does not specify the matching strategy. The plan's risk section notes "No FK from conversation -> score_history" and suggests "Lookup by user_id + event_type + timestamp proximity." The AC should specify: "Score breakdown matched by user_id + event_type='conversation' + timestamp within 60s of conversation.ended_at, or show 'No score data' if no match."

**Good Testability Examples**:
- T5.1: "Oldest thread: amber highlight if >7 days, red if >14 days" -- concrete thresholds
- T6.2: "Clingy >3 days: amber background + warning icon" -- specific threshold + visual
- T6.3: "Conflict regions: vertical red-tinted ReferenceArea bands when `conflict_state != 'none'`" -- concrete condition

### 4. Architecture Consistency

**Backend Pattern Compliance**:
- Plan references correct DI pattern (`Depends(get_current_user_id)`, `Depends(get_async_session)`)
- Schema pattern follows existing `portal.py` conventions (`BaseModel`, `model_config`)
- All referenced repository methods verified to exist:
  - `ScoreHistoryRepository.get_history_since()` at `score_history_repository.py:161` -- EXISTS
  - `ConversationThreadRepository.get_open_threads()` at `thread_repository.py:65` -- EXISTS
  - `StateStore.get_state_history()` at `store.py:216` -- EXISTS
- All referenced backend files verified to exist on disk

**Frontend Pattern Compliance**:
- New hooks follow existing `useQuery` pattern with `queryKey` + `staleTime`
- New components in `portal/src/components/insights/` -- follows existing directory structure
- Uses shadcn/ui components (Tabs, Table, Badge, Card, Select, etc.) -- all already installed
- Uses Recharts (already installed per Spec 044)
- No custom chart libraries introduced

**F-7 (LOW)**: Plan says `portal/src/components/dashboard/conversation-card.tsx` but the plan research section says `conversation-card.tsx:42-50` already has a score delta badge. Tasks.md T4.1 says to add the badge (FR-005). The plan itself notes "FR-005 is essentially done." This creates a confusing situation where T4.1 may be a no-op. **Recommendation**: T4.1 should note that the badge already exists and specify what enhancement (if any) is needed, or mark FR-005 as pre-implemented and adjust T4.1 scope to verification-only.

**Spec 046 Overlap Handling**:
- Plan correctly identifies the overlap with Spec 046 emotional endpoint
- T1.4 has conditional AC: "Check if Spec 046 already added endpoint -- if so, SKIP this task"
- Emotional trajectory data reuse is properly noted

**F-8 (LOW)**: The plan mentions `emotional-trajectory-chart.tsx` in the file tree but T6.3 references `emotional-trajectory.tsx` (different filename). Tasks.md and plan should align on the filename.

### 5. Completeness (Data Flow Chain)

**Chain 1: Detailed Score History** (FR-001 -> FR-002 -> FR-003)
```
ScoreHistoryRepository.get_history_since() [EXISTS]
  -> Unpack event_details JSONB [T1.2]
  -> DetailedScoreHistoryResponse [T1.1]
  -> GET /portal/score-history/detailed [T1.2]
  -> DetailedScoreHistory TypeScript type [T2.1]
  -> portalApi.getDetailedScoreHistory() [T2.2]
  -> useDetailedScores() hook [T2.3]
  -> MetricDeltaChart [T3.3] + InteractionImpactList [T3.4]
  -> /dashboard/insights page [T3.1]
```
**Status**: COMPLETE chain

**Chain 2: Threads** (FR-009 -> FR-010 -> FR-011 -> FR-012)
```
ConversationThreadRepository [EXISTS, needs get_threads_filtered -- F-4]
  -> ThreadListResponse [T1.1]
  -> GET /portal/threads [T1.3]
  -> ThreadList TypeScript type [T2.1]
  -> portalApi.getThreads() [T2.2]
  -> useThreads() hook [T2.3]
  -> ThreadSummaryCards [T5.1] + ThreadTable [T5.2] + Filters [T5.3] + Expansion [T5.4]
  -> /dashboard/insights?tab=threads [T3.1]
```
**Status**: COMPLETE chain (pending F-4 fix for repository method)

**Chain 3: Emotional Trajectory** (FR-015 -> FR-016 -> FR-017)
```
StateStore.get_state_history() [EXISTS]
  -> EmotionalTrajectoryResponse [T1.1]
  -> GET /portal/emotional-state/history [T1.4, conditional on Spec 046]
  -> EmotionalTrajectory TypeScript type [T2.1]
  -> portalApi.getEmotionalTrajectory() [T2.2]
  -> useEmotionalTrajectory() hook [T2.3]
  -> EmotionalTrajectoryChart [T6.3] + EmotionalDescription [T6.4]
  -> /dashboard/insights?tab=emotional [T3.1]
```
**Status**: COMPLETE chain

**Chain 4: Conversation Enhancements** (FR-005 -> FR-008)
```
Existing getConversations() [EXISTS]
  -> ConversationCard score_delta badge [T4.1, may be pre-implemented]
  -> ConversationCard tone badge [T4.2]
Existing getConversation() [EXISTS]
  -> Fix ConversationDetail type [MISSING TASK -- F-2]
  -> Analysis tab [T4.3] + Linked threads [T4.4]
```
**Status**: INCOMPLETE -- missing ConversationDetail type fix task

**Chain 5: Engagement Enhancements** (FR-013 -> FR-014)
```
Existing getEngagement() [EXISTS]
  -> CalibrationTrendChart [T6.1]
  -> ClingyDistantCounters [T6.2]
  -> /dashboard/engagement page [T6.1, T6.2]
```
**Status**: COMPLETE chain (calibration history fallback noted)

**F-9 (MEDIUM)**: The Interaction Impact List (T3.4, FR-003) states "Conversation events show clickable link to `/dashboard/conversations/{id}`" but the `DetailedScorePoint` schema does not include a `conversation_id` field. The `event_details` JSONB would need to contain a `conversation_id` reference, or the score_history record would need a FK. Neither the schema nor the task addresses how the conversation link is resolved. **Recommendation**: Either add `conversation_id: UUID | None` to `DetailedScorePoint` (extracted from `event_details` JSONB), or document that conversation links are not available and remove that AC.

---

## Issues Summary

| ID | Severity | Category | Description | Fix |
|----|----------|----------|-------------|-----|
| F-1 | LOW | Requirement Coverage | NFR-004 (dark theme) has no explicit task | Add AC to T7.1 or T7.2 for visual consistency check |
| F-2 | MEDIUM | Requirement Coverage | `ConversationDetail` TS type fix missing as task | Add AC to T2.1: fix ConversationDetail to include 5 missing fields |
| F-3 | LOW | Task Quality | Header says 28 tasks, actual count is 27 | Correct header to 27 |
| F-4 | MEDIUM | Task Quality | `get_threads_filtered()` repository method has no task/AC | Add AC to T1.3 for new repository method |
| F-5 | LOW | AC Testability | T3.3 cumulative view accumulation algorithm unspecified | Specify "running sum of deltas from oldest to newest" |
| F-6 | LOW | AC Testability | T4.3 score-to-conversation matching strategy unspecified | Specify matching by user_id + event_type + timestamp proximity |
| F-7 | LOW | Architecture Consistency | T4.1 (FR-005) may be pre-implemented per plan research | Clarify T4.1 scope (verify existing or enhance) |
| F-8 | LOW | Architecture Consistency | Filename mismatch: plan says `emotional-trajectory-chart.tsx`, T6.3 says `emotional-trajectory.tsx` | Align naming |
| F-9 | MEDIUM | Completeness | `DetailedScorePoint` has no `conversation_id` for T3.4 interaction list links | Add `conversation_id: UUID | None` to schema or document limitation |

**Blocking issues (MEDIUM)**: F-2, F-4, F-9 -- must be resolved before implementation.
**Non-blocking issues (LOW)**: F-1, F-3, F-5, F-6, F-7, F-8 -- should be fixed but won't prevent implementation.

---

## Positive Observations

1. **Thorough research notes** in plan.md -- existing code verified with file:line references
2. **Correct identification of Spec 046 overlap** with conditional skip logic in T1.4
3. **Proper identification of ConversationDetail type gap** in plan (even though task is missing)
4. **Risk assessment aligns with implementation reality** (JSONB nulls, calibration history, empty states)
5. **All data flow chains are traceable** end-to-end with only minor gaps
6. **Consistent use of existing patterns** (DI, hooks, shadcn/ui, Recharts)
7. **Task sizes are reasonable** (30-90 min each, none exceed 2 hours)
8. **Good AC specificity** overall -- concrete colors, thresholds, and behaviors

---

## Verdict

**CONDITIONAL PASS**

Fix the 3 MEDIUM issues (F-2, F-4, F-9) before starting implementation:

1. **F-2**: Add AC to T2.1 or new task for fixing `ConversationDetail` TypeScript interface
2. **F-4**: Add AC to T1.3 for creating `get_threads_filtered()` repository method
3. **F-9**: Add `conversation_id` to `DetailedScorePoint` schema or update T3.4 ACs to handle missing links

The 6 LOW issues should be addressed but are not blocking.

Once the 3 MEDIUM fixes are applied, this spec is **READY FOR IMPLEMENTATION**.
