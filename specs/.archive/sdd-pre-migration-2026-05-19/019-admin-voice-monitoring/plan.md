# Implementation Plan: Admin Voice Monitoring (019)

**Spec**: [spec.md](./spec.md)
**Status**: RETROACTIVE - Implementation already exists

---

## Executive Summary

This is a **retroactive** implementation plan documenting the already-completed voice monitoring endpoints. The code exists at `nikita/api/routes/admin_debug.py:718-1010`. This plan documents the implementation decisions for SDD compliance.

**Implementation Status**: COMPLETE (5 endpoints)
**Testing Status**: PENDING (0 tests)

---

## Architecture Decisions

### Decision 1: Single Router Pattern
**Choice**: Voice monitoring endpoints added to existing `admin_debug.py` router
**Rationale**: Consolidates all admin endpoints under single `/admin/debug/` prefix
**Alternative Considered**: Separate `admin_voice.py` router
**Trade-off**: More cohesive admin interface vs larger file

### Decision 2: Dual Data Sources
**Choice**: Both database (Conversation model) and ElevenLabs API
**Rationale**:
- Database has processed transcripts, scores, extracted entities
- ElevenLabs API has raw data, cost, tool calls
**Trade-off**: More comprehensive but depends on external API

### Decision 3: Pagination Model
**Choice**: Offset-based pagination for DB, cursor-based for ElevenLabs
**Rationale**:
- DB uses standard offset/limit (SQLAlchemy pattern)
- ElevenLabs API uses cursor-based (their API design)

---

## Technical Design

### Response Models

```python
# Voice Conversation List
class VoiceConversationListItem(BaseModel):
    id: UUID
    user_id: UUID
    user_name: str | None
    started_at: datetime
    ended_at: datetime | None
    message_count: int
    score_delta: float | None
    chapter_at_time: int | None
    elevenlabs_session_id: str | None
    status: str
    conversation_summary: str | None

class VoiceConversationListResponse(BaseModel):
    items: list[VoiceConversationListItem]
    count: int
    has_more: bool

# Voice Conversation Detail
class TranscriptEntryResponse(BaseModel):
    role: str
    content: str
    timestamp: str | None

class VoiceConversationDetailResponse(VoiceConversationListItem):
    emotional_tone: str | None
    transcript_raw: str | None
    messages: list[TranscriptEntryResponse]
    extracted_entities: dict | None
    processed_at: datetime | None

# Voice Stats
class VoiceStatsResponse(BaseModel):
    total_calls_24h: int
    total_calls_7d: int
    total_calls_30d: int
    calls_by_chapter: dict[int, int]
    calls_by_status: dict[str, int]
    processing_stats: dict[str, int]

# ElevenLabs API Models
class ElevenLabsCallListItem(BaseModel):
    conversation_id: str
    agent_id: str
    start_time_unix: int | None
    call_duration_secs: int | None
    message_count: int | None
    status: str
    call_successful: bool | None
    transcript_summary: str | None
    direction: str | None

class ElevenLabsTranscriptTurn(BaseModel):
    role: str
    message: str
    time_in_call_secs: float | None
    tool_calls: list | None
    tool_results: list | None
```

### Database Queries

**Voice Conversation List**:
```sql
SELECT * FROM conversations
WHERE platform = 'voice'
ORDER BY started_at DESC
LIMIT 50 OFFSET 0
```

**Voice Stats**:
```sql
-- 24h count
SELECT COUNT(*) FROM conversations
WHERE platform = 'voice' AND started_at >= NOW() - INTERVAL '24 hours'

-- By chapter
SELECT chapter_at_time, COUNT(*) FROM conversations
WHERE platform = 'voice' AND chapter_at_time IS NOT NULL
GROUP BY chapter_at_time
```

### External API Integration

**ElevenLabs Client**: `nikita/agents/voice/elevenlabs_client.py`
- `list_conversations(agent_id, limit, cursor)` → List recent calls
- `get_conversation(conversation_id)` → Full call detail with transcript

---

## Implementation Order (Completed)

```
Phase 1: DB Endpoints (DONE)
├── T1.1: list_voice_conversations
├── T1.2: get_voice_conversation_detail
└── T1.3: get_voice_stats

Phase 2: ElevenLabs Endpoints (DONE)
├── T1.4: list_elevenlabs_calls
└── T1.5: get_elevenlabs_call_detail

Phase 3: Testing (PENDING)
└── T2.1: Write functional tests
```

---

## Dependencies

### Internal Dependencies
- `nikita/db/models/conversation.py` - Conversation model
- `nikita/api/dependencies/auth.py` - Admin auth (`get_current_admin_user`)
- `nikita/api/dependencies/database.py` - DB session (`get_async_session`)

### External Dependencies
- `elevenlabs` Python SDK - ElevenLabs API access
- Supabase - Database storage

---

## Testing Strategy

### Test File: `tests/api/routes/test_admin_voice.py`

**Fixtures Needed**:
- Mock admin user (bypasses auth)
- Mock voice conversations in DB
- Mock ElevenLabs client responses

**Test Categories**:
1. **List Tests**: Pagination, filtering, empty results
2. **Detail Tests**: Success, 404, transcript parsing
3. **Stats Tests**: Aggregations, time windows
4. **ElevenLabs Tests**: Success, API errors, pagination

---

## Risk Mitigations

| Risk | Mitigation | Status |
|------|------------|--------|
| ElevenLabs API rate limits | Error handling with 500 response | Implemented |
| Large transcripts | Pagination at conversation level | Implemented |
| Missing conversations | 404 with clear message | Implemented |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-08 | Retroactive plan documenting existing implementation |
