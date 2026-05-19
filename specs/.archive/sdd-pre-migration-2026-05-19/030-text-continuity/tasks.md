# Tasks: Text Agent Message History and Continuity

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

---

## Progress Summary

| Phase | Tasks | Completed | Status |
|-------|-------|-----------|--------|
| US-1: Short Message Continuity | 7 | 7 | ✅ Complete |
| US-2: Same-Day Return Continuity | 4 | 4 | ✅ Complete |
| US-3: Thread Follow-Up | 4 | 4 | ✅ Complete |
| US-4: Returning User Experience | 3 | 3 | ✅ Complete |
| Cross-Cutting | 4 | 4 | ✅ Complete |
| **Total** | **22** | **22** | **✅ COMPLETE (100%)** |

---

## US-1: Short Message Continuity (P0)

### T1.1: Create HistoryLoader Class

- **Status**: [x] Complete
- **File**: `nikita/agents/text/history.py` (NEW)
- **Estimate**: M (2-3 hours)
- **Dependencies**: None

**Description**: Create a new `HistoryLoader` class responsible for retrieving and formatting conversation history for PydanticAI's `message_history` parameter.

**TDD Steps**:
1. ✅ Write test: `test_history_loader_empty_conversation`
2. ✅ Write test: `test_history_loader_formats_messages`
3. ✅ Write test: `test_history_loader_respects_limit`
4. ✅ Implement `HistoryLoader` class
5. ✅ Verify all tests pass

**Acceptance Criteria**:
- [x] AC-T1.1.1: Class accepts `conversation_id` and `limit` parameters
- [x] AC-T1.1.2: Returns `list[ModelMessage]` compatible with PydanticAI
- [x] AC-T1.1.3: Handles empty conversation gracefully (returns None, not empty list)
- [x] AC-T1.1.4: Preserves message order (oldest first)
- [x] AC-T1.1.5: Uses `ModelMessagesTypeAdapter.validate_python()` for conversion
- [x] AC-T1.1.6: Converts "nikita" role to `ModelResponse` with `TextPart`
- [x] AC-T1.1.7: Handles empty messages gracefully (returns None to trigger fresh prompt)

---

### T1.2: Add get_message_history() to Repository

- **Status**: [x] Complete
- **File**: `nikita/db/repositories/conversation_repository.py` (MODIFY)
- **Estimate**: S (1 hour)
- **Dependencies**: None
- **Parallel**: [P]

**Description**: Add method to retrieve raw message history from `conversations.messages` JSONB column.

**Implementation Note**: Repository method not needed - conversation.messages JSONB is loaded directly via Telegram MessageHandler and passed through handler chain. This is more efficient than a separate query.

**TDD Steps**:
1. ✅ Write test: `test_get_message_history_returns_messages` (covered by history.py tests)
2. ✅ Write test: `test_get_message_history_with_limit` (covered by history.py tests)
3. ✅ Implement loading via MessageHandler pass-through
4. ✅ Verify all tests pass (23 history tests)

**Acceptance Criteria**:
- [x] AC-T1.2.1: Method returns messages from JSONB column
- [x] AC-T1.2.2: Respects `limit` parameter (returns last N messages)
- [x] AC-T1.2.3: Returns empty list if no conversation found
- [x] AC-T1.2.4: Query executes in <50ms (direct JSONB access via ORM)

---

### T1.3: Implement PydanticAI ModelMessage Formatting

- **Status**: [x] Complete
- **File**: `nikita/agents/text/history.py` (MODIFY)
- **Estimate**: M (2-3 hours)
- **Dependencies**: T1.1

**Description**: Convert raw message dicts to PydanticAI `ModelMessage` types, ensuring tool calls and returns are properly paired.

**TDD Steps**:
1. ✅ Write test: `test_format_user_message`
2. ✅ Write test: `test_format_assistant_message`
3. ✅ Write test: `test_format_tool_call_pair`
4. ✅ Write test: `test_removes_unpaired_tool_calls`
5. ✅ Implement formatting logic
6. ✅ Verify all tests pass (23 tests in test_history.py)

**Acceptance Criteria**:
- [x] AC-T1.3.1: User messages formatted as `ModelRequest` with `UserPromptPart`
- [x] AC-T1.3.2: Assistant messages formatted as `ModelResponse` with `TextPart`
- [x] AC-T1.3.3: Tool calls have paired tool returns (PydanticAI requirement)
- [x] AC-T1.3.4: Unpaired tool calls at end of history are excluded

---

### T1.4: Add message_history to agent.run()

- **Status**: [x] Complete
- **File**: `nikita/agents/text/agent.py` (MODIFY), `nikita/agents/text/handler.py` (MODIFY), `nikita/platforms/telegram/message_handler.py` (MODIFY)
- **Estimate**: S (1 hour)
- **Dependencies**: T1.3

**Description**: Modify `generate_response()` to load and pass `message_history` to `nikita_agent.run()`.

**Implementation**:
- Telegram MessageHandler passes `conversation.messages` and `conversation.id` to handler
- Text agent handler.py injects into NikitaDeps
- agent.py generate_response() calls load_message_history() and passes to agent.run()

**TDD Steps**:
1. ✅ Write test: `test_generate_response_passes_history`
2. ✅ Write test: `test_generate_response_without_history`
3. ✅ Modify `generate_response()` function
4. ✅ Wire through handler chain (Telegram → handler → agent)
5. ✅ Verify all tests pass (206 tests)

**Acceptance Criteria**:
- [x] AC-T1.4.1: `message_history` parameter passed to `agent.run()`
- [x] AC-T1.4.2: History loaded via `load_message_history()` from history.py
- [x] AC-T1.4.3: Graceful degradation if history unavailable (message_history=None)
- [x] AC-T1.4.4: History loading logged for debugging ([HISTORY-DEBUG] prefix)
- [x] AC-T1.4.5: `message_history=None` for first message (triggers `@agent.instructions`)
- [x] AC-T1.4.6: `message_history` populated for subsequent messages
- [x] AC-T1.4.7: Session boundary detection based on conversation_messages length

---

### T1.5: Implement Token Budgeting for History Tier

- **Status**: [x] Complete
- **File**: `nikita/agents/text/history.py` (MODIFY)
- **Estimate**: M (2-3 hours)
- **Dependencies**: T1.3

**Description**: Implement token counting and truncation to keep history within 1500-3000 token budget.

**TDD Steps**:
1. ✅ Write test: `test_token_count_accurate`
2. ✅ Write test: `test_truncates_oldest_when_over_budget`
3. ✅ Write test: `test_respects_max_token_budget`
4. ✅ Implement token budgeting via `load_message_history()` token_budget param
5. ✅ Verify all tests pass

**Acceptance Criteria**:
- [x] AC-T1.5.1: Token counting uses `tiktoken` or equivalent (cl100k_base encoder)
- [x] AC-T1.5.2: History truncated from oldest when over 3000 tokens
- [x] AC-T1.5.3: Minimum 10 turns preserved even if under budget (configurable limit)
- [x] AC-T1.5.4: Token count logged in debug output

---

### T1.6: Write Unit Tests for HistoryLoader

- **Status**: [x] Complete
- **File**: `tests/agents/text/test_history.py` (NEW)
- **Estimate**: M (2 hours)
- **Dependencies**: T1.1-T1.5

**Description**: Comprehensive unit test suite for HistoryLoader class.

**Test Coverage**:
- [x] Empty conversation handling
- [x] Message formatting (user/assistant/tool)
- [x] Token budget enforcement
- [x] Truncation order (oldest first)
- [x] Tool call pairing
- [x] Performance (<50ms retrieval)

**Acceptance Criteria**:
- [x] AC-T1.6.1: ≥90% code coverage for history.py (23 tests)
- [x] AC-T1.6.2: All edge cases covered
- [x] AC-T1.6.3: Tests pass in CI

---

### T1.7: Safe Tool Call Pairing in Truncation (NEW)

- **Status**: [x] Complete
- **File**: `nikita/agents/text/history.py` (MODIFY)
- **Estimate**: S (1 hour)
- **Dependencies**: T1.1

**Description**: Implement safe truncation that preserves `ToolCallPart`/`ToolReturnPart` pairs per PydanticAI requirements. When slicing message history, unpaired tool calls at the truncation boundary must be excluded.

**TDD Steps**:
1. ✅ Write test: `test_truncation_preserves_tool_pairs`
2. ✅ Write test: `test_unpaired_tool_call_excluded`
3. ✅ Write test: `test_tool_return_without_call_excluded`
4. ✅ Implement safe truncation logic (in _truncate_history)
5. ✅ Verify all tests pass

**Acceptance Criteria**:
- [x] AC-T1.7.1: After truncation, every `ToolCallPart` has matching `ToolReturnPart`
- [x] AC-T1.7.2: Unpaired tool calls at truncation boundary are excluded
- [x] AC-T1.7.3: Test verifies pairing with mock tool call/return sequences
- [x] AC-T1.7.4: Logs warning when tool calls excluded due to pairing

---

## US-2: Same-Day Return Continuity (P0)

### T2.1: Enhance _load_context() for Daily Summaries

- **Status**: [x] Complete
- **File**: `nikita/meta_prompts/service.py` (MODIFY)
- **Estimate**: S (1 hour)
- **Dependencies**: None
- **Parallel**: [P]

**Description**: Ensure `daily_summaries` data is properly loaded and accessible in context.

**TDD Steps**:
1. ✅ Write test: `test_load_context_fetches_today_summary`
2. ✅ Write test: `test_load_context_no_summary_available`
3. ✅ Enhance `_load_memory_context()` method (lines 464-478)
4. ✅ Verify all tests pass

**Acceptance Criteria**:
- [x] AC-T2.1.1: Today's summary fetched from `daily_summaries` table
- [x] AC-T2.1.2: `summary_text` and `key_moments` both loaded
- [x] AC-T2.1.3: Graceful handling when no summary exists
- [x] AC-T2.1.4: Query completes in <30ms

---

### T2.2: Add today_summary to System Prompt Template

- **Status**: [x] Complete
- **File**: `nikita/meta_prompts/service.py` (MODIFY)
- **Estimate**: S (1 hour)
- **Dependencies**: T2.1

**Description**: Inject today's summary into the system prompt under a dedicated section.

**TDD Steps**:
1. ✅ Write test: `test_format_today_section_with_summary`
2. ✅ Write test: `test_format_today_section_without_summary`
3. ✅ Add `_format_today_section()` method (lines 736-771)
4. ✅ Wire into `_format_template()` (line 676)
5. ✅ Verify all tests pass

**Acceptance Criteria**:
- [x] AC-T2.2.1: `{{today_summaries}}` placeholder replaced with formatted section
- [x] AC-T2.2.2: Section header "Earlier today:" when summary exists
- [x] AC-T2.2.3: Returns "None" when no summary
- [x] AC-T2.2.4: Token budget: ≤500 tokens for today section (truncation at 500 chars)

---

### T2.3: Add key_moments Extraction and Injection

- **Status**: [x] Complete
- **File**: `nikita/meta_prompts/service.py` (MODIFY), `nikita/meta_prompts/models.py` (MODIFY)
- **Estimate**: S (1 hour)
- **Dependencies**: T2.1

**Description**: Extract and format key moments from today for injection.

**TDD Steps**:
1. ✅ Write test: `test_key_moments_formatted_as_bullets`
2. ✅ Write test: `test_key_moments_limited_to_5`
3. ✅ Write test: `test_key_moments_recent_prioritized`
4. ✅ Add `today_key_moments` field to MetaPromptContext (models.py:242)
5. ✅ Implement key moments extraction in `_load_memory_context()` (lines 470-478)
6. ✅ Implement key moments formatting in `_format_today_section()` (lines 762-770)
7. ✅ Verify all tests pass

**Acceptance Criteria**:
- [x] AC-T2.3.1: Key moments formatted as bullet points
- [x] AC-T2.3.2: Maximum 5 key moments injected ([-5:] slice)
- [x] AC-T2.3.3: Most recent moments prioritized (last 5)
- [x] AC-T2.3.4: Natural language formatting (not JSON)

---

### T2.4: Write Unit Tests for Today Buffer

- **Status**: [x] Complete
- **File**: `tests/meta_prompts/test_today_buffer.py` (NEW)
- **Estimate**: M (2 hours)
- **Dependencies**: T2.1-T2.3

**Test Coverage**:
- [x] Summary loading (TestKeyMomentsExtraction)
- [x] Template injection (TestTodaySummaryIntegration)
- [x] Key moments formatting (TestTodaySummaryFormatting)
- [x] Token budget (TestTodaySummaryTokenBudget)
- [x] Edge cases (no summary, empty moments)
- [x] Model fields (TestModelContextFields)

**Acceptance Criteria**:
- [x] AC-T2.4.1: All today buffer logic tested (12 tests)
- [x] AC-T2.4.2: Mocked Agent initialization
- [x] AC-T2.4.3: Tests pass (12/12)

---

## US-3: Thread Follow-Up (P1) ✅ COMPLETE

### T3.1: Add get_open_threads() to Repository

- **Status**: [x] Complete (already existed in thread_repository.py)
- **File**: `nikita/db/repositories/thread_repository.py` (ALREADY EXISTS)
- **Estimate**: S (1 hour)
- **Dependencies**: None
- **Parallel**: [P]

**Description**: Add method to retrieve open conversation threads for a user.

**TDD Steps**:
1. ✅ Method already exists: `get_open_threads()` in thread_repository.py
2. ✅ Filters by status='open'
3. ✅ Orders by created_at descending
4. ✅ Verified in test_thread_surfacing.py

**Acceptance Criteria**:
- [x] AC-T3.1.1: Returns threads with `status='open'`
- [x] AC-T3.1.2: Filters by `user_id`
- [x] AC-T3.1.3: Orders by `created_at` descending (most recent first)
- [x] AC-T3.1.4: Limits to 10 threads max

---

### T3.2: Add Open Threads Injection to MetaPromptService

- **Status**: [x] Complete
- **File**: `nikita/meta_prompts/service.py` (MODIFY)
- **Estimate**: M (2 hours)
- **Dependencies**: T3.1

**Description**: Inject open threads into system prompt for Nikita to reference.

**TDD Steps**:
1. ✅ Write test: `test_format_open_threads_section_with_threads`
2. ✅ Write test: `test_format_open_threads_section_empty`
3. ✅ Implement `_format_open_threads_section()` (lines 863-909)
4. ✅ Wire into `_format_template()` (line 692)
5. ✅ Verify all tests pass

**Acceptance Criteria**:
- [x] AC-T3.2.1: `{{open_threads}}` placeholder replaced
- [x] AC-T3.2.2: Section header "Unfinished Topics:"
- [x] AC-T3.2.3: Each thread formatted: "- [type]: [content]"
- [x] AC-T3.2.4: Token budget: ≤400 tokens (~1600 chars)

---

### T3.3: Implement Thread Prioritization

- **Status**: [x] Complete
- **File**: `nikita/meta_prompts/service.py` (MODIFY)
- **Estimate**: M (2 hours)
- **Dependencies**: T3.2

**Description**: Prioritize threads by recency and importance, deprioritize >7 days old.

**TDD Steps**:
1. ✅ Write test: `test_prioritize_threads_by_recency`
2. ✅ Write test: `test_old_threads_get_50_percent_penalty`
3. ✅ Write test: `test_max_5_threads_returned`
4. ✅ Implement `_prioritize_threads()` static method (lines 818-861)
5. ✅ Verify all tests pass

**Acceptance Criteria**:
- [x] AC-T3.3.1: Threads sorted by combined recency + type importance score
- [x] AC-T3.3.2: Threads >7 days old get 50% score penalty
- [x] AC-T3.3.3: Maximum 5 threads included in prompt
- [x] AC-T3.3.4: Thread importance from type (promise=10, unresolved=10, curiosity=7, callback=4)

---

### T3.4: Write Unit Tests for Thread Surfacing

- **Status**: [x] Complete
- **File**: `tests/meta_prompts/test_thread_surfacing.py` (NEW)
- **Estimate**: M (2 hours)
- **Dependencies**: T3.1-T3.3

**Test Coverage**:
- [x] Thread retrieval (TestThreadLoadingWithCreatedAt: 1 test)
- [x] Prioritization algorithm (TestThreadPrioritization: 5 tests)
- [x] Template injection (TestOpenThreadsFormatting: 4 tests)
- [x] Token budget (test_format_open_threads_token_budget)
- [x] Edge cases (test_empty_threads_returns_empty_list, test_format_open_threads_section_empty)
- [x] Model fields (TestModelContextFields: 2 tests)
- [x] Template integration (TestTemplateIntegration: 1 test)

**Acceptance Criteria**:
- [x] AC-T3.4.1: All thread logic tested (13 tests)
- [x] AC-T3.4.2: Mocked Agent to avoid API key requirement
- [x] AC-T3.4.3: Tests pass in CI (13/13)

---

## US-4: Returning User Experience (P2) ✅ COMPLETE

### T4.1: Add get_last_conversation_summary() to Repository

- **Status**: [x] Complete
- **File**: `nikita/db/repositories/conversation_repository.py` (MODIFY)
- **Estimate**: S (1 hour)
- **Dependencies**: None
- **Parallel**: [P]

**Description**: Add method to retrieve summary of user's last conversation.

**TDD Steps**:
1. ✅ Write test: `test_get_last_conversation_summary`
2. ✅ Write test: `test_returns_none_for_current_session`
3. ✅ Implement method (lines 447-487)
4. ✅ Verify all tests pass

**Acceptance Criteria**:
- [x] AC-T4.1.1: Returns `conversation_summary` from most recent non-current conversation
- [x] AC-T4.1.2: Excludes current session (by conversation_id)
- [x] AC-T4.1.3: Returns None if no prior conversations
- [x] AC-T4.1.4: Only returns summaries >24h old

---

### T4.2: Populate {{last_conversation_summary}} Template Variable

- **Status**: [x] Complete
- **File**: `nikita/meta_prompts/service.py` (MODIFY)
- **Estimate**: S (1 hour)
- **Dependencies**: T4.1

**Description**: Populate the existing template variable with actual data.

**TDD Steps**:
1. ✅ Write test: `test_last_conversation_summary_populated`
2. ✅ Write test: `test_last_conversation_summary_none`
3. ✅ Implement `_format_last_conversation_section()` (lines 911-944)
4. ✅ Wire into `_format_template()` (lines 689, 1187)
5. ✅ Verify all tests pass

**Acceptance Criteria**:
- [x] AC-T4.2.1: `{{last_conversation_summary}}` replaced with actual summary
- [x] AC-T4.2.2: Prefix "Last time we talked: " added
- [x] AC-T4.2.3: Truncated to ≤300 tokens (~1200 chars) if needed
- [x] AC-T4.2.4: "No prior conversation" when none available

---

### T4.3: Write Unit Tests for Last Conversation

- **Status**: [x] Complete
- **File**: `tests/meta_prompts/test_last_conversation.py` (NEW)
- **Estimate**: S (1 hour)
- **Dependencies**: T4.1-T4.2

**Test Coverage**:
- [x] Summary retrieval (TestRepositoryGetLastConversationSummary: 4 tests)
- [x] Template population (TestFormatLastConversationSection: 3 tests)
- [x] Truncation (test_format_truncates_long_summary)
- [x] Edge cases (test_returns_none_for_no_prior_conversations, test_format_without_summary)
- [x] Model fields (TestModelContextLastConversationField: 3 tests)

**Acceptance Criteria**:
- [x] AC-T4.3.1: All last conversation logic tested (11 tests)
- [x] AC-T4.3.2: Tests pass in CI (11/11)

---

## Cross-Cutting: Token Budget & Logging (P1)

### T5.1: Implement Combined Token Budget Manager

- **Status**: [x] Complete
- **File**: `nikita/agents/text/token_budget.py` (NEW)
- **Estimate**: M (2-3 hours)
- **Dependencies**: T1.5, T2.1-T2.3, T3.2, T4.2

**Description**: Central token budget manager for all context tiers.

**TDD Steps**:
1. ✅ Write test: `test_total_budget_respected`
2. ✅ Write test: `test_tier_budgets_enforced`
3. ✅ Write test: `test_hard_cap_never_exceeded`
4. ✅ Implement TokenBudgetManager class
5. ✅ Verify all tests pass (13 tests)

**Acceptance Criteria**:
- [x] AC-T5.1.1: Total budget: 4100 tokens (target), 6150 (hard cap)
- [x] AC-T5.1.2: Tier budgets: History 3000, Today 500, Threads 400, Last 300
- [x] AC-T5.1.3: Returns truncated content within budget
- [x] AC-T5.1.4: Provides token usage breakdown

---

### T5.2: Implement Truncation Priority Logic

- **Status**: [x] Complete
- **File**: `nikita/agents/text/token_budget.py` (MODIFY)
- **Estimate**: M (2 hours)
- **Dependencies**: T5.1

**Description**: When over budget, truncate in order: Last Conv → Threads → Today → History (oldest).

**TDD Steps**:
1. ✅ Write test: `test_truncation_order_last_conv_first`
2. ✅ Write test: `test_truncation_preserves_history_priority`
3. ✅ Write test: `test_minimum_history_preserved`
4. ✅ Implement truncation logic (in allocate() method)
5. ✅ Verify all tests pass (13 tests in test_token_budget.py)

**Acceptance Criteria**:
- [x] AC-T5.2.1: Truncation order: Last Conv → Threads → Today → History
- [x] AC-T5.2.2: Within History, oldest messages truncated first
- [x] AC-T5.2.3: Minimum 10 history turns always preserved (~100 tokens min)
- [x] AC-T5.2.4: Truncation logged with token counts (truncation_info dict)

---

### T5.3: Add context_snapshot Logging

- **Status**: [x] Complete
- **File**: `nikita/meta_prompts/service.py` (MODIFY)
- **Estimate**: S (1 hour)
- **Dependencies**: T5.1

**Description**: Log context composition to `generated_prompts.context_snapshot` JSONB.

**TDD Steps**:
1. ✅ Write test: `test_create_context_snapshot_with_all_fields`
2. ✅ Write test: `test_context_snapshot_fields` (with missing tiers, timestamp)
3. ✅ Implement `create_context_snapshot()` static method
4. ✅ Verify all tests pass (6 tests in test_context_snapshot.py)

**Acceptance Criteria**:
- [x] AC-T5.3.1: `context_snapshot` dict created with all fields
- [x] AC-T5.3.2: Fields: `message_history_count`, `message_history_tokens`, `today_summary_present`, `today_tokens`, `open_threads_count`, `threads_tokens`, `last_conversation_present`, `last_conversation_tokens`, `total_tokens`, `created_at`
- [x] AC-T5.3.3: Static method available for prompt generation
- [x] AC-T5.3.4: JSON serializable for JSONB storage and debugging

---

### T5.4: Write Integration Tests for Full Context Build

- **Status**: [x] Complete
- **File**: `tests/meta_prompts/test_full_context_integration.py` (NEW)
- **Estimate**: L (3-4 hours)
- **Dependencies**: All above tasks

**Test Coverage**:
- [x] Full context build with all 4 tiers
- [x] Token budget enforcement end-to-end
- [x] MetaPromptContext integration (mocked DB)
- [x] Latency under 200ms (50ms token allocation, 10ms snapshot creation)

**Acceptance Criteria**:
- [x] AC-T5.4.1: Integration test validates full pipeline (Context → TierContent → Budget → Snapshot)
- [x] AC-T5.4.2: All 4 tiers populated correctly (9 tests covering all tiers)
- [x] AC-T5.4.3: Token budget respected under load (large content, truncation pressure tests)
- [x] AC-T5.4.4: Latency <200ms for context build (<50ms for token allocation, <10ms for snapshot)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-19 | Initial task breakdown |
| 1.1 | 2026-01-20 | US-1 (Short Message Continuity) COMPLETE - 7/7 tasks done, 23 tests passing |
| 1.2 | 2026-01-20 | US-2 (Same-Day Return Continuity) COMPLETE - 4/4 tasks done, 12 today buffer tests |
| 1.3 | 2026-01-20 | US-3 (Thread Follow-Up) COMPLETE - 4/4 tasks done, 13 thread surfacing tests |
| 1.4 | 2026-01-20 | US-4 (Returning User Experience) COMPLETE - 3/3 tasks done, 11 last conversation tests |
| 2.0 | 2026-01-20 | **SPEC 030 COMPLETE** - Cross-Cutting T5.1-T5.4 done, 87 total tests (13 token budget + 6 context snapshot + 9 integration + 59 US-1 to US-4) |
