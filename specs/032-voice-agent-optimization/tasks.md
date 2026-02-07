# Tasks: ElevenLabs Voice Agent Optimization

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

---

## Progress Summary

| Phase | Tasks | Completed | Status |
|-------|-------|-----------|--------|
| US-1: Voice Context at Call Start | 5 | 0 | Not Started |
| US-2: Mid-Call Memory Lookup | 5 | 0 | Not Started |
| US-3: Voice Conversation Memory | 5 | 0 | Not Started |
| US-4: Personality Consistency | 3 | 0 | Not Started |
| Cross-Cutting: Logging | 4 | 0 | Not Started |
| **Total** | **22** | **0** | **Not Started** |

---

## US-1: Voice Context at Call Start (P1)

### T1.1: Expand DynamicVariables Model

- **Status**: [ ] Not Started
- **File**: `nikita/agents/voice/models.py` (MODIFY)
- **Estimate**: M (2 hours)
- **Dependencies**: None

**Description**: Add 10+ new fields to DynamicVariables model for expanded context.

**New Fields**:
```python
# Context from text (FR-001)
today_summary: str = ""
last_conversation_summary: str = ""
nikita_mood_arousal: float = 0.5
nikita_mood_valence: float = 0.5
nikita_mood_dominance: float = 0.5
nikita_mood_intimacy: float = 0.5
nikita_daily_events: str = ""
active_conflict_type: str = ""
active_conflict_severity: float = 0.0
emotional_context: str = ""
user_backstory: str = ""
context_block: str = ""
```

**TDD Steps**:
1. Write test: `test_dynamic_vars_has_new_fields`
2. Write test: `test_dynamic_vars_serialization`
3. Add fields to DynamicVariables model
4. Verify all tests pass

**Acceptance Criteria**:
- [ ] AC-T1.1.1: All 12 new fields added to model
- [ ] AC-T1.1.2: Default values set (empty string, 0.5 for floats)
- [ ] AC-T1.1.3: JSON serialization works correctly
- [ ] AC-T1.1.4: Backward compatible (existing code works)

---

### T1.2: Update DynamicVariablesBuilder

- **Status**: [ ] Not Started
- **File**: `nikita/agents/voice/context.py` (MODIFY)
- **Estimate**: M (2-3 hours)
- **Dependencies**: T1.1

**Description**: Populate new fields in DynamicVariablesBuilder.build() method.

**TDD Steps**:
1. Write test: `test_builder_populates_today_summary`
2. Write test: `test_builder_populates_mood_4d`
3. Write test: `test_builder_populates_emotional_context`
4. Update `build()` method to fetch and populate new fields
5. Verify all tests pass

**Acceptance Criteria**:
- [ ] AC-T1.2.1: today_summary loaded from daily_summaries
- [ ] AC-T1.2.2: 4D mood loaded from nikita_emotional_states
- [ ] AC-T1.2.3: last_conversation_summary loaded
- [ ] AC-T1.2.4: context_block generated from all fields

---

### T1.3: Add Context Loading in /voice/initiate

- **Status**: [ ] Not Started
- **File**: `nikita/agents/voice/inbound.py` (MODIFY)
- **Estimate**: M (2 hours)
- **Dependencies**: T1.2

**Description**: Load additional context data in the initiate call flow.

**TDD Steps**:
1. Write test: `test_initiate_loads_full_context`
2. Write test: `test_initiate_handles_missing_data`
3. Add context loading before DynamicVariablesBuilder
4. Verify all tests pass

**Acceptance Criteria**:
- [ ] AC-T1.3.1: Daily summary loaded at call start
- [ ] AC-T1.3.2: Emotional state loaded
- [ ] AC-T1.3.3: User backstory loaded from onboarding
- [ ] AC-T1.3.4: Graceful handling if data missing

---

### T1.4: Add context_block Generation

- **Status**: [ ] Not Started
- **File**: `nikita/agents/voice/context.py` (MODIFY)
- **Estimate**: M (2 hours)
- **Dependencies**: T1.2

**Description**: Generate `context_block` string that matches text agent's personalized context.

**TDD Steps**:
1. Write test: `test_context_block_format`
2. Write test: `test_context_block_includes_key_info`
3. Implement _build_context_block() method
4. Verify all tests pass

**Acceptance Criteria**:
- [ ] AC-T1.4.1: context_block includes relationship state
- [ ] AC-T1.4.2: context_block includes recent events
- [ ] AC-T1.4.3: context_block includes emotional context
- [ ] AC-T1.4.4: Token budget ≤500 tokens

---

### T1.5: Write Tests for Expanded Dynamic Variables

- **Status**: [ ] Not Started
- **File**: `tests/agents/voice/test_dynamic_vars_expanded.py` (NEW)
- **Estimate**: M (2 hours)
- **Dependencies**: T1.1-T1.4

**Test Coverage**:
- [ ] All 30+ fields populated
- [ ] Default values correct
- [ ] Serialization to ElevenLabs format
- [ ] context_block content

**Acceptance Criteria**:
- [ ] AC-T1.5.1: ≥90% coverage for new code
- [ ] AC-T1.5.2: All edge cases covered
- [ ] AC-T1.5.3: Tests pass in CI

---

## US-2: Mid-Call Memory Lookup (P1)

### T2.1: Update get_memory Tool Description

- **Status**: [ ] Not Started
- **File**: `nikita/agents/voice/server_tools.py` (MODIFY)
- **Estimate**: S (30 min)
- **Dependencies**: None
- **Parallel**: [P]

**Description**: Update get_memory tool description per ElevenLabs best practice.

**New Description**:
```
Search your memory for past events and conversations.

WHEN TO USE:
- User says "remember when..." or "do you recall..."
- User asks about specific dates or past events
- User references something you discussed before

HOW TO USE:
- Extract the key topic from user's question
- Use specific search terms like "birthday", "work", "dinner"

RETURNS:
- List of relevant memories with dates
- Empty list if nothing found

ERROR HANDLING:
- If no memories found, say "I don't remember that specifically, remind me?"
```

**TDD Steps**:
1. Write test: `test_get_memory_description_format`
2. Update description constant
3. Verify test passes

**Acceptance Criteria**:
- [ ] AC-T2.1.1: WHEN section present
- [ ] AC-T2.1.2: HOW section present
- [ ] AC-T2.1.3: ERROR section present
- [ ] AC-T2.1.4: Examples included

---

### T2.2: Update get_context Tool Description

- **Status**: [ ] Not Started
- **File**: `nikita/agents/voice/server_tools.py` (MODIFY)
- **Estimate**: S (30 min)
- **Dependencies**: None
- **Parallel**: [P]

**Description**: Update get_context to indicate it should be called at call START.

**Acceptance Criteria**:
- [ ] AC-T2.2.1: "Use at the START of each call" emphasized
- [ ] AC-T2.2.2: Describes what context is returned
- [ ] AC-T2.2.3: Explains when to refresh context

---

### T2.3: Update score_turn Tool Description

- **Status**: [ ] Not Started
- **File**: `nikita/agents/voice/server_tools.py` (MODIFY)
- **Estimate**: S (30 min)
- **Dependencies**: None
- **Parallel**: [P]

**Description**: Update score_turn to indicate when to use it.

**Acceptance Criteria**:
- [ ] AC-T2.3.1: "Use after emotional exchanges" emphasized
- [ ] AC-T2.3.2: Explains what gets scored
- [ ] AC-T2.3.3: Error handling documented

---

### T2.4: Update update_memory Tool Description

- **Status**: [ ] Not Started
- **File**: `nikita/agents/voice/server_tools.py` (MODIFY)
- **Estimate**: S (30 min)
- **Dependencies**: None
- **Parallel**: [P]

**Description**: Update update_memory to clarify when to store new facts.

**Acceptance Criteria**:
- [ ] AC-T2.4.1: "Use when user shares NEW information" emphasized
- [ ] AC-T2.4.2: Examples of what to store
- [ ] AC-T2.4.3: Explains confidence levels

---

### T2.5: Write Integration Tests for Tool Descriptions

- **Status**: [ ] Not Started
- **File**: `tests/agents/voice/test_tool_descriptions.py` (NEW)
- **Estimate**: M (2 hours)
- **Dependencies**: T2.1-T2.4

**Test Coverage**:
- [ ] All tools have WHEN/HOW/ERROR sections
- [ ] Descriptions are valid JSON
- [ ] Character limits respected

**Acceptance Criteria**:
- [ ] AC-T2.5.1: All description tests pass
- [ ] AC-T2.5.2: Format consistency verified

---

## US-3: Voice Conversation Memory (P1)

### T3.1: Add create_voice_conversation() to Repository

- **Status**: [ ] Not Started
- **File**: `nikita/db/repositories/conversation_repository.py` (MODIFY)
- **Estimate**: M (2 hours)
- **Dependencies**: None

**Description**: Add method to create conversation record from voice transcript.

**TDD Steps**:
1. Write test: `test_create_voice_conversation`
2. Write test: `test_voice_conversation_has_source_voice`
3. Implement `create_voice_conversation()` method
4. Verify all tests pass

**Acceptance Criteria**:
- [ ] AC-T3.1.1: Creates conversation with `source='voice'`
- [ ] AC-T3.1.2: Stores transcript in `messages` JSONB
- [ ] AC-T3.1.3: Sets initial `status='active'`
- [ ] AC-T3.1.4: Links to user and voice session

---

### T3.2: Store Transcript in Webhook Handler

- **Status**: [ ] Not Started
- **File**: `nikita/api/routes/voice.py` (MODIFY)
- **Estimate**: M (2 hours)
- **Dependencies**: T3.1

**Description**: Store voice transcript when call.ended webhook received.

**TDD Steps**:
1. Write test: `test_webhook_stores_transcript`
2. Write test: `test_webhook_handles_empty_transcript`
3. Update webhook handler to create conversation
4. Verify all tests pass

**Acceptance Criteria**:
- [ ] AC-T3.2.1: Transcript extracted from webhook payload
- [ ] AC-T3.2.2: create_voice_conversation() called
- [ ] AC-T3.2.3: Duration and metadata stored
- [ ] AC-T3.2.4: Logged for debugging

---

### T3.3: Add Voice Transcript to Post-Processing Queue

- **Status**: [ ] Not Started
- **File**: `nikita/api/routes/voice.py` (MODIFY)
- **Estimate**: M (1-2 hours)
- **Dependencies**: T3.2

**Description**: Voice conversations should be picked up by pg_cron like text.

**TDD Steps**:
1. Write test: `test_voice_conversation_detected_stale`
2. Verify pg_cron query includes voice conversations
3. Verify all tests pass

**Acceptance Criteria**:
- [ ] AC-T3.3.1: Voice conversations have status='active'
- [ ] AC-T3.3.2: Stale detection query includes source='voice'
- [ ] AC-T3.3.3: 5-minute timeout after call end (vs 15 min for text)

---

### T3.4: Update PostProcessor to Handle Voice Transcripts

- **Status**: [ ] Not Started
- **File**: `nikita/context/post_processor.py` (MODIFY)
- **Estimate**: M (2-3 hours)
- **Dependencies**: T3.3

**Description**: Ensure all 9 stages work correctly with voice transcript format.

**TDD Steps**:
1. Write test: `test_post_processor_handles_voice`
2. Write test: `test_entities_extracted_from_voice`
3. Verify/adapt each stage for voice format
4. Verify all tests pass

**Acceptance Criteria**:
- [ ] AC-T3.4.1: Entity extraction works on voice transcript
- [ ] AC-T3.4.2: Threads created from voice topics
- [ ] AC-T3.4.3: Summary generated for voice conversation
- [ ] AC-T3.4.4: Graph updates include voice facts

---

### T3.5: Write Tests for Voice Post-Processing

- **Status**: [ ] Not Started
- **File**: `tests/agents/voice/test_voice_post_processing.py` (NEW)
- **Estimate**: M (2 hours)
- **Dependencies**: T3.1-T3.4

**Test Coverage**:
- [ ] Transcript storage
- [ ] Queue detection
- [ ] Full pipeline execution
- [ ] Artifact creation

**Acceptance Criteria**:
- [ ] AC-T3.5.1: All voice PP scenarios tested
- [ ] AC-T3.5.2: Tests pass in CI

---

## US-4: Personality Consistency (P2)

### T4.1: Generate Personalized context_block

- **Status**: [ ] Not Started
- **File**: `nikita/agents/voice/context.py` (MODIFY)
- **Estimate**: M (2 hours)
- **Dependencies**: T1.4

**Description**: context_block should match text agent's personalized context structure.

**TDD Steps**:
1. Write test: `test_context_block_matches_text_format`
2. Write test: `test_context_block_includes_vice_prefs`
3. Implement matching format
4. Verify all tests pass

**Acceptance Criteria**:
- [ ] AC-T4.1.1: Format matches text MetaPromptService output
- [ ] AC-T4.1.2: Vice preferences included
- [ ] AC-T4.1.3: Engagement state included
- [ ] AC-T4.1.4: Chapter behavior hints included

---

### T4.2: Document ElevenLabs Console Changes

- **Status**: [ ] Not Started
- **File**: `docs/guides/elevenlabs-console-setup.md` (NEW)
- **Estimate**: S (1 hour)
- **Dependencies**: T4.1
- **Parallel**: [P]

**Description**: Document manual steps for ElevenLabs console configuration.

**Acceptance Criteria**:
- [ ] AC-T4.2.1: System prompt template documented
- [ ] AC-T4.2.2: Tool configuration steps documented
- [ ] AC-T4.2.3: Dynamic variable placeholders listed
- [ ] AC-T4.2.4: Testing instructions included

---

### T4.3: Write Tests for context_block Content

- **Status**: [ ] Not Started
- **File**: `tests/agents/voice/test_context_block.py` (NEW)
- **Estimate**: M (2 hours)
- **Dependencies**: T4.1

**Test Coverage**:
- [ ] Content structure
- [ ] Key sections present
- [ ] Token budget respected

**Acceptance Criteria**:
- [ ] AC-T4.3.1: All required sections tested
- [ ] AC-T4.3.2: Tests pass in CI

---

## Cross-Cutting: Logging & Debugging (P1)

### T5.1: Add Logging for Dynamic Variables

- **Status**: [ ] Not Started
- **File**: `nikita/agents/voice/inbound.py` (MODIFY)
- **Estimate**: S (30 min)
- **Dependencies**: T1.3

**Description**: Log all dynamic variables at call initiation for debugging.

**Acceptance Criteria**:
- [ ] AC-T5.1.1: All 30+ fields logged at INFO level
- [ ] AC-T5.1.2: User ID and session ID included
- [ ] AC-T5.1.3: Sensitive data redacted if needed

---

### T5.2: Add Logging for Server Tool Calls

- **Status**: [ ] Not Started
- **File**: `nikita/agents/voice/server_tools.py` (MODIFY)
- **Estimate**: S (30 min)
- **Dependencies**: None
- **Parallel**: [P]

**Description**: Log each server tool invocation with inputs, outputs, and latency.

**Acceptance Criteria**:
- [ ] AC-T5.2.1: Tool name logged
- [ ] AC-T5.2.2: Input parameters logged
- [ ] AC-T5.2.3: Response size and latency logged
- [ ] AC-T5.2.4: Errors logged with stack trace

---

### T5.3: Add Logging for Webhook Events

- **Status**: [ ] Not Started
- **File**: `nikita/api/routes/voice.py` (MODIFY)
- **Estimate**: S (30 min)
- **Dependencies**: T3.2

**Description**: Log webhook events for call lifecycle debugging.

**Acceptance Criteria**:
- [ ] AC-T5.3.1: Event type logged
- [ ] AC-T5.3.2: Call duration logged
- [ ] AC-T5.3.3: Transcript length logged
- [ ] AC-T5.3.4: Processing time logged

---

### T5.4: Write Tests for Logging Coverage

- **Status**: [ ] Not Started
- **File**: `tests/agents/voice/test_logging.py` (NEW)
- **Estimate**: M (2 hours)
- **Dependencies**: T5.1-T5.3

**Test Coverage**:
- [ ] Dynamic variable logging
- [ ] Tool call logging
- [ ] Webhook event logging

**Acceptance Criteria**:
- [ ] AC-T5.4.1: All logging scenarios tested
- [ ] AC-T5.4.2: Tests pass in CI

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-19 | Initial task breakdown |
