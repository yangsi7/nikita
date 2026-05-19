# Spec 034: Admin User Monitoring Dashboard

**Status**: Draft
**Created**: 2026-01-22
**Author**: Claude (SDD Workflow)

---

## 1. Overview

### 1.1 Problem Statement

The Nikita project has grown to 33 completed specifications with complex subsystems (voice agent, text agent, 3 memory graphs, 9-stage post-processing pipeline, humanization modules). Current admin tools (specs 016-020) provide basic visibility but lack:

1. **Comprehensive user-centric view** - No single dashboard to see all data for one user
2. **Generated prompt inspection** - Cannot view prompt layers (system, humanization, context)
3. **Memory graph visibility** - 3 Neo4j graphs stored but not viewable in admin
4. **Pipeline debugging** - Cannot trace 9-stage post-processing status
5. **Score timeline visualization** - No charts for metric trends
6. **Audit trail** - No logging of admin data access (compliance requirement)

### 1.2 Proposed Solution

A comprehensive admin monitoring dashboard that provides:
- Single-user focus (expandable to multi-user)
- 9 route-based pages covering all data entities
- Full drill-down from summary to detail
- Audit logging for all admin access
- Neo4j integration with timeout handling

### 1.3 Success Criteria

- [ ] All 9 pages functional with real data
- [ ] Full drill-down from user → conversation → prompt → scoring
- [ ] Charts render for score trends
- [ ] Search and filter working across all tables
- [ ] Dashboard overview loads in <2s
- [ ] Detail views respond in <500ms
- [ ] Audit logs capture all admin data access
- [ ] Neo4j cold start handled gracefully (loading UX)

---

## 2. Functional Requirements

### FR-001: User Monitoring

**Description**: View and explore user data with full context

**Acceptance Criteria**:
- AC-001.1: List all users with pagination (50/page), sortable by email, chapter, score, last_active
- AC-001.2: Filter users by game_status, chapter, engagement_state
- AC-001.3: User detail page shows profile, game state, metrics, engagement state
- AC-001.4: Navigate from user to their conversations, memory, scores

### FR-002: Conversation Monitoring

**Description**: View conversation threads with full message history

**Acceptance Criteria**:
- AC-002.1: List conversations with pagination, filterable by platform (telegram/voice), status, date range
- AC-002.2: Conversation detail shows full message thread (user + assistant)
- AC-002.3: Show conversation metadata: created_at, platform, status, summary
- AC-002.4: Navigate from conversation to prompts, pipeline status, scoring

### FR-003: Generated Prompt Inspection

**Description**: View generated prompts with layer breakdown

**Acceptance Criteria**:
- AC-003.1: List prompts by user or conversation, sortable by created_at, token_count
- AC-003.2: Prompt detail shows full content with syntax highlighting
- AC-003.3: Display prompt layers: system, humanization, context tiers
- AC-003.4: Show context_snapshot (JSONB) with expandable JSON viewer
- AC-003.5: Display token_count and generation_time_ms metrics

### FR-004: Post-Processing Pipeline

**Description**: View 9-stage pipeline status for conversations

**Acceptance Criteria**:
- AC-004.1: Show pipeline status per conversation (not_started, running, completed, failed)
- AC-004.2: Display 9 stages with individual status (ingestion, extraction, analysis, threads, thoughts, graph_updates, rollups, vice_processing, finalization)
- AC-004.3: Show timing for each stage (started_at, completed_at, duration_ms)
- AC-004.4: Display error details for failed stages (stack_trace, error_message)

### FR-005: Scoring History

**Description**: View score timeline and boss encounters

**Acceptance Criteria**:
- AC-005.1: Score timeline chart (Recharts) showing trust, intimacy, attraction, commitment over time
- AC-005.2: Date range picker for chart (default: 7 days)
- AC-005.3: Score history table with event_type, deltas, created_at
- AC-005.4: Boss encounters table showing chapter, outcome (pass/fail), judgment reasoning

### FR-006: Voice Session Monitoring

**Description**: View voice sessions with transcripts

**Acceptance Criteria**:
- AC-006.1: List voice sessions with duration, turn_count, created_at
- AC-006.2: Session detail shows full transcript (user + nikita turns)
- AC-006.3: Display per-turn scoring deltas
- AC-006.4: Show ElevenLabs metadata (conversation_id, agent_id)

### FR-007: Memory Graph Monitoring

**Description**: View 3 Neo4j memory graphs per user

**Acceptance Criteria**:
- AC-007.1: Memory overview showing graph counts (user_facts, relationship_episodes, nikita_events)
- AC-007.2: User graph table: fact content, source, created_at (50 facts max)
- AC-007.3: Relationship graph table: episode content, type, created_at (30 episodes max)
- AC-007.4: Nikita graph table: event content, type, created_at (20 events max)
- AC-007.5: Handle Neo4j cold start with loading UX (60s warning)
- AC-007.6: Timeout handling (30s max query time)

### FR-008: Job Execution Monitoring

**Description**: View background job executions

**Acceptance Criteria**:
- AC-008.1: List jobs with job_name, status, duration, created_at
- AC-008.2: Filter by status (RUNNING, COMPLETED, FAILED)
- AC-008.3: Job detail shows full result JSONB
- AC-008.4: Failed jobs show stack_trace
- AC-008.5: Show pipeline stage breakdown for post-processing jobs

### FR-009: Error Monitoring

**Description**: View and filter error logs

**Acceptance Criteria**:
- AC-009.1: Error log table with type, message, user_id, created_at
- AC-009.2: Filter by error type, severity, date range
- AC-009.3: Search by error message content
- AC-009.4: Error detail shows full stack trace
- AC-009.5: Error stats cards showing counts by category

### FR-010: System Overview

**Description**: Dashboard overview with system health metrics

**Acceptance Criteria**:
- AC-010.1: Active users count (last 24h)
- AC-010.2: Conversations today count
- AC-010.3: Processing success rate percentage
- AC-010.4: Average response time
- AC-010.5: Recent activity feed (last 10 events)
- AC-010.6: Alerts panel for failures/stuck conversations

### FR-011: Audit Logging (CRITICAL)

**Description**: Log all admin access to sensitive data

**Acceptance Criteria**:
- AC-011.1: Create audit_logs table with admin_id, action, resource_type, resource_id, user_id, created_at
- AC-011.2: Log all admin endpoint calls with @audit_log decorator
- AC-011.3: Admin can view audit logs for their own actions
- AC-011.4: Index audit_logs by admin_id and user_id for efficient queries

### FR-012: Cross-Module Navigation

**Description**: Seamless drill-down between related entities

**Acceptance Criteria**:
- AC-012.1: User page links to their conversations, memory, scores
- AC-012.2: Conversation page links to prompts, pipeline, scoring
- AC-012.3: Breadcrumb navigation showing current path
- AC-012.4: Back navigation preserves list filters

---

## 3. Non-Functional Requirements

### NFR-001: Performance

| Metric | Target | Measurement |
|--------|--------|-------------|
| Dashboard overview load | <2s | Time to interactive |
| Detail view response | <500ms | API response time |
| Table pagination | <300ms | Page change time |
| Chart rendering | <1s | After data received |
| Neo4j query timeout | 30s max | With graceful failure |

### NFR-002: Security

| Requirement | Implementation |
|-------------|----------------|
| Admin authentication | @silent-agents.com domain OR allowlist |
| Audit logging | All data access logged to audit_logs table |
| PII protection | Log sanitization (no message content in logs) |
| Rate limiting | 30 Neo4j queries/hour per admin |

### NFR-003: Scalability

| Scenario | Handling |
|----------|----------|
| Large conversation history | Server-side pagination (50/page) |
| Multiple concurrent admins | Stateless API, React Query caching |
| Growing user base | Database indexes on filtered columns |

### NFR-004: Reliability

| Scenario | Handling |
|----------|----------|
| Neo4j cold start | Loading UX with 60s warning |
| API endpoint failure | Error boundary per route |
| Invalid JSON data | Schema validation, graceful degradation |

---

## 4. Technical Architecture

### 4.1 Backend (FastAPI)

**New Endpoints**:
```
GET /admin/users/{id}/memory        → MemorySnapshot
GET /admin/users/{id}/scores        → ScoreTimeline
GET /admin/users/{id}/boss          → BossEncounters
GET /admin/conversations/{id}/prompts  → PromptHistory
GET /admin/conversations/{id}/pipeline → PipelineStatus
GET /admin/metrics/overview         → SystemMetrics
GET /admin/errors                   → ErrorList
GET /admin/audit-logs               → AuditLogs
```

**Extended Endpoints**:
```
GET /admin/users                    → Add pagination, filters, stats join
GET /admin/users/{id}               → Add full stats, game state
GET /admin/conversations            → Add date range, platform filter
GET /admin/conversations/{id}       → Add pipeline status
GET /admin/prompts/recent           → Add user filter
GET /admin/jobs                     → Add status filter
GET /admin/voice/sessions           → Add transcript preview
```

**New Service**:
```python
class AdminMonitoringService:
    async def get_system_overview() -> SystemMetrics
    async def get_error_summary() -> ErrorSummary
    async def get_memory_stats(user_id) -> MemorySnapshot
    async def get_score_timeline(user_id, days) -> ScoreTimeline
    async def get_boss_encounters(user_id) -> BossEncounters
```

**New Repository Methods**:
```python
UserRepository.get_with_full_stats(id)
ConversationRepository.get_by_user_paginated(user_id, page, size)
ConversationRepository.get_pipeline_status(id)
GeneratedPromptRepository.get_by_conversation_id(conv_id)
ScoreHistoryRepository.get_timeline_data(user_id, days)
ScoreHistoryRepository.get_boss_encounters(user_id)
```

### 4.2 Frontend (Next.js App Router)

**Route Structure**:
```
/admin/monitoring/
├── layout.tsx                         # Nav + ErrorBoundary
├── page.tsx                           # Overview
├── users/
│   ├── page.tsx                       # User list
│   └── [id]/
│       ├── page.tsx                   # User detail
│       ├── memory/page.tsx            # Memory graphs
│       └── scores/page.tsx            # Score timeline
├── conversations/
│   ├── page.tsx                       # Conversation list
│   └── [id]/
│       ├── page.tsx                   # Thread + messages
│       ├── prompts/page.tsx           # Prompt layers
│       └── pipeline/page.tsx          # 9-stage status
├── prompts/page.tsx                   # Prompt list
├── scoring/page.tsx                   # Charts + boss table
├── voice/page.tsx                     # Voice sessions
├── memory/page.tsx                    # System memory stats
├── jobs/page.tsx                      # Job executions
└── errors/page.tsx                    # Error log
```

**Shared Components**:
```
components/admin/
├── AdminNavigation.tsx          # Route-based navigation
├── DataTable.tsx                # Reusable table with pagination
├── JsonViewer.tsx               # JSON display component
├── Neo4jLoadingState.tsx        # Neo4j cold start UX
├── ErrorBoundary.tsx            # Per-route error handling
└── charts/
    └── ScoreTimelineChart.tsx   # Recharts line chart
```

### 4.3 Database Changes

**New Table**:
```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    admin_id UUID NOT NULL,
    admin_email TEXT NOT NULL,
    action TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    resource_id UUID,
    user_id UUID,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**New Indexes**:
```sql
CREATE INDEX idx_conversations_status ON conversations(status);
CREATE INDEX idx_conversations_platform ON conversations(platform);
CREATE INDEX idx_job_executions_status ON job_executions(status);
CREATE INDEX idx_conversations_user_status ON conversations(user_id, status);
CREATE INDEX idx_audit_logs_admin ON audit_logs(admin_id, created_at DESC);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id, created_at DESC);
```

### 4.4 Security Components

**Audit Logging Middleware**:
```python
# nikita/api/dependencies/audit.py
async def audit_admin_action(
    admin_id: UUID,
    action: str,
    resource_type: str,
    resource_id: UUID | None,
    user_id: UUID | None,
    session: AsyncSession
)
```

**PII-Safe Logging**:
```python
# nikita/api/dependencies/logging.py
class PiiSafeFormatter(logging.Formatter):
    """Redacts sensitive data from logs"""
```

**Rate Limiter**:
```python
admin_neo4j_limiter = RateLimiter(
    max_requests=30,
    window_seconds=3600,
)
```

---

## 5. Dependencies

### 5.1 Existing Specs

| Spec | Dependency | Purpose |
|------|------------|---------|
| 016-admin-debug-portal | Extend | Base admin patterns |
| 018-admin-prompt-viewing | Extend | Prompt display |
| 019-admin-voice-monitoring | Extend | Voice session UI |
| 020-admin-text-monitoring | Extend | Text conversation UI |
| 029-context-comprehensive | Data | 3-graph memory |
| 030-text-continuity | Data | Context snapshots |
| 031-post-processing-unification | Data | Job execution logs |
| 032-voice-agent-optimization | Data | Voice context |

### 5.2 External Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| recharts | ^3.5.1 | Score timeline charts |
| shadcn/ui | latest | UI components |
| @tanstack/react-query | ^5.90 | Data fetching |
| Neo4j Aura | - | Memory graph storage |

---

## 6. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Neo4j cold start (60-73s) | Medium | High | Loading UX, timeout handling, retry logic |
| Large datasets slow UI | Low | Medium | Server-side pagination, indexes |
| PII in logs | Medium | High | PiiSafeFormatter, structured logging |
| Admin abuse | Low | Medium | Audit logging, rate limiting |
| Complex navigation | Medium | Low | Breadcrumbs, URL state |

---

## 7. Out of Scope

- Multi-tenant admin (other organizations)
- Real-time WebSocket updates (polling acceptable)
- Export functionality (CSV/JSON download)
- Bulk operations (mass delete, mass update)
- Admin user management (add/remove admins)
- Custom alert configuration

---

## 8. References

- Requirements: docs-to-process/20260122-requirements-admin-monitoring.md
- Discovery: docs-to-process/20260122-discovery-findings.md
- Architecture: docs-to-process/20260122-tree-of-thought-v2.md
- Existing admin: nikita/api/routes/admin_debug.py
- Portal patterns: portal/src/app/admin/
