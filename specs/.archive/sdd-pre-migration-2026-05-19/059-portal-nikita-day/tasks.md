# Tasks: Spec 059 — Portal: Nikita's Day (Enhanced)

**Generated**: 2026-02-19
**Source**: `specs/059-portal-nikita-day/plan.md`
**Total**: 12 tasks (4 tracks)

---

## Track A: Backend — Psyche Tips Endpoint

### T1.1: Write psyche-tips endpoint tests [TDD-RED]
**File**: `tests/api/routes/test_portal_psyche_tips.py` (NEW)
**AC**: AC-2.1, AC-2.3, AC-2.6, AC-2.7
**Status**: [x]
**Tests**:
- `test_psyche_tips_returns_state` — mock PsycheStateRepository, verify response schema
- `test_psyche_tips_returns_defaults_when_no_state` — no DB record, verify default values
- `test_psyche_tips_requires_auth` — no JWT, verify 401
**Depends**: none

### T1.2: Add PsycheTipsResponse schema [TDD-GREEN]
**File**: `nikita/api/schemas/portal.py`
**AC**: AC-2.2
**Status**: [x]
**Changes**:
- Add `PsycheTipsResponse` Pydantic model with all fields from spec
**Depends**: T1.1

### T1.3: Implement psyche-tips endpoint [TDD-GREEN]
**File**: `nikita/api/routes/portal.py`
**AC**: AC-2.1, AC-2.3, AC-2.6
**Status**: [x]
**Changes**:
- Add `GET /psyche-tips` route using `get_current_user_id` + `get_async_session`
- Query `PsycheStateRepository.get_by_user_id()` → parse JSONB → return response
- Return `PsycheState.default()` values if no record exists
**Depends**: T1.2

### T1.4: Verify backend tests pass [TDD-VERIFY]
**Status**: [x]
**Command**: `pytest tests/api/routes/test_portal_psyche_tips.py -v`
**Depends**: T1.3

---

## Track B: Frontend — Types, Hook, Components

### T2.1: Add PsycheTipsData type
**File**: `portal/src/lib/api/types.ts`
**AC**: AC-2.2
**Status**: [x]
**Changes**:
- Add `PsycheTipsData` interface matching backend response
**Depends**: none

### T2.2: Add getPsycheTips API call
**File**: `portal/src/lib/api/portal.ts`
**AC**: AC-2.1
**Status**: [x]
**Changes**:
- Add `getPsycheTips: () => api.get<PsycheTipsData>("/portal/psyche-tips")`
**Depends**: T2.1

### T2.3: Create usePsycheTips hook
**File**: `portal/src/hooks/use-psyche-tips.ts` (NEW)
**AC**: AC-2.4
**Status**: [x]
**Changes**:
- TanStack Query hook, staleTime: 60s, retry: 2
**Depends**: T2.2

### T2.4: Create WarmthMeter component
**File**: `portal/src/components/dashboard/warmth-meter.tsx` (NEW)
**AC**: AC-3.1, AC-3.2, AC-3.3, AC-3.4, AC-3.5, AC-3.6
**Status**: [x]
**Changes**:
- Vertical gradient gauge (0-100%)
- Color stops: blue → amber → rose
- Labels: Cold/Cool/Neutral/Warm/Hot
- GlassCard wrapper, animated fill
**Depends**: none

### T2.5: Create PsycheTips component
**File**: `portal/src/components/dashboard/psyche-tips.tsx` (NEW)
**AC**: AC-2.4, AC-2.5, AC-2.8
**Status**: [x]
**Changes**:
- GlassCardWithHeader with "Psyche Insights" title
- Attachment style + defense mode + emotional tone badges
- Vulnerability progress bar
- Tips bullet list, topic chips
- Empty state: "Psyche analysis pending..."
**Depends**: T2.3

---

## Track C: Page Integration

### T3.1: Rewrite day page with 2-column layout
**File**: `portal/src/app/dashboard/nikita/day/page.tsx`
**AC**: AC-1.1, AC-1.2, AC-1.3, AC-1.4, AC-1.5, AC-1.6
**Status**: [x]
**Changes**:
- 2-column grid (lg:grid-cols-3 → 2 cols main, 1 col sidebar)
- Main: date nav + LifeEventTimeline + PsycheTips
- Sidebar: MoodOrb + WarmthMeter + SocialCircleGallery
- Loading skeletons for each section
- Error boundaries per section
**Depends**: T2.4, T2.5

### T3.2: Verify portal build
**Status**: [x]
**Command**: `cd portal && npm run build`
**Depends**: T3.1

---

## Track D: Full Verification

### T4.1: Full backend regression
**Status**: [x]
**Command**: `pytest tests/ -x -q`
**Depends**: T1.4, T3.2

---

## Dependency Graph

```
T1.1 ──→ T1.2 ──→ T1.3 ──→ T1.4 ──────────────────┐
                                                      ├──→ T4.1
T2.1 ──→ T2.2 ──→ T2.3 ──→ T2.5 ──┐                │
T2.4 ──────────────────────────────┼──→ T3.1 ──→ T3.2
```

## Summary

| Track | Tasks | New Files | Modified Files |
|-------|-------|-----------|----------------|
| A (Backend) | 4 | 1 test file | portal.py, schemas/portal.py |
| B (Frontend) | 5 | 3 (hook, 2 components) | types.ts, portal.ts |
| C (Integration) | 2 | 0 | day/page.tsx |
| D (Verify) | 1 | 0 | — |
| **Total** | **12** | **4** | **5** |
