# Pipeline Stages

```yaml
context_priority: high
audience: ai_agents
last_updated: 2026-02-03
related_docs:
  - CONTEXT_ENGINE.md
  - DATABASE_SCHEMA.md
  - TESTING_STRATEGY.md
```

## Overview

The post-processing pipeline runs asynchronously after each conversation, handling:
- Entity extraction and memory updates
- Thread and thought generation
- Scoring and graph updates
- Summary generation
- Voice cache invalidation

The pipeline has 11 stages organized into critical and non-critical categories.

---

## Pipeline Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        PIPELINE ARCHITECTURE                                  │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    PostProcessor.process_conversation()              │   │
│  │                    @ post_processor.py:100-250                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  CRITICAL STAGES (abort on failure)                                  │   │
│  │                                                                      │   │
│  │  ┌──────────────┐  ┌──────────────┐                                 │   │
│  │  │  1. INGEST   │──│ 2. EXTRACT   │                                 │   │
│  │  │  Message     │  │ Entities     │                                 │   │
│  │  │  Pairing     │  │ from LLM     │                                 │   │
│  │  └──────────────┘  └──────────────┘                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  NON-CRITICAL STAGES (skip on failure, continue pipeline)            │   │
│  │                                                                      │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │ 3. PSYCHOLOGY│──│ 4. NARRATIVE │──│ 5. THREADS   │              │   │
│  │  │ Analysis     │  │ Arcs         │  │ Detection    │              │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  │         │                                    │                       │   │
│  │         ▼                                    ▼                       │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │ 6. THOUGHTS  │──│ 7. GRAPH     │──│ 8. SUMMARIES │              │   │
│  │  │ Generation   │  │ Updates      │  │ Rollup       │              │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘              │   │
│  │         │                                    │                       │   │
│  │         ▼                                    ▼                       │   │
│  │  ┌──────────────┐  ┌──────────────┐                                 │   │
│  │  │ 9. VICES     │──│ 10. VOICE    │                                 │   │
│  │  │ Processing   │  │ Cache        │                                 │   │
│  │  └──────────────┘  └──────────────┘                                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│                                    ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  CRITICAL STAGE                                                      │   │
│  │                                                                      │   │
│  │  ┌──────────────────────────────────────────────────────────────┐  │   │
│  │  │  11. FINALIZE                                                 │  │   │
│  │  │  - Mark conversation complete                                 │  │   │
│  │  │  - Update stage_reached                                       │  │   │
│  │  │  - Log job execution                                          │  │   │
│  │  └──────────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Stage Details

### Stage 1: Ingestion

**File**: `nikita/context/stages/ingestion.py:1-100`

**Purpose**: Pair user messages with Nikita responses.

**Critical**: Yes - Cannot proceed without message pairs.

```python
# nikita/context/stages/ingestion.py:30-70

class IngestionStage(PipelineStage):
    """Ingest and pair messages from conversation."""

    async def process(self, context: PipelineContext) -> StageResult:
        conversation = context.conversation
        messages = conversation.messages or []

        # Pair user messages with Nikita responses
        pairs = []
        for i in range(0, len(messages) - 1, 2):
            if messages[i].role == "user" and messages[i+1].role == "assistant":
                pairs.append(MessagePair(
                    user_message=messages[i],
                    nikita_response=messages[i+1],
                    timestamp=messages[i].created_at
                ))

        if not pairs:
            return StageResult(
                success=False,
                error="No valid message pairs found"
            )

        context.message_pairs = pairs
        return StageResult(success=True, data={"pairs": len(pairs)})
```

### Stage 2: Extraction

**File**: `nikita/context/stages/extraction.py:1-150`

**Purpose**: Extract entities and facts from messages using LLM.

**Critical**: Yes - Facts needed for graph updates.

```python
# nikita/context/stages/extraction.py:40-100

class ExtractionStage(PipelineStage):
    """Extract entities and facts from message pairs."""

    async def process(self, context: PipelineContext) -> StageResult:
        extractions = []

        for pair in context.message_pairs:
            # Call LLM for extraction
            result = await self._extract_from_pair(pair)
            extractions.append(result)

        context.extractions = extractions
        return StageResult(
            success=True,
            data={"facts": sum(len(e.facts) for e in extractions)}
        )

    async def _extract_from_pair(self, pair: MessagePair) -> ExtractionResult:
        prompt = f"""
        Extract facts and entities from this conversation:

        User: {pair.user_message.content}
        Nikita: {pair.nikita_response.content}

        Extract:
        1. New facts about the user (preferences, experiences, feelings)
        2. Topics discussed
        3. Emotional tone
        4. Any promises or commitments made

        Respond in JSON.
        """
        return await self._call_llm(prompt)
```

### Stage 3: Psychology

**File**: `nikita/context/stages/psychology.py:1-150`

**Purpose**: Analyze psychological dynamics of conversation.

**Critical**: No - Pipeline continues if this fails.

```python
# nikita/context/stages/psychology.py:40-90

class PsychologyStage(PipelineStage):
    """Analyze psychological patterns in conversation."""

    async def process(self, context: PipelineContext) -> StageResult:
        try:
            analysis = await self._analyze_psychology(context)
            context.psychology = analysis
            return StageResult(success=True, data=analysis.model_dump())
        except Exception as e:
            logger.warning(f"Psychology analysis failed: {e}")
            return StageResult(success=False, error=str(e), skippable=True)

    async def _analyze_psychology(self, context: PipelineContext) -> PsychologyAnalysis:
        # Analyze attachment patterns, communication style, etc.
        ...
```

### Stage 4: Narrative Arcs

**File**: `nikita/context/stages/narrative_arcs.py:1-150`

**Purpose**: Track ongoing narrative threads in relationship.

**Critical**: No

```python
# nikita/context/stages/narrative_arcs.py:40-80

class NarrativeArcsStage(PipelineStage):
    """Update narrative arcs based on conversation."""

    async def process(self, context: PipelineContext) -> StageResult:
        repo = NarrativeArcRepository(context.session)

        # Get active arcs
        active_arcs = await repo.get_active(context.user_id)

        # Check if conversation advances any arcs
        for arc in active_arcs:
            if self._advances_arc(arc, context.extractions):
                await repo.advance(arc.id)

        return StageResult(success=True)
```

### Stage 5: Threads

**File**: `nikita/context/stages/threads.py:1-100`

**Purpose**: Detect and create conversation threads.

**Critical**: No

```python
# nikita/context/stages/threads.py:30-70

class ThreadsStage(PipelineStage):
    """Detect conversation threads for continuity."""

    async def process(self, context: PipelineContext) -> StageResult:
        repo = ThreadRepository(context.session)

        for extraction in context.extractions:
            for topic in extraction.topics:
                # Check if thread exists
                existing = await repo.find_by_topic(context.user_id, topic)

                if existing:
                    await repo.update_last_mentioned(existing.id)
                else:
                    await repo.create(
                        user_id=context.user_id,
                        conversation_id=context.conversation.id,
                        topic=topic,
                        status="open"
                    )

        return StageResult(success=True)
```

### Stage 6: Thoughts

**File**: `nikita/context/stages/thoughts.py:1-100`

**Purpose**: Generate Nikita's internal thoughts about conversation.

**Critical**: No

```python
# nikita/context/stages/thoughts.py:30-70

class ThoughtsStage(PipelineStage):
    """Generate Nikita's thoughts about the conversation."""

    async def process(self, context: PipelineContext) -> StageResult:
        thought = await self._generate_thought(context)

        if thought:
            repo = ThoughtRepository(context.session)
            await repo.create(
                user_id=context.user_id,
                conversation_id=context.conversation.id,
                thought=thought.content,
                thought_type=thought.type,
                psychological_context=thought.context
            )

        return StageResult(success=True, data={"thought_generated": bool(thought)})
```

### Stage 7: Graph Updates

**File**: `nikita/context/stages/graph_updates.py:1-150`

**Purpose**: Update Neo4j knowledge graphs with extracted facts.

**Critical**: No (has circuit breaker)

```python
# nikita/context/stages/graph_updates.py:40-100

class GraphUpdatesStage(PipelineStage):
    """Update Neo4j graphs with extracted information."""

    def __init__(self):
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=2,
            recovery_timeout=180  # 3 minutes
        )

    async def process(self, context: PipelineContext) -> StageResult:
        if self.circuit_breaker.is_open:
            logger.warning("Graph updates circuit breaker OPEN, skipping")
            return StageResult(success=False, error="Circuit breaker open", skippable=True)

        try:
            memory = await NikitaMemory.get_instance()

            for extraction in context.extractions:
                # Add to user graph
                for fact in extraction.user_facts:
                    await memory.add_episode(
                        content=fact,
                        graph_name=f"user_{context.user_id}",
                        source="conversation"
                    )

                # Add to relationship graph
                for memory_item in extraction.shared_memories:
                    await memory.add_episode(
                        content=memory_item,
                        graph_name=f"relationship_{context.user_id}",
                        source="conversation"
                    )

            self.circuit_breaker.record_success()
            return StageResult(success=True)

        except Exception as e:
            self.circuit_breaker.record_failure()
            return StageResult(success=False, error=str(e), skippable=True)
```

### Stage 8: Summary Rollups

**File**: `nikita/context/stages/summary_rollups.py:1-100`

**Purpose**: Update daily and weekly summaries.

**Critical**: No

```python
# nikita/context/stages/summary_rollups.py:30-70

class SummaryRollupsStage(PipelineStage):
    """Roll up conversation into daily/weekly summaries."""

    async def process(self, context: PipelineContext) -> StageResult:
        repo = SummaryRepository(context.session)
        today = date.today()

        # Get or create today's summary
        summary = await repo.get_or_create_daily(context.user_id, today)

        # Add this conversation's highlights
        highlights = self._extract_highlights(context)
        await repo.append_highlights(summary.id, highlights)

        return StageResult(success=True)
```

### Stage 9: Vice Processing

**File**: `nikita/context/stages/vice_processing.py:1-100`

**Purpose**: Process vice-related interactions.

**Critical**: No

```python
# nikita/context/stages/vice_processing.py:30-60

class ViceProcessingStage(PipelineStage):
    """Process and update vice preferences."""

    async def process(self, context: PipelineContext) -> StageResult:
        vice_service = ViceService()

        # Detect vice usage in conversation
        detected = await vice_service.detect_usage(context)

        # Update preferences based on user reactions
        if detected.positive_reactions:
            await vice_service.increase_preference(
                context.user_id,
                detected.vice_types
            )

        return StageResult(success=True)
```

### Stage 10: Voice Cache

**File**: `nikita/context/stages/voice_cache.py:1-100`

**Purpose**: Invalidate voice context cache after text conversations.

**Critical**: No

```python
# nikita/context/stages/voice_cache.py:30-60

class VoiceCacheStage(PipelineStage):
    """Invalidate voice context cache."""

    async def process(self, context: PipelineContext) -> StageResult:
        # Invalidate cached voice context
        cache_key = f"voice_context:{context.user_id}"

        if settings.REDIS_URL:
            redis = await get_redis()
            await redis.delete(cache_key)

        return StageResult(success=True)
```

### Stage 11: Finalization

**File**: `nikita/context/stages/finalization.py:1-100`

**Purpose**: Mark conversation complete and log job execution.

**Critical**: Yes - Must complete for data integrity.

```python
# nikita/context/stages/finalization.py:30-80

class FinalizationStage(PipelineStage):
    """Finalize conversation processing."""

    async def process(self, context: PipelineContext) -> StageResult:
        conversation_repo = ConversationRepository(context.session)
        job_repo = JobExecutionRepository(context.session)

        # Mark conversation complete
        await conversation_repo.mark_completed(
            context.conversation.id,
            stage_reached="complete"
        )

        # Log job execution
        await job_repo.create(
            conversation_id=context.conversation.id,
            stage_name="finalization",
            status="completed",
            metadata={
                "stages_run": context.stages_run,
                "stages_skipped": context.stages_skipped,
                "total_time_ms": context.total_time_ms
            }
        )

        return StageResult(success=True)
```

---

## Circuit Breakers

### Configuration

| Service | Failure Threshold | Recovery Timeout |
|---------|-------------------|------------------|
| LLM (Extraction) | 3 | 120s |
| Neo4j (Graphs) | 2 | 180s |

### Implementation

**File**: `nikita/context/stages/base.py:20-60`

```python
class CircuitBreaker:
    """Circuit breaker for external service calls."""

    STATES = ("CLOSED", "OPEN", "HALF_OPEN")

    def __init__(self, failure_threshold: int, recovery_timeout: float):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure = None
        self.state = "CLOSED"

    @property
    def is_open(self) -> bool:
        if self.state == "CLOSED":
            return False

        if self.state == "OPEN":
            if time.time() - self.last_failure > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return False
            return True

        return False

    def record_failure(self):
        self.failure_count += 1
        self.last_failure = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"

    def record_success(self):
        self.failure_count = 0
        self.state = "CLOSED"
```

---

## Error Handling

### Stage Results

```python
@dataclass
class StageResult:
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    skippable: bool = False  # If True, pipeline continues on failure
```

### Pipeline Execution

**File**: `nikita/context/post_processor.py:100-200`

```python
# nikita/context/post_processor.py:120-180

async def process_conversation(self, conversation_id: UUID) -> PipelineReport:
    """Execute full pipeline for conversation."""

    context = await self._create_context(conversation_id)
    stages_run = []
    stages_skipped = []

    for stage in self.stages:
        try:
            result = await asyncio.wait_for(
                stage.process(context),
                timeout=stage.timeout
            )

            if result.success:
                stages_run.append(stage.name)
            elif result.skippable:
                stages_skipped.append(stage.name)
                logger.warning(f"Stage {stage.name} skipped: {result.error}")
            else:
                # Critical stage failed
                raise PipelineError(f"Critical stage {stage.name} failed: {result.error}")

        except asyncio.TimeoutError:
            if stage.critical:
                raise PipelineError(f"Critical stage {stage.name} timed out")
            stages_skipped.append(stage.name)

    return PipelineReport(
        conversation_id=conversation_id,
        stages_run=stages_run,
        stages_skipped=stages_skipped,
        success=True
    )
```

---

## Job Tracking

### Job Execution Table

**File**: `nikita/db/models/job_execution.py:1-80`

Tracks each pipeline execution:

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `conversation_id` | UUID | FK to conversations |
| `stage_name` | VARCHAR | Stage that was executed |
| `status` | VARCHAR | pending/running/completed/failed |
| `started_at` | TIMESTAMP | Execution start |
| `completed_at` | TIMESTAMP | Execution end |
| `error_message` | TEXT | Error if failed |
| `metadata` | JSONB | Stage-specific data |

### Querying Job Status

```sql
-- Find failed jobs in last 24 hours
SELECT je.*, c.user_id
FROM job_executions je
JOIN conversations c ON je.conversation_id = c.id
WHERE je.status = 'failed'
  AND je.started_at > NOW() - INTERVAL '24 hours'
ORDER BY je.started_at DESC;

-- Find stuck conversations
SELECT c.id, c.status, c.processing_started_at
FROM conversations c
WHERE c.status = 'processing'
  AND c.processing_started_at < NOW() - INTERVAL '10 minutes';
```

---

## Stuck Conversation Detection

**File**: `nikita/db/repositories/conversation_repository.py:150-200`

```python
# nikita/db/repositories/conversation_repository.py:160-190

async def detect_stuck(self, threshold_minutes: int = 10) -> List[Conversation]:
    """Find conversations stuck in processing state."""

    threshold = datetime.now(UTC) - timedelta(minutes=threshold_minutes)

    result = await self.session.execute(
        select(Conversation)
        .where(
            Conversation.status == "processing",
            Conversation.processing_started_at < threshold
        )
    )

    return list(result.scalars().all())

async def recover_stuck(self, conversation_id: UUID) -> None:
    """Reset stuck conversation for reprocessing."""

    await self.session.execute(
        update(Conversation)
        .where(Conversation.id == conversation_id)
        .values(
            status="pending",
            processing_started_at=None,
            stage_reached="stuck_recovered"
        )
    )
```

---

## Admin Endpoint

**File**: `nikita/api/routes/admin.py:200-250`

```python
@router.get("/pipeline-health")
async def get_pipeline_health(
    session: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_admin_user)
):
    """Get pipeline health statistics."""

    job_repo = JobExecutionRepository(session)
    conv_repo = ConversationRepository(session)

    # Last 24 hours stats
    stats = await job_repo.get_stats(hours=24)

    # Stuck conversations
    stuck = await conv_repo.detect_stuck()

    return {
        "total_jobs": stats.total,
        "completed": stats.completed,
        "failed": stats.failed,
        "success_rate": stats.success_rate,
        "stuck_conversations": len(stuck),
        "avg_processing_time_ms": stats.avg_time_ms
    }
```

---

## Key File References

| File | Line | Purpose |
|------|------|---------|
| `nikita/context/post_processor.py` | 1-300 | Pipeline orchestration |
| `nikita/context/stages/base.py` | 1-100 | Base stage + circuit breaker |
| `nikita/context/stages/ingestion.py` | 1-100 | Message pairing |
| `nikita/context/stages/extraction.py` | 1-150 | LLM extraction |
| `nikita/context/stages/graph_updates.py` | 1-150 | Neo4j updates |
| `nikita/context/stages/finalization.py` | 1-100 | Completion |
| `nikita/db/models/job_execution.py` | 1-80 | Job tracking model |
| `nikita/api/routes/admin.py` | 200-250 | Health endpoint |

---

## Testing

### Test Files

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `tests/context/stages/test_ingestion.py` | 15 | Message pairing |
| `tests/context/stages/test_extraction.py` | 20 | LLM extraction |
| `tests/context/stages/test_graph_updates.py` | 18 | Neo4j circuit breaker |
| `tests/context/test_post_processor.py` | 25 | Full pipeline |
| `tests/context/test_pipeline_orchestrator.py` | 10 | Error handling |

### Running Tests

```bash
# All pipeline tests
pytest tests/context/ -v

# Just stages
pytest tests/context/stages/ -v

# With coverage
pytest tests/context/ --cov=nikita/context --cov-report=term-missing
```

---

## Related Documentation

- **Context Engine**: [CONTEXT_ENGINE.md](CONTEXT_ENGINE.md)
- **Database Schema**: [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md)
- **Testing Strategy**: [TESTING_STRATEGY.md](TESTING_STRATEGY.md)
