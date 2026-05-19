---
title: Slice 218-3 — age + city + occupation slots + slice-218-2 persist fix
parent: ../../tasks.md
plan_brief: ~/.claude/plans/immutable-wondering-gray.md
loc_estimate: ~600 (overage absorbs slice-218-2 persist gap fix)
walkable: v2 user advances display_name → age → city → occupation; slots 5-11 emit HandlerHandoffAsk
lifecycle: living
---

# Slice 218-3 — Age + City + Occupation Slots

Per plan §Slice sequencing PR-218-3 row + §3 of `docs-to-process/20260512-handover-spec-218-PR2-shipped.md`.

## Scope (in)

### Slice-218-2 follow-up (persist gap fix)

Slice-218-2 shipped `handle_v2_answer` without applying req.value to slots
or persisting back to `user.onboarding_profile`. Display_name accept-criterion
in subspecs/2/slice.md line 130 was unmet — agent emits TextShortAsk forever
because slots stay empty. This slice closes the gap because all 4 slots
need the same persist mechanism.

- `nikita/api/routes/portal_onboarding_v2.py`: add `_apply_prior_submission(req, slots, profile)` helper that:
  - Extracts `req.slot_kind` + `req.value` (when present).
  - Maps v1 SlotKind → SlotKindV2 string for {display_name, age, city, occupation}.
  - Wraps raw value into slot-specific payload via `_slot_payload(slot_name, raw_value)`.
  - Returns `(new_slots, new_profile_dict | None)`.
- `nikita/api/routes/portal_onboarding_v2.py`: in `handle_v2_answer`, after hydrating slots, call apply helper; persist via `UserRepository.update_onboarding_profile` when delta non-empty; then `pick_next_target(new_slots)`.

### 3 new slot shapes via decorator extension

- `nikita/agents/onboarding/v2/decorator_agent.py` — extend output_type union:
  ```python
  output_type=[
      ToolOutput(TextShortAsk, name="ask_text_short"),
      ToolOutput(CalendarAsk, name="ask_calendar"),
      ToolOutput(SingleSelectAsk, name="ask_single_select"),
      ToolOutput(HandlerHandoffAsk, name="handoff_to_v1"),
  ]
  ```
- `nikita/agents/onboarding/v2/decorator_agent.py` — extend `inject_v2_per_turn_context`:
  - `covered_in_slice = {display_name, age, city, occupation}`.
  - Per-target prompt string (age → CalendarAsk for DoB; city → SingleSelectAsk from `_CITY_OPTIONS`; occupation → TextShortAsk; display_name unchanged).
- `nikita/agents/onboarding/v2/decorator_agent.py` — extend `build_decorator_output_validator`:
  - target=display_name OR occupation → TextShortAsk valid; raise ModelRetry otherwise.
  - target=age → CalendarAsk valid.
  - target=city → SingleSelectAsk valid.
  - target ∉ covered_in_slice → HandlerHandoffAsk valid.
- `nikita/agents/onboarding/v2/cohort_cities.py` (new) — static `CITY_OPTIONS: list[Option]` (Berlin, NYC, SF, LA, London, Paris, Amsterdam, Tokyo). Firecrawl-driven extension deferred to slice 218-6.

### FE dispatcher extension

- `portal/src/app/onboarding/v2/calendar.tsx` (new) — wraps shadcn `Calendar` + `Popover`. Returns ISO date string.
- `portal/src/app/onboarding/v2/single-select.tsx` (new) — wraps shadcn `RadioGroup` + `Button`. Returns Option.value string.
- `portal/src/app/onboarding/v2/DynamicQuestion.tsx` (modified) — replace `case "single_select"` and `case "calendar"` defensive stubs with the new components.
- `portal/src/app/onboarding/v2/types/envelope.ts` — add `CalendarAsk` + `SingleSelectAsk` TS variants if not already present.

### Tests (slot-specific per R13; NOT full triplet re-run)

- `tests/api/routes/test_portal_onboarding_v2_slice3.py` (new):
  - `test_apply_request_persists_display_name_then_advances_to_age` — confirms slice-218-2 persist gap fix.
  - `test_apply_request_persists_age_dob_to_int` — DoB ISO → age int derivation.
  - `test_apply_request_persists_city_then_advances_to_occupation`.
  - `test_apply_request_persists_occupation_then_advances_to_primary_hobbies` — primary_hobbies emits HandlerHandoffAsk.
  - `test_apply_request_ignores_unknown_slot_kind`.
  - `test_apply_request_ignores_malformed_dob`.
- `tests/agents/onboarding/v2/test_decorator_agent_slice3.py` (new):
  - Output validator accepts CalendarAsk for age target.
  - Output validator accepts SingleSelectAsk for city target.
  - Output validator accepts TextShortAsk for occupation target.
  - Output validator rejects TextShortAsk for age target (raises ModelRetry).
  - Output validator rejects HandlerHandoffAsk for covered target (age).
- `portal/src/__tests__/app/onboarding/v2/DynamicQuestion.slice3.test.tsx` (new):
  - Dispatches CalendarShape for component=calendar.
  - Dispatches SingleSelectShape for component=single_select.
  - Submits ISO date from calendar.
  - Submits selected option from single_select.

## Scope (out — deferred)

| Item | Slice |
|---|---|
| primary_hobbies (chip_multi) + hangouts_personalized | 218-4 |
| voice_or_text + phone | 218-4 |
| saturday_morning + darkness_level + geek_out_on | 218-5 |
| Phase-2 research_agent | 218-6 |
| Firecrawl city extraction | 218-6 |
| Atomic v1 bulldoze | 218-8 |
| ROADMAP.md sync | 218-8 |

## Acceptance criteria (slice-level)

- [ ] Slice-218-2 latent persist gap closed: display_name submit persists to JSONB and advances target to age.
- [ ] Age via CalendarAsk: ISO DoB submit persists `{age: int, dob: "YYYY-MM-DD"}`.
- [ ] City via SingleSelectAsk: selected option value persists `{city: "Berlin"}`.
- [ ] Occupation via TextShortAsk: text submit persists `{occupation: "engineer"}`.
- [ ] After 4 slots filled, `pick_next_target` returns `primary_hobbies`; decorator emits HandlerHandoffAsk.
- [ ] Output validator rejects mismatched shape per target (raises ModelRetry per Hard Rule §5).
- [ ] FE renders Calendar + RadioGroup primitives via shadcn (no hand-rolled).
- [ ] Pre-push full suite green (R6).
- [ ] `/qa-review` fresh-context 0 findings (R7).
- [ ] Post-merge curl-only smoke (R8 tier for 218-3).

## References

- Plan brief: `~/.claude/plans/immutable-wondering-gray.md`
- Slice 218-2 (prior): `specs/218-onboarding-wizard-v2-agent-driven/subspecs/2/slice.md`
- Handover: `docs-to-process/20260512-handover-spec-218-PR2-shipped.md`
- Pattern source: `nikita/agents/onboarding/v2/decorator_agent.py` (extend in place)
