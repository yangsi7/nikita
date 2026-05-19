# Tasks 056: Psyche Agent

**Spec**: 056-psyche-agent/spec.md
**Plan**: 056-psyche-agent/plan.md
**Total**: 25 tasks | **Est**: ~24h (21h + 15% buffer)

---

## Phase 1: Data Layer (US-2, US-6)

### T1: PsycheState Pydantic Model
- [x] Create `nikita/agents/psyche/__init__.py` with `is_psyche_agent_enabled()` convenience function
- [x] Create `nikita/agents/psyche/models.py` with `PsycheState(BaseModel)` — 8 fields
- [x] Fields: `attachment_activation` (Literal["secure","anxious","avoidant","disorganized"]), `defense_mode` (Literal["open","guarded","deflecting","withdrawing"]), `behavioral_guidance` (str, ~50 words), `internal_monologue` (str, ~30 words), `vulnerability_level` (float, Field(ge=0, le=1)), `emotional_tone` (Literal["playful","serious","warm","distant","volatile"]), `topics_to_encourage` (list[str], max_length=3), `topics_to_avoid` (list[str], max_length=3)
- [x] Add validators: non-empty strings, bounded floats, list max length
- [x] Add `@classmethod default()` returning safe first-time-user state
- [x] Verify JSON round-trip: `PsycheState.model_validate_json(state.model_dump_json())`
- **File**: `nikita/agents/psyche/__init__.py`, `nikita/agents/psyche/models.py`
- **Test**: `tests/agents/psyche/test_models.py` (created in T5)
- **AC**: AC-2.1, AC-2.2, AC-2.3, AC-2.4
- **Est**: 0.5h

### T2: SQLAlchemy Model for psyche_states
- [x] Create `nikita/db/models/psyche_state.py` with `PsycheStateRecord(Base, UUIDMixin, TimestampMixin)`
- [x] Columns: `user_id` (UUID FK UNIQUE → auth.users), `state` (JSONB NOT NULL DEFAULT '{}'), `generated_at` (TIMESTAMPTZ), `model` (Text DEFAULT 'sonnet'), `token_count` (Integer DEFAULT 0)
- [x] Modify `nikita/db/models/__init__.py` to import `PsycheStateRecord`
- [x] Follow `ReadyPrompt` model pattern
- **File**: `nikita/db/models/psyche_state.py`, `nikita/db/models/__init__.py`
- **Test**: `tests/db/repositories/test_psyche_state_repository.py` (created in T5)
- **AC**: AC-6.1
- **Est**: 0.5h

### T3: Supabase Migration — Table + RLS + Index
- [x] CREATE TABLE `psyche_states` with columns: id (UUID PK), user_id (UUID UNIQUE FK), state (JSONB), generated_at, model, token_count, created_at, updated_at
- [x] CREATE INDEX `idx_psyche_states_user_id` ON psyche_states(user_id) — btree
- [x] ENABLE ROW LEVEL SECURITY on psyche_states
- [x] CREATE POLICY "Users can read own psyche state" FOR SELECT USING (auth.uid() = user_id)
- [x] CREATE POLICY "Service role full access" FOR ALL USING (auth.role() = 'service_role')
- [x] Verify migration with Supabase MCP `execute_sql`
- **Tool**: Supabase MCP `apply_migration`
- **AC**: AC-6.1, AC-6.2, AC-6.3
- **Est**: 0.5h

### T4: PsycheStateRepository
- [x] Create `nikita/db/repositories/psyche_state_repository.py` extending `BaseRepository[PsycheStateRecord]`
- [x] Method: `get_current(user_id: UUID) -> PsycheStateRecord | None` — single JSONB read, <50ms
- [x] Method: `upsert(user_id, state: dict, model: str, token_count: int) -> PsycheStateRecord` — INSERT ON CONFLICT(user_id) DO UPDATE
- [x] Follow `ReadyPromptRepository` pattern
- **File**: `nikita/db/repositories/psyche_state_repository.py`
- **Test**: `tests/db/repositories/test_psyche_state_repository.py` (created in T5)
- **AC**: AC-4.4, AC-6.1
- **Est**: 0.5h

### T5: Tests — Model + Repository
- [x] Create `tests/agents/psyche/test_models.py`: all 8 field validations, Literal enforcement, float bounds, list max_length, default() classmethod, JSON round-trip
- [x] Create `tests/db/repositories/test_psyche_state_repository.py`: get_current returns None for missing user, upsert creates new, upsert updates existing, async mock session pattern
- [x] Minimum 15 test cases across both files
- **File**: `tests/agents/psyche/test_models.py`, `tests/db/repositories/test_psyche_state_repository.py`
- **AC**: AC-2.1, AC-2.2, AC-2.3, AC-2.4
- **Est**: 1h

---

## Phase 2: Psyche Agent Core (US-1)

### T6: PsycheDeps Dataclass
- [x] Create `nikita/agents/psyche/deps.py` with `PsycheDeps` dataclass
- [x] Fields: `user_id: UUID`, `score_history: list[dict]`, `emotional_states: list[dict]`, `life_events: list[dict]`, `npc_interactions: list[dict]`, `current_chapter: int = 1`
- [x] Follow `NikitaDeps` pattern
- **File**: `nikita/agents/psyche/deps.py`
- **Test**: `tests/agents/psyche/test_agent.py` (created in T9)
- **AC**: AC-1.2
- **Est**: 0.5h

### T7: Psyche Agent (Structured Output)
- [x] Create `nikita/agents/psyche/agent.py` with Pydantic AI `Agent[PsycheDeps, PsycheState]`
- [x] Set `output_type=PsycheState` for structured output
- [x] Model from `settings.psyche_model` (default Sonnet 4.5)
- [x] System instructions describing Nikita's psychology framework
- [x] `@agent.instructions` injecting PsycheDeps context (score_history, emotional_states, life_events, NPC interactions)
- [x] Lazy singleton via `@lru_cache` — follow `_create_nikita_agent()` pattern
- [x] Function: `generate_psyche_state(deps) -> tuple[PsycheState, int]` returning state + token_count
- **File**: `nikita/agents/psyche/agent.py`
- **Test**: `tests/agents/psyche/test_agent.py` (created in T9)
- **AC**: AC-1.1, AC-1.3, AC-1.6
- **Est**: 1.5h

### T8: Feature Flag — psyche_agent_enabled + psyche_model
- [x] Add `psyche_agent_enabled: bool = False` to `nikita/config/settings.py` (~line 148, after conflict settings)
- [x] Add `psyche_model: str = "anthropic:claude-sonnet-4-5-20250929"` to settings
- [x] Wire `is_psyche_agent_enabled()` in `nikita/agents/psyche/__init__.py` reading from settings
- **File**: `nikita/config/settings.py`, `nikita/agents/psyche/__init__.py`
- **Test**: `tests/agents/psyche/test_models.py` (extend in T5)
- **AC**: AC-6.6, AC-7.1, AC-7.2
- **Est**: 0.25h

### T9: Tests — Agent Generation
- [x] Create `tests/agents/psyche/test_agent.py`
- [x] Test structured output returns valid PsycheState with all 8 fields
- [x] Test token count tracking returned correctly
- [x] Test configurable model setting respected
- [x] Mock Pydantic AI agent.run() — follow existing agent test patterns
- [x] Minimum 8 test cases
- **File**: `tests/agents/psyche/test_agent.py`
- **AC**: AC-1.1, AC-1.3, AC-1.6
- **Est**: 1h

---

## Phase 3: Batch Job (US-1, US-6)

### T10: Batch Orchestration Module
- [x] Create `nikita/agents/psyche/batch.py` with `run_psyche_batch() -> dict`
- [x] Get active users from DB
- [x] Load 48h of: score_history, emotional_states, life_events, NPC interactions per user
- [x] Call `generate_psyche_state()` per user
- [x] Upsert result via `PsycheStateRepository.upsert()`
- [x] Per-user `try/except` for failure isolation (AC-1.5)
- [x] Per-user `asyncio.wait_for(timeout=30)` for 30s timeout (AC-1.4)
- [x] Return summary dict: `{processed: int, failed: int, errors: list[str]}`
- **File**: `nikita/agents/psyche/batch.py`
- **Test**: `tests/agents/psyche/test_batch.py` (created in T12)
- **AC**: AC-1.1, AC-1.2, AC-1.4, AC-1.5
- **Est**: 1.5h

### T11: Task Endpoint — /tasks/psyche-batch
- [x] Modify `nikita/api/routes/tasks.py`: add `@router.post("/psyche-batch")` endpoint
- [x] Add `PSYCHE_BATCH` to job type enum in `nikita/db/models/job_execution.py`
- [x] Verify `verify_task_secret` auth, `JobExecutionRepository` tracking
- [x] Guard on `psyche_agent_enabled` feature flag — return 200 skip when OFF
- [x] Follow `/decay` endpoint pattern exactly
- **File**: `nikita/api/routes/tasks.py`, `nikita/db/models/job_execution.py`
- **Test**: `tests/api/routes/test_tasks_psyche.py` (created in T12)
- **AC**: AC-6.4, AC-6.5, AC-6.6
- **Est**: 1h

### T12: Tests — Batch + Endpoint
- [x] Create `tests/agents/psyche/test_batch.py`: multi-user processing, single-user failure isolation, 30s timeout behavior, flag OFF skips
- [x] Create `tests/api/routes/test_tasks_psyche.py`: auth verification, job logging, response format, flag OFF returns skip
- [x] Minimum 12 test cases across both files
- **File**: `tests/agents/psyche/test_batch.py`, `tests/api/routes/test_tasks_psyche.py`
- **AC**: AC-1.4, AC-1.5, AC-6.5, AC-6.6
- **Est**: 1.5h

---

## Phase 4: Trigger Detector (US-3)

### T13: Trigger Detection Module
- [x] Create `nikita/agents/psyche/trigger.py`
- [x] Define `TriggerTier` enum: CACHED=1, QUICK=2, DEEP=3
- [x] Function: `detect_trigger_tier(message, user, score_delta, conflict_state, is_first_message_today) -> TriggerTier` — pure function, rule-based, <5ms
- [x] Tier 3 triggers: horseman in conflict_state, boss_fight status, explicit emotional disclosure keywords
- [x] Tier 2 triggers: first_message_today, score_delta < -5, moderate emotional keywords
- [x] Tier 1: everything else (default)
- [x] Function: `check_tier3_circuit_breaker(user_id, session) -> bool` — max 5/user/day
- [x] Circuit breaker reads count from DB, returns False when limit reached
- **File**: `nikita/agents/psyche/trigger.py`
- **Test**: `tests/agents/psyche/test_trigger.py` (created in T15)
- **AC**: AC-3.1, AC-3.2, AC-3.3, AC-3.4, AC-3.5, AC-3.6
- **Est**: 1.5h

### T14: Quick Analysis (Tier 2) + Deep Analysis (Tier 3)
- [x] Modify `nikita/agents/psyche/agent.py`
- [x] Add `quick_analyze(deps, message, session) -> tuple[PsycheState, int]` — Sonnet, ~500 input tokens
- [x] Add `deep_analyze(deps, message, session) -> tuple[PsycheState, int]` — Opus
- [x] Both upsert result to DB via repository
- [x] Both track token count in return tuple
- **File**: `nikita/agents/psyche/agent.py`
- **Test**: `tests/agents/psyche/test_trigger.py` (created in T15)
- **AC**: AC-3.2, AC-3.3, AC-7.3
- **Est**: 1h

### T15: Tests — Trigger Detector + Circuit Breaker
- [x] Create `tests/agents/psyche/test_trigger.py`
- [x] Test all 6 trigger conditions route to correct tier
- [x] Test circuit breaker blocks at 5/day threshold
- [x] Test circuit breaker resets across days
- [x] Test default message → Tier 1
- [x] Test <5ms benchmark for detect_trigger_tier (rule-based, no LLM)
- [x] Test quick_analyze uses Sonnet, deep_analyze uses Opus
- [x] Minimum 15 test cases
- **File**: `tests/agents/psyche/test_trigger.py`
- **AC**: AC-3.1, AC-3.2, AC-3.3, AC-3.4, AC-3.5, AC-3.6, AC-7.3
- **Est**: 1.5h

---

## Phase 5: Conversation Integration (US-4, US-5)

### T16: Add psyche_state to NikitaDeps
- [x] Modify `nikita/agents/text/deps.py` — add `psyche_state: dict | None = None` after `session` field
- [x] Ensure backward compatibility: existing code unaffected by new optional field
- **File**: `nikita/agents/text/deps.py`
- **Test**: `tests/agents/psyche/test_integration.py` (created in T22)
- **AC**: AC-4.2
- **Est**: 0.25h

### T17: Add psyche_state to PipelineContext
- [x] Modify `nikita/pipeline/models.py` — add `psyche_state: dict | None = None` after `nikita_daily_events` (~line 92)
- [x] Ensure backward compatibility: pipeline unaffected when field is None
- **File**: `nikita/pipeline/models.py`
- **Test**: `tests/pipeline/test_psyche_prompt.py` (created in T22)
- **AC**: AC-5.5
- **Est**: 0.25h

### T18: Pre-Conversation Psyche Read in Message Handler
- [x] Modify `nikita/platforms/telegram/message_handler.py` (~line 225, before `text_agent_handler.handle()`)
- [x] If `psyche_agent_enabled`: read via `PsycheStateRepository.get_current(user_id)`
- [x] Run `detect_trigger_tier()` on message
- [x] Tier 2 → call `quick_analyze()`, Tier 3 → call `deep_analyze()` (with circuit breaker check)
- [x] Pass resulting dict to `NikitaDeps.psyche_state`
- [x] Wrap entire block in `try/except` for graceful degradation — log error, set psyche_state=None
- [x] When flag OFF: skip entirely, psyche_state stays None
- **File**: `nikita/platforms/telegram/message_handler.py`
- **Test**: `tests/agents/psyche/test_integration.py` (created in T22)
- **AC**: AC-4.1, AC-4.3, AC-4.4
- **Est**: 1h

### T19: Prompt Layer 3 in system_prompt.j2
- [x] Modify `nikita/pipeline/templates/system_prompt.j2`
- [x] Insert SECTION 3.5 between Section 3 (~line 119) and Section 4 (~line 122)
- [x] Template renders: behavioral_guidance, emotional_tone, topics_to_encourage, topics_to_avoid
- [x] When `psyche_state` is None/falsy: render empty string (zero tokens)
- [x] When populated: ~150 tokens
- **File**: `nikita/pipeline/templates/system_prompt.j2`
- **Test**: `tests/pipeline/test_psyche_prompt.py` (created in T22)
- **AC**: AC-5.1, AC-5.2, AC-5.3, AC-5.4
- **Est**: 0.5h

### T20: Prompt Builder — Pass psyche_state to Template
- [x] Modify `nikita/pipeline/stages/prompt_builder.py`
- [x] Include `psyche_state=ctx.psyche_state` in Jinja2 template context dict
- **File**: `nikita/pipeline/stages/prompt_builder.py`
- **Test**: `tests/pipeline/test_psyche_prompt.py` (created in T22)
- **AC**: AC-5.1, AC-5.5
- **Est**: 0.25h

### T21: Psyche Briefing via @agent.instructions
- [x] Modify `nikita/agents/text/agent.py`
- [x] Add `add_psyche_briefing(ctx)` as `@agent.instructions` handler
- [x] Returns formatted briefing string from `ctx.deps.psyche_state`
- [x] Returns empty string if `generated_prompt` is set (pipeline L3 already included)
- [x] Returns empty string if `psyche_state` is None
- **File**: `nikita/agents/text/agent.py`
- **Test**: `tests/agents/psyche/test_integration.py` (created in T22)
- **AC**: AC-4.2, AC-5.2
- **Est**: 0.5h

### T22: Tests — Integration
- [x] Create `tests/agents/psyche/test_integration.py`: handler reads psyche before agent call, graceful degradation on DB failure, flag OFF = no psyche read, trigger routing dispatches correct tier
- [x] Create `tests/pipeline/test_psyche_prompt.py`: L3 renders ~150 tokens when populated, L3 renders empty when None, psyche_state passed through prompt builder, @agent.instructions injection
- [x] Minimum 12 test cases across both files
- **File**: `tests/agents/psyche/test_integration.py`, `tests/pipeline/test_psyche_prompt.py`
- **AC**: AC-4.1, AC-4.3, AC-4.4, AC-5.1, AC-5.2, AC-5.3, AC-5.4, AC-5.5
- **Est**: 1.5h

---

## Phase 6: Cost Control (US-7)

### T23: Token Tracking + Cost Monitoring
- [x] Modify `nikita/agents/psyche/agent.py`: ensure all generate/quick/deep functions return token_count
- [x] Modify `nikita/agents/psyche/batch.py`: log token count per generation to DB via upsert
- [x] Add structured logging: `[PSYCHE] model=sonnet tokens=450 user_id=xxx tier=batch|quick|deep`
- **File**: `nikita/agents/psyche/agent.py`, `nikita/agents/psyche/batch.py`
- **Test**: `tests/agents/psyche/test_cost_control.py` (created in T24)
- **AC**: AC-7.1, AC-7.4, AC-1.6
- **Est**: 0.5h

### T24: Tests — Cost Control
- [x] Create `tests/agents/psyche/test_cost_control.py`
- [x] Test Sonnet is default model for batch generation
- [x] Test circuit breaker enforces 5/user/day limit
- [x] Test token count logged to DB on each generation
- [x] Test model switch via `psyche_model` setting
- [x] Minimum 6 test cases
- **File**: `tests/agents/psyche/test_cost_control.py`
- **AC**: AC-7.1, AC-7.2, AC-7.3, AC-7.4
- **Est**: 0.5h

---

## Phase 7: E2E

### T25: E2E — Full Psyche Flow
- [x] Create `tests/e2e/test_psyche_e2e.py`
- [x] Flow 1: Create user → batch generates PsycheState → verify DB row with all 8 fields
- [x] Flow 2: Simulate message → psyche read → L3 injected in system prompt
- [x] Flow 3: Trigger routing — default message → Tier 1 (cached read), emotional message → Tier 2
- [x] Flow 4: Feature flag OFF → no psyche read, no L3, batch skips
- [x] Use `httpx.ASGITransport` pattern (no Cloud Run needed)
- [x] Minimum 6 test cases
- **File**: `tests/e2e/test_psyche_e2e.py`
- **AC**: AC-1.1, AC-3.1, AC-4.1, AC-5.1
- **Est**: 1.5h

---

## Summary

| Phase | Tasks | Est Hours | Key Output |
|-------|-------|-----------|------------|
| 1: Data Layer | T1-T5 | 3.0h | PsycheState model, SQLAlchemy, migration, repository |
| 2: Agent Core | T6-T9 | 3.25h | PsycheDeps, agent, feature flag, agent tests |
| 3: Batch Job | T10-T12 | 4.0h | Batch orchestration, task endpoint, tests |
| 4: Trigger Detector | T13-T15 | 4.0h | Trigger routing, quick/deep analysis, tests |
| 5: Integration | T16-T22 | 4.25h | NikitaDeps, pipeline, handler, prompt L3, tests |
| 6: Cost Control | T23-T24 | 1.0h | Token tracking, cost tests |
| 7: E2E | T25 | 1.5h | Full flow E2E tests |
| **Total** | **25** | **~21h** | ~24h with 15% buffer |

## Task Status Tracker

| ID | Status | Description |
|----|--------|-------------|
| T1 | [ ] | PsycheState Pydantic model |
| T2 | [ ] | SQLAlchemy model for psyche_states |
| T3 | [ ] | Supabase migration — table + RLS + index |
| T4 | [ ] | PsycheStateRepository |
| T5 | [ ] | Tests — model + repository |
| T6 | [ ] | PsycheDeps dataclass |
| T7 | [ ] | Psyche agent (structured output) |
| T8 | [ ] | Feature flag + psyche_model setting |
| T9 | [ ] | Tests — agent generation |
| T10 | [ ] | Batch orchestration module |
| T11 | [ ] | Task endpoint /tasks/psyche-batch |
| T12 | [ ] | Tests — batch + endpoint |
| T13 | [ ] | Trigger detection module |
| T14 | [ ] | Quick analysis (Tier 2) + deep analysis (Tier 3) |
| T15 | [ ] | Tests — trigger detector + circuit breaker |
| T16 | [ ] | Add psyche_state to NikitaDeps |
| T17 | [ ] | Add psyche_state to PipelineContext |
| T18 | [ ] | Pre-conversation psyche read in message handler |
| T19 | [ ] | Prompt Layer 3 in system_prompt.j2 |
| T20 | [ ] | Prompt builder — pass psyche_state to template |
| T21 | [ ] | Psyche briefing via @agent.instructions |
| T22 | [ ] | Tests — integration |
| T23 | [ ] | Token tracking + cost monitoring |
| T24 | [ ] | Tests — cost control |
| T25 | [ ] | E2E — full psyche flow |
