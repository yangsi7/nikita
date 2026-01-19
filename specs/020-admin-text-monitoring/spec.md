---
feature: 020-admin-text-monitoring
created: 2026-01-08
status: Retroactive (Code Exists)
priority: P2
technology_agnostic: true
constitutional_compliance:
  article_iv: specification_first
  note: Retroactive spec - code was implemented before spec (SDD violation remediation)
---

# Feature Specification: Admin Text Monitoring

**IMPORTANT**: This is a RETROACTIVE specification. The implementation already exists in `nikita/api/routes/admin_debug.py:1018-1413`. This spec documents the existing behavior for SDD compliance.

---

## Summary

The Admin Text Monitoring feature provides Nikita developers with visibility into Telegram text conversations, the 9-stage post-processing pipeline, conversation threads, and Nikita's thoughts. It enables developers to debug text agent behavior, monitor pipeline health, and inspect memory operations.

**Problem Statement**: After text conversations end, developers need to verify post-processing completed correctly, inspect extracted threads and thoughts, and debug pipeline issues. Without monitoring, this requires complex database queries.

**Value Proposition**: Developers get complete visibility into text conversation data including the 9-stage pipeline status for debugging processing issues.

### CoD^Σ Overview

**System Model**:
```
Admin → TextMonitor → TextData
  ↓         ↓            ↓
Auth    Endpoints     DB_Queries

TextData := Conversations ∪ Threads ∪ Thoughts ∪ Pipeline
Endpoints ⊇ {ConvoList, ConvoDetail, Stats, Pipeline, Threads, Thoughts}
Pipeline := Stage1..Stage9 (9-stage post-processor)
```

---

## Functional Requirements

### FR-001: Text Conversation List
System MUST provide a paginated list of text (Telegram) conversations with filtering by user_id, status, and boss_fight_only.

**Rationale**: Core browsing capability for finding specific text conversations to debug
**Priority**: Must Have
**Implementation**: `admin_debug.py:1018-1086` - `list_text_conversations()`

### FR-002: Text Conversation Detail
System MUST display full conversation detail including all messages with analysis data, extracted entities, and processing metadata.

**Rationale**: Detailed inspection needed to debug message handling and extraction
**Priority**: Must Have
**Implementation**: `admin_debug.py:1089-1145` - `get_text_conversation_detail()`

### FR-003: Text Statistics
System MUST provide aggregated text conversation statistics including counts by time period (24h, 7d, 30d), boss fights, and processing status distribution.

**Rationale**: Overview metrics to understand text usage patterns and identify issues
**Priority**: Should Have
**Implementation**: `admin_debug.py:1148-1216` - `get_text_stats()`

### FR-004: Pipeline Status
System MUST display the 9-stage post-processing pipeline status for any conversation, showing which stages completed and their results.

**Rationale**: Critical for debugging post-processing failures and understanding data flow
**Priority**: Must Have
**Implementation**: `admin_debug.py:1219-1316` - `get_pipeline_status()`

### FR-005: Conversation Threads List
System MUST provide a paginated list of conversation threads with filtering by user_id and active status.

**Rationale**: Threads are key memory artifacts - developers need to inspect them
**Priority**: Should Have
**Implementation**: `admin_debug.py:1319-1367` - `list_threads()`

### FR-006: Nikita Thoughts List
System MUST provide a paginated list of Nikita's thoughts with filtering by user_id.

**Rationale**: Thoughts represent Nikita's internal state - useful for debugging persona behavior
**Priority**: Should Have
**Implementation**: `admin_debug.py:1370-1413` - `list_thoughts()`

---

## Non-Functional Requirements

### Performance
- Text list endpoint MUST return within 1 second for 50 items
- Pipeline status MUST return within 500ms (simple DB queries)

### Security
- All endpoints MUST require admin authentication (@silent-agents.com email)
- Message content may contain user PII - handle with care

### Reliability
- Database query failures MUST NOT crash the server
- Missing conversations MUST return 404 with clear message

---

## User Stories (CoD^Σ)

### US-1: Text Conversation Browser (Priority: P1 - Must-Have)
```
Developer → Browse text conversations → Find specific conversation to debug
Developer → filtered conversation list → locate problem conversation quickly
```
**Why P1**: Core debugging capability - can't inspect conversations without finding them first

**Acceptance Criteria**:
- **AC-FR001-001**: Given an admin on text monitoring, When page loads with default parameters, Then paginated list displays (50 per page)
- **AC-FR001-002**: Given an admin on text monitoring, When they filter by user_id, Then only that user's text conversations are shown
- **AC-FR001-003**: Given an admin on text monitoring, When they filter by status=processed, Then only processed conversations are shown
- **AC-FR001-004**: Given an admin on text monitoring, When they filter by boss_fight_only=true, Then only boss fights are shown
- **AC-FR001-005**: Given an admin on text monitoring, When they paginate with offset=50, Then the next 50 conversations are returned

**Implementation Reference**: `admin_debug.py:1018-1086`

---

### US-2: Text Conversation Detail (Priority: P1 - Must-Have)
```
Developer → View text conversation → Inspect messages and processing
Developer → full message history → understand what happened in the conversation
```
**Why P1**: Essential for debugging - need to see actual conversation content and analysis

**Acceptance Criteria**:
- **AC-FR002-001**: Given an admin viewing text detail, When the page loads, Then all messages are displayed with role, content, and timestamp
- **AC-FR002-002**: Given an admin viewing text detail, When the conversation has analysis, Then message analysis data is included
- **AC-FR002-003**: Given an admin viewing non-existent conversation, When detail is requested, Then 404 error is returned
- **AC-FR002-004**: Given an admin viewing text detail, When emotional_tone was extracted, Then it is displayed
- **AC-FR002-005**: Given an admin viewing text detail, When is_boss_fight is true, Then boss fight indicator is displayed

**Implementation Reference**: `admin_debug.py:1089-1145`

---

### US-3: Text Statistics (Priority: P2 - Important)
```
Developer → View text stats → Understand text usage patterns
Developer → aggregated metrics → assess text health at a glance
```
**Why P2**: Enhances monitoring but not blocking for individual conversation debugging

**Acceptance Criteria**:
- **AC-FR003-001**: Given an admin on text stats, When stats load, Then total_conversations_24h/7d/30d are displayed
- **AC-FR003-002**: Given an admin on text stats, When stats load, Then boss_fights_24h is displayed
- **AC-FR003-003**: Given an admin on text stats, When stats load, Then conversations_by_chapter distribution is displayed
- **AC-FR003-004**: Given an admin on text stats, When stats load, Then processing_stats (by status) is displayed

**Implementation Reference**: `admin_debug.py:1148-1216`

---

### US-4: Pipeline Status Inspection (Priority: P1 - Must-Have)
```
Developer → View pipeline status → Debug post-processing issues
Developer → 9-stage pipeline view → identify where processing failed
```
**Why P1**: Critical for debugging post-processing - need to know which stage failed

**Acceptance Criteria**:
- **AC-FR004-001**: Given an admin viewing pipeline status, When page loads, Then all 9 stages are displayed with completion status
- **AC-FR004-002**: Given an admin viewing pipeline status, When a stage completed, Then result_summary shows what was produced
- **AC-FR004-003**: Given an admin viewing pipeline status, When threads were created, Then threads_created count is displayed
- **AC-FR004-004**: Given an admin viewing pipeline status, When thoughts were created, Then thoughts_created count is displayed
- **AC-FR004-005**: Given an admin viewing non-existent conversation, When pipeline status requested, Then 404 error is returned

**Implementation Reference**: `admin_debug.py:1219-1316`

**9-Stage Pipeline**:
1. Ingestion - Messages stored
2. Entity Extraction - Facts extracted
3. Analysis - Summary and emotional tone
4. Thread Resolution - Conversation threads created
5. Thought Generation - Nikita thoughts created
6. Graph Updates - Neo4j memory updates
7. Summary Rollups - Daily summaries
8. Vice Processing - Vice signals detected
9. Finalization - Status set to 'processed'

---

### US-5: Thread and Thought Inspection (Priority: P2 - Important)
```
Developer → View threads and thoughts → Inspect memory artifacts
Developer → thread/thought lists → verify memory system working
```
**Why P2**: Enhances debugging but not essential for basic conversation inspection

**Acceptance Criteria**:
- **AC-FR005-001**: Given an admin on threads list, When page loads, Then paginated thread list displays
- **AC-FR005-002**: Given an admin on threads list, When filtering by user_id, Then only that user's threads are shown
- **AC-FR005-003**: Given an admin on threads list, When filtering by active_only=true, Then only active threads are shown
- **AC-FR006-001**: Given an admin on thoughts list, When page loads, Then paginated thought list displays
- **AC-FR006-002**: Given an admin on thoughts list, When filtering by user_id, Then only that user's thoughts are shown

**Implementation Reference**: `admin_debug.py:1319-1413`

---

## Implementation Evidence

**Code Location**: `nikita/api/routes/admin_debug.py:1018-1413`

**Endpoints Implemented**:
| Endpoint | Line | Method |
|----------|------|--------|
| `/admin/debug/text/conversations` | 1018 | `list_text_conversations` |
| `/admin/debug/text/conversations/{id}` | 1089 | `get_text_conversation_detail` |
| `/admin/debug/text/stats` | 1148 | `get_text_stats` |
| `/admin/debug/text/pipeline/{id}` | 1219 | `get_pipeline_status` |
| `/admin/debug/text/threads` | 1319 | `list_threads` |
| `/admin/debug/text/thoughts` | 1370 | `list_thoughts` |

**Response Models** (admin_debug.py):
- `TextConversationListResponse`
- `TextConversationDetailResponse`
- `TextStatsResponse`
- `PipelineStatusResponse`
- `ThreadListResponse`
- `ThoughtListResponse`

---

## Scope

### In-Scope Features
- Text conversation list with pagination and filtering
- Text conversation detail with messages
- Text conversation statistics
- 9-stage pipeline status display
- Conversation threads list
- Nikita thoughts list
- Admin authentication (inherited from admin_debug router)

### Out-of-Scope
- Pipeline retry/reprocess actions (would need write endpoints)
- Thread/thought editing (read-only for debugging)
- Memory graph visualization (would need Neo4j integration)

---

## Risks & Mitigations

### Risk 1: Large Message Arrays
**Likelihood**: Medium (0.5)
**Impact**: Medium (5) - Slow response
**Risk Score**: r = 2.5
**Mitigation**: Already paginated at conversation level; individual conversations typically <50 messages

### Risk 2: Pipeline Stage Inference
**Likelihood**: Low (0.2)
**Impact**: Low (2) - Inaccurate status
**Risk Score**: r = 0.4
**Mitigation**: Stages are inferred from data presence; explicit tracking would require schema changes

---

## Success Metrics

- Developers can find and inspect any text conversation within 30 seconds
- Pipeline status accurately reflects processing state
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
- [x] 9-stage pipeline documented

**Status**: Ready for Testing (code exists, tests missing)

---

**Version**: 1.0
**Last Updated**: 2026-01-08
**Implementation Status**: COMPLETE (tests pending)
