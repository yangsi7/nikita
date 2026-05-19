---
feature: 019-admin-voice-monitoring
created: 2026-01-08
status: Retroactive (Code Exists)
priority: P2
technology_agnostic: true
constitutional_compliance:
  article_iv: specification_first
  note: Retroactive spec - code was implemented before spec (SDD violation remediation)
---

# Feature Specification: Admin Voice Monitoring

**IMPORTANT**: This is a RETROACTIVE specification. The implementation already exists in `nikita/api/routes/admin_debug.py:718-1010`. This spec documents the existing behavior for SDD compliance.

---

## Summary

The Admin Voice Monitoring feature provides Nikita developers with visibility into voice conversations, ElevenLabs API calls, and voice call statistics. It enables developers to debug voice agent behavior, monitor call quality, and inspect transcript data.

**Problem Statement**: After voice calls end, developers need to inspect transcripts, verify post-processing completed, and debug issues with ElevenLabs integration. Without monitoring, this requires database queries and ElevenLabs dashboard access.

**Value Proposition**: Developers get unified visibility into all voice data - both database records and ElevenLabs API data - in a single admin interface.

### CoD^Σ Overview

**System Model**:
```
Admin → VoiceMonitor → VoiceData
  ↓         ↓            ↓
Auth    Endpoints     DB + ElevenLabs

VoiceData := DB_Conversations ∪ ElevenLabs_API
Endpoints ⊇ {List, Detail, Stats, ElevenLabsList, ElevenLabsDetail}
```

---

## Functional Requirements

### FR-001: Voice Conversation List
System MUST provide a paginated list of voice conversations from the database with filtering by user_id and status.

**Rationale**: Core browsing capability for finding specific voice calls to debug
**Priority**: Must Have
**Implementation**: `admin_debug.py:718-790` - `list_voice_conversations()`

### FR-002: Voice Conversation Detail
System MUST display full conversation detail including transcript, messages, extracted entities, and processing status.

**Rationale**: Detailed inspection needed to debug transcript issues and post-processing
**Priority**: Must Have
**Implementation**: `admin_debug.py:793-847` - `get_voice_conversation_detail()`

### FR-003: Voice Statistics
System MUST provide aggregated voice call statistics including counts by time period (24h, 7d, 30d), by chapter, and by processing status.

**Rationale**: Overview metrics to understand voice usage patterns and identify issues
**Priority**: Should Have
**Implementation**: `admin_debug.py:850-908` - `get_voice_stats()`

### FR-004: ElevenLabs API Call List
System MUST fetch and display recent calls from the ElevenLabs Conversations API with pagination.

**Rationale**: Access to calls that may not have been processed yet, or ElevenLabs-side metadata
**Priority**: Should Have
**Implementation**: `admin_debug.py:911-963` - `list_elevenlabs_calls()`

### FR-005: ElevenLabs API Call Detail
System MUST fetch full call detail from ElevenLabs including transcript, tool calls, cost, and audio availability.

**Rationale**: Debug raw ElevenLabs data when database records are incomplete or missing
**Priority**: Should Have
**Implementation**: `admin_debug.py:966-1010` - `get_elevenlabs_call_detail()`

---

## Non-Functional Requirements

### Performance
- Voice list endpoint MUST return within 1 second for 50 items
- ElevenLabs API calls MUST timeout after 10 seconds with appropriate error

### Security
- All endpoints MUST require admin authentication (@silent-agents.com email)
- ElevenLabs API key MUST NOT be exposed in responses

### Reliability
- ElevenLabs API failures MUST return 500 with descriptive error message
- Database query failures MUST NOT crash the server

---

## User Stories (CoD^Σ)

### US-1: Voice Conversation Browser (Priority: P1 - Must-Have)
```
Developer → Browse voice conversations → Find specific call to debug
Developer → filtered call list → locate problem call quickly
```
**Why P1**: Core debugging capability - can't inspect calls without finding them first

**Acceptance Criteria**:
- **AC-FR001-001**: Given an admin on voice monitoring, When page loads with default parameters, Then paginated list displays (50 per page)
- **AC-FR001-002**: Given an admin on voice monitoring, When they filter by user_id, Then only that user's voice calls are shown
- **AC-FR001-003**: Given an admin on voice monitoring, When they filter by status=processed, Then only processed calls are shown
- **AC-FR001-004**: Given an admin on voice monitoring, When they paginate with offset=50, Then the next 50 calls are returned

**Implementation Reference**: `admin_debug.py:718-790`

---

### US-2: Voice Conversation Detail (Priority: P1 - Must-Have)
```
Developer → View voice conversation → Inspect transcript and processing
Developer → full transcript → understand what happened in the call
```
**Why P1**: Essential for debugging - need to see actual conversation content

**Acceptance Criteria**:
- **AC-FR002-001**: Given an admin viewing voice detail, When the page loads, Then transcript messages are displayed with role and content
- **AC-FR002-002**: Given an admin viewing voice detail, When the conversation was processed, Then extracted_entities are displayed
- **AC-FR002-003**: Given an admin viewing non-existent conversation, When detail is requested, Then 404 error is returned
- **AC-FR002-004**: Given an admin viewing voice detail, When emotional_tone was extracted, Then it is displayed

**Implementation Reference**: `admin_debug.py:793-847`

---

### US-3: Voice Call Statistics (Priority: P2 - Important)
```
Developer → View voice stats → Understand voice usage patterns
Developer → aggregated metrics → assess voice health at a glance
```
**Why P2**: Enhances monitoring but not blocking for individual call debugging

**Acceptance Criteria**:
- **AC-FR003-001**: Given an admin on voice stats, When stats load, Then total_calls_24h/7d/30d are displayed
- **AC-FR003-002**: Given an admin on voice stats, When stats load, Then calls_by_chapter distribution is displayed
- **AC-FR003-003**: Given an admin on voice stats, When stats load, Then calls_by_status (processed/active/failed) is displayed

**Implementation Reference**: `admin_debug.py:850-908`

---

### US-4: ElevenLabs Integration (Priority: P2 - Important)
```
Developer → Access ElevenLabs data → Debug calls not in database
Developer → raw ElevenLabs calls → inspect server-side data
```
**Why P2**: Valuable for debugging but separate from core database monitoring

**Acceptance Criteria**:
- **AC-FR004-001**: Given an admin on ElevenLabs list, When page loads, Then recent calls from ElevenLabs API are displayed
- **AC-FR004-002**: Given an admin on ElevenLabs list, When ElevenLabs API fails, Then 500 error with descriptive message is returned
- **AC-FR005-001**: Given an admin on ElevenLabs detail, When viewing a call, Then full transcript with tool calls is displayed
- **AC-FR005-002**: Given an admin on ElevenLabs detail, When call has cost data, Then cost is displayed

**Implementation Reference**: `admin_debug.py:911-1010`

---

## Implementation Evidence

**Code Location**: `nikita/api/routes/admin_debug.py:718-1010`

**Endpoints Implemented**:
| Endpoint | Line | Method |
|----------|------|--------|
| `/admin/debug/voice/conversations` | 718 | `list_voice_conversations` |
| `/admin/debug/voice/conversations/{id}` | 793 | `get_voice_conversation_detail` |
| `/admin/debug/voice/stats` | 850 | `get_voice_stats` |
| `/admin/debug/voice/elevenlabs` | 911 | `list_elevenlabs_calls` |
| `/admin/debug/voice/elevenlabs/{id}` | 966 | `get_elevenlabs_call_detail` |

**Response Models** (admin_debug.py):
- `VoiceConversationListResponse`
- `VoiceConversationDetailResponse`
- `VoiceStatsResponse`
- `ElevenLabsCallListResponse`
- `ElevenLabsCallDetailResponse`

---

## Scope

### In-Scope Features
- Voice conversation list with pagination and filtering
- Voice conversation detail with transcript
- Voice call statistics aggregations
- ElevenLabs API integration for raw call data
- Admin authentication (inherited from admin_debug router)

### Out-of-Scope
- Audio playback (ElevenLabs has this in their dashboard)
- Real-time call monitoring (would need WebSocket)
- Call recording download (security/legal concerns)

---

## Risks & Mitigations

### Risk 1: ElevenLabs API Rate Limits
**Likelihood**: Medium (0.5)
**Impact**: Low (2) - Graceful degradation
**Risk Score**: r = 1.0
**Mitigation**: Return error message, suggest using ElevenLabs dashboard directly

### Risk 2: Large Transcripts
**Likelihood**: Low (0.2)
**Impact**: Medium (5) - Slow response
**Risk Score**: r = 1.0
**Mitigation**: Already paginated at conversation level

---

## Success Metrics

- Developers can find and inspect any voice call within 30 seconds
- ElevenLabs API integration failures are clearly reported
- All endpoints respond within 1 second for typical queries

---

## Stakeholders

**Owner**: Development Team
**Created By**: Claude Code (Retroactive spec for SDD compliance)
**Created**: 2026-01-08

---

## Approvals

- [x] **Engineering Lead**: User - 2026-01-08 (Retroactive approval)
- [ ] **Security**: Pending review

---

## Specification Checklist

**Retroactive Spec Requirements**:
- [x] All endpoints documented with line references
- [x] All user stories have ≥2 acceptance criteria
- [x] Implementation evidence provided
- [x] Response models documented

**Status**: Ready for Testing (code exists, tests missing)

---

**Version**: 1.0
**Last Updated**: 2026-01-08
**Implementation Status**: COMPLETE (tests pending)
