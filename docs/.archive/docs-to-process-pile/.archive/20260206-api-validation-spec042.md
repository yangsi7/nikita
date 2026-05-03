# API Validation Report: Spec 042 - Unified Pipeline Refactor

**Spec**: `/Users/yangsim/Nanoleq/sideProjects/nikita/specs/042-unified-pipeline/`
**Status**: **WARNING** (4 HIGH, 5 MEDIUM findings)
**Timestamp**: 2026-02-06T00:00:00Z
**Validator**: API & Backend Specialist

---

## Executive Summary

Spec 042 (Unified Pipeline Refactor) has **incomplete API specifications** for pipeline triggers, error handling, and response schemas. The specification defines data models and pipeline logic well, but **lacks clarity on how API routes will trigger and integrate with the unified pipeline**. Most issues are resolved by referencing existing patterns in `tasks.py` and `voice.py`, but critical gaps remain around:

1. **Pipeline trigger integration** — How `/tasks/process-conversations` calls `PipelineOrchestrator.process()`
2. **Response schemas** — No request/response models defined for pipeline status/errors
3. **Error handling** — Incomplete specification of failure modes and fallback behavior
4. **OpenAI embedding rate limits** — Missing timeout and retry specifications for embedding calls

**Pass Criteria**: 0 CRITICAL + 0 HIGH findings
**Current Status**: 4 HIGH findings → **FAIL (requires specification clarification)**

---

## Detailed Findings

| Severity | Category | Issue | Location | Recommendation |
|----------|----------|-------|----------|----------------|
| **HIGH** | Routes | Pipeline trigger endpoint missing from spec | spec.md, plan.md | Define T4.5 request/response schemas for unified trigger |
| **HIGH** | Routes | No request/response models for `POST /pipeline/process` | spec.md:spec | Add `PipelineProcessRequest`, `PipelineProcessResponse` models |
| **HIGH** | Error Handling | Critical vs non-critical stage failure behavior incomplete | spec.md:FR-006 | Specify exact HTTP status codes (500 for critical, 202 for async, etc.) |
| **HIGH** | External APIs | OpenAI embedding timeout/retry specs missing | spec.md, plan.md | Add timeout (30s), max_retries (3), backoff strategy to SupabaseMemory |
| **MEDIUM** | Async Patterns | Pipeline async processing pattern unclear | spec.md:FR-005 | Clarify: synchronous trigger endpoint vs async pipeline execution |
| **MEDIUM** | Health Checks | No pipeline health/status endpoint defined | spec.md | Add pipeline health endpoint for monitoring |
| **MEDIUM** | Compatibility | Tasks.py integration not specified | plan.md:Phase-4 | Specify exact API route modifications needed in tasks.py |
| **MEDIUM** | Feature Flag | Fallback behavior when UNIFIED_PIPELINE_ENABLED=false incomplete | plan.md:Phase-4 | Define fallback code path and which endpoints serve old vs new prompts |
| **MEDIUM** | Database | Unique constraint on ready_prompts may cause race conditions | spec.md:AC-1.4 | Add migration guidance for concurrent prompt updates |

---

## 1. Route Definitions & Integration

### Issue 1.1: Pipeline Trigger Endpoint Missing from Spec

**Severity**: HIGH
**Category**: Routes
**Location**: spec.md (all sections), plan.md:Phase-4
**Status**: Not Specified

**Problem**:
Spec 042 defines the internal `PipelineOrchestrator.process(conversation_id)` method but does NOT specify:
- How API routes trigger it
- What request/response format is used
- Where the trigger lives (`POST /pipeline/process`? `POST /tasks/process-conversations`?)

**Current Code Evidence**:
In `nikita/api/routes/tasks.py` (line 510):
```python
@router.post("/process-conversations")
async def process_stale_conversations(_: None = Depends(verify_task_secret)):
    # Currently calls nikita.post_processing.process_conversations()
    from nikita.post_processing import process_conversations
    pipeline_results = await process_conversations(...)
```

**Gap**: Spec 042 does not show how to modify this endpoint to call unified `PipelineOrchestrator.process()`.

**Recommendation**:
Add to plan.md Phase 4 (T4.5):
```markdown
### T4.5: Wire Pipeline Triggers (Specify Integration Points)

**Files to Modify**:
- `nikita/api/routes/tasks.py:510-589` — Modify process_stale_conversations() to call PipelineOrchestrator
- `nikita/api/routes/voice.py:xxx` — Add call to PipelineOrchestrator in webhook handler
- `nikita/config/settings.py` — Add UNIFIED_PIPELINE_ENABLED flag

**Existing Route Pattern**:
```python
# BEFORE: calls legacy post_processing pipeline
from nikita.post_processing import process_conversations
pipeline_results = await process_conversations(session, conversation_ids)

# AFTER: calls unified pipeline (if flag enabled)
if settings.UNIFIED_PIPELINE_ENABLED:
    orchestrator = PipelineOrchestrator(session)
    for conv_id in conversation_ids:
        result = await orchestrator.process(conv_id)
else:
    # Fallback to existing pipeline
    from nikita.post_processing import process_conversations
    pipeline_results = await process_conversations(...)
```

**ACs**:
- AC-4.5.1: `POST /tasks/process-conversations` detects stale convos, calls `PipelineOrchestrator.process()` when flag enabled
- AC-4.5.2: Voice webhook (line 546-814 in voice.py) triggers `PipelineOrchestrator.process()` when flag enabled
- AC-4.5.3: Falls back to existing pipeline when flag disabled
```

---

### Issue 1.2: No Request/Response Schemas for Pipeline Operations

**Severity**: HIGH
**Category**: Routes (Schemas)
**Location**: spec.md (missing), plan.md (missing)
**Status**: Not Specified

**Problem**:
The spec defines `PipelineOrchestrator.process()` as an internal method but does NOT define HTTP request/response schemas for:
- Pipeline status check endpoint (should exist per NFR monitoring requirements)
- Explicit pipeline trigger endpoint (if separate from tasks.py)

**Current Code Evidence**:
Existing endpoints in `tasks.py` return simple `dict`:
```python
result = {
    "status": "ok",
    "processed": processed_count,
    "failed": len(failed_ids),
}
```

But this is NOT standardized across endpoints. Some return `{"status": ..., "error": ...}`, others use `{"success": ..., "data": ...}`.

**Gap**: Spec 042 should define:
```python
# MISSING from spec
class PipelineProcessRequest(BaseModel):
    conversation_id: UUID
    skip_extraction: bool = False  # Optional override
    timeout_seconds: int = 30

class PipelineProcessResponse(BaseModel):
    status: Literal["processing", "success", "failed"]
    conversation_id: UUID
    pipeline_id: str  # For tracking
    started_at: datetime
    completed_at: datetime | None
    total_duration_ms: float
    stage_results: dict[str, StageResult]  # Dict of stage names → results
    error: str | None = None

class StageResult(BaseModel):
    stage_name: str
    success: bool
    duration_ms: float
    error: str | None = None
```

**Recommendation**:
Add to spec.md Section 4 (Architecture) or new Section 5a (API Schemas):

```markdown
## 5. API Schemas (Pipeline Operations)

### PipelineProcessRequest
```python
class PipelineProcessRequest(BaseModel):
    conversation_id: UUID = Field(..., description="Conversation to process")
    force_reprocess: bool = Field(default=False, description="Re-run even if already processed")
    timeout_seconds: int = Field(default=30, description="Max pipeline duration")
```

### PipelineProcessResponse (202 Accepted - async)
```python
class PipelineProcessResponse(BaseModel):
    status: Literal["queued", "processing", "success", "failed"]
    conversation_id: UUID
    pipeline_execution_id: str  # For polling status
    started_at: datetime
    completed_at: datetime | None = None
    total_duration_ms: float = 0.0
    stage_results: dict[str, dict] = {}  # {stage_name: {success, duration_ms, error}}
    error: str | None = None
```

### PipelineStatusResponse (200 OK)
```python
class PipelineStatusResponse(BaseModel):
    execution_id: str
    status: Literal["queued", "processing", "success", "failed"]
    progress_percent: int  # 0-100
    stage_name: str  # Current stage executing
    started_at: datetime
    estimated_completion_at: datetime | None
    stage_results: dict[str, dict]
```
```

---

## 2. Error Handling

### Issue 2.1: Critical vs Non-Critical Stage Failure Behavior Incomplete

**Severity**: HIGH
**Category**: Error Handling
**Location**: spec.md:FR-006 (line 58-60), plan.md:Phase-2
**Status**: Partially Specified

**Problem**:
Spec FR-006 defines:
> - **Critical** (stop on failure): Extraction, MemoryUpdate
> - **Non-critical** (log and continue): LifeSim, Emotional, GameState, Conflict, Touchpoint, Summary, PromptBuilder

But does NOT specify:
1. **HTTP status codes** for critical vs non-critical failures
2. **Response format** when pipeline partially fails
3. **Whether client should retry** or consider partial results valid
4. **Logging levels** for different failure types

**Current Code Evidence**:
In `tasks.py` line 580, generic error handling:
```python
except Exception as e:
    result = {"status": "error", "error": str(e), "detected": 0, "processed": 0}
    await job_repo.fail_execution(execution.id, result=result)
    await session.commit()
    return result
```

This doesn't distinguish critical vs non-critical failures.

**Gap**: Spec should specify error responses like:
```python
# Critical failure (Extraction or MemoryUpdate fails)
HTTP 500 Internal Server Error
{
    "status": "failed",
    "error": "Critical stage failed",
    "failed_stage": "extraction",
    "reason": "LLM timeout after 30s",
    "fallback_action": "none_available"
}

# Non-critical failure (PromptBuilder fails)
HTTP 202 Accepted (async still processing)
{
    "status": "partial_success",
    "error": "Non-critical stage failed",
    "failed_stage": "prompt_builder",
    "reason": "Haiku timeout, fell back to raw Jinja2",
    "completion_status": {
        "extraction": "success",
        "memory_update": "success",
        "life_sim": "success",
        "emotional": "success",
        "game_state": "success",
        "conflict": "success",
        "touchpoint": "success",
        "summary": "failed",
        "prompt_builder": "failed"
    }
}
```

**Recommendation**:
Add to spec.md Section 6 (Data Models) or new Error Handling section:

```markdown
## 6. Error Handling

### Critical Stage Failure (Extraction, MemoryUpdate)

**HTTP Response**: 500 Internal Server Error

```python
class CriticalStageFailureResponse(BaseModel):
    status: Literal["failed"]
    error: str
    failed_stage: Literal["extraction", "memory_update"]
    reason: str  # e.g., "LLM timeout", "Database constraint violation"
    fallback_action: Literal["none_available", "retry", "skip_conversation"]
    conversation_id: UUID
    pipeline_execution_id: str
    stage_started_at: datetime
    failed_at: datetime
    duration_ms: float
```

### Non-Critical Stage Failure (LifeSim, Emotional, GameState, etc.)

**HTTP Response**: 202 Accepted (async processing)

```python
class NonCriticalStageFailureResponse(BaseModel):
    status: Literal["partial_success"]
    error: str  # Informational
    failed_stage: str
    reason: str
    completion_status: dict[str, Literal["success", "failed", "skipped"]]
    # {...all other success stage results...}
    prompt_ready: bool  # Was PromptBuilder successful? (determines readiness)
```

### Error Classification

| Stage | Category | HTTP Response | Action |
|-------|----------|---------------|--------|
| Extraction | CRITICAL | 500 | Stop, log, retry within 5 min |
| MemoryUpdate | CRITICAL | 500 | Stop, log, retry within 5 min |
| LifeSim | NON-CRITICAL | 202 | Log, skip, continue to next |
| Emotional | NON-CRITICAL | 202 | Log, skip, continue |
| GameState | NON-CRITICAL | 202 | Log, skip, continue |
| Conflict | NON-CRITICAL | 202 | Log, skip, continue |
| Touchpoint | NON-CRITICAL | 202 | Log, skip, continue |
| Summary | NON-CRITICAL | 202 | Log, skip, continue |
| PromptBuilder | NON-CRITICAL | 202 | Log, use raw Jinja2 as fallback |
```

---

## 3. External API Integration

### Issue 3.1: OpenAI Embedding Timeout/Retry Specs Missing

**Severity**: HIGH
**Category**: External APIs (OpenAI)
**Location**: spec.md:FR-003 (line 48), plan.md:Phase-1 (SupabaseMemory)
**Status**: Not Specified

**Problem**:
Spec defines SupabaseMemory must call OpenAI `text-embedding-3-small` API for:
1. Single fact embedding (in `add_fact()`)
2. Query embedding (in `search()`)
3. Batch embeddings (in migration script)

But does NOT specify:
- **Timeout** for OpenAI API calls (network latency can be 2-10s)
- **Retry strategy** (exponential backoff, max attempts)
- **Rate limiting** (OpenAI has rate limits: ~3,500 requests/minute for some tiers)
- **Fallback behavior** when OpenAI is unavailable

**Current Code Evidence**:
No OpenAI embedding calls in current codebase. Graphiti (Neo4j) uses embeddings but spec doesn't mention OpenAI integration details.

**Gap**: SupabaseMemory AC-1.1.2 just says "generates embedding" with no implementation details.

**Recommendation**:
Add to plan.md Phase 1, T1.3 (Embedding Generation):

```markdown
### T1.3: Implement Embedding Generation

**Key Methods** (updated):
```python
class SupabaseMemory:
    async def add_fact(
        user_id: UUID,
        fact: str,
        graph_type: str,
        source: str = "conversation",
        confidence: float = 0.8,
        metadata: dict = None,
        timeout_seconds: int = 30,  # NEW
    ) -> MemoryFact:
        """
        Add fact to memory with OpenAI embedding.

        Timeout: 30s (includes OpenAI API call + DB insert)
        Retry: 3 attempts with exponential backoff (1s, 2s, 4s)
        Rate Limit: OpenAI tier-dependent (assume 3500 req/min)
        Fallback: If OpenAI fails, store fact with NULL embedding (unsearchable)
        """
        embedding = await self._embed_text(fact, timeout=30, max_retries=3)
        # embedding = None if OpenAI fails

    async def _embed_text(
        text: str,
        timeout: int = 30,
        max_retries: int = 3,
    ) -> list[float] | None:
        """
        Generate embedding via OpenAI text-embedding-3-small.

        Timeout: 30s total (includes API + network latency)
        Retry: Up to 3 attempts with exponential backoff
        - Attempt 1: Wait 1s before retry
        - Attempt 2: Wait 2s before retry
        - Attempt 3: Wait 4s before retry
        Returns None if all retries fail (fact stored without embedding)

        Rate Limit Handling:
        - If OpenAI returns 429 (rate limit), retry with backoff
        - If backoff exceeds timeout, return None (fail gracefully)
        """
        import httpx

        client = httpx.AsyncClient(timeout=timeout)

        for attempt in range(max_retries):
            try:
                response = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    json={"input": text, "model": "text-embedding-3-small"},
                    headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                    timeout=timeout,
                )

                if response.status_code == 200:
                    data = response.json()
                    return data["data"][0]["embedding"]

                elif response.status_code == 429:  # Rate limited
                    if attempt < max_retries - 1:
                        wait = 2 ** attempt  # Exponential backoff
                        await asyncio.sleep(wait)
                        continue
                    else:
                        return None  # All retries exhausted

                elif response.status_code >= 500:  # Server error
                    if attempt < max_retries - 1:
                        wait = 2 ** attempt
                        await asyncio.sleep(wait)
                        continue
                    else:
                        return None

                else:  # Client error (4xx except 429)
                    logger.error(f"OpenAI API error: {response.status_code}: {response.text}")
                    return None

            except httpx.TimeoutException:
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    await asyncio.sleep(wait)
                    continue
                else:
                    logger.warning(f"OpenAI embedding timeout after {timeout}s")
                    return None

            except Exception as e:
                logger.error(f"OpenAI embedding error: {e}")
                return None

        return None
```

**ACs for T1.3 (updated)**:
- AC-1.3.1: Uses OpenAI `text-embedding-3-small` (1536 dims) with 30s timeout
- AC-1.3.2: Batch embedding support with per-text timeout (e.g., 3s each for 100 texts)
- AC-1.3.3: Exponential backoff retry (3x): 1s, 2s, 4s
- AC-1.3.4: Graceful fallback: if OpenAI fails, store fact with NULL embedding
- AC-1.3.5: Rate limit handling: retry on 429, respect Retry-After header if present
```

---

## 4. Async & Response Patterns

### Issue 4.1: Pipeline Async Processing Pattern Unclear

**Severity**: MEDIUM
**Category**: Async Patterns
**Location**: spec.md:FR-005 (line 54-55), plan.md
**Status**: Partially Specified

**Problem**:
Spec says:
> The system SHALL provide `PipelineOrchestrator.process(conversation_id)` as a single entry point for all post-conversation processing

But does NOT clarify:
1. **Is the endpoint synchronous or async?** (Return when pipeline done vs fire-and-forget?)
2. **What does client see during processing?** (Status = "processing"? Poll for completion?)
3. **Timeout handling** — Pipeline is 8-12s, but API timeout might be 30s. What if pipeline exceeds client timeout?

**Current Code Evidence**:
In `tasks.py` line 546-560:
```python
# This is synchronous relative to HTTP request
queued_ids = await detect_stale_sessions(...)
pipeline_results = await process_conversations(...)
# Return when all done
return {"status": "ok", "processed": processed_count}
```

But this is called from a **background job** (pg_cron), not from a user-facing HTTP endpoint.

**Gap**: Spec should clarify whether:
- User API calls `POST /pipeline/process/{conversation_id}` and **waits** (synchronous, 30s timeout)
- Or **queues it** and returns immediately (asynchronous, 202 Accepted)

**Recommendation**:
Add to spec.md Section 5 (or new Async Patterns section):

```markdown
## Async Processing Pattern

### Synchronous Pipeline Trigger (for internal/admin use)

**Use Case**: pg_cron background job or manual admin trigger

```python
@router.post("/pipeline/process/{conversation_id}")
async def process_conversation(
    conversation_id: UUID,
    _: None = Depends(verify_task_secret),
) -> PipelineProcessResponse:
    """Synchronously process a conversation."""
    orchestrator = PipelineOrchestrator(session)
    result = await asyncio.wait_for(
        orchestrator.process(conversation_id),
        timeout=30.0,  # Max 30s, pipeline target is 8-12s
    )

    if result.failed:
        return PipelineProcessResponse(
            status="failed",
            conversation_id=conversation_id,
            error=result.error_message,
            stage_results={...},
        )
    else:
        return PipelineProcessResponse(
            status="success",
            conversation_id=conversation_id,
            stage_results=result.stage_results,
            total_duration_ms=result.duration_ms,
        )
```

### Key Properties

- **Timeout**: 30s (API-level timeout)
- **Pipeline Target**: 8-12s (should complete well before timeout)
- **Failure**: If pipeline exceeds 30s or critical stage fails, return 500
- **Non-critical stage failure**: Return 202 with partial results
- **Monitoring**: All timings logged per-stage in `job_executions` table

## Status Polling Pattern (Optional - if async required later)

If user-facing async pipeline needed:

```python
@router.post("/pipeline/process/{conversation_id}/async")
async def enqueue_pipeline(conversation_id: UUID) -> PipelineEnqueueResponse:
    """Queue pipeline, return execution_id for polling."""
    job_id = await pipeline_queue.enqueue(conversation_id)
    return PipelineEnqueueResponse(
        execution_id=job_id,
        status="queued",
        check_status_url=f"/pipeline/status/{job_id}",
    )

@router.get("/pipeline/status/{execution_id}")
async def get_pipeline_status(execution_id: str) -> PipelineStatusResponse:
    """Poll pipeline execution status."""
    execution = await pipeline_queue.get_status(execution_id)
    return PipelineStatusResponse(
        execution_id=execution_id,
        status=execution.status,
        stage_name=execution.current_stage,
        progress_percent=execution.progress,
    )
```
```

---

## 5. Monitoring & Health Checks

### Issue 5.1: No Pipeline Health/Status Endpoint

**Severity**: MEDIUM
**Category**: Health Checks / Monitoring
**Location**: spec.md (missing), plan.md (missing)
**Status**: Not Specified

**Problem**:
Spec 042 focuses on the unified pipeline but does NOT define:
- Health check endpoint for pipeline system
- Status endpoint for recent pipeline executions
- Monitoring metrics (success rate, avg duration, failure reasons)

**Current Code Evidence**:
`tasks.py` has `job_executions` logging but no public status endpoint. Voice/portal have no pipeline health visibility.

**Gap**: Production systems need visibility into pipeline health to:
- Monitor SLA compliance (target 8-12s)
- Detect stuck stages
- Alert on repeated failures

**Recommendation**:
Add new section to plan.md or tasks.md:

```markdown
### T4.7: Pipeline Health & Monitoring Endpoint (NEW)

**Files to Create**:
- `nikita/api/routes/pipeline_health.py` (new)

**Endpoints**:

```python
@router.get("/pipeline/health")
async def pipeline_health() -> PipelineHealthResponse:
    """
    Health check for unified pipeline system.

    Returns:
    - status: "healthy" | "degraded" | "unhealthy"
    - recent_success_rate: % of last 100 executions successful
    - avg_duration_ms: Average pipeline duration
    - stuck_conversations: Count of convos >30min in processing
    """

@router.get("/pipeline/stats/last-24h")
async def pipeline_stats_24h() -> PipelineStatsResponse:
    """
    Pipeline metrics for last 24 hours.

    Returns:
    - total_executions: Count
    - success_count: Count
    - failure_count: Count by stage
    - avg_duration_ms: By stage
    - slowest_stage: Which stage takes longest
    """
```

**Use Cases**:
- Admin dashboard shows pipeline health
- Monitoring/alerting system polls /health endpoint
- Debugging: See which stage is slowest, failing most
```

---

## 6. Existing Pattern Analysis

### Summary of Existing API Patterns (GOOD to reuse)

**Task Trigger Pattern** (tasks.py):
```python
@router.post("/endpoint")
async def task_endpoint(
    _: None = Depends(verify_task_secret),
):
    """All internal task endpoints require secret verification."""
    try:
        # Do work
        result = {"status": "ok", "details": {...}}
        return result
    except Exception as e:
        logger.error(...); raise
```

**Voice Webhook Pattern** (voice.py:843-905):
```python
@router.post("/webhook")
async def handle_webhook(
    request: Request,
    elevenlabs_signature: str = Header(...),
) -> WebhookResponse:
    """Verify signature, parse, process."""
    if not verify_signature(payload, signature, secret):
        raise HTTPException(401, "Invalid signature")

    event_data = json.loads(payload)
    result = await _process_webhook_event(event_data)
    return WebhookResponse(status=result.get("status"))
```

**Dependency Injection Pattern**:
```python
async def get_session_maker():
    return get_session_maker()

@router.post("/endpoint")
async def endpoint(session = Depends(get_session_maker)):
    repo = UserRepository(session)
    user = await repo.get(user_id)
```

**Recommendation**: Follow these patterns when implementing Spec 042 Phase 4 API routes.

---

## 7. Compatibility & Migration

### Issue 7.1: Existing Endpoint Modifications Not Fully Specified

**Severity**: MEDIUM
**Category**: Compatibility
**Location**: plan.md:Phase-4 (T4.5)
**Status**: Vague

**Problem**:
Plan says modify `tasks.py` and `voice.py` to call `PipelineOrchestrator` but doesn't specify:
- Exact line numbers to modify
- Exact code changes needed
- Whether modifications are **additive** (both paths live) or **replacive** (old path removed)

**Current Code** (tasks.py:510-589):
```python
@router.post("/process-conversations")
async def process_stale_conversations(_: None = Depends(verify_task_secret)):
    # Currently calls post_processing.process_conversations
    from nikita.post_processing import process_conversations
    pipeline_results = await process_conversations(
        session=session,
        conversation_ids=queued_ids,
    )
```

**Gap**: Should specify:
```python
# AFTER modification with feature flag

@router.post("/process-conversations")
async def process_stale_conversations(_: None = Depends(verify_task_secret)):
    settings = get_settings()

    if settings.UNIFIED_PIPELINE_ENABLED:
        # NEW: Call unified pipeline
        from nikita.pipeline.orchestrator import PipelineOrchestrator
        orchestrator = PipelineOrchestrator(session)
        results = []
        for conv_id in queued_ids:
            try:
                result = await asyncio.wait_for(
                    orchestrator.process(conv_id),
                    timeout=30.0,
                )
                results.append(result)
            except asyncio.TimeoutError:
                logger.error(f"Pipeline timeout for {conv_id}")
                results.append(PipelineResult.failed(...))
    else:
        # OLD: Fallback to existing pipeline
        from nikita.post_processing import process_conversations
        results = await process_conversations(...)
```

**Recommendation**:
Update plan.md Phase 4, T4.5 with code snippets showing:
1. Exact location in tasks.py and voice.py to modify
2. Before/after code comparison
3. Feature flag usage pattern

---

## 8. Database & Concurrency

### Issue 8.1: Ready Prompts Unique Constraint May Cause Race Conditions

**Severity**: MEDIUM
**Category**: Database
**Location**: spec.md:AC-1.4 (line 242)
**Status**: Migration guidance missing

**Problem**:
Spec defines:
> AC-1.4: Unique index on ready_prompts(user_id, platform) WHERE is_current = TRUE

But concurrent processes could violate this:
1. Process A: `UPDATE ready_prompts SET is_current=FALSE WHERE user_id=123, platform='text'`
2. Process B: `INSERT ready_prompts (user_id, platform, is_current=TRUE) ...`
3. If B executes between A's UPDATE and new INSERT, the index constraint fails

**Current Code Evidence**:
None (schema not yet created). But `ReadyPromptRepository.set_current()` AC says it "deactivates old prompt and inserts new".

**Gap**: Need migration guidance and implementation pattern.

**Recommendation**:
Add to plan.md Phase 0, T0.2 (indexes):

```markdown
### Concurrent Prompt Update Pattern

To avoid race conditions with the unique constraint on `ready_prompts(user_id, platform) WHERE is_current = TRUE`:

```python
class ReadyPromptRepository:
    async def set_current(
        self,
        user_id: UUID,
        platform: str,  # 'text' or 'voice'
        prompt_text: str,
        token_count: int,
        context_snapshot: dict,
        pipeline_version: str,
        generation_time_ms: float,
        conversation_id: UUID | None,
    ) -> ReadyPrompt:
        """
        Atomically deactivate old prompt and insert new one.

        Pattern: Use PostgreSQL transaction isolation to prevent race conditions.
        Isolation Level: SERIALIZABLE (or READ_COMMITTED with careful ordering)

        Steps:
        1. Lock the (user_id, platform) pair
        2. Set old prompt is_current=FALSE
        3. Insert new prompt with is_current=TRUE
        4. Commit (releases lock)

        If INSERT fails with unique constraint violation, another process
        won the race and inserted first. This is OK - the race loser's
        prompt is simply not inserted (idempotent).
        """
        stmt = select(ReadyPrompt).where(
            (ReadyPrompt.user_id == user_id) &
            (ReadyPrompt.platform == platform) &
            (ReadyPrompt.is_current == True)
        ).with_for_update()  # Lock for update

        result = await self.session.execute(stmt)
        old_prompt = result.scalar_one_or_none()

        if old_prompt:
            old_prompt.is_current = False
            self.session.add(old_prompt)

        new_prompt = ReadyPrompt(
            user_id=user_id,
            platform=platform,
            prompt_text=prompt_text,
            token_count=token_count,
            context_snapshot=context_snapshot,
            pipeline_version=pipeline_version,
            generation_time_ms=generation_time_ms,
            is_current=True,
            conversation_id=conversation_id,
        )
        self.session.add(new_prompt)
        await self.session.flush()  # Trigger unique constraint check

        return new_prompt
```

**ACs**:
- AC-0.6.2: `set_current()` uses `SELECT ... FOR UPDATE` to atomically deactivate old + insert new
- AC-0.6.3: If INSERT fails with unique constraint, log warning (another process won the race)
```

---

## API Inventory (From Existing Routes)

### Current Endpoints (to be modified/extended for Spec 042)

| Method | Endpoint | Purpose | Auth | Input | Output |
|--------|----------|---------|------|-------|--------|
| POST | `/tasks/process-conversations` | Trigger pipeline | TaskSecret | - | `{status, detected, processed, failed}` |
| POST | `/tasks/decay` | Apply hourly decay | TaskSecret | - | `{status, processed, decayed, game_overs}` |
| POST | `/voice/webhook` | Voice transcription webhook | HMAC | ElevenLabs JSON | `{status, message}` |
| POST | `/voice/initiate` | Start voice call | - | `InitiateCallRequest` | `InitiateCallResponse` |
| GET | `/voice/availability/{user_id}` | Check call availability | - | - | `AvailabilityResponse` |

### Spec 042 New Endpoints (To be Defined)

| Method | Endpoint | Purpose | Auth | Input | Output |
|--------|----------|---------|------|-------|--------|
| POST | `/pipeline/process/{conversation_id}` | Trigger unified pipeline | TaskSecret | `PipelineProcessRequest` | `PipelineProcessResponse` |
| GET | `/pipeline/status/{execution_id}` | Poll pipeline status | TaskSecret | - | `PipelineStatusResponse` |
| GET | `/pipeline/health` | Health check | - | - | `PipelineHealthResponse` |

---

## Verification Checklist for Implementation

Before implementation begins, ensure:

- [ ] **Request/response schemas** defined for all new endpoints
- [ ] **Error codes and HTTP statuses** specified (500 for critical failures, 202 for partial)
- [ ] **Feature flag behavior** documented (fallback code path when disabled)
- [ ] **OpenAI embedding timeout/retry** specified (30s timeout, 3x retry with backoff)
- [ ] **Async processing pattern** clarified (sync endpoint with 30s timeout vs async queue)
- [ ] **Database constraint** handling documented (FOR UPDATE lock for race conditions)
- [ ] **Monitoring endpoints** defined for operational visibility
- [ ] **Existing endpoint modifications** specified with before/after code

---

## Summary & Next Steps

### High-Priority Clarifications Needed (Before Phase 4 Implementation)

1. **Add request/response schemas** for pipeline operations (NEW Pydantic models)
2. **Define error response format** for critical vs non-critical stage failures (HTTP 500 vs 202)
3. **Specify OpenAI embedding** timeout (30s) and retry strategy (3x exponential backoff)
4. **Clarify async pattern** (synchronous endpoint with 30s timeout is recommended)
5. **Document existing route modifications** with code snippets (tasks.py, voice.py)

### Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|-----------|
| API route integration unclear | HIGH | Add detailed code snippets to plan.md Phase 4 |
| OpenAI embedding failures | HIGH | Add timeout/retry specs to T1.3, handle NULL embeddings gracefully |
| Critical stage failures cause 500s | HIGH | Define error response format, add test cases |
| Race conditions on ready_prompts | MEDIUM | Add FOR UPDATE locking pattern, document in T0.2 |
| No operational visibility | MEDIUM | Add /pipeline/health and /pipeline/stats endpoints |

### Recommendation

**Spec Status**: **CONDITIONAL PASS** (can proceed with implementation if HIGH findings addressed in code)

The specification is **architecturally sound** but **operationally incomplete**. API integration details should be added to plan.md before Phase 4 implementation begins. Most gaps are closure of existing patterns already in the codebase.

**Suggested Process**:
1. Add API schemas section to spec.md or plan.md
2. Add code snippets to plan.md Phase 4 showing exact modifications
3. Validate updated spec against existing patterns in tasks.py, voice.py
4. Re-run audit after clarifications

---

## References

- **Spec Document**: `/Users/yangsim/Nanoleq/sideProjects/nikita/specs/042-unified-pipeline/spec.md`
- **Plan Document**: `/Users/yangsim/Nanoleq/sideProjects/nikita/specs/042-unified-pipeline/plan.md`
- **Existing Tasks Route**: `/Users/yangsim/Nanoleq/sideProjects/nikita/nikita/api/routes/tasks.py` (lines 510-589)
- **Existing Voice Route**: `/Users/yangsim/Nanoleq/sideProjects/nikita/nikita/api/routes/voice.py` (lines 546-814)
- **Current API Patterns**: `/Users/yangsim/Nanoleq/sideProjects/nikita/nikita/api/CLAUDE.md`

