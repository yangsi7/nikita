> **SUPERSEDED**: This spec has been replaced by Spec 042. See specs/042-unified-pipeline/spec.md for current requirements.

# Feature Specification: Post-Processing Unification and Reliability

**Spec ID**: 031-post-processing-unification
**Status**: Complete (16/17 tasks - T4.4 deferred)
**Created**: 2026-01-19
**Completed**: 2026-01-19
**Priority**: P0 (Critical)

## Overview

### Problem Statement

The post-processing pipeline has multiple critical bugs causing long-term memory to become stale:

1. **Broken Adapter** (`nikita/post_processing/adapter.py:24`): Calls `conv_repo.get_messages(conv_id)` but this method **DOES NOT EXIST** in `ConversationRepository`. Post-processing silently fails.

2. **Stuck Conversations**: Conversations get marked `status='processing'` but never transition to `processed` due to the adapter bug, leaving them stuck indefinitely.

3. **Voice-Text Desync**: Voice reads `nikita_summary_text` from `daily_summaries`, but post-processing writes to `summary_text`. Different columns = stale voice context.

4. **No Voice Cache Refresh**: After text post-processing completes, `users.cached_voice_prompt` is never invalidated. Voice calls use stale context.

5. **No Observability**: Post-processing failures aren't logged to `job_executions`, making debugging impossible.

**Evidence**:
```python
# nikita/post_processing/adapter.py:24 - BUG
messages = await conv_repo.get_messages(conv_id)  # Method doesn't exist!

# nikita/db/repositories/conversation_repository.py - No get_messages method
# Available methods: create_conversation, append_message, get_recent, ...
```

### Proposed Solution

1. **Fix Adapter**: Use `Conversation.messages` JSONB column directly (already has data)
2. **Status State Machine**: Implement proper `active → processing → processed/failed` transitions
3. **Voice Cache Refresh**: Invalidate `cached_voice_prompt` after text processing
4. **Column Alignment**: Ensure voice reads what post-processing writes
5. **Observability**: Log all processing events to `job_executions`

### Success Criteria

- [x] SC-1: 99% post-processing success rate (up from ~70%) - adapter bug fixed
- [x] SC-2: 0 conversations stuck in 'processing' for >30 minutes - detect_stuck() + endpoint
- [x] SC-3: Voice reflects text conversation updates within same day - voice cache invalidation
- [x] SC-4: All processing failures visible in admin tooling - job_execution logging + stats endpoint
- [x] SC-5: Clear error messages for each failure mode - stage-level context in errors

---

## Functional Requirements

### FR-001: Fix Adapter get_messages() Bug
**Priority**: P0
**Description**: Fix the post-processing adapter to correctly retrieve conversation messages.

**Technical Details**:
- **Option A**: Add `get_messages()` method to `ConversationRepository`
- **Option B** (Recommended): Use `Conversation.messages` JSONB directly
- `Conversation.messages` already contains full message history
- No new DB query needed - just load the relationship

**Root Cause**:
```python
# nikita/post_processing/adapter.py:24
messages = await conv_repo.get_messages(conv_id)  # BUG: Method doesn't exist

# Fix: Load conversation with messages relationship
conversation = await conv_repo.get(conv_id)  # Has .messages JSONB
transcript = conversation.messages  # Already structured list
```

### FR-002: Implement Status State Machine
**Priority**: P0
**Description**: Implement proper conversation status transitions with timeout detection.

**State Machine**:
```
active ─────────────────────────────┐
   │ (15 min timeout detected)      │
   ▼                                │
processing ─────────────────────────┤
   │          │                     │
   │ (success)│ (error)             │ (>30 min stuck)
   ▼          ▼                     ▼
processed   failed ←────────────────┘
```

**Technical Details**:
- Add `processing_started_at` timestamp column
- Stuck detection: `status='processing' AND processing_started_at < NOW() - INTERVAL '30 min'`
- Auto-transition stuck → failed with error message
- Log all transitions to `job_executions`

### FR-003: Voice Cache Refresh After Text Processing
**Priority**: P0
**Description**: Invalidate `users.cached_voice_prompt` after text post-processing completes.

**Technical Details**:
- After Stage 8 (Cache Invalidation) in `PostProcessor`:
  - Set `user.cached_voice_prompt = NULL`
  - Set `user.cached_voice_prompt_at = NULL`
- Next voice call will regenerate from fresh data
- Log cache invalidation in `job_executions`

### FR-004: Column Alignment (summary_text vs nikita_summary_text)
**Priority**: P1
**Description**: Ensure voice and text read/write the same summary columns.

**Current State**:
- Post-processing writes: `daily_summaries.summary_text`
- Voice reads: `daily_summaries.nikita_summary_text`
- Template generator: Tries both with fallback

**Solution**:
- Standardize on `summary_text` as the canonical column
- Update voice server tools to read `summary_text`
- Keep `nikita_summary_text` for backward compatibility (but don't write to it)
- Add migration to copy existing `nikita_summary_text` → `summary_text`

### FR-005: Job Execution Logging
**Priority**: P1
**Description**: Log all post-processing events to `job_executions` for observability.

**Events to Log**:
- Processing started: `job_type='post_processing', status='running'`
- Processing completed: `status='completed', result={stages, duration_ms}`
- Processing failed: `status='failed', error_message, stack_trace`
- Stuck detection: `job_type='stuck_detection', conversation_ids=[...]`

### FR-006: Retry Logic
**Priority**: P1
**Description**: Implement retry with exponential backoff for transient failures.

**Technical Details**:
- Max retries: 3
- Backoff: 1s, 5s, 30s
- Retry on: Neo4j timeout, LLM rate limit, transient DB errors
- Don't retry on: Invalid data, permanent failures
- Track retry count in conversation metadata

---

## User Stories

### US-1: Reliable Memory Updates
**As a** user **I want** my conversations to be processed into long-term memory **So that** Nikita remembers what we talked about.

**Acceptance Criteria**:
- [ ] AC-1.1: Post-processing completes for 99% of conversations
- [ ] AC-1.2: Threads and thoughts created from conversation
- [ ] AC-1.3: Graphiti graphs updated with new facts
- [ ] AC-1.4: Daily summary reflects all conversations

**Priority**: P0

### US-2: Voice-Text Consistency
**As a** user **I want** voice calls to know what I said in text **So that** Nikita feels like the same person across modalities.

**Acceptance Criteria**:
- [ ] AC-2.1: Voice calls receive today's text summaries
- [ ] AC-2.2: Voice context refreshed after text processing
- [ ] AC-2.3: Same summary data available to both channels
- [ ] AC-2.4: Refresh happens within 5 minutes of text processing

**Priority**: P0

### US-3: Processing Observability
**As an** engineer **I want** to see why post-processing failed **So that** I can debug and fix issues.

**Acceptance Criteria**:
- [ ] AC-3.1: All processing runs logged to `job_executions`
- [ ] AC-3.2: Error messages include stage that failed
- [ ] AC-3.3: Stack traces captured for exceptions
- [ ] AC-3.4: Admin dashboard shows processing stats

**Priority**: P1

### US-4: No Stuck Conversations
**As a** user **I want** my conversations to eventually process **So that** they don't get stuck forever.

**Acceptance Criteria**:
- [ ] AC-4.1: Stuck detection runs every 5 minutes
- [ ] AC-4.2: Conversations stuck >30 min marked as failed
- [ ] AC-4.3: Failed conversations can be manually reprocessed
- [ ] AC-4.4: Alert generated when stuck count > 5

**Priority**: P1

---

## Non-Functional Requirements

### NFR-001: Reliability
- Post-processing success rate: ≥99%
- Retry success rate: ≥80% of transient failures

### NFR-002: Performance
- Processing latency: <60s per conversation
- Stuck detection: <5s per scan
- Voice cache invalidation: <100ms

### NFR-003: Observability
- All failures logged with context
- Metrics: processing_time, success_rate, retry_count
- Admin visibility into processing queue

---

## Constraints & Assumptions

### Constraints
- Must maintain backward compatibility with existing conversations
- Cannot drop `nikita_summary_text` column (legacy data)
- pg_cron can only run every minute (not seconds)

### Assumptions
- `Conversation.messages` JSONB contains full message history
- `job_executions` table exists and is used by other pg_cron jobs
- Voice agent reads `daily_summaries` on each call start

---

## Out of Scope

- Text agent message history changes (covered in Spec 030)
- Voice agent optimization (covered in Spec 032)
- New post-processing stages
- Message storage format changes

---

## Technical Design Notes

### The Adapter Bug

```python
# CURRENT (BROKEN) - nikita/post_processing/adapter.py:24
messages = await conv_repo.get_messages(conv_id)  # AttributeError!

# FIX - Use conversation.messages directly
async def get_conversation_transcript(self, conversation_id: UUID) -> list[dict]:
    """Get conversation transcript from messages JSONB."""
    conversation = await self._session.get(Conversation, conversation_id)
    if not conversation or not conversation.messages:
        return []
    return conversation.messages  # Already a list of dicts
```

### Status State Machine Implementation

```python
class ConversationStatus(str, Enum):
    ACTIVE = "active"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"

# In ConversationRepository
async def mark_processing(self, conv_id: UUID) -> None:
    """Mark conversation as processing with timestamp."""
    conv = await self.session.get(Conversation, conv_id)
    conv.status = ConversationStatus.PROCESSING
    conv.processing_started_at = datetime.now(UTC)
    await self.session.commit()

async def detect_stuck(self, timeout_minutes: int = 30) -> list[UUID]:
    """Find conversations stuck in processing."""
    cutoff = datetime.now(UTC) - timedelta(minutes=timeout_minutes)
    result = await self.session.execute(
        select(Conversation.id)
        .where(Conversation.status == "processing")
        .where(Conversation.processing_started_at < cutoff)
    )
    return [row[0] for row in result.all()]
```

### Voice Cache Invalidation

```python
# In PostProcessor, after Stage 8
async def _invalidate_voice_cache(self, user_id: UUID) -> None:
    """Invalidate cached voice prompt so next call gets fresh context."""
    user = await self._user_repo.get(user_id)
    user.cached_voice_prompt = None
    user.cached_voice_prompt_at = None
    await self._session.commit()

    logger.info(f"Voice cache invalidated for user {user_id}")
```

### Key Files to Modify

| File | Change |
|------|--------|
| `nikita/post_processing/adapter.py` | Fix get_messages bug |
| `nikita/db/repositories/conversation_repository.py` | Add detect_stuck(), get() |
| `nikita/context/post_processor.py` | Add voice cache invalidation |
| `nikita/api/routes/tasks.py` | Add stuck detection endpoint |
| `nikita/db/models/conversation.py` | Add processing_started_at column |
| `nikita/agents/voice/server_tools.py` | Read summary_text not nikita_summary_text |

---

## Open Questions

*No open questions requiring clarification at this time.*

---

## References

- [Research: Nikita Memory Continuity PRD](docs-to-process/2026-01-19-continuity-memory-prd/)
- [Post-Processing Module](nikita/context/CLAUDE.md)
- Spec 012: Context Engineering
- Spec 030: Text Continuity (message history)
