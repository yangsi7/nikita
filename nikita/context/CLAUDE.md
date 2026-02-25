# context/ - Context Engineering Module

> **LEGACY**: The active pipeline is `nikita/pipeline/` (Spec 042). See `nikita/pipeline/CLAUDE.md`.
> This module retains only `session_detector.py` and `validation.py`. The PostProcessor below was superseded by `nikita/pipeline/orchestrator.py`.

## Purpose

Implements the context engineering redesign (specs 012, 037) for Nikita AI girlfriend game. Moves memory operations from in-conversation (high latency) to post-processing (async, no latency impact).

## Architecture

```
PRE-CONVERSATION:  Generate rich system prompt from pre-computed context (~50ms)
DURING CONVERSATION: Pure LLM conversation with optional retrieval (NO memory writes)
POST-CONVERSATION: Async 11-stage pipeline extracts facts, updates graphs, generates summaries
```

## Components

### SessionDetector (`session_detector.py`)
Detects when text sessions have timed out (15 min no messages).

```python
from nikita.context import SessionDetector

detector = SessionDetector(session, timeout_minutes=15)
stale_ids = await detector.detect_and_queue(limit=50)
```

### PostProcessor (`post_processor.py`)
11-stage async pipeline for processing ended conversations (Spec 037):

| # | Stage | Class | Critical | Purpose |
|---|-------|-------|----------|---------|
| 1 | Ingestion | IngestionStage | ✅ | Load and validate conversation |
| 2 | Extraction | ExtractionStage | ✅ | LLM extracts facts, threads, thoughts |
| 3 | Psychology | PsychologyStage | ❌ | Analyze relationship dynamics |
| 4 | Narrative Arcs | NarrativeArcsStage | ❌ | Update story arcs |
| 5 | Threads | ThreadsStage | ❌ | Create/resolve conversation threads |
| 6 | Thoughts | ThoughtsStage | ❌ | Generate Nikita's inner thoughts |
| 7 | Graph Updates | GraphUpdatesStage | ❌ | Update memory facts (pgVector) |
| 8 | Summary Rollups | SummaryRollupsStage | ❌ | Update daily summaries |
| 9 | Vice Processing | ViceProcessingStage | ❌ | Detect user vice signals |
| 10 | Voice Cache | VoiceCacheStage | ❌ | Invalidate voice agent cache |
| 11 | Finalization | FinalizationStage | ❌ | Mark conversation processed |

```python
from nikita.context import PostProcessor

processor = PostProcessor(session)
result = await processor.process_conversation(conversation_id)
```

### PipelineStage Base Class (`stages/base.py`)
Unified stage infrastructure with:
- **Timeout handling** - Configurable per stage
- **Retry logic** - Exponential backoff with jitter (tenacity)
- **Structured logging** - Stage name, duration, errors
- **OpenTelemetry tracing** - Per-stage spans

```python
from nikita.context.stages.base import PipelineStage, StageResult

class MyStage(PipelineStage[InputType, OutputType]):
    name = "my_stage"
    is_critical = False
    timeout_seconds = 30.0
    max_retries = 2

    async def _run(self, context: PipelineContext, input: InputType) -> OutputType:
        # Stage implementation
        ...
```

### Circuit Breakers (`stages/circuit_breaker.py`)
Prevents cascading failures from external dependencies:

| Circuit Breaker | Failure Threshold | Recovery Timeout |
|----------------|-------------------|------------------|
| LLM (Claude) | 3 failures | 120 seconds |
| Supabase | 2 failures | 180 seconds |

### PipelineContext (`pipeline_context.py`)
Shared context passed between stages:
- `conversation_id`, `user_id`, `started_at`
- `conversation` (from ingestion)
- `extraction_result` (from extraction)
- `stage_errors` (accumulated errors)
- `metadata` (per-stage results)

### TemplateGenerator (`template_generator.py`)
6-layer system prompt generation (~4500 tokens):

1. **Core Identity** (static, ~400 tokens) - Nikita's personality
2. **Current Moment** (computed, ~300 tokens) - Time, mood, energy
3. **Relationship State** (pre-computed, ~500 tokens) - Chapter, score, trends
4. **Conversation History** (pre-computed, ~1800 tokens) - Summaries, threads
5. **Knowledge & Inner Life** (pre-computed, ~1000 tokens) - Facts, thoughts
6. **Response Guidelines** (computed, ~500 tokens) - Style parameters

```python
from nikita.context import generate_system_prompt

prompt = await generate_system_prompt(session, user_id)
```

## Database Tables

| Table | Purpose |
|-------|---------|
| `conversation_threads` | Unresolved topics, questions, promises |
| `nikita_thoughts` | Simulated inner life thoughts |
| `daily_summaries` | Pre-computed daily conversation summaries |
| `conversations.status` | Processing status (active/processing/processed/failed) |
| `job_executions` | Pipeline run tracking and metrics |

## pg_cron Integration

Endpoint: `POST /tasks/process-conversations`

Called every minute to:
1. Find stale active conversations (15+ min no messages)
2. Queue them for post-processing
3. Run the 11-stage pipeline on each

## Admin Endpoint

`GET /admin/pipeline-health` returns:
- Circuit breaker states (open/closed/half_open)
- Per-stage statistics (success rate, avg duration)
- Recent failures (last 10)
- Overall pipeline health status

## Key Design Decisions

1. **No memory writes during conversation** - Reduces latency
2. **Rich pre-computed context** - System prompt built from cached data
3. **Simulated inner life** - Makes Nikita feel alive between conversations
4. **Thread tracking** - Natural conversation continuity
5. **15 min text timeout** - Clear session boundary for processing
6. **Stage isolation** - Non-critical failures don't stop pipeline (Spec 037)
7. **Circuit breakers** - Protect against Supabase/LLM outages (Spec 037)

## Related Files

### Stage Classes (stages/)
- `stages/base.py` - PipelineStage base class, StageResult, StageError
- `stages/circuit_breaker.py` - CircuitBreaker, CircuitState
- `stages/ingestion.py` - IngestionStage
- `stages/extraction.py` - ExtractionStage
- `stages/psychology.py` - PsychologyStage
- `stages/narrative_arcs.py` - NarrativeArcsStage
- `stages/threads.py` - ThreadsStage
- `stages/thoughts.py` - ThoughtsStage
- `stages/graph_updates.py` - GraphUpdatesStage
- `stages/summary_rollups.py` - SummaryRollupsStage
- `stages/vice_processing.py` - ViceProcessingStage
- `stages/voice_cache.py` - VoiceCacheStage
- `stages/finalization.py` - FinalizationStage

### Other Files
- `pipeline_context.py` - PipelineContext dataclass
- `logging.py` - Structured logging configuration
- `nikita/db/models/context.py` - ConversationThread, NikitaThought models
- `nikita/db/repositories/thread_repository.py` - Thread CRUD
- `nikita/db/repositories/thought_repository.py` - Thought CRUD
- `nikita/api/routes/tasks.py` - pg_cron endpoints
- `nikita/api/routes/admin.py` - /admin/pipeline-health endpoint
- `nikita/agents/text/handler.py` - Message handling (fact extraction removed)

## Tests (160 total)

- `tests/context/stages/` - Stage unit tests (129 tests)
- `tests/context/test_pipeline_orchestrator.py` - Orchestrator tests (9 tests)
- `tests/context/test_pipeline_integration.py` - Integration tests (9 tests)
- `tests/api/routes/test_admin_pipeline_health.py` - Admin endpoint tests (9 tests)
