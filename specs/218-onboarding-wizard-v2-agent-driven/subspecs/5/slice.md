---
title: Spec 218 Slice 218-5 — SliderAsk + TextLongAsk rollout
lifecycle: frozen
---

# Slice 218-5: Slider + TextLong slots (full Phase-1 coverage)

## Scope

Adds 3 new slots to the v2 decorator coverage, completing Phase-1:

| Slot | Shape | Persist as |
|------|-------|-----------|
| `saturday_morning` | `SliderAsk` (0-10) | `int` |
| `darkness_level` | `SliderAsk` (0-10) | `int` |
| `geek_out_on` | `TextLongAsk` | `str` stripped, max 1000 chars |

After this slice `COVERED_IN_SLICE == 11` (full Phase-1).

## Backend changes

### `nikita/agents/onboarding/v2/decorator_agent.py`
- Imports: `SliderAsk`, `TextLongAsk` from `envelope`
- `COVERED_IN_SLICE` extended to 11 slots
- `_SHAPE_BY_TARGET` extended: `saturday_morning` → `SliderAsk`, `darkness_level` → `SliderAsk`, `geek_out_on` → `TextLongAsk`
- `inject_v2_per_turn_context`: 3 new target branches
- `_create_decorator_agent.output_type`: `ToolOutput(SliderAsk, name="ask_slider")` + `ToolOutput(TextLongAsk, name="ask_text_long")`

### `nikita/api/routes/portal_onboarding_v2.py`
- `_PERSISTABLE_SLOT_NAMES` extended to 11 slots
- `_slot_payload`:
  - `saturday_morning` / `darkness_level`: `isinstance(int) and not bool and 0 <= v <= 10`
  - `geek_out_on`: `str.strip()` non-empty and `len ≤ 1000`

## Frontend changes

### `portal/src/app/onboarding/v2/slider.tsx` (new)
- `SliderShape` component: Radix `Slider` from `@/components/ui/slider`, sparse label map rendered below track, default value = `min_val`, submit calls `onSubmit(currentValue: number)`.

### `portal/src/app/onboarding/v2/text-long.tsx` (new)
- `TextLongShape` component: `<textarea>` with `maxLength=envelope.max_chars ?? 500`, submit blocked when trimmed empty, calls `onSubmit(trimmed)`.

### `portal/src/app/onboarding/v2/DynamicQuestion.tsx`
- Imports `SliderShape`, `TextLongShape`
- `case "slider"`: renders `<SliderShape>`
- `case "text_long"`: renders `<TextLongShape>`
- `case "complete"`: still defensive stub (slice 218-8)

## DAG (FR-007)

No new edges. `saturday_morning`, `darkness_level`, `geek_out_on` have no dependent slots. `invalidate_dependents` returns `[]` for all three.

## Test coverage

### Python
- `tests/agents/onboarding/v2/test_decorator_agent_slice5.py`: 15 tests
- `tests/api/routes/test_portal_onboarding_v2_slice5.py`: 25 tests (incl. 3 handle_v2_answer persist + 3 bool-reject)
- `tests/agents/onboarding/v2/test_decorator_agent_slice3.py`: retargeted "uncovered" test
- `tests/agents/onboarding/v2/test_decorator_agent_slice4.py`: retargeted "uncovered" test + subset assertion

### TypeScript
- `portal/src/__tests__/app/onboarding/v2/DynamicQuestion.slice5.test.tsx`: 9 tests

## Next slice

Slice 218-6 (Phase-2 research agent) or slice 218-8 (bulldoze v1) — see ROADMAP.md.
