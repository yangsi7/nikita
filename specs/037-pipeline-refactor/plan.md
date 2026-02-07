# Implementation Plan: 037-pipeline-refactor

**Spec**: [spec.md](spec.md) | **Tasks**: [tasks.md](tasks.md)

---

## Executive Summary

**Objective**: Refactor the 10-stage post-processing pipeline to use unified infrastructure, consistent patterns, comprehensive testing, and production-grade observability.

**Current State**: The pipeline processes conversations asynchronously but has:
- 23 identified issues (2 CRITICAL, 7 HIGH, 9 MEDIUM, 5 LOW)
- 3 different error handling patterns across stages
- Resource leaks in Neo4j and ViceService
- Missing timeouts on LLM and external API calls
- Code duplication between Stages 4 and 5
- 260+ line god method orchestrating everything

**Target State**: A modular, observable, resilient pipeline with:
- Unified `PipelineStage` base class for all stages
- Circuit breakers for external dependencies
- Structured logging with correlation IDs
- Per-stage metrics and tracing
- Comprehensive test coverage (unit + integration + chaos)

---

## Part 1: Current Issues Inventory

### CRITICAL (Must Fix - Blocking Production)

| ID | Issue | File:Line | Impact |
|----|-------|-----------|--------|
| C-1 | **Memory client resource leak** | `post_processor.py:685-744` | Neo4j connection pool exhaustion |
| C-2 | **ViceService resource leak** | `post_processor.py:789-840` | DB connection leaks when exception before finally |

### HIGH (Fix This Sprint)

| ID | Issue | File:Line | Impact |
|----|-------|-----------|--------|
| H-1 | **No timeout on LLM extraction** | `post_processor.py:508` | Pipeline stalls if Claude hangs |
| H-2 | **No timeout on Neo4j ops** | `post_processor.py:687` | 61s cold start blocks pipeline |
| H-3 | **Silent thread resolution failure** | `post_processor.py:604` | Threads never resolved, no error tracking |
| H-4 | **Message pairing assumption** | `post_processor.py:812-814` | Fails silently on non-alternating messages |
| H-5 | **Race condition in session detector** | `session_detector.py:101-125` | Duplicate processing |
| H-6 | **Sequential conversation processing** | `post_processor.py:1176-1196` | N+1 performance issue |
| H-7 | **Partial Neo4j updates** | `post_processor.py:689-729` | Graph inconsistency on mid-loop failure |

### MEDIUM (Next Sprint)

| ID | Issue | File:Line |
|----|-------|-----------|
| M-1 | God method (260+ lines) | `process_conversation:169-450` |
| M-2 | 3 different error handling patterns | Multiple stages |
| M-3 | Deep nesting (4 levels) in vice processing | `post_processor.py:812-827` |
| M-4 | Code duplication Stages 4 & 5 | `post_processor.py:584-654` |
| M-5 | Type hints using `Any` | `post_processor.py:842-846, 1005-1010` |
| M-6 | Hardcoded magic numbers | 20, 0.8, 0.05 scattered throughout |
| M-7 | Missing composite index for stale query | `conversation_repository.py:231-260` |
| M-8 | Thread-unsafe singleton | `relationship_analyzer.py` |
| M-9 | Inconsistent method naming | Mixed `_stage_*` and `_*` patterns |

### LOW (Technical Debt Backlog)

| ID | Issue | File:Line |
|----|-------|-----------|
| L-1 | Unused `llm_model` parameter | `post_processor.py:106` |
| L-2 | Hardcoded "nikita" role check | Should be "assistant" |
| L-3 | `date.today()` without timezone | `post_processor.py:757` |
| L-4 | Missing return type annotations | Several methods |
| L-5 | Raw SQL in force_status_update | Bypasses ORM |

---

## Part 2: Proposed Architecture

### 2.1 New File Structure

```
nikita/context/
├── __init__.py
├── post_processor.py          # Slim orchestrator (< 100 lines)
├── pipeline_context.py        # Shared context object
├── logging.py                 # Structured logging config
├── stages/
│   ├── __init__.py
│   ├── base.py                # PipelineStage base class
│   ├── circuit_breaker.py     # External dependency protection
│   ├── ingestion.py           # Stage 1
│   ├── extraction.py          # Stage 2
│   ├── psychology.py          # Stage 2.5
│   ├── narrative_arcs.py      # Stage 2.6
│   ├── threads.py             # Stage 4
│   ├── thoughts.py            # Stage 5
│   ├── graph_updates.py       # Stage 6
│   ├── summary_rollups.py     # Stage 7
│   ├── vice_processing.py     # Stage 7.5
│   ├── voice_cache.py         # Stage 7.7
│   └── finalization.py        # Stage 8
├── relationship_analyzer.py   # Existing (unchanged)
└── session_detector.py        # Existing (minor fixes)
```

### 2.2 Stage Base Class Pattern

```python
# nikita/context/stages/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential_jitter
from opentelemetry import trace

T = TypeVar("T")  # Stage input type
R = TypeVar("R")  # Stage result type

@dataclass
class StageResult(Generic[R]):
    """Unified result from any pipeline stage."""
    success: bool
    data: R | None = None
    error: str | None = None
    duration_ms: float = 0.0
    retries: int = 0

class PipelineStage(ABC, Generic[T, R]):
    """Base class for all pipeline stages."""

    name: str  # e.g., "extraction", "graph_updates"
    is_critical: bool = False  # If True, failure stops pipeline
    timeout_seconds: float = 30.0
    max_retries: int = 3

    async def execute(self, context: PipelineContext, input: T) -> StageResult[R]:
        """Execute stage with full observability."""
        # Timeout + retry + logging + tracing
        ...

    @abstractmethod
    async def _run(self, context: PipelineContext, input: T) -> R:
        """Implement stage logic. Override in subclass."""
        ...
```

### 2.3 Circuit Breaker for External Dependencies

```python
# nikita/context/stages/circuit_breaker.py
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing recovery

class CircuitBreaker:
    """Prevents cascading failures from external dependencies."""

    async def call(self, func, *args, **kwargs):
        """Execute function through circuit breaker."""
        ...
```

---

## Part 3: Implementation Phases

### Phase 1: Foundation (4 hours)

**Goal**: Create base infrastructure without changing behavior

| Task | File | Description |
|------|------|-------------|
| T0.1 | requirements.txt | Add tenacity, opentelemetry-api, opentelemetry-sdk |
| T0.2 | directories | Create nikita/context/stages/, tests/context/stages/ |
| T2.1 | `stages/circuit_breaker.py` | Create CircuitBreaker class |
| T2.2 | `stages/base.py` | Create `PipelineStage` base class |
| T2.3 | `pipeline_context.py` | Create `PipelineContext` dataclass |
| T2.4 | `logging.py` | Configure structlog with JSON output |

### Phase 2: Context Managers (2 hours)

**Goal**: Fix CRITICAL resource leaks

| Task | File | Description |
|------|------|-------------|
| T1.1 | `memory/graphiti_client.py` | Add async context manager |
| T1.2 | `engine/vice/service.py` | Add async context manager |

### Phase 3: Stage Migration (6 hours)

**Goal**: Extract each stage to its own class

| Task | Original Lines | New File |
|------|----------------|----------|
| T2.5 | 452-474 | `stages/ingestion.py` |
| T2.6 | 476-572 | `stages/extraction.py` |
| T2.7 | 656-744 | `stages/graph_updates.py` |
| T2.8 | 789-840 | `stages/vice_processing.py` |
| T2.9-14 | Various | Remaining stages |
| T2.15 | 169-450 | Slim PostProcessor orchestrator |

### Phase 4: Observability (2 hours)

| Task | Description |
|------|-------------|
| T3.1 | Add OpenTelemetry spans to each stage |
| T3.2 | Add `/admin/pipeline-health` endpoint |
| T3.3 | Add thread resolution failure logging |

### Phase 5: Testing (4 hours)

| Task | File | Tests |
|------|------|-------|
| T5.1 | `test_chaos.py` | Neo4j timeout, LLM rate limit, multi-failure |
| T5.2 | `test_pipeline_integration.py` | Full E2E pipeline |
| T4.1 | `test_message_pairing.py` | Vice processing edge cases |

---

## Part 4: Detailed Stage Specifications

### Stage 1: Ingestion

**Class**: `IngestionStage(PipelineStage[UUID, Conversation])`
- **is_critical**: True
- **timeout_seconds**: 10.0
- **max_retries**: 2

### Stage 2: Extraction [Fixes H-1]

**Class**: `ExtractionStage(PipelineStage[Conversation, ExtractionResult])`
- **is_critical**: True
- **timeout_seconds**: 120.0 (LLM calls can be slow)
- **max_retries**: 2
- **circuit_breaker**: threshold=3, recovery=120s

### Stage 6: Graph Updates [Fixes H-2, H-7]

**Class**: `GraphUpdatesStage(PipelineStage[tuple, None])`
- **is_critical**: False
- **timeout_seconds**: 90.0 (Neo4j cold start)
- **max_retries**: 2
- **circuit_breaker**: threshold=2, recovery=180s

### Stage 7.5: Vice Processing [Fixes H-4]

**Class**: `ViceProcessingStage(PipelineStage[Conversation, int])`
- **is_critical**: False
- **timeout_seconds**: 30.0
- **Fixed message pairing**: Handles non-alternating messages

---

## Part 5: Success Criteria

| Metric | Current | Target |
|--------|---------|--------|
| Pipeline success rate | ~85% | ≥98% |
| Average pipeline duration | ~12s | ≤10s |
| Stage failure isolation | Partial | 100% |
| Test coverage | ~60% | ≥90% |
| P99 latency | Unknown | ≤30s |
| Resource leaks | 2 critical | 0 |
| Code duplication | ~300 lines | ≤50 lines |

---

## Part 6: Files to Create/Modify

### CREATE

| File | Purpose |
|------|---------|
| `nikita/context/stages/__init__.py` | Package init |
| `nikita/context/stages/base.py` | PipelineStage base class |
| `nikita/context/stages/circuit_breaker.py` | External dependency protection |
| `nikita/context/pipeline_context.py` | Shared context object |
| `nikita/context/logging.py` | Structured logging config |
| `nikita/context/stages/ingestion.py` | Stage 1 |
| `nikita/context/stages/extraction.py` | Stage 2 |
| `nikita/context/stages/psychology.py` | Stage 2.5 |
| `nikita/context/stages/narrative_arcs.py` | Stage 2.6 |
| `nikita/context/stages/threads.py` | Stage 4 |
| `nikita/context/stages/thoughts.py` | Stage 5 |
| `nikita/context/stages/graph_updates.py` | Stage 6 |
| `nikita/context/stages/summary_rollups.py` | Stage 7 |
| `nikita/context/stages/vice_processing.py` | Stage 7.5 |
| `nikita/context/stages/voice_cache.py` | Stage 7.7 |
| `nikita/context/stages/finalization.py` | Stage 8 |
| `tests/context/stages/__init__.py` | Test package |
| `tests/context/stages/conftest.py` | Test fixtures |
| `tests/context/stages/test_base.py` | Base class tests |
| `tests/context/stages/test_circuit_breaker.py` | Circuit breaker tests |
| `tests/context/stages/test_*.py` | Per-stage tests |
| `tests/context/test_pipeline_integration.py` | Integration tests |
| `tests/context/test_chaos.py` | Chaos tests |

### MODIFY

| File | Change |
|------|--------|
| `nikita/context/post_processor.py` | Slim down to orchestrator |
| `nikita/memory/graphiti_client.py` | Add context manager |
| `nikita/engine/vice/service.py` | Add context manager |
| `requirements.txt` | Add tenacity, opentelemetry |

---

## Part 7: Estimated Effort

| Phase | Duration | Risk |
|-------|----------|------|
| Phase 1: Foundation | 4 hours | Low |
| Phase 2: Context Managers | 2 hours | Low |
| Phase 3: Stage Migration | 6 hours | Medium |
| Phase 4: Observability | 2 hours | Low |
| Phase 5: Testing | 4 hours | Low |
| **Total** | **18 hours** | Medium |
