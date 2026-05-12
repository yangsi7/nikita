---
title: "Spec 218 Slice 218-4 — chip_multi + phone + voice_or_text slots"
lifecycle: living
---

# Spec 218 Slice 218-4: chip_multi + phone + voice_or_text slots

## 1. Scope

Vertical-slice increment extending the v2 onboarding wizard to cover 4 additional
Phase-1 slots: `primary_hobbies`, `hangouts_personalized`, `voice_or_text`, `phone`.
After this slice `COVERED_IN_SLICE` is 8 slots and the v2 path covers all slots
through `phone` in the REQUIRED_ORDER.

## 2. In-scope

### Backend

| File | Change |
|------|--------|
| `nikita/agents/onboarding/v2/cohort_cities.py` | Add `HOBBY_OPTIONS` (8 hobbies) + `HANGOUT_OPTIONS` (8 venue types) |
| `nikita/agents/onboarding/v2/decorator_agent.py` | Extend `COVERED_IN_SLICE` to 8 slots; add `ChipMultiAsk` + `PhoneAsk` to `output_type`; extend `_SHAPE_BY_TARGET` with 4 new entries; add 4 new branches in `inject_v2_per_turn_context` |
| `nikita/api/routes/portal_onboarding_v2.py` | Extend `_PERSISTABLE_SLOT_NAMES` to 8 slots; add 4 new branches in `_slot_payload` (chip_multi → list[str] 1-5 items, voice_or_text → {"voice"|"text"}, phone → E.164 regex) |

### Frontend

| File | Change |
|------|--------|
| `portal/src/app/onboarding/v2/chip-multi.tsx` | New `ChipMultiShape` component with toggle-chips + min/max_pick enforcement |
| `portal/src/app/onboarding/v2/phone.tsx` | New `PhoneShape` component with E.164 client-side guard |
| `portal/src/app/onboarding/v2/DynamicQuestion.tsx` | Add `chip_multi` + `phone` cases; remove from defensive stub block |

### Tests

| File | Change |
|------|--------|
| `tests/agents/onboarding/v2/test_decorator_agent_slice4.py` | 15 tests: ChipMultiAsk/PhoneAsk validator, max_pick > CHIP_MULTI_MAX_PICK ModelRetry, COVERED_IN_SLICE == 8, HOBBY_OPTIONS + HANGOUT_OPTIONS |
| `tests/api/routes/test_portal_onboarding_v2_slice4.py` | 12 tests: primary_hobbies persist, whitespace-padded items stripped, all-whitespace no-op, empty/over-cap no-op, voice_or_text persist + FR-007 phone invalidation, phone E.164 boundary |
| `portal/src/__tests__/app/onboarding/v2/DynamicQuestion.slice4.test.tsx` | 5 tests: chip_multi render + toggle + deselect, phone render + submit |

## 3. Out-of-scope

- `saturday_morning`, `darkness_level`, `geek_out_on` (slice 218-5)
- Firecrawl city-personalized hangout options (slice 218-6)
- Phase-2 open-bounce turns (slice 218-7)
- v1 bulldoze (slice 218-8)
- Live demo call after phone submit (slice 218-6 wires FR-009)
- react-phone-number-input library integration (slice 218-6)

## 4. Acceptance Criteria

### AC1: COVERED_IN_SLICE == 8
`COVERED_IN_SLICE` equals exactly `{display_name, age, city, occupation, primary_hobbies, hangouts_personalized, voice_or_text, phone}`.
**Evidence:** `test_covered_set_contains_eight_slots` PASS.

### AC2: ChipMultiAsk valid for primary_hobbies and hangouts_personalized targets
Validator returns the envelope unchanged when target matches slot.
**Evidence:** `test_chip_multi_valid_for_primary_hobbies_target` + `test_chip_multi_valid_for_hangouts_personalized_target` PASS.

### AC3: Slot mismatch raises ModelRetry
ChipMultiAsk with slot='hangouts_personalized' emitted when target='primary_hobbies' raises ModelRetry.
**Evidence:** `test_chip_multi_slot_mismatch_raises_model_retry` PASS.

### AC4: SingleSelectAsk valid for voice_or_text target
**Evidence:** `test_single_select_valid_for_voice_or_text_target` PASS.

### AC5: PhoneAsk valid for phone target
**Evidence:** `test_phone_ask_valid_for_phone_target` PASS.

### AC6: HandlerHandoffAsk rejected for all 4 new covered targets
**Evidence:** `test_handoff_rejected_for_covered_target_primary_hobbies` PASS; HandlerHandoffAsk for uncovered saturday_morning still accepted (`test_handoff_accepted_for_uncovered_target_saturday_morning` PASS).

### AC7: primary_hobbies persists list[str]
Submit `["music","sports","travel"]` → `{primary_hobbies: ["music","sports","travel"]}` in JSONB.
**Evidence:** `test_primary_hobbies_submit_persists_list` PASS.

### AC8: chip_multi empty list and over-cap no-op
Empty list [] and list of 6 items both rejected; no persist call.
**Evidence:** `test_primary_hobbies_empty_list_no_ops` + `test_primary_hobbies_more_than_five_items_no_ops` PASS.

### AC9: voice_or_text='voice' persists and does NOT invalidate phone
**Evidence:** `test_voice_or_text_voice_persists_and_does_not_invalidate_phone` PASS.

### AC10: voice_or_text='text' invalidates phone (FR-007 DAG)
Pre-filled phone dropped from JSONB; `invalidated: ["phone"]` in updates.
**Evidence:** `test_voice_or_text_text_invalidates_phone` PASS.

### AC11: voice_or_text invalid value no-ops
**Evidence:** `test_voice_or_text_invalid_value_no_ops` PASS.

### AC12: phone E.164 valid persists; malformed no-ops
`+14155550100` persists; `14155550100` (no +), `+123` (too short) do not.
**Evidence:** `test_phone_valid_e164_persists` + `test_phone_invalid_no_plus_no_ops` + `test_phone_too_short_no_ops` + `test_phone_valid_e164_minimum_length_persists` PASS.

### AC13: HOBBY_OPTIONS + HANGOUT_OPTIONS exported from cohort_cities
Both lists 3-24 items; all labels non-empty.
**Evidence:** `test_hobby_options_*` + `test_hangout_options_*` PASS.

### AC14: ChipMulti FE renders + toggles + submits array
`data-testid="v2-chip-multi-shape"` present; clicked chip toggles; double-click deselects; Next submits string array.
**Evidence:** `DynamicQuestion.slice4.test.tsx` chip_multi tests PASS.

### AC15: Phone FE renders + submits E.164
`data-testid="v2-phone-shape"` present; form submit calls onSubmit with E.164 string.
**Evidence:** `DynamicQuestion.slice4.test.tsx` phone tests PASS.

## 5. Risks

| ID | Risk | Mitigation |
|----|------|------------|
| R1 | `ChipMultiAsk.model_post_init` rejects if LLM emits `max_pick > len(options)` | `inject_v2_per_turn_context` sets `max_pick = len(OPTIONS)` to match exactly |
| R2 | Two targets map to same ChipMultiAsk shape (primary_hobbies + hangouts_personalized) | Validator slot-field assertion disambiguates: `output.slot != target` → ModelRetry |
| R3 | FR-007 DAG: voice_or_text='text' does not invalidate phone if state.py dependency wiring broken | `test_voice_or_text_text_invalidates_phone` guards this path |
| R4 | Phone E.164 regex `+1234567` (7 total digits) boundary — must pass | `test_phone_valid_e164_minimum_length_persists` validates minimum boundary |
| R5 | FE chip deselect on double-click | `test_chip_multi_toggles_chip_off_when_clicked_twice` validates this |

## Shipped in PR

PR-218-4 (branch: `feat/218-4-chip-multi-and-phone`)

Last verified: 2026-05-12
