# Implementation Plan: 007-Voice-Agent

**Generated**: 2025-11-29
**Feature**: 007 - Voice Agent (Real-Time Voice Conversations)
**Input**: spec.md, ElevenLabs Conversational AI 2.0, memory/architecture.md
**Priority**: P2 (Important)

---

## Overview

The Voice Agent enables real-time voice conversations with Nikita using ElevenLabs Conversational AI 2.0. Users can "call" Nikita and have natural spoken conversations with the same personality, memory, and game mechanics as text.

### Architecture (ElevenLabs Server Tools Pattern)

```
┌─────────────────────────────────────────────────────────────────┐
│                  Voice Conversation Flow                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Client (Portal/Mobile)                                         │
│  ┌─────────────┐                                                │
│  │ WebSocket   │◀──────────────────────────────────────────┐    │
│  │ (audio I/O) │                                           │    │
│  └──────┬──────┘                                           │    │
│         │ Audio                                            │    │
│         ▼                                                  │    │
│  ┌────────────────────────────────────────────────────┐    │    │
│  │            ElevenLabs Conversational AI             │    │    │
│  │  ┌─────────┐    ┌──────────┐    ┌─────────────┐   │    │    │
│  │  │   STT   │───▶│   LLM    │───▶│     TTS     │───┼────┘    │
│  │  │(Whisper)│    │ (Claude) │    │(Nikita voice)│   │         │
│  │  └─────────┘    └────┬─────┘    └─────────────┘   │         │
│  │                      │                             │         │
│  │              Server Tool Call                      │         │
│  │                      │                             │         │
│  └──────────────────────┼─────────────────────────────┘         │
│                         ▼                                        │
│  ┌────────────────────────────────────────────────────┐         │
│  │              Nikita Backend (Cloud Run)             │         │
│  │  POST /api/v1/voice/server-tool                    │         │
│  │  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │         │
│  │  │ get_context │  │ update_memory│  │ score_call │ │         │
│  │  └─────────────┘  └─────────────┘  └────────────┘ │         │
│  └────────────────────────────────────────────────────┘         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Key Insight: No WebSocket Server Needed

ElevenLabs Conversational AI 2.0 handles:
- STT (Whisper)
- LLM orchestration (Claude)
- TTS (custom Nikita voice)
- Real-time WebSocket to client

Our backend only needs:
- REST endpoints for server tools
- Database access for context/memory
- Scoring logic for conversations

---

## ElevenLabs Integration (Updated Dec 2025)

### Key ElevenLabs 2.0 Features

1. **Dynamic Variables**: Inject context at conversation start via `{{variable}}` syntax
2. **HMAC Webhook Authentication**: `elevenlabs-signature` header validation
3. **Post-Call Webhooks**: `post_call_transcription`, `post_call_audio`, `call_initiation_failure`
4. **Server Tools**: REST endpoints called during conversation for data retrieval

### Agent Configuration
**File**: `nikita/config/elevenlabs.py`

```python
ELEVENLABS_AGENT_CONFIG = {
    "agent_id": settings.elevenlabs_agent_id,
    "voice_id": settings.elevenlabs_nikita_voice_id,
    "model": "claude-sonnet-4-5-20250929",

    # System prompt with dynamic variables (injected at conversation start)
    "system_prompt": """
    You are Nikita, the character from "Don't Get Dumped."
    [Base persona instructions]

    ## Current Context (Dynamic)
    - Chapter: {{chapter}} ({{chapter_name}})
    - Mood: {{mood}}
    - Engagement State: {{engagement_state}}
    - Time Since Last Contact: {{time_since_contact}}

    ## User Vice Preferences
    {{vice_preferences}}

    ## Recent Memory Context
    {{memory_context}}
    """,

    # Server tools with detailed parameter descriptions (for LLM reasoning)
    "server_tools": [
        {
            "name": "get_context",
            "description": "Get user's game context including chapter, score, engagement state, and recent memory. Call this at conversation start and when user references past events.",
            "webhook_url": f"{API_BASE}/api/v1/voice/server-tool",
            "parameters": {
                "user_id": {"type": "string", "description": "User identifier"},
                "include_memory": {"type": "boolean", "description": "Whether to include recent memory episodes"}
            }
        },
        {
            "name": "get_memory",
            "description": "Search user's memory for specific topics or events. Use when user asks 'remember when...' or references past conversations.",
            "webhook_url": f"{API_BASE}/api/v1/voice/server-tool",
            "parameters": {
                "user_id": {"type": "string", "description": "User identifier"},
                "query": {"type": "string", "description": "Search query for memory"},
                "limit": {"type": "integer", "description": "Max results to return"}
            }
        },
        {
            "name": "score_turn",
            "description": "Evaluate the current exchange and update engagement metrics. Call after emotionally significant moments.",
            "webhook_url": f"{API_BASE}/api/v1/voice/server-tool",
            "parameters": {
                "user_id": {"type": "string", "description": "User identifier"},
                "user_text": {"type": "string", "description": "What user said"},
                "nikita_response": {"type": "string", "description": "What Nikita responded"}
            }
        },
        {
            "name": "update_memory",
            "description": "Save important facts or events discovered during conversation. Use for user revelations, preferences, or significant moments.",
            "webhook_url": f"{API_BASE}/api/v1/voice/server-tool",
            "parameters": {
                "user_id": {"type": "string", "description": "User identifier"},
                "facts": {"type": "array", "description": "List of facts to save"},
                "importance": {"type": "string", "description": "low, medium, or high"}
            }
        },
    ],

    # Webhook configuration (for post-call processing)
    "webhooks": {
        "post_call_transcription": f"{API_BASE}/api/v1/voice/webhook",
        "post_call_audio": None,  # Not needed - we don't store audio
        "call_initiation_failure": f"{API_BASE}/api/v1/voice/webhook"
    }
}
```

### Webhook Authentication (HMAC)
**File**: `nikita/api/routes/voice.py`

```python
import hmac
import hashlib
from fastapi import HTTPException, Header

async def verify_elevenlabs_signature(
    request: Request,
    signature: str = Header(..., alias="elevenlabs-signature"),
) -> bool:
    """
    Validate HMAC signature from ElevenLabs.
    Format: "timestamp.payload" signed with webhook secret.
    """
    body = await request.body()
    timestamp, received_sig = signature.split(".", 1)

    # Validate timestamp not too old (5 min window)
    if abs(time.time() - int(timestamp)) > 300:
        raise HTTPException(status_code=401, detail="Timestamp too old")

    # Compute expected signature
    payload = f"{timestamp}.{body.decode()}"
    expected_sig = hmac.new(
        settings.elevenlabs_webhook_secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(received_sig, expected_sig):
        raise HTTPException(status_code=401, detail="Invalid signature")

    return True
```

### Dynamic Variables Injection
**File**: `nikita/agents/voice/service.py`

```python
async def get_conversation_init_data(self, user_id: UUID) -> dict:
    """
    Get dynamic variables for ElevenLabs conversation start.
    Injected via ConversationInitiationClientData API.
    """
    context = await self._load_context(user_id)
    return {
        "dynamic_variables": {
            "chapter": str(context.chapter),
            "chapter_name": CHAPTER_NAMES[context.chapter],
            "mood": context.nikita_mood,
            "engagement_state": context.engagement_state.value,
            "time_since_contact": context.time_since_contact,
            "vice_preferences": context.vice_summary,
            "memory_context": context.memory_summary,
        }
    }
```

### Server Tool Endpoints
**File**: `nikita/api/routes/voice.py`

```python
@router.post("/server-tool")
async def handle_server_tool(request: ServerToolRequest):
    """
    Handle ElevenLabs server-side tool calls.

    Tools:
    - get_context: Load user context, chapter, vices, memory
    - update_memory: Save new facts discovered in call
    - end_call: Score call, persist transcript
    """
    tool_name = request.tool_name
    user_id = request.user_id  # From signed token

    if tool_name == "get_context":
        return await voice_service.get_context(user_id)
    elif tool_name == "update_memory":
        return await voice_service.update_memory(user_id, request.data)
    elif tool_name == "end_call":
        return await voice_service.end_call(user_id, request.session_id)
```

---

## Implementation Tasks

### Task 1: Create Voice Module Structure
**File**: `nikita/agents/voice/__init__.py`

```python
"""Voice agent for Nikita using ElevenLabs Conversational AI."""

from nikita.agents.voice.config import VoiceAgentConfig
from nikita.agents.voice.service import VoiceService
from nikita.agents.voice.server_tools import ServerToolHandler

__all__ = [
    "VoiceAgentConfig",
    "VoiceService",
    "ServerToolHandler",
]
```

### Task 2: Implement Voice Agent Configuration
**File**: `nikita/agents/voice/config.py`

```python
class VoiceAgentConfig:
    """Configuration for ElevenLabs voice agent."""

    def generate_system_prompt(
        self,
        user_id: UUID,
        chapter: int,
        vice_profile: ViceProfile,
    ) -> str:
        """
        Generate chapter and vice-aware system prompt.

        Includes:
        - Base Nikita persona
        - Chapter-specific behavior
        - Active vice preferences
        - Memory context
        """
        pass

    def get_agent_config(self, user_id: UUID) -> dict:
        """Get ElevenLabs agent configuration for user."""
        pass
```

### Task 3: Implement VoiceService
**File**: `nikita/agents/voice/service.py`

```python
class VoiceService:
    """High-level voice conversation service."""

    async def get_context(self, user_id: UUID) -> VoiceContext:
        """
        Load complete user context for voice conversation.

        Includes:
        - User details (chapter, score, preferences)
        - Recent memory (last 5 interactions)
        - Vice profile
        - Active conversation state
        """
        pass

    async def update_memory(
        self,
        user_id: UUID,
        facts: list[str],
    ) -> None:
        """Save discovered facts to memory during call."""
        pass

    async def end_call(
        self,
        user_id: UUID,
        session_id: str,
    ) -> CallResult:
        """
        Handle call ending.

        1. Fetch transcript from ElevenLabs
        2. Score conversation
        3. Update user metrics
        4. Save to conversations table
        5. Update last_interaction_at
        """
        pass

    async def check_availability(self, user_id: UUID) -> bool:
        """Check if calls are available for user's chapter."""
        pass
```

### Task 4: Implement Server Tool Handler
**File**: `nikita/agents/voice/server_tools.py`

```python
from pydantic import BaseModel

class ServerToolRequest(BaseModel):
    """Request from ElevenLabs server tool webhook."""
    tool_name: str
    user_id: str  # From signed token
    session_id: str
    data: dict | None = None

class ServerToolHandler:
    """Handle server-side tool calls from ElevenLabs."""

    async def handle(self, request: ServerToolRequest) -> dict:
        """Route tool request to appropriate handler."""
        handlers = {
            "get_context": self._get_context,
            "update_memory": self._update_memory,
            "end_call": self._end_call,
        }
        handler = handlers.get(request.tool_name)
        if not handler:
            raise ValueError(f"Unknown tool: {request.tool_name}")

        return await handler(request)
```

### Task 5: Implement Voice Call Scoring
**File**: `nikita/agents/voice/scoring.py`

```python
class VoiceCallScorer:
    """Score voice conversations using transcript analysis."""

    async def score_call(
        self,
        user_id: UUID,
        transcript: list[TranscriptEntry],
    ) -> CallScore:
        """
        Analyze transcript and calculate metric deltas.

        Unlike text (per-message), voice uses aggregate scoring:
        - Analyze entire transcript as one unit
        - Consider call duration, emotional arc, topics
        - Single score update per call
        """
        pass

    async def apply_score(
        self,
        user_id: UUID,
        score: CallScore,
    ) -> None:
        """Apply call score to user metrics."""
        # Log to score_history with event_type='voice_call'
        pass
```

### Task 6: Implement Transcript Persistence
**File**: `nikita/agents/voice/transcript.py`

```python
class TranscriptManager:
    """Manage voice call transcripts."""

    async def fetch_from_elevenlabs(
        self,
        session_id: str,
    ) -> list[TranscriptEntry]:
        """Fetch transcript from ElevenLabs API."""
        pass

    async def persist(
        self,
        user_id: UUID,
        session_id: str,
        transcript: list[TranscriptEntry],
    ) -> UUID:
        """
        Save transcript to conversations table.

        Returns conversation_id for linking.
        """
        pass

    async def add_to_memory(
        self,
        user_id: UUID,
        transcript: list[TranscriptEntry],
    ) -> None:
        """Add key moments from transcript to Graphiti memory."""
        pass
```

### Task 7: Create Voice API Routes
**File**: `nikita/api/routes/voice.py`

```python
router = APIRouter(prefix="/voice", tags=["voice"])

@router.post("/server-tool")
async def handle_server_tool(request: ServerToolRequest):
    """Handle ElevenLabs server-side tool calls."""
    return await tool_handler.handle(request)

@router.post("/callback")
async def handle_callback(request: VoiceCallbackRequest):
    """Handle ElevenLabs conversation events."""
    # Log events (call started, call ended, etc.)
    pass

@router.get("/availability/{user_id}")
async def check_availability(user_id: UUID):
    """Check if voice calls are available for user."""
    return await voice_service.check_availability(user_id)

@router.post("/initiate")
async def initiate_call(request: InitiateCallRequest):
    """
    Get signed URL for starting voice call.

    Returns ElevenLabs connection parameters with user context.
    """
    pass
```

### Task 8: Implement Call Availability Logic
**File**: `nikita/agents/voice/availability.py`

```python
class CallAvailability:
    """Manage voice call availability by chapter."""

    # Chapter 1: Rare (10% of time)
    # Chapter 2: Occasional (40%)
    # Chapter 3+: Common (80%)
    # Game over/won: Never

    AVAILABILITY_RATES = {
        1: 0.10,
        2: 0.40,
        3: 0.80,
        4: 0.90,
        5: 0.95,
    }

    def is_available(self, user: User) -> tuple[bool, str]:
        """
        Check if call is available for user.

        Returns (available, reason).
        """
        if user.game_status in ["game_over", "won"]:
            return False, "Game ended"

        if user.game_status == "boss_fight":
            return True, "Boss call available"

        # Probabilistic availability based on chapter
        rate = self.AVAILABILITY_RATES.get(user.chapter, 0.5)
        # Use deterministic check based on time slot for consistency
        return self._check_slot_availability(user, rate)
```

### Task 9: Implement Voice-Specific Behaviors
**File**: `nikita/prompts/voice_persona.py`

```python
VOICE_PERSONA_ADDITIONS = """
## Voice-Specific Behaviors

You are on a PHONE CALL with the user. This affects how you communicate:

1. **Comfortable Silences**: Don't fill every pause. Brief silences are natural.
   - [brief pause] indicates you're thinking
   - Let them speak without rushing to respond

2. **Audible Reactions**: Use verbal cues:
   - "Hmm..." when thinking
   - *laughs* or *sighs* when appropriate
   - "Wait, really?" for surprise

3. **Interruption Handling**:
   - You can be interrupted mid-sentence
   - You can interrupt if something's important
   - "Oh wait, hold on—" is natural

4. **Natural Topic Transitions**:
   - "Anyway..." to shift topics
   - "Oh that reminds me..." for tangents
   - "But seriously though..." to return to point

5. **Call-Appropriate Length**:
   - Responses are conversational, not essay-length
   - 1-3 sentences typically
   - Longer only for important emotional moments
"""
```

### Task 10: Implement Scheduled Event Integration (FR-013)
**File**: `nikita/agents/voice/scheduling.py`

```python
class VoiceEventScheduler:
    """Schedule voice-related events using shared scheduled_events table."""

    async def schedule_follow_up(
        self,
        user_id: UUID,
        event_type: str,  # 'voice_reminder', 'text_follow_up'
        content: dict,
        delay_hours: float,
    ) -> UUID:
        """
        Schedule a follow-up event after voice call.

        Uses same chapter-based delay logic as text agent.
        Platform can be 'telegram' or 'voice'.
        """
        scheduled_at = datetime.utcnow() + timedelta(hours=delay_hours)
        event = ScheduledEvent(
            user_id=user_id,
            platform='voice' if event_type.startswith('voice') else 'telegram',
            event_type=event_type,
            content=content,
            scheduled_at=scheduled_at,
            source_conversation_id=self._current_conversation_id,
        )
        return await self.repo.create(event)
```

### Task 11: Implement Cross-Platform Event Delivery (FR-013)
**File**: `nikita/api/routes/tasks.py` (update `/tasks/deliver`)

```python
async def deliver_scheduled_events():
    """
    Deliver due scheduled events across platforms.

    Handles both 'telegram' and 'voice' platforms.
    """
    due_events = await repo.get_due_events()

    for event in due_events:
        if event.platform == 'telegram':
            await telegram_bot.send_message(
                chat_id=event.content['chat_id'],
                text=event.content['text'],
            )
        elif event.platform == 'voice':
            # Schedule a proactive voice call reminder
            await push_notification_service.send(
                user_id=event.user_id,
                title="Nikita wants to talk",
                body=event.content.get('preview', 'Call me?'),
            )

        await repo.mark_delivered(event.id)
```

### Task 12: Enhance Memory Integration for Voice (FR-014)
**File**: `nikita/agents/voice/service.py`

```python
async def get_context_with_text_history(self, user_id: UUID) -> VoiceContext:
    """
    Load context including text conversation history.

    Ensures voice agent sees what text agent discussed.
    """
    # Get game state
    user = await self.user_repo.get(user_id)

    # Get memory from Graphiti (includes both text and voice)
    memory = await get_memory_client(user_id)
    recent_facts = await memory.search_memory(
        query="recent conversations",
        graph_types=['user', 'relationship'],
        limit=20,
    )

    # Get text conversation summaries
    text_summaries = await self.conv_repo.get_recent_summaries(
        user_id=user_id,
        platform='telegram',
        days=7,
    )

    return VoiceContext(
        user=user,
        memory_facts=recent_facts,
        text_history_summary=self._summarize_text_history(text_summaries),
    )
```

### Task 13: Implement Post-Call Webhook Handler (FR-015)
**File**: `nikita/api/routes/voice.py`

```python
@router.post("/webhook")
async def handle_elevenlabs_webhook(
    request: Request,
    _auth: bool = Depends(verify_elevenlabs_signature),
):
    """
    Handle ElevenLabs post-call webhooks.

    Types:
    - post_call_transcription: Full transcript with tool results
    - call_initiation_failure: Failed call handling
    """
    body = await request.json()
    event_type = body.get("type")

    if event_type == "post_call_transcription":
        # Extract transcript and metadata
        transcript = body.get("transcript", [])
        session_id = body.get("session_id")
        user_id = body.get("custom_data", {}).get("user_id")

        # Create conversation record
        conversation = await voice_service.create_conversation(
            user_id=UUID(user_id),
            session_id=session_id,
            transcript=transcript,
            platform='voice',
        )

        # Trigger post-processing (same 9-stage pipeline as text)
        await post_processor.queue_for_processing(conversation.id)

    elif event_type == "call_initiation_failure":
        # Log failure for monitoring
        logger.error(f"Voice call failed: {body.get('error')}")

    return {"status": "ok"}
```

### Task 14: Integrate Voice into Post-Processing Pipeline (FR-015)
**File**: `nikita/platforms/telegram/post_processor.py` (extend)

```python
async def process_voice_conversation(self, conversation_id: UUID):
    """
    Run 9-stage post-processing on voice transcript.

    Same pipeline as text, but with voice-specific adaptations:
    - Transcript parsing instead of message parsing
    - Source tag 'voice_call' for memory episodes
    """
    conversation = await self.conv_repo.get(conversation_id)

    if conversation.platform != 'voice':
        return await self.process_text_conversation(conversation_id)

    # Stage 1-2: Extract facts from transcript
    facts = await self.extract_facts_from_transcript(conversation.transcript_raw)

    # Stage 3: Generate summary
    summary = await self.generate_summary(conversation)

    # Stage 4: Detect unresolved threads
    threads = await self.detect_threads(conversation)

    # Stage 5: Generate Nikita thoughts
    thoughts = await self.generate_thoughts(conversation, source='voice_call')

    # Stage 6: Update Neo4j/Graphiti
    await self.update_memory(
        user_id=conversation.user_id,
        facts=facts,
        source='voice_call',
    )

    # Stage 7-9: Summaries, vice updates, finalization
    await self.finalize(conversation)
```

---

## User Story Mapping

| User Story | Tasks | Components |
|------------|-------|------------|
| US-1: Start Voice Call | T7 (initiate), T8 | API routes, Availability |
| US-2: Natural Conversation | T2, T4 | Config, ServerTools |
| US-3: Personality Consistency | T2, T9 | VoiceAgentConfig, Persona |
| US-4: Call Scoring | T5, T6 | VoiceCallScorer, Transcript |
| US-5: Cross-Modality Memory | T3, T6 | VoiceService, TranscriptManager |
| US-6: Server Tool Access | T4 | ServerToolHandler |
| US-7: Availability Progression | T8 | CallAvailability |
| US-8: Unified Event Scheduling | T10, T11 | ScheduledEventService, CrossPlatformDelivery |
| US-9: Cross-Agent Memory Access | T3, T12 | VoiceService, NikitaMemory integration |
| US-10: Post-Call Processing | T13, T14 | WebhookHandler, PostProcessingTrigger |

---

## Implementation Order (Updated Dec 2025)

**Prerequisites**: Spec 011 must be complete (pg_cron + scheduled_events)

```
Phase 0: Infrastructure (BLOCKER - Spec 011)
├── scheduled_events table migration
├── /tasks/deliver implementation
└── pg_cron configuration

Phase 1: Foundation
├── T1: Module structure
└── T2: Voice agent config (with dynamic variables)

Phase 2: Server Tools & Webhooks (US-2, US-6)
├── T4: Server tool handler
├── T7: API routes (partial)
└── T13: Post-call webhook handler (HMAC auth) ← NEW

Phase 3: Context & Memory (US-3, US-5, US-9)
├── T3: VoiceService
├── T6: Transcript persistence
└── T12: Cross-agent memory integration ← NEW

Phase 4: Scoring & Post-Processing (US-4, US-10)
├── T5: VoiceCallScorer
└── T14: Voice post-processing integration ← NEW

Phase 5: Event Scheduling (US-8) ← NEW
├── T10: Scheduled event integration
└── T11: Cross-platform event delivery

Phase 6: Availability & Polish (US-1, US-7)
├── T7: Complete API routes
├── T8: Call availability
└── T9: Voice behaviors
```

---

## Constitution Alignment

**§I.1 Invisible Game Interface**:
- ✅ Voice feels like real phone call, not game UI
- ✅ Natural conversation flow with silences and reactions

**§II.1 Temporal Memory Persistence**:
- ✅ Transcripts stored with timestamps
- ✅ Memory shared between voice and text

**§III.1 Scoring Formula**:
- ✅ Same metric weights apply to voice
- ✅ Aggregate scoring per call

**§VII.1 Test-Driven Development**:
- ✅ Tests before implementation
- ✅ 80%+ coverage required

---

## Dependencies (Updated Dec 2025)

| Spec | Status | Blocking? | Notes |
|------|--------|-----------|-------|
| 001-text-agent | ✅ Complete | No | Memory integration pattern |
| 003-scoring-engine | ✅ Complete | No | Voice uses same scoring |
| 006-vice-personalization | ✅ Complete | No | Vice injection working |
| 009-database-infrastructure | ✅ Complete | No | Conversation storage |
| 010-api-infrastructure | ✅ Complete | No | Cloud Run deployed |
| 011-background-tasks | ⚠️ 80% | **YES** | `scheduled_events` table + `/tasks/deliver` required |

### Spec 011 Dependency (Critical)

Voice agent requires Spec 011 completion for:
1. **`scheduled_events` table** - Cross-platform event storage (text + voice)
2. **`/tasks/deliver` endpoint** - Actual delivery logic (currently stubbed)
3. **pg_cron configuration** - Automatic scheduled event delivery

**Recommendation**: Complete Spec 011 before implementing Spec 007.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-29 | Initial plan from spec.md |
| 2.0 | 2025-12-29 | Updated for ElevenLabs 2.0: dynamic variables, HMAC webhooks, post-call processing |
| 2.1 | 2025-12-29 | Added FR-013 (Unified Scheduling), FR-014 (Cross-Agent Memory), FR-015 (Post-Call Processing) |
| 2.2 | 2025-12-29 | Added Tasks T10-T14 for new FRs, updated Dependencies (Spec 011 blocker) |
