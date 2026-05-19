# Plan — Subspec 217-2 Backstory Fallback

**Parent**: `subspecs/217-2-backstory-fallback/spec.md`
**Phase**: 5
**Date**: 2026-05-07
**Authoritative**: spike `docs-to-process/20260507-spec217-2-backstory-diagnosis.md`

## Architecture

Two surgical edits aligned with spike findings:

### FR-4a (FE guard, ~80-120 LOC)

`WizardShell.tsx:771-776` currently:
```tsx
case "archetype":
  return archetypeCards
    ? <BackstoryArchetypeCards ... />
    : <p>preparing the three of us…</p>;  // <-- the hang
```

Replace with EITHER:

**Option A** (preferred — screen-advance guard, AC-4a.3):
```tsx
// In the screenIndex reducer; refuse to advance to "archetype" until cards are populated.
if (nextScreen === "archetype" && state.lastResponse?.output?.archetype_cards == null) {
  return state; // hold position; BE will repopulate on next /answer turn
}
```

**Option B** (fallback Alert with retry, AC-4a.1+2):
```tsx
case "archetype": {
  if (archetypeCards) return <BackstoryArchetypeCards ... />;
  return (
    <ArchetypeFallback
      onRetry={() => repostLastAnswer()}
      onTimeoutMs={4000}  // 3-5s budget per AC-4a.1
    />
  );
}
```

`ArchetypeFallback` renders a brand-veil + Skeleton-of-cards for the first 3-5s, then morphs into shadcn/ui `Alert` with retry button. Logs `backstory_fallback_fired` on retry click.

Recommended: implement Option A primary (deterministic; no race) AND Option B as a defense-in-depth tier (`Alert` only fires if Option A guard somehow leaks an `archetype` screen with null cards). Both fit in 80-150 LOC.

### FR-4b (BE 5-LOC defense-in-depth)

`nikita/api/routes/portal_onboarding.py:1367` (call site of `pick_three_archetypes`):
```python
try:
    cards = await asyncio.wait_for(pick_three_archetypes(...), timeout=20.0)
except (asyncio.TimeoutError, Exception) as e:
    logger.warning("backstory_pipeline_timeout", extra={"user_id_hash": hash_user(uid), "stage": "archetype", "elapsed_ms": int((time.time()-t0)*1000)})
    cards = default_archetype_cards(...)
```

This is the existing `except Exception` flow with `wait_for` added in front. ~5 LOC.

## Test Plan (TDD)

| Test | File | Purpose |
|---|---|---|
| `WizardShell.archetype-fallback.test.tsx` (NEW vitest) | `portal/src/app/onboarding/_components/__tests__/` | Render Alert when archetype_cards null; retry click POSTs; success advances |
| `test_portal_onboarding_archetype_timeout.py` (NEW pytest) | `tests/api/routes/` | Mock pick_three_archetypes to sleep 25s; assert wait_for raises; default_archetype_cards returned; warning logged |

## Verification

- Walk B2 (12-step) per `live-testing-protocol.md` from `simon.yang.ch+walkB2@gmail.com`.
- Spike falsifier (AC-W.2): driving 11 turns to `next_slot_kind=backstory_pick` and inspecting `output.archetype_cards`.

## Risks

| Risk | Mitigation |
|---|---|
| Spike's mechanism-1 wrong (BE conditional skip is real culprit) | FR-4b 5-LOC defense-in-depth covers both mechanisms |
| Option A race against `/answer` arriving with cards | Option B Alert tier as safety net |
| FE retry POST creates duplicate turn → idempotency cache miss | Existing `(user_id, turn_id)` cache covers; no NEW endpoint |

## Dependencies

217-1 merged.
