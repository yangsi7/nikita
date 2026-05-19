# Plan: Spec 059 — Portal: Nikita's Day (Enhanced)

**Generated**: 2026-02-19
**Source**: `specs/059-portal-nikita-day/spec.md`
**Complexity**: 1 (Solo SDD)

---

## Implementation Order

### Track A: Backend (psyche-tips endpoint)

1. **T1.1** [TDD-RED]: Write tests for `GET /portal/psyche-tips` endpoint
2. **T1.2** [TDD-GREEN]: Add `PsycheTipsResponse` schema to `nikita/api/schemas/portal.py`
3. **T1.3** [TDD-GREEN]: Implement endpoint in `nikita/api/routes/portal.py`
4. **T1.4** [TDD-VERIFY]: Run backend tests

### Track B: Frontend — New Components

5. **T2.1**: Add `PsycheTipsData` type to `portal/src/lib/api/types.ts`
6. **T2.2**: Add `getPsycheTips()` to `portal/src/lib/api/portal.ts`
7. **T2.3**: Create `usePsycheTips` hook
8. **T2.4**: Create `WarmthMeter` component
9. **T2.5**: Create `PsycheTips` component

### Track C: Page Integration

10. **T3.1**: Rewrite `day/page.tsx` with 2-column layout and all sections
11. **T3.2**: Verify portal build passes

### Track D: Verify

12. **T4.1**: Full backend test suite regression

---

## Dependency Graph

```
T1.1 → T1.2 → T1.3 → T1.4 ──────┐
                                   ├─→ T4.1
T2.1 → T2.2 → T2.3 ────────┐     │
T2.4 ────────────────────────┤     │
T2.5 (needs T2.3) ──────────┼─→ T3.1 → T3.2
                             │
```

**Parallel tracks**: A (backend) and B (frontend types/components) are independent until T3.1 integration.
