# Spec 114 — Vice Pipeline Activation

## Status: In Progress

## Problem

`ViceAnalyzer.analyze_exchange()` (`nikita/engine/vice/analyzer.py:97`) and `ViceScorer.process_signals()` (`nikita/engine/vice/scorer.py:86`) have **zero callers outside the vice module**. The pipeline template renders `{{ vices }}` (system_prompt.j2:627-655) but no stage populates it from live conversations. Vice profiles are static post-seeding for ALL users — they never change after onboarding.

### Current gap (audit finding GE-006)

| Component | Status |
|-----------|--------|
| ViceAnalyzer.analyze_exchange() | ✅ Built, ❌ Never called |
| ViceScorer.process_signals() | ✅ Built, ❌ Never called |
| ViceService.process_conversation() | ✅ Built, ❌ Never called |
| Pipeline stage | ❌ Missing |
| Feature flag | ❌ Missing |
| {{ vices }} template variable | ✅ Template renders it, ❌ always static |

## Functional Requirements

### FR-001 — ViceStage in pipeline
Add `ViceStage` as a non-critical pipeline stage between `EmotionalStage` (position 5) and `GameStateStage` (position 6). New stage order:

1. extraction (critical)
2. memory_update (critical)
3. persistence
4. life_sim
5. emotional
6. **vice** ← NEW (non-critical)
7. game_state
8. conflict
9. touchpoint
10. summary
11. prompt_builder

### FR-002 — Vice analysis from last exchange
`ViceStage` must:
1. Extract the last user message + last Nikita response from `ctx.conversation.messages` (JSONB list of dicts with `role`/`content` keys; guard for `ctx.conversation is None`)
2. Call `ViceService().process_conversation(user_id=ctx.user_id, user_message=user_message, nikita_message=nikita_response, conversation_id=ctx.conversation_id, chapter=ctx.chapter)` — note: parameter is `nikita_message` (not `nikita_response`)
3. If fewer than 2 valid messages (user + nikita pair), skip analysis without error

### FR-003 — Feature flag guard
Check `settings.vice_pipeline_enabled` (new setting, default `False`). If False, stage exits immediately without calling LLM. Allows safe rollout via `VICE_PIPELINE_ENABLED=true` env var.

### FR-004 — Non-fatal execution
Stage must never abort the pipeline. All exceptions caught and logged at WARNING level. Stage timeout: 45 seconds (ViceAnalyzer makes an LLM call).

### FR-005 — ViceService session management
`ViceService()` takes no constructor arguments — `ViceScorer` manages its own session via `get_session_maker()` internally (`scorer.py:77-82`). `ViceStage` simply instantiates `ViceService()` with no arguments. Note: ViceScorer's DB writes occur on a separate session and are committed independently; they are outside the orchestrator's SAVEPOINT boundary. This is acceptable for a non-critical stage — vice preference updates are best-effort.

## Acceptance Criteria

| ID | Criterion | Test |
|----|-----------|------|
| AC-001 | ViceStage appears between EmotionalStage and GameStateStage in orchestrator | `test_vice_stage_position` |
| AC-002 | ViceService.process_conversation() called with last exchange messages | `test_vice_stage_calls_service` |
| AC-003 | Stage skipped (no-op) when vice_pipeline_enabled=False | `test_vice_stage_flag_disabled` |
| AC-004 | Stage failure is non-fatal (pipeline continues) | `test_vice_stage_failure_non_fatal` |
| AC-005 | Stage skipped when fewer than 2 valid messages | `test_vice_stage_insufficient_messages` |
| AC-006 | settings.vice_pipeline_enabled exists and defaults to False | `test_vice_flag_setting_default` |

## Implementation Scope

### Files to modify
- `nikita/config/settings.py` — add `vice_pipeline_enabled: bool = False`
- `nikita/pipeline/orchestrator.py` — add `ViceStage` between EmotionalStage and GameStateStage; update `stages_total=10` → `11`
- `nikita/pipeline/models.py` — update `stages_total: int = 10` → `11`
- `nikita/observability/types.py` — add `VICE_COMPLETE` constant + `"vice"` entry in `STAGE_EVENT_TYPES` + `ALL_EVENT_TYPES`
- `nikita/observability/snapshots.py` — add `"vice": []` entry in `STAGE_FIELDS` (stage writes to DB, not ctx fields)

### Files to create
- `nikita/pipeline/stages/vice.py` — `ViceStage` class
- `tests/pipeline/stages/test_vice_stage.py` — AC-001 through AC-005
- `tests/config/test_vice_setting.py` — AC-006

### Out of scope
- Modifying ViceAnalyzer, ViceScorer, ViceService themselves
- Voice path changes (vice analysis runs via pipeline, which covers both text + voice)
- Changing {{ vices }} template rendering (already correct; stage updates the DB, prompt_builder reads it next run via `user.vice_preferences`)

## Design Decisions

1. **Non-critical**: Stage timeout 45s. Any exception → `logger.warning`, pipeline continues.
2. **Feature flag default=False**: Safe rollout gate. Production opt-in via env var `VICE_PIPELINE_ENABLED=true`.
3. **Last exchange extraction**: Iterate `ctx.conversation.messages` in reverse to find last `(user, nikita)` consecutive pair. Skip if not found. Guard for `ctx.conversation is None`.
4. **ViceService reuse**: Use existing `ViceService()` (no-arg constructor; handles analyze + score in one call). `ViceScorer` manages its own DB session internally. Parameter name is `nikita_message` (not `nikita_response`).
5. **No same-run prompt update**: ViceStage updates DB; `ctx.vices` was populated before stages ran. Updated vices appear in the next pipeline run. Acceptable — vice profile evolves over multiple conversations, not within one.
6. **Stage name**: `"vice"` (matches convention: single lowercase word).
