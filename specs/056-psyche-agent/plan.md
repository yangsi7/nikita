# Plan: Spec 056 — Psyche Agent

**Spec**: `specs/056-psyche-agent/spec.md` | **Wave**: B | **Tasks**: 25 | **Effort**: ~21h (+15% buffer)

---

## 1. Summary

This plan implements a Psyche Agent that generates and maintains a per-user PsycheState model capturing Nikita's psychological disposition. Four layers: (1) PsycheState Pydantic model + SQLAlchemy model + Supabase `psyche_states` table, (2) Pydantic AI agent producing structured PsycheState output, (3) 3-tier trigger detector routing messages to cached reads / Sonnet quick-analysis / Opus deep-analysis, (4) conversation integration via Layer 3 in system_prompt.j2. All gated behind `psyche_agent_enabled` feature flag (default OFF).

---

## 2. Implementation Phases

### Phase 1: Data Layer (US-2, US-6)

**T1.1 — PsycheState Pydantic model**
- **Create**: `nikita/agents/psyche/__init__.py`, `nikita/agents/psyche/models.py`
- Define `PsycheState(BaseModel)` with 8 validated fields (Literal types for enums, `Field(ge=0, le=1)` for vulnerability_level, `max_length=3` for topic lists). Add `@classmethod default()` for first-time users.
- **AC**: AC-2.1, AC-2.2, AC-2.3, AC-2.4 | **Effort**: 0.5h | **Deps**: None

**T1.2 — SQLAlchemy model for psyche_states**
- **Create**: `nikita/db/models/psyche_state.py` | **Modify**: `nikita/db/models/__init__.py`
- `PsycheStateRecord(Base, UUIDMixin, TimestampMixin)` with `user_id` (UUID FK UNIQUE), `state` (JSONB), `generated_at`, `model` (Text), `token_count` (Integer). Follows `ReadyPrompt` model pattern.
- **AC**: AC-6.1 | **Effort**: 0.5h | **Deps**: T1.1

**T1.3 — Supabase migration: table + RLS + index**
- Execute via Supabase MCP. CREATE TABLE, btree index on user_id, RLS (user SELECT own, service_role ALL). SQL from spec.md Technical Design.
- **AC**: AC-6.1, AC-6.2, AC-6.3 | **Effort**: 0.5h | **Deps**: T1.2

**T1.4 — PsycheStateRepository**
- **Create**: `nikita/db/repositories/psyche_state_repository.py`
- Extends `BaseRepository[PsycheStateRecord]`. Methods: `get_current(user_id)` (single JSONB read), `upsert(user_id, state, model, token_count)` (INSERT ON CONFLICT UPDATE). Follows `ReadyPromptRepository` pattern.
- **AC**: AC-4.4, AC-6.1 | **Effort**: 0.5h | **Deps**: T1.2

**T1.5 — Tests: Model + repository**
- **Create**: `tests/agents/psyche/test_models.py`, `tests/db/repositories/test_psyche_state_repository.py`
- All 8 field validations, default state, JSON round-trip. Repository: get_current (None for missing), upsert creates/updates. Async mock session pattern.
- **AC**: AC-2.1-AC-2.4 | **Effort**: 1h | **Deps**: T1.1, T1.4

### Phase 2: Psyche Agent Core (US-1)

**T2.1 — PsycheDeps dataclass**
- **Create**: `nikita/agents/psyche/deps.py`
- Fields: `user_id: UUID`, `score_history: list[dict]`, `emotional_states: list[dict]`, `life_events: list[dict]`, `npc_interactions: list[dict]`, `current_chapter: int = 1`. Follows `NikitaDeps` pattern.
- **AC**: AC-1.2 | **Effort**: 0.5h | **Deps**: T1.1

**T2.2 — Psyche agent (structured output)**
- **Create**: `nikita/agents/psyche/agent.py`
- Pydantic AI `Agent[PsycheDeps, PsycheState]` with `output_type=PsycheState`. Model from `settings.psyche_model`. System instructions describe Nikita's psychology. `@agent.instructions` injects PsycheDeps context. Lazy singleton via `@lru_cache`. Follows `_create_nikita_agent()` pattern.
- Key functions: `generate_psyche_state(deps) -> tuple[PsycheState, int]`
- **AC**: AC-1.1, AC-1.3, AC-1.6 | **Effort**: 1.5h | **Deps**: T1.1, T2.1

**T2.3 — Feature flag: psyche_agent_enabled + psyche_model**
- **Modify**: `nikita/config/settings.py` (~line 148, after conflict_temperature_enabled)
- Add `psyche_agent_enabled: bool = False` and `psyche_model: str = "anthropic:claude-sonnet-4-5-20250929"`. Add convenience `is_psyche_agent_enabled()` in `__init__.py`.
- **AC**: AC-6.6, AC-7.1, AC-7.2 | **Effort**: 0.25h | **Deps**: None

**T2.4 — Tests: Agent generation**
- **Create**: `tests/agents/psyche/test_agent.py`
- Structured output validation, token count tracking, configurable model. Mock Pydantic AI agent run.
- **AC**: AC-1.1, AC-1.3, AC-1.6 | **Effort**: 1h | **Deps**: T2.2

### Phase 3: Batch Job (US-1, US-6)

**T3.1 — Batch orchestration module**
- **Create**: `nikita/agents/psyche/batch.py`
- `run_psyche_batch() -> dict` gets active users, loads 48h of score_history/emotional_states/life_events/NPC interactions per user, calls `generate_psyche_state()`, upserts via repository. Per-user try/except + 30s `asyncio.wait_for` timeout.
- **AC**: AC-1.1, AC-1.2, AC-1.4, AC-1.5 | **Effort**: 1.5h | **Deps**: T1.4, T2.2

**T3.2 — Task endpoint: /tasks/psyche-batch**
- **Modify**: `nikita/api/routes/tasks.py`, `nikita/db/models/job_execution.py` (add `PSYCHE_BATCH`)
- `@router.post("/psyche-batch")` with `verify_task_secret`, `JobExecutionRepository` tracking. Guards on feature flag. Follows `/decay` endpoint pattern exactly.
- **AC**: AC-6.4, AC-6.5, AC-6.6 | **Effort**: 1h | **Deps**: T3.1

**T3.3 — Tests: Batch + endpoint**
- **Create**: `tests/agents/psyche/test_batch.py`, `tests/api/routes/test_tasks_psyche.py`
- Multi-user processing, single-user failure isolation, 30s timeout, flag OFF skips. Endpoint: auth, job logging, response format.
- **AC**: AC-1.4, AC-1.5, AC-6.5, AC-6.6 | **Effort**: 1.5h | **Deps**: T3.1, T3.2

### Phase 4: Trigger Detector (US-3)

**T4.1 — Trigger detection module**
- **Create**: `nikita/agents/psyche/trigger.py`
- `TriggerTier` enum (CACHED=1, QUICK=2, DEEP=3). `detect_trigger_tier(message, user, score_delta, conflict_state, is_first_message_today) -> TriggerTier` — pure function, rule-based, <5ms.
- Tier 3 triggers: horseman in conflict_state, boss_fight status, explicit emotional disclosure keywords.
- Tier 2 triggers: first_message_today, score_delta < -5, moderate emotional keywords.
- Tier 1: everything else (default).
- `check_tier3_circuit_breaker(user_id, session) -> bool` — max 5/user/day.
- **AC**: AC-3.1-AC-3.6 | **Effort**: 1.5h | **Deps**: T1.1

**T4.2 — Quick analysis (Tier 2) + deep analysis (Tier 3)**
- **Modify**: `nikita/agents/psyche/agent.py`
- Add `quick_analyze(deps, message, session) -> tuple[PsycheState, int]` (Sonnet, ~500 input tokens) and `deep_analyze(deps, message, session) -> tuple[PsycheState, int]` (Opus). Both upsert to DB.
- **AC**: AC-3.2, AC-3.3, AC-7.3 | **Effort**: 1h | **Deps**: T2.2, T4.1

**T4.3 — Tests: Trigger detector + circuit breaker**
- **Create**: `tests/agents/psyche/test_trigger.py`
- All 6 trigger conditions -> correct tier. Circuit breaker blocks at 5/day. Default -> Tier 1. <5ms benchmark.
- **AC**: AC-3.1-AC-3.6, AC-7.3 | **Effort**: 1.5h | **Deps**: T4.1, T4.2

### Phase 5: Conversation Integration (US-4, US-5)

**T5.1 — Add psyche_state to NikitaDeps**
- **Modify**: `nikita/agents/text/deps.py` — add `psyche_state: dict | None = None` after `session` field.
- **AC**: AC-4.2 | **Effort**: 0.25h | **Deps**: None

**T5.2 — Add psyche_state to PipelineContext**
- **Modify**: `nikita/pipeline/models.py` — add `psyche_state: dict | None = None` after `nikita_daily_events` (~line 92).
- **AC**: AC-5.5 | **Effort**: 0.25h | **Deps**: None

**T5.3 — Pre-conversation psyche read in message handler**
- **Modify**: `nikita/platforms/telegram/message_handler.py` (~line 225, before `text_agent_handler.handle()`)
- If `psyche_agent_enabled`: read via `PsycheStateRepository.get_current()`, run trigger detector, Tier 2/3 -> analysis. Pass dict to `NikitaDeps.psyche_state`. Wrapped in try/except for graceful degradation (AC-4.3).
- **AC**: AC-4.1, AC-4.3, AC-4.4 | **Effort**: 1h | **Deps**: T1.4, T4.1, T5.1

**T5.4 — Prompt Layer 3 in system_prompt.j2**
- **Modify**: `nikita/pipeline/templates/system_prompt.j2` — insert SECTION 3.5 between Section 3 (line ~119) and Section 4 (line ~122). Renders behavioral_guidance, emotional_tone, topics_to_encourage, topics_to_avoid when `psyche_state` is truthy. Empty when None. ~150 tokens.
- **AC**: AC-5.1, AC-5.2, AC-5.3, AC-5.4 | **Effort**: 0.5h | **Deps**: T5.2

**T5.5 — Prompt builder: pass psyche_state to template**
- **Modify**: `nikita/pipeline/stages/prompt_builder.py` — include `psyche_state=ctx.psyche_state` in Jinja2 template context dict.
- **AC**: AC-5.1, AC-5.5 | **Effort**: 0.25h | **Deps**: T5.2, T5.4

**T5.6 — Psyche briefing via @agent.instructions**
- **Modify**: `nikita/agents/text/agent.py` — add `add_psyche_briefing(ctx)` returning formatted briefing from `ctx.deps.psyche_state`. Returns empty if `generated_prompt` is set (pipeline L3 already included) or if psyche_state is None.
- **AC**: AC-4.2, AC-5.2 | **Effort**: 0.5h | **Deps**: T5.1

**T5.7 — Tests: Integration**
- **Create**: `tests/agents/psyche/test_integration.py`, `tests/pipeline/test_psyche_prompt.py`
- Handler reads psyche before agent call. Graceful degradation on failure. L3 ~150 tokens populated / empty when None. @agent.instructions injection. Flag OFF = no read.
- **AC**: AC-4.1, AC-4.3, AC-4.4, AC-5.1-AC-5.5 | **Effort**: 1.5h | **Deps**: T5.3, T5.4, T5.6

### Phase 6: Cost Control (US-7)

**T6.1 — Token tracking + cost monitoring**
- **Modify**: `nikita/agents/psyche/agent.py`, `nikita/agents/psyche/batch.py`
- Log token count per generation in DB. Structured logging: `[PSYCHE] model=sonnet tokens=450 user_id=xxx tier=batch`.
- **AC**: AC-7.1, AC-7.4, AC-1.6 | **Effort**: 0.5h | **Deps**: T2.2, T3.1

**T6.2 — Tests: Cost control**
- **Create**: `tests/agents/psyche/test_cost_control.py`
- Sonnet default, circuit breaker 5/day, token logging, model switch.
- **AC**: AC-7.1-AC-7.4 | **Effort**: 0.5h | **Deps**: T6.1

### Phase 7: E2E

**T7.1 — E2E: Full psyche flow**
- **Create**: `tests/e2e/test_psyche_e2e.py`
- Create user -> batch generates state -> simulate message -> psyche read -> L3 in prompt -> trigger routing. Uses `httpx.ASGITransport` pattern.
- **AC**: AC-1.1, AC-3.1, AC-4.1, AC-5.1 | **Effort**: 1.5h | **Deps**: All

---

## 3. Dependency Graph

```
T1.1 ─────┬──→ T1.2 ──→ T1.3
           │          └──→ T1.4 ──→ T1.5
           │                    └──→ T3.1 ──→ T3.2 ──→ T3.3
           ├──→ T2.1 ──→ T2.2 ──→ T2.4
           │               └──→ T4.2
           └──→ T4.1 ──→ T4.2 ──→ T4.3
                    └──→ T5.3

T2.3 (settings) ── independent, do first
T5.1 (NikitaDeps), T5.2 (PipelineContext) ── independent
T5.4 depends on T5.2 | T5.5 depends on T5.2+T5.4
T5.6 depends on T5.1 | T5.3 depends on T1.4+T4.1+T5.1
T6.1 depends on T2.2+T3.1 | T7.1 depends on all
```

**Critical path**: T1.1 -> T1.2 -> T1.4 -> T3.1 -> T3.2 -> T5.3 -> T5.7 -> T7.1

**Parallelizable**: T2.3 first (independent) | T5.1+T5.2 alongside Phase 1-3 | T4.1 alongside T2.2 | T5.4 alongside T5.6

---

## 4. Files Summary

### Create (8 source + 11 test)
| File | Task | Purpose |
|------|------|---------|
| `nikita/agents/psyche/__init__.py` | T1.1 | Package + `is_psyche_agent_enabled()` |
| `nikita/agents/psyche/models.py` | T1.1 | PsycheState (8 fields) |
| `nikita/agents/psyche/deps.py` | T2.1 | PsycheDeps dataclass |
| `nikita/agents/psyche/agent.py` | T2.2 | Pydantic AI agent + generate/quick/deep |
| `nikita/agents/psyche/batch.py` | T3.1 | Batch orchestration |
| `nikita/agents/psyche/trigger.py` | T4.1 | 3-tier trigger detector |
| `nikita/db/models/psyche_state.py` | T1.2 | SQLAlchemy model |
| `nikita/db/repositories/psyche_state_repository.py` | T1.4 | get_current + upsert |

### Modify (10)
| File | Task | Change |
|------|------|--------|
| `nikita/config/settings.py` | T2.3 | +`psyche_agent_enabled`, `psyche_model` |
| `nikita/db/models/__init__.py` | T1.2 | +import PsycheStateRecord |
| `nikita/db/models/job_execution.py` | T3.2 | +`PSYCHE_BATCH` enum value |
| `nikita/agents/text/deps.py` | T5.1 | +`psyche_state: dict \| None` |
| `nikita/agents/text/agent.py` | T5.6 | +`add_psyche_briefing` instructions |
| `nikita/pipeline/models.py` | T5.2 | +`psyche_state` field |
| `nikita/pipeline/stages/prompt_builder.py` | T5.5 | +psyche_state in template ctx |
| `nikita/pipeline/templates/system_prompt.j2` | T5.4 | +Section 3.5 L3 block |
| `nikita/platforms/telegram/message_handler.py` | T5.3 | +psyche read before agent |
| `nikita/api/routes/tasks.py` | T3.2 | +`/psyche-batch` endpoint |

---

## 5. Risk Mitigations

| Risk | Mitigation |
|------|------------|
| Agent returns invalid structured output | PsycheState validator + `default()` fallback. L3 renders empty on None |
| Batch exceeds 30s/user | `asyncio.wait_for(timeout=30)` + isolated try/except per user |
| Tier 3 Opus cost spiral | Circuit breaker: 5/user/day hardcoded. Structured logging |
| Psyche read adds latency | Tier 1 = single JSONB read <50ms. No LLM on hot path |
| Flag OFF but code executes | Gate at 3 points: handler, batch endpoint, template |
| L3 exceeds 150 tokens | Minimal template. behavioral_guidance validated ~50 words |

---

## 6. Effort Summary

| Phase | Tasks | Hours |
|-------|-------|-------|
| 1: Data Layer | T1.1-T1.5 | 3.0h |
| 2: Agent Core | T2.1-T2.4 | 3.25h |
| 3: Batch Job | T3.1-T3.3 | 4.0h |
| 4: Trigger Detector | T4.1-T4.3 | 4.0h |
| 5: Integration | T5.1-T5.7 | 4.25h |
| 6: Cost Control | T6.1-T6.2 | 1.0h |
| 7: E2E | T7.1 | 1.5h |
| **Total** | **25 tasks** | **~21h** |

~40% test coverage overhead. +15% buffer for integration = **~24h total**.
