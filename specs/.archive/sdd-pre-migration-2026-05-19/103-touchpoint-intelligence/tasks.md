# Tasks: Spec 103 — Touchpoint Intelligence

## Story 1: Wire Life Events to MessageGenerator

### T1.1: Store life event in trigger_context [S]
- [ ] Edit `engine.py` `evaluate_and_schedule_for_user()`:
  - If `life_events` non-empty, store `life_events[0].description` in trigger_context dict
- **AC**: Life event description stored in touchpoint trigger_context metadata

### T1.2: Pass life event during generation [S]
- [ ] Edit `engine.py` `_generate_message()`:
  - Extract `life_event_description` from `touchpoint.trigger_context` dict
  - Pass as `life_event_description=` to `generator.generate()`
- **AC**: Life event reaches MessageGenerator

### T1.3: Write life event wiring tests [S]
- [ ] `tests/touchpoints/test_life_event_wiring.py`
  - `test_life_event_stored_in_trigger_context`
  - `test_life_event_passed_to_generator`
  - `test_no_life_events_default_behavior`
- **AC**: 3 tests pass

## Story 2: PsycheState Integration

### T2.1: Add psyche_state parameter to StrategicSilence [M]
- [ ] Edit `silence.py` `apply_strategic_silence()`:
  - Add `psyche_state: dict | None = None` parameter
  - In `_compute_emotional_modifier()`: Add `psyche_state` param
  - If `defense_mode == "withdrawing"`: modifier += 0.5
  - If `defense_mode == "guarded"`: modifier += 0.3
  - If `attachment_activation == "avoidant"`: modifier += 0.3
- **AC**: Silence modifier influenced by psyche state

### T2.2: Load PsycheState in TouchpointEngine [M]
- [ ] Edit `engine.py` `_evaluate_silence()`:
  - Import `PsycheStateRepository`
  - Load psyche state record for user
  - Parse JSONB state field
  - Pass `psyche_state={"defense_mode": ..., "attachment_activation": ...}` to silence
  - Wrap in try/except for graceful degradation
- **AC**: PsycheState loaded and passed to silence evaluator

### T2.3: Write psyche silence tests [M]
- [ ] `tests/touchpoints/test_psyche_silence.py`
  - `test_withdrawing_defense_increases_silence`
  - `test_guarded_defense_increases_silence`
  - `test_avoidant_attachment_increases_silence`
  - `test_open_secure_no_change`
  - `test_none_psyche_graceful_degradation`
- **AC**: 5 tests pass

## Story 3: Content Deduplication

### T3.1: Add `get_recent_delivered_content()` to TouchpointStore [S]
- [ ] Edit `nikita/touchpoints/store.py`:
  - Method: `async def get_recent_delivered_content(self, user_id: UUID, limit: int = 5) -> list[str]`
  - Query delivered touchpoints, return message_content list
- **AC**: Returns last 5 delivered message contents

### T3.2: Add dedup check to `_deliver_single()` [M]
- [ ] Edit `engine.py` `_deliver_single()`:
  - After generating message, before Telegram send:
  - Get recent delivered content from store
  - Compare using `difflib.SequenceMatcher`, threshold 0.70
  - If similar: regenerate once; if still similar, skip with "content_dedup"
- **AC**: Similar content triggers regeneration or skip

### T3.3: Write content dedup tests [M]
- [ ] `tests/touchpoints/test_content_dedup.py`
  - `test_identical_content_triggers_dedup`
  - `test_different_content_proceeds`
  - `test_71_percent_similarity_triggers_dedup`
  - `test_69_percent_similarity_no_dedup`
  - `test_empty_recent_content_proceeds`
- **AC**: 5 tests pass

## Story 4: Conversation Thread Injection

### T4.1: Add `open_threads` parameter to MessageGenerator [S]
- [ ] Edit `generator.py` `generate()`:
  - Add `open_threads: list[dict] | None = None` parameter
  - Format as bullet list: "Open topics:\n- [type] content"
  - Inject into context as `{{open_threads}}` template var
- **AC**: Threads appear in generation prompt

### T4.2: Load threads in TouchpointEngine [M]
- [ ] Edit `engine.py` `_generate_message()`:
  - Import ConversationThreadRepository
  - Load open threads (max 3): get_open_threads(user_id, limit=3)
  - Priority: questions first, then promises, follow_ups, topics
  - Format as dicts: `{"type": thread_type, "content": content}`
  - Pass to generator
- **AC**: Top 3 prioritized threads loaded and passed

### T4.3: Write thread injection tests [M]
- [ ] `tests/touchpoints/test_thread_injection.py`
  - `test_threads_injected_into_prompt`
  - `test_priority_ordering`
  - `test_max_3_threads`
  - `test_no_threads_default`
- **AC**: 4 tests pass

## Story 5: Vice Category Hints

### T5.1: Add `vice_hints` parameter to MessageGenerator [S]
- [ ] Edit `generator.py` `generate()`:
  - Add `vice_hints: list[str] | None = None` parameter
  - Format as: "Personality hints: she knows you enjoy [cat1] and [cat2]"
  - Inject into context as `{{vice_hints}}` template var
- **AC**: Vice hints appear in generation prompt

### T5.2: Load vices in TouchpointEngine [M]
- [ ] Edit `engine.py` `_generate_message()`:
  - Import VicePreferenceRepository
  - Load `get_active(user_id)` → filter engagement_score > 0.3 → take top 2
  - Format category names (replace underscores with spaces)
  - Pass to generator
- **AC**: Top 2 vices loaded with threshold filtering

### T5.3: Write vice hints tests [S]
- [ ] `tests/touchpoints/test_vice_hints.py`
  - `test_top_2_vices_injected`
  - `test_threshold_filtering`
  - `test_no_vices_default`
  - `test_vice_hint_formatting`
- **AC**: 4 tests pass

---

## Summary

| Story | Tasks | Size | Tests |
|-------|-------|------|-------|
| S1: Life Events | T1.1-T1.3 | S | 3 |
| S2: Psyche Silence | T2.1-T2.3 | M | 5 |
| S3: Content Dedup | T3.1-T3.3 | M | 5 |
| S4: Thread Injection | T4.1-T4.3 | M | 4 |
| S5: Vice Hints | T5.1-T5.3 | S | 4 |
| **Total** | **15 tasks** | | **21 tests** |
