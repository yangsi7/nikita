# Audit Report: Spec 103 — Touchpoint Intelligence
**Date**: 2026-02-25
**Status**: PASS (with findings)
**Auditor**: Claude Code (retroactive)

## Summary

Retroactive audit of Spec 103 covering 5 functional requirements: life events wiring (FR-001), PsycheState silence integration (FR-002), content deduplication (FR-003), conversation thread injection (FR-004), and vice category hints (FR-005). Core functionality is implemented with tests passing. Three architectural gaps identified where parameters are accepted but not fully utilized downstream.

## Acceptance Criteria Verification

| AC | Description | Status | Evidence |
|----|-------------|--------|----------|
| AC-1.1 | Life event stored in trigger_context metadata | PASS (PARTIAL) | `nikita/touchpoints/engine.py:354-356` — `_generate_message()` reads `life_event_description` from `touchpoint.trigger_context` via `getattr()`. However, `evaluate_and_schedule_for_user()` (line 522) does NOT store life events into trigger_context during scheduling. The extraction happens at generation time from the trigger_context attribute, but the storage path is missing. |
| AC-1.2 | Life event passed to `generator.generate()` | PASS | `nikita/touchpoints/engine.py:365` — `life_event_description=life_event_description` passed to generator. Test: `tests/touchpoints/test_intelligence.py::TestLifeEventsWiring::test_generate_message_passes_life_events` |
| AC-1.3 | No life events = None passed | PASS | `nikita/touchpoints/engine.py:354-356` — `getattr(..., None)` returns None when no attribute. Test: `tests/touchpoints/test_intelligence.py::TestLifeEventsWiring::test_generate_message_handles_no_life_event` |
| AC-2.1 | `_evaluate_silence()` loads PsycheState | FAIL | `nikita/touchpoints/engine.py:233-254` — `_evaluate_silence()` does NOT import `PsycheStateRepository` or load PsycheState. It only loads emotional state and conflict state. No `psyche_state` parameter is passed to `apply_strategic_silence()`. |
| AC-2.2 | `apply_strategic_silence()` accepts `psyche_state` | FAIL | `nikita/touchpoints/silence.py:79-84` — `apply_strategic_silence()` signature does NOT include a `psyche_state` parameter. The `psyche_state` parameter exists only on the internal `_compute_emotional_modifier()` method (line 172), but the public API never passes it through. |
| AC-2.3 | `defense_mode == "withdrawing"` adds modifier | PASS (PARTIAL) | `nikita/touchpoints/silence.py:159` — `DEFENSE_MODE_MODIFIERS["withdrawing"] = 0.6` (spec says +0.5, implementation uses +0.6). The modifier is applied in `_compute_emotional_modifier()` (line 219). Test: `tests/touchpoints/test_intelligence.py::TestPsycheStateSilence::test_defense_mode_withdrawing_increases_silence_more` |
| AC-2.4 | `defense_mode == "guarded"` adds +0.3 | PASS | `nikita/touchpoints/silence.py:158` — `DEFENSE_MODE_MODIFIERS["guarded"] = 0.3`. Test: `tests/touchpoints/test_intelligence.py::TestPsycheStateSilence::test_defense_mode_guarded_increases_silence` |
| AC-2.5 | `attachment_activation == "avoidant"` adds modifier | PASS (DEVIATION) | `nikita/touchpoints/silence.py:167` — `ATTACHMENT_MODIFIERS["avoidant"] = 0.15` (spec says +0.3, implementation uses +0.15). Also `anxious = 0.25` is not in spec but is implemented. Test: `tests/touchpoints/test_intelligence.py::TestPsycheStateSilence::test_attachment_anxious_increases_silence` (tests anxious, not avoidant specifically) |
| AC-2.6 | Graceful degradation if PsycheState unavailable | PASS | `nikita/touchpoints/silence.py:190-191` — `if not emotional_state: return 1.0` and `if psyche_state:` guard on line 217. Test: `tests/touchpoints/test_intelligence.py::TestPsycheStateSilence::test_no_psyche_state_uses_default` |
| AC-3.1 | `TouchpointStore.get_recent_delivered_content()` | FAIL | `nikita/touchpoints/store.py` — method does NOT exist. The spec required this method on `TouchpointStore` to return last 5 delivered message contents. |
| AC-3.2 | Similarity check >70% via SequenceMatcher | PASS | `nikita/touchpoints/engine.py:370-395` — `is_content_duplicate()` uses `SequenceMatcher` with threshold 0.7. Test: `tests/touchpoints/test_intelligence.py::TestContentDedup::test_similar_message_detected` |
| AC-3.3 | Regenerate or skip with "content_dedup" | FAIL | `nikita/touchpoints/engine.py:149-201` — `_deliver_single()` does NOT call `is_content_duplicate()`. The method exists as a utility but is not wired into the delivery pipeline. No regeneration or "content_dedup" skip logic in the delivery path. |
| AC-3.4 | Similarity check is O(N) where N=5 | PASS | `nikita/touchpoints/engine.py:389-394` — Simple for-loop over `recent_messages` list. O(N) by construction. |
| AC-4.1 | `MessageGenerator.generate()` accepts `open_threads` | PASS (PARTIAL) | `nikita/touchpoints/generator.py:111` — parameter accepted. But the parameter is NOT injected into the template context (lines 128-148 show context building without open_threads). |
| AC-4.2 | Open threads formatted as bullet list | FAIL | `nikita/touchpoints/generator.py:128-148` — `open_threads` is accepted but never added to the `context` dict or template. The formatting described in the spec is absent. |
| AC-4.3 | Max 3 threads injected (priority order) | PASS (STUB) | `nikita/touchpoints/engine.py:397-411` — `_load_open_threads()` always returns `[]` with a TODO comment: "Requires conversation_threads table (not yet created)." |
| AC-4.4 | Engine loads threads and passes to generator | PASS | `nikita/touchpoints/engine.py:359-360` — `open_threads = await self._load_open_threads(touchpoint.user_id)` loaded and passed to `generator.generate()`. |
| AC-5.1 | `MessageGenerator.generate()` accepts `vice_hints` | PASS (PARTIAL) | `nikita/touchpoints/generator.py:112` — parameter accepted. But NOT injected into the template context. Same gap as open_threads. |
| AC-5.2 | Vice hints formatted in prompt | FAIL | `nikita/touchpoints/generator.py:128-148` — `vice_hints` is never added to the `context` dict. The formatting string "Personality hints: she knows you enjoy..." is absent. |
| AC-5.3 | Only top 2 vices with `engagement_score > 0.3` | FAIL | `nikita/touchpoints/engine.py:413-433` — `_load_top_vices()` returns top 3 (not 2) via `prefs[:3]` and does NOT filter by `engagement_score > 0.3`. It loads all active vices without threshold. |
| AC-5.4 | Engine loads vices and passes to generator | PASS | `nikita/touchpoints/engine.py:360` — `vice_hints = await self._load_top_vices(touchpoint.user_id)` loaded and passed. |

## Test Coverage

- **14 tests** found in 1 test file:
  - `tests/touchpoints/test_intelligence.py`:
    - `TestLifeEventsWiring` — 2 tests (life event passed, no life event graceful)
    - `TestPsycheStateSilence` — 4 tests (guarded, withdrawing, anxious, no psyche state)
    - `TestContentDedup` — 4 tests (identical, similar, different, empty)
    - `TestThreadInjection` — 2 tests (threads included, no threads)
    - `TestViceHints` — 2 tests (vices included, no vices)

Note: Tests verify parameters are passed to mock generator but do NOT verify template injection (since the generator is mocked). This masks the gaps in AC-4.2 and AC-5.2.

## Findings

### HIGH: PsycheState not loaded in `_evaluate_silence()` (AC-2.1, AC-2.2)

The `_compute_emotional_modifier()` method correctly accepts and processes `psyche_state`, but there is no code path that actually passes it. `_evaluate_silence()` in `engine.py` does not import `PsycheStateRepository` or load psyche state. `apply_strategic_silence()` does not accept a `psyche_state` parameter, so even if it were loaded, there is no way to pass it through the public API.

**Impact**: PsycheState defense_mode and attachment_activation never influence silence decisions in production.

**Fix**: (1) Add `psyche_state: dict | None = None` parameter to `apply_strategic_silence()` and thread it to `_compute_emotional_modifier()`. (2) In `_evaluate_silence()`, load PsycheState via `PsycheStateRepository` and pass to `apply_strategic_silence()`.

### MEDIUM: Content dedup not wired into delivery path (AC-3.1, AC-3.3)

`is_content_duplicate()` exists as a utility method on `TouchpointEngine` but is never called from `_deliver_single()`. Additionally, `TouchpointStore.get_recent_delivered_content()` was never implemented, so there is no way to retrieve recent message content for comparison.

**Impact**: Nikita can send duplicate or near-identical proactive messages consecutively.

**Fix**: (1) Add `get_recent_delivered_content()` to `TouchpointStore`. (2) Call `is_content_duplicate()` in `_deliver_single()` after message generation, before Telegram send.

### MEDIUM: `open_threads` and `vice_hints` accepted but not injected into template (AC-4.2, AC-5.2)

`MessageGenerator.generate()` accepts both parameters but the method body (lines 128-148) never adds them to the `context` dict for template substitution. The parameters are silently dropped.

**Impact**: Even when open threads and vice hints are loaded, they have zero effect on the generated message content.

**Fix**: In `generator.py:generate()`, add `open_threads` and `vice_hints` to the `context` dict before `_format_template()`, and add corresponding `{{open_threads}}` and `{{vice_hints}}` placeholders to the template.

### LOW: Vice loading deviates from spec (AC-5.3)

`_load_top_vices()` returns top 3 vices (spec says 2) and does not filter by `engagement_score > 0.3`. This is a minor deviation since the downstream template injection is also broken.

### LOW: PsycheState modifier values deviate from spec (AC-2.3, AC-2.5)

- `withdrawing` modifier: spec says +0.5, implementation uses +0.6
- `avoidant` modifier: spec says +0.3, implementation uses +0.15
- `anxious` modifier: not in spec but implemented at +0.25

These may be intentional tuning adjustments but differ from the specification.

### LOW: `_load_open_threads()` is a permanent stub (AC-4.3)

Returns `[]` with a TODO comment noting the `conversation_threads` table does not exist. This is a known limitation documented in project memory.

## Recommendation

PASS with caveats — The structural scaffolding for all 5 features is in place (parameters threaded, methods defined, tests passing against mocks), but three integration gaps prevent FR-002 (PsycheState silence), FR-003 (content dedup), and FR-004/FR-005 (thread/vice template injection) from functioning end-to-end. The 14 tests all pass but test at the mock boundary, masking the downstream gaps. A follow-up spec should address the HIGH and MEDIUM findings to complete the intended behavior.
