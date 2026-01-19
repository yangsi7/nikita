# Implementation Plan: Admin Text Monitoring (020)

**Spec**: [spec.md](./spec.md)
**Status**: RETROACTIVE - Implementation already exists

---

## Executive Summary

This is a **retroactive** implementation plan documenting the already-completed text monitoring endpoints. The code exists at `nikita/api/routes/admin_debug.py:1018-1413`. This plan documents the implementation decisions for SDD compliance.

**Implementation Status**: COMPLETE (6 endpoints)
**Testing Status**: PENDING (0 tests)

---

## Architecture Decisions

### Decision 1: Single Router Pattern
**Choice**: Text monitoring endpoints added to existing `admin_debug.py` router
**Rationale**: Consolidates all admin endpoints under single `/admin/debug/` prefix
**Trade-off**: More cohesive admin interface vs larger file

### Decision 2: Pipeline Stage Inference
**Choice**: Infer pipeline stage completion from data presence (not explicit tracking)
**Rationale**:
- Avoids schema changes for pipeline tracking
- Works with existing conversation model
**Trade-off**: Less precise tracking but simpler implementation

### Decision 3: Separate Threads/Thoughts Endpoints
**Choice**: Dedicated endpoints for threads and thoughts instead of embedding in conversation detail
**Rationale**:
- Supports cross-conversation querying
- Allows filtering by user without loading all conversations
**Trade-off**: More endpoints but more flexible

---

## Technical Design

### Response Models

```python
# Text Conversation List
class TextConversationListItem(BaseModel):
    id: UUID
    user_id: UUID
    user_name: str | None
    started_at: datetime
    ended_at: datetime | None
    message_count: int
    score_delta: float | None
    chapter_at_time: int | None
    is_boss_fight: bool
    status: str
    conversation_summary: str | None
    emotional_tone: str | None

class TextConversationListResponse(BaseModel):
    items: list[TextConversationListItem]
    count: int
    has_more: bool

# Text Conversation Detail
class MessageResponse(BaseModel):
    role: str
    content: str
    timestamp: str | None
    analysis: dict | None

class TextConversationDetailResponse(TextConversationListItem):
    messages: list[MessageResponse]
    extracted_entities: dict | None
    processed_at: datetime | None
    processing_attempts: int
    last_message_at: datetime | None

# Text Stats
class TextStatsResponse(BaseModel):
    total_conversations_24h: int
    total_conversations_7d: int
    total_conversations_30d: int
    total_messages_24h: int | None
    boss_fights_24h: int
    avg_messages_per_conversation: float | None
    conversations_by_chapter: dict[int, int]
    conversations_by_status: dict[str, int]
    processing_stats: dict[str, int]

# Pipeline Status
class PipelineStageStatus(BaseModel):
    stage_name: str
    stage_number: int
    completed: bool
    result_summary: str | None

class PipelineStatusResponse(BaseModel):
    conversation_id: UUID
    status: str
    processing_attempts: int
    processed_at: datetime | None
    stages: list[PipelineStageStatus]
    threads_created: int
    thoughts_created: int
    entities_extracted: int
    summary: str | None

# Threads
class ThreadListItem(BaseModel):
    id: UUID
    user_id: UUID
    thread_type: str
    topic: str
    is_active: bool
    message_count: int
    created_at: datetime
    last_mentioned_at: datetime | None

class ThreadListResponse(BaseModel):
    items: list[ThreadListItem]
    count: int

# Thoughts
class ThoughtListItem(BaseModel):
    id: UUID
    user_id: UUID
    content: str
    thought_type: str
    created_at: datetime

class ThoughtListResponse(BaseModel):
    items: list[ThoughtListItem]
    count: int
```

### 9-Stage Pipeline

```
Stage 1: Ingestion         → Messages stored in conversation.messages
Stage 2: Entity Extraction → extracted_entities populated
Stage 3: Analysis          → conversation_summary + emotional_tone
Stage 4: Thread Resolution → ConversationThread records created
Stage 5: Thought Generation→ NikitaThought records created
Stage 6: Graph Updates     → Neo4j memory updated (not tracked)
Stage 7: Summary Rollups   → daily_summaries updated
Stage 8: Vice Processing   → Vice signals detected
Stage 9: Finalization      → status set to 'processed'
```

---

## Implementation Order (Completed)

```
Phase 1: Core Endpoints (DONE)
├── T1.1: list_text_conversations
├── T1.2: get_text_conversation_detail
└── T1.3: get_text_stats

Phase 2: Pipeline Monitoring (DONE)
└── T1.4: get_pipeline_status

Phase 3: Memory Artifacts (DONE)
├── T1.5: list_threads
└── T1.6: list_thoughts

Phase 4: Testing (PENDING)
└── T2.1: Write functional tests
```

---

## Dependencies

### Internal Dependencies
- `nikita/db/models/conversation.py` - Conversation model
- `nikita/db/models/context.py` - ConversationThread, NikitaThought models
- `nikita/api/dependencies/auth.py` - Admin auth (`get_current_admin_user`)
- `nikita/api/dependencies/database.py` - DB session (`get_async_session`)

### External Dependencies
- Supabase - Database storage

---

## Testing Strategy

### Test File: `tests/api/routes/test_admin_text.py`

**Fixtures Needed**:
- Mock admin user (bypasses auth)
- Mock text conversations with messages
- Mock threads and thoughts in DB

**Test Categories**:
1. **List Tests**: Pagination, filtering, boss fights
2. **Detail Tests**: Success, 404, message parsing
3. **Stats Tests**: Aggregations, time windows
4. **Pipeline Tests**: Stage completion, 404
5. **Threads/Thoughts Tests**: Pagination, filtering

---

## Risk Mitigations

| Risk | Mitigation | Status |
|------|------------|--------|
| Large message arrays | Conversation-level pagination | Implemented |
| Pipeline inference accuracy | Based on data presence | Accepted |
| Missing conversations | 404 with clear message | Implemented |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-08 | Retroactive plan documenting existing implementation |
