# Audit Report: Spec 046 — Portal Emotional Intelligence Dashboard

**Date**: 2026-02-12
**Auditor**: Claude Opus 4.6
**Result**: CONDITIONAL PASS

---

## Summary

| Category | Score | Issues |
|----------|-------|--------|
| Requirement Coverage | 9/10 | 2 issues |
| Task Quality | 9/10 | 2 issues |
| AC Testability | 9/10 | 3 issues |
| Architecture Consistency | 8/10 | 3 issues |
| Completeness | 9/10 | 2 issues |
| **Overall** | **44/50** | **12 total** |

**Verdict**: CONDITIONAL PASS — 3 issues must be resolved before implementation; 9 are advisory.

---

## Detailed Findings

### 1. Requirement Coverage

**FR → Plan → Tasks Traceability Matrix:**

| FR | Plan Phase | Task(s) | Covered? |
|----|-----------|---------|----------|
| FR-001 (Mood Orb) | Phase 3 | T5.1 | YES |
| FR-002 (Conflict Override) | Phase 3 | T5.1 (AC-T5.1.7), T5.3 | YES |
| FR-003 (Sparkline) | Phase 3 | T4.4 (AC-T4.4.2), T2.2 | YES |
| FR-004 (Life Events) | Phase 4 | T6.1, T6.2 | YES |
| FR-005 (Calendar Nav) | Phase 4 | T6.3 | YES |
| FR-006 (Domain Filtering) | Phase 4 | T6.3 (AC-T6.3.5, T6.3.6) | YES |
| FR-007 (Thought Cards) | Phase 5 | T7.1 | YES |
| FR-008 (Thought Filtering) | Phase 5 | T7.2 | YES |
| FR-009 (Thought Pagination) | Phase 5 | T7.2 (AC-T7.2.4), T7.3 | YES |
| FR-010 (Narrative Arcs) | Phase 6 | T8.1, T8.2, T8.4 | YES |
| FR-011 (Arc Detail) | Phase 6 | T8.2 (AC-T8.2.5, T8.2.6) | YES |
| FR-012 (Friend Grid) | Phase 6 | T8.3, T8.4 | YES |
| FR-013 (Friend Detail) | Phase 6 | T8.3 (AC-T8.3.5, T8.3.6) | YES |
| FR-014 (Mini Mood) | Phase 7 | T5.2, T9.2 | YES |
| FR-015 (Conflict Banner Dashboard) | Phase 7 | T9.2 (AC-T9.2.2) | YES |
| FR-016 (Thought Preview) | Phase 7 | T9.2 (AC-T9.2.3, T9.2.4) | YES |
| FR-017 (Hub Page) | Phase 7 | T9.1 | YES |
| NFR-001 (Performance) | Phase 8 | T10.1 (partial) | PARTIAL |
| NFR-002 (Accessibility) | Phase 8 | T10.2 | YES |
| NFR-003 (Responsive) | Phase 8 | T10.1 | YES |
| NFR-004 (Dark Theme) | — | Implicit in component tasks | YES (implicit) |
| NFR-005 (Data Freshness) | Phase 2 | T4.3, T4.4 | YES |

**Issues:**

1. **RC-1 (LOW)**: FR-003 (Mood History Sparkline) has a backend endpoint (T2.2) and hook (T4.4.2) but **no frontend component task** for the actual sparkline chart rendering. The spec mentions "uses existing Recharts area chart component pattern" but no task explicitly creates a sparkline component or integrates it into the mood orb section. While the task T5.1 handles the mood orb, it has no AC referencing sparkline rendering. **Recommendation**: Add an AC to T5.1 or create a small sub-task for the sparkline visual within the mood orb card.

2. **RC-2 (LOW)**: NFR-001 (Performance) — The spec requires "LCP < 2s on warm cache" and "orb animation at 60fps", but T10.1 does not include explicit ACs for performance benchmarks. T9.1 has AC-T9.1.6 for LCP, but 60fps and CLS testing are not covered by any task AC. **Recommendation**: Add performance ACs to T10.1 (e.g., "orb animation runs at 60fps measured by Chrome DevTools Performance panel") or accept this as a manual verification step.

### 2. Task Quality

**Structure Check (all 35 tasks):**

| Check | Result |
|-------|--------|
| All tasks have Status field | YES (35/35) |
| All tasks have Priority field | YES (35/35) |
| All tasks have Effort field | YES (35/35) |
| All tasks have Files field | YES (35/35) |
| All tasks have 2+ ACs | YES (34/35) — see TQ-2 |
| Tasks sized 30-90 min | YES (33/35) — see TQ-1 |
| No task exceeds 2 hours | YES (35/35) |
| Dependencies reasonable | YES |

**Issues:**

3. **TQ-1 (LOW)**: T4.3 (Add Stale Time Constants) is extremely small — 6 lines added to one file. This is under 5 minutes of work, not 30 minutes. While not harmful, it could be merged into T4.2 (API Client Methods) for efficiency. The same applies to T9.3 (Sidebar) which is straightforward array modification. **Recommendation**: Consider merging T4.3 into T4.2 if the implementor prefers fewer context switches.

4. **TQ-2 (LOW)**: The task phases in tasks.md (Phases 1-10) do not align 1:1 with the plan phases (Phases 1-8). Tasks.md splits plan Phase 1 (Backend) into tasks Phases 1-3 (Schemas, Endpoints, Tests) and plan Phase 2 (Frontend Foundation) into tasks Phase 4. This is acceptable but the implementor should reference the tasks.md phases, not the plan phases. No action needed, just noted for clarity.

### 3. AC Testability

**Sample AC Review (checking for vagueness):**

| AC | Verdict | Issue |
|----|---------|-------|
| AC-T5.1.2: "Arousal maps to animation speed: 0.0 -> 4s cycle, 1.0 -> 0.8s cycle" | GOOD | Concrete values |
| AC-T5.1.3: "Valence maps to color warmth: 0.0 -> cool blue/indigo (#6366f1), 1.0 -> warm rose/coral (#fb7185)" | GOOD | Hex values specified |
| AC-T6.1.1: "Domain-colored left border: work=blue (#3b82f6), social=purple (#a855f7), personal=green (#22c55e)" | GOOD | Concrete |
| AC-T7.1.1: "Each of 15 thought types renders with designated icon and color (from static config map)" | GOOD | References config |
| AC-T8.2.6: "Smooth collapse/expand animation" | WEAK | What defines "smooth"? |
| AC-T8.3.6: "Smooth collapse/expand animation" | WEAK | Same vagueness |
| AC-T9.1.6: "Page loads within 2s (LCP) on warm cache" | GOOD | Measurable |
| AC-T10.2.5: "Color alone does not convey meaning -- icons and text labels always present" | GOOD | Verifiable |

**Issues:**

5. **AT-1 (LOW)**: AC-T8.2.6 and AC-T8.3.6 both say "Smooth collapse/expand animation" without defining "smooth." **Recommendation**: Specify "transition duration 200-300ms using CSS transition" or "no visible jank at 60fps."

6. **AT-2 (LOW)**: AC-T7.2.2 says "Count badge per category showing number of active thoughts" — but the thoughts endpoint returns ALL thoughts (including expired). The "active" count computation is not specified. Should it count only non-expired thoughts? **Recommendation**: Clarify whether "active" means `is_expired === false` or all thoughts.

7. **AT-3 (LOW)**: AC-T9.2.5 says "Hidden when no emotional state data exists (new users)" but the corresponding backend endpoint T2.1 (AC-T2.1.2) returns a **default state** (all 0.5) when no state exists. So the frontend will always receive data. These two ACs contradict each other. **Recommendation**: Either (a) the backend returns null/404 for new users and the frontend hides, or (b) the backend returns defaults and the frontend always shows. Pick one. The current spec FR-001 AC-001.6 implies option (b) — default state renders as neutral purple orb. Remove or clarify AC-T9.2.5.

### 4. Architecture Consistency

**Backend Pattern Check:**

| Pattern | Spec Approach | Existing Pattern | Consistent? |
|---------|--------------|-----------------|-------------|
| DI for repos | Injected AsyncSession for Thought/Arc/Social | Yes — matches `portal.py` line 31-39 | YES |
| Store singletons | `get_state_store()`, `get_event_store()` | Not used in current `portal.py` | NEW but valid |
| Route file | Add to existing `portal.py` | Matches — single file for all portal routes | YES |
| Schema file | Add to existing `schemas/portal.py` | Matches — single file for all portal schemas | YES |
| Auth pattern | `get_current_user_id` dependency | Matches `portal.py` line 11 | YES |

**Frontend Pattern Check:**

| Pattern | Spec Approach | Existing Pattern | Consistent? |
|---------|--------------|-----------------|-------------|
| Hook file naming | `use-emotional-state.ts` | `use-user-stats.ts`, `use-score-history.ts` | YES |
| Hook structure | `useQuery` with `queryKey` + `staleTime` | Matches `use-user-stats.ts` | YES |
| API client | `portalApi.getEmotionalState()` | `portalApi.getStats()` | YES |
| Types file | Add interfaces to `types.ts` | Matches existing | YES |
| Page location | `app/dashboard/nikita/page.tsx` | `app/dashboard/engagement/page.tsx` | YES |
| Components | `components/nikita/mood-orb.tsx` | `components/dashboard/` exists | YES (new namespace is fine) |
| Glass system | `GlassCard` variants | Matches existing | YES |

**Issues:**

8. **AC-1 (MEDIUM — MUST FIX)**: The spec routes reference `app/(player)/dashboard/nikita/page.tsx` but the actual codebase uses `app/dashboard/` directly — there is **no `(player)` route group** in the portal. All existing pages are at `portal/src/app/dashboard/{route}/page.tsx`. The tasks.md correctly uses `portal/src/app/dashboard/nikita/page.tsx` (no route group), so this is a spec-only issue. **Recommendation**: Update spec.md route table (line 515-519) to remove `(player)` references to match actual codebase structure. Tasks.md is correct.

9. **AC-2 (MEDIUM — MUST FIX)**: The plan references `get_state_history(user_id, days=ceil(hours/24), limit=100)` in T2.2 (AC-T2.2.2). The actual `StateStore.get_state_history()` signature is `(user_id, days=7, limit=100)` which takes `days` and a `timedelta` cutoff internally. The plan's approach of converting hours to days via `ceil(hours/24)` means requesting 1 hour returns 1 day of data and then filters. This is semantically correct but the AC should note the post-query filtering step. Additionally, the spec says the endpoint returns `EmotionalStateHistoryResponse` with a `total_count` field — but `get_state_history` returns `list[EmotionalStateModel]` which doesn't include total_count. The endpoint must compute this. **Recommendation**: AC-T2.2.2 should explicitly mention post-query time filtering and `total_count` computation from the filtered result set.

10. **AC-3 (LOW)**: The sidebar in the spec shows "Nikita's World" inserted between "Score History" and "Conversations", but the actual sidebar (`sidebar.tsx` line 21-28) has `playerItems` as: Dashboard, Engagement, Vices, Conversations, Diary, Settings — there is **no "Score History" item**. The spec's sidebar layout doesn't match reality. Task T9.3 (AC-T9.3.1) says "between Engagement and Conversations" which is more accurate. **Recommendation**: The tasks.md version is correct; update spec.md sidebar section to match actual sidebar order.

### 5. Completeness

**Data Flow Chain Analysis (per data domain):**

| Domain | Backend Store | Schema | Endpoint | TS Type | API Method | Hook | Component | Page | Complete? |
|--------|-------------|--------|----------|---------|------------|------|-----------|------|-----------|
| Emotional State | StateStore | T1.1 | T2.1 | T4.1.1 | T4.2.1 | T4.4.1 | T5.1 | T9.1, T9.2 | YES |
| Emotional History | StateStore | T1.1 | T2.2 | T4.1.2 | T4.2.2 | T4.4.2 | *(see CO-1)* | — | PARTIAL |
| Life Events | EventStore | T1.2 | T2.3 | T4.1.3 | T4.2.3 | T4.4.3 | T6.1, T6.2 | T6.3 | YES |
| Thoughts | ThoughtRepo | T1.2 | T2.4 | T4.1.4 | T4.2.4 | T4.4.4 | T7.1, T7.2 | T7.3 | YES |
| Narrative Arcs | ArcRepo | T1.3 | T2.5 | T4.1.5 | T4.2.5 | T4.4.5 | T8.1, T8.2 | T8.4 | YES |
| Social Circle | CircleRepo | T1.3 | T2.6 | T4.1.6 | T4.2.6 | T4.4.6 | T8.3 | T8.4 | YES |

**Issues:**

11. **CO-1 (LOW)**: Emotional History has the full backend chain (schema T1.1, endpoint T2.2, type T4.1.2, API method T4.2.2, hook T4.4.2) but **no frontend component** that consumes the hook. FR-003 is marked "Optional Enhancement" and specifies a sparkline, but no task creates a sparkline component or integrates the hook into any page. The hook exists but is unused. This matches the spec marking FR-003 as optional, but the backend work (T2.2) would be wasted if the sparkline is never built. **Recommendation**: Either (a) add a sparkline sub-task, or (b) mark T2.2 as P2/optional to match FR-003's optional status and defer all history work together.

12. **CO-2 (MEDIUM — MUST FIX)**: The plan mentions adding `get_paginated_thoughts()` to `NikitaThoughtRepository`, and T2.4 (AC-T2.4.1) specifies it. However, the existing repository only has `get_active_thoughts()`. The new method name is `get_paginated()` in the task AC. The backend test task T3.2 (AC-T3.2.7) references testing this new method. This is all consistent. **However**, the task does not specify whether `get_paginated()` includes expired thoughts in results. The spec says expired thoughts should be shown with reduced opacity (FR-007 AC-007.3), which implies the API returns them. AC-T2.4.1 says "returns ALL thoughts (including expired and used)" — this is correct and explicit. No action needed on this point specifically, but the task should also mention the `ORDER BY created_at DESC` requirement explicitly in the method signature — currently it says "ordered by `created_at DESC`" which is good. **Downgraded to advisory**: This chain is complete. No action needed.

---

## Verdict

### CONDITIONAL PASS

**3 conditions that MUST be resolved before implementation:**

1. **AC-1 (Architecture)**: Update spec.md routes table (lines 515-519) to remove `(player)` route group prefix — use `app/dashboard/nikita/` to match actual codebase structure. Tasks.md is already correct.

2. **AC-2 (Architecture)**: Update AC-T2.2.2 to explicitly document (a) post-query time filtering from days to hours, and (b) `total_count` computation from the filtered list. The current AC implies a direct pass-through that won't work.

3. **AT-3 (Testability)**: Resolve contradiction between AC-T2.1.2 (backend returns default state for new users) and AC-T9.2.5 (frontend hidden when no data exists). Choose one behavior and update both ACs accordingly. Recommended: keep backend defaults (AC-T2.1.2) and remove AC-T9.2.5, since FR-001 AC-001.6 expects default rendering.

**9 advisory recommendations (non-blocking):**

- RC-1: Add sparkline component task or AC for FR-003
- RC-2: Add performance benchmark ACs (60fps, CLS)
- TQ-1: Consider merging T4.3 into T4.2
- TQ-2: Note tasks.md phase numbering differs from plan.md
- AT-1: Define "smooth" animation in AC-T8.2.6 and AC-T8.3.6
- AT-2: Define "active" thoughts counting logic for category badges
- AC-3: Update spec.md sidebar layout to match actual sidebar items
- CO-1: Align T2.2 priority with FR-003 optional status
- CO-2: (Resolved — chain is complete)

---

## Version History

| Date | Version | Changes |
|------|---------|---------|
| 2026-02-12 | 1.0 | Initial audit — CONDITIONAL PASS (3 must-fix, 9 advisory) |
