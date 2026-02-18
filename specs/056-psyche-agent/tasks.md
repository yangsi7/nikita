# Tasks 056: Psyche Agent

**Spec**: 056-psyche-agent/spec.md
**Plan**: 056-psyche-agent/plan.md
**Total**: 25 tasks | **Est**: ~24h (21h + 15% buffer)

---

## Phase 1: Data Layer (US-2, US-6)

### T1: PsycheState Pydantic Model
- [ ] Create `nikita/agents/psyche/__init__.py` with `is_psyche_agent_enabled()` convenience function
- [ ] Create `nikita/agents/psyche/models.py` with `PsycheState(BaseModel)` — 8 fields
- [ ] Fields: `attachment_activation` (Literal["secure","anxious","avoidant","disorganized"]), `defense_mode` (Literal["open","guarded","deflecting","withdrawing"]), `behavioral_guidance` (str, ~50 words), `internal_monologue` (str, ~30 words), `vulnerability_level` (float, Field(ge=0, le=1)), `emotional_tone` (Literal["playful","serious","warm","distant","volatile"]), `topics_to_encourage` (list[str], max_length=3), `topics_to_avoid` (list[str], max_length=3)
- [ ] Add validators: non-empty strings, bounded floats, list max length
- [ ] Add `@classmethod default()` returning safe first-time-user state
- [ ] Verify JSON round-trip: `PsycheState.model_validate_json(state.model_dump_json())`
- **File**: `nikita/agents/psyche/__init__.py`, `nikita/agents/psyche/models.py`
- **Test**: `tests/agents/psyche/test_models.py` (created in T5)
- **AC**: AC-2.1, AC-2.2, AC-2.3, AC-2.4
- **Est**: 0.5h

### T2: SQLAlchemy Model for psyche_states
- [ ] Create `nikita/db/models/psyche_state.py` with `PsycheStateRecord(Base, UUIDMixin, TimestampMixin)`
- [ ] Columns: `user_id` (UUID FK UNIQUE → auth.users), `state` (JSONB NOT NULL DEFAULT '{}'), `generated_at` (TIMESTAMPTZ), `model` (Text DEFAULT 'sonnet'), `token_count` (Integer DEFAULT 0)
- [ ] Modify `nikita/db/models/__init__.py` to import `PsycheStateRecord`
- [ ] Follow `ReadyPrompt` model pattern
- **File**: `nikita/db/models/psyche_state.py`, `nikita/db/models/__init__.py`
- **Test**: `tests/db/repositories/test_psyche_state_repository.py` (created in T5)
- **AC**: AC-6.1
- **Est**: 0.5h

### T3: Supabase Migration — Table + RLS + Index
- [ ] CREATE TABLE `psyche_states` with columns: id (UUID PK), user_id (UUID UNIQUE FK), state (JSONB), generated_at, model, token_count, created_at, updated_at
- [ ] CREATE INDEX `idx_psyche_states_user_id` ON psyche_states(user_id) — btree
- [ ] ENABLE ROW LEVEL SECURITY on psyche_states
- [ ] CREATE POLICY "Users can read own psyche state" FOR SELECT USING (auth.uid() = user_id)
- [ ] CREATE POLICY "Service role full access" FOR ALL USING (auth.role() = 'service_role')
- [ ] Verify migration with Supabase MCP `execute_sql`
- **Tool**: Supabase MCP `apply_migration`
- **AC**: AC-6.1, AC-6.2, AC-6.3
- **Est**: 0.5h

### T4: PsycheStateRepository
- [ ] Create `nikita/db/repositories/psyche_state_repository.py` extending `BaseRepository[PsycheStateRecord]`
- [ ] Method: `get_current(user_id: UUID) -> PsycheStateRecord | None` — single JSONB read, <50ms
- [ ] Method: `upsert(user_id, state: dict, model: str, token_count: int) -> PsycheStateRecord` — INSERT ON CONFLICT(user_id) DO UPDATE
- [ ] Follow `ReadyPromptRepository` pattern
- **File**: `nikita/db/repositories/psyche_state_repository.py`
- **Test**: `tests/db/repositories/test_psyche_state_repository.py` (created in T5)
- **AC**: AC-4.4, AC-6.1
- **Est**: 0.5h

### T5: Tests — Model + Repository
- [ ] Create `tests/agents/psyche/test_models.py`: all 8 field validations, Literal enforcement, float bounds, list max_length, default() classmethod, JSON round-trip
- [ ] Create `tests/db/repositories/test_psyche_state_repository.py`: get_current returns None for missing user, upsert creates new, upsert updates existing, async mock session pattern
- [ ] Minimum 15 test cases across both files
- **File**: `tests/agents/psyche/test_models.py`, `tests/db/repositories/test_psyche_state_repository.py`
- **AC**: AC-2.1, AC-2.2, AC-2.3, AC-2.4
- **Est**: 1h

---

## Phase 2: Psyche Agent Core (US-1)

### T6: PsycheDeps Dataclass
- [ ] Create `nikita/agents/psyche/deps.py` with `PsycheDeps` dataclass
- [ ] Fields: `user_id: UUID`, `score_history: list[dict]`, `emotional_states: list[dict]`, `life_events: list[dict]`, `npc_interactions: list[dict]`, `current_chapter: int = 1`
- [ ] Follow `NikitaDeps` pattern
- **File**: `nikita/agents/psyche/deps.py`
- **Test**: `tests/agents/psyche/test_agent.py` (created in T9)
- **AC**: AC-1.2
- **Est**: 0.5h

### T7: Psyche Agent (Structured Output)
- [ ] Create `nikita/agents/psyche/agent.py` with Pydantic AI `Agent[PsycheDeps, PsycheState]`
- [ ] Set `output_type=PsycheState` for structured output
- [ ] Model from `settings.psyche_model` (default Sonnet 4.5)
- [ ] System instructions describing Nikita's psychology framework
- [ ] `@agent.instructions` injecting PsycheDeps context (score_history, emotional_states, life_events, NPC interactions)
- [ ] Lazy singleton via `@lru_cache` — follow `_create_nikita_agent()` pattern
- [ ] Function: `generate_psyche_state(deps) -> tuple[PsycheState, int]` returning state + token_count
- **File**: `nikita/agents/psyche/agent.py`
- **Test**: `tests/agents/psyche/test_agent.py` (created in T9)
- **AC**: AC-1.1, AC-1.3, AC-1.6
- **Est**: 1.5h

### T8: Feature Flag — psyche_agent_enabled + psyche_model
- [ ] Add `psyche_agent_enabled: bool = False` to `nikita/config/settings.py` (~line 148, after conflict settings)
- [ ] Add `psyche_model: str = "anthropic:claude-sonnet-4-5-20250929"` to settings
- [ ] Wire `is_psyche_agent_enabled()` in `nikita/agents/psyche/__init__.py` reading from settings
- **File**: `nikita/config/settings.py`, `nikita/agents/psyche/__init__.py`
- **Test**: `tests/agents/psyche/test_models.py` (extend in T5)
- **AC**: AC-6.6, AC-7.1, AC-7.2
- **Est**: 0.25h

### T9: Tests — Agent Generation
- [ ] Create `tests/agents/psyche/test_agent.py`
- [ ] Test structured output returns valid PsycheState with all 8 fields
- [ ] Test token count tracking returned correctly
- [ ] Test configurable model setting respected
- [ ] Mock Pydantic AI agent.run() — follow existing agent test patterns
- [ ] Minimum 8 test cases
- **File**: `tests/agents/psyche/test_agent.py`
- **AC**: AC-1.1, AC-1.3, AC-1.6
- **Est**: 1h

---

## Phase 3: Batch Job (US-1, US-6)

### T10: Batch Orchestration Module
- [ ] Create `nikita/agents/psyche/batch.py` with `run_psyche_batch() -> dict`
- [ ] Get active users from DB
- [ ] Load 48h of: score_history, emotional_states, life_events, NPC interactions per user
- [ ] Call `generate_psyche_state()` per user
- [ ] Upsert result via `PsycheStateRepository.upsert()`
- [ ] Per-user `try/except` for failure isolation (AC-1.5)
- [ ] Per-user `asyncio.wait_for(timeout=30)` for 30s timeout (AC-1.4)
- [ ] Return summary dict: `{processed: int, failed: int, errors: list[str]}`
- **File**: `nikita/agents/psyche/batch.py`
- **Test**: `tests/agents/psyche/test_batch.py` (created in T12)
- **AC**: AC-1.1, AC-1.2, AC-1.4, AC-1.5
- **Est**: 1.5h

### T11: Task Endpoint — /tasks/psyche-batch
- [ ] Modify `nikita/api/routes/tasks.py`: add `@router.post("/psyche-batch")` endpoint
- [ ] Add `PSYCHE_BATCH` to job type enum in `nikita/db/models/job_execution.py`
- [ ] Verify `verify_task_secret` auth, `JobExecutionRepository` tracking
- [ ] Guard on `psyche_agent_enabled` feature flag — return 200 skip when OFF
- [ ] Follow `/decay` endpoint pattern exactly
- **File**: `nikita/api/routes/tasks.py`, `nikita/db/models/job_execution.py`
- **Test**: `tests/api/routes/test_tasks_psyche.py` (created in T12)
- **AC**: AC-6.4, AC-6.5, AC-6.6
- **Est**: 1h

### T12: Tests — Batch + Endpoint
- [ ] Create `tests/agents/psyche/test_batch.py`: multi-user processing, single-user failure isolation, 30s timeout behavior, flag OFF skips
- [ ] Create `tests/api/routes/test_tasks_psyche.py`: auth verification, job logging, response format, flag OFF returns skip
- [ ] Minimum 12 test cases across both files
- **File**: `tests/agents/psyche/test_batch.py`, `tests/api/routes/test_tasks_psyche.py`
- **AC**: AC-1.4, AC-1.5, AC-6.5, AC-6.6
- **Est**: 1.5h

---

## Phase 4: Trigger Detector (US-3)

### T13: Trigger Detection Module
- [ ] Create `nikita/agents/psyche/trigger.py`
- [ ] Define `TriggerTier` enum: CACHED=1, QUICK=2, DEEP=3
- [ ] Function: `detect_trigger_tier(message, user, score_delta, conflict_state, is_first_message_today) -> TriggerTier` — pure function, rule-based, <5ms
- [ ] Tier 3 triggers: horseman in conflict_state, boss_fight status, explicit emotional disclosure keywords
- [ ] Tier 2 triggers: first_message_today, score_delta < -5, moderate emotional keywords
- [ ] Tier 1: everything else (default)
- [ ] Function: `check_tier3_circuit_breaker(user_id, session) -> bool` — max 5/user/day
- [ ] Circuit breaker reads count from DB, returns False when limit reached
- **File**: `nikita/agents/psyche/trigger.py`
- **Test**: `tests/agents/psyche/test_trigger.py` (created in T15)
- **AC**: AC-3.1, AC-3.2, AC-3.3, AC-3.4, AC-3.5, AC-3.6
- **Est**: 1.5h

### T14: Quick Analysis (Tier 2) + Deep Analysis (Tier 3)
- [ ] Modify `nikita/agents/psyche/agent.py`
- [ ] Add `quick_analyze(deps, message, session) -> tuple[PsycheState, int]` — Sonnet, ~500 input tokens
- [ ] Add `deep_analyze(deps, message, session) -> tuple[PsycheState, int]` — Opus
- [ ] Both upsert result to DB via repository
- [ ] Both track token count in return tuple
- **File**: `nikita/agents/psyche/agent.py`
- **Test**: `tests/agents/psyche/test_trigger.py` (created in T15)
- **AC**: AC-3.2, AC-3.3, AC-7.3
- **Est**: 1h

### T15: Tests — Trigger Detector + Circuit Breaker
- [ ] Create `tests/agents/psyche/test_trigger.py`
- [ ] Test all 6 trigger conditions route to correct tier
- [ ] Test circuit breaker blocks at 5/day threshold
- [ ] Test circuit breaker resets across days
- [ ] Test default message → Tier 1
- [ ] Test <5ms benchmark for detect_trigger_tier (rule-based, no LLM)
- [ ] Test quick_analyze uses Sonnet, deep_analyze uses Opus
- [ ] Minimum 15 test cases
- **File**: `tests/agents/psyche/test_trigger.py`
- **AC**: AC-3.1, AC-3.2, AC-3.3, AC-3.4, AC-3.5, AC-3.6, AC-7.3
- **Est**: 1.5h

---

## Phase 5: Conversation Integration (US-4, US-5)

### T16: Add psyche_state to NikitaDeps
- [ ] Modify `nikita/agents/text/deps.py` — add `psyche_state: dict | None = None` after `session` field
- [ ] Ensure backward compatibility: existing code unaffected by new optional field
- **File**: `nikita/agents/text/deps.py`
- **Test**: `tests/agents/psyche/test_integration.py` (created in T22)
- **AC**: AC-4.2
- **Est**: 0.25h

### T17: Add psyche_state to PipelineContext
- [ ] Modify `nikita/pipeline/models.py` — add `psyche_state: dict | None = None` after `nikita_daily_events` (~line 92)
- [ ] Ensure backward compatibility: pipeline unaffected when field is None
- **File**: `nikita/pipeline/models.py`
- **Test**: `tests/pipeline/test_psyche_prompt.py` (created in T22)
- **AC**: AC-5.5
- **Est**: 0.25h

### T18: Pre-Conversation Psyche Read in Message Handler
- [ ] Modify `nikita/platforms/telegram/message_handler.py` (~line 225, before `text_agent_handler.handle()`)
- [ ] If `psyche_agent_enabled`: read via `PsycheStateRepository.get_current(user_id)`
- [ ] Run `detect_trigger_tier()` on message
- [ ] Tier 2 → call `quick_analyze()`, Tier 3 → call `deep_analyze()` (with circuit breaker check)
- [ ] Pass resulting dict to `NikitaDeps.psyche_state`
- [ ] Wrap entire block in `try/except` for graceful degradation — log error, set psyche_state=None
- [ ] When flag OFF: skip entirely, psyche_state stays None
- **File**: `nikita/platforms/telegram/message_handler.py`
- **Test**: `tests/agents/psyche/test_integration.py` (created in T22)
- **AC**: AC-4.1, AC-4.3, AC-4.4
- **Est**: 1h

### T19: Prompt Layer 3 in system_prompt.j2
- [ ] Modify `nikita/pipeline/templates/system_prompt.j2`
- [ ] Insert SECTION 3.5 between Section 3 (~line 119) and Section 4 (~line 122)
- [ ] Template renders: behavioral_guidance, emotional_tone, topics_to_encourage, topics_to_avoid
- [ ] When `psyche_state` is None/falsy: render empty string (zero tokens)
- [ ] When populated: ~150 tokens
- **File**: `nikita/pipeline/templates/system_prompt.j2`
- **Test**: `tests/pipeline/test_psyche_prompt.py` (created in T22)
- **AC**: AC-5.1, AC-5.2, AC-5.3, AC-5.4
- **Est**: 0.5h

### T20: Prompt Builder — Pass psyche_state to Template
- [ ] Modify `nikita/pipeline/stages/prompt_builder.py`
- [ ] Include `psyche_state=ctx.psyche_state` in Jinja2 template context dict
- **File**: `nikita/pipeline/stages/prompt_builder.py`
- **Test**: `tests/pipeline/test_psyche_prompt.py` (created in T22)
- **AC**: AC-5.1, AC-5.5
- **Est**: 0.25h

### T21: Psyche Briefing via @agent.instructions
- [ ] Modify `nikita/agents/text/agent.py`
- [ ] Add `add_psyche_briefing(ctx)` as `@agent.instructions` handler
- [ ] Returns formatted briefing string from `ctx.deps.psyche_state`
- [ ] Returns empty string if `generated_prompt` is set (pipeline L3 already included)
- [ ] Returns empty string if `psyche_state` is None
- **File**: `nikita/agents/text/agent.py`
- **Test**: `tests/agents/psyche/test_integration.py` (created in T22)
- **AC**: AC-4.2, AC-5.2
- **Est**: 0.5h

### T22: Tests — Integration
- [ ] Create `tests/agents/psyche/test_integration.py`: handler reads psyche before agent call, graceful degradation on DB failure, flag OFF = no psyche read, trigger routing dispatches correct tier
- [ ] Create `tests/pipeline/test_psyche_prompt.py`: L3 renders ~150 tokens when populated, L3 renders empty when None, psyche_state passed through prompt builder, @agent.instructions injection
- [ ] Minimum 12 test cases across both files
- **File**: `tests/agents/psyche/test_integration.py`, `tests/pipeline/test_psyche_prompt.py`
- **AC**: AC-4.1, AC-4.3, AC-4.4, AC-5.1, AC-5.2, AC-5.3, AC-5.4, AC-5.5
- **Est**: 1.5h

---

## Phase 6: Cost Control (US-7)

### T23: Token Tracking + Cost Monitoring
- [ ] Modify `nikita/agents/psyche/agent.py`: ensure all generate/quick/deep functions return token_count
- [ ] Modify `nikita/agents/psyche/batch.py`: log token count per generation to DB via upsert
- [ ] Add structured logging: `[PSYCHE] model=sonnet tokens=450 user_id=xxx tier=batch|quick|deep`
- **File**: `nikita/agents/psyche/agent.py`, `nikita/agents/psyche/batch.py`
- **Test**: `tests/agents/psyche/test_cost_control.py` (created in T24)
- **AC**: AC-7.1, AC-7.4, AC-1.6
- **Est**: 0.5h

### T24: Tests — Cost Control
- [ ] Create `tests/agents/psyche/test_cost_control.py`
- [ ] Test Sonnet is default model for batch generation
- [ ] Test circuit breaker enforces 5/user/day limit
- [ ] Test token count logged to DB on each generation
- [ ] Test model switch via `psyche_model` setting
- [ ] Minimum 6 test cases
- **File**: `tests/agents/psyche/test_cost_control.py`
- **AC**: AC-7.1, AC-7.2, AC-7.3, AC-7.4
- **Est**: 0.5h

---

## Phase 7: E2E

### T25: E2E — Full Psyche Flow
- [ ] Create `tests/e2e/test_psyche_e2e.py`
- [ ] Flow 1: Create user → batch generates PsycheState → verify DB row with all 8 fields
- [ ] Flow 2: Simulate message → psyche read → L3 injected in system prompt
- [ ] Flow 3: Trigger routing — default message → Tier 1 (cached read), emotional message → Tier 2
- [ ] Flow 4: Feature flag OFF → no psyche read, no L3, batch skips
- [ ] Use `httpx.ASGITransport` pattern (no Cloud Run needed)
- [ ] Minimum 6 test cases
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
