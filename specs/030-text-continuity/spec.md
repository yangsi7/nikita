# Feature Specification: Text Agent Message History and Continuity

**Spec ID**: 030-text-continuity
**Status**: Draft
**Created**: 2026-01-19
**Priority**: P0 (Critical)

## Overview

### Problem Statement

The text agent experiences "amnesia" within single conversations because PydanticAI's `message_history` parameter is never passed to `agent.run()`. Users can say "yes", "why", or "lol" and Nikita has no idea what they're responding to because:

1. **No Working Memory**: `nikita_agent.run()` at `nikita/agents/text/agent.py:48` only receives `user_message` and `deps` - no conversation history
2. **Context Lost**: Short messages become meaningless without prior turns
3. **Today Buffer Missing**: When returning after a break, Nikita doesn't reference earlier same-day conversation
4. **Open Threads Ignored**: Unresolved conversation threads aren't being surfaced for follow-up

**Root Cause Analysis**:
```
CONTINUITY FAILURE
├── [A] No message_history → PydanticAI supports it, we don't use it
├── [B] Short replies ("yes", "why") → 100% context loss
├── [C] Same-day returns → No "today buffer" injection
└── [D] Open threads → Created but never read back
```

### Proposed Solution

Implement a 4-tier working memory system that injects conversation context:

1. **Tier 1: Message History** - Pass 30-80 recent turns as `message_history` to `agent.run()`
2. **Tier 2: Today Buffer** - Inject `daily_summary.summary_text` + `key_moments` into system prompt
3. **Tier 3: Open Threads** - Surface `conversation_threads` with status='open' for follow-up
4. **Tier 4: Last Conversation** - Include `last_conversation_summary` for returning users

### Success Criteria

- [ ] SC-1: "yes"/"why" responses reference prior context (manual test)
- [ ] SC-2: 90% of return sessions include correct callback to earlier conversation
- [ ] SC-3: Token budget respected (1.5-3K for history tier)
- [ ] SC-4: Message history window logged in `generated_prompts.context_snapshot`
- [ ] SC-5: Open threads appear in Nikita's context when user returns

---

## Functional Requirements

### FR-001: Message History Injection
**Priority**: P0
**Description**: Pass recent conversation turns to `agent.run()` via the `message_history` parameter per PydanticAI best practices.

**Technical Details**:
- Retrieve last N messages from `conversations.messages` JSONB column
- Format as PydanticAI-compatible `list[ModelMessage]`
- Token budget: 1500-3000 tokens for history tier
- Ensure tool calls and tool returns are always paired (PydanticAI requirement)
- Use `result.new_messages()` pattern for conversation continuation

### FR-002: Today Buffer Integration
**Priority**: P0
**Description**: Inject same-day conversation summary and key moments into the system prompt context.

**Technical Details**:
- Load from `daily_summaries` table (`summary_text`, `key_moments`)
- Add to `MetaPromptContext.today_summaries` (already exists but needs usage)
- Surface in `{{today_summary}}` template variable
- Token budget: 300-500 tokens

### FR-003: Open Threads Surfacing
**Priority**: P1
**Description**: Surface unresolved conversation threads for natural follow-up.

**Technical Details**:
- Query `conversation_threads` where `status='open'` and `user_id=?`
- Inject into system prompt under "## Open Threads" section
- Nikita can naturally reference or close threads
- Token budget: 250-400 tokens

### FR-004: Last Conversation Summary
**Priority**: P2
**Description**: For returning users, include summary of last conversation for continuity.

**Technical Details**:
- Load most recent `conversations.nikita_summary` where `user_id=?`
- Only for conversations older than current session
- Inject as `{{last_conversation_summary}}` (template exists, not populated)
- Token budget: 200-300 tokens

### FR-005: Token Budget Management
**Priority**: P1
**Description**: Implement deterministic truncation when combined context exceeds budget.

**Technical Details**:
- Total budget: 4100 tokens (hard cap: 6150)
- Tier 1 (History): 1500-3000 tokens
- Tier 2 (Today): 300-500 tokens
- Tier 3 (Threads): 250-400 tokens
- Tier 4 (Last Conv): 200-300 tokens
- Truncation priority: Last Conv → Threads → Today → History (oldest first)

### FR-006: Context Snapshot Logging
**Priority**: P1
**Description**: Log the history window and context sources for debugging.

**Technical Details**:
- Add to `generated_prompts.context_snapshot` JSONB:
  - `message_history_count`: number of turns passed
  - `message_history_tokens`: token count
  - `today_summary_present`: boolean
  - `open_threads_count`: number of threads injected
  - `last_conversation_present`: boolean

---

## User Stories

### US-1: Short Message Continuity
**As a** user **I want to** reply "yes", "sure", or "why?" **So that** Nikita knows what I'm agreeing to or asking about without me repeating context.

**Acceptance Criteria**:
- [ ] AC-1.1: When user says "yes" after Nikita's question, response references the question
- [ ] AC-1.2: When user says "why?", Nikita explains her prior statement
- [ ] AC-1.3: At least 30 recent turns available in message_history
- [ ] AC-1.4: Token budget ≤3000 for history tier

**Priority**: P0

### US-2: Same-Day Return Continuity
**As a** user **I want** Nikita to remember what we talked about earlier today **So that** returning to chat feels natural.

**Acceptance Criteria**:
- [ ] AC-2.1: Today's summary available in context when user returns
- [ ] AC-2.2: Key moments from today accessible
- [ ] AC-2.3: Nikita can reference earlier conversation ("Earlier you mentioned...")
- [ ] AC-2.4: Works for gaps of 1-12 hours within same day

**Priority**: P0

### US-3: Thread Follow-Up
**As a** user **I want** Nikita to follow up on unresolved topics **So that** conversations feel continuous across sessions.

**Acceptance Criteria**:
- [ ] AC-3.1: Open threads injected into Nikita's context
- [ ] AC-3.2: Nikita can naturally reference unresolved threads
- [ ] AC-3.3: Threads older than 7 days deprioritized
- [ ] AC-3.4: Maximum 5 threads surfaced per session

**Priority**: P1

### US-4: Returning User Experience
**As a** user returning after days **I want** Nikita to reference our last conversation **So that** she feels like a continuous relationship.

**Acceptance Criteria**:
- [ ] AC-4.1: Last conversation summary available for users returning after >24h
- [ ] AC-4.2: Summary naturally integrated ("Last time we talked about...")
- [ ] AC-4.3: Token-efficient summary (≤300 tokens)

**Priority**: P2

---

## Non-Functional Requirements

### NFR-001: Performance
- Message history retrieval: <50ms
- Token counting: <10ms
- Total context build: <200ms (existing MetaPromptService budget)

### NFR-002: Reliability
- Graceful degradation: If history unavailable, proceed with system prompt only
- No conversation failure due to memory issues

### NFR-003: Token Efficiency
- History tier: ≤3000 tokens
- Combined context: ≤6150 tokens (hard cap)
- Deterministic truncation (oldest messages first)

---

## Constraints & Assumptions

### Constraints
- Must use existing `conversations.messages` JSONB schema
- Cannot exceed PydanticAI context window limits
- Must maintain <200ms prompt generation latency
- **System Prompt Isolation**: `message_history` must NOT be passed on first message of new session (breaks `@agent.instructions` decorators)
- **Tool Call Pairing**: History truncation MUST preserve `ToolCallPart`/`ToolReturnPart` pairs
- **Format Conversion**: Must convert `"nikita"` role to `ModelResponse` (not directly compatible)

### Assumptions
- `conversations.messages` contains structured message data
- `daily_summaries` table is populated by post-processing
- `conversation_threads` table exists with open/closed status

---

## Out of Scope

- Voice agent changes (covered in Spec 032)
- Post-processing pipeline fixes (covered in Spec 031)
- Long-term memory retrieval changes (Graphiti queries)
- Message storage format changes

---

## Technical Design Notes

### Critical Implementation Notes (from Research 2026-01-20)

#### System Prompt Behavior (CRITICAL)
**When `message_history` is non-empty, PydanticAI does NOT regenerate the system prompt.**

From PydanticAI documentation:
> "If `message_history` is set and not empty, a new system prompt is not generated — we assume the existing message history includes a system prompt."

**Impact on Nikita**: Our `@agent.instructions` decorators dynamically generate personalized prompts (vices, engagement, memory context). If we pass non-empty `message_history`, these decorators WON'T be called.

**Solution**: Session-aware two-path approach:
- **New Session** (first message): Pass `message_history=None` to trigger fresh system prompt generation via decorators
- **Mid-Conversation** (subsequent messages): Pass `message_history` for continuity (system prompt already in history)

```python
# Session detection in generate_response()
if len(conversation.messages) == 0:
    # New session - let @agent.instructions generate fresh prompt
    message_history = None
else:
    # Mid-conversation - load history for continuity
    message_history = await load_and_convert_history(conversation)
```

#### Message Format Conversion (Required)
Current JSONB format is NOT directly compatible with PydanticAI:

| Current Format | PydanticAI Format |
|----------------|-------------------|
| `{"role": "user", "content": "..."}` | `ModelRequest(parts=[UserPromptPart(...)])` |
| `{"role": "nikita", "content": "..."}` | `ModelResponse(parts=[TextPart(...)])` |

**Solution**: Use `ModelMessagesTypeAdapter` for conversion:
```python
from pydantic_ai import ModelMessagesTypeAdapter
from pydantic_core import to_jsonable_python

# Save after agent.run():
messages_to_store = to_jsonable_python(result.all_messages())
conversation.messages = messages_to_store  # Store as JSONB

# Load before agent.run():
history = ModelMessagesTypeAdapter.validate_python(conversation.messages)
result = agent.run(prompt, message_history=history)
```

#### Tool Call Pairing (CRITICAL WARNING)
From PydanticAI documentation:
> "When slicing the message history, you need to make sure that tool calls and returns are paired, otherwise the LLM may return an error."

**Solution**: When truncating history, implement safe slicing that preserves `ToolCallPart`/`ToolReturnPart` pairs. Unpaired tool calls at truncation boundary must be excluded.

#### History Processors (Token Management)
PydanticAI supports automatic history processing via `history_processors`:
```python
from pydantic_ai import Agent, ModelMessage

async def keep_recent_with_budget(messages: list[ModelMessage]) -> list[ModelMessage]:
    """Keep messages within 3000 token budget."""
    return messages[-40:] if len(messages) > 40 else messages

agent = Agent(
    MODEL_NAME,
    deps_type=NikitaDeps,
    history_processors=[keep_recent_with_budget],
)
```

### PydanticAI Message History Pattern

```python
# From PydanticAI docs: Conversation continuity
result1 = await agent.run("First message", deps=deps)

# Continue conversation with history
result2 = await agent.run(
    "Second message",
    deps=deps,
    message_history=result1.all_messages()  # Or new_messages()
)
```

**For Nikita**: Load history from DB rather than chaining results:

```python
# Load from conversations.messages
history = await load_message_history(conversation_id, limit=80)

# Pass to agent
result = await nikita_agent.run(
    user_message,
    deps=deps,
    message_history=history,
)
```

### Key Files to Modify

| File | Change |
|------|--------|
| `nikita/agents/text/history.py` | NEW: HistoryLoader class with ModelMessagesTypeAdapter |
| `nikita/agents/text/agent.py` | Add `message_history` to `agent.run()` call (session-aware) |
| `nikita/meta_prompts/service.py` | Add today_buffer, open_threads injection |
| `nikita/db/repositories/conversation_repository.py` | Add `get_message_history()` method |

---

## Open Questions

*No open questions requiring clarification at this time.*

---

## References

- [PydanticAI Message History Docs](https://ai.pydantic.dev/message-history/)
- [Research: Nikita Memory Continuity PRD](docs-to-process/2026-01-19-continuity-memory-prd/)
- Spec 012: Context Engineering (existing MetaPromptService)
- Spec 029: Context Comprehensive (3-graph memory)
