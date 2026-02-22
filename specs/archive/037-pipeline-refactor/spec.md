> **SUPERSEDED**: This spec has been functionally replaced by [Spec 042](../042-unified-pipeline/spec.md) (Unified Pipeline).
> The 11-stage pipeline and orchestrator described here were redesigned as a 9-stage unified pipeline with SupabaseMemory. See Spec 042 for the authoritative specification.

# Feature Specification: Pipeline Refactoring

**Spec ID**: 037-pipeline-refactor
**Status**: Superseded
**Complexity Score**: 11 (Complex - Phase 0 implicit via prior analysis)

---

## Overview

### Problem Statement

The 10-stage post-processing pipeline (`nikita/context/post_processor.py`) has accumulated 23 identified issues including 2 CRITICAL resource leaks and 7 HIGH priority bugs. The pipeline processes conversations asynchronously but suffers from:

1. **Resource Leaks**: Neo4j connections and ViceService DB connections leak when exceptions occur
2. **Missing Timeouts**: LLM and Neo4j operations can hang indefinitely, stalling the entire pipeline
3. **Inconsistent Error Handling**: 3 different patterns across stages make debugging difficult
4. **Poor Observability**: No structured logging, no tracing, no correlation IDs
5. **Code Duplication**: ~300 lines duplicated between stages
6. **God Method**: 260+ line orchestrator method with deep nesting

### Proposed Solution

Refactor to a modular, observable, resilient pipeline with:
1. **Unified `PipelineStage` base class** - Consistent timeout, retry, logging, tracing for all stages
2. **Circuit breakers** - For Neo4j (180s recovery) and LLM (120s recovery) dependencies
3. **Structured logging** - JSON output with conversation_id correlation via structlog
4. **OpenTelemetry tracing** - Per-stage spans for distributed tracing
5. **Chaos testing** - Comprehensive tests for failure scenarios

### Success Criteria

- [ ] Pipeline success rate ≥98% (currently ~85%)
- [ ] Average duration ≤10s (currently ~12s)
- [ ] Zero resource leaks (currently 2 CRITICAL)
- [ ] Test coverage ≥90% (currently ~60%)
- [ ] All 23 issues resolved

---

## Functional Requirements

| ID | Requirement | Priority | Issue IDs |
|----|-------------|----------|-----------|
| FR-001 | Unified `PipelineStage` base class with timeout, retry, logging, tracing | P0 | M-1, M-2, M-9 |
| FR-002 | Circuit breaker pattern for external dependencies (Neo4j, LLM) | P0 | H-1, H-2, H-7 |
| FR-003 | Structured logging with JSON output and conversation correlation | P1 | M-2 |
| FR-004 | Context manager pattern for NikitaMemory to prevent leaks | P0 | C-1 |
| FR-005 | Context manager pattern for ViceService to prevent leaks | P0 | C-2 |
| FR-006 | Fixed message pairing logic for vice processing | P1 | H-4 |
| FR-007 | Thread resolution failure tracking and logging | P1 | H-3 |
| FR-008 | Race condition fix in session detector | P1 | H-5 |
| FR-009 | OpenTelemetry spans per pipeline stage | P2 | - |
| FR-010 | Admin endpoint `/admin/pipeline-health` for observability | P2 | - |
| FR-011 | Comprehensive chaos testing infrastructure | P1 | - |

---

## User Stories

### US-1: Pipeline Reliability (P0)
**As a** system operator
**I want** the post-processing pipeline to complete reliably without resource leaks
**So that** conversations are processed correctly and system resources aren't exhausted

**Acceptance Criteria**:
- [ ] AC-1.1: NikitaMemory uses `async with` context manager pattern
- [ ] AC-1.2: ViceService uses `async with` context manager pattern
- [ ] AC-1.3: Neo4j connections are closed even when exceptions occur
- [ ] AC-1.4: DB connections are closed even when exceptions occur
- [ ] AC-1.5: Pipeline success rate ≥98% over 100 test runs

### US-2: Timeout Handling (P0)
**As a** system operator
**I want** all external calls to have explicit timeouts
**So that** the pipeline doesn't hang on slow dependencies

**Acceptance Criteria**:
- [ ] AC-2.1: LLM extraction has 120s timeout with graceful fallback
- [ ] AC-2.2: Neo4j operations have 90s timeout
- [ ] AC-2.3: Thread resolution has 10s timeout
- [ ] AC-2.4: Timeout errors are logged with duration and stage name
- [ ] AC-2.5: Circuit breaker opens after 3 LLM failures (120s recovery)
- [ ] AC-2.6: Circuit breaker opens after 2 Neo4j failures (180s recovery)

### US-3: Unified Stage Infrastructure (P0)
**As a** developer
**I want** all pipeline stages to use the same base class
**So that** I can add/modify stages consistently

**Acceptance Criteria**:
- [ ] AC-3.1: `PipelineStage` base class exists with timeout, retry, logging
- [ ] AC-3.2: All 10 stages extend `PipelineStage`
- [ ] AC-3.3: Each stage has explicit `is_critical` flag (True = stops pipeline on failure)
- [ ] AC-3.4: Each stage has configurable `timeout_seconds` and `max_retries`
- [ ] AC-3.5: Stage results use unified `StageResult` dataclass

### US-4: Observability (P1)
**As a** system operator
**I want** structured logging with correlation IDs
**So that** I can trace issues through the pipeline

**Acceptance Criteria**:
- [ ] AC-4.1: All logs include `conversation_id` and `stage` fields
- [ ] AC-4.2: Logs are JSON formatted via structlog
- [ ] AC-4.3: Stage completion logged with `duration_ms` and `success` fields
- [ ] AC-4.4: Stage failures logged with `error` and `exc_info`
- [ ] AC-4.5: OpenTelemetry spans created for each stage

### US-5: Vice Processing Fix (P1)
**As a** player
**I want** vice signals detected from all message exchanges
**So that** my vice profile is accurate

**Acceptance Criteria**:
- [ ] AC-5.1: Non-alternating messages handled correctly (user→user→assistant)
- [ ] AC-5.2: Assistant role and nikita role both recognized
- [ ] AC-5.3: Empty content messages skipped gracefully
- [ ] AC-5.4: Single-message conversations handled (no pair = skip)
- [ ] AC-5.5: 8 unit tests for message pairing edge cases

### US-6: Chaos Testing (P1)
**As a** developer
**I want** chaos tests that simulate failures
**So that** I can verify pipeline resilience

**Acceptance Criteria**:
- [ ] AC-6.1: Test simulates Neo4j 61s cold start timeout
- [ ] AC-6.2: Test simulates LLM rate limiting (429)
- [ ] AC-6.3: Test simulates multiple non-critical stage failures
- [ ] AC-6.4: Pipeline completes when only non-critical stages fail
- [ ] AC-6.5: Pipeline fails fast when critical stages fail
- [ ] AC-6.6: Circuit breaker state transitions tested (CLOSED→OPEN→HALF_OPEN)

---

## Non-Functional Requirements

| ID | Requirement | Target | Current |
|----|-------------|--------|---------|
| NFR-001 | Pipeline success rate | ≥98% | ~85% |
| NFR-002 | Average pipeline duration | ≤10s | ~12s |
| NFR-003 | P99 pipeline latency | ≤30s | Unknown |
| NFR-004 | Test coverage (context/stages/) | ≥90% | ~60% |
| NFR-005 | All existing tests pass | 100% | 100% |
| NFR-006 | No new security vulnerabilities | 0 | 0 |
| NFR-007 | Code duplication | ≤50 lines | ~300 lines |

---

## Technical Constraints

1. **Python 3.11+** - Required for asyncio improvements
2. **Existing Dependencies** - structlog already in requirements
3. **New Dependencies** - tenacity, opentelemetry-api, opentelemetry-sdk
4. **Database** - PostgreSQL via SQLAlchemy async
5. **Neo4j** - Via Graphiti client (NikitaMemory)
6. **LLM** - Claude via Anthropic SDK

---

## Out of Scope

- Complete rewrite of NikitaMemory (only add context manager)
- Migration to different LLM provider
- Kubernetes/distributed tracing backend setup
- Real-time alerting (only logging for now)
- Database schema changes

---

## Dependencies

- **Internal**: nikita/memory/graphiti_client.py (context manager addition)
- **Internal**: nikita/engine/vice/service.py (context manager addition)
- **External**: tenacity (PyPI) - retry logic
- **External**: opentelemetry-api, opentelemetry-sdk (PyPI) - tracing
- **Existing**: structlog (already in requirements)

---

## Issue Mapping

| Issue ID | Description | User Story | Task |
|----------|-------------|------------|------|
| C-1 | Memory client resource leak | US-1 | T1.1 |
| C-2 | ViceService resource leak | US-1 | T1.2 |
| H-1 | No timeout on LLM extraction | US-2 | T2.6 |
| H-2 | No timeout on Neo4j ops | US-2 | T2.7 |
| H-3 | Silent thread resolution failure | US-4 | T3.3 |
| H-4 | Message pairing assumption | US-5 | T2.8 |
| H-5 | Race condition in session detector | - | Deferred |
| H-6 | Sequential conversation processing | - | Deferred |
| H-7 | Partial Neo4j updates | US-2 | T2.7 |
| M-1 | God method (260+ lines) | US-3 | T2.15 |
| M-2 | 3 different error handling patterns | US-3, US-4 | T2.2, T2.4 |
| M-3 | Deep nesting (4 levels) in vice processing | US-5 | T2.8 |
| M-4 | Code duplication Stages 4 & 5 | US-3 | T2.9 |
| M-5 | Type hints using `Any` | - | Addressed in refactor |
| M-6 | Hardcoded magic numbers | - | Addressed in refactor |
| M-7 | Missing composite index for stale query | - | Deferred |
| M-8 | Thread-unsafe singleton | - | Deferred |
| M-9 | Inconsistent method naming | US-3 | T2.2 |
