# Spec 034: Admin User Monitoring Dashboard - Implementation Plan

**Status**: Draft
**Created**: 2026-01-22
**Spec Reference**: specs/034-admin-user-monitoring/spec.md

---

## 1. Implementation Phases

### Phase A: Foundation (3-4 hours)

**Objective**: Establish base infrastructure for all subsequent work

| Task | Description | Effort | Deps |
|------|-------------|--------|------|
| A.1 | Database migration (indexes + audit_logs) | 30min | None |
| A.2 | Audit logging middleware | 1h | A.1 |
| A.3 | PII-safe logging formatter | 30min | None |
| A.4 | Response schemas (8 new) | 1h | None |
| A.5 | Shared UI components (Neo4jLoadingState, JsonViewer) | 1h | None |

**Deliverables**:
- `alembic/versions/0009_admin_monitoring.py` (migration)
- `nikita/api/dependencies/audit.py` (audit middleware)
- `nikita/api/dependencies/logging.py` (PII formatter)
- `nikita/api/schemas/monitoring.py` (response schemas)
- `portal/src/components/admin/` (shared components)

### Phase B: Backend Endpoints (5-6 hours) [P]

**Objective**: Implement all API endpoints in parallel tracks

| Track | Tasks | Effort | Parallel |
|-------|-------|--------|----------|
| B.1 | User endpoints (4 endpoints) | 1.5h | [P] |
| B.2 | Conversation endpoints (4 endpoints) | 1.5h | [P] |
| B.3 | Prompts + Scoring endpoints (3 endpoints) | 1.5h | [P] |
| B.4 | Memory + Jobs + Errors endpoints (3 endpoints) | 1.5h | [P] |

**Track B.1: User Endpoints**
- B.1.1: GET /admin/users (extend with stats)
- B.1.2: GET /admin/users/{id} (extend with full stats)
- B.1.3: GET /admin/users/{id}/memory (NEW)
- B.1.4: GET /admin/users/{id}/scores (NEW)

**Track B.2: Conversation Endpoints**
- B.2.1: GET /admin/conversations (extend with filters)
- B.2.2: GET /admin/conversations/{id} (extend with pipeline)
- B.2.3: GET /admin/conversations/{id}/prompts (NEW)
- B.2.4: GET /admin/conversations/{id}/pipeline (NEW)

**Track B.3: Prompts + Scoring Endpoints**
- B.3.1: GET /admin/prompts/recent (extend with user filter)
- B.3.2: GET /admin/users/{id}/boss (NEW)
- B.3.3: GET /admin/metrics/overview (NEW)

**Track B.4: Memory + Jobs + Errors**
- B.4.1: GET /admin/jobs (extend with status filter)
- B.4.2: GET /admin/errors (NEW)
- B.4.3: GET /admin/audit-logs (NEW)

**Deliverables**:
- `nikita/api/routes/admin_monitoring.py` (8 new endpoints)
- `nikita/api/services/admin_monitoring.py` (AdminMonitoringService)
- Repository method additions (6 methods)

### Phase C: Frontend Routes (6-8 hours) [P]

**Objective**: Implement all UI routes in parallel

| Track | Tasks | Effort | Parallel |
|-------|-------|--------|----------|
| C.1 | Layout + Overview | 1.5h | [P] |
| C.2 | Users module (list + detail + memory + scores) | 2h | [P] |
| C.3 | Conversations module (list + detail + prompts + pipeline) | 2h | [P] |
| C.4 | Supporting pages (prompts, scoring, voice, memory, jobs, errors) | 3h | [P] |

**Track C.1: Layout + Overview**
- C.1.1: /admin/monitoring/layout.tsx (navigation + error boundary)
- C.1.2: /admin/monitoring/page.tsx (overview with health cards)

**Track C.2: Users Module**
- C.2.1: /admin/monitoring/users/page.tsx (user list)
- C.2.2: /admin/monitoring/users/[id]/page.tsx (user detail)
- C.2.3: /admin/monitoring/users/[id]/memory/page.tsx (memory graphs)
- C.2.4: /admin/monitoring/users/[id]/scores/page.tsx (score timeline)

**Track C.3: Conversations Module**
- C.3.1: /admin/monitoring/conversations/page.tsx (conversation list)
- C.3.2: /admin/monitoring/conversations/[id]/page.tsx (thread detail)
- C.3.3: /admin/monitoring/conversations/[id]/prompts/page.tsx (prompt layers)
- C.3.4: /admin/monitoring/conversations/[id]/pipeline/page.tsx (9-stage status)

**Track C.4: Supporting Pages**
- C.4.1: /admin/monitoring/prompts/page.tsx (prompt list)
- C.4.2: /admin/monitoring/scoring/page.tsx (charts + boss table)
- C.4.3: /admin/monitoring/voice/page.tsx (voice sessions)
- C.4.4: /admin/monitoring/memory/page.tsx (system memory stats)
- C.4.5: /admin/monitoring/jobs/page.tsx (job executions)
- C.4.6: /admin/monitoring/errors/page.tsx (error log)

**Deliverables**:
- 15 Next.js page files
- React Query hooks for data fetching
- Recharts components for visualizations

### Phase D: Integration + Polish (2-3 hours)

**Objective**: Complete cross-module features and testing

| Task | Description | Effort | Deps |
|------|-------------|--------|------|
| D.1 | Cross-page navigation verification | 45min | C.* |
| D.2 | Breadcrumb component | 30min | C.* |
| D.3 | Error aggregation endpoint | 45min | B.4.2 |
| D.4 | E2E testing (all routes) | 1h | All |

**Deliverables**:
- Verified navigation between all pages
- E2E test coverage
- Final bug fixes

---

## 2. Repository Method Implementations

### UserRepository

```python
async def get_with_full_stats(self, user_id: UUID) -> UserWithStats:
    """Join users + user_metrics + engagement_state + game_progress."""
    stmt = (
        select(User)
        .options(
            selectinload(User.metrics),
            selectinload(User.engagement_state),
        )
        .where(User.id == user_id)
    )
    result = await self.session.execute(stmt)
    return result.scalar_one_or_none()
```

### ConversationRepository

```python
async def get_by_user_paginated(
    self, user_id: UUID, page: int, page_size: int
) -> list[Conversation]:
    """Get user's conversations with pagination."""
    offset = (page - 1) * page_size
    stmt = (
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await self.session.execute(stmt)
    return list(result.scalars().all())

async def get_pipeline_status(self, conversation_id: UUID) -> PipelineStatus:
    """Get 9-stage pipeline status from job_executions."""
    stmt = (
        select(JobExecution)
        .where(
            JobExecution.job_name == "process_conversation",
            JobExecution.result["conversation_id"].astext == str(conversation_id)
        )
        .order_by(JobExecution.created_at.desc())
        .limit(1)
    )
    result = await self.session.execute(stmt)
    job = result.scalar_one_or_none()
    # Parse stages from job.result JSONB
```

### GeneratedPromptRepository

```python
async def get_by_conversation_id(
    self, conversation_id: UUID
) -> list[GeneratedPrompt]:
    """Get all prompts for a conversation."""
    stmt = (
        select(GeneratedPrompt)
        .where(GeneratedPrompt.conversation_id == conversation_id)
        .order_by(GeneratedPrompt.created_at)
    )
    result = await self.session.execute(stmt)
    return list(result.scalars().all())
```

### ScoreHistoryRepository

```python
async def get_timeline_data(
    self, user_id: UUID, days: int = 7
) -> list[ScoreTimelinePoint]:
    """Get score timeline for charts."""
    cutoff = datetime.now(UTC) - timedelta(days=days)
    stmt = (
        select(ScoreHistory)
        .where(
            ScoreHistory.user_id == user_id,
            ScoreHistory.created_at >= cutoff
        )
        .order_by(ScoreHistory.created_at)
    )
    result = await self.session.execute(stmt)
    return list(result.scalars().all())

async def get_boss_encounters(self, user_id: UUID) -> list[ScoreHistory]:
    """Get boss encounter events only."""
    stmt = (
        select(ScoreHistory)
        .where(
            ScoreHistory.user_id == user_id,
            ScoreHistory.event_type == "boss_encounter"
        )
        .order_by(ScoreHistory.created_at.desc())
    )
    result = await self.session.execute(stmt)
    return list(result.scalars().all())
```

---

## 3. AdminMonitoringService Implementation

```python
# nikita/api/services/admin_monitoring.py

class AdminMonitoringService:
    def __init__(
        self,
        session: AsyncSession,
        user_repo: UserRepository,
        conv_repo: ConversationRepository,
        job_repo: JobExecutionRepository,
        memory: NikitaMemory,
    ):
        self.session = session
        self.user_repo = user_repo
        self.conv_repo = conv_repo
        self.job_repo = job_repo
        self.memory = memory

    async def get_system_overview(self) -> SystemMetrics:
        """Aggregate system health metrics."""
        now = datetime.now(UTC)
        yesterday = now - timedelta(hours=24)

        # Active users (last 24h)
        active_users = await self.user_repo.count_active_since(yesterday)

        # Conversations today
        conversations_today = await self.conv_repo.count_since(yesterday)

        # Processing success rate
        jobs = await self.job_repo.get_recent_stats(hours=24)
        success_rate = jobs.completed / max(jobs.total, 1) * 100

        # Average response time
        avg_response_time = await self.conv_repo.get_avg_response_time(hours=24)

        return SystemMetrics(
            active_users=active_users,
            conversations_today=conversations_today,
            processing_success_rate=success_rate,
            average_response_time_ms=avg_response_time,
            updated_at=now,
        )

    async def get_memory_stats(self, user_id: UUID) -> MemorySnapshot:
        """Get 3-graph memory snapshot for user."""
        try:
            async with asyncio.timeout(30):  # 30s timeout
                user_facts = await self.memory.search_memory(
                    "*", ["user"], user_id, limit=50
                )
                relationship = await self.memory.search_memory(
                    "*", ["relationship"], user_id, limit=30
                )
                nikita = await self.memory.search_memory(
                    "*", ["nikita"], user_id, limit=20
                )
        except TimeoutError:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "Memory database is warming up",
                    "code": "NEO4J_TIMEOUT",
                    "retry_after": 60,
                }
            )

        return MemorySnapshot(
            user_id=user_id,
            user_facts=user_facts,
            relationship_episodes=relationship,
            nikita_events=nikita,
            counts={
                "user": len(user_facts),
                "relationship": len(relationship),
                "nikita": len(nikita),
            },
        )

    async def get_error_summary(
        self, hours: int = 24, limit: int = 50
    ) -> ErrorSummary:
        """Get error log with categorization."""
        cutoff = datetime.now(UTC) - timedelta(hours=hours)
        jobs = await self.job_repo.get_failed_since(cutoff, limit)

        # Categorize errors
        by_type: dict[str, int] = {}
        for job in jobs:
            error_type = job.result.get("error_type", "unknown")
            by_type[error_type] = by_type.get(error_type, 0) + 1

        return ErrorSummary(
            total=len(jobs),
            by_type=by_type,
            recent_errors=[
                ErrorLogEntry(
                    id=job.id,
                    type=job.result.get("error_type", "unknown"),
                    message=job.result.get("error", ""),
                    user_id=job.result.get("user_id"),
                    created_at=job.created_at,
                )
                for job in jobs
            ],
        )
```

---

## 4. Frontend Hooks Implementation

```typescript
// portal/src/hooks/use-admin-monitoring.ts

export function useSystemOverview() {
  return useQuery({
    queryKey: ['admin', 'overview'],
    queryFn: () => apiClient.get<SystemMetrics>('/admin/metrics/overview'),
    refetchInterval: 30000, // 30s polling
  });
}

export function useUserWithStats(userId: string) {
  return useQuery({
    queryKey: ['admin', 'users', userId],
    queryFn: () => apiClient.get<UserWithStats>(`/admin/users/${userId}`),
  });
}

export function useUserMemory(userId: string) {
  return useQuery({
    queryKey: ['admin', 'users', userId, 'memory'],
    queryFn: () => apiClient.get<MemorySnapshot>(`/admin/users/${userId}/memory`),
    retry: 3,
    retryDelay: 5000, // 5s between retries for Neo4j cold start
  });
}

export function useConversationPrompts(conversationId: string) {
  return useQuery({
    queryKey: ['admin', 'conversations', conversationId, 'prompts'],
    queryFn: () =>
      apiClient.get<PromptHistory>(`/admin/conversations/${conversationId}/prompts`),
  });
}

export function useScoreTimeline(userId: string, days: number = 7) {
  return useQuery({
    queryKey: ['admin', 'users', userId, 'scores', days],
    queryFn: () =>
      apiClient.get<ScoreTimeline>(`/admin/users/${userId}/scores`, {
        params: { days },
      }),
  });
}

export function useErrorLog(params: ErrorLogParams) {
  return useQuery({
    queryKey: ['admin', 'errors', params],
    queryFn: () => apiClient.get<ErrorSummary>('/admin/errors', { params }),
  });
}
```

---

## 5. Testing Strategy

### Unit Tests (Backend)

| Module | Tests | Coverage |
|--------|-------|----------|
| AdminMonitoringService | 15 tests | Methods, edge cases, timeouts |
| Repository methods | 12 tests | CRUD, pagination, filters |
| Audit middleware | 8 tests | Logging, PII redaction |
| Response schemas | 10 tests | Validation, serialization |

### Integration Tests (API)

| Endpoint | Tests | Focus |
|----------|-------|-------|
| /admin/users | 5 tests | Pagination, filters, auth |
| /admin/conversations | 5 tests | Filters, pipeline status |
| /admin/metrics/overview | 3 tests | Aggregation accuracy |
| /admin/errors | 4 tests | Error categorization |
| /admin/audit-logs | 3 tests | Admin access logging |

### E2E Tests (Frontend)

| Flow | Steps | Verification |
|------|-------|--------------|
| User drill-down | List → Detail → Memory → Scores | Navigation, data display |
| Conversation drill-down | List → Thread → Prompts → Pipeline | All layers visible |
| Error monitoring | Filter → Detail → Stack trace | Search, filter work |
| System health | Dashboard overview | All cards render |

---

## 6. Database Migration

```python
# alembic/versions/0009_admin_monitoring.py

def upgrade():
    # Audit logs table
    op.execute("""
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

        CREATE INDEX idx_audit_logs_admin ON audit_logs(admin_id, created_at DESC);
        CREATE INDEX idx_audit_logs_user ON audit_logs(user_id, created_at DESC);
    """)

    # Performance indexes
    op.execute("""
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_conversations_status
            ON conversations(status);
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_conversations_platform
            ON conversations(platform);
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_job_executions_status
            ON job_executions(status);
        CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_conversations_user_status
            ON conversations(user_id, status);
    """)

def downgrade():
    op.execute("DROP TABLE IF EXISTS audit_logs;")
    op.execute("DROP INDEX IF EXISTS idx_conversations_status;")
    op.execute("DROP INDEX IF EXISTS idx_conversations_platform;")
    op.execute("DROP INDEX IF EXISTS idx_job_executions_status;")
    op.execute("DROP INDEX IF EXISTS idx_conversations_user_status;")
```

---

## 7. Effort Estimates

| Phase | Tasks | Effort | Parallel |
|-------|-------|--------|----------|
| A: Foundation | 5 | 3-4h | Sequential |
| B: Backend | 14 | 5-6h | [P] 4 tracks |
| C: Frontend | 15 | 6-8h | [P] 4 tracks |
| D: Integration | 4 | 2-3h | Sequential |
| **Total** | **38** | **16-21h** | |

---

## 8. Risk Mitigation

| Risk | Mitigation | Owner |
|------|------------|-------|
| Neo4j cold start | Loading UX + retry logic | Phase A.5 |
| Large datasets | Pagination + indexes | Phase A.1 |
| PII in logs | PiiSafeFormatter | Phase A.3 |
| Admin accountability | Audit logging | Phase A.2 |

---

## 9. Definition of Done

- [ ] All 38 tasks completed
- [ ] 45+ unit tests passing
- [ ] 20+ integration tests passing
- [ ] E2E flows verified
- [ ] Audit logging functional
- [ ] <2s dashboard load time
- [ ] <500ms detail view response
- [ ] Documentation updated
