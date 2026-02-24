# Plan: Spec 103 — Touchpoint Intelligence

## Implementation Order

Stories ordered by independence: life events wiring first (most impactful), then psyche integration, then content dedup, then thread injection, then vice hints.

## Story 1: Wire Life Events to MessageGenerator (FR-001)

### T1.1: Store life event in trigger_context
- Edit `nikita/touchpoints/engine.py` `evaluate_and_schedule_for_user()`:
  - If `life_events` is not empty, extract first event description
  - Store in `trigger_context.metadata["life_event_description"]` (or add field to TriggerContext)

### T1.2: Pass life event during generation
- Edit `nikita/touchpoints/engine.py` `_generate_message()`:
  - Extract `life_event_description` from `touchpoint.trigger_context`
  - Pass to `generator.generate(life_event_description=...)`

### T1.3: Write tests
- `tests/touchpoints/test_life_event_wiring.py`:
  - Test life event stored in trigger_context
  - Test life event passed to generator
  - Test None life events → no change

## Story 2: PsycheState Integration (FR-002)

### T2.1: Add psyche_state parameter to StrategicSilence
- Edit `nikita/touchpoints/silence.py` `apply_strategic_silence()`:
  - Add `psyche_state: dict | None = None` parameter
  - In modifier computation: check defense_mode and attachment_activation
  - `"withdrawing"` → +0.5, `"guarded"` → +0.3, avoidant → +0.3

### T2.2: Load PsycheState in TouchpointEngine
- Edit `nikita/touchpoints/engine.py` `_evaluate_silence()`:
  - Import PsycheStateRepository
  - Load psyche state for user, convert to dict
  - Pass `psyche_state=...` to `self.silence.apply_strategic_silence()`
  - Wrap in try/except for graceful degradation

### T2.3: Write tests
- `tests/touchpoints/test_psyche_silence.py`:
  - Test withdrawing defense → increased silence modifier
  - Test guarded defense → increased silence modifier
  - Test avoidant attachment → increased silence modifier
  - Test open/secure → no change
  - Test None psyche state → no change (graceful)

## Story 3: Content Deduplication (FR-003)

### T3.1: Add `get_recent_delivered_content()` to TouchpointStore
- Edit `nikita/touchpoints/store.py`:
  - Method: `async def get_recent_delivered_content(user_id, limit=5) -> list[str]`
  - Query: delivered touchpoints ordered by delivered_at DESC, return message_content

### T3.2: Add dedup check to `_deliver_single()`
- Edit `nikita/touchpoints/engine.py` `_deliver_single()`:
  - After generating message, before delivery:
    - Get recent delivered content
    - Check similarity (SequenceMatcher) against each
    - If >70% similar: regenerate once, or skip with "content_dedup"

### T3.3: Write tests
- `tests/touchpoints/test_content_dedup.py`:
  - Test identical recent content → skip/regenerate
  - Test different content → proceed
  - Test 71% similarity → triggers dedup
  - Test 69% similarity → no dedup
  - Test empty recent content → proceed

## Story 4: Conversation Thread Injection (FR-004)

### T4.1: Add `open_threads` parameter to MessageGenerator
- Edit `nikita/touchpoints/generator.py` `generate()`:
  - Add `open_threads: list[dict] | None = None` parameter
  - Format threads as bullet list in context
  - Inject into template as `{{open_threads}}`

### T4.2: Load threads in TouchpointEngine
- Edit `nikita/touchpoints/engine.py` `_generate_message()`:
  - Import ConversationThreadRepository
  - Load open threads (max 3, prioritized)
  - Format and pass to generator

### T4.3: Write tests
- `tests/touchpoints/test_thread_injection.py`:
  - Test threads injected into prompt
  - Test priority ordering (questions > promises > follow_ups)
  - Test max 3 threads
  - Test no threads → no change

## Story 5: Vice Category Hints (FR-005)

### T5.1: Add `vice_hints` parameter to MessageGenerator
- Edit `nikita/touchpoints/generator.py` `generate()`:
  - Add `vice_hints: list[str] | None = None` parameter
  - Format as: "Personality hints: she knows you enjoy [cat1] and [cat2]"
  - Inject into template as `{{vice_hints}}`

### T5.2: Load vices in TouchpointEngine
- Edit `nikita/touchpoints/engine.py` `_generate_message()`:
  - Import VicePreferenceRepository
  - Load top 2 vices with engagement_score > 0.3
  - Format category names and pass to generator

### T5.3: Write tests
- `tests/touchpoints/test_vice_hints.py`:
  - Test top 2 vices injected
  - Test threshold filtering (only > 0.3)
  - Test no vices → no change
  - Test formatting of vice hint string
