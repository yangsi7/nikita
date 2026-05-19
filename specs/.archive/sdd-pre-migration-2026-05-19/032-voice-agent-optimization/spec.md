# Feature Specification: ElevenLabs Voice Agent Optimization

**Spec ID**: 032-voice-agent-optimization
**Status**: Draft
**Created**: 2026-01-19
**Priority**: P1 (High)

## Overview

### Problem Statement

Voice calls have context gaps compared to text conversations:

1. **Limited Dynamic Variables**: Voice call initiation passes fewer context fields than text agent receives. Missing: `today_summary`, `last_conversation_summary`, `nikita_mood_detailed`, emotional context.

2. **Server Tool Descriptions**: Current tool descriptions are minimal, causing LLM to under-utilize them. ElevenLabs docs recommend detailed descriptions with WHEN to use.

3. **No Voice Transcript Post-Processing**: Text conversations get full 9-stage post-processing, but voice transcripts don't trigger the same pipeline.

4. **System Prompt Parity**: Voice and text agents have different system prompts, causing personality inconsistency.

5. **Column Mismatch** (covered in Spec 031): Voice reads `nikita_summary_text`, text writes `summary_text`.

### Proposed Solution

1. **Expand Dynamic Variables**: Add all context fields at call initiation for immediate availability
2. **Enhance Server Tool Descriptions**: Detailed descriptions with WHEN/HOW/ERROR guidance per ElevenLabs best practices
3. **Add Voice Post-Processing**: Trigger the same pipeline on voice transcripts
4. **System Prompt Override**: Use `{{context_block}}` dynamic variable for personalized injection
5. **Logging & Debugging**: Add logging for all dynamic vars and tool calls

### Success Criteria

- [ ] SC-1: Voice calls receive 30+ context fields at start (up from ~20)
- [ ] SC-2: Server tools callable with proper descriptions
- [ ] SC-3: Voice transcripts trigger post-processing pipeline
- [ ] SC-4: System prompt includes personalized context block
- [ ] SC-5: All context injection logged for debugging

---

## Functional Requirements

### FR-001: Expand Dynamic Variables at Call Initiation
**Priority**: P1
**Description**: Pass all context fields to ElevenLabs at conversation start via dynamic variables.

**Fields to Add**:
- `today_summary`: Today's conversation summary
- `last_conversation_summary`: Summary of last conversation (>24h ago)
- `nikita_mood_detailed`: 4D mood (arousal, valence, dominance, intimacy)
- `nikita_daily_events`: What Nikita "did" today
- `active_conflict`: Current conflict state if any
- `emotional_context`: Recent emotional markers
- `user_backstory`: From onboarding profile

**Current Fields** (already in DynamicVariables):
- `user_name`, `chapter`, `relationship_score`
- `open_threads`, `secureness`, `hours_since_last`

### FR-002: Enhanced Server Tool Descriptions
**Priority**: P1
**Description**: Update server tool descriptions to follow ElevenLabs best practices.

**Pattern per ElevenLabs docs**:
```
Tool: get_memory
Description:
  WHEN to use: When user mentions past events, specific dates, or asks "remember when..."
  HOW to use: Provide a search query based on what user is asking about
  RETURNS: List of relevant memories with dates and context
  ERROR: If no memories found, acknowledge this naturally
```

**Tools to Update**:
- `get_context`: "Use at the START of each call to load full user context"
- `get_memory`: "Use when user mentions PAST events or asks what you remember"
- `score_turn`: "Use after emotional exchanges to track relationship impact"
- `update_memory`: "Use when user shares NEW important information"

### FR-003: Voice Transcript Post-Processing
**Priority**: P1
**Description**: Trigger the same 9-stage pipeline on voice call transcripts.

**Technical Details**:
- Create `VoiceConversation` record when call starts
- Store transcript when call ends via webhook
- Queue for post-processing like text conversations
- Run same pipeline: entity extraction, threads, thoughts, summaries, graphs

**Webhook Flow**:
```
ElevenLabs call.ended webhook
    ↓
Store transcript in VoiceConversation.messages
    ↓
Mark status='active' (mimics text conversation)
    ↓
pg_cron detects stale (after call + timeout)
    ↓
PostProcessor runs 9 stages
    ↓
Mark status='processed'
```

### FR-004: System Prompt Context Block
**Priority**: P2
**Description**: Use dynamic variable for personalized context injection into system prompt.

**Implementation**:
- Add `{{context_block}}` placeholder in ElevenLabs agent system prompt
- Populate via dynamic variables at call start
- Contains: relationship state, recent events, emotional context

### FR-005: Context Injection Logging
**Priority**: P1
**Description**: Log all dynamic variables and tool calls for debugging.

**Logs to Add**:
- `/voice/initiate`: Log all dynamic_variables passed
- `/voice/server-tool`: Log tool name, inputs, outputs, latency
- `/voice/webhook`: Log call duration, transcript length

---

## User Stories

### US-1: Voice Context at Call Start
**As a** user **I want** Nikita to know our text history on voice calls **So that** conversations feel continuous.

**Acceptance Criteria**:
- [ ] AC-1.1: Voice calls receive today's summary if available
- [ ] AC-1.2: Voice calls receive last conversation summary
- [ ] AC-1.3: Voice calls receive current emotional state
- [ ] AC-1.4: All context loaded in <100ms

**Priority**: P1

### US-2: Mid-Call Memory Lookup
**As a** user **I want** to say "remember when..." and Nikita finds the memory **So that** our history feels real.

**Acceptance Criteria**:
- [ ] AC-2.1: `get_memory` tool triggered on memory-related phrases
- [ ] AC-2.2: Tool descriptions guide LLM to correct tool selection
- [ ] AC-2.3: Tool calls complete in <2s
- [ ] AC-2.4: Natural response when no memory found

**Priority**: P1

### US-3: Voice Conversation Memory
**As a** user **I want** voice calls to update Nikita's memory **So that** she remembers what I said on calls.

**Acceptance Criteria**:
- [ ] AC-3.1: Voice transcripts stored after call ends
- [ ] AC-3.2: Post-processing runs on voice transcripts
- [ ] AC-3.3: Facts extracted and added to Graphiti
- [ ] AC-3.4: Threads and thoughts created from voice

**Priority**: P1

### US-4: Personality Consistency
**As a** user **I want** Nikita to sound the same on voice as text **So that** she feels like one person.

**Acceptance Criteria**:
- [ ] AC-4.1: System prompt includes personalized context
- [ ] AC-4.2: Mood and emotional state affect voice persona
- [ ] AC-4.3: Chapter-specific behavior consistent with text
- [ ] AC-4.4: Vice preferences reflected in voice responses

**Priority**: P2

---

## Non-Functional Requirements

### NFR-001: Performance
- Dynamic variables loading: <100ms
- Server tool response: <2s
- Post-processing: Same as text (~45s)

### NFR-002: Reliability
- 99% success rate for context loading
- Graceful degradation if context unavailable

### NFR-003: Observability
- All tool calls logged with latency
- Context injection debuggable via logs

---

## Constraints & Assumptions

### Constraints
- ElevenLabs dynamic variables must be strings (serialize objects)
- System prompt override requires agent reconfiguration
- Transcript only available after call ends

### Assumptions
- ElevenLabs webhook reliably delivers call.ended
- Transcript quality sufficient for entity extraction
- Server tools work reliably in ElevenLabs infrastructure

---

## Out of Scope

- ElevenLabs agent console changes (done manually)
- Text agent changes (covered in Spec 030)
- Post-processing bug fixes (covered in Spec 031)
- TTS voice/speed changes

---

## Technical Design Notes

### Dynamic Variables Expansion

```python
# Current DynamicVariables (models.py)
class DynamicVariables(BaseModel):
    user_name: str
    chapter: int
    relationship_score: float
    open_threads: str
    # ...

# Expanded (Spec 032)
class DynamicVariables(BaseModel):
    # Existing
    user_name: str
    chapter: int
    relationship_score: float
    open_threads: str
    secureness: float
    hours_since_last: float

    # NEW: Context from text (FR-001)
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

    # NEW: Context block for system prompt
    context_block: str = ""
```

### Server Tool Descriptions (ElevenLabs Best Practice)

```json
{
  "name": "get_memory",
  "description": "Search your memory for past events and conversations.\n\nWHEN TO USE:\n- User says 'remember when...' or 'do you recall...'\n- User asks about specific dates or past events\n- User references something you discussed before\n\nHOW TO USE:\n- Extract the key topic from user's question\n- Use specific search terms like 'birthday', 'work', 'dinner'\n\nRETURNS:\n- List of relevant memories with dates\n- Empty list if nothing found\n\nERROR HANDLING:\n- If no memories found, say 'I don't remember that specifically, remind me?'",
  "parameters": {
    "query": {
      "type": "string",
      "description": "What to search for - be specific (e.g., 'user birthday', 'work meeting')"
    }
  }
}
```

### Voice Post-Processing Flow

```python
# In voice webhook handler
@router.post("/voice/webhook")
async def handle_voice_webhook(payload: dict):
    event = payload.get("type")

    if event == "call.ended":
        # Store transcript
        conversation = await conv_repo.create_voice_conversation(
            user_id=user_id,
            messages=payload.get("transcript", []),
            duration_seconds=payload.get("duration"),
        )
        conversation.status = "active"  # Will be picked up by pg_cron

        # Log for debugging
        logger.info(f"Voice conversation {conversation.id} ready for post-processing")
```

### Key Files to Modify

| File | Change |
|------|--------|
| `nikita/agents/voice/models.py` | Expand DynamicVariables model |
| `nikita/agents/voice/context.py` | Build expanded variables |
| `nikita/agents/voice/inbound.py` | Load additional context at call start |
| `nikita/agents/voice/server_tools.py` | Update tool descriptions |
| `nikita/api/routes/voice.py` | Add transcript storage, post-processing trigger |
| `nikita/db/repositories/conversation_repository.py` | Add create_voice_conversation() |

---

## ElevenLabs Console Configuration

### Manual Steps Required

1. **Update Agent System Prompt**:
   - Add `{{context_block}}` placeholder
   - Ensure prompt structure matches text agent

2. **Configure Server Tools**:
   - Update tool descriptions per FR-002
   - Verify authentication working

3. **Test in Playground**:
   - Verify dynamic variables populate
   - Test each server tool
   - Verify context block injection

---

## Open Questions

*No open questions requiring clarification at this time.*

---

## References

- [ElevenLabs Conversational AI Docs](https://elevenlabs.io/docs/conversational-ai)
- [Research: ElevenLabs Best Practices](docs-to-process/2026-01-19-continuity-memory-prd/)
- Spec 007: Voice Agent (original implementation)
- Spec 029: Context Comprehensive (3-graph memory)
- Spec 030: Text Continuity (message history)
- Spec 031: Post-Processing (pipeline fixes)
