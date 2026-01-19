# Tasks: Admin Voice Monitoring (019)

**Spec**: [spec.md](./spec.md)
**Plan**: [plan.md](./plan.md)
**Status**: Implementation COMPLETE, Tests PENDING

---

## Task Overview

| Task | User Story | Status | Notes |
|------|------------|--------|-------|
| T1.1 | US-1 | [x] Complete | Voice conversation list endpoint |
| T1.2 | US-2 | [x] Complete | Voice conversation detail endpoint |
| T1.3 | US-3 | [x] Complete | Voice statistics endpoint |
| T1.4 | US-4 | [x] Complete | ElevenLabs list endpoint |
| T1.5 | US-4 | [x] Complete | ElevenLabs detail endpoint |
| T2.1 | ALL | [ ] Pending | Write functional tests |

---

## Phase 1: Implementation (COMPLETE)

### T1.1: Voice Conversation List Endpoint
- **Status**: [x] Complete
- **File**: `nikita/api/routes/admin_debug.py:718-790`
- **ACs**:
  - [x] AC-FR001-001: Paginated list with 50 per page default
  - [x] AC-FR001-002: Filter by user_id parameter
  - [x] AC-FR001-003: Filter by status parameter
  - [x] AC-FR001-004: Pagination via offset parameter

### T1.2: Voice Conversation Detail Endpoint
- **Status**: [x] Complete
- **File**: `nikita/api/routes/admin_debug.py:793-847`
- **ACs**:
  - [x] AC-FR002-001: Transcript messages with role and content
  - [x] AC-FR002-002: Extracted entities displayed
  - [x] AC-FR002-003: 404 for non-existent conversation
  - [x] AC-FR002-004: Emotional tone displayed

### T1.3: Voice Statistics Endpoint
- **Status**: [x] Complete
- **File**: `nikita/api/routes/admin_debug.py:850-908`
- **ACs**:
  - [x] AC-FR003-001: total_calls_24h/7d/30d displayed
  - [x] AC-FR003-002: calls_by_chapter distribution
  - [x] AC-FR003-003: calls_by_status distribution

### T1.4: ElevenLabs List Endpoint
- **Status**: [x] Complete
- **File**: `nikita/api/routes/admin_debug.py:911-963`
- **ACs**:
  - [x] AC-FR004-001: Recent calls from ElevenLabs API
  - [x] AC-FR004-002: 500 error on API failure

### T1.5: ElevenLabs Detail Endpoint
- **Status**: [x] Complete
- **File**: `nikita/api/routes/admin_debug.py:966-1010`
- **ACs**:
  - [x] AC-FR005-001: Full transcript with tool calls
  - [x] AC-FR005-002: Cost displayed when available

---

## Phase 2: Testing (PENDING)

### T2.1: Write Functional Tests
- **Status**: [ ] Pending
- **File**: `tests/api/routes/test_admin_voice.py` (TO CREATE)
- **Test Requirements**:
  - [ ] test_list_voice_conversations_pagination
  - [ ] test_list_voice_conversations_filter_by_user
  - [ ] test_list_voice_conversations_filter_by_status
  - [ ] test_voice_conversation_detail_success
  - [ ] test_voice_conversation_detail_404
  - [ ] test_voice_conversation_detail_includes_transcript
  - [ ] test_voice_stats_returns_aggregations
  - [ ] test_voice_stats_counts_by_chapter
  - [ ] test_voice_stats_counts_by_status
  - [ ] test_elevenlabs_list_success
  - [ ] test_elevenlabs_list_api_error
  - [ ] test_elevenlabs_detail_success
  - [ ] test_elevenlabs_detail_includes_tool_calls
  - [ ] test_all_endpoints_require_admin_auth

---

## Progress Summary

| Phase | Tasks | Completed | Status |
|-------|-------|-----------|--------|
| Implementation | 5 | 5 | Complete |
| Testing | 1 | 0 | Pending |
| **Total** | **6** | **5** | **83%** |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-01-08 | Retroactive spec created, documented existing implementation |
