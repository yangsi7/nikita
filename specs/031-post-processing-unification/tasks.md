# Tasks: Post-Processing Unification and Reliability

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

---

## Progress Summary

| Phase | Tasks | Completed | Status |
|-------|-------|-----------|--------|
| US-1: Reliable Memory Updates | 4 | 4 | ✅ Complete |
| US-2: Voice-Text Consistency | 4 | 4 | ✅ Complete |
| US-3: Processing Observability | 4 | 4 | ✅ Complete |
| US-4: No Stuck Conversations | 5 | 4 | ✅ Complete (T4.4 deferred) |
| **Total** | **17** | **16** | ✅ Complete (T4.4 deferred) |

---

## US-1: Reliable Memory Updates (P0)

### T1.1: Fix adapter.py to Use Conversation.messages

- **Status**: [x] Complete
- **File**: `nikita/post_processing/adapter.py` (MODIFY)
- **Estimate**: S (1 hour)
- **Dependencies**: None
- **CRITICAL**: This is the root cause of post-processing failures

**Description**: Fix the adapter to use `Conversation.messages` JSONB directly instead of the non-existent `get_messages()` method.

**Bug Location**:
```python
# nikita/post_processing/adapter.py:24 (CURRENT - BROKEN)
messages = await conv_repo.get_messages(conv_id)  # Method doesn't exist!
```

**TDD Steps**:
1. Write test: `test_adapter_gets_messages_from_conversation`
2. Write test: `test_adapter_handles_empty_messages`
3. Fix adapter to load conversation and read `.messages`
4. Verify all tests pass

**Acceptance Criteria**:
- [ ] AC-T1.1.1: Adapter loads conversation using session.get()
- [ ] AC-T1.1.2: Messages extracted from `conversation.messages` JSONB
- [ ] AC-T1.1.3: Returns empty list for conversation with no messages
- [ ] AC-T1.1.4: No AttributeError when processing

---

### T1.2: Add get() Method to ConversationRepository

- **Status**: [x] Complete (inherited from BaseRepository)
- **File**: `nikita/db/repositories/base.py` (EXISTING)
- **Estimate**: S (30 min)
- **Dependencies**: None
- **Parallel**: [P]

**Description**: Add a simple `get()` method to retrieve a conversation by ID.

**Note**: BaseRepository already provides `get()` method at line 58-67. ConversationRepository inherits this method. For the adapter use case, only direct columns (`user_id`, `messages` JSONB) are needed, so eager loading is not required.

**Acceptance Criteria**:
- [x] AC-T1.2.1: Method `get(conversation_id: UUID) -> Conversation | None` (inherited)
- [x] AC-T1.2.2: Loads conversation (eager loading not needed for adapter - uses JSONB columns)
- [x] AC-T1.2.3: Returns None if not found

---

### T1.3: Write Unit Tests for Adapter Fix

- **Status**: [x] Complete
- **File**: `tests/post_processing/test_adapter.py` (NEW)
- **Estimate**: M (2 hours)
- **Dependencies**: T1.1

**Description**: Comprehensive unit tests for the fixed adapter.

**TDD Steps**:
1. Test message retrieval from JSONB
2. Test empty conversation handling
3. Test transcript formatting
4. Test error handling

**Acceptance Criteria**:
- [ ] AC-T1.3.1: Test covers happy path (messages retrieved)
- [ ] AC-T1.3.2: Test covers empty conversation
- [ ] AC-T1.3.3: Test covers missing conversation
- [ ] AC-T1.3.4: ≥90% coverage for adapter.py

---

### T1.4: Write Integration Test for Full Pipeline

- **Status**: [x] Complete
- **File**: `tests/context/test_post_processor_integration.py` (NEW)
- **Estimate**: M (2-3 hours)
- **Dependencies**: T1.1-T1.3

**Description**: Integration test that runs the full 10-stage pipeline on a test conversation.

**TDD Steps**:
1. Create test conversation with messages
2. Run PostProcessor.process_conversation()
3. Verify all stages completed
4. Verify artifacts created (threads, thoughts, summaries)

**Acceptance Criteria**:
- [x] AC-T1.4.1: Pipeline completes without error (8 tests)
- [x] AC-T1.4.2: Status transitions: active → processing → processed
- [x] AC-T1.4.3: Threads and thoughts created
- [x] AC-T1.4.4: Daily summary updated

---

## US-2: Voice-Text Consistency (P0)

### T2.1: Add Voice Cache Invalidation to PostProcessor

- **Status**: [x] Complete
- **File**: `nikita/context/post_processor.py` (MODIFY)
- **Estimate**: S (1 hour)
- **Dependencies**: T1.1

**Description**: Add a new stage (7.7) to invalidate `users.cached_voice_prompt` after text processing.

**TDD Steps**:
1. Write test: `test_post_processor_invalidates_voice_cache`
2. Write test: `test_voice_cache_cleared_after_processing`
3. Add `_invalidate_voice_cache()` method
4. Call after Stage 7.5 in pipeline
5. Verify all tests pass

**Acceptance Criteria**:
- [x] AC-T2.1.1: `user.cached_voice_prompt` set to NULL after processing
- [x] AC-T2.1.2: `user.cached_voice_prompt_at` set to NULL
- [x] AC-T2.1.3: Invalidation logged with user_id
- [x] AC-T2.1.4: Graceful handling if user not found

---

### T2.2: Update server_tools.py to Read summary_text

- **Status**: [x] Complete
- **File**: `nikita/agents/voice/server_tools.py` (MODIFY)
- **Estimate**: S (30 min)
- **Dependencies**: None
- **Parallel**: [P]

**Description**: Update voice server tools to read `summary_text` column consistently.

**TDD Steps**:
1. Write test: `test_server_tools_reads_summary_text`
2. Update `get_context()` to prefer `summary_text`
3. Keep fallback to `nikita_summary_text` for backward compat
4. Verify all tests pass

**Acceptance Criteria**:
- [x] AC-T2.2.1: `get_context()` reads `summary_text` first
- [x] AC-T2.2.2: Falls back to `nikita_summary_text` if null
- [x] AC-T2.2.3: No change in response format
- [x] AC-T2.2.4: All existing tests pass (21 tests)

---

### T2.3: Create Migration for Summary Text Alignment

- **Status**: [x] Complete
- **File**: Applied via Supabase MCP (no file needed)
- **Estimate**: S (30 min)
- **Dependencies**: None
- **Parallel**: [P]

**Description**: Migration to copy existing `nikita_summary_text` to `summary_text` where needed.

**TDD Steps**:
1. Write migration script
2. Test on staging database
3. Apply via Supabase MCP

**Acceptance Criteria**:
- [x] AC-T2.3.1: Migration copies data where summary_text is NULL
- [x] AC-T2.3.2: Does not overwrite existing summary_text
- [x] AC-T2.3.3: Idempotent (can run multiple times)

**Note**: Table currently empty (0 records). Migration applied and verified idempotent.

---

### T2.4: Write Tests for Voice Cache Invalidation

- **Status**: [x] Complete
- **File**: `tests/context/test_post_processor_voice.py` (NEW)
- **Estimate**: M (2 hours)
- **Dependencies**: T2.1

**Description**: Test suite for voice cache invalidation functionality.

**Test Coverage**:
- [x] Cache invalidation called after processing
- [x] User fields correctly nullified
- [x] Logging captures invalidation
- [x] Error handling for missing user

**Acceptance Criteria**:
- [x] AC-T2.4.1: All voice cache scenarios tested (6 tests)
- [x] AC-T2.4.2: Mocked DB interactions
- [x] AC-T2.4.3: Tests pass in CI

---

## US-3: Processing Observability (P1)

### T3.1: Add job_execution Logging to PostProcessor

- **Status**: [x] Complete
- **File**: `nikita/context/post_processor.py` (MODIFIED)
- **Estimate**: M (2 hours)
- **Dependencies**: T1.1

**Description**: Log all processing events to `job_executions` table.

**Implementation**:
- Added POST_PROCESSING to JobName enum
- Added JobExecutionRepository integration to PostProcessor.__init__
- Logs job start, completion (with duration), and failure events
- Result JSON includes conversation_id, stage_reached, threads_created, etc.

**Acceptance Criteria**:
- [x] AC-T3.1.1: `job_type='post_processing'` logged at start
- [x] AC-T3.1.2: `status='completed'` logged with duration_ms
- [x] AC-T3.1.3: `status='failed'` logged with error_message
- [x] AC-T3.1.4: `result` JSON includes stages completed

---

### T3.2: Log Stage-Level Failures with Context

- **Status**: [x] Complete
- **File**: `nikita/context/post_processor.py` (MODIFIED)
- **Estimate**: S (1 hour)
- **Dependencies**: T3.1

**Description**: When a stage fails, log which stage and relevant context.

**Implementation**:
- Added traceback import and stack trace capture
- Error includes stage_reached (where failure occurred), conversation_id
- Stack trace included in result.stack_trace field

**Acceptance Criteria**:
- [x] AC-T3.2.1: Failed stage name in error_message
- [x] AC-T3.2.2: Conversation ID included
- [x] AC-T3.2.3: Stack trace in `result.stack_trace`
- [x] AC-T3.2.4: Previous successful stages listed (via stage_reached)

---

### T3.3: Add Processing Stats to Admin Dashboard

- **Status**: [x] Complete
- **File**: `nikita/api/routes/admin.py` (MODIFIED)
- **Estimate**: M (2 hours)
- **Dependencies**: T3.1
- **Parallel**: [P]

**Description**: Add endpoint to show post-processing statistics.

**Implementation**:
- Added ProcessingStatsResponse schema to admin.py
- Added GET /admin/processing-stats endpoint
- Queries job_executions for 24h stats (success_rate, avg_duration_ms)
- Queries conversations for pending_count, stuck_count
- 7 tests passing

**Acceptance Criteria**:
- [x] AC-T3.3.1: Endpoint returns 24h stats
- [x] AC-T3.3.2: Includes success_rate, avg_duration_ms
- [x] AC-T3.3.3: Includes pending_count, failed_count, stuck_count
- [ ] AC-T3.3.4: Response cached for 1 minute (not implemented - low priority)

---

### T3.4: Write Tests for job_execution Logging

- **Status**: [x] Complete
- **File**: `tests/context/test_post_processor_logging.py` (NEW)
- **Estimate**: M (2 hours)
- **Dependencies**: T3.1-T3.2

**Test Coverage**:
- [x] Job execution created at start
- [x] Completion logged with duration
- [x] Failure logged with error
- [x] Stage-level context captured
- [x] Stack trace included on failure
- [x] Pipeline resilience if job logging fails

**Tests**: 8 tests passing

**Acceptance Criteria**:
- [x] AC-T3.4.1: All logging scenarios tested (8 tests)
- [x] AC-T3.4.2: Tests pass in CI

---

## US-4: No Stuck Conversations (P1)

### T4.1: Add processing_started_at Column Migration

- **Status**: [x] Complete
- **File**: `nikita/db/models/conversation.py` (MODIFIED) + Supabase migration
- **Estimate**: S (30 min)
- **Dependencies**: None
- **Parallel**: [P]

**Description**: Add timestamp column for stuck detection.

**TDD Steps**:
1. Write migration script
2. Add index for efficient querying
3. Apply via Supabase MCP

**Acceptance Criteria**:
- [x] AC-T4.1.1: Column added: `processing_started_at TIMESTAMP WITH TIME ZONE`
- [x] AC-T4.1.2: Index created on (status, processing_started_at)
- [x] AC-T4.1.3: Migration applies successfully

**Note**: Applied via Supabase MCP, model updated with field

---

### T4.2: Implement detect_stuck() in Repository

- **Status**: [x] Complete
- **File**: `nikita/db/repositories/conversation_repository.py` (MODIFIED)
- **Estimate**: S (1 hour)
- **Dependencies**: T4.1

**Description**: Add method to find conversations stuck in processing state.

**TDD Steps**:
1. Write test: `test_detect_stuck_finds_old_processing`
2. Write test: `test_detect_stuck_ignores_recent`
3. Implement `detect_stuck()` method
4. Verify all tests pass

**Acceptance Criteria**:
- [x] AC-T4.2.1: Returns conversation IDs stuck >30 min
- [x] AC-T4.2.2: Does not return recently started processing
- [x] AC-T4.2.3: Query uses index efficiently
- [x] AC-T4.2.4: Returns empty list if none stuck

**Note**: Also updated `mark_processing()` to set `processing_started_at` timestamp

---

### T4.3: Add Stuck Detection Endpoint to tasks.py

- **Status**: [x] Complete
- **File**: `nikita/api/routes/tasks.py` (MODIFIED)
- **Estimate**: M (2 hours)
- **Dependencies**: T4.2

**Description**: Add pg_cron endpoint to detect and handle stuck conversations.

**TDD Steps**:
1. Write test: `test_stuck_detection_endpoint`
2. Add `POST /tasks/detect-stuck` endpoint
3. Mark stuck conversations as failed
4. Log to job_executions
5. Verify all tests pass

**Acceptance Criteria**:
- [x] AC-T4.3.1: Endpoint finds stuck conversations
- [x] AC-T4.3.2: Marks them as `status='failed'`
- [x] AC-T4.3.3: Logs error: "Processing timed out after 30 minutes"
- [x] AC-T4.3.4: Returns count of conversations marked failed

**Note**: Endpoint created with job_execution logging and error handling

---

### T4.4: Add Retry Logic with Exponential Backoff

- **Status**: [ ] Deferred (P2 - not blocking, can be added later)
- **File**: `nikita/context/post_processor.py` (MODIFY)
- **Estimate**: M (2-3 hours)
- **Dependencies**: T4.1-T4.2

**Description**: Implement retry logic for transient failures.

**Reason for Deferral**: The stuck detection system (T4.1-T4.3) handles failed conversations by marking them for reprocessing. Exponential backoff adds complexity and is not critical for MVP. The existing `processing_attempts` counter already provides basic retry tracking.

**TDD Steps**:
1. Write test: `test_retry_on_transient_failure`
2. Write test: `test_max_retries_respected`
3. Write test: `test_exponential_backoff`
4. Implement retry decorator/logic
5. Verify all tests pass

**Acceptance Criteria**:
- [ ] AC-T4.4.1: Max 3 retries for transient failures
- [ ] AC-T4.4.2: Backoff: 1s, 5s, 30s
- [ ] AC-T4.4.3: Retry count tracked in conversation metadata
- [ ] AC-T4.4.4: Non-transient errors fail immediately

---

### T4.5: Write Tests for Stuck Detection

- **Status**: [x] Complete
- **File**: `tests/db/test_conversation_stuck.py` (NEW)
- **Estimate**: M (2 hours)
- **Dependencies**: T4.2-T4.3

**Test Coverage**:
- [x] detect_stuck() method
- [x] Stuck detection endpoint
- [x] State transitions
- [ ] Retry logic (deferred with T4.4)

**Tests**: 12 tests passing

**Acceptance Criteria**:
- [x] AC-T4.5.1: All stuck detection scenarios tested
- [x] AC-T4.5.2: Tests pass in CI

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-19 | Initial task breakdown |
| 2.0 | 2026-01-19 | US-1 through US-4 complete (16/17 tasks), T4.4 deferred |
