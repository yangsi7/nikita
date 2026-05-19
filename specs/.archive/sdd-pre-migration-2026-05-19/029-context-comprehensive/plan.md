# Implementation Plan: Spec 029 - Comprehensive Context System

**Spec**: [spec.md](./spec.md)
**Status**: PLANNING
**Estimated Effort**: 8-12 hours (AI agent time)

---

## Implementation Phases

### Phase A: Memory Retrieval Enhancement (US-1)
**Priority**: P0 | **Effort**: 2-3 hours

#### A1: Expand Graph Querying
**File**: `nikita/meta_prompts/service.py`

1. Modify `get_user_facts()` at line 296:
   - Change from single graph query to multi-graph
   - Add `graph_types` parameter
   - Increase limit from 5 to 50

2. Modify `_load_context()` at line 320:
   - Add relationship episode loading
   - Add Nikita life event loading
   - Add weekly summary loading

3. Create new helper methods:
   - `_get_relationship_episodes(user_id, limit=10)`
   - `_get_nikita_events(limit=10)`
   - `_get_weekly_summaries(user_id, weeks=4)`

#### A2: Memory Search Enhancement
**File**: `nikita/memory/graphiti_client.py`

1. Ensure `search_memory()` supports multiple graph_types
2. Add time_range filtering
3. Implement result aggregation across graphs

#### A3: Context Model Updates
**File**: `nikita/meta_prompts/models.py`

1. Expand `ContextPackage` model:
   - `relationship_episodes: list[Episode]`
   - `nikita_events: list[Event]`
   - `weekly_summaries: list[Summary]`

---

### Phase B: Humanization Pipeline Wiring (US-2)
**Priority**: P0 | **Effort**: 3-4 hours

#### B1: Production Integration Point
**File**: `nikita/api/routes/tasks.py`

1. Replace OLD post_processor import:
```python
# REMOVE
from nikita.context.post_processor import PostProcessor

# ADD
from nikita.post_processing import PostProcessingPipeline
```

2. Wire pipeline after response generation:
```python
pipeline = PostProcessingPipeline()
processed = await pipeline.process(response, context)
```

#### B2: Message Handler Integration
**File**: `nikita/platforms/telegram/message_handler.py`

1. Import new modules:
   - `from nikita.life_simulation import LifeSimulationEngine`
   - `from nikita.emotional_state import EmotionalStateEngine`
   - `from nikita.behavioral import BehavioralEngine`
   - `from nikita.text_patterns import TextPatternProcessor`

2. Add pre-response hooks:
   - Life simulation check (daily events)
   - Emotional state update
   - Behavioral instruction injection

3. Add post-response hooks:
   - Text pattern application
   - Response formatting

#### B3: Conflict Integration
**File**: `nikita/platforms/telegram/message_handler.py`

1. Import: `from nikita.conflicts import ConflictGenerator`
2. Check conflict triggers before response
3. Apply conflict modifiers to prompt

#### B4: Touchpoint Integration
**File**: `nikita/platforms/telegram/bot.py`

1. Import: `from nikita.touchpoints import TouchpointScheduler`
2. Register scheduler on bot startup
3. Handle Nikita-initiated message delivery

---

### Phase C: Token Budget Expansion (US-3)
**Priority**: P1 | **Effort**: 2-3 hours

#### C1: Layer Template Updates
**Directory**: `nikita/meta_prompts/templates/`

1. Expand `base_persona.md`: 400 → 800 tokens
   - Add more personality detail
   - Add speaking style examples
   - Add boundary definitions

2. Expand `chapter_behavior.md`: 300 → 600 tokens
   - Add chapter-specific behaviors
   - Add threshold descriptions
   - Add boss encounter context

3. Expand `emotional_state.md`: 200 → 500 tokens
   - Add 4D mood descriptions
   - Add life event impacts
   - Add energy level effects

4. Expand `situational.md`: 200 → 400 tokens
   - Add time-of-day context
   - Add gap duration effects
   - Add engagement state behaviors

#### C2: Context Injection Scaling
**File**: `nikita/meta_prompts/service.py`

1. Increase context limits:
   - `MAX_USER_FACTS = 50` (from 5)
   - `MAX_THREADS = 10` (from 3)
   - `MAX_THOUGHTS = 10` (from 3)
   - `MAX_RELATIONSHIP_EPISODES = 10` (new)
   - `MAX_NIKITA_EVENTS = 10` (new)

2. Implement tiered loading:
   - Tier 1: Critical context (always loaded)
   - Tier 2: Recent context (last 7 days)
   - Tier 3: Historical context (on demand)

#### C3: Token Counting Validation
**File**: `nikita/meta_prompts/service.py`

1. Add token counting per layer
2. Log total tokens to `generated_prompts.context_snapshot`
3. Add warning if exceeds budget

---

### Phase D: Voice-Text Parity (US-4)
**Priority**: P1 | **Effort**: 2-3 hours

#### D1: Server Tools Enhancement
**File**: `nikita/agents/voice/server_tools.py`

1. Expand `get_context` tool response:
   - Add `secureness` field
   - Add full `vice_profile` (all 8 categories)
   - Add `hours_since_last_contact`
   - Add `nikita_activity`
   - Add `relationship_episodes`
   - Add `active_threads`
   - Add `weekly_summaries`

2. Increase user_facts limit: 3 → 50

3. Add engagement_state field

#### D2: Voice Prompt Logging
**File**: `nikita/agents/voice/service.py`

1. Ensure all voice prompts logged to `generated_prompts` table
2. Include full context_snapshot matching text format

#### D3: Dynamic Variables Sync
**File**: `nikita/agents/voice/models.py`

1. Update `DynamicVariables` model to include all new fields
2. Ensure ElevenLabs dynamic variables match context

---

## Testing Strategy

### Unit Tests (per phase)

| Phase | Test File | New Tests |
|-------|-----------|-----------|
| A | `tests/meta_prompts/test_service.py` | 15 |
| B | `tests/platforms/telegram/test_handler.py` | 20 |
| C | `tests/meta_prompts/test_token_budget.py` | 10 |
| D | `tests/agents/voice/test_server_tools.py` | 12 |

### Integration Tests

1. **Memory flow E2E**: Graph → MetaPromptService → Prompt
2. **Humanization E2E**: All 8 modules → response modification
3. **Voice-text parity**: Compare outputs side-by-side

### Verification

```bash
# Run all tests
source .venv/bin/activate && python -m pytest tests/ -v --tb=short

# Run specific phase tests
python -m pytest tests/meta_prompts/ -v
python -m pytest tests/platforms/telegram/ -v
python -m pytest tests/agents/voice/ -v
```

---

## Rollout Plan

### Stage 1: Local Development
- Implement all phases
- Run full test suite
- Manual testing with test user

### Stage 2: Staging Deployment
- Deploy to Cloud Run (non-production tag)
- E2E test with test Telegram bot
- Verify logs and metrics

### Stage 3: Production Deployment
- Deploy to production
- Monitor token usage
- Monitor memory retrieval latency
- Gradual rollout if needed

---

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| Humanization modules (021-028) | ✅ Complete | 1575+ tests passing |
| MetaPromptService | ✅ Complete | Needs modification |
| Graphiti/Neo4j | ✅ Complete | No changes needed |
| ElevenLabs integration | ✅ Complete | Server tools need update |

---

## Risks

| Risk | Mitigation |
|------|------------|
| Breaking existing tests | Run full suite after each phase |
| Performance regression | Add timing assertions, monitor P95 |
| Token cost spike | Implement tiered loading, monitor usage |
| Voice agent disruption | Test with separate agent ID first |

---

## Success Criteria

Before marking complete:
- [ ] All 4 phases implemented
- [ ] 50+ new tests passing
- [ ] Total test suite green (1800+ tests)
- [ ] Token count verified at 10,000+
- [ ] All 3 graphs queried in production
- [ ] Voice-text parity verified
- [ ] E2E test passing with real conversation
