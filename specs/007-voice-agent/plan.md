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

## ElevenLabs Integration

### Agent Configuration
**File**: `nikita/config/elevenlabs.py`

```python
ELEVENLABS_AGENT_CONFIG = {
    "agent_id": settings.elevenlabs_agent_id,
    "voice_id": settings.elevenlabs_nikita_voice_id,
    "model": "claude-sonnet-4-20250514",

    # System prompt includes Nikita persona
    "system_prompt": """
    You are Nikita, the character from "Don't Get Dumped."
    [Base persona instructions]
    {chapter_behavior}
    {vice_preferences}
    """,

    # Server tools for backend access
    "server_tools": [
        {
            "name": "get_context",
            "description": "Get user context and memory",
            "webhook_url": f"{API_BASE}/api/v1/voice/server-tool",
        },
        {
            "name": "update_memory",
            "description": "Save new facts to memory",
            "webhook_url": f"{API_BASE}/api/v1/voice/server-tool",
        },
        {
            "name": "end_call",
            "description": "Handle call ending",
            "webhook_url": f"{API_BASE}/api/v1/voice/server-tool",
        },
    ],
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

---

## Implementation Order

```
Phase 1: Foundation
├── T1: Module structure
└── T2: Voice agent config

Phase 2: Server Tools (US-2, US-6)
├── T4: Server tool handler
└── T7: API routes (partial)

Phase 3: Context & Memory (US-3, US-5)
├── T3: VoiceService
└── T6: Transcript persistence

Phase 4: Scoring (US-4)
└── T5: VoiceCallScorer

Phase 5: Availability & Polish (US-1, US-7)
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

## Dependencies

| Spec | Status | Blocking? |
|------|--------|-----------|
| 001-text-agent | ✅ Complete | No |
| 003-scoring-engine | ⏳ Pending | Scoring integration |
| 006-vice-personalization | ⏳ Pending | Vice injection |
| 010-api-infrastructure | ✅ Audit PASS | No |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-29 | Initial plan from spec.md |
