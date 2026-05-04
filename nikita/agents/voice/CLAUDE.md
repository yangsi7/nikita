# voice/ - ElevenLabs Voice Agent

## Purpose

Voice agent implementation for Nikita using ElevenLabs Conversational AI 2.0 with Server Tools pattern.

## Status: 100% Complete (Spec 007)

**14 modules** | **5 API endpoints**

## Module Structure

```
voice/
├── __init__.py           # Package exports
├── availability.py       # Chapter-based call availability (10% Ch1 → 95% Ch5)
├── config.py             # VoiceAgentConfig - system prompts, TTS settings
├── context.py            # DynamicVariablesBuilder, ConversationConfigBuilder
├── deps.py               # FastAPI dependency injection
├── elevenlabs_client.py  # ElevenLabs SDK wrapper (API calls, agent config)
├── inbound.py            # InboundCallHandler, VoiceSessionManager
├── models.py             # Pydantic models (CallSession, ServerToolRequest/Response)
├── scheduling.py         # VoiceEventScheduler (cross-platform events)
├── scoring.py            # VoiceCallScorer (transcript → metric deltas)
├── server_tools.py       # ServerToolHandler (get_context, get_memory, score_turn)
├── service.py            # VoiceService (initiate_call, end_call)
├── transcript.py         # TranscriptManager (fetch, persist, summarize)
└── tts_config.py         # TTSConfigManager (chapter-based voice settings)
```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/voice/initiate` | POST | Start voice call, get agent config |
| `/api/v1/voice/server-tool` | POST | Handle server tool calls from ElevenLabs |
| `/api/v1/voice/webhook` | POST | Process call events (connected, ended) |
| `/api/v1/voice/pre-call` | POST | Inbound call webhook (Twilio → ElevenLabs) |
| `/api/v1/voice/availability/{user_id}` | GET | Check if Nikita is available |

## Key Patterns

### Server Tools Pattern

ElevenLabs calls our API with tool requests during conversation:

```python
# nikita/agents/voice/server_tools.py
class ServerToolHandler:
    async def get_context(self, user_id: UUID) -> dict:
        """Load user facts, threads, memories for context"""

    async def get_memory(self, user_id: UUID, query: str) -> dict:
        """Query SupabaseMemory (pgVector) for relevant memories"""

    async def score_turn(self, user_id: UUID, turn_data: dict) -> dict:
        """Score individual conversation turn"""

    async def update_memory(self, user_id: UUID, fact: str) -> dict:
        """Store new fact via SupabaseMemory (pgVector)"""
```

### Inbound Call Flow

```
Twilio → POST /pre-call → InboundCallHandler
  ↓
Phone lookup → get_by_phone_number()
  ↓
Availability check → chapter-based probability
  ↓
Accept: dynamic_variables + conversation_config_override
Reject: message explaining unavailability
```

### Voice Call Scoring

```python
# nikita/agents/voice/scoring.py
scorer = VoiceCallScorer()

# Score entire call from transcript
call_score = await scorer.score_call(
    user_id=user_id,
    session_id=session_id,
    transcript=transcript,
    context=context,
)

# Apply to user metrics
await scorer.apply_score(user_id, call_score)
```

## Configuration

### TTS Settings by Chapter

```python
# nikita/agents/voice/tts_config.py
CHAPTER_TTS = {
    1: TTSSettings(stability=0.75, similarity_boost=0.65, speed=0.95),  # Reserved
    3: TTSSettings(stability=0.55, similarity_boost=0.80, speed=1.05),  # Playful
    5: TTSSettings(stability=0.45, similarity_boost=0.90, speed=1.10),  # Passionate
}
```

### Availability Rates

```python
# nikita/agents/voice/availability.py
CHAPTER_AVAILABILITY = {
    1: 0.10,  # 10% - Nikita is busy
    2: 0.30,  # 30%
    3: 0.50,  # 50%
    4: 0.70,  # 70%
    5: 0.95,  # 95% - Almost always available
}
```

## Testing

```bash
# Run all voice tests
pytest tests/agents/voice/ -v

# Run specific test file
pytest tests/agents/voice/test_inbound.py -v

# Run with coverage
pytest tests/agents/voice/ --cov=nikita/agents/voice
```

## Dependencies

- **ElevenLabs API**: Conversational AI 2.0, Server Tools
- **Twilio**: Phone number (+41445056044) for inbound
- **SupabaseMemory**: pgVector-based memory queries during conversation (Spec 042)

## Related

- [Spec 007: Voice Agent](../../../specs/007-voice-agent/spec.md)
- [API Routes](../../api/routes/voice.py)
- [Text Agent](../text/CLAUDE.md)

## Callers

- `nikita/api/routes/voice.py:350` POST `/server-tool` — ElevenLabs server-tool callback entry; validated via `_validate_signed_token` at `:347`.
- `nikita/api/routes/voice.py:727` — pipeline invocation site post-call (1 of 5 PipelineOrchestrator entry points).
- `nikita/agents/voice/transcript.py:228` + `:377` — Pydantic AI batch utilities `extract_agent` + `summarize_agent` are post-call only; called from voice-transcript processing endpoints.

## Gotchas

- **Live voice is NOT a Pydantic AI agent**. The conversational voice loop runs through ElevenLabs Conversational AI 2.0 Server Tools (`server_tools.py`, `service.py`, `elevenlabs_client.py`). Pydantic AI agents in `transcript.py:200,361` are post-call batch utilities ONLY (W4 audit).
- **Function name in `inbound.py:223` is `handle_incoming_call`** — earlier docs say `handle_inbound_call` (wrong).
- **`config/elevenlabs.py` was DELETED in PR #231** (dead multi-agent code). Don't try to import it.
- **ElevenLabs agent IDs are per-environment** (dev vs prod) — managed in `nikita/config/settings.py` + ElevenLabs dashboard. Document BOTH sides when configuring.
- **Voice timeout = 2s** for server-tool calls (ElevenLabs constraint). Tools must return fast.
- **`asyncio.wait_for` wrapper in tests** — unwrap by mocking `asyncio.wait_for` to call coroutine directly. See `tests/agents/voice/conftest.py`.

## Navigation

- Backend module map: [`../../CLAUDE.md`](../../CLAUDE.md)
- Architecture canonical: [`../../../memory/architecture.md`](../../../memory/architecture.md) §"Pydantic AI Agents"
- Voice integration config: [`../../../memory/integrations.md`](../../../memory/integrations.md) §ElevenLabs

Last verified: 2026-05-05
