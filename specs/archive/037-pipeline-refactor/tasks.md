# Tasks: 037-pipeline-refactor

**Plan**: [plan.md](plan.md) | **Total**: 32 | **Completed**: 32 (7 SUPERSEDED by Spec 042)

---

## Progress Summary

| Phase/User Story | Tasks | Done | Status |
|------------------|-------|------|--------|
| Setup | 2 | 2 | ✅ Complete |
| US-1: Pipeline Reliability | 5 | 5 | ✅ Complete |
| US-2: Timeout Handling | 4 | 4 | ✅ Complete |
| US-3: Unified Stage Infrastructure | 12 | 12 | ✅ Complete (T2.16 SUPERSEDED by Spec 042) |
| US-4: Observability | 3 | 3 | ✅ Complete (T3.2, T3.3 SUPERSEDED by Spec 042) |
| US-5: Vice Processing Fix | 1 | 1 | ✅ Complete |
| US-6: Chaos Testing | 2 | 2 | ✅ Complete (T5.2 SUPERSEDED by Spec 042) |
| Finalization | 1 | 1 | ✅ SUPERSEDED by Spec 042 |

### Stage Implementation Summary (11/11 stages complete)

| Stage | File | Tests | Status |
|-------|------|-------|--------|
| IngestionStage | ingestion.py | 5 | ✅ |
| ExtractionStage | extraction.py | 8 | ✅ |
| GraphUpdatesStage | graph_updates.py | 8 | ✅ |
| ViceProcessingStage | vice_processing.py | 11 | ✅ |
| ThreadsStage | threads.py | 8 | ✅ |
| ThoughtsStage | thoughts.py | 7 | ✅ |
| SummaryRollupsStage | summary_rollups.py | 8 | ✅ |
| PsychologyStage | psychology.py | 8 | ✅ |
| NarrativeArcsStage | narrative_arcs.py | 11 | ✅ |
| VoiceCacheStage | voice_cache.py | 8 | ✅ |
| FinalizationStage | finalization.py | 10 | ✅ |
| **Total** | 11 stages | **92** | **Complete** |

---

## Phase 0: Setup

### T0.1: Add Dependencies
- **Status**: [x] Complete
- **Priority**: P0
- **Est**: S | **Deps**: None
- **ACs**:
  - [x] AC-T0.1.1: `tenacity` added to pyproject.toml
  - [x] AC-T0.1.2: `opentelemetry-api` added to pyproject.toml
  - [x] AC-T0.1.3: `opentelemetry-sdk` added to pyproject.toml
  - [x] AC-T0.1.4: `pip install -e .` succeeds

### T0.2: Create Directory Structure
- **Status**: [x] Complete
- **Priority**: P0
- **Est**: S | **Deps**: T0.1
- **ACs**:
  - [x] AC-T0.2.1: `nikita/context/stages/` directory created
  - [x] AC-T0.2.2: `nikita/context/stages/__init__.py` created
  - [x] AC-T0.2.3: `tests/context/stages/` directory created
  - [x] AC-T0.2.4: `tests/context/stages/conftest.py` created

---

## US-1: Pipeline Reliability (P0)

**Story**: As a system operator, I want the post-processing pipeline to complete reliably without resource leaks, so that conversations are processed correctly and system resources aren't exhausted.

### T1.1: Add Context Manager to NikitaMemory [Fixes C-1]
- **Status**: [x] Complete
- **Priority**: P0
- **Est**: M | **Deps**: T0.2
- **File**: `nikita/memory/graphiti_client.py`
- **ACs**:
  - [x] AC-T1.1.1: `NikitaMemory.__aenter__` returns self
  - [x] AC-T1.1.2: `NikitaMemory.__aexit__` closes Neo4j driver
  - [x] AC-T1.1.3: Exceptions during `__aexit__` are logged, not raised
  - [x] AC-T1.1.4: 5 tests pass (test_resource_cleanup.py)

### T1.2: Add Context Manager to ViceService [Fixes C-2]
- **Status**: [x] Complete
- **Priority**: P0
- **Est**: M | **Deps**: T0.2
- **File**: `nikita/engine/vice/service.py`
- **ACs**:
  - [x] AC-T1.2.1: `ViceService.__aenter__` returns self
  - [x] AC-T1.2.2: `ViceService.__aexit__` commits or rollbacks session
  - [x] AC-T1.2.3: Exceptions during `__aexit__` are logged, not raised
  - [x] AC-T1.2.4: 6 tests pass (test_resource_cleanup.py)

### T1.3: Update GraphUpdatesStage to Use Context Manager
- **Status**: [x] Complete
- **Priority**: P0
- **Est**: S | **Deps**: T1.1, T2.7
- **File**: `nikita/context/stages/graph_updates.py`
- **ACs**:
  - [x] AC-T1.3.1: Stage uses `async with get_memory_client(user_id) as memory`
  - [x] AC-T1.3.2: No direct `memory.close()` calls

### T1.4: Update ViceProcessingStage to Use Context Manager
- **Status**: [x] Complete
- **Priority**: P0
- **Est**: S | **Deps**: T1.2, T2.8
- **File**: `nikita/context/stages/vice_processing.py`
- **ACs**:
  - [x] AC-T1.4.1: Stage uses `async with ViceService() as vice_service`
  - [x] AC-T1.4.2: No direct session.close() calls

### T1.5: Resource Leak Integration Test
- **Status**: [x] Complete
- **Priority**: P0
- **Est**: M | **Deps**: T1.3, T1.4
- **File**: `tests/context/stages/test_resource_cleanup.py`
- **ACs**:
  - [x] AC-T1.5.1: Test verifies NikitaMemory closed after exception
  - [x] AC-T1.5.2: Test verifies ViceService closed after exception
  - [x] AC-T1.5.3: 16 tests pass

---

## US-2: Timeout Handling (P0)

**Story**: As a system operator, I want all external calls to have explicit timeouts, so that the pipeline doesn't hang on slow dependencies.

### T2.1: Create CircuitBreaker Class
- **Status**: [x] Complete
- **Priority**: P0
- **Est**: M | **Deps**: T0.2
- **File**: `nikita/context/stages/circuit_breaker.py`
- **ACs**:
  - [x] AC-T2.1.1: CircuitBreaker.call() executes function when CLOSED
  - [x] AC-T2.1.2: CircuitBreaker opens after `failure_threshold` failures
  - [x] AC-T2.1.3: CircuitBreaker transitions to HALF_OPEN after `recovery_timeout`
  - [x] AC-T2.1.4: CircuitBreaker closes after `half_open_max_calls` successes
  - [x] AC-T2.1.5: 10 tests pass (test_circuit_breaker.py)

### T2.2: Create PipelineStage Base Class
- **Status**: [x] Complete
- **Priority**: P0
- **Est**: L | **Deps**: T2.1
- **File**: `nikita/context/stages/base.py`
- **ACs**:
  - [x] AC-T2.2.1: PipelineStage.execute() returns StageResult
  - [x] AC-T2.2.2: Timeout wraps _run() with asyncio.wait_for
  - [x] AC-T2.2.3: Retry uses tenacity with exponential backoff
  - [x] AC-T2.2.4: Logger bound with stage name and conversation_id
  - [x] AC-T2.2.5: Errors recorded in context.stage_errors
  - [x] AC-T2.2.6: 15 tests pass (test_base_stage.py)

### T2.3: Create PipelineContext Dataclass
- **Status**: [x] Complete
- **Priority**: P0
- **Est**: S | **Deps**: T0.2
- **File**: `nikita/context/pipeline_context.py`
- **ACs**:
  - [x] AC-T2.3.1: PipelineContext has conversation_id, user_id, started_at
  - [x] AC-T2.3.2: Optional fields: conversation, extraction_result
  - [x] AC-T2.3.3: record_stage_error() method for error tracking

### T2.4: Configure Structured Logging
- **Status**: [x] Complete
- **Priority**: P1
- **Est**: S | **Deps**: T0.2
- **File**: `nikita/context/logging.py`
- **ACs**:
  - [x] AC-T2.4.1: Logs output as JSON
  - [x] AC-T2.4.2: conversation_id bound to logger
  - [x] AC-T2.4.3: log_stage_start/log_stage_complete helper functions

---

## US-3: Unified Stage Infrastructure (P0)

**Story**: As a developer, I want all pipeline stages to use the same base class, so that I can add/modify stages consistently.

### T2.5: Create IngestionStage
- **Status**: [x] Complete
- **Priority**: P1
- **Est**: M | **Deps**: T2.2, T2.3
- **File**: `nikita/context/stages/ingestion.py`
- **Original**: `post_processor.py:452-474`
- **ACs**:
  - [x] AC-T2.5.1: Stage is_critical = True
  - [x] AC-T2.5.2: timeout_seconds = 10.0
  - [x] AC-T2.5.3: Raises StageError if conversation not found
  - [x] AC-T2.5.4: Raises StageError if messages empty
  - [x] AC-T2.5.5: 5 tests pass (test_ingestion.py)

### T2.6: Create ExtractionStage [Fixes H-1]
- **Status**: [x] Complete
- **Priority**: P0
- **Est**: L | **Deps**: T2.2, T2.1
- **File**: `nikita/context/stages/extraction.py`
- **Original**: `post_processor.py:476-572`
- **ACs**:
  - [x] AC-T2.6.1: is_critical = True
  - [x] AC-T2.6.2: timeout_seconds = 120.0
  - [x] AC-T2.6.3: Uses _llm_circuit_breaker (threshold=3, recovery=120s)
  - [x] AC-T2.6.4: Validates LLM output before returning
  - [x] AC-T2.6.5: ExtractionResult dataclass for structured output

### T2.7: Create GraphUpdatesStage [Fixes H-2, H-7]
- **Status**: [x] Complete
- **Priority**: P0
- **Est**: L | **Deps**: T2.2, T2.1
- **File**: `nikita/context/stages/graph_updates.py`
- **Original**: `post_processor.py:656-744`
- **ACs**:
  - [x] AC-T2.7.1: is_critical = False
  - [x] AC-T2.7.2: timeout_seconds = 90.0
  - [x] AC-T2.7.3: Uses _neo4j_circuit_breaker (threshold=2, recovery=180s)
  - [x] AC-T2.7.4: Uses async context manager for NikitaMemory

### T2.8: Create ViceProcessingStage [Fixes H-4]
- **Status**: [x] Complete
- **Priority**: P1
- **Est**: M | **Deps**: T2.2
- **File**: `nikita/context/stages/vice_processing.py`
- **Original**: `post_processor.py:789-840`
- **ACs**:
  - [x] AC-T2.8.1: is_critical = False
  - [x] AC-T2.8.2: timeout_seconds = 30.0
  - [x] AC-T2.8.3: _extract_exchanges() handles non-alternating messages
  - [x] AC-T2.8.4: Both "assistant" and "nikita" roles recognized
  - [x] AC-T2.8.5: 11 tests pass (test_message_pairing.py)

### T2.9: Create ThreadsStage
- **Status**: [x] Complete
- **Priority**: P1
- **Est**: M | **Deps**: T2.2
- **File**: `nikita/context/stages/threads.py`
- **Original**: `post_processor.py:584-602`
- **ACs**:
  - [x] AC-T2.9.1: is_critical = False
  - [x] AC-T2.9.2: timeout_seconds = 10.0
  - [x] AC-T2.9.3: 8 tests pass (test_threads.py)

### T2.10: Create ThoughtsStage
- **Status**: [x] Complete
- **Priority**: P1
- **Est**: M | **Deps**: T2.2
- **File**: `nikita/context/stages/thoughts.py`
- **Original**: `post_processor.py:604-654`
- **ACs**:
  - [x] AC-T2.10.1: is_critical = False
  - [x] AC-T2.10.2: timeout_seconds = 10.0
  - [x] AC-T2.10.3: 7 tests pass (test_thoughts.py)

### T2.11: Create SummaryRollupsStage
- **Status**: [x] Complete
- **Priority**: P1
- **Est**: M | **Deps**: T2.2
- **File**: `nikita/context/stages/summary_rollups.py`
- **Original**: `post_processor.py:746-787`
- **ACs**:
  - [x] AC-T2.11.1: is_critical = False
  - [x] AC-T2.11.2: timeout_seconds = 15.0
  - [x] AC-T2.11.3: 8 tests pass (test_summary_rollups.py)

### T2.12: Create PsychologyStage
- **Status**: [x] Complete
- **Priority**: P1
- **Est**: M | **Deps**: T2.2
- **File**: `nikita/context/stages/psychology.py`
- **Original**: `post_processor.py:842-940`
- **ACs**:
  - [x] AC-T2.12.1: is_critical = False
  - [x] AC-T2.12.2: timeout_seconds = 30.0
  - [x] AC-T2.12.3: 8 tests pass (test_psychology.py)

### T2.13: Create NarrativeArcsStage
- **Status**: [x] Complete
- **Priority**: P1
- **Est**: M | **Deps**: T2.2
- **File**: `nikita/context/stages/narrative_arcs.py`
- **Original**: `post_processor.py:1005-1116`
- **ACs**:
  - [x] AC-T2.13.1: is_critical = False
  - [x] AC-T2.13.2: timeout_seconds = 20.0
  - [x] AC-T2.13.3: 11 tests pass (test_narrative_arcs.py)

### T2.14: Create VoiceCacheStage
- **Status**: [x] Complete
- **Priority**: P1
- **Est**: S | **Deps**: T2.2
- **File**: `nikita/context/stages/voice_cache.py`
- **Original**: `post_processor.py:1147-1173`
- **ACs**:
  - [x] AC-T2.14.1: is_critical = False
  - [x] AC-T2.14.2: timeout_seconds = 10.0
  - [x] AC-T2.14.3: 8 tests pass (test_voice_cache.py)

### T2.15: Create FinalizationStage
- **Status**: [x] Complete
- **Priority**: P1
- **Est**: S | **Deps**: T2.2
- **File**: `nikita/context/stages/finalization.py`
- **Original**: `post_processor.py:363-450`
- **ACs**:
  - [x] AC-T2.15.1: is_critical = True
  - [x] AC-T2.15.2: timeout_seconds = 10.0
  - [x] AC-T2.15.3: Updates conversation status to 'processed' with force update fallback
  - [x] AC-T2.15.4: 10 tests pass (test_finalization.py)

### T2.16: Slim Down PostProcessor Orchestrator
- **Status**: [x] SUPERSEDED by Spec 042 (unified pipeline orchestrator)
- **Priority**: P1
- **Est**: L | **Deps**: T2.5-T2.15
- **File**: `nikita/context/post_processor.py`
- **ACs**:
  - [ ] AC-T2.16.1: process_conversation() < 100 lines
  - [ ] AC-T2.16.2: Instantiates and executes stages in order
  - [ ] AC-T2.16.3: Critical stage failure stops pipeline
  - [ ] AC-T2.16.4: Non-critical failures logged, continue
  - [ ] AC-T2.16.5: 6 integration tests pass

---

## US-4: Observability (P1)

**Story**: As a system operator, I want structured logging with correlation IDs, so that I can trace issues through the pipeline.

### T3.1: Add OpenTelemetry Spans
- **Status**: [x] Complete
- **Priority**: P2
- **Est**: M | **Deps**: T2.2
- **File**: `nikita/context/stages/base.py`
- **ACs**:
  - [x] AC-T3.1.1: Each stage creates span named `stage.{name}`
  - [x] AC-T3.1.2: Span has conversation_id attribute
  - [x] AC-T3.1.3: Span status set on error

### T3.2: Create /admin/pipeline-health Endpoint
- **Status**: [x] SUPERSEDED by Spec 042 (admin pipeline view)
- **Priority**: P2
- **Est**: M | **Deps**: T2.16
- **File**: `nikita/api/routes/admin.py`
- **ACs**:
  - [ ] AC-T3.2.1: Returns circuit breaker states
  - [ ] AC-T3.2.2: Returns recent stage error counts
  - [ ] AC-T3.2.3: Returns average duration per stage

### T3.3: Thread Resolution Logging [Fixes H-3]
- **Status**: [x] SUPERSEDED by Spec 042 (extraction stage handles threads)
- **Priority**: P1
- **Est**: S | **Deps**: T2.9
- **File**: `nikita/context/stages/threads.py`
- **ACs**:
  - [ ] AC-T3.3.1: Failed thread resolutions logged with error
  - [ ] AC-T3.3.2: Includes thread_id and reason

---

## US-5: Vice Processing Fix (P1)

**Story**: As a player, I want vice signals detected from all message exchanges, so that my vice profile is accurate.

### T4.1: Message Pairing Unit Tests
- **Status**: [x] Complete
- **Priority**: P1
- **Est**: M | **Deps**: T2.8
- **File**: `tests/context/stages/test_message_pairing.py`
- **ACs**:
  - [x] AC-T4.1.1: test_non_alternating_multiple_user_messages
  - [x] AC-T4.1.2: test_nikita_only_messages_skipped
  - [x] AC-T4.1.3: test_role_variants_nikita_and_assistant
  - [x] AC-T4.1.4: test_empty_content_messages_skipped
  - [x] AC-T4.1.5: test_single_message_conversation
  - [x] AC-T4.1.6: test_whitespace_only_content_skipped
  - [x] AC-T4.1.7: 11 tests pass

---

## US-6: Chaos Testing (P1)

**Story**: As a developer, I want chaos tests that simulate failures, so that I can verify pipeline resilience.

### T5.1: Create Chaos Test Infrastructure
- **Status**: [x] Complete
- **Priority**: P1
- **Est**: M | **Deps**: T2.7, T2.6
- **File**: `tests/context/stages/test_chaos.py`
- **ACs**:
  - [x] AC-T5.1.1: test_neo4j_cold_start_timeout (2 tests)
  - [x] AC-T5.1.2: test_llm_rate_limited (2 tests)
  - [x] AC-T5.1.3: test_multiple_stage_failures (2 tests)
  - [x] AC-T5.1.4: test_critical_stage_fail_fast (2 tests)
  - [x] AC-T5.1.5: test_circuit_breaker_state_transitions (4 tests)
  - [x] AC-T5.1.6: 12 tests pass

### T5.2: Create Integration Tests
- **Status**: [x] SUPERSEDED by Spec 042 (190 pipeline tests)
- **Priority**: P1
- **Est**: M | **Deps**: T2.16
- **File**: `tests/context/test_pipeline_integration.py`
- **ACs**:
  - [ ] AC-T5.2.1: Full pipeline E2E test
  - [ ] AC-T5.2.2: Stage isolation test
  - [ ] AC-T5.2.3: 6 tests pass

---

## Finalization

### TD-1: Documentation Sync
- **Status**: [x] SUPERSEDED by Spec 042 (full doc sync complete)
- **Priority**: P0
- **Trigger**: After ALL user stories complete
- **ACs**:
  - [ ] Update `nikita/context/CLAUDE.md`
  - [ ] Update `memory/architecture.md` with new pipeline diagram
  - [ ] Update `event-stream.md` with completion
  - [ ] Update `todos/master-todo.md`

---

## Dependency Graph

```
T0.1 → T0.2 ─┬→ T2.1 → T2.2 → T2.5-T2.15 → T2.16 → T5.1/T5.2
             ├→ T2.3
             ├→ T2.4
             ├→ T1.1 → T1.3 ─┐
             └→ T1.2 → T1.4 ─┴→ T1.5
```

## Parallelization Groups

| Group | Tasks | Reason |
|-------|-------|--------|
| 1 | T1.1, T1.2 | Independent context managers |
| 2 | T2.1, T2.3, T2.4 | Independent infrastructure |
| 3 | T2.5, T2.6, T2.7, T2.8 | Independent stages (after T2.2) |
| 4 | T2.9-T2.15 | Remaining stages |
| 5 | T5.1, T5.2 | Independent test files |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-27 | Initial task breakdown |
| 1.1 | 2026-01-27 | Completed T0.1-T0.2, T1.1-T1.5, T2.1-T2.8, T3.1, T4.1, T5.1 (18/32 tasks, 69 tests) |
