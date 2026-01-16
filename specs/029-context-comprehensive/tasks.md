# Tasks: Spec 029 - Comprehensive Context System

**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)
**Total Tasks**: 31 | **Completed**: 31 | **Status**: COMPLETE ✅

---

## Phase A: Memory Retrieval Enhancement (US-1) ✅ COMPLETE

### T-A1: Expand get_user_facts() to Query All 3 Graphs
- **Status**: [x] Complete
- **File**: `nikita/meta_prompts/service.py:296`
- **ACs**:
  - [x] AC-A1.1: Method accepts `graph_types` parameter defaulting to `["user", "relationship", "nikita"]`
  - [x] AC-A1.2: Queries all 3 graphs via `memory.search_memory()`
  - [x] AC-A1.3: Aggregates results from all graphs into single list
  - [x] AC-A1.4: Respects `limit` parameter per graph (default 50)
  - [x] AC-A1.5: Unit test verifies multi-graph query

### T-A2: Add Relationship Episode Loading
- **Status**: [x] Complete
- **File**: `nikita/meta_prompts/service.py`
- **ACs**:
  - [x] AC-A2.1: New method `_get_relationship_episodes(user_id, limit=10)` created
  - [x] AC-A2.2: Queries relationship_graph for significant episodes
  - [x] AC-A2.3: Returns list of Episode objects with timestamp, description, emotional_impact
  - [x] AC-A2.4: Episodes sorted by recency (most recent first)
  - [x] AC-A2.5: Unit test verifies episode retrieval

### T-A3: Add Nikita Life Event Loading
- **Status**: [x] Complete
- **File**: `nikita/meta_prompts/service.py`
- **ACs**:
  - [x] AC-A3.1: New method `_get_nikita_events(limit=10)` created
  - [x] AC-A3.2: Queries nikita_graph for recent events
  - [x] AC-A3.3: Returns list of Event objects with timestamp, activity, mood_impact
  - [x] AC-A3.4: Events from last 7 days prioritized
  - [x] AC-A3.5: Unit test verifies event retrieval

### T-A4: Add Weekly Summary Loading
- **Status**: [x] Complete
- **File**: `nikita/meta_prompts/service.py`
- **ACs**:
  - [x] AC-A4.1: New method `_get_weekly_summaries(user_id, weeks=4)` created
  - [x] AC-A4.2: Retrieves conversation summaries from last N weeks
  - [x] AC-A4.3: Returns list of Summary objects with week_start, highlights, themes
  - [x] AC-A4.4: Summaries include key topics and emotional moments
  - [x] AC-A4.5: Unit test verifies summary retrieval

### T-A5: Expand ContextPackage Model
- **Status**: [x] Complete
- **File**: `nikita/meta_prompts/models.py`
- **ACs**:
  - [x] AC-A5.1: Add `relationship_episodes: list[Episode]` field
  - [x] AC-A5.2: Add `nikita_events: list[Event]` field
  - [x] AC-A5.3: Add `weekly_summaries: list[Summary]` field
  - [x] AC-A5.4: All fields have proper type hints and defaults
  - [x] AC-A5.5: Serialization to context_snapshot works

### T-A6: Update _load_context() with All Data Sources
- **Status**: [x] Complete
- **File**: `nikita/meta_prompts/service.py:320`
- **ACs**:
  - [x] AC-A6.1: Calls `_get_relationship_episodes()` and adds to context
  - [x] AC-A6.2: Calls `_get_nikita_events()` and adds to context
  - [x] AC-A6.3: Calls `_get_weekly_summaries()` and adds to context
  - [x] AC-A6.4: All data loaded in parallel where possible
  - [x] AC-A6.5: Integration test verifies full context loading

### T-A7: Memory Retrieval Performance Test
- **Status**: [x] Complete
- **File**: `tests/meta_prompts/test_performance.py`
- **ACs**:
  - [x] AC-A7.1: Test measures memory retrieval time
  - [x] AC-A7.2: P95 latency under 500ms for all graphs
  - [x] AC-A7.3: Test runs with realistic data volume
  - [x] AC-A7.4: Performance regression test added to CI

---

## Phase B: Humanization Pipeline Wiring (US-2) ✅ COMPLETE

### T-B1: Replace OLD Post-Processor Import
- **Status**: [x] Complete
- **File**: `nikita/api/routes/tasks.py`
- **ACs**:
  - [x] AC-B1.1: Remove `from nikita.context.post_processor import PostProcessor`
  - [x] AC-B1.2: Add `from nikita.post_processing import PostProcessingPipeline`
  - [x] AC-B1.3: Update all references from `PostProcessor` to `PostProcessingPipeline`
  - [x] AC-B1.4: Existing tests still pass

### T-B2: Wire Life Simulation Engine (022)
- **Status**: [x] Complete
- **File**: `nikita/platforms/telegram/message_handler.py`
- **ACs**:
  - [x] AC-B2.1: Import `from nikita.life_simulation import LifeSimulationEngine`
  - [x] AC-B2.2: Check for daily events before response generation
  - [x] AC-B2.3: Inject Nikita's activities into context
  - [x] AC-B2.4: Integration test verifies life events in prompt

### T-B3: Wire Emotional State Engine (023)
- **Status**: [x] Complete
- **File**: `nikita/platforms/telegram/message_handler.py`
- **ACs**:
  - [x] AC-B3.1: Import `from nikita.emotional_state import EmotionalStateEngine`
  - [x] AC-B3.2: Update 4D mood before response generation
  - [x] AC-B3.3: Mood affects prompt personality layer
  - [x] AC-B3.4: Integration test verifies mood in prompt

### T-B4: Wire Behavioral Engine (024)
- **Status**: [x] Complete
- **File**: `nikita/platforms/telegram/message_handler.py`
- **ACs**:
  - [x] AC-B4.1: Import `from nikita.behavioral import BehavioralEngine`
  - [x] AC-B4.2: Get behavioral instructions before response
  - [x] AC-B4.3: Instructions injected into situational layer
  - [x] AC-B4.4: Integration test verifies behavioral nudges

### T-B5: Wire Text Pattern Processor (026)
- **Status**: [x] Complete
- **File**: `nikita/platforms/telegram/message_handler.py`
- **ACs**:
  - [x] AC-B5.1: Import `from nikita.text_patterns import TextPatternProcessor`
  - [x] AC-B5.2: Apply patterns to response after generation
  - [x] AC-B5.3: Patterns affect emoji usage, message length, timing
  - [x] AC-B5.4: Integration test verifies pattern application

### T-B6: Wire Conflict Generator (027)
- **Status**: [x] Complete
- **File**: `nikita/platforms/telegram/message_handler.py`
- **ACs**:
  - [x] AC-B6.1: Import `from nikita.conflicts import ConflictGenerator`
  - [x] AC-B6.2: Check conflict triggers before response
  - [x] AC-B6.3: Apply conflict modifiers to prompt when triggered
  - [x] AC-B6.4: Integration test verifies conflict behavior

### T-B7: Wire Touchpoint Scheduler (025)
- **Status**: [x] Complete
- **File**: `nikita/platforms/telegram/bot.py`
- **ACs**:
  - [x] AC-B7.1: Import `from nikita.touchpoints import TouchpointScheduler`
  - [x] AC-B7.2: Register scheduler on bot startup
  - [x] AC-B7.3: Scheduler triggers Nikita-initiated messages
  - [x] AC-B7.4: Integration test verifies proactive messaging

### T-B8: Humanization Pipeline E2E Test
- **Status**: [x] Complete
- **File**: `tests/platforms/telegram/test_humanization_e2e.py`
- **ACs**:
  - [x] AC-B8.1: Test verifies all 7 modules called in order
  - [x] AC-B8.2: Test verifies life events in context
  - [x] AC-B8.3: Test verifies emotional state in context
  - [x] AC-B8.4: Test verifies behavioral instructions applied
  - [x] AC-B8.5: Test verifies text patterns applied

---

## Phase C: Token Budget Expansion (US-3) ✅ COMPLETE

### T-C1: Expand Base Persona Template
- **Status**: [x] Complete
- **File**: `nikita/meta_prompts/templates/base_persona.md`
- **ACs**:
  - [x] AC-C1.1: Template expanded to 800 tokens (from 400)
  - [x] AC-C1.2: Added personality detail section
  - [x] AC-C1.3: Added speaking style examples
  - [x] AC-C1.4: Added boundary definitions
  - [x] AC-C1.5: Token count validated

### T-C2: Expand Chapter Behavior Template
- **Status**: [x] Complete
- **File**: `nikita/meta_prompts/templates/chapter_behavior.md`
- **ACs**:
  - [x] AC-C2.1: Template expanded to 600 tokens (from 300)
  - [x] AC-C2.2: Added chapter-specific behaviors per chapter (1-5)
  - [x] AC-C2.3: Added threshold descriptions
  - [x] AC-C2.4: Added boss encounter context
  - [x] AC-C2.5: Token count validated

### T-C3: Expand Emotional State Template
- **Status**: [x] Complete
- **File**: `nikita/meta_prompts/templates/emotional_state.md`
- **ACs**:
  - [x] AC-C3.1: Template expanded to 500 tokens (from 200)
  - [x] AC-C3.2: Added 4D mood descriptions (joy, sadness, fear, anger)
  - [x] AC-C3.3: Added life event impact descriptions
  - [x] AC-C3.4: Added energy level effects
  - [x] AC-C3.5: Token count validated

### T-C4: Expand Situational Template
- **Status**: [x] Complete
- **File**: `nikita/meta_prompts/templates/situational.md`
- **ACs**:
  - [x] AC-C4.1: Template expanded to 400 tokens (from 200)
  - [x] AC-C4.2: Added time-of-day context variations
  - [x] AC-C4.3: Added gap duration effect descriptions
  - [x] AC-C4.4: Added engagement state behaviors (6 states)
  - [x] AC-C4.5: Token count validated

### T-C5: Increase Context Limits in Service
- **Status**: [x] Complete
- **File**: `nikita/meta_prompts/service.py`
- **ACs**:
  - [x] AC-C5.1: `MAX_USER_FACTS = 50` (from 5)
  - [x] AC-C5.2: `MAX_THREADS = 10` (from 3)
  - [x] AC-C5.3: `MAX_THOUGHTS = 10` (from 3)
  - [x] AC-C5.4: `MAX_RELATIONSHIP_EPISODES = 10` (new)
  - [x] AC-C5.5: `MAX_NIKITA_EVENTS = 10` (new)

### T-C6: Implement Tiered Context Loading
- **Status**: [x] Complete
- **File**: `nikita/meta_prompts/service.py`
- **ACs**:
  - [x] AC-C6.1: Tier 1 (Critical): Always loaded - user profile, current chapter, scores
  - [x] AC-C6.2: Tier 2 (Recent): Last 7 days - facts, events, threads
  - [x] AC-C6.3: Tier 3 (Historical): On demand - older summaries, episodes
  - [x] AC-C6.4: Tiered loading reduces cold-path tokens by 30%+
  - [x] AC-C6.5: Unit test verifies tier selection logic

### T-C7: Token Counting and Validation
- **Status**: [x] Complete
- **File**: `nikita/meta_prompts/service.py`
- **ACs**:
  - [x] AC-C7.1: Token count calculated per layer
  - [x] AC-C7.2: Total tokens logged to `generated_prompts.context_snapshot`
  - [x] AC-C7.3: Warning logged if total exceeds 12,000 tokens
  - [x] AC-C7.4: Test validates 10,000+ token prompts generated

---

## Phase D: Voice-Text Parity (US-4) ✅ COMPLETE

### T-D1: Expand get_context Server Tool Response
- **Status**: [x] Complete
- **File**: `nikita/agents/voice/server_tools.py`
- **ACs**:
  - [x] AC-D1.1: Add `secureness` field (float 0-1)
  - [x] AC-D1.2: Add full `vice_profile` (all 8 categories)
  - [x] AC-D1.3: Add `hours_since_last_contact` (float)
  - [x] AC-D1.4: Add `nikita_activity` (string, last 24h)
  - [x] AC-D1.5: Add `engagement_state` (enum)

### T-D2: Increase User Facts in Voice Context
- **Status**: [x] Complete
- **File**: `nikita/agents/voice/server_tools.py`
- **ACs**:
  - [x] AC-D2.1: User facts limit increased from 3 to 50
  - [x] AC-D2.2: Facts include all 3 graph types
  - [x] AC-D2.3: Facts sorted by relevance/recency
  - [x] AC-D2.4: Test verifies 50 facts returned

### T-D3: Add Relationship and Thread Context to Voice
- **Status**: [x] Complete
- **File**: `nikita/agents/voice/server_tools.py`
- **ACs**:
  - [x] AC-D3.1: Add `relationship_episodes` field (list)
  - [x] AC-D3.2: Add `active_threads` field (list)
  - [x] AC-D3.3: Add `weekly_summaries` field (list)
  - [x] AC-D3.4: Fields match text agent format

### T-D4: Voice Prompt Logging
- **Status**: [x] Complete
- **File**: `nikita/agents/voice/context.py`
- **ACs**:
  - [x] AC-D4.1: All voice prompts logged to `generated_prompts` table (via skip_logging=False)
  - [x] AC-D4.2: `context_snapshot` includes all new fields
  - [x] AC-D4.3: Logging format matches text agent
  - [x] AC-D4.4: Test verifies voice prompt logging

### T-D5: Update DynamicVariables Model
- **Status**: [x] Complete
- **File**: `nikita/agents/voice/models.py`
- **ACs**:
  - [x] AC-D5.1: Model includes all new context fields (secureness, hours_since_last, day_of_week, nikita_activity)
  - [x] AC-D5.2: Field types match server tool response
  - [x] AC-D5.3: Serialization to ElevenLabs format works
  - [x] AC-D5.4: Test validates model schema (18 tests passing)

### T-D6: Voice-Text Parity E2E Test
- **Status**: [x] Complete
- **File**: `tests/agents/voice/test_dynamic_vars.py`, `tests/agents/voice/test_server_tools.py`
- **ACs**:
  - [x] AC-D6.1: Compare voice context vs text context for same user
  - [x] AC-D6.2: Assert field coverage >= 95% (all fields now match)
  - [x] AC-D6.3: Assert value equivalence for shared fields
  - [x] AC-D6.4: Document any intentional differences (none - full parity achieved)

---

## Progress Summary

| Phase | User Story | Tasks | Completed | Status |
|-------|------------|-------|-----------|--------|
| A | US-1: Deep Memory | 7 | 7 | ✅ Complete |
| B | US-2: Humanization | 8 | 8 | ✅ Complete |
| C | US-3: Token Budget | 7 | 7 | ✅ Complete |
| D | US-4: Voice Parity | 6 | 6 | ✅ Complete |
| **Total** | | **31** | **31** | **✅ COMPLETE** |

---

## Implementation Summary (2026-01-16)

### Phase A: Memory Retrieval Enhancement
- Extended `_load_context()` to query all 3 Graphiti graphs (user, relationship, nikita)
- Added relationship episodes, nikita events, and weekly summaries
- User facts limit increased from 5 → 50

### Phase B: Humanization Pipeline Wiring
- Wired all 7 humanization specs (021-027) into production flows
- Integrated LifeSimulationEngine, EmotionalStateEngine, BehavioralInstructions
- Enabled text patterns and conflict generation systems

### Phase C: Token Budget Expansion
- Expanded token budget from ~4K to 10K+
- Implemented tiered context loading (Critical → Recent → Historical)
- Added token counting and validation

### Phase D: Voice-Text Parity
- Added all missing context fields to DynamicVariables model
- Updated server tools with 50 user facts, relationship context, threads
- Added helper methods matching meta_prompts/service.py implementation
- 54 core tests passing (18 + 21 + 15)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-15 | Initial task breakdown |
